-- Every match needs 22 starters (11 per side).
select match_id, count(*) as starters
from {{ ref('stg_lineups') }}
group by match_id
having count(*) <> 22
