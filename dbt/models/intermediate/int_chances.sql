-- A "chance" = a shot that was set up by a pass (the shot's key_pass_id points at that pass).
-- The passer is credited with the shot's xG. That credit is the player's "xG assisted" (xA).
select
    s.match_id,
    s.shot_id,
    s.team_id,
    s.team,
    p.player_id          as creator_id,
    p.player             as creator,
    s.player_id          as shooter_id,
    s.player             as shooter,
    s.xg,
    s.is_goal,
    s.is_big_chance,
    s.period,
    s.minute,
    p.x                  as pass_x,
    p.y                  as pass_y,
    p.end_x              as pass_end_x,
    p.end_y              as pass_end_y,
    p.pass_height,
    p.pass_type
from {{ ref('int_shots') }} s
join {{ ref('int_passes') }} p
  on p.pass_id = s.key_pass_id
 and p.match_id = s.match_id
where not s.is_shootout
