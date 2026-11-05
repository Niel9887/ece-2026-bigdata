import os
import re
import time

import pandas as pd
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StringType


bucket = os.environ["KUBERNETES_NAMESPACE"]
spark = (
    SparkSession.builder
    .appName("lab-silver-exercises")
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
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

orders = spark.read.parquet(f"s3a://{bucket}/silver/spark/orders.parquet")
users_bronze = spark.read.csv(
    f"s3a://{bucket}/bronze/users.csv",
    header=True,
    inferSchema=True,
    samplingRatio=0.01,
    multiLine=True,
)
users = users_bronze.select(
    F.col("uuid").alias("user_id"), F.col("birthdate")
)
first_orders = orders.groupBy("user_id").agg(F.min("ordered_at").alias("first_order"))

users_df = (
    users.join(first_orders, "user_id", "left")
    .withColumn(
        "birthdate_is_valid",
        F.col("first_order").isNull()
        | (F.col("birthdate") <= F.to_date("first_order")),
    )
    .drop("first_order")
)

users.createOrReplaceTempView("users")
orders.createOrReplaceTempView("orders")
users_sql = spark.sql("""
    WITH first_orders AS (
        SELECT user_id, min(ordered_at) AS first_order
        FROM orders GROUP BY user_id
    )
    SELECT users.*,
           first_order IS NULL OR birthdate <= to_date(first_order)
               AS birthdate_is_valid
    FROM users LEFT JOIN first_orders USING (user_id)
""")

flags_df = users_df.select("user_id", "birthdate_is_valid")
flags_sql = users_sql.select("user_id", "birthdate_is_valid")
assert flags_df.exceptAll(flags_sql).count() == 0
assert flags_sql.exceptAll(flags_df).count() == 0
invalid_count = users_df.filter(~F.col("birthdate_is_valid")).count()
silver_users = spark.read.parquet(f"s3a://{bucket}/silver/spark/users.parquet")
silver_flags = silver_users.select("user_id", "birthdate_is_valid")
assert flags_df.exceptAll(silver_flags).count() == 0
assert silver_flags.exceptAll(flags_df).count() == 0
assert silver_users.filter(
    ~F.col("birthdate_is_valid") & F.col("birthdate").isNotNull()
).count() == 0
print("Invalid birthdates:", invalid_count)
print("DataFrame and SQL flags agree")


@F.udf(StringType())
def zip_python(address):
    match = re.search(r"([A-Z]{2}) ([0-9]{5})$", address or "")
    return match.group(2) if match else ""


@F.pandas_udf(StringType())
def zip_pandas(address: pd.Series) -> pd.Series:
    return address.str.extract(r"([A-Z]{2}) ([0-9]{5})$")[1].fillna("")


versions = {
    "regex": F.regexp_extract("address", r"([A-Z]{2}) ([0-9]{5})$", 2),
    "python_udf": zip_python("address"),
    "pandas_udf": zip_pandas("address"),
}
for name, expression in versions.items():
    times = []
    for _ in range(3):
        started = time.perf_counter()
        result = users_bronze.select(expression.alias("zip_code"))
        count = result.filter(F.col("zip_code") != "").count()
        times.append(round(time.perf_counter() - started, 3))
    print(name, "matched:", count, "seconds:", times)

spark.stop()
