"""Resumable ESPN backfill: scoreboard -> match summary -> parsed shots (raw JSON is not kept).

Stored per match (small): espn/matches/{league}/{event}.json containing the match header, boxscore
totals and the parsed shots, plus a coverage flag saying whether parsed shots reconcile with ESPN's
own boxscore totals. Unofficial endpoints: keep the pace polite.

Run: python -m pitchline.espn_backfill --league eng.1 --from 2023-08-01 --to 2024-06-01
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import date, datetime, timedelta

from .espn_shots import parse_shots
from .http import HttpStatus, get_json
from .storage import Store, get_store

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
log = logging.getLogger("pitchline.espn")


def _daterange(a: date, b: date, step: int):
    d = a
    while d <= b:
        yield d, min(d + timedelta(days=step - 1), b)
        d += timedelta(days=step)


def list_events(league: str, start: date, end: date, window: int, fetch, sleep) -> list[dict]:
    """Completed events in [start, end]. Falls back to single days if ESPN rejects the window."""
    events: dict[str, dict] = {}

    def pull(a: date, b: date):
        qs = a.strftime("%Y%m%d") if a == b else f"{a:%Y%m%d}-{b:%Y%m%d}"
        data, _ = fetch(f"{BASE}/{league}/scoreboard?dates={qs}&limit=300")
        for e in data.get("events", []):
            if e.get("status", {}).get("type", {}).get("completed"):
                events[e["id"]] = e

    for a, b in _daterange(start, end, window):
        try:
            pull(a, b)
        except HttpStatus as err:
            if err.status != 400 or a == b:
                raise
            log.warning("window %s..%s rejected; using single days", a, b)
            for d, _ in _daterange(a, b, 1):
                pull(d, d)
                sleep(1)
        sleep(1)
    return list(events.values())


def _totals(summary: dict) -> dict[str, dict]:
    out = {}
    for t in summary.get("boxscore", {}).get("teams", []):
        st = {s["name"]: s.get("displayValue") for s in t.get("statistics", [])}
        keys = ("totalShots", "shotsOnTarget", "blockedShots")
        out[t["team"]["displayName"]] = {k: st.get(k) for k in keys}
    return out


def _players(summary: dict) -> list[dict]:
    """ESPN's own per-player match stats (authoritative for shots / shots on target / goals / assists)."""
    out = []
    for r in summary.get("rosters", []):
        team = (r.get("team") or {}).get("displayName")
        for pl in r.get("roster", []):
            st = {s["name"]: s.get("value") for s in pl.get("stats", [])}
            row = {"team": team, "player": (pl.get("athlete") or {}).get("displayName"),
                   "shots": int(st.get("totalShots") or 0),
                   "shots_on_target": int(st.get("shotsOnTarget") or 0),
                   "goals": int(st.get("totalGoals") or 0), "assists": int(st.get("goalAssists") or 0),
                   "own_goals": int(st.get("ownGoals") or 0)}
            if any(row[k] for k in ("shots", "shots_on_target", "goals", "assists", "own_goals")):
                out.append(row)
    return out


def reconcile(shots: list[dict], totals: dict[str, dict], detail: list | None = None) -> str:
    """Strict check on TOTAL shots per team. On-target is deliberately not part of the check:
    ESPN counts some blocked shots as on target in its own stats while commentary only says 'blocked'."""
    if not totals or all(v["totalShots"] is None for v in totals.values()):
        return "no_boxscore"
    if not shots:
        return "no_commentary"
    status = "ok"
    teams_in_shots = sorted({s["team"] for s in shots if s["team"]})
    for team, tot in totals.items():
        mine = [s for s in shots if s["team"] == team and s["outcome"] != "own_goal"]
        if str(len(mine)) != str(tot["totalShots"]):
            status = "mismatch"
            if detail is not None:
                detail.append(f"{team}: parsed total={len(mine)} boxscore total={tot['totalShots']}"
                              f" shot-teams={teams_in_shots}")
    return status


