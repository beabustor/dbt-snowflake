select evento_id, importe_eur
from {{ ref('stg_eventos_pedidos') }}
where importe_eur < 0
