import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent / "sports" / "fixtures"

RECORDED_ROUTES: dict[str, str] = {
    "basketball/nba/teams?": "espn_teams_nba",
    "mens-college-basketball/teams?": "espn_teams_ncaam",
    "/roster": "espn_roster_nba",
    "basketball/nba/scoreboard": "espn_scoreboard_nba",
    "schools-index": "henrygd_schools",
    "playerindex": "nba_playerindex",
    "statsapi.mlb.com/api/v1/teams": "mlb_teams",
    "sports/1/players": "mlb_players",
}


def payload(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def body(name: str) -> bytes:
    return (FIXTURES / f"{name}.json").read_bytes()


class Recorded:
    """A sports `fetch` answering from the trimmed fixtures by URL part; anything else is 404."""

    def __init__(self, routes: dict[str, Any] | None = None) -> None:
        self.routes = dict(RECORDED_ROUTES if routes is None else routes)
        self.asked: list[tuple[str, dict[str, str]]] = []

    async def __call__(self, url: str, headers: dict[str, str], seconds: int) -> tuple[int, bytes]:
        self.asked.append((url, dict(headers)))
        for part, answer in self.routes.items():
            if part not in url:
                continue
            if isinstance(answer, BaseException):
                raise answer
            if isinstance(answer, tuple):
                return answer
            if isinstance(answer, (dict, list)):
                return 200, json.dumps(answer).encode("utf-8")
            return 200, body(answer)
        return 404, b""

    def urls(self) -> list[str]:
        return [url for url, _ in self.asked]
