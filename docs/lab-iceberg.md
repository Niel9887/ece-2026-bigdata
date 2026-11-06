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
