{{
    config(
        materialized='external',
        location=env_var('LAB_SILVER_ROOT', 's3://' ~ env_var('LAB_BUCKET_NAME') ~ '/silver/dbt') ~ '/users.parquet'
    )
}}

with source as (
    select * from {{ source('bronze', 'users') }}
),

first_orders as (
    select user_id, min(ordered_at)::date as first_order_date
    from {{ ref('stg_orders') }}
    group by user_id
),

typed as (
    select
        cast(uuid as uuid) as user_id,
        trim(username) as username,
        lower(trim(username)) as username_normalized,
        trim(name) as name,
        upper(trim(sex)) as sex,
        lower(trim(mail)) as email,
        cast(birthdate as date) as birthdate,
        split_part(address, chr(10), 1) as street,
        split_part(address, chr(10), 2) as address_line_2
    from source
),

checked as (
    select
        typed.*,
        first_orders.first_order_date,
        first_orders.first_order_date is null
            or typed.birthdate <= first_orders.first_order_date as birthdate_is_valid
    from typed
    left join first_orders using (user_id)
)

select
    user_id,
    username,
    username_normalized,
    name,
    sex,
    email,
    case when birthdate_is_valid then birthdate else null end as birthdate,
    birthdate_is_valid,
    street,
    nullif(regexp_extract(address_line_2, '^(.+), [A-Z]{2} \d{5}$', 1), '') as city, -- Military addresses have no city.
    regexp_extract(address_line_2, '([A-Z]{2}) (\d{5})$', 1) as state,
    regexp_extract(address_line_2, '([A-Z]{2}) (\d{5})$', 2) as zip_code
from checked
