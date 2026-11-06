import os

from pyspark.sql import SparkSession


bucket = os.environ["KUBERNETES_NAMESPACE"]

spark = (
    SparkSession.builder
    .appName("lab-iceberg-inspect")
    .master("local[2]")
    .config("spark.sql.shuffle.partitions", "4")
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

spark.sql("SHOW NAMESPACES IN lab").show()

for table in ("orders", "users"):
    name = f"lab.silver.{table}"
    print(name, "rows:", spark.table(name).count())
    spark.sql(f"""
        SELECT snapshot_id, operation, committed_at
        FROM {name}.snapshots
        ORDER BY committed_at
    """).show(truncate=False)
    spark.sql(f"""
        SELECT file_path, file_format, record_count, file_size_in_bytes
        FROM {name}.files
    """).show(truncate=False)

first_snapshot = spark.sql("""
    SELECT snapshot_id FROM lab.silver.orders.snapshots
    ORDER BY committed_at LIMIT 1
""").first()[0]
first_rows = spark.sql(f"""
    SELECT count(*) FROM lab.silver.orders VERSION AS OF {first_snapshot}
""").first()[0]
print("Orders in first snapshot:", first_rows)
print("Orders now:", spark.table("lab.silver.orders").count())

spark.stop()
