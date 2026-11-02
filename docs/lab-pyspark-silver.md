# PySpark silver lab

## SparkSession with S3 access

### What happens if the service is restarted during a Spark job?

The job stops because the driver and executors run inside the Onyxia service. A new service starts a new Spark session with new temporary credentials.

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

I would use SQL for a quick query and the DataFrame API for a transformation kept in the Python script. Both use the same Spark engine.

### Where could an empty string cause another wrong result?

The `state` or `zip_code` extraction could also return an empty string when the address does not match. Grouping by state would then count an empty state as if it were a real value.
