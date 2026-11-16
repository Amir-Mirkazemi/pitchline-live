{{ config(severity='warn') }}
-- Warns (does not fail) when a team's minutes fall well short of 11 players x match length.
-- Red cards legitimately cause this, so it is an early-warning signal, not a hard rule.
select pm.match_id, pm.team_id, sum(pm.minutes) as team_minutes, 11 * e.end_minute as expected
from {{ ref('fct_player_match') }} pm
join (
    select match_id, max(minute) + 1 as end_minute
    from {{ ref('stg_events') }} where is_regular_play group by match_id
) e using (match_id)
group by pm.match_id, pm.team_id, e.end_minute
having sum(pm.minutes) < 0.85 * 11 * e.end_minute
