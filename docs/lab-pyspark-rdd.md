# PySpark RDD lab

## RDD creation and partitions

### 1. What decides the default number of partitions?

`textFile()` uses input file splits and Spark's minimum partition setting. Onyxia used two partitions for each small CSV file. `repartition(8)` produced eight partitions for orders.

### 2. Which operation shuffles data?

`repartition()` shuffles data to make new partitions. `coalesce()` can reduce the partition count without a shuffle by default.

## Lazy evaluation and lineage

### 1. Does a second `count()` run a new stage?

Yes. `orders_data` is not cached, so each `count()` runs the filter and reads the CSV again. Both counts returned 2,829 with `bronze/orders.csv` from S3.

### 2. Where would `.cache()` change this?

I would call `orders_data.cache()` before the first `count()`. The first count would fill the cache. The second count would still start a new job, but it could read the cached data instead of reading and filtering the CSV again.

## The cost of no schema: the multiline address

### 1. Why does `spark.read.csv(multiLine=True)` work here?

The CSV reader keeps reading a quoted field across line breaks. `textFile()` stops at each line break, so it split 50 users into 101 lines, including the header. Filtering lines that start with a UUID leaves 50 records, but their addresses are still incomplete.

### 2. When is `textFile()` safe for records?

Each complete record must fit on one physical line. A line break inside a field breaks that assumption.

## Manual parsing of orders

### 1. What happens if `product` contains a comma?

`split(",")` returns six parts instead of five. The unpacking fails when an action runs the parser.

### 2. Where does the DataFrame API check the fields?

The CSV reader parses quoted fields when it reads the file, including commas inside `product`. In the DataFrame lab, `inferSchema=True` scans the file while creating the DataFrame, but it does not guarantee that malformed rows are rejected.

## Key-value RDDs: total quantity per user

### 1. What does `groupByKey()` shuffle?

It sends each quantity to the partition for its user. `reduceByKey(add)` sends partial sums instead. In my Spark UI run, `reduceByKey` wrote 2.5 KiB and the next stage read 2.5 KiB; `groupByKey` wrote 6.1 KiB and the next stage read 6.1 KiB.

### 2. When would `groupByKey()` be needed?

An exact median needs each user's individual quantities, so `reduceByKey(add)` cannot calculate it. `groupByKey()` gathers them, but a reducer that keeps the values would also work.

## Manual deduplication

### 1. What plays the role of the window partition?

`reduceByKey(most_recent)` groups orders with the same `order_id` and shuffles them by key before keeping one order.

### 2. Which version states the intent more directly?

The DataFrame window is clearer to me: it shows the grouping key and descending date together. With the RDD, I have to read `most_recent` to see which order wins.

## Joining orders with users

### 1. When can Spark skip the join shuffle?

Both RDDs must already be partitioned the same way by `user_id`, with the same partitioner and number of partitions. Then matching keys are already together.

### 2. What changes with `leftOuterJoin()`?

It keeps every order. If a user is missing, the username in `(order, username)` is `None` instead of dropping that order.

### 3. What is the risk of calling `.collect()` here?

It sends every joined record to the driver. On a large dataset, the driver could run out of memory.

## Exercises

### 1. Average order quantity per user

`aggregateByKey` calculates `(order_count, total_quantity)` together for each user. The average is `total_quantity / order_count`.

### 2. Order with no matching user

I added one order with `user_id` set to `missing-user`. The `leftOuterJoin()` kept it, and filtering rows whose username is `None` returned one order.

### 3. RDD and DataFrame aggregation

In my script, the RDD aggregation spans three lines and the DataFrame aggregation uses one line. The DataFrame states the grouping and sum directly; its `explain()` shows an `Exchange` and aggregation, while `toDebugString()` shows the RDD lineage. Both gave the same totals.

### 4. Count with and without cache

On one Onyxia run with the bronze CSV files from S3, `orders_rdd.count()` took 0.107 s with cache and 0.157 s on a new RDD without `.cache()`. The quantity totals took 0.201 s and 0.435 s. In a separate check, the Storage tab showed one cached RDD before `unpersist()` and none afterward.
