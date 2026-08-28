# Phase 4 design — events: form → review channel → Scheduled Event → go-live ping (F4 + F5)

> **Audience:** the Phase 4 build agent and the reviewer. **Status:** LOCAL
> ONLY. **Last verified: 2026-08-26** — owner decisions dated in `TODO.md`;
> Discord constraints from `reference-bots.md` §"Discord platform notes"
> (modal input cap is ambiguous between 5 and a newer 40-component scheme —
> **design to 5, verify against discord.py at build time**). Depends on
> Phase 1 (settings, action log, staff derivation).

## Owner decisions this implements

- `/event create` opens a **Discord modal**.
- Timezone cannot be auto-detected (Discord exposes no tz) → `/timezone set`
  once, city autocomplete, **default America/Phoenix**.
- Review = **one channel per submission** under an **Events** category,
  named `<status>-<user>-<event>` (`pending-sky-block-party` →
  `approved-…` / `denied-…`).
- **Approvers = anyone who can see the staff channel** (Phase 1
  `staff_role_ids`).
- On approve: **create a real Discord Scheduled Event — toggle, default ON**;
  announce with `<t:…>` stamps.
- Go-live ping: post in **`#live-now`** (setting), **role ping is a setting,
  default none** (F14 later).
- Future (not this phase): add the requester to their channel / ticket page;
  site settings.

## Shape

```
black_bloc/
├── timezones.py                 ← per-user tz store + `/timezone` cog helpers (pure: parse, convert, autocomplete list)
├── events.py                    ← pure logic: slugify channel names, parse "date time" in a tz → aware datetime, render cards
└── cogs/community/events.py     ← the cog: modal, review channels, buttons, scheduled-event creation, go-live task
tests/ test_timezones.py · test_events.py · cogs/community/test_events.py
```

Schema v5 (additive):

```sql
CREATE TABLE IF NOT EXISTS user_timezones (user_id INTEGER PRIMARY KEY, tz TEXT NOT NULL, set_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, requester_id INTEGER NOT NULL,
    title TEXT NOT NULL, description TEXT, location TEXT,
    starts_at TEXT NOT NULL, ends_at TEXT,                       -- ISO-8601 UTC
    status TEXT NOT NULL DEFAULT 'pending',                      -- pending | approved | denied | live | done | cancelled
    review_channel_id INTEGER, review_message_id INTEGER,
    scheduled_event_id INTEGER, announce_message_id INTEGER,
    decided_by INTEGER, decided_at TEXT, deny_reason TEXT,
    created_at TEXT NOT NULL
);
```

Settings keys: `events_category_id` (the *Events* category; while TEST_MODE
the test channel's category), `events_announce_channel_id` (default
`#live-now` `1225457308230746202`; test channel while TEST_MODE),
`events_ping_role_id` (none), `events_create_scheduled` (bool, **true**),
`events_mode` (`off|shadow|on`, default `on` — the flow is all staff-gated,
nothing punishes; shadow only suppresses the public announcement).

## The flow

1. **`/event create`** (anyone with `Member`): modal with 5 inputs — *Title*
   (≤100), *Description* (paragraph, ≤1000), *Start* (`YYYY-MM-DD HH:MM`,
   interpreted in the requester's tz; validation error → ephemeral sentence
   with an example), *Duration* (`1h30m`, default 2h), *Location or link*.
   No stream/voice picker in the modal (cap); location text is enough for
   v1. Result: `events` row `pending`; a channel
   `pending-<slug(user)>-<slug(title)>` (Discord rules: lowercase, `a-z0-9-`,
   ≤100 chars, collapse dashes) created in `events_category_id` with
   overwrites: staff roles view+send, requester **not** added (future ask),
   `@everyone` denied; the bot posts the **review card** there (embed:
   title, requester, `<t:start:F>` + `<t:start:R>`, duration, location,
   description) with **Approve** / **Deny** buttons (persistent view,
   `custom_id="event:<id>:approve|deny"`). Requester gets an ephemeral
   "submitted — mods will review" and a DM (best effort) with the same card.
2. **Approve** (staff only, checked on click): status `approved`, channel
   renamed `approved-…`, buttons disabled, `log_action("event.approve")`; if
   `events_create_scheduled`: `guild.create_scheduled_event(name,
   description, start_time, end_time, entity_type=external,
   location=location)` (external type needs an end time — default start +
   duration) and store its id; post the **announcement** to
   `events_announce_channel_id` (the card + "Interested? click the event
   above"); DM the requester.
3. **Deny**: modal asking a one-line reason → status `denied`, rename
   `denied-…`, DM the requester the reason, log.
4. **Go-live**: a `tasks.loop(minutes=1)` finds `approved` events with
   `starts_at <= now` → status `live`, post `**{title}** is starting now!`
   (+ `<@&events_ping_role_id>` if set, with `AllowedMentions(roles=True)`)
   in the announce channel, log. When `ends_at <= now` → `done`, and the
   review channel is **archived**: renamed `done-…` and moved/left in place
   (deleting is the owner's call; default keep for 7 days then delete —
   setting `events_channel_retention_days`, default 7).
5. **Commands** — `/event list` (staff: pending/approved with links),
   `/event cancel <id>` (staff or requester; cancels the scheduled event),
   `/timezone set <tz>` (autocomplete over `zoneinfo.available_timezones()`
   filtered by the typed text; shows the current local time as confirmation),
   `/timezone show`, `/event settings …` (staff: category, announce channel,
   ping role, create-scheduled toggle).

## HammerTime

Every rendered time is `<t:{unix}:F>` (full) plus `<t:{unix}:R>` (relative)
— Discord renders each viewer's local zone, which is the whole point.

## Test mode

Channel creation and scheduled-event creation are side effects the guard
cannot see. While `TEST_MODE`: `events_category_id` defaults to the test
channel's category; the announce channel is the test channel (guard would
force it anyway); **scheduled-event creation is skipped and logged as
`event.would_create_scheduled`** (a real event would be visible to the whole
server). The owner sees the full flow inside the test category.

## Tests (offline)

`test_timezones.py`: parse/convert round-trips incl. DST zones and Phoenix;
autocomplete filter. `test_events.py`: slugify (spaces, `!`, unicode, length
cap, `pending→approved` rename); duration parsing; status transitions as a
pure state machine (illegal transitions refused); card rendering contains
`<t:` stamps. `cogs/community/test_events.py`: approve/deny handlers with a
fake interaction + fake guild; test-mode skip of scheduled-event creation;
go-live loop picks exactly the due rows.

## Definition of done

As before: green tests, clean ruff, code-notes, architecture tree, three
commits (timezones → events logic → cog), not pushed. Live verification is
the owner's test sweep: `/timezone set`, `/event create`, approve, deny,
watch a 2-minutes-ahead event go live in the test channel.
