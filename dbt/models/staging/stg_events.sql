-- One row per on-ball event. Materialized as a table: it is the biggest model and is read often.
select
    * exclude ("type"),
    "type"        as event_type,
    (period <= 4) as is_regular_play   -- period 5 is the penalty shootout
from {{ source('bronze', 'events') }}
