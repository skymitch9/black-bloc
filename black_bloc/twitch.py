from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
HELIX_URL = "https://api.twitch.tv/helix"
BATCH_SIZE = 100
REQUEST_TIMEOUT_SECONDS = 15


class TwitchError(RuntimeError):
    """Twitch refused a request or answered with something unusable."""


@dataclass(frozen=True)
class TwitchStream:
    user_id: str
    user_login: str
    user_name: str
    game_name: str
    title: str
    started_at: str

    @property
    def url(self) -> str:
        return f"https://www.twitch.tv/{self.user_login}"


@dataclass(frozen=True)
class TwitchUser:
    id: str
    login: str
    display_name: str


def batches(logins: Any, size: int = BATCH_SIZE) -> list[list[str]]:
    ordered = [str(login).lower() for login in logins]
    return [ordered[i : i + size] for i in range(0, len(ordered), size)]


def stream_from(row: dict[str, Any]) -> TwitchStream:
    return TwitchStream(
        user_id=str(row.get("user_id") or ""),
        user_login=str(row.get("user_login") or "").lower(),
        user_name=str(row.get("user_name") or ""),
        game_name=str(row.get("game_name") or ""),
        title=str(row.get("title") or ""),
        started_at=str(row.get("started_at") or ""),
    )


def user_from(row: dict[str, Any]) -> TwitchUser:
    return TwitchUser(
        id=str(row.get("id") or ""),
        login=str(row.get("login") or "").lower(),
        display_name=str(row.get("display_name") or ""),
    )


class TwitchClient:
    def __init__(self, client_id: str, client_secret: str, *, request: Any = None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._request = request or self._aiohttp_request
        self._session: Any = None
        self._token: str | None = None

    async def _aiohttp_request(
        self,
        method: str,
        url: str,
        *,
        headers: Any = None,
        params: Any = None,
        data: Any = None,
    ) -> tuple[int, dict[str, Any]]:
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            )
        try:
            async with self._session.request(
                method, url, headers=headers, params=params, data=data
            ) as response:
                try:
                    payload = await response.json(content_type=None)
                except Exception:
                    payload = {}
                return response.status, payload if isinstance(payload, dict) else {}
        except (TimeoutError, aiohttp.ClientError, OSError) as exc:
            raise TwitchError(f"twitch unreachable: {type(exc).__name__}: {exc}") from exc

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def token(self) -> str:
        if self._token is None:
            self._token = await self._fetch_token()
        return self._token

    async def _fetch_token(self) -> str:
        status, payload = await self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        )
        access = payload.get("access_token")
        if status != 200 or not access:
            raise TwitchError(
                f"Twitch refused the app token ({status}); check TWITCH_CLIENT_ID and "
                "TWITCH_CLIENT_SECRET."
            )
        log.info("twitch: app token obtained")
        return str(access)

    async def _get(self, path: str, params: list[tuple[str, str]]) -> list[dict[str, Any]]:
        status, payload = await self._call(path, params, await self.token())
        if status == 401:
            self._token = None
            status, payload = await self._call(path, params, await self.token())
        if status != 200:
            raise TwitchError(f"Twitch answered {status} for {path}")
        data = payload.get("data") or []
        return [row for row in data if isinstance(row, dict)]

    async def _call(
        self, path: str, params: list[tuple[str, str]], token: str
    ) -> tuple[int, dict[str, Any]]:
        return await self._request(
            "GET",
            f"{HELIX_URL}/{path}",
            headers={"Client-Id": self.client_id, "Authorization": f"Bearer {token}"},
            params=params,
        )

    async def get_streams(self, logins: Any) -> list[TwitchStream]:
        """Live streams for these logins; offline logins are simply absent."""
        found: list[TwitchStream] = []
        for chunk in batches(logins):
            rows = await self._get("streams", [("user_login", login) for login in chunk])
            found.extend(stream_from(row) for row in rows)
        return found

    async def get_users(self, logins: Any) -> list[TwitchUser]:
        found: list[TwitchUser] = []
        for chunk in batches(logins):
            rows = await self._get("users", [("login", login) for login in chunk])
            found.extend(user_from(row) for row in rows)
        return found
