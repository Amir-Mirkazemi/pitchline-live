-- One row per team per match, with the opponent's numbers alongside.
with sides as (
    select match_id, competition_label, home_team_id as team_id, home_team as team,
           away_team_id as opponent_id, home_score as goals_for, away_score as goals_against
    from {{ ref('dim_match') }}
    union all
    select match_id, competition_label, away_team_id, away_team,
           home_team_id, away_score, home_score
    from {{ ref('dim_match') }}
),
shots as (
    select match_id, team_id, count(*) as shots, coalesce(sum(xg), 0) as xg
    from {{ ref('int_shots') }}
    where not is_shootout
    group by match_id, team_id
)
select
    s.match_id,
    s.competition_label,
    s.team_id,
    s.team,
    s.opponent_id,
    s.goals_for,
    s.goals_against,
    coalesce(f.shots, 0)  as shots_for,
    coalesce(f.xg, 0)     as xg_for,
    coalesce(a.shots, 0)  as shots_against,
    coalesce(a.xg, 0)     as xg_against
from sides s
left join shots f on f.match_id = s.match_id and f.team_id = s.team_id
left join shots a on a.match_id = s.match_id and a.team_id = s.opponent_id
