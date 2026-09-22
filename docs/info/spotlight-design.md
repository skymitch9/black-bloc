# Spotlight — Twitch channels that are not Discord members, announced, bumped every N hours, pinned for the duration, staff-curated with an expiry

> 🔴 **SUPERSEDED IN PART, 2026-09-21 (branch `channel-streamers`): the spotlight row IS NOW THE CHANNEL RECORD.**
> A `spotlight_channels` row is a channel Black Bloc watches whether or not it is spotlighted — `spotlight` is a
> toggle ON the row (schema 52), beside `announce` (its own opt-out) and `youtube_channel_id` / `youtube_handle`.
> Spotlight OFF announces the channel exactly as a member's go-live is announced and only drops the pin, the
> reminders and the expiry; the row, its sessions and its ping role survive the toggle, and **only Remove this
> channel takes them**. Everything below still describes the spotlight-ON behaviour correctly. Read
> [`channel-streamers-design.md`](channel-streamers-design.md) first.

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v148** — merge `e7f54c9`, release `f73d3a7`, deployed **2026-09-20 18:23** Phoenix; `spotlight_mode` ships **shadow**; sweeps **637–643** are the owner's; verified: boot log: the spotlight cog loaded, logged in, no Traceback; /health ready=true; the Go-live page rendered on the local mock after the merge (a Spotlight strip cell in shadow, a GamesDoneQuick Live-now card with spotlight badges, three channel-only Streamers rows, the Spotlight chip and the Spotlight a channel button; zero console errors); the first gate run's one red test was KI-32, green alone and on the re-run. Was: 🔨 BUILT on branch `spotlight` 2026-09-20 — nothing in it had met Discord or Helix. The `## Deviations` foot is the truth where this body departs from what shipped, and `## What was NOT verified` is the honest half; sweeps `SL-a` … `SL-g` in `../access/sweeps.md` are the proof that is missing. ⚠️ **Schema is 48, not the 47 this body says** — `selftest-boot` took 47 on `main` while this was being built. Was: 📐 **DESIGN (Fable, 2026-09-20 17:0x) — dispatches
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
| **the announcement** | offline → live | rendered by the SAME pure helpers as a member's go-live (`golive_template`, `golive_embed`, the card with the Twitch colour), `{name}` = the channel's display name, no member; **pinned** when the row's `pin` is on (`_pin` with reason *Black Bloc keeps this spotlight pinned while it streams*); logs `golive.spotlight_announced` (~~IMPORTANT~~ **ROUTINE since 2026-09-21 17:3x**, branch `quiet-channel-kinds`: Owner, 2026-09-21 17:2x, verbatim: *"okay that works, i dont want log messages appearing in black bloc logs for channel linking or channel spotlight or channel annouce"* — every `golive.spotlight_*` success kind, `golive.channel_announced`, `golive.history_swept`, `golive.link` and `youtube.link` are ROUTINE, so nothing in this family reaches `#blackbloc-logs` at the default level; the rows are all still written and still on the Logs page, and `golive_log_level = all` turns the mirror back up with no deploy. The `_failed` twins stay IMPORTANT) — or `golive.spotlight_would_announce` in shadow. No fan-role ping (there is no member); `golive_ping_role_id` applies as it does to any announcement |
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

0. **2026-09-20, branch `spotlight-pings` — a spotlight channel can now hold a ping role of its
   own** (`golive_fan_roles.spotlight_id`, schema 50). §A's *"No fan-role ping (there is no
   member)"* in the three-posts table is ~~true~~ **reversed**: the announcement mentions the
   channel's fan role beside `golive_ping_role_id` when one exists, a reminder does too but only
   while `spotlight_bump_pings` is on (default false), and an expiring or removed row takes its
   role away through `pings.remove_fan_role`. Design:
   [`spotlight-pings-design.md`](spotlight-pings-design.md). ⚠️ `_announce` also writes Twitch's
   spelling of the name onto the row the first time it sees the channel live, so a hand-added
   `gamesdonequick` becomes `GamesDoneQuick` and names its role properly.

