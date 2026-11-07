# Polaris catalog lab

## Connect Spark to the catalogs

`SHOW NAMESPACES IN lab` listed `silver` from the Hadoop catalog in S3. `SHOW NAMESPACES IN polaris` asked the Polaris REST catalog and returned no namespaces before registration. Spark sends the `dev` credential to Polaris. S3 access uses the separate temporary AWS credentials.

## Register `silver.orders`

The current Hadoop metadata file was `v8.metadata.json`. I registered it as `polaris.silver.orders`. Both catalogs returned 2,834 orders. The S3 directory had 30 objects before and after the registration, so Polaris added a table reference without copying the data files.

I will write new versions of this table through Polaris. A write through `lab` would update the Hadoop catalog's metadata pointer while Polaris could still point to the previous version.
