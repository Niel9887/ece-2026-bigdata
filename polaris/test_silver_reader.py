import os
import sys

from session import make_spark


action = sys.argv[1]
if action == "check":
    os.environ["POLARIS_PRINCIPAL"] = "silver_test"
else:
    os.environ["POLARIS_PRINCIPAL"] = "dev"

spark = make_spark()

if action == "prepare":
    spark.sql("CREATE NAMESPACE IF NOT EXISTS polaris.gold")
    tables = {row.tableName for row in spark.sql("SHOW TABLES IN polaris.gold").collect()}
    if "test_orders" not in tables:
        spark.sql("CREATE TABLE polaris.gold.test_orders USING iceberg AS "
                  "SELECT * FROM polaris.silver.orders LIMIT 1")
    print("Gold test rows:", spark.sql("SELECT count(*) AS total FROM polaris.gold.test_orders").first()["total"])

elif action == "check":
    spark.sql("SHOW TABLES IN polaris.silver").show()
    print("Silver orders:", spark.sql("SELECT count(*) AS total FROM polaris.silver.orders").first()["total"])
    try:
        spark.sql("SELECT count(*) FROM polaris.gold.test_orders").show()
    except Exception as exc:
        print("Gold denied:", str(exc).splitlines()[0])
    else:
        raise SystemExit("Gold was unexpectedly readable")

elif action == "cleanup":
    spark.sql("DROP TABLE IF EXISTS polaris.gold.test_orders")
    spark.sql("DROP NAMESPACE IF EXISTS polaris.gold")
    print("Gold test table and namespace removed")

else:
    raise SystemExit("Use prepare, check, or cleanup")

spark.stop()
