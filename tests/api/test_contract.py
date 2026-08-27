from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from discord.ext import tasks

from black_bloc.api.settings_api import grouped
from black_bloc.cogs.community.birthdays import save_birthday
from black_bloc.cogs.community.events import create_event
from black_bloc.cogs.community.tempvoice import add_channel
from black_bloc.cogs.content.golive import set_link, set_optout, start_session
from black_bloc.cogs.moderation.honeypot import record_hit
from black_bloc.cogs.moderation.modmail import add_message, create_ticket, set_ticket_place
from black_bloc.golive import StreamInfo
from black_bloc.modcases import add_case
from black_bloc.modmail import IN

CONTRACT = Path(__file__).resolve().parents[2] / "site" / "mock" / "contract.json"
MEMBER_ID = 21


class FakeCog:
    """One loop-bearing cog, because /api/status reports nothing without one."""

    @tasks.loop(minutes=5)
    async def _sweep(self) -> None:
        return None

    def loop_health(self, name: str):
        return (datetime.now(UTC).isoformat(), None)


def contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


ROUTES = contract()["routes"]
IDS = [f"{route['method']} {route['path']}" for route in ROUTES]


def missing(found: dict, keys: list[str]) -> list[str]:
    return [key for key in keys if key not in found]


def check_rows(where: str, rows: list, keys: list[str], *, allow_empty: bool = False) -> None:
    assert isinstance(rows, list), f"{where} is {type(rows).__name__}, not a list"
    if not rows:
        assert allow_empty, f"{where} came back empty, so its row shape was never checked"
        return
    for row in rows:
        assert not missing(row, keys), f"{where} row is missing {missing(row, keys)}"


def check(where: str, payload, spec: dict) -> None:
    keys = spec.get("keys", [])
    shape = spec["shape"]
    if shape == "list":
        check_rows(where, payload, keys)
    elif shape == "map":
        assert isinstance(payload, dict) and payload, f"{where} came back empty"
        for value in payload.values():
            assert not missing(value, keys), f"{where} entry is missing {missing(value, keys)}"
    elif shape == "namespaces":
        assert isinstance(payload, dict)
        for namespace in spec["namespaces"]:
            assert namespace in payload, f"{where} has no {namespace} namespace"
            check_rows(f"{where}[{namespace}]", payload[namespace], keys)
        for namespace in spec["no_namespaces"]:
            assert namespace not in payload, (
                f"{where} still groups {namespace} on its own; it belongs in automod"
            )
    else:
        assert isinstance(payload, dict), f"{where} is {type(payload).__name__}, not an object"
        assert not missing(payload, keys), f"{where} is missing {missing(payload, keys)}"
    for field, row_keys in (spec.get("rows") or {}).items():
        if shape == "list":
            for row in payload:
                check_rows(f"{where}.{field}", row[field], row_keys)
        else:
            check_rows(f"{where}.{field}", payload[field], row_keys)
    for field, nested_keys in (spec.get("nested") or {}).items():
        found = payload[field]
        assert isinstance(found, dict), f"{where}.{field} is not an object"
        assert not missing(found, nested_keys), (
            f"{where}.{field} is missing {missing(found, nested_keys)}"
        )


