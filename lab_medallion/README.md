# dbt medallion lab

This dbt project reads bronze CSV files from S3 and builds the silver models as DuckDB views. The silver views can also be exported to Parquet under `silver/dbt/` in S3.

Run commands from this directory. Set `LAB_BUCKET_NAME` to the Onyxia bucket name first.

```bash
uv run dbt debug
uv run dbt build
uv run duckdb lab_medallion.duckdb -c "COPY (SELECT * FROM main_silver.stg_users) TO 's3://$LAB_BUCKET_NAME/silver/dbt/users.parquet' (FORMAT parquet, OVERWRITE_OR_IGNORE true);"
uv run duckdb lab_medallion.duckdb -c "COPY (SELECT * FROM main_silver.stg_orders) TO 's3://$LAB_BUCKET_NAME/silver/dbt/orders.parquet' (FORMAT parquet, OVERWRITE_OR_IGNORE true);"
uv run dbt docs generate --static
```

The ZIP prefix test warns on the generated addresses with inconsistent state and ZIP pairs.
