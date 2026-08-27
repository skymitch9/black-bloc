from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

log = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"
AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
TOKEN_URL = f"{DISCORD_API}/oauth2/token"
SCOPES = "identify guilds.members.read"
REQUEST_TIMEOUT_SECONDS = 15

SESSION_COOKIE = "__Host-bb_session"
STATE_COOKIE = "__Host-bb_state"
STATE_TTL_SECONDS = 600
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
LOGIN_RATE = 10
LOGIN_WINDOW_SECONDS = 60
BUCKET_MAX_KEYS = 4096

NOT_SIGNED_IN = (
    "You are not signed in, so there is nothing to show yet. Sign in with the Discord account "
    "you moderate Black in a Flash! with, and this page will fill in."
)
SESSION_EXPIRED = (
    "Your sign-in has expired — they last seven days. Nothing is wrong with your access; sign in "
    "with Discord again and you will be straight back in."
)
NOT_STAFF = (
    "This dashboard is for the mods and admins of Black in a Flash!. You are signed in, but your "
    "Discord account does not hold a staff role or Manage Server. Ask a Lead for the role, then "
    "sign in again."
)
STAFF_UNKNOWN = (
    "Black Bloc could not check your roles with Discord just now — nothing is wrong with your "
    "access; try again in a minute."
)
LOGIN_UNAVAILABLE = (
    "Signing in is not switched on for this server yet — the Discord application credentials have "
    "not been set. This is a setup step for the owner, not something you are missing. Tell a Lead "
    "that DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET and SESSION_SECRET need setting."
)
LOGIN_FAILED = (
    "Discord could not complete the sign-in, so nobody was signed in. This is a fault on the way "
    "to Discord and not a permission problem — try again in a moment."
)
SLOW_DOWN = (
    "That is more sign-in attempts than Black Bloc will take in a minute, so this one was not "
    "started. Nothing is wrong with your account — wait a minute and try again."
)
BAD_REQUEST = (
    "That request did not make sense to Black Bloc, so nothing was done. It is a fault in the "
    "link or the page rather than a problem with your access — start again from this page."
)


class OAuthError(RuntimeError):
    """Discord refused an OAuth request or answered with something unusable."""


class Refused(Exception):
    """An API request was refused; the site shows `message`, never the status."""

    def __init__(self, status: int, error: str, message: str) -> None:
        super().__init__(error)
        self.status = status
        self.error = error
        self.message = message


async def refused_handler(request: Request, exc: Refused) -> JSONResponse:
    return JSONResponse({"error": exc.error, "message": exc.message}, status_code=exc.status)


async def validation_handler(request: Request, exc: Exception) -> JSONResponse:
    """A malformed query string is a sentence, not FastAPI's `detail` list."""
    return JSONResponse({"error": "bad_request", "message": BAD_REQUEST}, status_code=400)


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_session(secret: str, payload: dict[str, Any]) -> str:
    """HMAC-SHA256 over the base64url payload; `<payload>.<mac>`."""
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    mac = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{mac}"


def read_session(
    secret: str, token: str | None, *, now: float | None = None
) -> tuple[str, dict[str, Any] | None]:
    """('ok', payload) / ('expired', None) / ('invalid', None)."""
    if not token or "." not in token:
        return ("invalid", None)
    body, _, mac = token.rpartition(".")
    try:
        signed, given = body.encode("ascii"), mac.encode("ascii")
    except UnicodeEncodeError:
        return ("invalid", None)
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(given, expected.encode("ascii")):
        return ("invalid", None)
    try:
        payload = json.loads(_b64d(body))
    except Exception:
        return ("invalid", None)
    if not isinstance(payload, dict):
        return ("invalid", None)
    expires = payload.get("exp")
    if not isinstance(expires, int | float) or isinstance(expires, bool):
        return ("invalid", None)
    if (time.time() if now is None else now) >= expires:
        return ("expired", None)
    return ("ok", payload)


def guild_of(bot: Any) -> Any:
    """The one guild this site is about: DEV_GUILD_ID, else the only guild there is."""
    guild_id = getattr(bot.settings, "dev_guild_id", None)
    if guild_id:
        found = bot.get_guild(guild_id)
        if found is not None:
            return found
    guilds = list(getattr(bot, "guilds", ()) or ())
    return guilds[0] if len(guilds) == 1 else None


def role_ids_from(member_payload: dict[str, Any]) -> set[int]:
    found: set[int] = set()
    for raw in member_payload.get("roles") or ():
        try:
            found.add(int(raw))
        except (TypeError, ValueError):
            continue
    return found


def is_admitted(guild: Any, store: Any, user_id: int, role_ids: set[int]) -> bool:
    """Staff role or Manage Server, decided against the bot's cached guild."""
    if guild is None:
        return False
    member = guild.get_member(user_id)
    if member is not None:
        return bool(store.is_staff(member))
    if getattr(guild, "owner_id", None) == user_id:
        return True
    staff_ids = store.staff_role_ids(guild)
    if role_ids & staff_ids:
        return True
    for role_id in role_ids:
        role = guild.get_role(role_id)
        perms = getattr(role, "permissions", None)
        if perms is not None and getattr(perms, "manage_guild", False):
            return True
    return False


