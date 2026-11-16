select * from {{ source('bronze', 'lineups') }}
