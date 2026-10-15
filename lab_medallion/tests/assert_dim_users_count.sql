select
    (select count(*) from {{ ref('stg_users') }}) as silver_users,
    (select count(*) from {{ ref('dim_users') }}) as gold_users
where silver_users <> gold_users
