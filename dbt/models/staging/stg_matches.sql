select
    match_id,
    cast(match_date as date)                      as match_date,
    competition_id,
    season_id,
    competition_name,
    season_name,
    competition_name || ' ' || season_name        as competition_label,
    stage,
    home_team_id,
    home_team,
    away_team_id,
    away_team,
    home_score,
    away_score,
    stadium,
    referee
from {{ source('bronze', 'matches') }}
