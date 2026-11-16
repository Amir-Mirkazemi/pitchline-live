select team_id, any_value(team) as team_name
from {{ ref('stg_events') }}
where team_id is not null
group by team_id
