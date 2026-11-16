-- A team can never have more than 11 players' worth of minutes on the pitch.
select pm.match_id, pm.team_id, sum(pm.minutes) as team_minutes
from {{ ref('fct_player_match') }} pm
join (
    select match_id, max(minute) + 1 as end_minute
    from {{ ref('stg_events') }} where is_regular_play group by match_id
) e using (match_id)
group by pm.match_id, pm.team_id, e.end_minute
having sum(pm.minutes) > 11 * e.end_minute + 1
