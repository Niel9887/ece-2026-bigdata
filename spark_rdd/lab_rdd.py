import re
from operator import add

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

print("First user lines:")
for line in users_lines.take(6):
    print(line)
print("Physical user lines:", users_lines.count())

UUID_AT_START = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
users_records = users_lines.filter(
    lambda line: UUID_AT_START.match(line) is not None
)
print("User records:", users_records.count())


def parse_order(line):
    order_id, user_id, date, quantity, product = line.split(",")
    return {
        "order_id": order_id,
        "user_id": user_id,
        "date": date,
        "quantity": int(quantity),
        "product": product.strip().lower(),
    }


orders_rdd = orders_data.map(parse_order).cache()
print("Parsed orders:", orders_rdd.count())
print("First parsed orders:", orders_rdd.take(3))

user_quantity = orders_rdd.map(
    lambda order: (order["user_id"], order["quantity"])
).reduceByKey(add)
user_quantity_grouped = (
    orders_rdd.map(lambda order: (order["user_id"], order["quantity"]))
    .groupByKey()
    .mapValues(sum)
)
print("reduceByKey:", user_quantity.take(5))
print("groupByKey:", user_quantity_grouped.take(5))
reduce_totals = user_quantity.collectAsMap()
grouped_totals = user_quantity_grouped.collectAsMap()
print("Users with orders:", len(reduce_totals))
print("Same quantity per user:", reduce_totals == grouped_totals)


def most_recent(order_a, order_b):
    return order_a if order_a["date"] > order_b["date"] else order_b


orders_dedup = (
    orders_rdd.map(lambda order: (order["order_id"], order))
    .reduceByKey(most_recent)
    .values()
)
print("Orders before dedup:", orders_rdd.count())
print("Orders after dedup:", orders_dedup.count())

spark.stop()
