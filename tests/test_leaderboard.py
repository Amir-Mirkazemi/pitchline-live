import json

from pitchline import leaderboard as lb
from pitchline.storage import LocalStore


def _put(store, league, eid, date, players, coverage="ok"):
    rec = {"league": league, "event_id": eid, "date": date, "coverage": coverage, "players": players}
    store.write_bytes(f"espn/matches/{league}/{eid}.json", json.dumps(rec).encode())


def _p(team, name, shots, sot, goals=0, assists=0):
    return {"team": team, "player": name, "shots": shots, "shots_on_target": sot,
            "goals": goals, "assists": assists, "own_goals": 0}


def test_totals_accumulate_across_matches_and_rank_by_shots_on_target(tmp_path):
    s = LocalStore(tmp_path)
    _put(s, "eng.1", "1", "2025-08-16", [_p("A", "X", 4, 3, goals=1), _p("B", "Y", 5, 1)])
    _put(s, "eng.1", "2", "2025-08-23", [_p("A", "X", 2, 2, assists=1)], coverage="mismatch")
    players, cov = lb.load_totals(s)
    x = players[("eng.1", "X")]
    assert (x["matches"], x["shots"], x["shots_on_target"], x["goals"], x["assists"]) == (2, 6, 5, 1, 1)
    assert [r["player"] for r in lb.top(players, "eng.1")] == ["X", "Y"]
    assert cov["eng.1"] == {"matches": 2, "ok": 1}


def test_ties_break_on_shots_then_name_and_leagues_stay_separate(tmp_path):
    s = LocalStore(tmp_path)
    _put(s, "eng.1", "1", "2025-08-16", [_p("A", "Zed", 3, 2), _p("A", "Amy", 3, 2), _p("A", "Bob", 4, 2)])
    _put(s, "esp.1", "9", "2025-08-16", [_p("C", "Zed", 9, 9)])
    players, _ = lb.load_totals(s)
    assert [r["player"] for r in lb.top(players, "eng.1")] == ["Bob", "Amy", "Zed"]
    assert [r["player"] for r in lb.top(players, "esp.1")] == ["Zed"]


def test_team_is_the_latest_one_and_markdown_renders(tmp_path):
    s = LocalStore(tmp_path)
    _put(s, "eng.1", "2", "2025-09-01", [_p("New FC", "X", 1, 1)])
    _put(s, "eng.1", "1", "2025-08-01", [_p("Old FC", "X", 1, 0)])
    players, cov = lb.load_totals(s, "eng.1")
    assert players[("eng.1", "X")]["team"] == "New FC"
    md = lb.markdown(players, cov, 5)
    assert "| 1 | X | New FC | 2 | 2 | 1 | 0 | 0 |" in md and "2 matches stored" in md
