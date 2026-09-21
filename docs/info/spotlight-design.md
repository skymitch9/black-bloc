# Spotlight — Twitch channels that are not Discord members, announced, bumped every N hours, pinned for the duration, staff-curated with an expiry

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-20 17:0x) — dispatches
> AFTER `costream` lands**, because both touch the go-live cog, its keys and its sessions. **Last verified: 2026-09-20 17:0x**
> against `main` `e88573d` (v142 deploying): `black_bloc/twitch.py` — `TwitchClient.get_streams(logins)` `:177` (Helix
> `streams` by login, batched by 100), `get_users` `:185`, `get_games` `:192`; the go-live cog holds the client as
> `self.helix` (`cogs/content/golive.py:573`) and its pure render helpers take a `StreamInfo` + a name (`golive.py:render`
> `:394`, `announcement_embed` `:209`, `ended_render` `:309`); `events.py:where_link(text)` `:276` turns an event's Where
> into a URL (the `ttv=` aliases already make `twitch.tv/…` links); the pin precedent is `cogs/community/polls.py:_pin`
> `:1554` / `_unpin` with a reason; the event card's `DynamicItem` template holds five actions (`cogs/community/events.py:234`).
> Schema is **45** on `main`; `costream` takes **46**; this build takes **47**. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-20 16:5x)

*"we have a twitch channel gamesdonequick, it 1 needs to be tracked even though its not in the discord. It's an org channel
not a person so it cant be in the discord. Also a few times a year they run 24 hours marathons. and other times they run
marathons that last most of the day. I want them to get bumped in the go live channel every x (default 4) hours to remind
people that the important marathon is still going on. I also want a way to add and remove people from this list and with an
expiration date. That way we can highligh other marathons too. I also want a way to pin channels so while others will expire
and have to be reinputted, certain reoccuring channels like GamesDoneQuick can be always in the list while the rest get purged
after a set amount of time. i think this should be a website only feature but if you think we could do this organically in
discord without it being confusing to manage we can have it there too. This list needs to be staff managed and approved. I
imagine end users will submit an event and then the staff of the discord will set this up for the duration of their event.
lets also pin those streams in the go live channel for the duration of their event when this option is triggered."*

**Two words the ask uses for two things.** *Pin* means both "this row never expires" and "pin the announcement in the
channel". Here: a row is **kept** (forever) or **expires**; a message is **pinned**. The code and the wording keep them apart.

## A. The model

