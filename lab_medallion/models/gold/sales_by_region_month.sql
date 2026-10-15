{{
    config(
        materialized='external',
        location=env_var('LAB_GOLD_ROOT', 's3://' ~ env_var('LAB_BUCKET_NAME') ~ '/gold') ~ '/sales_by_region_month.parquet'
    )
}}

select
    strftime(order_date, '%Y-%m') as month,
    region,
    product,
    count(*) as orders,
    count(distinct user_id) as customers,
    cast(sum(quantity) as integer) as quantity
from {{ ref('fct_orders') }}
group by all
order by all
