spark-submit \
    --master yarn \
    --deploy-mode client \
    MovieData_Summary.py \
    --output $1
