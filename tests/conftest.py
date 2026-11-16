import pytest
import requests


class FakeResponse:
    def __init__(self, payload=None, status=200, bad_json=False):
        self._payload, self.status_code, self._bad = payload, status, bad_json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        if self._bad:
            raise ValueError("bad json")
        return self._payload


class FakeSession:
    """Serves canned responses by URL suffix; a list means 'one item per call'."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, timeout=None):
        self.calls.append(url)
        for suffix, resp in self.routes.items():
            if url.endswith(suffix):
                if isinstance(resp, list):
                    item = resp.pop(0) if len(resp) > 1 else resp[0]
                else:
                    item = resp
                if isinstance(item, Exception):
                    raise item
                return item
        return FakeResponse(status=404)


def make_match(match_id=1, home=("10", "Aland"), away=("20", "Borduria"), hs=1, as_=0):
    return {
        "match_id": match_id, "match_date": "2024-06-01", "kick_off": "18:00:00.000",
        "competition": {"competition_id": 99, "competition_name": "Test Cup"},
        "season": {"season_id": 1, "season_name": "2024"},
        "competition_stage": {"name": "Final"},
        "home_team": {"home_team_id": int(home[0]), "home_team_name": home[1]},
        "away_team": {"away_team_id": int(away[0]), "away_team_name": away[1]},
        "home_score": hs, "away_score": as_, "stadium": {"name": "Arena"},
        "referee": {"name": "R. Ref"}, "match_status": "available",
    }


def make_events():
    t10 = {"id": 10, "name": "Aland"}
    return [
        {"id": "e0", "index": 1, "period": 1, "minute": 0, "second": 0, "type": {"name": "Starting XI"},
         "team": t10, "tactics": {"lineup": [{"player": {"id": 1, "name": "Ann"}},
                                              {"player": {"id": 2, "name": "Bea"}}]}},
        {"id": "e1", "index": 2, "period": 1, "minute": 5, "second": 1, "type": {"name": "Pass"},
         "team": t10, "player": {"id": 1, "name": "Ann"}, "position": {"name": "Left Wing"},
         "location": [60.0, 30.0],
         "pass": {"recipient": {"id": 2, "name": "Bea"}, "length": 20.0, "end_location": [80.0, 35.0],
                  "shot_assist": True}},
        {"id": "e2", "index": 3, "period": 1, "minute": 5, "second": 4, "type": {"name": "Shot"},
         "team": t10, "player": {"id": 2, "name": "Bea"}, "location": [100.0, 38.0],
         "shot": {"statsbomb_xg": 0.31, "outcome": {"name": "Goal"}, "key_pass_id": "e1",
                  "end_location": [120.0, 40.0, 1.0], "type": {"name": "Open Play"},
                  "body_part": {"name": "Right Foot"}}},
        {"id": "e3", "index": 4, "period": 2, "minute": 60, "second": 0, "type": {"name": "Substitution"},
         "team": t10, "player": {"id": 1, "name": "Ann"},
         "substitution": {"replacement": {"id": 3, "name": "Cal"}}},
    ]


@pytest.fixture
def match_list():
    return [make_match(1), make_match(2)]
