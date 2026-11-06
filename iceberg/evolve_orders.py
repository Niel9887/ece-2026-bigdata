import os

from pyspark.sql import SparkSession, functions as F


bucket = os.environ["KUBERNETES_NAMESPACE"]

spark = (
    SparkSession.builder
    .appName("lab-iceberg-schema")
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
rows_before = spark.table(table).count()
files_before = {
    row.file_path for row in spark.sql(f"SELECT file_path FROM {table}.files").collect()
}
assert "source" not in spark.table(table).columns

spark.sql(f"ALTER TABLE {table} ADD COLUMN source STRING")
assert "source" in spark.table(table).columns

new_order = (
    spark.table(table).limit(1)
    .withColumn("order_id", F.expr("uuid()"))
    .withColumn("source", F.lit("spark"))
)
new_order.writeTo(table).append()

rows_after = spark.table(table).count()
files_after = {
    row.file_path for row in spark.sql(f"SELECT file_path FROM {table}.files").collect()
}
assert rows_after == rows_before + 1
assert files_before.issubset(files_after)
assert spark.table(table).filter(F.col("source") == "spark").count() == 1

print("Rows before:", rows_before)
print("Rows after:", rows_after)
print("Old files still current:", files_before.issubset(files_after))
print("Columns:", ", ".join(spark.table(table).columns))
spark.stop()
