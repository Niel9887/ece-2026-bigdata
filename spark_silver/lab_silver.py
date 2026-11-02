import os

from pyspark.sql import SparkSession


bucket = os.environ["KUBERNETES_NAMESPACE"]
iceberg_package = "org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0"

spark = (
    SparkSession.builder
    .appName("lab-silver-pyspark")
    .master("local[*]")
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

spark.stop()