def on_target_gap(shots: list[dict], totals: dict[str, dict]) -> int:
    """Boxscore on-target minus commentary on-target, summed over teams (informational)."""
    gap = 0
    for team, tot in totals.items():
        mine = [s for s in shots if s["team"] == team and s["outcome"] != "own_goal"]
        try:
            gap += int(tot["shotsOnTarget"]) - sum(1 for s in mine if s["on_target"])
        except (TypeError, ValueError):
            pass
    return gap


def process_event(store: Store, league: str, ev: dict, fetch, retry_bad: bool = False) -> str | None:
    key = f"espn/matches/{league}/{ev['id']}.json"
    if store.exists(key):
        if not retry_bad or json.loads(store.read_bytes(key)).get("coverage") == "ok":
            return None
    summary, _ = fetch(f"{BASE}/{league}/summary?event={ev['id']}")
    shots = parse_shots(summary, ev["id"], league)
    comp = ev["competitions"][0]
    rec = {
        "league": league, "event_id": ev["id"], "date": ev["date"],
        "season": (ev.get("season") or {}).get("year"),
        "teams": [{"name": c["team"]["displayName"], "home": c["homeAway"] == "home",
                   "score": c.get("score")} for c in comp["competitors"]],
        "boxscore_totals": _totals(summary), "shots": shots, "players": _players(summary),
    }
    rec["on_target_gap"] = on_target_gap(shots, rec["boxscore_totals"])
    detail: list[str] = []
    rec["coverage"] = reconcile(shots, rec["boxscore_totals"], detail)
    if rec["coverage"] != "ok":
        log.warning("event %s %s: %s | commentary entries=%d, shots parsed=%d | %s", ev["id"],
                    rec["coverage"], " / ".join(t["name"] for t in rec["teams"]),
                    len(summary.get("commentary", [])), len(shots), "; ".join(detail))
    store.write_bytes(key, json.dumps(rec).encode())
    return rec["coverage"]


def backfill(store: Store, league: str, start: date, end: date, fetch=None, sleep=time.sleep,
             window: int = 7, max_minutes: float = 300, clock=time.monotonic,
             retry_bad: bool = False) -> dict:
    fetch = fetch or (lambda url: get_json(url))
    t0 = clock()
    events = list_events(league, start, end, window, fetch, sleep)
    stats = {"listed": len(events), "new": 0, "skipped": 0, "failed": 0, "stopped_early": False}
    for ev in sorted(events, key=lambda e: e["date"]):
        if (clock() - t0) / 60 > max_minutes:
            stats["stopped_early"] = True
            break
        try:
            cov = process_event(store, league, ev, fetch, retry_bad)
        except Exception as err:  # one bad match must not stop the run
            log.error("event %s failed: %s", ev["id"], err)
            stats["failed"] += 1
            continue
        if cov is None:
            stats["skipped"] += 1
        else:
            stats["new"] += 1
            stats[cov] = stats.get(cov, 0) + 1
            sleep(1)
    log.info("%s %s..%s %s", league, start, end, stats)
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--league")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    ap.add_argument("--targets", help="YAML list of {league, from, to}; processed in order")
    ap.add_argument("--root")
    ap.add_argument("--window", type=int, default=7)
    ap.add_argument("--retry-bad", action="store_true",
                    help="re-download matches whose stored coverage is not 'ok'")
    ap.add_argument("--max-minutes", type=float, default=300)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parse = lambda s: datetime.strptime(s, "%Y-%m-%d").date()  # noqa: E731
    store = get_store(a.root)
    if a.targets:
        import yaml

        targets = yaml.safe_load(open(a.targets))["targets"]
    elif a.league and a.start and a.end:
        targets = [{"league": a.league, "from": a.start, "to": a.end}]
    else:
        ap.error("give --targets, or --league with --from and --to")
    t0, bad = time.monotonic(), False
    for t in targets:
        left = a.max_minutes - (time.monotonic() - t0) / 60
        if left <= 0:
            log.info("time budget used up; remaining targets run next time")
            break
        stats = backfill(store, t["league"], parse(str(t["from"])), parse(str(t["to"])),
                         window=a.window, max_minutes=left, retry_bad=a.retry_bad)
        bad = bad or bool(stats["failed"] and not stats["new"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
