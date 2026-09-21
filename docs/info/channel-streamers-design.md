# Channel streamers — an org channel is a persistent row like any linked member; spotlight and the ping role are toggles on it

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE v151 (2026-09-21)** — release `c1b83f0`,
> deployed commit `c7ef8f1`, **2026-09-21 09:51** Phoenix; merge `e3f873a`, 7 commits; sweeps **719–725** (were
> `CS-a` … `CS-g`) are the owner's and **none has been walked**. ✅ **The migration RAN at this boot** — `database: added
> spotlight_channels.spotlight / .announce / .youtube_channel_id / .youtube_handle`, schema **52**, four ADDED columns,
> **no rebuild** (so no backup was needed). ✅ **Applied on live through the site 09:5x:** GDQ (row id 3) linked to
> `@GamesDoneQuick` (`UCI3DTtB-a3fJPjKtQ5kYHfA`, *Games Done Quick*), ESA (row id 4) linked to `@esamarathon`
> (`UC3Oe-jfrIqEGygxYBYyN6jQ`, *ESA Speedrunning*) with announce **OFF**, `rpglimitbreak` added as row id 5 kept +
> spotlight on + announce **OFF**. ⚠️ **NOTHING IN IT HAS MET DISCORD, HELIX OR YOUTUBE LIVE**, and ⚠️ **ESA was
> announced and pinned at the boot itself, before its opt-out could land** — the 🔇 *channel opt-out must end an open
> session* item on [`../TODO.md`](../TODO.md), branch `channel-optout`. Was 🔨 BUILT on branch `channel-streamers`
> 2026-09-21 (design: Fable, 08:2x, dispatched to Opus the
> same turn). The `## Deviations` foot is the truth where this body departs from
> what was built, and `## What was NOT verified` is the honest half; sweeps `CS-a` … `CS-g` in
> [`../access/sweeps.md`](../access/sweeps.md) are the proof that is missing. ⚠️ **Schema is 52 and the migration
> added FOUR columns, not three** — `announce` is the owner's mid-build ask. Was: **Last verified: 2026-09-21 08:2x** against `main` `c4cc672`
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
drawer in both toggle states and Add a streamer with no member. Docs: `code-notes.md`; this doc's `

## Deviations

**Built 2026-09-21 on branch `channel-streamers` off `main` `9b865b8` (v150 live).** Where this
body and the code disagree, the code is what shipped and this section is why.

1. ⚠️ **`twitch_login` was NOT relaxed; a YouTube-only channel is refused in words *for now*.**
   §A left the choice to the builder. The migration is **purely additive** — four columns
   through `ADDED_COLUMNS`, no rebuild — because `spotlight_channels.id` is referenced by
   `spotlight_sessions.spotlight_id` and `golive_fan_roles.spotlight_id` with **no foreign key
   to protect either**, and the live rows (GDQ, ESA, re-added by the owner this morning) carry
   both. A `mod_cases`-style rebuild of that table buys nothing today — both of the owner's
   channels have Twitch logins — and risks the two tables that point at it. The refusal is
   `spotlight.NEEDS_A_TWITCH_NAME`, raised as `400 needs_twitch` by `POST /api/golive/spotlight`
   and said in the browser by `page-golive.js`'s `ADD_CHANNEL_NEEDS_TWITCH` before any request
   goes out. Relaxing the column later is a one-commit rebuild on the `golive_fan_roles`
   precedent; nothing built here assumes the column is `NOT NULL` except the two refusals.

2. ⚠️ **The log kind is the EXISTING `golive.spotlight_announced` with `spotlight: false` in
   details — no new kind.** §A offered `golive.channel_announced` as the alternative. Reusing it
   keeps the Logs chip honest in the way that actually matters: the rest of the family
   (`golive.spotlight_ended`, `…_post_failed`, `…_pin_failed`, `…_bumped`) is unchanged, so a
   reader who filters on the announce kind still finds the matching end. A new head would have
   split one event across two kinds whose ends were the same kind, and would have needed a
   `logkinds.py` registration and a chip mapping for a row that is not a new event at all — it
   is the same event with one field different. The details now carry `spotlight`, `announce`,
   `platform`, and `pin` already reflects the toggle (`pin AND is_spotlit`).

3. ⚠️ **A channel with the spotlight OFF never expires**, and `sweep_expiries` skips it. The
   body only said the **Expires** cell reads `—`. Letting such a row keep expiring would
   reproduce the owner's complaint exactly — a channel added for persistence vanishing a week
   later — so `spotlight_channel(...)` stores `expires_at = NULL` for a row it makes with the
   spotlight off, AND the sweep ignores a non-spotlit row whatever its date. Turning the
   spotlight back ON re-arms whatever date the row still carries.

4. ⚠️ **"A session joins from either side" is ONE SESSION PER ROW, not two platforms on one
   session row.** `spotlight_sessions` has no `also_*` columns and §A capped the migration at the
   three (now four) columns, so a co-stream on a channel row is not modelled the way a member's
   is. Instead: whichever sweep sees it first opens the session; the other logs
   `youtube.live_seen` with `announced: false` and `because: joined_session` and posts nothing;
   and **only the side whose address the session carries ends it**. Which side that is is read
   off the session's own `url` (`spotlight.platform_of`), because no column says it — the Twitch
   sweep's miss counter now skips a session on a `youtu…` address, and the YouTube sweep's skips
   one that is not. The Live-now card and Recent-streams row read the same way, so a YouTube
   session draws a YouTube card, not a Twitch one.

