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

`assert_state_zip_prefix` joins each user's state and the first three ZIP digits to `zip_prefixes.csv`. Unmatched pairs produce a warning. The separate `states.csv` seed checks only state codes.

## Silver Parquet export

I exported the two Silver views to `silver/dbt/users.parquet` and `silver/dbt/orders.parquet` in S3. I queried both files with DuckDB: they contain 50 users and 2,829 orders, the same counts as the views.

## Exercises

### 1. Add a cleaned column

`stg_users` creates `username_normalized` with `lower(trim(username))`. The column is documented and has `unique` and `not_null` tests.

### 2. Improve order validation

`stg_orders` checks the allowed products and quantities in `silver.yml`. The singular `assert_orders_quantity_positive` test rejects zero or negative quantities, and `assert_orders_have_users` checks the user reference.

### 3. Clean invalid birthdates

`stg_users` replaces a birthdate later than the user's first order with `NULL` and records the check in `birthdate_is_valid`. Five users on Onyxia have an invalid birthdate. `assert_orders_after_user_birth` passes.

### 4. Detect invalid ZIP codes

I built `zip_prefixes.csv` from the [2020 Census ZCTA-to-county file](https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt) and its [state codes](https://www2.census.gov/geo/docs/reference/codes2020/national_state2020.txt). It contains 997 three-digit ZIP prefix and state pairs. The Silver test `assert_state_zip_prefix` warns on 43 users whose pair is absent; generated addresses are random, so the warning does not stop the pipeline. Military ZIPs are excluded because the Census file does not cover them. The seed would need updating when the reference changes. A matching prefix does not prove that the full five-digit ZIP is valid.

### 5. Materialization experiment

I ran `dbt build --select silver` with views, then with tables: 7.19 seconds versus 3.74 seconds on Onyxia. Views run their SQL when queried and read the CSV again. Tables store the result in DuckDB and read the CSV when rebuilt, so they use more storage. A CSV change appears in a view on the next query but reaches a table only after rebuilding it. Tables avoid reading the source files for every query. I restored the views afterward. The final `dbt build` passed 23 steps with one ZIP warning and no errors. `dbt docs generate --static` also completed.
