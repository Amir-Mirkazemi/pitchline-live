from pitchline.espn_shots import parse_shots


def _play(ptype, text, parts, x=90.0, y=50.0):
    return {
        "text": text,
        "play": {
            "id": "1", "type": {"text": ptype}, "text": text, "period": {"number": 1},
            "clock": {"value": 210.0}, "team": {"displayName": "Home"},
            "participants": [{"athlete": {"displayName": p}} for p in parts],
            "fieldPositionX": x, "fieldPositionY": y, "goalPositionY": 50.0,
        },
    }


def test_assisted_header_off_target():
    s = {"commentary": [_play("Shot Off Target",
        "Attempt missed. A B (Home) header from the left side of the six yard box is too high. Assisted by C D.",
        ["A B", "C D"])]}
    r = parse_shots(s, "9", "eng.1")[0]
    assert (r["player"], r["assist_player"], r["body_part"], r["outcome"]) == ("A B", "C D", "header", "off_target")
    assert r["zone_text"] == "left side of the six yard box"
    assert r["on_target"] is False


def test_penalty_goal_has_no_assister():
    s = {"commentary": [_play("Penalty - Scored",
        "Goal! Home 2, Away 0. P G (Home) converts the penalty with a right footed shot to the top right corner.", ["P G"])]}
    r = parse_shots(s, "9", "eng.1")[0]
    assert r["situation"] == "penalty" and r["is_goal"] and r["on_target"] and r["assist_player"] is None


def test_cross_after_corner():
    s = {"commentary": [_play("Goal - Header",
        "Goal! A 0, B 2. M B (B) header from the centre of the box to the bottom left corner. Assisted by D C with a cross following a corner.",
        ["M B", "D C"])]}
    r = parse_shots(s, "9", "esp.1")[0]
    assert r["assist_is_cross"] and r["situation"] == "from_corner" and r["body_part"] == "header"


def test_own_goal_never_credits_assist_and_non_shots_ignored():
    s = {"commentary": [
        _play("Own Goal", "Own Goal by X Y, Lazio. Napoli 1, Lazio 1.", ["X Y"]),
        _play("Foul", "Foul by someone.", ["S"]),
        {"text": "no play object"},
    ]}
    rows = parse_shots(s, "9", "ita.1")
    assert len(rows) == 1 and rows[0]["outcome"] == "own_goal" and rows[0]["on_target"] is False


def test_direct_free_kick_attempt_typed_free_kick_is_still_a_shot():
    line = ("Attempt missed. M D (Brentford) right footed shot from outside the box "
            "is too high from a direct free kick.")
    s = {"commentary": [_play("Free Kick", line, ["M D"])]}
    r = parse_shots(s, "9", "eng.1")[0]
    assert r["outcome"] == "off_target" and r["player"] == "M D" and r["situation"] == "free_kick"


def test_non_shot_free_kick_lines_are_ignored():
    s = {"commentary": [_play("Free Kick", "Free kick awarded to Home.", ["X"])]}
    assert parse_shots(s, "9", "eng.1") == []
