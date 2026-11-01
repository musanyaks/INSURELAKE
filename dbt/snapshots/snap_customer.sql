{% snapshot snap_customer %}
{{
  config(
    target_schema='snapshots',
    unique_key='customer_id',
    strategy='timestamp',
    updated_at='updated_at',
  )
}}
SELECT
    customer_id,
    name,
    address,
    phone,
    county,
    updated_at
FROM {{ source('iceberg', 'customers') }}
{% endsnapshot %}