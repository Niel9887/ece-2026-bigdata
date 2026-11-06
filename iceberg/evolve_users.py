import os
from uuid import uuid4

from pyspark.sql import SparkSession, functions as F


bucket = os.environ["KUBERNETES_NAMESPACE"]

spark = (
    SparkSession.builder
    .appName("lab-iceberg-users-country")
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

table = "lab.silver.users"
rows_before = spark.table(table).count()
files_before = {
    row.file_path for row in spark.sql(f"SELECT file_path FROM {table}.files").collect()
}
assert "country" not in spark.table(table).columns

spark.sql(f"ALTER TABLE {table} ADD COLUMN country STRING")
assert "country" in spark.table(table).columns

new_id = str(uuid4())
new_user = (
    spark.table(table).limit(1)
    .withColumn("user_id", F.lit(new_id))
    .withColumn("username", F.lit(f"lab8_{new_id}"))
    .withColumn("email", F.lit(f"lab8_{new_id}@example.com"))
    .withColumn("country", F.lit("US"))
)
new_user.writeTo(table).append()

rows_after = spark.table(table).count()
files_after = {
    row.file_path for row in spark.sql(f"SELECT file_path FROM {table}.files").collect()
}
assert rows_after == rows_before + 1
assert files_before.issubset(files_after)
assert spark.table(table).filter(F.col("country") == "US").count() == 1

print("Users before country:", rows_before)
print("Users after country:", rows_after)
print("Old user files still current:", files_before.issubset(files_after))
print("Country column:", "country" in spark.table(table).columns)
spark.stop()
