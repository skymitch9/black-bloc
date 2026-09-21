# Channel streamers — an org channel is a persistent row like any linked member; spotlight and the ping role are toggles on it

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-21 08:2x), dispatched to
> Opus as branch `channel-streamers`** the same turn. **Last verified: 2026-09-21 08:2x** against `main` `c4cc672`
> (v150 live): a channel with no member exists ONLY as a `spotlight_channels` row (`storage/db.py:876` — `id, guild_id,
> twitch_login, twitch_user_id, display_name, note, added_by, added_at, expires_at, bump_hours, pin, event_id`); its
> go-live is announced/pinned/bumped by `cogs/content/spotlight.py` (the five-minute Helix poll, `_announce`, the bump,
> `_end`); its ping role hangs off `golive_fan_roles.spotlight_id` (v150); `forget_spotlight` `:995` deletes the row —
> and with it the channel, its role and its sessions — which is what the owner hit; `golive-join.js` draws a spotlight
> row as `spotlight:<id>` with a *channel only* badge; the YouTube live sweep (`cogs/content/youtube.py`) walks
> `youtube_links` (member-keyed) only; `api/tools/youtube.py:40` accepts `youtube.com/channel/UC…` or an `@handle` and
> resolves it (`:55` `handle`).

## The ask, verbatim (owner, 2026-09-21 08:1x)

*"I removed them from Spotlight as a test and they vanished from the whole list. I want them linked like any other stream
so they're persistent. I then want to be able to spotlight or role them like any other stream on and off. Also find
YouTube channels for both of them if possible to link"*

## A. The model — the spotlight row becomes the channel record; spotlight is a flag on it

`spotlight_channels` is renamed in MEANING, not in name (no table rename — checklist: migrations are additive): it gains
**`spotlight INTEGER NOT NULL DEFAULT 1`** (the toggle; existing rows stay spotlighted, so GDQ and ESA keep today's
behaviour), **`youtube_channel_id TEXT`** and **`youtube_handle TEXT`** (`ADDED_COLUMNS`, schema 51 → **52**). The
row is the channel streamer: *a Twitch login and/or a YouTube channel with no Discord member behind it*. `twitch_login`
becomes nullable in effect for a YouTube-only channel — if the column is `NOT NULL`, keep it and store `''` … NO: the
UNIQUE `(guild_id, twitch_login)` would then collide; the builder picks between relaxing the column (the `mod_cases`
two-step rebuild the spotlight-pings build used for `golive_fan_roles`) and requiring a Twitch login for every channel
row (YouTube-only channels refused in words *for now*) — and SAYS which in Deviations. The owner's two channels both
have Twitch logins, so either choice serves today.

**Going live.** A channel row's Twitch login is polled as today (one batched Helix call). When it goes live:
- **spotlight off** → announced EXACTLY as a member's go-live is (`golive_template`, the card, `golive_live_author`,
  the global ping role + the row's own fan role), one `spotlight_sessions` row, the end path edits to past tense per
  the one end wording — **no pin, no bumps**. Log `golive.channel_announced` (IMPORTANT) — or reuse
  `golive.spotlight_announced` with `spotlight: false` in details; the builder picks the one that keeps the Logs chip
  honest and says why.
