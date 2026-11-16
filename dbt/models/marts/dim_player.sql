select
    player_id,
    mode(player) as player_name,
    mode(team)   as primary_team
from {{ ref('stg_events') }}
where player_id is not null
group by player_id
