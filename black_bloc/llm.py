from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)

IMPORTANT = "important"
SIMPLE = "simple"
TIERS: tuple[str, ...] = (IMPORTANT, SIMPLE)

ANTHROPIC = "anthropic"
GROQ = "groq"

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 400
REQUEST_TIMEOUT_SECONDS = 20.0
MAX_RETRIES = 1

OK = "ok"
ERROR = "error"

RATE_LIMITED = "rate_limited"
REFUSED = "refused"
UNREACHABLE = "unreachable"
BROKEN = "broken"


@dataclass(frozen=True)
class Price:
    """Dollars per million tokens, pinned here rather than fetched."""

    input: float
    output: float
    cache_write: float = 0.0
    cache_read: float = 0.0


PRICES: dict[str, Price] = {
    "claude-haiku-4-5": Price(input=1.0, output=5.0, cache_write=1.25, cache_read=0.10),
    "llama-3.3-70b-versatile": Price(input=0.0, output=0.0),
    "openai/gpt-oss-120b": Price(input=0.0, output=0.0),
}

UNKNOWN_PRICE: dict[str, Price] = {
    ANTHROPIC: PRICES["claude-haiku-4-5"],
    GROQ: Price(input=0.0, output=0.0),
}


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class Reply:
    text: str
    provider: str
    model: str
    usage: Usage


class LLMError(RuntimeError):
    """A model tier could not answer; `reason` says which kind of failure it was."""

    def __init__(self, reason: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.status = status


def price_for(provider: str, model: str) -> Price:
    found = PRICES.get(str(model))
    if found is not None:
        return found
    fallback = UNKNOWN_PRICE.get(str(provider), Price(input=0.0, output=0.0))
    log.warning("llm: %s is not in the price table, charging it as %s", model, provider)
    return fallback


def cost_microdollars(provider: str, model: str, usage: Usage) -> int:
    """A token at $1/MTok is exactly one microdollar, so the sum is the price table times tokens."""
    price = price_for(provider, model)
    return round(
        usage.input_tokens * price.input
        + usage.output_tokens * price.output
        + usage.cache_write_tokens * price.cache_write
        + usage.cache_read_tokens * price.cache_read
    )


def whole(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def field(payload: Any, *names: str) -> Any:
    for name in names:
        found = payload.get(name) if isinstance(payload, dict) else getattr(payload, name, None)
        if found is not None:
            return found
    return None


def usage_from(payload: Any) -> Usage:
    """The SDK's usage object and Groq's JSON, read the one way."""
    if payload is None:
        return Usage()
    return Usage(
        input_tokens=whole(field(payload, "input_tokens", "prompt_tokens")),
        output_tokens=whole(field(payload, "output_tokens", "completion_tokens")),
        cache_read_tokens=whole(field(payload, "cache_read_input_tokens")),
        cache_write_tokens=whole(field(payload, "cache_creation_input_tokens")),
    )


def text_of(content: Any) -> str:
    found: list[str] = []
    for block in content or ():
        kind = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
        if kind != "text":
            continue
        said = block.get("text") if isinstance(block, dict) else getattr(block, "text", "")
        if said:
            found.append(str(said))
    return "\n".join(found).strip()


async def record(
    db: Any,
    *,
    guild_id: int | None,
    user_id: int | None,
    turn: str,
    provider: str,
    model: str,
    tier: str,
    outcome: str = OK,
    usage: Usage | None = None,
    at: datetime | None = None,
    trope: str | None = None,
) -> int | None:
    """One ledger row per model call, answered or not. Never raises into a reply."""
    spent = usage or Usage()
    try:
        cur = await db.conn.execute(
            "INSERT INTO llm_ledger(at, guild_id, user_id, turn, provider, model, tier, outcome, "
            "input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, "
            "cost_microdollars, trope) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (at or datetime.now(UTC)).isoformat(),
                None if guild_id is None else int(guild_id),
                None if user_id is None else int(user_id),
                str(turn),
                str(provider),
                str(model),
                str(tier),
                str(outcome),
                spent.input_tokens,
                spent.output_tokens,
                spent.cache_read_tokens,
                spent.cache_write_tokens,
                cost_microdollars(provider, model, spent),
                trope,
            ),
        )
        await db.conn.commit()
    except Exception as exc:
        log.warning("llm: the ledger row was not written — %s: %s", type(exc).__name__, exc)
        return None
    return int(cur.lastrowid)


_ERRORS: tuple[type[BaseException], ...] | None = None


class _NeverRaised(Exception):
    """Stands in for an SDK exception class when the SDK is not installed."""


def sdk_errors() -> tuple[type[BaseException], ...]:
    global _ERRORS
    if _ERRORS is None:
        try:
            from anthropic import APIConnectionError, APIStatusError, RateLimitError
        except Exception:
            _ERRORS = (_NeverRaised, _NeverRaised, _NeverRaised)
        else:
            _ERRORS = (RateLimitError, APIStatusError, APIConnectionError)
    return _ERRORS


def build_create(api_key: str, *, timeout: float, retries: int) -> Any:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=retries)
    return client.messages.create, client


class HaikuClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = MODEL,
        max_tokens: int = MAX_TOKENS,
        create: Any = None,
    ) -> None:
        self.model = str(model)
        self.max_tokens = int(max_tokens)
        self._key = str(api_key)
        self._create = create
        self._client: Any = None

    def _ready(self) -> Any:
        if self._create is None:
            self._create, self._client = build_create(
                self._key, timeout=REQUEST_TIMEOUT_SECONDS, retries=MAX_RETRIES
            )
        return self._create

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            except Exception as exc:
                log.debug("llm: the client did not close cleanly — %s", exc)
        self._client = None

    async def reply(self, *, system: Any, messages: Any) -> Reply:
        rate_limited, refused, unreachable = sdk_errors()
        create = self._ready()
        try:
            message = await create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=list(system),
                messages=list(messages),
            )
        except rate_limited as exc:
            raise LLMError(RATE_LIMITED, f"anthropic is rate limiting: {exc}") from exc
        except refused as exc:
            status = getattr(exc, "status_code", None)
            raise LLMError(REFUSED, f"anthropic answered {status}", status=status) from exc
        except unreachable as exc:
            raise LLMError(UNREACHABLE, f"anthropic unreachable: {exc}") from exc
        except Exception as exc:
            raise LLMError(BROKEN, f"anthropic call failed: {type(exc).__name__}") from exc
        return Reply(
            text=text_of(getattr(message, "content", ())),
            provider=ANTHROPIC,
            model=str(getattr(message, "model", None) or self.model),
            usage=usage_from(getattr(message, "usage", None)),
        )
