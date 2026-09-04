# Phase 11 — Chat 2 (F10 step 2): editable lines, data intents, routing, manners

> ⚠️ **SUPERSEDED IN PART, 2026-09-04, by [`chat-panel-design.md`](chat-panel-design.md)** —
> the FEATURE behaviour below is what shipped, but every `/chat …` subcommand it names is
> retired: `/chat` is now ONE staff command that opens a panel. Read the doors off the panel
> design; read the behaviour here.

> ✅ **11a built in `e508232` + `6a91b87` + `f00e8de`** (branch `worktree-agent-aba2337a090a6d590`
> off `main` @ `ebf99a2`, 2026-08-27). Sections 1 (storage, seed, classification
> order, `POST /api/chat/try`), 2, 3 and 4 are **done and tested** — `pytest -q`
> 1941 passed, `ruff` clean, `site/mock/check.mjs` clean at 80 routes. ⚠️ Nothing
> has run against live Discord. **11b — the Chat page, the Try-it box and the
> settings section — is still to build.** How it was built, and the three places
> the build deviated from this document, are in `code-notes.md` § *chat 2 (11a)*.

> **Audience:** the Phase 11 build agents and the reviewer. **Status:** TRACKED (2026-08-31; private repo).
> Last verified: **2026-08-27** — owner decision taken 14:12 ("yes lets do all of those"); code facts from
> `black_bloc/chat.py` and `cogs/content/chat.py` at `1899f6e` (`code-notes.md` § "chat — @-mention
> replies"). NOT verified: nothing has run. **Priority: after Phase 10 (polls).**
>
> ✅ **11b built in `1aba879` (contract + mock) and `cfc5a2f` (the Chat page)** on
> branch `worktree-agent-aa53d8a518425a5df` off `main` @ `ebf99a2`, 2026-08-27 —
> `docs/info/code-notes.md` § "chat 2 — dashboard (11b)". ⚠️ **Not merged.**
> **11a is still open**, so the page runs against `site/mock/server.mjs` only and
> the eight new chat rows in `contract.json` fail `tests/api/test_contract.py`
> until the real routes exist.

## What exists
`chat.py`: `INTENTS` trigger tables, `LINES` (5–6 per intent), `ATTENDEE_LINES`, `classify(text)`,
`respond(intent, name=…, attendees=…)`, and the seam `reply_for(text, member, bot) -> str | None`.
`cogs/content/chat.py`: mention-only `on_message`, `chat_mode`, `chat_cooldown_seconds`, guard first,
reply with `mention_author=False`, `chat.insult` action row. Every reply passes `emoji.toned_text`.

## Build

### 1. Editable lines and intents (dashboard "Chat" page — the 15th tab, MODERATION group? no: COMMUNITY)
- Storage (additive, `SCHEMA_VERSION` +1): `chat_intents(id, guild_id, name, triggers TEXT(json list),
  kind IN ('canned','data','route'), enabled, sort, created_by, updated_at)` and
  `chat_lines(id, intent_id, text, enabled, created_by, updated_at)`. Seed from the code tables on first
  boot per guild (`chat.seed_defaults`); the code tables remain the fallback when a guild has no rows
  or an intent has no enabled lines.
- Classification order: guild intents (custom first, by `sort`) → built-in kinds → `unknown`.
  Word-boundary matching as today; a trigger is a phrase, case-insensitive.
- API `black_bloc/api/tools/chat.py` (staff-gated, refusals in words): `GET /api/chat/intents`,
  `POST /api/chat/intents`, `PUT /api/chat/intents/{id}`, `DELETE /api/chat/intents/{id}`,
  `POST /api/chat/intents/{id}/lines`, `PUT /api/chat/lines/{id}`, `DELETE /api/chat/lines/{id}`,
  `POST /api/chat/try` `{text}` → `{intent, line}` (a dry run, nothing sent). Action log `web.chat.*`.
- Page `chat.html` + `page-chat.js`: one card per intent (name, trigger chips editable, enabled switch,
  lines as an editable list with add/remove, "{name}" / "{attendees}" token help one line), "New intent"
  form, a **Try it** box that shows which intent a sentence would hit and the line it would get; the
  `chat_mode` / `chat_cooldown_seconds` / new settings in the page's Settings section. Level fields,
  token-only CSS, pager scroll-to-top helper (owner ask 14:01) if any list pages.

### 2. Data intents (kind `data`, answered from live state, never stored lines)
| intent | triggers (seed) | answer source |
|---|---|---|
| `who_is_live` | who's live, anyone live, who is streaming | open go-live sessions (`golive.open_sessions`) → names + links; "nobody right now" |
| `whats_next` | what's next, next event, when is the next | next approved event → title + `<t:…:R>` (HammerTime) + channel; none → "nothing scheduled" |
| `birthdays` | birthdays, whose birthday, next birthday | `birthdays.upcoming(limit=3)` respecting opt-outs |
| `head_count` | how many of us, how many people, member count | `presence.human_count` |
| `my_roles` | my roles, what roles can I pick | menus the member can pick from (`rolemenu_mode` on) + the roles they hold from those menus |
| `time_for_me` | what time is that for me, in my time zone | F4: parse a `<t:…>` or a time in the message → convert with the member's stored zone; no zone → point at the zone box (⚠️ 2026-09-03: `/timezone set` is retired — it is **My time zone** on `/event`, and `chat.py`'s sentence was rewritten) |
Each data intent renders through a short template line that IS editable on the Chat page (e.g. "{count} of us at the cookout right now").

### 3. Routing (kind `route`)
`need_a_mod` (I need a mod, help me, report, staff please): if modmail is on → tell them how to open a ticket (DM the bot) and, when `chat_route_ping_staff` is on, drop a one-line note in the staff channel with a link to the message; if modmail is off → name the staff roles. Logged as `chat.route`.

### 4. Manners (settings)
`chat_ignore_channels` (channels list; default empty) — the bot never answers there; `chat_greeting_reaction`
(off/on, default off) — a bare greeting gets a 👋🏿 (toned) reaction instead of a reply; `chat_reply_in_threads`
(off/on, default on). All on the Chat page and global Settings.

### 5. Later (not this phase)
A conversation backend behind `reply_for` with a persona prompt assembled from the enabled lines; out of
scope until the owner asks.

## Test-mode + guard
Unchanged: guard first, replies and reactions only where `allows_channel`; the staff-channel route note
goes through the guarded send too.

## Slices
- **11a** (bot + storage + API + tests, ~250k): storage/seed, classification over guild intents, data
  intents, routing, manners settings, routes, contract/mock entries.
- **11b** (dashboard, ~200k): the Chat page, Try-it, settings section, pager helper.

## Definition of done
Tests for every intent and for the seed/fallback; `pytest -q` green; `ruff` clean; `check.mjs` clean;
code-notes keyed `path:line`; owner sweep: `@Black Bloc who's live`, `what's next`, `how many of us`,
edit a greeting line on the dashboard and see it used.
