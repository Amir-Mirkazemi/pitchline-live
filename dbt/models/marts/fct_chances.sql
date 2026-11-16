select c.*, m.competition_label
from {{ ref('int_chances') }} c
join {{ ref('dim_match') }} m using (match_id)
