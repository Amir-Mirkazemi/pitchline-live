from datetime import date
from itertools import chain, repeat

from pitchline import espn_backfill as eb
from pitchline.http import HttpStatus
from pitchline.storage import LocalStore


def _shot(pid, team, ptype, text="Attempt missed. A (T) right footed shot from outside the box is too high."):
    return {"text": text, "play": {"id": pid, "type": {"text": ptype}, "text": text, "period": {"number": 1},
            "clock": {"value": 60.0}, "team": {"displayName": team},
            "participants": [{"athlete": {"displayName": "A"}}],
            "fieldPositionX": 85.0, "fieldPositionY": 50.0, "goalPositionY": 50.0}}


def _summary(n_home, n_home_on, boxscore_total=None):
    shots = [_shot(str(i), "Home", "Shot On Target" if i < n_home_on else "Shot Off Target")
             for i in range(n_home)]
    stats = [{"name": "totalShots", "displayValue": str(boxscore_total or n_home)},
             {"name": "shotsOnTarget", "displayValue": str(n_home_on)},
             {"name": "blockedShots", "displayValue": "0"}]
    return {"commentary": shots, "boxscore": {"teams": [{"team": {"displayName": "Home"}, "statistics": stats}]}}


def _event(eid="1"):
    return {"id": eid, "date": "2024-01-01T12:00Z", "status": {"type": {"completed": True}},
            "competitions": [{"competitors": [{"team": {"displayName": "Home"}, "homeAway": "home", "score": "1"}]}]}


def make_fetch(summary, log=None):
    def fetch(url):
        if log is not None:
            log.append(url)
        if "scoreboard" in url:
            return {"events": [_event("1"), {**_event("2"), "status": {"type": {"completed": False}}}]}, {}
        return summary, {}
    return fetch


def test_backfill_stores_slim_record_and_reconciles(tmp_path):
    store = LocalStore(tmp_path)
    st = eb.backfill(store, "eng.1", date(2024, 1, 1), date(2024, 1, 1), make_fetch(_summary(5, 2)),
                     sleep=lambda s: None)
    assert st["listed"] == 1 and st["new"] == 1 and st["ok"] == 1   # unfinished match ignored
    assert store.exists("espn/matches/eng.1/1.json")


def test_mismatch_is_flagged_not_hidden(tmp_path):
    store = LocalStore(tmp_path)
    st = eb.backfill(store, "eng.1", date(2024, 1, 1), date(2024, 1, 1),
                     make_fetch(_summary(5, 2, boxscore_total=9)), sleep=lambda s: None)
    assert st["mismatch"] == 1


def test_resume_skips_saved_matches(tmp_path):
    store, log = LocalStore(tmp_path), []
    args = (store, "eng.1", date(2024, 1, 1), date(2024, 1, 1))
    eb.backfill(*args, make_fetch(_summary(3, 1)), sleep=lambda s: None)
    eb.backfill(*args, make_fetch(_summary(3, 1), log), sleep=lambda s: None)
    assert not any("summary" in u for u in log)


def test_window_rejected_falls_back_to_single_days(tmp_path):
    seen = []

    def fetch(url):
        seen.append(url)
        if "-" in url.split("dates=")[1].split("&")[0]:
            raise HttpStatus(400, url)
        return {"events": []}, {}

    eb.list_events("eng.1", date(2024, 1, 1), date(2024, 1, 3), 7, fetch, lambda s: None)
    singles = [u for u in seen if "-" not in u.split("dates=")[1].split("&")[0]]
    assert len(singles) == 3


def test_time_budget_stops_cleanly(tmp_path):
    ticks = chain([0], repeat(999999))
    st = eb.backfill(LocalStore(tmp_path), "eng.1", date(2024, 1, 1), date(2024, 1, 1),
                     make_fetch(_summary(3, 1)), sleep=lambda s: None, max_minutes=1,
                     clock=lambda: next(ticks))
    assert st["stopped_early"] is True and st["new"] == 0


def test_retry_bad_refetches_only_non_ok(tmp_path):
    store = LocalStore(tmp_path)
    args = (store, "eng.1", date(2024, 1, 1), date(2024, 1, 1))
    eb.backfill(*args, make_fetch(_summary(5, 2, boxscore_total=9)), sleep=lambda s: None)  # mismatch
    st = eb.backfill(*args, make_fetch(_summary(5, 2)), sleep=lambda s: None, retry_bad=True)
    assert st["new"] == 1 and st["ok"] == 1                                               # refetched, now ok
    log = []
    eb.backfill(*args, make_fetch(_summary(5, 2), log), sleep=lambda s: None, retry_bad=True)
    assert not any("summary" in u for u in log)                                           # ok -> not refetched


def test_mismatch_detail_names_teams_and_counts():
    shots = [{"team": "Home", "outcome": "saved", "on_target": True}]
    detail = []
    tot = {"Home": {"totalShots": "4", "shotsOnTarget": "2", "blockedShots": "1"}}
    assert eb.reconcile(shots, tot, detail) == "mismatch"
    assert "parsed total/on=(1, 1)" in detail[0] and "boxscore total/on=('4', '2')" in detail[0]