5. **A fourth column, `announce`, landed in the same migration** (owner, mid-build: *"once built
   let's keep esam in the list but opt them out of notifications"*). It is a channel's own
   opt-out, the twin of a member's: `announce_info` returns before it starts a session, so an
   opted-out channel gets no post, no session, no pin and no reminder, and therefore no end
   either — while the row, its ping role, its YouTube link and its spotlight all stay exactly as
   they were. The **Opted out** column on the Streamers list reads it for a channel row the way
   it already reads a member's. Sweep row `CS-g`.

6. **A member row offers Spotlight whether or not they are linked** (owner, mid-build: *"It
   seems like you need to be linked to be spotlighted. While this is preferred I don't think this
   should be mandatory"*). The **Spotlight this channel…** button used to render only under
   `row.twitch`; it now always renders on a member row with no spotlight, and opens the same form
   with an EMPTY box when there is no link to prefill. The join is unchanged, so a login typed
   that matches a linked member is still ONE row — theirs — carrying the channel's facts. **A
   link is preferred, not required.**

7. **The mock cannot reach YouTube**, so its `PATCH …/{id}` with `youtube` resolves a `UC…` id
   out of the value itself and otherwise knows the owner's two handles by name
   (`KNOWN_CHANNELS`); anything else is refused with the same shape of sentence the bot uses.
   The bot's own path is `client.resolve(...)`, which needs **no API key** — it reads the channel
   page's canonical link, which is exactly how the two ids below were found.

8. **The two YouTube channel ids, resolved 2026-09-21 by `curl` of the channel page** (the same
   canonical link `YouTubeClient.resolve_without_key` reads; no API key was available):

   | Handle | Channel id | Title on the page |
   |---|---|---|
   | `@GamesDoneQuick` | `UCI3DTtB-a3fJPjKtQ5kYHfA` | Games Done Quick |
   | `@esamarathon` | `UC3Oe-jfrIqEGygxYBYyN6jQ` | ESA Speedrunning |

   Both are in the mock seed. ⚠️ **They are NOT on the live rows** — the conductor links them
   through the new route after the deploy (`CS-d`).

9. **`/golive` ▸ Spotlight… is `Channels…`**, and its buttons moved to three rows — the spotlight
   toggle and its moves on row 1, the opt-out / role / YouTube / remove moves on row 2, Add and
   Back on row 3 — because a spotlit, live, roled, YouTube-linked channel now offers eight
   buttons and Discord caps a row at five.

## What was NOT verified

- ⚠️ **NOTHING IN THIS BUILD HAS MET DISCORD.** No panel was opened, no button pressed, no
  announcement posted. The `/golive` ▸ **Channels…** half is exercised only by `pytest` against
  fakes.
- ⚠️ **Nothing has met Helix.** No channel was polled, no real stream announced, pinned, bumped
  or ended. The spotlight-off announcement path is proved by a test asserting the rendered text,
  not by a post in `#go-live`.
- ⚠️ **Nothing has met YouTube live.** The two channel ids were resolved by fetching the channel
  pages, which is a real network read — but `probe_live` was never called against either, so no
  channel row has been announced from a YouTube stream and the either-side join has never run
  outside a fixture.
- ⚠️ **The migration has NOT run on the live database.** Schema 51 → 52 applies at the next
  boot. ✅ **What IS measured (2026-09-21): a hand-built schema-51 `spotlight_channels` holding a
  `gamesdonequick` and an `esamarathon` row was opened by `Database.connect()` and came back at
  schema 52 with `spotlight = 1` and `announce = 1` on both**, the two new text columns NULL — so
  the four `ALTER TABLE … DEFAULT` statements do keep an existing channel behaving exactly as it
  did. What is still NOT measured is that run against the PRODUCTION file, which has rows,
  sessions and fan roles this fixture did not.
- ⚠️ **The site half was pressed against the LOCAL MOCK only**, in `chrome-headless-shell`
  149.0.7827.22 over raw CDP, at 1280 px and 390 px, with **zero console rows** of any kind.
  Verified there: the GamesDoneQuick drawer in BOTH toggle states (spotlight on offers
  *Spotlight off · Extend a week · Let it expire · Bump now · Stop pinning it*; spotlight off
  offers *Spotlight on* alone and the other four are gone), **Add a streamer** with the member
  left blank, and **Link a YouTube channel** on the `rpglimitbreak` row — after which that row's
  YouTube cell read `@GamesDoneQuick`. The Streamers list showed ESA and RPG Limit Break as
  *opted out* and GamesDoneQuick as *kept for ever*.
- **Not exercised at all:** the expiry sweep against a real clock; `pings_fan_role_delete` on a
  real Discord role through **Remove this channel**; the event-card **Spotlight this stream**
  path (it now passes `spotlight=True` explicitly, and its own tests pass, but no event was
  spotlighted end to end).
- **A pre-existing failure, NOT from this build:** `site/mock/discordmock.test.mjs` fails one
  assertion (*the go-live embed: drops the embed stamp*). Measured on a throwaway worktree of
  `main` `9b865b8` — it fails there identically.
