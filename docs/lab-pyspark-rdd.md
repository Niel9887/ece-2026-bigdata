# PySpark RDD lab

## RDD creation and partitions

### 1. What decides the default number of partitions?

`textFile()` uses input file splits and Spark's minimum partition setting. Onyxia used two partitions for each small CSV file. `repartition(8)` produced eight partitions for orders.

### 2. Which operation shuffles data?

`repartition()` shuffles data to make new partitions. `coalesce()` can reduce the partition count without a shuffle by default.

## Lazy evaluation and lineage

### 1. Does a second `count()` run a new stage?

Yes. `orders_data` is not cached, so each `count()` runs the filter and reads the CSV again. Both counts returned 2,829 on the locally generated dataset.

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

An exact median needs each user's individual quantities, so `reduceByKey(add)` cannot calculate it. `groupByKey()` keeps the quantities together, but it is not strictly unavoidable: a different reducer could also keep them.

## Manual deduplication

### 1. What plays the role of the window partition?

`reduceByKey(most_recent)` groups orders with the same `order_id` and shuffles them by key before keeping one order.

### 2. Which version states the intent more directly?

The DataFrame window is clearer to me: it shows the grouping key and descending date together. With the RDD, I have to read `most_recent` to see which order wins.
