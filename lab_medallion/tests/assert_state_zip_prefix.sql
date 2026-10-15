{{ config(severity='warn') }}

select u.user_id, u.state, u.zip_code
from {{ ref('stg_users') }} u
left join {{ ref('zip_prefixes') }} z
    on left(u.zip_code, 3) = z.zip3 and u.state = z.state
where u.state not in ('AA', 'AE', 'AP') -- Military ZIPs are absent from the Census reference.
    and z.zip3 is null
