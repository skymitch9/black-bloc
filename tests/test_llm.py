from types import SimpleNamespace

import pytest

from black_bloc import llm
from black_bloc.llm import (
    ANTHROPIC,
    BROKEN,
    GROQ,
    MAX_TOKENS,
    MODEL,
    PRICES,
    RATE_LIMITED,
    REFUSED,
    UNREACHABLE,
    HaikuClient,
    LLMError,
    Usage,
    cost_microdollars,
    price_for,
    record,
    text_of,
    usage_from,
)
from black_bloc.storage.db import Database


def block(text):
    return SimpleNamespace(type="text", text=text)


class FakeMessage:
    def __init__(self, text="Sure thing.", usage=None, model=MODEL):
        self.content = [block(text)]
        self.usage = usage
        self.model = model


class FakeUsage:
    def __init__(self, **fields):
        for name in (
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        ):
            setattr(self, name, fields.get(name, 0))


def calls_with(message=None, raises=None):
    seen = {}

    async def create(**kwargs):
        seen.update(kwargs)
        if raises is not None:
            raise raises
        return message or FakeMessage()

    return create, seen


def test_the_pinned_price_table_is_the_published_haiku_rate():
    price = PRICES[MODEL]
    assert (price.input, price.output) == (1.0, 5.0)
    assert (price.cache_write, price.cache_read) == (1.25, 0.10)


def test_a_token_at_a_dollar_a_million_costs_exactly_one_microdollar():
    assert cost_microdollars(ANTHROPIC, MODEL, Usage(input_tokens=1)) == 1
    assert cost_microdollars(ANTHROPIC, MODEL, Usage(output_tokens=1)) == 5
    spent = Usage(
        input_tokens=1000, output_tokens=200, cache_read_tokens=500, cache_write_tokens=100
    )
    assert cost_microdollars(ANTHROPIC, MODEL, spent) == round(1000 + 1000 + 50 + 125)


def test_the_free_groq_tier_costs_nothing_but_is_still_priced_by_the_table():
    assert cost_microdollars(GROQ, "llama-3.3-70b-versatile", Usage(input_tokens=9999)) == 0


def test_a_model_the_table_does_not_know_is_charged_as_its_provider_not_as_free():
    """Charging an unknown Anthropic model zero would hide real spend from the cap."""
    assert price_for(ANTHROPIC, "claude-something-new") == PRICES[MODEL]
    assert price_for(GROQ, "llama-99").input == 0.0


def test_usage_is_read_the_same_way_from_the_sdk_object_and_from_groqs_json():
    sdk = usage_from(
        FakeUsage(
            input_tokens=10,
            output_tokens=4,
            cache_read_input_tokens=2,
            cache_creation_input_tokens=1,
        )
    )
    assert sdk == Usage(input_tokens=10, output_tokens=4, cache_read_tokens=2, cache_write_tokens=1)
    web = usage_from({"prompt_tokens": 10, "completion_tokens": 4})
    assert web == Usage(input_tokens=10, output_tokens=4)
    assert usage_from(None) == Usage()


def test_a_usage_field_that_is_nonsense_reads_as_nothing_spent():
    assert usage_from({"prompt_tokens": "lots"}) == Usage()
    assert usage_from({"prompt_tokens": -5}) == Usage()


def test_only_text_blocks_become_the_answer():
    assert text_of([block("one"), SimpleNamespace(type="thinking"), block("two")]) == "one\ntwo"
    assert text_of(()) == ""
    assert text_of([{"type": "text", "text": "dict shaped"}]) == "dict shaped"


async def test_the_request_is_the_shape_the_design_pinned():
    create, seen = calls_with(FakeMessage("Hey."))
    client = HaikuClient("k", create=create)
    answer = await client.reply(
        system=[{"type": "text", "text": "core"}], messages=[{"role": "user", "content": "hi"}]
    )
    assert seen["model"] == MODEL
    assert seen["max_tokens"] == MAX_TOKENS
    assert "thinking" not in seen
    assert seen["system"] == [{"type": "text", "text": "core"}]
    assert answer.text == "Hey."
    assert answer.provider == ANTHROPIC


async def test_each_sdk_failure_keeps_its_own_reason_rather_than_one_broad_catch(monkeypatch):
    class Rate(Exception):
        pass

    class Status(Exception):
        status_code = 503

    class Connection(Exception):
        pass

    monkeypatch.setattr(llm, "_ERRORS", (Rate, Status, Connection))
    for error, reason in (
        (Rate(), RATE_LIMITED),
        (Status(), REFUSED),
        (Connection(), UNREACHABLE),
        (ValueError("odd"), BROKEN),
    ):
        create, _ = calls_with(raises=error)
        client = HaikuClient("k", create=create)
        with pytest.raises(LLMError) as caught:
            await client.reply(system=[], messages=[])
        assert caught.value.reason == reason


async def test_a_refusal_carries_the_status_it_answered_with(monkeypatch):
    class Rate(Exception):
        pass

    class Status(Exception):
        status_code = 400

    class Connection(Exception):
        pass

    monkeypatch.setattr(llm, "_ERRORS", (Rate, Status, Connection))
    create, _ = calls_with(raises=Status())
    with pytest.raises(LLMError) as caught:
        await HaikuClient("k", create=create).reply(system=[], messages=[])
    assert caught.value.status == 400


async def test_no_error_message_ever_carries_the_key(monkeypatch):
    class Rate(Exception):
        pass

    monkeypatch.setattr(llm, "_ERRORS", (Rate, Rate, Rate))
    create, _ = calls_with(raises=Rate("upstream said no"))
    with pytest.raises(LLMError) as caught:
        await HaikuClient("sk-ant-secret-value", create=create).reply(system=[], messages=[])
    assert "sk-ant-secret-value" not in str(caught.value)


async def ledger_rows(db):
    cur = await db.conn.execute("SELECT * FROM llm_ledger ORDER BY id")
    return list(await cur.fetchall())


async def test_every_call_writes_one_ledger_row_answered_or_not(tmp_path):
    db = Database(tmp_path / "l.sqlite3")
    await db.connect()
    try:
        await record(
            db,
            guild_id=7,
            user_id=900,
            turn="t1",
            provider=ANTHROPIC,
            model=MODEL,
            tier="important",
            usage=Usage(input_tokens=100, output_tokens=20),
        )
        await record(
            db,
            guild_id=7,
            user_id=900,
            turn="t2",
            provider=GROQ,
            model="llama-3.3-70b-versatile",
            tier="simple",
            outcome="error",
        )
        rows = await ledger_rows(db)
        assert [row["outcome"] for row in rows] == ["ok", "error"]
        assert rows[0]["cost_microdollars"] == 200
        assert rows[1]["cost_microdollars"] == 0
        assert rows[1]["input_tokens"] == 0
    finally:
        await db.close()


async def test_a_ledger_that_will_not_write_does_not_take_the_reply_down():
    class Broken:
        @property
        def conn(self):
            raise RuntimeError("no database")

    assert await record(
        Broken(),
        guild_id=7,
        user_id=900,
        turn="t",
        provider=ANTHROPIC,
        model=MODEL,
        tier="important",
    ) is None