**A spotlight channel** is a Twitch login watched by name, with no Discord member behind it. Table `spotlight_channels`:
`id, guild_id, twitch_login, twitch_user_id, display_name, note, added_by, added_at, expires_at` (NULL = kept forever),
`bump_hours` (NULL = the key's default), `pin` (1/0, default from the key), `event_id` (NULL unless an event made it),
`UNIQUE (guild_id, twitch_login)`. **A spotlight session** is one live stretch: table `spotlight_sessions`: `id, guild_id,
spotlight_id, started_at, ended_at, title, game, url, mode, announced_message_id, last_bump_at, bump_count`, partial unique
index one open per `spotlight_id`. Both new tables through the `SCHEMA` bootstrap, **schema → 47**; bump messages' ids in a
small `spotlight_bumps` (`session_id, message_id`) so cleanup can delete them. Sessions are NOT `golive_sessions` rows — that
table is keyed by member, and a sentinel member is a lie the Members and Streamers pages would inherit.

**Detection** is a poll, not presence: every `spotlight_poll_minutes` (5) the cog asks Helix `get_streams` for every row's
login in one batched call (100 per call; the list will be single digits). Offline → live = a new session and the announce;
`spotlight_end_misses` (2) quiet polls = the end. No Helix key → the panel and the page say so in words and nothing polls.

**The three posts, all into `golive_channel_id` (or the shadow home under shadow, with the rehearsal note):**

| Post | When | What |
|---|---|---|
| **the announcement** | offline → live | rendered by the SAME pure helpers as a member's go-live (`golive_template`, `golive_embed`, the card with the Twitch colour), `{name}` = the channel's display name, no member; **pinned** when the row's `pin` is on (`_pin` with reason *Black Bloc keeps this spotlight pinned while it streams*); logs `golive.spotlight_announced` (IMPORTANT) — or `golive.spotlight_would_announce` in shadow. No fan-role ping (there is no member); `golive_ping_role_id` applies as it does to any announcement |
| **a bump** | every `bump_hours` (the row's, else `spotlight_bump_hours` = 4) while the session is open, measured from `started_at` then from `last_bump_at` | a NEW short message from `spotlight_bump_template` (default *"**{name}** is still live — **{game}**, {duration} in. {url}"*; placeholders `{name} {game} {title} {url} {duration}`), never pinned, no ping; its id kept for cleanup; logs `golive.spotlight_bumped` (routine) |
| **the end** | the last quiet poll | unpin; the past-tense edit exactly as `golive_end_mode` does for a member; when `spotlight_bump_cleanup` (true) delete that session's bumps; logs `golive.spotlight_ended` |

**Expiry** is the same five-minute tick: a row whose `expires_at` has passed ends its open session first (unpin, cleanup),
then is deleted, `golive.spotlight_expired`. A kept row (`expires_at` NULL) never expires. Adding a row already present
refuses in words and offers *extend* instead.

## B. The event hook — the member path

Members never touch the list. Their door is the one that exists: propose an event. On an **approved** event whose Where
resolves to a `twitch.tv` URL (`events.where_link`), staff get **Spotlight this stream** — a sixth action on the event
card / post's `DynamicItem` (`event:<id>:spotlight`), and the same button on the events page's row — which adds the row with
`twitch_login` from the URL, `expires_at` = the event's end + `spotlight_event_slack_hours` (2), `event_id` set, `pin` from
the key; refused in words when the login is already spotlighted (offers extend to the event's end instead). A cancelled event
expires its spotlight row at once (`golive.spotlight_expired`, `because: event_cancelled`). The spotlight row's drawer links
the event; the event's card says *spotlighted until …*.

## C. Doors — staff only, both

**The site — the go-live page (v142), extended, not a new section.** A spotlight channel is a streamer without a member,
so it is a ROW in the Streamers list (test 3: one subject, one place): the Member cell reads *channel only*, the Twitch cell
the login, the Announced cell *spotlight · until 30 Sep* or *spotlight · kept*, with a **Spotlight** filter chip beside the
others; the row's drawer gains a **Spotlight** group — Extend (+7 days / to a date), Keep forever / Let it expire, Bump now,
Pin on/off, Remove — each through the routes below with a confirm; **Add a streamer** gains *a channel with no member* (the
member picker becomes optional; then: the name after twitch.tv/, until (a date, default today + `spotlight_default_days` = 7),
keep forever, bump every N hours, pin). `golive-join.js` takes a sixth payload (`spotlight`) and its test gains the fixtures
(a channel-only row; a channel that is ALSO a linked member's login — one row, the member's, with the spotlight facts on it;
an expired row absent; a kept row present). Routes: `GET /api/golive/spotlight`, `POST /api/golive/spotlight`, `PATCH
/api/golive/spotlight/{id}` (expires_at / keep / bump_hours / pin / note), `DELETE /api/golive/spotlight/{id}`, `POST
/api/golive/spotlight/{id}/bump`; `POST /api/events/{id}/spotlight`; contract rows + mock rows (GamesDoneQuick kept, one
expiring marathon, one expired). The Live-now card and Recent streams include spotlight sessions (a `spotlight` source).

**Discord — small, because the owner asked whether it could be organic.** `/golive`'s staff half gains one button
**Spotlight…** → a sub-panel: the list (login · until / kept · live now?), **Add a channel…** (modal: the name after
twitch.tv/, days to keep it — blank means for ever), and per row a select → Extend a week / Keep for ever / Bump now /
Remove. Plus the event card's **Spotlight this stream** (§B). Nothing a member can press.

## D. Keys — nine, prefix `spotlight_`, `NAMESPACE_OVERRIDE` → **golive** (the group select is at its 25-cap; golive's group
grows past 25 and gains the Find box like events)

`spotlight_mode` (off / **shadow** / on — shadow posts everything into the shadow home with the note, as go-live itself does
today), `spotlight_poll_minutes` (5, 2–30), `spotlight_end_misses` (2, 1–5), `spotlight_bump_hours` (4, 1–48),
`spotlight_bump_template` (text, the default above; a validator refuses an unknown `{…}`; filled as `render` fills
`golive_template`), `spotlight_bump_cleanup` (bool, true), `spotlight_pin` (bool, true — the default for a new row),
`spotlight_default_days` (7, 1–365), `spotlight_event_slack_hours` (2, 0–24). Every posted word is a key (the bump template;
the announcement reuses go-live's); panel and page words are constants.

## E. The cog and the module

`black_bloc/spotlight.py` (pure: the row / session shapes, `next_bump_at`, `is_expired`, `login_from_url`, the bump render,
the refusals' words) + `black_bloc/cogs/content/spotlight.py` (cog **23**: the poll loop through `loops.wait_ready`, the
expiry sweep on the same tick, the announce / bump / end posts through the go-live cog's channel + shadow rules — import the
pure helpers, never copy them — and the `/golive` sub-panel's items) + `black_bloc/api/tools/golive.py` (the routes) +
`cogs/community/events.py` (the sixth action). Log kinds all under the `golive` feature (`logkinds.HEADS`; no new feature,
no new Logs chip). ⚠️ `reconcile_open_sessions`-style boot reconcile under `loops.Reconciler` (review-checklist **37**): an
open spotlight session whose message is gone is closed, one row per boot. ⚠️ Rate: one Helix call per poll for the whole
list; `get_streams` is already batched.

## F. Tests, docs, gate

`tests/test_spotlight.py` (pure), `tests/cogs/content/test_spotlight.py` (offline → live announces + pins once; shadow →
the shadow home + `would_announce`; the bump fires at the interval and not before, from `started_at` then `last_bump_at`;
the end unpins, edits past tense, deletes the bumps when cleanup is on and keeps them when off; expiry ends an open session
first; a kept row never expires; a duplicate add refuses and offers extend; no key → nothing polls, words say so; the boot
reconcile writes one row), `tests/cogs/community/test_events.py` (the sixth action: adds with the event's end + slack, refuses
a duplicate, a cancelled event expires the row), `tests/api/tools/test_golive.py` (the routes + staff gate), `tests/api/
test_contract.py`, `tests/storage/test_db.py` (47), `golive-join.test.mjs` (the four fixtures), the count guards (cogs 23,
keys, kinds, `BEFORE_LOOPS`). Both `pytest -n 8` orders, `ruff`, the ES-module parse, `check.mjs`, the four node tests, env
cleared. ⚠️ KI-26 (eleven sightings; a killed xdist run's exit code lies — read the log): kill by process tree only.
Docs: `code-notes.md`; this doc's `## Deviations` + `## What was NOT verified`; `architecture.md` (cog 23, schema 47, keys,
routes); `docs/info/README.md`; `golive-page-design.md` one dated line (the Streamers list gained channel-only rows);
`sweeps.md` rows `SL-a…` (a: add gamesdonequick kept forever on the go-live page → the row reads *channel only · spotlight ·
kept*; b: when GDQ goes live the announcement lands in #live-now (or the shadow home) and is pinned; c: four hours later a
bump; d: the stream ends → unpinned, past tense, bumps gone; e: a marathon added with an expiry disappears after it; f: an
approved event with a twitch link → **Spotlight this stream** on its post → the row appears with the event's end; g: the
`/golive` ▸ Spotlight… sub-panel lists and extends). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.
⚠️ Migrate before deploy — schema 47 is additive tables through the bootstrap; `Database.connect` applies it.

## Deviations

*(the build agent writes here what it had to do differently, dated)*
