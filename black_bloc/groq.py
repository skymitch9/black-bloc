from __future__ import annotations

import logging
from typing import Any

from .llm import (
    BROKEN,
    GROQ,
    MAX_TOKENS,
    RATE_LIMITED,
    REFUSED,
    UNREACHABLE,
    LLMError,
    Reply,
    usage_from,
)

log = logging.getLogger(__name__)

CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
REQUEST_TIMEOUT_SECONDS = 15
TOO_MANY = 429
SERVER_TROUBLE = 500
JSON_OBJECT = {"type": "json_object"}


def message_text(payload: Any) -> str:
    choices = payload.get("choices") if isinstance(payload, dict) else None
    for choice in choices or ():
        if not isinstance(choice, dict):
            continue
        said = (choice.get("message") or {}).get("content")
        if said:
            return str(said).strip()
    return ""


class GroqClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = MAX_TOKENS,
        request: Any = None,
    ) -> None:
        self.model = str(model or DEFAULT_MODEL)
        self.max_tokens = int(max_tokens)
        self._key = str(api_key)
        self._request = request or self._aiohttp_request
        self._session: Any = None

    async def _aiohttp_request(self, url: str, *, headers: Any, json: Any) -> tuple[int, Any]:
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            )
        try:
            async with self._session.post(url, headers=headers, json=json) as response:
                try:
                    payload = await response.json(content_type=None)
                except Exception:
                    payload = {}
                return response.status, payload if isinstance(payload, dict) else {}
        except (TimeoutError, aiohttp.ClientError, OSError) as exc:
            raise LLMError(UNREACHABLE, f"groq unreachable: {type(exc).__name__}") from exc

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def reply(self, *, system: Any, messages: Any, json_only: bool = False) -> Reply:
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "system", "content": str(system)}, *list(messages)],
        }
        if json_only:
            body["response_format"] = JSON_OBJECT
        try:
            status, payload = await self._request(
                CHAT_URL,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(BROKEN, f"groq call failed: {type(exc).__name__}") from exc
        if status == TOO_MANY:
            raise LLMError(RATE_LIMITED, "groq is rate limiting", status=status)
        if status != 200:
            reason = UNREACHABLE if status >= SERVER_TROUBLE else REFUSED
            raise LLMError(reason, f"groq answered {status}", status=status)
        said = message_text(payload)
        if not said:
            raise LLMError(BROKEN, "groq answered with no words in it", status=status)
        return Reply(
            text=said,
            provider=GROQ,
            model=str(payload.get("model") or self.model),
            usage=usage_from(payload.get("usage")),
        )
