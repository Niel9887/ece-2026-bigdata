import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


bucket = os.environ["KUBERNETES_NAMESPACE"]
iceberg_package = "org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0"

spark = (
    SparkSession.builder
    .appName("lab-silver-pyspark")
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

users_bronze = spark.read.csv(
    f"s3a://{bucket}/bronze/users.csv",
    header=True,
    inferSchema=True,
    samplingRatio=0.01,
    multiLine=True,
)
orders_bronze = spark.read.csv(
    f"s3a://{bucket}/bronze/orders.csv",
    header=True,
    inferSchema=True,
    samplingRatio=0.01,
    multiLine=True,
)

users_bronze.printSchema()
users_bronze.show(3, truncate=False)
users_bronze.select("address").show(3, truncate=False)
orders_bronze.printSchema()
print("Users:", users_bronze.count())
print("Orders:", orders_bronze.count())

users_typed = (
    users_bronze
    .select(
        F.col("uuid").cast("string").alias("user_id"),
        F.trim("username").alias("username"),
        F.trim("name").alias("name"),
        F.upper(F.trim("sex")).alias("sex"),
        F.lower(F.trim("mail")).alias("email"),
        F.col("birthdate").cast("date").alias("birthdate"),
        F.split("address", "\n").alias("address_lines"),
    )
    .withColumn("street", F.element_at("address_lines", 1))
    .withColumn("address_line_2", F.element_at("address_lines", 2))
    .drop("address_lines")
)

stg_users = users_typed.select(
    "user_id", "username", "name", "sex", "email", "birthdate", "street",
    F.regexp_extract("address_line_2", "^(.+), [A-Z]{2} [0-9]{5}$", 1).alias("city"),
    F.regexp_extract("address_line_2", "([A-Z]{2}) ([0-9]{5})$", 1).alias("state"),
    F.regexp_extract("address_line_2", "([A-Z]{2}) ([0-9]{5})$", 2).alias("zip_code"),
)
stg_users = stg_users.withColumn(
    "city", F.when(F.col("city") == "", None).otherwise(F.col("city"))
)  # Military addresses have no city, so I keep that as null.

orders_typed = orders_bronze.select(
    F.col("uuid").cast("string").alias("order_id"),
    F.col("user_uuid").cast("string").alias("user_id"),
    F.col("date").cast("timestamp").alias("ordered_at"),
    F.col("quantity").cast("int").alias("quantity"),
    F.lower(F.trim("product")).alias("product"),
)
orders_with_duplicates = orders_typed.unionByName(orders_typed.limit(3))
dedup_window = Window.partitionBy("order_id").orderBy(F.col("ordered_at").desc())
stg_orders = (
    orders_with_duplicates
    .withColumn("row_number", F.row_number().over(dedup_window))
    .filter(F.col("row_number") == 1)
    .drop("row_number")
)

print("Orders with duplicates:", orders_with_duplicates.count())
print("Orders after deduplication:", stg_orders.count())
print("Users without a city:", stg_users.filter(F.col("city").isNull()).count())
print(
    "Duplicate order IDs left:",
    stg_orders.groupBy("order_id").count().filter(F.col("count") > 1).count(),
)

orders_with_duplicates.createOrReplaceTempView("orders_with_duplicates")
stg_orders_sql = spark.sql("""
    SELECT order_id, user_id, ordered_at, quantity, product
    FROM (
        SELECT *, row_number() OVER (
            PARTITION BY order_id ORDER BY ordered_at DESC
        ) AS rn
        FROM orders_with_duplicates
    )
    WHERE rn = 1
""")

assert stg_orders_sql.count() == stg_orders.count()
assert set(stg_orders_sql.columns) == set(stg_orders.columns)
print("SQL orders after deduplication:", stg_orders_sql.count())

first_orders = stg_orders.groupBy("user_id").agg(
    F.min("ordered_at").alias("first_order")
)
stg_users = (
    stg_users.join(first_orders, "user_id", "left")
    .withColumn(
        "birthdate_is_valid",
        F.col("first_order").isNull()
        | (F.col("birthdate") <= F.to_date("first_order")),
    )
    .withColumn(
        "birthdate",
        F.when(F.col("birthdate_is_valid"), F.col("birthdate")),
    )
    .drop("first_order")
)
print("Invalid birthdates:", stg_users.filter(~F.col("birthdate_is_valid")).count())

stg_users.createOrReplaceTempView("stg_users")
spark.sql("""
    SELECT state, count(*) AS users,
           sum(CASE WHEN city IS NULL THEN 1 ELSE 0 END) AS missing_city
    FROM stg_users
    GROUP BY state
    ORDER BY users DESC
""").show(10)

users_parquet = f"s3a://{bucket}/silver/spark/users.parquet"
orders_parquet = f"s3a://{bucket}/silver/spark/orders.parquet"
stg_users.write.mode("overwrite").parquet(users_parquet)
stg_orders.write.mode("overwrite").parquet(orders_parquet)

users_silver = spark.read.parquet(users_parquet)
orders_silver = spark.read.parquet(orders_parquet)
assert users_silver.count() == users_bronze.count()
assert orders_silver.count() == stg_orders.count()
print("Parquet users:", users_silver.count())
print("Parquet orders:", orders_silver.count())

spark.sql("CREATE NAMESPACE IF NOT EXISTS lab.silver")
stg_users.writeTo("lab.silver.users").createOrReplace()
stg_orders.writeTo("lab.silver.orders").createOrReplace()

spark.sql("""
    SELECT snapshot_id, operation, committed_at
    FROM lab.silver.orders.snapshots
""").show(truncate=False)
spark.sql("""
    SELECT file_path, file_format, record_count, file_size_in_bytes
    FROM lab.silver.orders.files
""").show(truncate=False)

users_iceberg = spark.table("lab.silver.users")
orders_iceberg = spark.table("lab.silver.orders")
assert users_iceberg.count() == users_bronze.count()
assert orders_iceberg.count() == stg_orders.count()
print("Iceberg users:", users_iceberg.count())
print("Iceberg orders:", orders_iceberg.count())

spark.stop()
