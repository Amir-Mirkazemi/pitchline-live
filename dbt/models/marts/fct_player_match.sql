-- One row per player per match they played in.
with minutes as (
    select match_id, player_id, any_value(team_id) as team_id, any_value(team) as team,
           sum(minutes_played) as minutes
    from {{ ref('int_player_minutes') }}
    group by match_id, player_id
),
pass_stats as (
    select match_id, player_id,
           count(*)                                   as passes,
           sum(is_completed::int)                     as passes_completed,
           sum(is_progressive::int)                   as progressive_passes,
           sum(is_goal_assist::int)                   as goal_assists
    from {{ ref('int_passes') }}
    group by match_id, player_id
),
shot_stats as (
    select match_id, player_id,
           count(*)                                   as shots,
           coalesce(sum(xg), 0)                       as xg,
           sum(is_goal::int)                          as goals
    from {{ ref('int_shots') }}
    where not is_shootout
    group by match_id, player_id
),
chance_stats as (
    select match_id, creator_id as player_id,
           count(*)                                   as key_passes,
           sum(xg)                                    as xg_assisted,
           sum(is_big_chance::int)                    as big_chances_created
    from {{ ref('int_chances') }}
    group by match_id, creator_id
)
select
    m.match_id,
    m.player_id,
    m.team_id,
    m.team,
    m.minutes,
    coalesce(p.passes, 0)               as passes,
    coalesce(p.passes_completed, 0)     as passes_completed,
    coalesce(p.progressive_passes, 0)   as progressive_passes,
    coalesce(p.goal_assists, 0)         as goal_assists,
    coalesce(s.shots, 0)                as shots,
    coalesce(s.xg, 0)                   as xg,
    coalesce(s.goals, 0)                as goals,
    coalesce(c.key_passes, 0)           as key_passes,
    coalesce(c.xg_assisted, 0)          as xg_assisted,
    coalesce(c.big_chances_created, 0)  as big_chances_created
from minutes m
left join pass_stats p   using (match_id, player_id)
left join shot_stats s   using (match_id, player_id)
left join chance_stats c using (match_id, player_id)
