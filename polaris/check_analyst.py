import os
import re

from session import make_spark


os.environ["POLARIS_PRINCIPAL"] = "analyst"
spark = make_spark()
print("Principal: analyst")
spark.sql("SHOW TABLES IN polaris.silver").show()
spark.sql("SELECT product, count(*) AS orders FROM polaris.silver.orders GROUP BY product").show()

checks = {
    "INSERT": "INSERT INTO polaris.silver.orders SELECT * FROM polaris.silver.orders LIMIT 1",
    "ALTER": "ALTER TABLE polaris.silver.users ADD COLUMN phone STRING",
}

for name, statement in checks.items():
    try:
        spark.sql(statement).collect()
    except Exception as exc:
        match = re.search(r"ForbiddenException: ([^\n]+)", str(exc))
        print(name, "denied:", match.group(0) if match else str(exc).splitlines()[0])
    else:
        raise SystemExit(name + " was unexpectedly allowed")

spark.stop()
