from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from ..chat_llm import MICRODOLLARS_IN_A_DOLLAR, month_start
from ..config import Settings
from ..llm import ANTHROPIC, GROQ, OK
from .auth import staff_dependency
from .writes import require_db, require_guild

log = logging.getLogger(__name__)

HOSTING_KEY = "cost_hosting_usd"

SECRET_ENDINGS: tuple[str, ...] = ("_token", "_secret", "_key", "_client_id")
SECRET_NOTES: dict[str, str] = {
    "discord_token": "the bot's own login. Without it Black Bloc does not start at all.",
    "discord_client_id": "the dashboard's sign-in. Without it nobody can sign in to this site.",
    "discord_client_secret": "the other half of the dashboard sign-in.",
    "session_secret": "signs the sign-in cookie. Changing it signs everybody out.",
    "twitch_client_id": "reads Twitch for go-live posts. Free; unset means presence only.",
    "twitch_client_secret": "the other half of the Twitch app.",
    "youtube_api_key": (
        "sorts a new upload into video, Short or live stream, and turns an @handle into a "
        "channel id. Free within a daily quota; unset leaves uploads on the public feed alone."
    ),
    "poll_vote_secret": "keys anonymous poll votes. Unset falls back to a plain hash.",
    "anthropic_api_key": "pays for the careful chat tier. Unset means that tier does not exist.",
    "groq_api_key": "the free chat tier. Unset means that tier does not exist.",
}
SECRET_UNKNOWN = "no note has been written for this one yet."

PROVIDER_LABELS: dict[str, str] = {ANTHROPIC: "Anthropic", GROQ: "Groq"}

HOSTING_NAME = "Hosting — the always-on container"
HOSTING_WORD = "${amount} a month, as somebody typed it in off the invoice."
HOSTING_BLANK = (
    "Nobody has filled this in yet, so the total below is only what the models have cost. "
    "Read the monthly figure off your Fly invoice and put it in `cost_hosting_usd`."
)
FREE_ITEMS: tuple[tuple[str, str], ...] = (
    ("Discord", "The gateway, the API and the slash commands are free at any size this bot is."),
    ("Twitch API", "Helix costs nothing for the go-live checks Black Bloc makes."),
    (
        "Groq — the quick chat tier",
        "Free while their tier is. Every call is still written to the ledger with its real "
        "token counts, so the day it is not free the figure is already there.",
    ),
)

MONTH_WORD = "{spent} on models so far this month."
MONTH_NOTHING = "No model has been asked anything this month, so the models have cost nothing."
PRIOR_WORD = "{spent} on models in {month}."
PRIOR_NOTHING = "Nothing was spent on models in {month}."
TOTAL_WORD = "{total} this month: {models} on models and {hosting} on hosting."
TOTAL_NO_HOSTING = "{models} this month, all of it models — hosting has not been filled in."
MODEL_WORD = "{turns} answer(s), {tokens} tokens, {spent}."
MODEL_FREE = "{turns} answer(s), {tokens} tokens, free at this tier."

NO_LEDGER = (
    "Black Bloc has never called a model, so there is nothing on the models line yet. That is "
    "what an unspent month looks like, not a fault."
)


def money(value: Any) -> str:
    return f"${float(value or 0):.2f}"


def in_dollars(microdollars: Any) -> float:
    return round(int(microdollars or 0) / MICRODOLLARS_IN_A_DOLLAR, 2)


def prior_month_start(now: datetime) -> str:
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year = first.year - 1 if first.month == 1 else first.year
    month = 12 if first.month == 1 else first.month - 1
    return first.replace(year=year, month=month).isoformat()


