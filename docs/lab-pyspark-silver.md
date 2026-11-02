# PySpark silver lab

## SparkSession with S3 access

### What happens if the service is restarted during a Spark job?

The job stops because the driver and executors run inside the Onyxia service. A new service starts a new Spark session with new temporary credentials.

### Why does `SimpleAWSCredentialsProvider` fail here?

It sends the access key and secret key without the session token. Onyxia's temporary credentials need all three values, so the S3 request fails.

## Bronze layer

The S3 read returned 50 users and 2,829 orders. Spark inferred `birthdate` as a date and the order `date` as a timestamp.
