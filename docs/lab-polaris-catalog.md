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

`lab.silver.users` already had `country` from the Iceberg lab, so the new Polaris table inherited it. The add-column script found the column and did not run `ALTER TABLE`. No metadata JSON was added and the table stayed at one snapshot. The initial Polaris metadata file, `00000-ad5ecde7-add2-4c5f-8f40-7631e2b48395.metadata.json`, already records `country`.
