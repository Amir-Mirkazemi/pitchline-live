"""Player leaderboards from the match files stored by the ESPN backfill.

Shots on Target uses ESPN's own per-player match stats (stored under ``players`` in each match file),
because ESPN counts some blocked shots as on target and the commentary cannot reproduce that.
"Matches" counts only matches where ESPN recorded at least one shot, goal or assist for the player (ESPN's
roster stats are stored for non-zero players only), so it is NOT an appearance count.
Players are keyed by (league, name); ESPN athlete ids are not stored yet, so two different players
with an identical name in one league would be merged (rare, documented in the README).
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict

from .storage import Store, get_store

PREFIX = "espn/matches/"


def load_totals(store: Store, league: str | None = None) -> tuple[dict, dict]:
    """Return (players, coverage). players[(league, name)] -> running totals; coverage[league] -> counts."""
    players: dict[tuple[str, str], dict] = {}
    coverage: dict[str, dict] = defaultdict(lambda: {"matches": 0, "ok": 0})
    prefix = PREFIX + (f"{league}/" if league else "")
    recs = []
    for key in store.list_keys(prefix):
        if not key.endswith(".json"):
            continue
        rec = json.loads(store.read_bytes(key))
        recs.append(rec)
    for rec in sorted(recs, key=lambda r: r.get("date") or ""):  # oldest first, so "team" ends as the latest
        lg = rec["league"]
        coverage[lg]["matches"] += 1
        coverage[lg]["ok"] += rec.get("coverage") == "ok"
        for p in rec.get("players", []):
            row = players.setdefault((lg, p["player"]), {
                "league": lg, "player": p["player"], "team": p["team"], "matches": 0,
                "shots": 0, "shots_on_target": 0, "goals": 0, "assists": 0})
            row["team"] = p["team"]
            row["matches"] += 1
            for k in ("shots", "shots_on_target", "goals", "assists"):
                row[k] += int(p.get(k) or 0)
    return players, dict(coverage)


def top(players: dict, league: str, n: int = 10, key: str = "shots_on_target") -> list[dict]:
    rows = [r for r in players.values() if r["league"] == league]
    return sorted(rows, key=lambda r: (-r[key], -r["shots"], r["player"]))[:n]


def markdown(players: dict, coverage: dict, n: int = 10) -> str:
    out = []
    for lg in sorted(coverage):
        c = coverage[lg]
        out.append(f"### {lg}: top {n} by shots on target "
                   f"({c['matches']} matches stored, {c['ok']} reconcile on total shots)\n")
        out.append("| # | Player | Team | Matches with a stat | Shots | On target | Goals | Assists |")
        out.append("|--:|---|---|--:|--:|--:|--:|--:|")
        for i, r in enumerate(top(players, lg, n), 1):
            out.append(f"| {i} | {r['player']} | {r['team']} | {r['matches']} | {r['shots']} | "
                       f"{r['shots_on_target']} | {r['goals']} | {r['assists']} |")
        out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root")
    ap.add_argument("--league")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args(argv)
    players, coverage = load_totals(get_store(a.root), a.league)
    text = markdown(players, coverage, a.top) if coverage else "No matches stored yet."
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:  # shows the tables on the workflow run page
        with open(summary, "a") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
