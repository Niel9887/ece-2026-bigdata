# PySpark RDD lab

Run from the repository root:

```bash
export LAB_BUCKET_NAME="$KUBERNETES_NAMESPACE"
aws s3 cp "s3://$LAB_BUCKET_NAME/bronze/users.csv" users.csv
aws s3 cp "s3://$LAB_BUCKET_NAME/bronze/orders.csv" orders.csv
spark-submit --master 'local[*]' spark_rdd/lab_rdd.py
rm -f users.csv orders.csv
```

The CSV files are local copies and are ignored by Git.
