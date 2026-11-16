-- Approximate minutes played, from the starting XI and substitution events.
-- Limitation: red cards are not modelled, so a sent-off player keeps full minutes.
with match_end as (
    select match_id, max(minute) + 1 as end_minute
    from {{ ref('stg_events') }}
    where is_regular_play
    group by match_id
),
starters as (
    select match_id, team_id, team, player_id, player, 0 as on_minute
    from {{ ref('stg_lineups') }}
),
subs as (
    select match_id, team_id, team, player_id as off_player_id,
           sub_replacement_id as player_id, sub_replacement as player, minute as sub_minute
    from {{ ref('stg_events') }}
    where event_type = 'Substitution'
),
appearances as (
    select match_id, team_id, team, player_id, player, on_minute from starters
    union all
    select match_id, team_id, team, player_id, player, sub_minute from subs
),
subbed_off as (
    select match_id, off_player_id as player_id, sub_minute as off_minute from subs
)
select
    a.match_id,
    a.team_id,
    a.team,
    a.player_id,
    a.player,
    a.on_minute,
    coalesce(o.off_minute, e.end_minute)                    as off_minute,
    coalesce(o.off_minute, e.end_minute) - a.on_minute      as minutes_played
from appearances a
join match_end e using (match_id)
left join subbed_off o
  on o.match_id = a.match_id and o.player_id = a.player_id
