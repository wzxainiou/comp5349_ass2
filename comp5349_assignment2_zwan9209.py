# -*- coding: utf-8 -*-
"""comp5349_assignment2_zwan9209.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Otz-XRZXMJZR6wlFq253UsZxpGlgpiB7

### Introduction
This notebook demonstrates a few useful methods for loading json file and for handling nested json objects. The example file is `test.json` in assignment 2.
"""

# !pip install pyspark

# !pip install pandas

# from google.colab import drive
# drive.mount('/content/drive')

from pyspark.sql import Column
from pyspark.sql.functions import upper
from pyspark.sql.functions import split

from pyspark.sql import SparkSession
spark = SparkSession \
    .builder \
    .appName("COMP5349 A2 Data Loading Example") \
    .getOrCreate()

spark.eventLog.logBlockUpdates.enabled=True
"""### Load Json file as data frame"""

test_data = "s3://comp5349-2022/test.json"
test_init_df = spark.read.json(test_data)

# The original file will be loaded into a data frame with one row and two columns
test_init_df.show(1)

"""### Check the schema of a data frame

`printSchema` is a useful method to display the schema of a data frame
"""

test_init_df.printSchema()

test_init_df.count()

"""### `select` and `explode`

The [`select`](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.DataFrame.select.html) method is used to select one or more columns for the source dataframe. 

The [`explode`](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.functions.explode.html) method is used to expand an array into multiple rows. The [`alias`](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.Column.alias.html) method is used to specify a name for column storing the array element.

"""

from pyspark.sql.functions import explode
test_data_df= test_init_df.select((explode("data").alias('data')))

test_data_df.printSchema()

test_data_df.count()

test_paragraph_df = test_data_df.select(explode("data.paragraphs").alias("paragraph")).cache()

test_paragraph_df.printSchema()

test_paragraph_df.count()

test_paragraph_df.take(1)

# divide the questions from the whole paragraph of each context.
test_questions_df = test_paragraph_df.select(explode("paragraph.qas").alias("questions")).cache()

# the count is 41 multiple number of the paragraph, because there are 41 questions for each context.
test_questions_df.count()

test_questions_df.printSchema()

# change the Structures of the paragraphs
test_paragraph_df.printSchema()

# define the ave number of positive samples of each question

# define the functions

# used to mark the possible samples
def possible_counter(answer):
  return [answer[0],1]

def count_ave(value):
  result = []

  ave = int(value[1][0]/value[1][1])
  result = [value[0],ave]
  return result

# modify df structure
test_questions_counter_df = test_questions_df.filter("questions.is_impossible == False").select("questions.question","questions.answers.answer_start")
test_questions_counter_df.printSchema()

# count the number of possible samples of each question
test_possible_counter_rdd = test_questions_counter_df.rdd.map(list).map(possible_counter).reduceByKey(lambda a,b: a+b)
# test_possible_counter_rdd = test_possible_counter_rdd.map(possible_counter)
# test_possible_counter_rdd = test_possible_counter_rdd.reduceByKey(lambda a,b: a+b)

# count the number of answers of each question
test_answer_counter_df = test_questions_counter_df.select("question",explode("answer_start"))
test_answer_counter_rdd = test_answer_counter_df.rdd.map(list).map(possible_counter).reduceByKey(lambda a,b: a+b)
# test_answer_counter_rdd = test_answer_counter_rdd.map(possible_counter)
# test_answer_counter_rdd = test_answer_counter_rdd.reduceByKey(lambda a,b: a+b)

# calculate the ave possible samples of each question
test_ave_possible_rdd = test_answer_counter_rdd.join(test_possible_counter_rdd).map(count_ave)
# test_ave_possible_rdd = test_ave_possible_rdd.map(count_ave)

# transform the results into dict 
test_ave_possible_dict = test_ave_possible_rdd.collectAsMap()

print(test_ave_possible_dict)

# define the functions

# define the start and the end for each question, both for possible and impossible questions

def define_context_answer(answer):
  result = []
  store = []
  if answer[2] == True:
    result.append([answer[4],[0,0],answer[3],0])

    result = (result)
  else:
    i = len(answer[0])
    for j in range(i):
      end = answer[0][j] + len(answer[1][j])
      store.append([answer[0][j],end])
    
    result.append([answer[4],store,answer[3],i])
 
  return result


test_context_answer_step_df = test_paragraph_df.select(explode("paragraph.qas").alias("questions"),"paragraph.context").cache()
test_context_answer_step_df = test_context_answer_step_df.withColumnRenamed("paragraph.context","context")
test_context_answer_step_df.printSchema()
print(test_context_answer_step_df.count())

test_context_answer_df = test_context_answer_step_df.select("questions.answers.answer_start","questions.answers.text","questions.is_impossible","questions.question","context")
# test_context_answer_df = test_context_answer_df.select("context","questions.answers.answer_start","questions.answers.text","questions.is_impossible","questions.question")
# test_context_answer_df = test_context_answer_df.select("answer_start","text","text","question","context")
test_context_answer_df.printSchema()
print(test_context_answer_df.count())

