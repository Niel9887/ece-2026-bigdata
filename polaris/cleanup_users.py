import os

from session import make_spark


os.environ["POLARIS_PRINCIPAL"] = "dev"
spark = make_spark()

spark.sql("DROP TABLE IF EXISTS polaris.silver.users")
tables = {row.tableName for row in spark.sql("SHOW TABLES IN polaris.silver").collect()}
print("Polaris silver tables:", sorted(tables))
print("Hadoop users:", spark.sql("SELECT count(*) AS total FROM lab.silver.users").first()["total"])
print("Polaris orders:", spark.sql("SELECT count(*) AS total FROM polaris.silver.orders").first()["total"])

spark.stop()