*(written by the build agent, branch `spotlight`, **2026-09-20**, off `main` `f0e7ef3` — the commit
that carries `costream`. Every item is a departure from the body above; where the body is silent and
a choice had to be made, it says so.)*

1. ⚠️ **Schema is 48, not 47.** The body was written against a `main` where 46 was the top; the
   `selftest-boot` branch merged as `0f006ea` and took **47** while this was in flight, so this build
   takes **48**. Still two new tables plus `spotlight_bumps` through the `SCHEMA` bootstrap and
   nothing in `ADDED_COLUMNS`, so migrate-before-deploy is automatic exactly as §F says.

2. ⚠️ **The shadow kind is `golive.would_spotlight_announce`, not the body's
   `golive.spotlight_would_announce`.** `logkinds.SHADOW` is the literal string `".would_"`, so
   `is_shadow()` and `test_every_shadow_kind_is_routine_by_rule_not_by_being_listed` only recognise a
   kind whose head is followed by `would_`. The body's spelling classifies as UNCLASSIFIED and fails
   `test_every_emitted_kind_is_classified` by name. Checklist **2** asks for `<feature>.would_<action>`
   anyway, so the house spelling is the one that gets the classification for free.

3. **The default bump wording is `"… {duration} so far. {url}"`, not `"… {duration} in. {url}"`.**
   The shared `tidy()` strips a dangling `in` before a full stop — that is what it exists to do for an
   empty placeholder — so the body's wording renders *"4 h."* and silently eats the word. **Measured,
   not reasoned**: `test_the_reminder_fills_the_five_placeholders_and_tidies_what_is_missing` failed
   on exactly that before the wording changed. It is a settings key either way, so the owner can put
   it back in one edit if he wants the gap.

4. **The cog borrows the go-live cog's Helix client rather than making its own.** §E says "one Helix
   call per poll for the whole list" and is silent on whose client. Two `TwitchClient`s would mean two
   app tokens, two `aiohttp` sessions and two things to close; `_helix()` reads
   `bot.get_cog("GoLive").helix`, so the credentials and the token refresh have one home. The
   consequence the panel and the page both say out loud: with no key, nothing polls, and
   `words.NO_KEY` is the sentence.

5. **`render` and `announcement_embed` gained a keyword-only `name=`.** A spotlight has no member, and
   `display_name(None)` is `"Someone"` — the card would have read *"Someone is now live on Twitch!"*.
   The alternative was a fake object with a `display_name` attribute, which is a lie in the shape of a
   member. Both changes are additive and every existing caller is byte-for-byte unchanged
   (`test_the_card_names_the_channel_not_someone` is the guard).

6. **The `/golive` sub-panel's moves are BUTTONS, not the select §C describes.** The owner's standing
   rule (2026-09-03) is *"moves are buttons that render only when valid, never a status menu with two
   spellings of the same move"*, and the Streamers sub-panel beside it already works that way (a
   select to pick the row, buttons to act on it). So: `ChannelPick` selects the channel, and the row
   gets **Extend a week** / **Keep for ever** *or* **Let it expire** (never both), **Bump now** only
   while it is actually live, and **Remove**.

7. **`bump_now` tells "no such row", "not live" and "the cog is not up" apart, and the route answers
   404 / 409 / 503.** The first draft returned `no_row` when the cog was missing, so staff on a
   perfectly good row were told it had gone — a bare-status failure in words' clothing. `words.NO_COG`
   is its own sentence. Traced to `test_a_bump_refuses_in_words_when_the_channel_is_not_live` failing
   with a 404 the first time it ran.

8. **`POST /api/golive/spotlight/{id}/bump` and `POST /api/events/{id}/spotlight` are NOT in
   `contract.json`, and that is deliberate.** `tests/api/test_contract.py` drives every listed route
   against the real router and demands a 200; a bump needs a live session *and* a `Spotlight` cog
   instance on the harness bot, and the event route needs the shared seed's event to be approved with
   a twitch.tv Where. Both are covered instead where those can be arranged —
   `tests/api/tools/test_golive.py` and `tests/cogs/community/test_events.py` — and both are in the
   mock, so `check.mjs` still serves them to the page. The four CRUD routes ARE in the contract, with
   a seeded `{spotlight_id}`.

