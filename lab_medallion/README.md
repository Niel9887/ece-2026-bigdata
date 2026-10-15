# dbt medallion lab

This dbt project reads the bronze CSV files from S3 and builds silver models with DuckDB.

Run commands from this directory. Set `LAB_BUCKET_NAME` to the Onyxia bucket name first.

```bash
uv run dbt debug
uv run dbt build --select silver
```

From the repository root, export the two silver models to S3 with:

```bash
uv run python scripts/export_silver.py
```