def live_staff(bot: Any, user_id: int, recorded: bool) -> tuple[bool, bool]:
    """(staff, known). `known` is False only when the guild cannot be consulted."""
    if not bot.is_ready():
        return (recorded, False)
    guild = guild_of(bot)
    if guild is None:
        return (recorded, False)
    member = guild.get_member(user_id)
    if member is None:
        return (False, True)
    return (bool(bot.store.is_staff(member)), True)


def current_session(request: Request, bot: Any) -> dict[str, Any]:
    secret = bot.settings.session_secret
    if not secret:
        raise Refused(503, "login_unavailable", LOGIN_UNAVAILABLE)
    state, payload = read_session(secret, request.cookies.get(SESSION_COOKIE))
    if state == "expired":
        raise Refused(401, "session_expired", SESSION_EXPIRED)
    if state != "ok" or payload is None:
        raise Refused(401, "not_signed_in", NOT_SIGNED_IN)
    try:
        user_id = int(payload["uid"])
    except (KeyError, TypeError, ValueError):
        raise Refused(401, "not_signed_in", NOT_SIGNED_IN) from None
    staff, known = live_staff(bot, user_id, bool(payload.get("staff")))
    return {
        "id": str(user_id),
        "name": str(payload.get("name") or ""),
        "avatar": payload.get("avatar"),
        "staff": staff,
        "staff_known": known,
    }


def session_dependency(bot: Any):
    async def dependency(request: Request) -> dict[str, Any]:
        return current_session(request, bot)

    return dependency


def staff_state(who: dict[str, Any]) -> str:
    if not who["staff_known"]:
        return "staff_unknown"
    return "staff" if who["staff"] else "not_staff"


def staff_dependency(bot: Any):
    async def dependency(request: Request) -> dict[str, Any]:
        who = current_session(request, bot)
        state = staff_state(who)
        if state == "staff_unknown":
            raise Refused(503, "staff_unknown", STAFF_UNKNOWN)
        if state == "not_staff":
            raise Refused(403, "not_staff", NOT_STAFF)
        return who

    return dependency


def cookie_kwargs(settings: Any) -> dict[str, Any]:
    return {
        "httponly": True,
        "samesite": settings.session_cookie_samesite,
        "secure": settings.origin.lower().startswith("https"),
        "path": "/",
    }


class DiscordOAuth:
    def __init__(
        self, client_id: str, client_secret: str, redirect_uri: str, *, request: Any = None
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._request = request or self._aiohttp_request
        self._session: Any = None

    async def _aiohttp_request(
        self, method: str, url: str, *, headers: Any = None, data: Any = None
    ) -> tuple[int, dict[str, Any]]:
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            )
        try:
            async with self._session.request(method, url, headers=headers, data=data) as response:
                try:
                    payload = await response.json(content_type=None)
                except Exception:
                    payload = {}
                return response.status, payload if isinstance(payload, dict) else {}
        except (TimeoutError, aiohttp.ClientError, OSError) as exc:
            raise OAuthError(f"discord unreachable: {type(exc).__name__}: {exc}") from exc

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def exchange(self, code: str) -> str:
        status, payload = await self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
        )
        token = payload.get("access_token")
        if status != 200 or not token:
            raise OAuthError(f"Discord refused the code exchange ({status})")
        return str(token)

    async def _bearer(self, path: str, token: str) -> tuple[int, dict[str, Any]]:
        return await self._request(
            "GET", f"{DISCORD_API}{path}", headers={"Authorization": f"Bearer {token}"}
        )

    async def identity(self, token: str) -> dict[str, Any]:
        status, payload = await self._bearer("/users/@me", token)
        if status != 200 or not payload.get("id"):
            raise OAuthError(f"Discord refused /users/@me ({status})")
        return payload

    async def guild_member(self, token: str, guild_id: int) -> dict[str, Any] | None:
        status, payload = await self._bearer(f"/users/@me/guilds/{guild_id}/member", token)
        if status in (403, 404):
            return None
        if status != 200:
            raise OAuthError(f"Discord refused the guild member lookup ({status})")
        return payload


