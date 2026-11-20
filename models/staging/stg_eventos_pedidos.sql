{{ config(materialized='view') }}

select distinct
    evento_id,
    lote_id,
    pedido_id,
    fecha_pedido,
    lower(trim(canal)) as canal,
    lower(trim(estado)) as estado,
    importe_eur
from {{ ref('eventos_pedidos') }}
where lote_id <= {{ var('lote_hasta', 2) | int }}
