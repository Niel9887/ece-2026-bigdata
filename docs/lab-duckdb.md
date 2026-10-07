# DuckDB lab

The queries are in `sql/`, one file per part of the lab. I run them in the DuckDB CLI with `.read sql/<file>.sql`.

## S3 configuration

### The persistent secret is stored in a file of your home directory. What are the risks, and why are they limited on Onyxia?

The file `~/.duckdb/stored_secrets` stores the access key, the secret key and the session token unencrypted. Anyone who can read this file, or a copy of my home directory, gets read and write access to my whole bucket. On Onyxia the credentials are temporary: a stolen key expires on its own and stops working, and a restart of the service gives me new ones.

### The secret is visible to any process running as your user. How would you restrict the access to S3 for a Kubernetes Job?

I would give the Job its own credentials instead of mine. They are stored in a Kubernetes Secret and injected only into its pod with `envFrom` and `secretRef`, the same way as the `upload-bronze` Job of the S3 lab, which reused my credentials. A policy limits them to what the Job needs, for example `s3:PutObject` on `bronze/` only.

## Query the bronze layer

### Why does `approx_unique` return 40 and 3167?

`approx_unique` is an estimate: `SUMMARIZE` counts the distinct values without storing them all, so the result can be too low or too high, here 40 instead of 50 and 3167 instead of 2829. The `count(DISTINCT ...)` query at the end of `sql/01_bronze.sql` gives the exact values, 50 and 2829.

### Which issue may occur with a large file whose first rows are not representative?

DuckDB picks the type of a column from the sample. If a column only has integers in the first rows, it becomes `BIGINT`, and the read fails later on the first text or decimal value.
