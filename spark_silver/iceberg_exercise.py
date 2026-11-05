import os
from datetime import datetime, timezone
from uuid import uuid4

from pyspark.sql import SparkSession


bucket = os.environ["KUBERNETES_NAMESPACE"]
iceberg_package = "org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0"
spark = (
    SparkSession.builder
    .appName("lab-silver-time-travel")
    .master("local[2]")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.hadoop.fs.s3a.committer.name", "file")
    .config("spark.hadoop.fs.s3a.endpoint", f"https://{os.environ['AWS_S3_ENDPOINT']}")
    .config("spark.hadoop.fs.s3a.access.key", os.environ["AWS_ACCESS_KEY_ID"])
    .config("spark.hadoop.fs.s3a.secret.key", os.environ["AWS_SECRET_ACCESS_KEY"])
    .config("spark.hadoop.fs.s3a.session.token", os.environ["AWS_SESSION_TOKEN"])
    .config(
        "spark.hadoop.fs.s3a.aws.credentials.provider",
        "org.apache.hadoop.fs.s3a.TemporaryAWSCredentialsProvider",
    )
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.jars.packages", iceberg_package)
    .config(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    )
    .config("spark.sql.catalog.lab", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.lab.type", "hadoop")
    .config("spark.sql.catalog.lab.warehouse", f"s3a://{bucket}/warehouse")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

orders = spark.table("lab.silver.orders")
previous_count = orders.count()
previous_snapshot = spark.sql("""
    SELECT snapshot_id FROM lab.silver.orders.snapshots
    ORDER BY committed_at DESC LIMIT 1
""").first()[0]
user_id = spark.table("lab.silver.users").select("user_id").first()[0]
new_order = spark.createDataFrame(
    [(str(uuid4()), user_id, datetime.now(timezone.utc).replace(tzinfo=None), 1, "bread")],
    schema=orders.schema,
)
new_order.writeTo("lab.silver.orders").append()

current_count = spark.table("lab.silver.orders").count()
old_count = spark.sql(
    f"SELECT count(*) FROM lab.silver.orders VERSION AS OF {previous_snapshot}"
).first()[0]
print("Iceberg current and previous rows:", current_count, old_count)
assert current_count == previous_count + 1
assert old_count == previous_count
spark.sql("""
    SELECT snapshot_id, operation, committed_at FROM lab.silver.orders.snapshots
    ORDER BY committed_at
""").show(truncate=False)

parquet_copy = f"s3a://{bucket}/silver/spark/orders_exercise.parquet"
base_orders = spark.read.parquet(f"s3a://{bucket}/silver/spark/orders.parquet")
base_orders.write.mode("overwrite").parquet(parquet_copy)
print("Parquet before append:", spark.read.parquet(parquet_copy).count())
new_order.write.mode("append").parquet(parquet_copy)
print("Parquet after append:", spark.read.parquet(parquet_copy).count())

spark.stop()
