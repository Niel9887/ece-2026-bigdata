# Iceberg lab

The tables from the Spark silver lab are the starting point. `inspect_tables.py` only reads them; it does not create or overwrite either table.

Run from the repository root in the Onyxia `vscode-pyspark` service, after checking that its temporary S3 credentials work:

```bash
aws s3 ls "s3://$KUBERNETES_NAMESPACE/warehouse/silver/" --recursive --endpoint-url "https://$AWS_S3_ENDPOINT"
spark-submit --master 'local[2]' --driver-memory 512m \
  --packages org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0 \
  iceberg/inspect_tables.py
```

The script prints the current row counts, snapshots, and data files for `orders` and `users`. It also compares the first orders snapshot with the current table. Snapshot counts can be higher than the initial metadata committed during the previous lab because that lab also ran an append exercise.

After recording those results, run the append exercise once:

```bash
spark-submit --master 'local[2]' --driver-memory 512m \
  --packages org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0 \
  iceberg/append_orders.py
```

The script adds three orders with new IDs, checks the row count before and after, and reads the preceding snapshot with `VERSION AS OF`. Running it again would add three more orders.

To add the `source` column and one order with the new schema, run once:

```bash
spark-submit --master 'local[2]' --driver-memory 512m \
  --packages org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0 \
  iceberg/evolve_orders.py
```

The script checks that the old data files remain in the table. It expects `source` to be absent at the start, so do not rerun it after it succeeds.