# transform the df into rdd
test_context_answer_rdd= test_context_answer_df.rdd.map(list)

# # transform the data structure in to [context, [s,e], questions, is_impossible]
test_context_answer_rdd = test_context_answer_rdd.flatMap(define_context_answer)
print(test_context_answer_rdd.take(5))

# split the context into segments
def split_context_segment(input):
  context = input[0]
  segments_result = []
  result = []
  segment = []
  start = 0
  end = 4096
  while(end<len(context)):
    segment = context[start:end]
    segments_result.append([segment,start,end])
    start = start + 2048
    end = start + 4096
  if start != len(context):
    segment = context[start:]
    segments_result.append([segment,start,len(context)])
  result.append(segments_result)
  result.append(input[1])
  result.append(input[2])
  result.append(input[3])
  return result

# divide all the context into segments which length is 4096 and mark the s,e of each segment
test_segment_answer_rdd = test_context_answer_rdd.map(split_context_segment)
print(test_segment_answer_rdd.take(2))

import random

# define the functions
def select_samples(input):
  result = []
  sample = []
  negative = 0

  # locate the impossible_nagetive samples for the imposiible questions
  if input[3] == 0:
    try:
      negative = test_ave_possible_dict[input[2]]
      list_negative = list(range(len(input[0])))
      if negative <= ((len(input[0])-1)/3+1):
        for i in range(negative):
          index = random.choice(list_negative)
          result.append([input[0][index][0],input[2],0,0])

          if (index + 1) not in list_negative:
            if (index - 1) not in list_negative:
              list_negative.remove(index)
            else:
              list_negative.remove(index)
              list_negative.remove(index -1)

          else:
            if (index - 1) not in list_negative:
              list_negative.remove(index)
              list_negative.remove(index +1)
            else:
              list_negative.remove(index)
              list_negative.remove(index -1)
              list_negative.remove(index +1)

      elif negative >= len(input[0]):
        for i in range(len(input[0])):
          result.append([input[0][i][0],input[2],0,0])

      else:
        for i in range(negative):
          index = random.choice(list_negative)
          list_negative.remove(index)
          result.append([input[0][index][0],input[2],0,0])

    except:
      negative = 0
    
  # locate the samples for the posiible questions
  else:
    negative = input[3]
    list_negative = list(range(len(input[0])))

    # locate the positive samples for each question
    for i in range(input[3]):

      # local the positive samples
      for j in range(len(input[0])):
        if input[1][i][0] in range(input[0][j][1],input[0][j][2]):
          if input[1][i][1] in range(input[0][j][1],input[0][j][2]):
            result.append([input[0][j][0],input[2],input[1][i][0]-input[0][j][1],input[1][i][1]-input[0][j][1]])
            list_negative[j] = -1

          else:
            result.append([input[0][j][0],input[2],input[1][i][0]-input[0][j][1],4096])
            list_negative[j] = -1

        else:
          if input[1][i][1] in range(input[0][j][1],input[0][j][2]):
            result.append([input[0][j][0],input[2],0,input[1][i][1]-input[0][j][1]])
            list_negative[j] = -1
          else:
            pass

    # locate the possible_nagetive samples for each question

    # locate the Possible_negative segments
    for i in range(len(list_negative)):
      try:
        list_negative.remove(-1)
      except:
        pass

    # locate the possible_nagetive samples
    if len(list_negative) > 0:
      if negative <= ((len(list_negative)-1)/3+1):
        for i in range(negative):
          index = random.choice(list_negative)
          result.append([input[0][index][0],input[2],0,0])

          if (index + 1) not in list_negative:
            if (index - 1) not in list_negative:
              list_negative.remove(index)
            else:
              list_negative.remove(index)
              list_negative.remove(index -1)
          else:
            if (index - 1) not in list_negative:
              list_negative.remove(index)
              list_negative.remove(index +1)
            else:
              list_negative.remove(index)
              list_negative.remove(index -1)
              list_negative.remove(index +1)

      elif negative >= len(list_negative):
        for i in range(len(list_negative)):
          result.append([input[0][i][0],input[2],0,0])

      else:
        for i in range(negative):
          index = random.choice(list_negative)
          list_negative.remove(index)
          result.append([input[0][index][0],input[2],0,0])
    else:
      pass
  # result.append(negative) 

  return result

test_sample_rdd = test_segment_answer_rdd.flatMap(select_samples).cache()


test_sample_rdd.collect()

from pyspark.sql.types import StructField,StringType,IntegerType,StructType,LongType
# transform the data into dataframe

# set the structure of the df
result_schema = StructType([
  StructField("source",StringType(),True),
  StructField("question",StringType(),True),
  StructField("answer_start",IntegerType(),True),
  StructField("answer_end",IntegerType(),True),
  ])


result_df = spark.createDataFrame(test_sample_rdd,schema=result_schema).cache()

result_df.printSchema()

print(result_df.take(5))

result_df.coalesce(1).write.json('data/')
