select
    (select sum(quantity) from {{ ref('stg_orders') }}) as silver_quantity,
    (select sum(quantity) from {{ ref('sales_by_region_month') }}) as gold_quantity
where silver_quantity <> gold_quantity
