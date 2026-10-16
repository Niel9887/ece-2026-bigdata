import re
from operator import add
from time import perf_counter

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


def parse_user_for_join(line):
    fields = line.split(",")
    return fields[0], fields[1]


users_kv = users_records.map(parse_user_for_join)
orders_kv = orders_rdd.map(lambda order: (order["user_id"], order))

enriched = orders_kv.join(users_kv)
print("Joined orders:", enriched.count())
print("Joined sample:", enriched.take(3))

enriched_left = orders_kv.leftOuterJoin(users_kv)
print("Left join orders:", enriched_left.count())

order_stats = orders_rdd.map(
    lambda order: (order["user_id"], order["quantity"])
).aggregateByKey(
    (0, 0),
    lambda stats, quantity: (stats[0] + 1, stats[1] + quantity),
    lambda left, right: (left[0] + right[0], left[1] + right[1]),
)
average_quantity = order_stats.mapValues(lambda stats: stats[1] / stats[0])
print("Order stats sample:", order_stats.take(3))
print("Average quantity sample:", average_quantity.take(3))

fake_order = dict(orders_rdd.first())
fake_order["order_id"] = "test-missing-user"
fake_order["user_id"] = "missing-user"
orders_with_missing = orders_rdd.union(sc.parallelize([fake_order]))
orders_with_missing_kv = orders_with_missing.map(
    lambda order: (order["user_id"], order)
)
missing_user_orders = orders_with_missing_kv.leftOuterJoin(users_kv).filter(
    lambda pair: pair[1][1] is None
)
print("Orders with missing user:", missing_user_orders.count())

orders_df = spark.createDataFrame(orders_rdd)
df_totals = orders_df.groupBy("user_id").sum("quantity")
df_totals_map = {row["user_id"]: row["sum(quantity)"] for row in df_totals.collect()}
print("DataFrame totals match:", df_totals_map == reduce_totals)
print("DataFrame plan:")
df_totals.explain()
print("RDD lineage:")
print(user_quantity.toDebugString().decode())


def timed_count(label, rdd):
    start = perf_counter()
    count = rdd.count()
    print(f"{label}: {count} rows in {perf_counter() - start:.3f} s")


timed_count("Parsed orders cached", orders_rdd)
timed_count("Totals with cache", user_quantity)
orders_rdd.unpersist(blocking=True)
orders_uncached = orders_data.map(parse_order)
user_quantity_uncached = orders_uncached.map(
    lambda order: (order["user_id"], order["quantity"])
).reduceByKey(add)
timed_count("Parsed orders uncached", orders_uncached)
timed_count("Totals without cache", user_quantity_uncached)

spark.stop()
