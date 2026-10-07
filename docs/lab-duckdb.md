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
