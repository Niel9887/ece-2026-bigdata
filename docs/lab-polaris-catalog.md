# Polaris catalog lab

## Connect Spark to the catalogs

`SHOW NAMESPACES IN lab` listed `silver` from the Hadoop catalog in S3. `SHOW NAMESPACES IN polaris` asked the Polaris REST catalog and returned no namespaces before registration. Spark sends the `dev` credential to Polaris. S3 access uses the separate temporary AWS credentials.

## Register `silver.orders`

The current Hadoop metadata file was `v8.metadata.json`. I registered it as `polaris.silver.orders`. Both catalogs returned 2,834 orders. The S3 directory had 30 objects before and after the registration, so Polaris added a table reference without copying the data files.

I will write new versions of this table through Polaris. A write through `lab` would update the Hadoop catalog's metadata pointer while Polaris could still point to the previous version.

## Create `silver.users` as dev

I read 54 users from `lab.silver.users` and created `polaris.silver.users` from that DataFrame. Polaris also returned 54 users. The new table files are under `s3://user-n-raluy-ece/warehouse/silver/users/`, the location of the `silver` namespace.

For `orders`, registration reused the existing metadata and data files. Creating `users` wrote a new table version and a Parquet data file through Polaris. The older Hadoop table still has its own catalog pointer.

## Check the `country` column

`lab.silver.users` already had `country` from the Iceberg lab, so my first Polaris table inherited it. I dropped `country` from the source DataFrame when I recreated `polaris.silver.users`. Then I ran `ALTER TABLE ... ADD COLUMN country STRING` as `dev`. Polaris wrote `00001-adad0675-85cb-4e09-bc9a-950117576f9c.metadata.json`. The snapshot count stayed at one. This is different from `v8.metadata.json`, the file used to register `orders`.

The analyst's later `ALTER TABLE` attempt was denied for missing `ADD_TABLE_SCHEMA`. This is the privilege Polaris checks for a column change.

## Read as analyst

The `analyst` session listed the `silver` tables and ran the order count by product. Polaris refused `INSERT` because this principal is not authorized for `ADD_TABLE_SNAPSHOT`. It refused `ALTER TABLE ... ADD COLUMN phone` because it is not authorized for `ADD_TABLE_SCHEMA`. The `catalog_reader` role grants `TABLE_READ_DATA`, `TABLE_READ_PROPERTIES`, and `CATALOG_READ_PROPERTIES`.

I checked `orders` again as `dev` after the failed insert. It still had 2,834 rows and the same seven snapshots, so the denied write did not commit a new table version.

Polaris checks catalog requests, but Spark also has S3 credentials. Someone with direct access to those S3 credentials can read the files in the bucket without asking Polaris.

## Exercise: remove `country`

I dropped `country` from `polaris.silver.users`. Polaris wrote `00001-ab0c1893-d7ee-41e5-b219-e86995b786ce.metadata.json`. The table still had one snapshot before and after. Dropping a column changes the schema in metadata; it does not rewrite the Parquet rows.

## Exercise: read only `silver`

I created `silver_tester`, assigned it `silver_test_role`, and granted that role the `silver_reader` catalog role. The catalog-level grant allows reading catalog properties. The listing and table read grants apply only to the `silver` namespace.

As `silver_tester`, I could count 2,834 rows in `polaris.silver.orders`. I created `polaris.gold.test_orders` as `dev` with one row. Reading it as `silver_tester` returned `Forbidden`: the principal was not authorized for `LOAD_TABLE` in `gold`.

I then dropped the test table and the empty `gold` namespace as `dev`.

## Cleanup

I dropped `polaris.silver.users` as `dev`. `polaris.silver.orders` remained with 2,834 rows for the Trino lab. The separate Hadoop catalog still read 54 rows from `lab.silver.users` after the drop.
