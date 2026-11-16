select
    match_id,
    match_date,
    competition_id,
    season_id,
    competition_label,
    stage,
    stage <> 'Group Stage'                                      as is_knockout,
    home_team_id,
    home_team,
    away_team_id,
    away_team,
    home_score,
    away_score,
    home_score + away_score                                     as total_goals,
    case when home_score > away_score then home_team_id
         when away_score > home_score then away_team_id end     as winner_team_id,
    stadium,
    referee
from {{ ref('stg_matches') }}
