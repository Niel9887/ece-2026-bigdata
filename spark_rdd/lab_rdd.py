from pyspark.sql import SparkSession


spark = SparkSession.builder.appName("lab-rdd").master("local[*]").getOrCreate()
sc = spark.sparkContext
sc.setLogLevel("ERROR")

users_lines = sc.textFile("users.csv")
orders_lines = sc.textFile("orders.csv")

print("Users partitions:", users_lines.getNumPartitions())
print("Orders partitions:", orders_lines.getNumPartitions())

orders_repartitioned = orders_lines.repartition(8)
print("Orders after repartition:", orders_repartitioned.getNumPartitions())

header = orders_lines.first()
orders_data = orders_lines.filter(
    lambda line: line != header and line.strip() != ""
)  # Spark waits for an action before running this filter.
print(orders_data.toDebugString().decode())
print("First count:", orders_data.count())
print("Second count:", orders_data.count())

spark.stop()
