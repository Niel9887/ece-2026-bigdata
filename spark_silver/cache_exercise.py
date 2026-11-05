import os
import sys

from pyspark.sql import SparkSession, functions as F


bucket = os.environ["KUBERNETES_NAMESPACE"]
spark = (
    SparkSession.builder
    .appName("lab-silver-cache")
    .master("local[2]")
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

users = spark.read.csv(
    f"s3a://{bucket}/bronze/users.csv",
    header=True, inferSchema=True, samplingRatio=0.01, multiLine=True,
)
orders = spark.read.csv(
    f"s3a://{bucket}/bronze/orders.csv",
    header=True, inferSchema=True, samplingRatio=0.01,
)
print("Bronze rows:", users.count(), orders.count())
users.cache()
orders.cache()
print("Cached rows:", users.count(), orders.count())
print("Users cache:", users.storageLevel)
print("Orders cache:", orders.storageLevel)

users.groupBy("sex").count().show()
orders.groupBy("product").agg(F.sum("quantity").alias("quantity")).show()

if "--inspect-ui" in sys.argv:
    input("Check the Spark UI Storage tab, then press Enter to stop Spark: ")

spark.stop()
