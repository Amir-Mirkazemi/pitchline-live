-- Pitch coordinates run 0-120 (own goal to opponent goal) by 0-80.
-- "Progressive" here means: a completed open-play pass that moves the ball at least 10 yards
-- toward the opponent goal and ends in the attacking 60% of the pitch.
select
    match_id,
    event_id                                  as pass_id,
    period,
    minute,
    team_id,
    team,
    player_id,
    player,
    position,
    x,
    y,
    pass_end_x                                as end_x,
    pass_end_y                                as end_y,
    pass_length,
    pass_height,
    pass_type,
    pass_recipient_id,
    pass_recipient,
    pass_outcome,
    pass_outcome is null                      as is_completed,
    pass_shot_assist                          as is_shot_assist,
    pass_goal_assist                          as is_goal_assist,
    (
        pass_outcome is null
        and pass_end_x is not null
        and (pass_end_x - x) >= 10
        and pass_end_x >= 48
        and coalesce(pass_type, 'Open Play') not in
            ('Corner', 'Free Kick', 'Throw-in', 'Goal Kick', 'Kick Off')
    )                                         as is_progressive
from {{ ref('stg_events') }}
where event_type = 'Pass'