def month_name(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%B %Y")
    except (TypeError, ValueError):
        return "the month before"


def secret_names() -> list[str]:
    """Derived from `config.py`'s own fields, so a new secret cannot be forgotten here."""
    return [name for name in Settings.model_fields if name.endswith(SECRET_ENDINGS)]


def secret_rows(settings: Any) -> list[dict[str, Any]]:
    """Names and set/unset. ⚠️ A value is never read out of the settings object."""
    return [
        {
            "name": name.upper(),
            "set": bool(getattr(settings, name, None)),
            "what": SECRET_NOTES.get(name, SECRET_UNKNOWN),
        }
        for name in secret_names()
    ]


async def spent_by_model(db: Any, since: str, until: str | None = None) -> list[dict[str, Any]]:
    """One row per provider, model and tier that has ever answered in the window."""
    where = "at >= ?" + (" AND at < ?" if until else "")
    args: tuple[Any, ...] = (since, until) if until else (since,)
    try:
        cur = await db.conn.execute(
            "SELECT provider, model, tier, COUNT(DISTINCT turn) AS turns, COUNT(*) AS calls, "
            "SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens, "
            "SUM(cache_read_tokens) AS cache_read_tokens, "
            "SUM(cache_write_tokens) AS cache_write_tokens, "
            "SUM(cost_microdollars) AS spent FROM llm_ledger "
            f"WHERE {where} AND outcome = ? GROUP BY provider, model, tier "
            "ORDER BY spent DESC, provider, model",
            (*args, OK),
        )
        rows = list(await cur.fetchall())
    except Exception as exc:
        log.warning("costs: the ledger was not read — %s: %s", type(exc).__name__, exc)
        return []
    return [dict(row) for row in rows]


def model_row(row: dict[str, Any], prior: dict[tuple[str, str, str], int]) -> dict[str, Any]:
    spent = in_dollars(row.get("spent"))
    tokens = int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0)
    key = (str(row["provider"]), str(row["model"]), str(row["tier"]))
    said = (MODEL_FREE if spent == 0 else MODEL_WORD).format(
        turns=int(row.get("turns") or 0), tokens=tokens, spent=money(spent)
    )
    return {
        "provider": str(row["provider"]),
        "provider_label": PROVIDER_LABELS.get(str(row["provider"]), str(row["provider"])),
        "model": str(row["model"]),
        "tier": str(row["tier"]),
        "turns": int(row.get("turns") or 0),
        "calls": int(row.get("calls") or 0),
        "input_tokens": int(row.get("input_tokens") or 0),
        "output_tokens": int(row.get("output_tokens") or 0),
        "cache_read_tokens": int(row.get("cache_read_tokens") or 0),
        "cache_write_tokens": int(row.get("cache_write_tokens") or 0),
        "spent_usd": spent,
        "prior_usd": in_dollars(prior.get(key)),
        "word": said,
    }


def hosting_row(amount: int) -> dict[str, Any]:
    return {
        "name": HOSTING_NAME,
        "kind": "configured",
        "amount_usd": float(amount),
        "key": HOSTING_KEY,
        "word": HOSTING_BLANK if amount <= 0 else HOSTING_WORD.format(amount=amount),
    }


def cost_items(amount: int) -> list[dict[str, Any]]:
    """Hosting, then the things that genuinely cost nothing — named, not left out."""
    return [
        hosting_row(amount),
        *(
            {"name": name, "kind": "free", "amount_usd": 0.0, "key": None, "word": said}
            for name, said in FREE_ITEMS
        ),
    ]


def build_router(bot: Any) -> APIRouter:
    from .writes import reader_dependency

    reader = reader_dependency(bot)
    router = APIRouter(
        prefix="/api", tags=["costs"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/costs", dependencies=[Depends(reader)])
    async def costs() -> dict[str, Any]:
        """Every dollar Black Bloc costs, in one place: measured, configured or free."""
        guild = require_guild(bot)
        db = require_db(bot)
        at = datetime.now(UTC)
        this_month, last_month = month_start(at), prior_month_start(at)

        rows = await spent_by_model(db, this_month)
        was = await spent_by_model(db, last_month, this_month)
        prior = {(r["provider"], r["model"], r["tier"]): r.get("spent") for r in was}
        models = [model_row(row, prior) for row in rows]

        spent_usd = round(sum(row["spent_usd"] for row in models), 2)
        prior_usd = round(sum(in_dollars(row.get("spent")) for row in was), 2)
        hosting = int(bot.store.get(guild.id, HOSTING_KEY) or 0)
        total_usd = round(spent_usd + hosting, 2)

        notes = [] if models or was else [NO_LEDGER]
        return {
            "month": {
                "from": this_month,
                "spent_usd": spent_usd,
                "word": (
                    MONTH_NOTHING if not models else MONTH_WORD.format(spent=money(spent_usd))
                ),
            },
            "prior": {
                "from": last_month,
                "to": this_month,
                "spent_usd": prior_usd,
                "word": (PRIOR_NOTHING if not was else PRIOR_WORD).format(
                    spent=money(prior_usd), month=month_name(last_month)
                ),
            },
            "models": models,
            "items": cost_items(hosting),
            "total": {
                "month_usd": total_usd,
                "models_usd": spent_usd,
                "hosting_usd": float(hosting),
                "word": (
                    TOTAL_NO_HOSTING.format(models=money(spent_usd))
                    if hosting <= 0
                    else TOTAL_WORD.format(
                        total=money(total_usd),
                        models=money(spent_usd),
                        hosting=money(hosting),
                    )
                ),
            },
            "secrets": secret_rows(bot.settings),
            "hosting_key": HOSTING_KEY,
            "notes": notes,
            "checked_at": at.isoformat(),
        }

    return router
