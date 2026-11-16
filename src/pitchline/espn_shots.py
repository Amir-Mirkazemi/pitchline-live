"""Parse ESPN match-summary commentary into one clean row per shot.

Source: https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/summary?event=ID
(unofficial endpoint). Every shot-like commentary entry carries a structured
``play`` object with type, team, participants (shooter first, assister second)
and pitch coordinates, so the parser relies on structure first and uses the
free text only for body part, situation and cross detection.
"""
from __future__ import annotations

import re
from typing import Any

# ESPN play type text -> (outcome, on_target)
SHOT_TYPES: dict[str, tuple[str, bool]] = {
    "Shot Off Target": ("off_target", False),
    "Shot Blocked": ("blocked", False),
    "Shot On Target": ("saved", True),
    "Shot Hit Woodwork": ("woodwork", False),
    "Goal": ("goal", True),
    "Goal - Header": ("goal", True),
    "Goal - Free-kick": ("goal", True),
    "Penalty - Scored": ("goal", True),
    "Penalty - Saved": ("saved", True),
    "Penalty - Missed": ("off_target", False),
    "Own Goal": ("own_goal", False),
}

# Some shot lines carry another play type (e.g. a direct free-kick attempt is typed "Free Kick"),
# so lines are also classified by their text prefix.
_TEXT_PREFIX: list[tuple[str, tuple[str, bool]]] = [
    ("Attempt missed", ("off_target", False)),
    ("Attempt saved", ("saved", True)),
    ("Attempt blocked", ("blocked", False)),
    ("Penalty saved", ("saved", True)),
    ("Penalty missed", ("off_target", False)),
]

_BODY = [
    ("header", re.compile(r"\bheader\b", re.I)),
    ("right_foot", re.compile(r"right footed", re.I)),
    ("left_foot", re.compile(r"left footed", re.I)),
]
_ZONE = re.compile(
    r"from (?:the )?((?:very )?close range"
    r"|(?:the )?(?:centre|right|left)(?: side)? of the (?:six yard box|box)"
    r"|(?:a )?difficult angle(?: and long range| on the (?:right|left))?|outside the box|long range"
    r"|more than 35 yards|the (?:right|left) wing|very close range)",
    re.I,
)
_CROSS = re.compile(r"with a cross", re.I)
_THROUGH = re.compile(r"through ball", re.I)


def _situation(play_type: str, text: str) -> str:
    if play_type.startswith("Penalty") or text.startswith("Penalty") or "converts the penalty" in text:
        return "penalty"
    if play_type == "Goal - Free-kick" or "free kick" in text.lower():
        return "free_kick"
    if "following a corner" in text.lower():
        return "from_corner"
    return "open_play"


# A structured "shot" play whose text is not about a shot is an ESPN data glitch
# (seen: play typed "Shot On Target" with the text "Foul by ... (Sunderland)."). Such plays are rejected.
_SHOT_WORDS = ("attempt", "goal", "penalty", "hits the", "converts", "header", "shot")


def looks_like_shot(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in _SHOT_WORDS)


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().replace("&", "and"))


_TEXT_SHOT = re.compile(r"^(?:Attempt|Penalty) (missed|saved|blocked)\. (.+?) \((.+?)\) ")
_ASSIST = re.compile(r"Assisted by (.+?)(?: with | following |\.|$)")
_TEXT_OUTCOME = {"missed": ("off_target", False), "saved": ("saved", True), "blocked": ("blocked", False)}


def _text_only_shot(entry: dict, team_names: dict[str, str], event_id: str, league: str) -> dict | None:
    """Shots that ESPN publishes as plain commentary text with no structured `play` (no coordinates)."""
    text = entry.get("text") or ""
    m = _TEXT_SHOT.match(text)
    if not m:
        return None
    kind, player, team_txt = m.groups()
    team = team_names.get(_norm(team_txt))
    if team is None:
        return None
    outcome, on_target = _TEXT_OUTCOME[kind]
    body = next((n for n, rx in _BODY if rx.search(text)), "other")
    zone = _ZONE.search(text)
    assist = _ASSIST.search(text)
    t = entry.get("time") or {}
    return {
        "league": league, "event_id": str(event_id), "play_id": f"text:{entry.get('sequence')}",
        "period": None, "seconds": t.get("value"), "wallclock": None, "team": team, "player": player,
        "assist_player": assist.group(1) if assist else None, "outcome": outcome, "on_target": on_target,
        "is_goal": False, "body_part": body, "situation": _situation("", text),
        "assist_is_cross": bool(_CROSS.search(text)), "assist_is_through_ball": bool(_THROUGH.search(text)),
        "zone_text": zone.group(1).lower() if zone else None, "x": None, "y": None, "goal_y": None,
        "has_location": False, "raw_text": text,
    }


def parse_shots(summary: dict[str, Any], event_id: str, league: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    team_names = {_norm(t["team"]["displayName"]): t["team"]["displayName"]
                  for t in summary.get("boxscore", {}).get("teams", []) if t.get("team")}
    for entry in summary.get("commentary", []):
        play = entry.get("play")
        if not play:
            extra = _text_only_shot(entry, team_names, event_id, league)
            if extra:
                rows.append(extra)
            continue
        ptype = play.get("type", {}).get("text")
        text = play.get("text") or entry.get("text") or ""
        if ptype in SHOT_TYPES:
            if not looks_like_shot(text):
                continue
            outcome, on_target = SHOT_TYPES[ptype]
        else:
            hit = next((v for p, v in _TEXT_PREFIX if text.startswith(p)), None)
            if hit is None:
                continue
            outcome, on_target = hit
        parts = [p["athlete"]["displayName"] for p in play.get("participants", []) if p.get("athlete")]
        body = next((n for n, rx in _BODY if rx.search(text)), "other")
        zone = _ZONE.search(text)
        rows.append(
            {
                "league": league,
                "event_id": str(event_id),
                "play_id": str(play["id"]),
                "period": (play.get("period") or {}).get("number"),
                "seconds": (play.get("clock") or {}).get("value"),
                "wallclock": play.get("wallclock"),
                "team": (play.get("team") or {}).get("displayName"),
                "player": parts[0] if parts else None,
                "assist_player": parts[1] if len(parts) > 1 and outcome != "own_goal" else None,
                "outcome": outcome,
                "on_target": on_target,
                "is_goal": outcome == "goal",
                "body_part": body,
                "situation": _situation(ptype, text),
                "assist_is_cross": bool(_CROSS.search(text)),
                "assist_is_through_ball": bool(_THROUGH.search(text)),
                "zone_text": zone.group(1).lower() if zone else None,
                "x": play.get("fieldPositionX"),
                "y": play.get("fieldPositionY"),
                "goal_y": play.get("goalPositionY"),
                "has_location": play.get("fieldPositionX") is not None,
                "raw_text": text,
            }
        )
    return rows
