select
    competition_label,
    team_id,
    team,
    count(*)                                   as matches,
    sum(goals_for)                             as goals_for,
    sum(goals_against)                         as goals_against,
    round(sum(xg_for), 2)                      as xg_for,
    round(sum(xg_against), 2)                  as xg_against,
    round(sum(xg_for) - sum(xg_against), 2)    as xg_diff,
    round(sum(goals_for) - sum(xg_for), 2)     as goals_minus_xg,
    sum(shots_for)                             as shots_for,
    sum(shots_against)                         as shots_against
from {{ ref('fct_team_match') }}
group by competition_label, team_id, team
