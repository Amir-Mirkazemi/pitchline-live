-- A match that is listed but has no events means a download or conversion step silently lost data.
select m.match_id, m.home_team, m.away_team
from {{ ref('dim_match') }} m
left join (select distinct match_id from {{ ref('stg_events') }}) e using (match_id)
where e.match_id is null
