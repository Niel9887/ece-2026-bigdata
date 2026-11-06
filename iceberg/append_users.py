import os

from pyspark.sql import SparkSession, functions as F


bucket = os.environ["KUBERNETES_NAMESPACE"]

spark = (
    SparkSession.builder
    .appName("lab-iceberg-users")
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
users = spark.table(table)
rows_before = users.count()
snapshots_before = spark.sql(f"SELECT count(*) FROM {table}.snapshots").first()[0]
previous_snapshot = spark.sql(f"""
    SELECT snapshot_id FROM {table}.snapshots
    ORDER BY committed_at DESC LIMIT 1
""").first()[0]

new_users = users.limit(3).withColumn("user_id", F.expr("uuid()"))
assert new_users.count() == 3
new_users.writeTo(table).append()

rows_after = spark.table(table).count()
snapshots_after = spark.sql(f"SELECT count(*) FROM {table}.snapshots").first()[0]
old_rows = spark.sql(
    f"SELECT count(*) FROM {table} VERSION AS OF {previous_snapshot}"
).first()[0]

assert rows_after == rows_before + 3
assert snapshots_after == snapshots_before + 1
assert old_rows == rows_before

print("Users before:", rows_before)
print("Users after:", rows_after)
print("Users in previous snapshot:", old_rows)
print("User snapshots before and after:", snapshots_before, snapshots_after)
spark.stop()