@pytest.fixture
async def seeded(client, sign_in, web, guild, wf):
    """One of everything the contract's routes read, so no route answers empty."""
    wf.member(guild, MEMBER_ID, name="ada")
    wf.member(guild, 7, name="lead", staff=True)
    sign_in(client)
    db, guild_id = web.db, wf.GUILD_ID

    web.cogs["Contract"] = FakeCog()
    await web.store.set(guild_id, "events_create_scheduled", False, by=7)
    await web.store.set(guild_id, "rolemenu_mode", "on", by=7)

    case_id = await add_case(
        db,
        guild_id,
        MEMBER_ID,
        "warn",
        moderator_id=7,
        reason="contract seed",
        mode="shadow",
        applied=False,
        actions=["warn"],
    )
    starts = datetime.now(UTC) + timedelta(days=1)
    event_id = await create_event(
        db,
        guild_id,
        MEMBER_ID,
        title="Bloc night",
        description="come along",
        location="the park",
        starts_at=starts,
        finishes_at=starts + timedelta(hours=2),
    )
    ticket_id = await create_ticket(db, guild_id, MEMBER_ID, "channel")
    await set_ticket_place(db, ticket_id, wf.TEST_CHANNEL_ID, None)
    await add_message(db, ticket_id, MEMBER_ID, IN, content="are you there?")
    hit_id = await record_hit(
        db, guild_id, MEMBER_ID, wf.OTHER_CHANNEL_ID, 999, "buy my coins", "shadow", "would_ban"
    )
    await set_link(db, MEMBER_ID, "adastreams", "t-1")
    await set_optout(db, MEMBER_ID)
    await start_session(
        db,
        guild_id,
        MEMBER_ID,
        "presence",
        StreamInfo(url="https://twitch.tv/ada", game="Balatro", title="one more"),
        "on",
    )
    await save_birthday(db, guild_id, MEMBER_ID, 3, 4, None, "staff")
    await add_channel(db, wf.VOICE_CHANNEL_ID, guild_id, MEMBER_ID, wf.OTHER_CHANNEL_ID)
    client.post(
        "/api/rolemenus",
        json={"name": "contract", "title": "Contract", "mode": "multiple"},
    )
    client.put(
        "/api/rolemenus/contract",
        json={
            "title": "Contract",
            "mode": "multiple",
            "options": [{"role_id": str(wf.PLAIN_ROLE_ID), "label": "Member"}],
        },
    )
    client.post("/api/modmail/snippets", json={"name": "contract", "content": "hello"})
    client.post("/api/modmail/blocks", json={"user_id": str(MEMBER_ID)})
    return {
        "member_id": str(MEMBER_ID),
        "case_id": str(case_id),
        "event_id": str(event_id),
        "ticket_id": str(ticket_id),
        "hit_id": str(hit_id),
        "test_channel_id": str(wf.TEST_CHANNEL_ID),
    }


def fill(text: str, ids: dict) -> str:
    for name, value in ids.items():
        text = text.replace("{" + name + "}", value)
    return text


@pytest.mark.parametrize("spec", ROUTES, ids=IDS)
async def test_every_route_answers_with_the_keys_the_pages_read(client, seeded, spec):
    path = fill(spec["path"], seeded)
    body = spec.get("body")
    if isinstance(body, dict):
        body = json.loads(fill(json.dumps(body), seeded))
    response = client.request(spec["method"], path, json=body)
    where = f"{spec['method']} {path}"
    assert response.status_code == 200, f"{where} answered {response.status_code}: {response.text}"
    check(where, response.json(), spec)


def test_the_moderation_settings_all_live_in_the_automod_namespace(web, wf):
    """modlog and mod were one-key namespaces of their own; they are moderation keys."""
    found = grouped(web.store, wf.GUILD_ID)
    automod = {row["key"] for row in found["automod"]}

    assert {"modlog_channel_id", "mod_dm_on_action"} <= automod
    assert not {"modlog", "mod"} & set(found)


async def test_every_write_leaves_the_action_kind_the_audit_tab_filters_on(
    client, seeded, web, wf
):
    """The audit tab shows `web.` and nothing else, so every write route must spell it that way."""
    client.put("/api/settings/birthday_show_age", json={"value": True})
    client.post("/api/mod/warn", json={"user_id": seeded["member_id"], "reason": "contract"})
    client.post("/api/modmail/snippets", json={"name": "second", "content": "hi"})

    kinds = [kind for kind in await wf.kinds_in(web.db) if kind.startswith("web")]

    assert kinds, "no write left a web.* line at all"
    known = set(contract()["action_kinds"])
    assert all(kind.startswith("web.") for kind in kinds), kinds
    assert set(kinds) <= known, f"unlisted kinds: {sorted(set(kinds) - known)}"
