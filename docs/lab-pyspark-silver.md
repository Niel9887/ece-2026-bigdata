# PySpark silver lab

## SparkSession with S3 access

### What happens if the service is restarted during a Spark job?

The job stops because the driver and executors run inside the Onyxia service. After a restart, I need a new Spark session and valid temporary S3 credentials before reading the files again.

### Why does `SimpleAWSCredentialsProvider` fail here?

It sends the access key and secret key without the session token. Onyxia's temporary credentials need all three values, so the S3 request fails.

## Bronze layer

The S3 read returned 50 users and 2,829 orders. Spark inferred `birthdate` as a date and the order `date` as a timestamp.

## Silver layer with DataFrames

Adding three repeated orders raised the count from 2,829 to 2,832. The window kept one row per `order_id`, so the result returned to 2,829 orders with no duplicate IDs. Six users have no city after parsing their addresses.

## Spark SQL

### What does the state query show?

It counts users and missing cities for each state. In the ten states shown, all three AE users and both AP users have no city; the other displayed states have none. The SQL deduplication also returned 2,829 orders, like the DataFrame version.

### Which approach would you use?

For a one-off check in PySpark, I would use the DataFrame API to inspect each step. For a model shared with colleagues who know SQL, I would use Spark SQL so they can read and change the query directly.

### Where could an empty string cause another wrong result?

The `state` or `zip_code` extraction could also return an empty string when the address does not match. Grouping by state would then count an empty state as if it were a real value.

## Parquet files

### Which objects were written?

`silver/spark/users.parquet/` contains one `part-...parquet` file and `_SUCCESS`. `silver/spark/orders.parquet/` has the same layout. Spark wrote one data file per output partition here; `_SUCCESS` marks the completed job. Reading them back gave 50 users and 2,829 orders.

### What would `coalesce(1)` cost on a larger dataset?

It would force the output through one partition, so the write could no longer use several workers in parallel.

## Iceberg tables

### Which files contain data and metadata?

Both outputs store their rows in Parquet files. Iceberg also has a `metadata/` directory with JSON and Avro files for the schema, manifests and snapshot. The `orders` snapshot reports one Parquet data file with 2,829 records; reading the tables returned 50 users and 2,829 orders.

### What happens during an overwrite?

A reader of a Parquet directory may see files being removed and replaced while the write runs. An Iceberg reader stays on a committed snapshot and sees the new version after the commit.

### What if two jobs commit at the same time?

With this Hadoop catalog, both jobs can try to update the current table version in S3 and one change can be lost. A catalog service coordinates that update.

## Comparing dbt and Spark

DuckDB counted 2,829 orders and a quantity total of 8,615 in both outputs. It counted 50 users in each output. In my bucket the dbt files are `silver/dbt/orders.parquet` and `silver/dbt/users.parquet`.

### What differs between the schemas?

DuckDB reads the dbt IDs as `UUID` and `ordered_at` as `TIMESTAMP WITH TIME ZONE`. In the Spark output they are strings and a plain `TIMESTAMP`. I kept the IDs as strings because Spark has no UUID column type. A reader expecting the dbt schema must cast the IDs, handle the timestamp without a stored time zone, and compute the missing `username_normalized` column. Both models mark invalid birthdates and set them to null.

### How do the file layouts compare?

dbt wrote one Parquet object per model. Spark wrote a directory with a part file and `_SUCCESS` for each model. The single object is simple to open. Spark's layout can use several output partitions on a larger dataset.

### How are the data checked?

This script uses count and duplicate checks, then reads the written files and tables back. The dbt model also tests null IDs, unique usernames and emails, allowed `sex`, `product`, and `quantity` values, valid states, and whether every order's `user_id` exists in users. Those checks would need to be added in Spark.

### What replaces `ref()` and `source()` here?

The script runs the steps in order and passes DataFrames from one step to the next. There is no dbt dependency graph in this script.

### Can the run times be compared directly?

The dbt build included its models and tests. The Spark run included JVM startup and both Parquet and Iceberg writes. I did not measure the Spark transformations separately, so I cannot compare their run times fairly.

### Which tool would I choose?

For a 10 GB daily batch or a SQL-only analyst team, I would use dbt with DuckDB. For 10 TB daily, I would use Spark because the work can be split across machines.

## Exercises

### Birthdate check

The DataFrame and SQL versions gave the same validity flag for every user. Five birthdates were later than the first order, matching the dbt lab. The Spark silver output now marks these five rows as invalid and sets their birthdates to null, as the dbt model does.

### Zip code extraction

All three methods found a zip code in the 50 bronze addresses. `%%timeit` is a notebook command, so I timed each full DataFrame action three times with `perf_counter` in the script:

| Method | Seconds |
| --- | --- |
| Spark regex | 0.543, 0.567, 0.390 |
| Python UDF | 2.087, 0.305, 0.326 |
| pandas UDF | 1.205, 0.297, 0.349 |

The first UDF run was slower than later runs. With only 50 rows, these timings mostly show startup overhead, so I would keep the Spark regex for this extraction.

### Cache the bronze files

After the first read, I cached both bronze DataFrames and ran a group by on users and orders. Spark UI's Storage tab showed two cached RDDs, each with one partition 100% cached. The users cache used 9.2 KiB of memory and the orders cache used 144.4 KiB. The later group by jobs could reuse those cached rows instead of reading the CSV files again.

### Append an Iceberg order

I appended one order to `lab.silver.orders`. The current table had 2,830 orders, while `VERSION AS OF` the snapshot before the append returned 2,829. The snapshots table showed an `append` after the earlier `overwrite` snapshots.

I also copied the Parquet orders to a separate exercise directory and appended the same order there. Its count went from 2,829 to 2,830, but the directory has no snapshot ID or `VERSION AS OF` query. To recover the earlier state, I would need to keep a separate copy or track the files myself.
