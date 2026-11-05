# PySpark silver lab

Run this on the Onyxia `vscode-pyspark` service from the repository root. The service needs the S3 environment variables and the bronze CSV files from the S3 lab.

```bash
aws s3 --endpoint-url "https://$AWS_S3_ENDPOINT" ls "s3://$KUBERNETES_NAMESPACE/bronze/"
pyspark --version
ls "$SPARK_HOME/jars" | grep -i hadoop-aws
spark-submit --master 'local[2]' --driver-memory 512m \
  --packages org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0 \
  spark_silver/lab_silver.py
```

The script uses an Iceberg package for Spark 4.1 and Scala 2.13. If the service uses other versions, change `iceberg_package` in the script and the `--packages` value in the command. If `hadoop-aws` is missing, add its matching package before running the script.

This service has a 2 GiB memory limit, so the script uses two local threads and a 512 MiB driver. The S3A magic committer failed during the Parquet write; the script uses the file committer for this single-writer lab.
