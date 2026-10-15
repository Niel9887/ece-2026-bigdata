{{
    config(
        materialized='incremental',
        unique_key='order_id'
    )
}}

select
    o.order_id,
    o.ordered_at,
    cast(o.ordered_at as date) as order_date,
    o.product,
    o.quantity,
    u.user_id,
    u.state,
    s.name as state_name,
    s.region
from {{ ref('stg_orders') }} o
join {{ ref('stg_users') }} u on o.user_id = u.user_id
left join {{ ref('states') }} s on u.state = s.code
{% if is_incremental() %}
where o.ordered_at > (select max(ordered_at) from {{ this }})
{% endif %}