9. **`GET /api/golive/spotlight` carries each row's open session AND its last five, rather than a
   second route.** §C says *"The Live-now card and Recent streams include spotlight sessions"* and
   lists no route for them. One list with `session` (the open one, or null) and `sessions` (the recent
   ones) is what lets `spotlightCards()` and `spotlightSessions()` be pure and testable without a
   sixth fetch.

10. **`spotlight_bump_template` lives in the *How streams are spotted* drawer, not in *The
    announcement*.** It is the only posted wording this build adds, so §D's *"every posted word is a
    key"* is satisfied either way — but `announcementSection` takes `placed.wording` and renders a
    hand-picked set of keys from the `golive` namespace, so a key placed there would have passed the
    every-key-lands-once test while appearing **nowhere on the page**. The drawer renders it through
    `settingsPanel`, which is the surface that actually shows it.

11. ⚠️ **The every-key-lands-once fixture was already two behind, and this build fixed it.**
    `NAMESPACE_KEYS` in `golive-join.test.mjs` said **36**; the three `golive_costream_*` keys landed
    after it was measured and nobody updated it, so the test was asserting a stale list against itself
    and would never have caught them. It is now **48** — measured by import, not counted by hand — and
    the catch-all assertion names the three costream keys explicitly.

12. **`spotlight_mode` is the header strip's fourth mode cell.** §C does not say where the mode
    switch goes. Putting it beside Twitch / YouTube / Ping roles is the one place staff already look
    for "is this on", and its note says how many channels have no member behind them.

13. **A spotlight-only row's `user_id` is the string `spotlight:<id>`.** The join keys rows by member
    id and a spotlight has none. A synthetic prefix keeps one sorted list, keeps `blankRow`'s shape
    intact, and is what `memberCell` reads to print *channel only* instead of calling `nameNode` with
    something Discord has never heard of.

14. **A cancelled event drops its spotlight from `events.cancel_for`, through a function-level
    import.** §B says a cancelled event expires its row at once, and `cancel_for` is the one place
    BOTH doors (the card and `POST /api/events/{id}/cancel`) pass through. `black_bloc/events.py` is
    imported by the cog, so a module-level import of the cog would be a cycle; `drop_spotlight()`
    imports inside the call and logs a warning rather than raising if the spotlight half is not up.

15. **`forget_spotlight` closes an open session itself when the cog is not loaded.** Staff final say:
    the row goes whatever state it is in, and leaving an orphan open session behind would have made
    the next boot's reconcile clean up after a move that already reported success.

16. **Three files outside the design's list had to change, and two of them are gate failures if they
    do not.** `site/public/assets/labels.js` gains nine label lines, or
    `test_every_registry_key_the_site_shows_has_a_label` fails by name. `tests/test_settings_panel.py`
    gains `golive` to the over-the-cap list, because §D said the golive group grows past 25 and it
    does — the guard asserts exactly which groups need the Find box. `tests/test_loops.py`
    `BEFORE_LOOPS` goes 19 → 20 for the new poller's `before_loop`.

17. **Four commits, not the six the brief sketched, and the reason is the AST guards.**
    `tests/test_logkinds.py::test_no_classification_entry_is_dead` refuses a classified kind that
    nothing emits, so `logkinds.py` had to land in the same commit as the cog that writes the kinds,
    not with the storage and the keys. The routes, the contract, the mock, the page, the join and the
    event action landed together because `check.mjs` and `test_contract.py` each read both halves and
    a split would have left one commit red.

18. **NOT done, deliberately:** nothing merged, nothing deployed, nothing pushed to `main`; no key
    flipped — `spotlight_mode` ships **shadow** as its registry DEFAULT (checklist 37's standing rule
    that anything which POSTS ships shadow), and no guild row was written; `TODO.md`, `DONE.md`,
    `deploys.log` and `KNOWN_ISSUES.md` untouched; `C:/lcw/bb-preview-c` never entered and nothing
    under `site/public/preview/` or `assets/page-preview-*.js` touched; no `twitch_user_id` is
    resolved at add time (the design's column exists and is left NULL — `get_users` would be a second
    Helix call for a fact nothing reads yet); the events PAGE has no **Spotlight this stream** button
    (the route is there and the card has it — the page button is one call on `page-events.js` and is
    named here rather than guessed at).

