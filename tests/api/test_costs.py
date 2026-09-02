from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from black_bloc.api.costs import (
    HOSTING_KEY,
    SECRET_NOTES,
    prior_month_start,
    secret_names,
    secret_rows,
)
from black_bloc.config import Settings
from black_bloc.llm import ANTHROPIC, GROQ, IMPORTANT, MODEL, OK, SIMPLE, Usage, record

GROQ_MODEL = "llama-3.3-70b-versatile"


async def spend(db, *, provider, model, tier, at, turn, usage, outcome=OK):
    await record(
        db,
        guild_id=4242,
        user_id=21,
        turn=turn,
        provider=provider,
        model=model,
        tier=tier,
        outcome=outcome,
        usage=usage,
        at=at,
    )


@pytest.fixture
async def spent(web):
    """One month-to-date Haiku turn, one free Groq turn, and one from the month before."""
    now = datetime.now(UTC)
    this_month = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
    last_month = this_month - timedelta(days=1)
    await spend(
        web.db,
        provider=ANTHROPIC,
        model=MODEL,
        tier=IMPORTANT,
        at=this_month,
        turn="a",
        usage=Usage(input_tokens=1000, output_tokens=200),
    )
    await spend(
        web.db,
        provider=GROQ,
        model=GROQ_MODEL,
        tier=SIMPLE,
        at=this_month,
        turn="b",
        usage=Usage(input_tokens=500, output_tokens=100),
    )
    await spend(
        web.db,
        provider=ANTHROPIC,
        model=MODEL,
        tier=IMPORTANT,
        at=last_month,
        turn="c",
        usage=Usage(input_tokens=4000, output_tokens=400),
    )
    return web


async def test_the_month_to_date_figure_is_the_ledger_summed_not_a_counter(
    client, sign_in, spent
):
    sign_in(client)

    body = client.get("/api/costs").json()

    # 1000 input + 200 output at $1/$5 per MTok = 1000 + 1000 microdollars.
    assert body["month"]["spent_usd"] == 0.0
    assert [row["model"] for row in body["models"]] == [MODEL, GROQ_MODEL]
    haiku = body["models"][0]
    assert haiku["turns"] == 1 and haiku["input_tokens"] == 1000
    assert haiku["prior_usd"] == 0.01


async def test_a_groq_row_is_shown_at_zero_dollars_rather_than_left_out(client, sign_in, spent):
    sign_in(client)

    rows = client.get("/api/costs").json()["models"]
    quick = next(row for row in rows if row["provider"] == GROQ)

    assert quick["spent_usd"] == 0.0
    assert quick["output_tokens"] == 100
    assert "free" in quick["word"]


async def test_the_month_before_is_counted_on_its_own_and_not_folded_into_this_one(
    client, sign_in, spent
):
    sign_in(client)

    body = client.get("/api/costs").json()

    assert body["prior"]["spent_usd"] == 0.01
    assert body["prior"]["from"] == prior_month_start(datetime.now(UTC))
    assert body["prior"]["to"] == body["month"]["from"]


async def test_a_call_that_failed_is_not_charged_to_the_month(client, sign_in, web):
    await spend(
        web.db,
        provider=ANTHROPIC,
        model=MODEL,
        tier=IMPORTANT,
        at=datetime.now(UTC),
        turn="d",
        usage=Usage(input_tokens=9_000_000, output_tokens=0),
        outcome="error",
    )
    sign_in(client)

    body = client.get("/api/costs").json()

    assert body["models"] == []
    assert body["month"]["spent_usd"] == 0.0


async def test_hosting_at_zero_says_it_is_unfilled_rather_than_claiming_it_is_free(
    client, sign_in, web
):
    sign_in(client)

    body = client.get("/api/costs").json()
    hosting = body["items"][0]

    assert hosting["key"] == HOSTING_KEY and hosting["amount_usd"] == 0.0
    assert "nobody has filled this in yet" in hosting["word"].lower()
    assert "hosting has not been filled in" in body["total"]["word"]
    # One home: the unfilled fact is the hosting row's own sentence, not a second note as well.
    assert not [said for said in body["notes"] if "invoice" in said]


async def test_the_configured_hosting_figure_joins_the_total(client, sign_in, web, wf):
    await web.store.set(wf.GUILD_ID, HOSTING_KEY, 12, by=7)
    sign_in(client)

    body = client.get("/api/costs").json()

    assert body["items"][0]["amount_usd"] == 12.0
    assert body["total"]["hosting_usd"] == 12.0
    assert body["total"]["month_usd"] == 12.0
    assert "$12.00 on hosting" in body["total"]["word"]


async def test_the_free_things_are_named_at_zero_rather_than_left_off_the_page(
    client, sign_in, web
):
    sign_in(client)

    items = client.get("/api/costs").json()["items"]
    free = [row for row in items if row["kind"] == "free"]

    assert {row["name"] for row in free} >= {"Discord", "Twitch API"}
    assert all(row["amount_usd"] == 0.0 and row["word"] for row in free)


def test_the_secret_inventory_is_derived_from_config_so_a_new_one_cannot_be_forgotten():
    assert set(secret_names()) == {
        name
        for name in Settings.model_fields
        if name.endswith(("_token", "_secret", "_key", "_client_id"))
    }
    assert set(SECRET_NOTES) == set(secret_names())


async def test_the_inventory_says_set_or_unset_and_never_a_value(client, sign_in, web):
    sign_in(client)

    rows = client.get("/api/costs").json()["secrets"]
    by_name = {row["name"]: row for row in rows}

    assert by_name["DISCORD_CLIENT_SECRET"]["set"] is True
    assert by_name["ANTHROPIC_API_KEY"]["set"] is False
    said = str(rows)
    assert "client-secret" not in said and web.settings.session_secret not in said
    assert all(set(row) == {"name", "set", "what"} for row in rows)


def test_a_secret_never_reaches_the_row_even_when_the_settings_object_holds_one():
    rows = secret_rows(
        Settings(_env_file=None, discord_token="hunter2", groq_api_key="gsk-live")
    )
    assert "hunter2" not in str(rows) and "gsk-live" not in str(rows)
    assert {row["name"]: row["set"] for row in rows}["DISCORD_TOKEN"] is True


async def test_a_member_who_is_not_staff_is_refused_in_words(client, sign_in):
    sign_in(client, uid=21, staff=False)

    response = client.get("/api/costs")

    assert response.status_code == 403
    assert "staff" in response.json()["message"].lower()


async def test_an_unspent_month_says_so_rather_than_looking_broken(client, sign_in):
    sign_in(client)

    body = client.get("/api/costs").json()

    assert body["models"] == []
    assert "never called a model" in " ".join(body["notes"])
    assert body["month"]["word"] and body["prior"]["word"]
