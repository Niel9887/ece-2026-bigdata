# dbt lab

## Bronze layer

### 1. Why keep the bronze CSV files unchanged?

We can correct the transformation and run dbt again from the original data, even if the bug is found months later.

### 2. How should hourly orders be stored over several years?

I would store them as Parquet files partitioned by ingestion date. Queries could read only the relevant dates instead of scanning one large CSV file.

## Silver layer

### 1. When is a view preferable to a table?

A view runs its SQL when queried, so the first silver version reads the bronze CSV again each time. It is useful when the data is small or changes often and we want the latest result without storing another copy.

### 2. How many bytes does a UUID use as VARCHAR?

The usual UUID text has 36 ASCII characters, including four hyphens. It therefore uses 36 bytes in UTF-8, compared with 16 bytes for DuckDB's UUID type.

## Data tests

### 1. What should happen to invalid birthdates in the two dashboards?

For an age dashboard, I set a birthdate later than the first order to `NULL` and exclude it from age calculations. A sales by region dashboard can keep the order because its quantity and region do not depend on the birthdate.

### 2. How could we detect wrong state and ZIP combinations?

A singular test could join each `(state, zip_code)` pair to a reference table of valid combinations and return unmatched users. The `states.csv` seed only checks state codes, so this test would need a separate state and ZIP mapping.

## Gold layer

### 1. Why cast `quantity` to an integer?

Without the cast, `sum(quantity)` produced a `DOUBLE` column in the Parquet file during my local test. With the cast, the Parquet column is `INT32`, which matches an integer count of items.

### 2. Can `customers` be summed across months or products?

No. The same customer can appear in several months and buy several products, so summing those distinct counts would count that customer more than once.

### 3. What happens when the Parquet file is overwritten?

A dashboard reading during an overwrite has no consistent snapshot of the whole dataset and may fail if the file is temporarily unavailable. Apache Iceberg provides snapshots, so readers can keep using a complete version while a new one is committed.

## Pipeline

### 1. How do we rebuild `stg_orders` and its downstream models with tests?

Run `uv run dbt build --select stg_orders+` from `lab_medallion`. The `+` selects models downstream of `stg_orders`.

### 2. What happens if a column in `users.csv` is renamed?

`stg_users` still refers to the old column, so its SQL fails when dbt builds that model. The gold models depending on it are skipped until the silver model is updated.

I also removed the three military codes from the seed temporarily. The state test failed and dbt skipped 16 dependent steps. After restoring the codes, all 38 steps passed.

On Onyxia, `dbt build` passed all 38 steps in 6.98 seconds. It wrote `silver/users.parquet`, `silver/orders.parquet` and `gold/sales_by_region_month.parquet` to my S3 bucket. `dbt docs generate --static` also completed.

## Exercises

### 1. User dimension

`dim_users` keeps one row per user and adds the state name, region, first and last order dates, order count and total quantity. Its `user_id` is unique and not null. The row count test found 50 users in both `stg_users` and `dim_users` on Onyxia.

### 2. Business model

`best_product_by_region` groups orders by region and product, sums their quantities, then ranks products within each region. It returns the product with the largest quantity for each region. The model has tests for its region, product and quantity columns.

### 3. Birthdate correction

`stg_users` replaces a birthdate later than the user's first order with `NULL` and records the check in `birthdate_is_valid`. Five users on Onyxia have an invalid birthdate. `assert_orders_after_user_birth` passes.

### 4. Quantity reconciliation

`assert_gold_quantity_matches_orders` compares the sum of `quantity` in `stg_orders` and `sales_by_region_month`. Both were 8,615 on Onyxia, from 2,829 orders.

### 5. Silver Parquet materialization

Both silver models now use dbt's `external` materialization and write Parquet files under `silver/`. On the local dataset, a full `dbt build` took 3.82 seconds with views and 3.72 seconds with external Parquet. This small difference does not establish a speed gain on S3.
