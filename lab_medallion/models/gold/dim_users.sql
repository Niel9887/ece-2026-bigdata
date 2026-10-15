select
    u.user_id,
    u.name,
    u.username_normalized,
    u.email,
    u.birthdate,
    u.birthdate_is_valid,
    u.state,
    s.name as state_name,
    s.region,
    min(cast(o.ordered_at as date)) as first_order_date,
    max(cast(o.ordered_at as date)) as last_order_date,
    count(o.order_id) as order_count,
    coalesce(sum(o.quantity), 0) as total_quantity
from {{ ref('stg_users') }} u
left join {{ ref('states') }} s on u.state = s.code
left join {{ ref('stg_orders') }} o on u.user_id = o.user_id
group by all
