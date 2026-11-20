{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='pedido_id'
    )
}}

with eventos as (
    select *
    from {{ ref('stg_eventos_pedidos') }}
    {% if is_incremental() %}
        where lote_id >= (select coalesce(max(lote_id), 0) from {{ this }})
    {% endif %}
),

versiones as (
    select
        *,
        row_number() over (
            partition by pedido_id
            order by lote_id desc, evento_id desc
        ) as posicion
    from eventos
)

select
    pedido_id,
    fecha_pedido,
    canal,
    estado,
    importe_eur,
    lote_id,
    evento_id
from versiones
where posicion = 1