- **spotlight on** → today's behaviour: pinned, bumped every `bump_hours`, unpinned + cleaned at the end.
The **YouTube side**: the YouTube live sweep walks channel rows with a `youtube_channel_id` beside `youtube_links`
(same `probe_live`, same `_live_now` path with a `name=` instead of a member, the same co-stream join if the Twitch side
is already open — `open_session_on` finds the row's session by either side). A YouTube handle typed in (`@GamesDoneQuick`)
resolves through the same code `api/tools/youtube.py` uses for a member link.

## B. Doors

**Site — Go-live page.** **Add a streamer** takes *a channel with no member*: the member picker becomes optional; with
no member, the typed value routes as today (Twitch login or YouTube URL/handle) and makes a channel row (spotlight OFF by
default — a key, `golive_channel_spotlight_default`, bool false, so the owner can flip it). **Spotlight a channel** stays
as the door that makes a row with spotlight ON (it is what the owner used today). The row's drawer: **Spotlight** group
becomes a toggle — *Spotlight on* / *Spotlight off* (with the kept / expires / bump / pin moves shown only while on) —
plus **Link a YouTube channel** / **Unlink it** in the YouTube group (the member group's construct), the Ping-role group
as v150 (Add / Rename / Remove), and **Remove this channel** (danger, confirm: *"Removes GamesDoneQuick from the list,
its spotlight, its YouTube link and its ping role (per pings_fan_role_delete). Nothing in Discord is deleted except the
role if that setting says so."*). The Streamers list: the *channel only* badge stays; the Announced cell reads *live now*
/ *ready*; the Expires cell reads *kept for ever* / *until …* only while spotlight is on, else *—*; a new
**Spotlight** column? NO — the existing Spotlight chip filters, and the drawer's toggle says the state; the Expires
column's *—* is enough.

**Discord — `/golive` ▸ Spotlight… sub-panel** becomes **Channels…**: the list, Add a channel… (Twitch login, optional
YouTube handle, spotlight on/off), per row: Spotlight on/off, Extend / Keep, Bump now (while on and live), the ping role
moves, Remove. Panels-over-slash: buttons that render only when valid.

**Routes:** `POST /api/golive/spotlight` gains `spotlight: bool` (default from the key) and `youtube: <url|handle>`;
`PATCH /api/golive/spotlight/{id}` gains `spotlight` and `youtube` (null to unlink); `GET` rows carry `spotlight`,
`youtube_channel_id`, `youtube_handle`. Contract + mock rows (GDQ with both links, spotlight on; a channel with
spotlight off; a YouTube-only channel if allowed).

## C. Keys — one, `golive_channel_spotlight_default` (bool, false, group golive), registry + mock + label + `placeSettings`
+ the join fixture.

## D. The two channels — do the lookup, then the owner links them

The design cannot know YouTube channel ids. The builder RESOLVES `@GamesDoneQuick` and `@ESAMarathon` (or the
handles the channels actually use — check `youtube.com/@GamesDoneQuick` and `youtube.com/@esamarathon`) through the
resolver the routes use (or a one-off `curl` of the channel page for its canonical `UC…` id if the resolver needs the
API key it cannot have) and writes the two ids into the **mock seed** and into the report; the conductor links them on
the live site through the new route after the deploy (the live rows are GDQ `id 1`… re-added 08:1x — read them, do
not assume ids).

## E. Tests, docs, gate

`tests/test_spotlight.py` + `tests/cogs/content/test_spotlight.py` (a channel with spotlight off is announced like a
member and never pinned or bumped; on → today's behaviour; the toggle flips without losing the row, the role or the
sessions; Remove takes everything; the YouTube side announces and co-streams), `tests/cogs/content/test_youtube.py`
(the sweep walks channel rows), `tests/api/tools/test_golive.py` (the route fields, both defaults, refusals in words),
`tests/api/test_contract.py`, `tests/storage/test_db.py` (52), `golive-join.test.mjs`, the key/kind guards. Both
`pytest -n 8` orders, `ruff`, ES parse, `check.mjs`, the six node tests, env cleared. A headless render of the row
drawer in both toggle states and Add a streamer with no member. Docs: `code-notes.md`; this doc's `## Deviations` +
`## What was NOT verified`; `spotlight-design.md` + `spotlight-pings-design.md` a dated banner each (the spotlight row is
now the channel record); `golive-page-design.md` one line; `architecture.md`; `docs/info/README.md`; `sweeps.md` rows
`CS-a…` (a: Spotlight off on GDQ → the row stays, the role stays, the Expires cell reads —; b: GDQ goes live with
spotlight off → announced like a member, not pinned, no bump; c: Spotlight on → pinned and bumped; d: link
@GamesDoneQuick's YouTube → the row shows it and a YouTube live announces; e: Remove this channel → everything gone,
with the confirm read first; f: `/golive` ▸ Channels… does the same). NOT `TODO.md` / `DONE.md` / `deploys.log` /
`KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: added columns (or one rebuild — say which).

## Deviations

*(the build agent writes here what it had to do differently, dated)*