19. 🔴 **2026-09-20, branch `boot-sweep` — the boot reconcile this build shipped was never
    running on the real bot, and is fixed.** `Spotlight.reconcile_open_sessions` is correct;
    nothing reached it. `bot.py:setup_hook` loads every cog **before IDENTIFY**, so
    `self.bot.guilds` is **empty** at `cog_load` — and `cog_load`'s
    `self._reconciler.run(self.reconcile_open_sessions)` used the default `stamp=True`, which
    closed the `Reconciler`'s 60-second window from a pass that had walked **nothing**. The
    `on_ready` pass, the only one with guilds, then hit `skip_if_recent=True` and skipped. Net
    effect: an open spotlight session whose announcement had gone was never closed at boot, and
    `golive.spotlight_reconciled` could not be emitted on a real restart. The fix is one
    argument — `stamp=bool(self._guilds())` — plus `_guilds()` as the one home for *which guilds
    a boot pass covers* (non-`unavailable`, checklist 32), which `reconcile_open_sessions` now
    reads. Found while building the go-live boot sweep, which had the identical defect
    ([`golive-boot-sweep-design.md`](golive-boot-sweep-design.md) ▸ Deviations ▸ **0**). Guarded
    by `tests/cogs/content/test_spotlight.py::test_a_cog_load_with_no_guilds_yet_leaves_the_boot_to_on_ready`,
    which was **falsified first** — it fails on the un-fixed cog. ⚠️ `poll_once` and
    `_poll_minutes` still read `self.bot.guilds` directly and were deliberately left alone: they
    run after ready, so the emptiness never bites them. ⚠️ **Still not verified against
    Discord** — no bot has been restarted with a spotlight session open; the new sweep row
    `BS-e` in `../access/sweeps.md` is the proof that does not exist yet.

## What was NOT verified

⚠️ **Nothing in this build has met Discord, and nothing has met Helix.** No spotlight has been
announced, pinned, bumped, unpinned or expired anywhere but in the suite, against `FakeChannel` /
`FakeMessage` / `FakeHelix`. The sweep rows `SL-a` … `SL-g` in `../access/sweeps.md` are the proof
that does not exist yet.

Specifically NOT verified:

- **That Discord pins and unpins as the code asks.** `message.pin(reason=…)` and `.unpin()` are
  library knowledge; the tests prove the CALLS and the refusal words, not the pin. A channel's
  50-pin ceiling and the **Manage Messages** permission have never been met — `SL-b` is the row that
  turns the pin into a fact and `PIN_REFUSED` into a sentence somebody has actually read.
- **That Helix answers for a channel nobody here is linked to.** `get_streams(["gamesdonequick"])`
  is the same batched call the go-live poll already makes, but it has never been made for a login
  that is not a member's. The whole feature rests on that one assumption.
- **The four-hour bump against a real clock.** Every bump test moves `started_at` in the database
  and polls again. Nothing has waited four hours, and no reminder has appeared in a channel.
- **The migration on a real database.** Schema 48 was applied by `Database.connect` in the suite's
  `tmp_path` databases only; the Fly volume has never seen `spotlight_channels`. It is additive
  tables through the bootstrap, so migrate-before-deploy is automatic — but that is an argument,
  not a measurement.
- **Any browser.** The Go-live page was not opened. The channel-only row, the Spotlight chip, the
  drawer's Spotlight group, the fourth mode cell in the strip and the Spotlight-a-channel form were
  checked through `check.mjs` and the join's fixtures, and **rendered nowhere**.
- **The `/golive` ▸ Spotlight… sub-panel in Discord.** Built and tested against a fake interaction;
  no button has been pressed, and the modal has never been opened.
- **A spotlight that goes live in the same tick as its row expires.** The per-row lock and the
  partial unique index make one outcome the only possible one, and the tests drive the two in
  sequence; nothing raced them.
- **`spotlight_event_slack_hours` against a real event that overran.** The maths is unit-tested; no
  event has ever run long.

