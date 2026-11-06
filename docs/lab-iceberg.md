# Iceberg lab

## Inspect the files

### Which files contain the actual rows?

The rows are in Parquet files under `warehouse/silver/orders/data/` and `warehouse/silver/users/data/`. The initial metadata saved after the Spark lab records one data file with 2,829 orders and one with 50 users. Onyxia now has 2,830 orders after the previous lab's append.

### Which files describe the table?

The `metadata/` directories contain `v1.metadata.json`, a `snap-...avro` manifest list, and a `...-m0.avro` manifest. The saved JSON file records the schema and points to one initial snapshot for each table.

### Why does an Iceberg table need more than Parquet files?

The metadata records the table schema, the current snapshot, and which data files belong to it. A Parquet directory alone does not identify a committed table version.

## Explore Iceberg metadata

### How many snapshots and current data files are there?

Spark found five snapshots and two current data files for `orders`. It found three snapshots and one current data file for `users`. The extra snapshots were created during the previous Spark lab; the committed `v1.metadata.json` files show only the first version.

### What does `snapshots` show that the Parquet files do not?

It gives a snapshot ID, operation, and commit time for each table version. A Parquet data file contains rows but does not record this table history.

## Create a second snapshot

### How many snapshots are there now?

There are six snapshots for `orders` after appending three rows. The table now has 2,833 orders.

### Did the original Parquet files disappear?

No. Both files that belonged to the table before the append are still current. The append added a third data file.

### Why does Iceberg create a new snapshot?

The new snapshot records the added file while keeping the previous table version available for a query.

## Time travel

### What does time travel read?

`VERSION AS OF` reads the rows visible at the selected snapshot. The first snapshot has 2,829 orders and the current table has 2,833.

### Why is a complete copy unnecessary?

The first snapshot still points to its original Parquet file. Later appends add files and metadata without copying those original rows.

### What if the old metadata and files were deleted?

The query for that snapshot would fail because Iceberg would no longer have the files needed to reconstruct it.

## Schema evolution

### Did the existing Parquet files have to be rewritten?

No. The files that were current before adding `source` are still part of the table. The new row increased the count from 2,833 to 2,834.

### Where is the new schema recorded?

It is recorded in the Iceberg table metadata. The `source` column appears when Spark reads the table.

### Why is schema evolution a table-level operation?

The table schema applies to both old and new data files. Changing only one Parquet file would not update the schema used to read the whole table.

## Users exercises

### Create the table and append a batch

`lab.silver.users` was created in the Spark silver lab with 50 rows. I copied three rows and gave them new `user_id` values for the append exercise. Their other fields are reused. The table now has 53 rows and its snapshot count went from three to four.

### Query before and after the append

The snapshot immediately before this append has 50 users. The current table has 53.

### Add a country column

I added `country` to `lab.silver.users` and wrote one row with `country = 'US'`. The table went from 53 to 54 rows. Its old data files are still current.

### Compare the users and orders layouts

Both Iceberg tables have `data/` and `metadata/` under `warehouse/silver/`. On S3, `orders` has seven objects in `data/` and 23 in `metadata/`. `users` has five in `data/` and 17 in `metadata/` after the exercises.

### Parquet, Iceberg, and the catalog

Parquet stores the rows in files. Iceberg adds table metadata, snapshots, and the list of files in each table version. The `lab` catalog gives Spark a name and warehouse location for those Iceberg tables.

## Compare Iceberg with Parquet

### Which path is only a Parquet directory?

`silver/spark/orders.parquet/` is a Parquet output directory. It has no Iceberg `metadata/` directory. `warehouse/silver/orders/` is an Iceberg table with data files and metadata.

### How could a Parquet directory be replaced safely during a read?

Write the replacement to a separate directory, then coordinate when readers switch to it. Overwriting the files in place could leave a reader with a mix of old and new files.

### How does Iceberg publish a new table state?

Iceberg writes the data and metadata first, then makes the new snapshot current with a metadata update. A reader sees one committed table version.

### Why use a catalog across several engines?

The catalog gives each engine the same table name and current metadata location. After a commit, the engines can find the new table version there.
