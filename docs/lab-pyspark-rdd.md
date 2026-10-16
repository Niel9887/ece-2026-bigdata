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
