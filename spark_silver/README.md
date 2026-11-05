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

Run the first two exercises after the silver files have been written:

```bash
spark-submit --master 'local[2]' --driver-memory 512m spark_silver/exercises.py
```

Open `spark_silver/zip_timeit.ipynb` on Onyxia to time the three zip code expressions with `%%timeit`. It uses the full bronze users DataFrame and runs each action three times.

For the cache exercise, keep the session open while checking the Spark UI Storage tab:

```bash
spark-submit --master 'local[2]' --driver-memory 512m spark_silver/cache_exercise.py --inspect-ui
```

For the snapshot exercise, run this once after creating the Iceberg tables:

```bash
spark-submit --master 'local[2]' --driver-memory 512m \
  --packages org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0 \
  spark_silver/iceberg_exercise.py
```

The lab recommends 4000 Mi of memory. My Onyxia service had a 2 GiB limit, so these commands use two local threads and a 512 MiB driver. The S3A magic committer failed during the Parquet write; the script uses the file committer for this single-writer lab.
