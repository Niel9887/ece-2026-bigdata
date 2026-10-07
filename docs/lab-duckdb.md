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

## Exercises

The queries are in `sql/04_exercises.sql`.

### 1. Average number of orders per user and average quantity per order

```sql
SELECT
  round((SELECT count(*) FROM orders) / (SELECT count(*) FROM users), 2) AS avg_orders_per_user,
  round(avg(quantity), 2) AS avg_quantity_per_order
FROM orders;
```

| avg_orders_per_user | avg_quantity_per_order |
|---|---|
| 56.58 | 3.05 |

Each user has 56.58 orders on average (2829 / 50), and each order has 3.05 items.

### 2. First and last order of each user, and number of days between them

```sql
SELECT
  u.username,
  min(o.date)::DATE AS first_order,
  max(o.date)::DATE AS last_order,
  date_diff('day', min(o.date)::DATE, max(o.date)::DATE) AS days_between
FROM users u
LEFT JOIN orders o ON o.user_uuid = u.uuid
GROUP BY u.uuid, u.username
ORDER BY first_order, u.username;
```

| username | first_order | last_order | days_between |
|---|---|---|---|
| garzaanthony | 2020-01-01 | 2020-01-04 | 3 |
| blairamanda | 2020-01-04 | 2020-01-05 | 1 |
| elizabethmiles | 2020-01-05 | 2020-01-06 | 1 |
| ... | | | |

The query returns 50 rows and the gap is never more than 5 days. The generator creates the orders of a user one after the other, one per hour, so each user only orders over a few days.

### 3. Hour of the day with the highest quantity sold

```sql
SELECT hour(date) AS hour, sum(quantity) AS quantity
FROM orders
GROUP BY hour
ORDER BY quantity DESC
LIMIT 3;
```

| hour | quantity |
|---|---|
| 6 | 385 |
| 15 | 382 |
| 0 | 379 |

6 AM (UTC) has the highest quantity with 385 items, ahead of 3 PM (382) and midnight (379). There is one order per hour, so every hour has 117 or 118 orders and the gap mostly comes from the random quantities.

### 4. Month-over-month variation of the quantity sold per product, in percent

```sql
WITH monthly AS (
  SELECT product, strftime(date, '%Y-%m') AS month, sum(quantity) AS quantity
  FROM orders
  GROUP BY product, month
),
with_previous AS (
  SELECT
    product,
    month,
    quantity,
    lag(quantity) OVER (PARTITION BY product ORDER BY month) AS previous_quantity
  FROM monthly
)
SELECT
  product,
  month,
  quantity,
  previous_quantity,
  round(100 * (quantity - previous_quantity) / previous_quantity, 1) AS variation_pct
FROM with_previous
ORDER BY product, month;
```

The query returns one row per product and month (January rows have `NULL`). I reshaped `variation_pct` (in %) into one column per month:

| product | 2020-02 | 2020-03 | 2020-04 |
|---|---|---|---|
| bread | 14.9 | 13.5 | -19.2 |
| brioche | -18.8 | -4.9 | -6.9 |
| cookie | -1.3 | -8.4 | -18.2 |
| croissant | 8.9 | -1.8 | 0.3 |
| donut | -28.3 | 2.2 | -1.2 |
| drink | -3.2 | 10.1 | -13.2 |

January has no previous month, so `lag` returns `NULL`. The last order is on April 27, so April has only 645 orders against 744 in March, which explains part of the drop.

### 5. Users who ordered every product at least once

```sql
SELECT u.username, count(DISTINCT o.product) AS products
FROM orders o
JOIN users u ON o.user_uuid = u.uuid
GROUP BY u.uuid, u.username
HAVING count(DISTINCT o.product) = (SELECT count(DISTINCT product) FROM orders)
ORDER BY u.username;
```

45 users out of 50 ordered all 6 products. The other 5 users have very few orders: millertodd (2 orders), kayla51 (4), clarence34 (6), heatherberger (8) and perezrebecca (12).

## Parquet export

The queries are in `sql/05_parquet.sql`.

### Why is the `uuid` column barely compressed?

The UUIDs are random and all different, so dictionary encoding cannot help, unlike for `user_uuid`, and Snappy only finds the repeated hexadecimal characters and dashes. The column only goes from 113189 to 102191 bytes.

### Why is the compressed size of some columns larger than their uncompressed size?

These columns are already compact before compression: `product` uses dictionary encoding and `date` is stored as binary integers. Snappy has nothing left to remove and adds a few bytes of its own, so `date` goes from 22661 to 22667 bytes and `product` from 1266 to 1271.

## Hive partitioning

### Why is partitioning by `uuid` a bad idea?

Every order would get its own directory, which gives 2829 Parquet files of one row each. This is the small files problem of object storage: each file costs a request and listing the prefix becomes slow. Queries almost never filter on a `uuid`, so no file would be skipped anyway.

### Which partition column would you choose for a dataset of orders growing every day?

I would partition by a time column: by day (a `day` column computed as `date::DATE`) when the daily volume is large, or by month for this dataset, where a day only holds 24 orders and daily files would bring back the small files problem. New orders go into a new partition without rewriting the old files, and a query on a period only reads the partitions of that period.

## CSV vs. Parquet at scale

The queries are in `sql/06_large.sql` and the measurements in `scripts/measure_csv_parquet.sh`. With `-u 5000` I get 252416 orders, a CSV of 28.2 MiB and a Parquet file of 11.0 MiB.

| Query | Data received | #GET | Time (s) |
|---|---|---|---|
| CSV on S3, `sum(quantity)` per product | 28.2 MiB | 1 | 1.30 |
| Parquet on S3, same query | 203.5 KiB | 4 | 0.34 |
| Parquet on S3, `date >= '2100-01-01'` | 16.0 KiB | 1 | 0.27 |
| Local CSV file, `sum(quantity)` per product (no network) | - | - | 0.23 |

### How many row groups does the file contain, and how many are skipped by the filter `date >= '2100-01-01'`?

The file has 3 row groups (123573, 124276 and 4567 rows). The last date is in October 2048, so the maximum of every row group is before 2100 and the 3 row groups are skipped. DuckDB only reads the footer of the file: 16.0 KiB in 1 GET request.

### The orders are sorted by date. What would happen to the efficiency of the filter if they were shuffled?

Most filters could not skip any row group anymore. Each row group would contain dates from 2020 to 2048, so its min and max would be almost those of the whole file, and a filter like `date >= '2040-01-01'` would read the whole `date` column. The filter on 2100 would still skip everything, because no date reaches 2100.

### Compare the execution time of the CSV and Parquet queries. Which part of the difference is due to the network, which part to the parsing of the CSV file?

Most of the 0.96 s gap between CSV and Parquet comes from the network. The CSV query takes 1.30 s on S3 but only 0.23 s on the local file, so about 1.07 s is the download of the 28.2 MiB file and about 0.23 s is parsing the text. The Parquet query takes 0.34 s and the filtered Parquet query already takes 0.27 s for 16 KiB, so the Parquet time is mostly a fixed cost for its requests.
