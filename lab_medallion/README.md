# dbt medallion lab

This dbt project reads the bronze CSV files from S3 and builds silver models with DuckDB.

Run commands from this directory. Set `LAB_BUCKET_NAME` to the Onyxia bucket name first.

```bash
uv run dbt debug
uv run dbt build --select silver
```
