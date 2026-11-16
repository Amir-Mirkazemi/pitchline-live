-- Who creates the best chances? One row per player per competition.
select
    pm.player_id,
    p.player_name,
    mode(pm.team)                                                         as team,
    m.competition_label,
    count(*)                                                              as matches,
    sum(pm.minutes)                                                       as minutes,
    sum(pm.key_passes)                                                    as key_passes,
    round(sum(pm.xg_assisted), 3)                                         as xg_assisted,
    round(sum(pm.xg_assisted) * 90.0 / nullif(sum(pm.minutes), 0), 3)     as xg_assisted_per90,
    sum(pm.big_chances_created)                                           as big_chances_created,
    sum(pm.goal_assists)                                                  as goal_assists,
    sum(pm.passes)                                                        as passes,
    round(100.0 * sum(pm.passes_completed) / nullif(sum(pm.passes), 0), 1) as pass_completion_pct,
    sum(pm.progressive_passes)                                            as progressive_passes,
    round(sum(pm.progressive_passes) * 90.0 / nullif(sum(pm.minutes), 0), 2) as progressive_passes_per90
from {{ ref('fct_player_match') }} pm
join {{ ref('dim_match') }} m using (match_id)
join {{ ref('dim_player') }} p using (player_id)
group by pm.player_id, p.player_name, m.competition_label
