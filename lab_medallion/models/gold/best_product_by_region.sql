with product_totals as (
    select
        region,
        product,
        sum(quantity) as total_quantity,
        count(*) as order_count
    from {{ ref('fct_orders') }}
    group by region, product
),

ranked as (
    select
        *,
        row_number() over (
            partition by region order by total_quantity desc, product
        ) as product_rank
    from product_totals
)

select
    region,
    product,
    total_quantity,
    order_count
from ranked
where product_rank = 1
