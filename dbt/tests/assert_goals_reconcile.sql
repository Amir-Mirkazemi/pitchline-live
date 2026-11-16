-- The scoreline must equal goals rebuilt from events (shots that scored, plus own goals).
-- Penalty-shootout shots (period 5) are excluded because they are not part of the score.
with shot_goals as (
    select match_id, team_id, count(*) as goals
    from {{ ref('fct_shots') }}
    where is_goal and not is_shootout
    group by match_id, team_id
),
own_goals as (
    select match_id, team_id, count(*) as goals
    from {{ ref('stg_events') }}
    where event_type = 'Own Goal For' and is_regular_play
    group by match_id, team_id
),
by_team as (
    select match_id, team_id, sum(goals) as goals
    from (select * from shot_goals union all select * from own_goals)
    group by match_id, team_id
)
select
    m.match_id, m.home_team, m.away_team, m.home_score, m.away_score,
    coalesce(h.goals, 0) as home_goals_from_events,
    coalesce(a.goals, 0) as away_goals_from_events
from {{ ref('dim_match') }} m
left join by_team h on h.match_id = m.match_id and h.team_id = m.home_team_id
left join by_team a on a.match_id = m.match_id and a.team_id = m.away_team_id
where coalesce(h.goals, 0) <> m.home_score
   or coalesce(a.goals, 0) <> m.away_score
