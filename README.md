# Dataset generator

This project generates a random dataset consisting of users and orders. Scripts are written in Python and the project
uses [uv](https://docs.astral.sh/uv/).

## Usage

```bash
uv run dataset-users -h
#> usage: dataset-users [-h] [-c COUNT] [-o {csv,json,jsonline}]
uv run dataset-orders -h
#> usage: dataset-orders [-h] [-C COUNT_MIN] [-c COUNT_MAX] [-d DATE_FROM] [-o {csv,json,jsonline}] [-u COUNT_USERS]
uv run orders-report -h
#> usage: orders-report [-h] [-p PRODUCT]
```

## Labs

- S3 lab: answers in [docs/lab-s3.md](docs/lab-s3.md), Kubernetes Job in `k8s/`
- DuckDB lab: answers in [docs/lab-duckdb.md](docs/lab-duckdb.md), queries in `sql/`
