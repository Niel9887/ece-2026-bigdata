import os

from pyspark.sql import SparkSession, functions as F


bucket = os.environ["KUBERNETES_NAMESPACE"]

spark = (
    SparkSession.builder
    .appName("lab-iceberg-append")
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

table = "lab.silver.orders"
orders = spark.table(table)
rows_before = orders.count()
snapshots_before = spark.sql(f"SELECT count(*) FROM {table}.snapshots").first()[0]
previous_snapshot = spark.sql(f"""
    SELECT snapshot_id FROM {table}.snapshots
    ORDER BY committed_at DESC LIMIT 1
""").first()[0]
files_before = {
    row.file_path for row in spark.sql(f"SELECT file_path FROM {table}.files").collect()
}

new_orders = orders.limit(3).withColumn("order_id", F.expr("uuid()"))
assert new_orders.count() == 3
new_orders.writeTo(table).append()

rows_after = spark.table(table).count()
old_rows = spark.sql(
    f"SELECT count(*) FROM {table} VERSION AS OF {previous_snapshot}"
).first()[0]
snapshots_after = spark.sql(f"SELECT count(*) FROM {table}.snapshots").first()[0]
files_after = {
    row.file_path for row in spark.sql(f"SELECT file_path FROM {table}.files").collect()
}

assert rows_after == rows_before + 3
assert old_rows == rows_before
assert snapshots_after == snapshots_before + 1
assert files_before.issubset(files_after)

print("Rows before:", rows_before)
print("Rows after:", rows_after)
print("Rows in previous snapshot:", old_rows)
print("Snapshots before and after:", snapshots_before, snapshots_after)
print("Current data files before and after:", len(files_before), len(files_after))
spark.sql(f"""
    SELECT snapshot_id, operation, committed_at
    FROM {table}.snapshots
    ORDER BY committed_at
""").show(truncate=False)

spark.stop()
