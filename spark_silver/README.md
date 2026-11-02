# PySpark silver lab

Run this on the Onyxia `vscode-pyspark` service from the repository root. The service needs the S3 environment variables and the bronze CSV files from the S3 lab.

```bash
aws s3 --endpoint-url "https://$AWS_S3_ENDPOINT" ls "s3://$KUBERNETES_NAMESPACE/bronze/"
pyspark --version
ls "$SPARK_HOME/jars" | grep -i hadoop-aws
spark-submit --master 'local[*]' spark_silver/lab_silver.py
```

The script uses an Iceberg package for Spark 4.1 and Scala 2.13. If the service uses other versions, change `iceberg_package` in the script. If `hadoop-aws` is missing, add its matching package to `spark.jars.packages` before running it.
