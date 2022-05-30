spark-submit \
    --master yarn \
    --deploy-mode client \
    --num-executors 4\
    comp5349_assignment2_zwan9209.py \
    --output $1
