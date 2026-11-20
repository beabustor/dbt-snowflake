{{ config(materialized='view') }}

select
    fecha_pedido,
    count(*) as pedidos_pagados,
    sum(importe_eur) as importe_pagado_eur
from {{ ref('fct_pedidos') }}
where estado = 'pagado'
group by fecha_pedido
