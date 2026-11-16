select s.*, m.competition_label
from {{ ref('int_shots') }} s
join {{ ref('dim_match') }} m using (match_id)