def client_ip(request: Request) -> str:
    """Fly's own header first; it is the one the proxy sets and a caller cannot forge."""
    for header in ("fly-client-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return getattr(request.client, "host", None) or "unknown"


class TokenBucket:
    """LOGIN_RATE attempts a minute per client IP, refilled continuously."""

    def __init__(self, limit: int = LOGIN_RATE, window: float = LOGIN_WINDOW_SECONDS) -> None:
        self.limit = limit
        self.window = window
        self._seen: dict[str, tuple[float, float]] = {}

    def take(self, key: str, *, now: float | None = None) -> bool:
        at = time.time() if now is None else now
        tokens, stamp = self._seen.pop(key, (float(self.limit), at))
        tokens = min(float(self.limit), tokens + (at - stamp) * self.limit / self.window)
        allowed = tokens >= 1
        self._seen[key] = (tokens - 1 if allowed else tokens, at)
        while len(self._seen) > BUCKET_MAX_KEYS:
            del self._seen[next(iter(self._seen))]
        return allowed


def state_matches(given: str | None, expected: str | None) -> bool:
    if not given or not expected:
        return False
    try:
        return hmac.compare_digest(given, expected)
    except TypeError:
        return False


def display_name(identity: dict[str, Any]) -> str:
    return str(
        identity.get("global_name") or identity.get("username") or identity.get("id") or "someone"
    )


def build_router(bot: Any, *, oauth_request: Any = None) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])
    settings = bot.settings
    attempts = TokenBucket()

    def _rate_limit(request: Request) -> None:
        who = client_ip(request)
        if not attempts.take(who):
            log.warning("auth: rate-limited %s", who)
            raise Refused(429, "slow_down", SLOW_DOWN)

    def _client() -> DiscordOAuth:
        return DiscordOAuth(
            str(settings.discord_client_id),
            str(settings.discord_client_secret),
            settings.oauth_redirect_uri,
            request=oauth_request,
        )

    def _home(outcome: str) -> RedirectResponse:
        return RedirectResponse(f"{settings.origin}/?signin={outcome}", status_code=303)

    @router.get("/login")
    async def login(request: Request) -> Any:
        _rate_limit(request)
        if not settings.site_login_configured:
            raise Refused(503, "login_unavailable", LOGIN_UNAVAILABLE)
        state = secrets.token_urlsafe(24)
        query = urlencode(
            {
                "client_id": settings.discord_client_id,
                "redirect_uri": settings.oauth_redirect_uri,
                "response_type": "code",
                "scope": SCOPES,
                "state": state,
                "prompt": "none",
            }
        )
        response = RedirectResponse(f"{AUTHORIZE_URL}?{query}", status_code=303)
        response.set_cookie(
            STATE_COOKIE, state, max_age=STATE_TTL_SECONDS, **cookie_kwargs(settings)
        )
        return response

    @router.get("/callback")
    async def callback(
        request: Request,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ) -> Any:
        _rate_limit(request)
        if not settings.site_login_configured:
            raise Refused(503, "login_unavailable", LOGIN_UNAVAILABLE)
        if error or not code:
            return _home("denied")
        if not state_matches(state, request.cookies.get(STATE_COOKIE)):
            log.warning("auth: callback rejected — the state cookie did not match")
            rejected = _home("state")
            rejected.delete_cookie(STATE_COOKIE, **cookie_kwargs(settings))
            return rejected

        client = _client()
        member: dict[str, Any] | None = None
        try:
            token = await client.exchange(code)
            identity = await client.identity(token)
            guild = guild_of(bot)
            guild_id = getattr(guild, "id", None) or settings.dev_guild_id
            if guild_id:
                try:
                    member = await client.guild_member(token, guild_id)
                except OAuthError as exc:
                    log.warning("auth: the guild member lookup failed — %s", exc)
        except OAuthError as exc:
            log.warning("auth: sign-in failed — %s", exc)
            return _home("failed")
        finally:
            await client.close()

        user_id = int(identity["id"])
        staff = (
            is_admitted(guild, bot.store, user_id, role_ids_from(member))
            if member is not None
            else False
        )
        payload = {
            "uid": str(user_id),
            "name": display_name(identity),
            "avatar": identity.get("avatar"),
            "staff": staff,
            "exp": int(time.time()) + SESSION_TTL_SECONDS,
        }
        log.info("auth: signed in %s (staff=%s)", user_id, staff)
        response = _home("ok")
        response.set_cookie(
            SESSION_COOKIE,
            sign_session(str(settings.session_secret), payload),
            max_age=SESSION_TTL_SECONDS,
            **cookie_kwargs(settings),
        )
        response.delete_cookie(STATE_COOKIE, **cookie_kwargs(settings))
        return response

    @router.post("/logout")
    async def logout() -> Any:
        response = JSONResponse({"ok": True})
        response.delete_cookie(SESSION_COOKIE, **cookie_kwargs(settings))
        return response

    @router.get("/me")
    async def me(request: Request) -> dict[str, Any]:
        who = current_session(request, bot)
        guild = guild_of(bot)
        state = staff_state(who)
        return {
            "user": {"id": who["id"], "name": who["name"], "avatar": who["avatar"]},
            "staff": state == "staff",
            "state": state,
            "guild": {"id": str(guild.id), "name": guild.name} if guild is not None else None,
            "message": {"staff": None, "not_staff": NOT_STAFF, "staff_unknown": STAFF_UNKNOWN}[
                state
            ],
        }

    return router


__all__ = [
    "NOT_STAFF",
    "SESSION_COOKIE",
    "SLOW_DOWN",
    "STAFF_UNKNOWN",
    "STATE_COOKIE",
    "DiscordOAuth",
    "OAuthError",
    "Refused",
    "TokenBucket",
    "build_router",
    "client_ip",
    "current_session",
    "guild_of",
    "is_admitted",
    "live_staff",
    "read_session",
    "refused_handler",
    "session_dependency",
    "sign_session",
    "staff_dependency",
    "state_matches",
    "validation_handler",
]
