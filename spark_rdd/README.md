# PySpark RDD lab

Run from the repository root:

```bash
export LAB_BUCKET_NAME="$KUBERNETES_NAMESPACE"
aws s3 --profile default cp "s3://$LAB_BUCKET_NAME/bronze/users.csv" users.csv
aws s3 --profile default cp "s3://$LAB_BUCKET_NAME/bronze/orders.csv" orders.csv
spark-submit --master 'local[*]' spark_rdd/lab_rdd.py
```

The CSV files stay local and are ignored by Git.
