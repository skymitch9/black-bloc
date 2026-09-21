# Auto-link — the go-live history links people to the channel they streamed from, and a presence go-live links them from then on

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 🔨 **BUILT on branch `autolink` 2026-09-21, off
> `main` `0d83065` (v150 live) — NOT merged, NOT deployed, and ⚠️ NOTHING IN IT HAS MET DISCORD.** Gate green both
> orders. The `## Deviations` foot is the truth where this body departs from what was built, `## What was NOT
> verified` is the honest half, and sweeps `AL-a` … `AL-d` in `../access/sweeps.md` are the proof that is missing.
> 🔴 **Read Deviation 2 first:** the already-linked check has to run before the readable check, or a clean server is
> told *1 could not be read* every time. Was: 📐 **DESIGN (Fable, 2026-09-21 08:4x), dispatched to
> Opus as branch `autolink`** the same turn. **Last verified: 2026-09-21 08:4x** against `main` `9b865b8` (v150 live):
> `golive_sessions` rows carry `user_id, source (twitch|presence|youtube), url, platform, started_at` (`storage/db.py:134`);
> `golive.twitch_login_from_url` `:149`; `cogs/content/golive.py:link_channel` `:471` (the one path that writes a
> `golive_links` row — the `/golive` panel's Link my Twitch, the site's Add a streamer and the Link them button on
> Recent streams all call it), `opt_out` `:533`, `_go_live_once` (the presence path: a member whose Discord status says
> Streaming is announced with `source = presence` and the presence's URL); `cogs/content/youtube.py:link_channel`-equivalent
> for `youtube_links` (`api/tools/youtube.py` resolves a URL/handle); `golive_optout` (`:129`) — an opted-out member is
> never announced.

## The ask, verbatim (owner, 2026-09-21 08:3x)

*"can we do a sweep of the golive channel and link people to their twitch channel and or YouTube channel? Can we also
perform the link for each user when they go live with presence?"*

The go-live history IS the sweep's source: every presence-detected session already recorded who streamed and the URL
their Discord status carried. The "go-live channel" the owner names is what those sessions posted into; the sessions
table is the same facts without re-reading Discord.

## A. The sweep — once, staff-run, from the sessions table

`golive.link_from_history(bot, guild, *, actor, via)` (in the go-live cog beside `link_channel`): walk `golive_sessions`
for the guild, newest first; for each `user_id` with NO `golive_links` row whose sessions include a `twitch.tv` URL, take
the login from the MOST RECENT such URL (`twitch_login_from_url`) and call `link_channel` — the same path, the same
refusals (a login already linked to another member is refused in words and listed, not overwritten), the same
`golive.link` log row with `because: history_sweep`. Same for YouTube URLs → `youtube_links` through the YouTube cog's
link path (a `youtube.com/watch?v=…` URL from a presence carries no channel id — resolve the video's channel through the
existing probe if it can, else list it as *could not tell the channel*). **Opted-out members are skipped** and listed.
Members no longer in the guild are skipped. The answer is a report in words: *"Linked 4 people (Casey → caseyfast, …),
skipped 2 opted out, 1 login already belongs to somebody else (…), 0 could not be read."* — one IMPORTANT
`golive.history_swept` row with the counts and the names. Idempotent: a second sweep links nobody.

**Doors:** the Go-live page ▸ Streamers toolbar gains **Link from history** (staff, `ask()` confirm naming what it does,
`POST /api/golive/links/sweep` → the report sentence, the list re-renders); `/golive` ▸ the staff half gains the same
button. Contract + mock (the mock's seed has a presence-only session for Moth — the sweep links Moth to `mothlight`).

## B. From then on — a presence go-live links the member

Key **`golive_autolink_presence`** (bool, **true**, group golive; help: *"true links a member to the Twitch or YouTube
channel their Discord status names the first time they are announced from it; false leaves linking to the person or to
staff"*). In `_go_live_once`, when `source == "presence"`, the announcement is going out (mode on or shadow), the member
has no link for that platform and the presence URL yields a login → `link_channel` (same path, same refusal if the login
belongs to another member — then no link, the announcement still goes, a `golive.autolink_refused` routine row says why),
logged as `golive.link` with `because: presence`. The person is told once by DM through the existing link DM if one
exists (read `link_channel` — if it already DMs, nothing new; if not, no new DM: the `/golive` panel shows the link and
Unlink stays theirs). Opted-out members are never announced, so never auto-linked.

## C. Keys — one (`golive_autolink_presence`); registry + mock + label + `placeSettings` + the join fixture.

## D. Logging — `golive.history_swept` (IMPORTANT), `golive.autolink_refused` (routine); `golive.link` gains `because`.

## E. Tests, docs, gate

`tests/cogs/content/test_golive.py` (the sweep links from the newest URL, skips opted-out and already-linked, refuses a
login that belongs to another member and says so, is idempotent, writes one row; the presence hook links once, never
when the key is off, never when opted out, never over another member's login), `tests/api/tools/test_golive.py` (the
route + gate), `tests/api/test_contract.py`, the key/kind guards. Both `pytest -n 8` orders, `ruff`, ES parse,
`check.mjs`, the six node tests, env cleared. A headless render of the toolbar button → the report sentence on the mock.
Docs: `code-notes.md`; this doc's `## Deviations` + `## What was NOT verified`; `golive-design.md` one dated line;
`architecture.md`; `docs/info/README.md`; `sweeps.md` rows `AL-a…` (a: Link from history on the live site → the report
names who got linked; b: a presence-only streamer goes live → announced AND linked, the row shows the login; c: the key
off → announced, not linked; d: an opted-out member is skipped by both). NOT `TODO.md` / `DONE.md` / `deploys.log` /
`KNOWN_ISSUES.md`.

## Deviations

*(written by the build agent, branch `autolink`, **2026-09-21**, off `main` `0d83065` — v150 live.
Every item is a departure from the body above; where the body is silent and a choice had to be
made, it says so.)*

1. **The sweep and the presence hook share ONE new function, `link_from_url`, and that is where
   every refusal is decided.** §A and §B each describe "call `link_channel`, and the YouTube path
   for a YouTube URL", which is the same four decisions twice (which platform the address names,
   whether they already have a channel there, whether somebody else holds it, whether it can be
   read at all). Two copies is checklist **15**, and four chances to drift. So
   `cogs/content/golive.py` gained **two** module functions rather than the brief's one:
   `link_from_url(bot, guild, actor, target, url, *, via, because)` → `(outcome, the channel in
   words)` with outcomes `linked` / `already` / `taken` / `unreadable`, and `link_from_history`
   on top of it. The presence hook is one line in `_go_live_once` calling a third, private
   `GoLive._autolink_presence`.

2. 🔴 **The already-linked check runs BEFORE the readable check, and the order is load-bearing.**
   Written the other way round — which is how it was first built — a member who already has a
   channel but whose newest session URL is a `youtube.com/watch?v=…` is reported as *could not be
   read*, which is a lie about somebody the sweep should not have looked at. Measured on the mock's
   own seed: Casey is linked on both platforms and his co-stream's YouTube side is a watch URL, so
   the wrong order made every sweep of a clean server say *1 could not be read*. Guarded by
   `test_the_history_sweep_leaves_a_member_who_already_has_a_channel_alone`, which asserts
   `unreadable == []`.

3. **A `watch?v=…` address is answered *could not be read* WITHOUT asking YouTube.** §A says
   *"resolve the video's channel through the existing probe if it can"*. There is no such probe:
   `youtube.confirm_live` answers a `Confirm` with `channel_title` and no `channelId`, and
   `YouTubeClient.resolve` refuses a watch URL before any request. Calling it anyway would have
   written a `youtube.resolve_failed` row for **every** YouTube presence go-live, since a Discord
   presence's URL is a watch URL nearly always. So `link_from_url` pre-checks with
   `youtube.channel_id_in` / `handle_in` and only calls the link path when a channel can actually
   be told. Guarded by
   `test_a_watch_address_carries_no_channel_so_the_sweep_says_it_could_not_be_read`, which asserts
   the fake client was never asked and no `youtube.resolve_failed` row exists.

4. **`helix=None` on both paths, so Twitch can never refuse a link the member's own stream
   proved.** `link_channel` with a helix returns `no_such_channel` when `get_users` comes back
   empty, and an empty answer is indistinguishable from a bad minute at Twitch. The login here came
   from the address the member was *streaming on*, which is stronger evidence than a typed name, so
   neither the sweep nor the presence hook verifies it. The link is therefore stored unverified
   (`twitch_user_id` NULL), exactly as the site's own **Add a streamer** stores one, and the panel
   already says *"not verified with Twitch"* — checklist **10**.

5. **`also_url` is read too, so a co-stream offers both sides.** The body names `url` only; a
   co-stream row carries the YouTube half in `also_url`, and skipping it would miss the one case
   where somebody demonstrably has a channel on both platforms. `golive.history_urls` walks both
   columns of every row. Guarded by `test_a_costream_row_offers_both_sides_to_the_sweep`.

6. **The site's toolbar button keeps its own notice, `sayAgain('golive.sweep', …)`, because the
   section's notice is not where the report lands.** `load()` hands ONE `say` node to both
   `streamersSection` and `recentSection`; a node lives in one place, so the last append wins and
   the section's notice is physically inside **Recent streams**, which is collapsed. Rendered with
   `keepSaying('golive.links', …)` the report sentence was in the DOM and invisible — found by
   looking at the pixels, not the tree. The door now keeps its own key and re-says it under the
   button that was pressed. ⚠️ **The same trap still applies to `golive.links`, `golive.optouts`,
   `youtube.links`, `pings.streamers` and `pings.streamer`** on this page; NOT fixed here, named
   so the next person does not rediscover it.

7. **`/golive`'s **Link from history** acts straight away — no confirm card.** §A asks for an
   `ask()` confirm on the SITE and is silent about Discord. A confirm card there means two button
   classes and a second render path in a cog the other agent is also in; the sweep is idempotent
   and every link it makes is reversible with **Unlink** (staff final say), so the button runs and
   answers with the report. The site's confirm is built as specified.

8. **The staff button sits on ROW 1, not row 2.** Row 2 already holds Refresh, Logs, Streamers…,
   Spotlight… and the site link — five, which is Discord's cap. Row 1 holds one member button, so
   `LINK_HISTORY` joins it there and `test_the_link_moves_open_a_modal_and_nothing_else_does`'s
   `{0, 1, 2}` assertion still holds.

9. **The route answers COUNTS plus the sentence, not the lists.** `POST /api/golive/links/sweep`
   returns `linked` / `opted_out` / `taken` / `unreadable` / `left` as integers and `message` as the
   report; the names are in the sentence and on the log row. A contract `rows` entry would have
   required the contract's seeded world to link somebody on every run, which ties the shape check
   to fixture luck.

10. **`golive.history_swept`'s details carry `who` (the linked list) beside the five counts** — the
    body says *"the counts and the names"*, and a count with no names cannot answer *"who did that
    sweep link?"* six weeks later. The refused and unreadable names are in `message` on the same
    row.

11. **`link_channel` gained a keyword-only `because: str | None = None`, written into the
    `golive.link` row ONLY when set.** Every existing caller leaves the details dict byte-identical,
    which is what `tests/api/tools/test_golive.py`'s exact-dict assertion wanted. `youtube.link`
    gains nothing: `cogs/content/youtube.py` is the other agent's file this session and §D names
    only `golive.link`.

12. **Both the sweep and the presence hook swallow an exception from the link path and count it as
    *could not be read*.** A `resolve` that raises something the client did not wrap must not 500 a
    staff route, and nothing in `_go_live_once` may abort an announcement that has already been
    posted — the hook runs AFTER the post and the live role, last thing before `return ANNOUNCED`.
    Both log a warning naming the type.

13. **`recent_sessions(…, HISTORY_SESSIONS)` with `HISTORY_SESSIONS = 2000`**, rather than a new
    "all sessions" query. The sweep wants the whole history and `recent_sessions` already orders
    newest-first, which is the order `history_urls` depends on; 2000 is far past this server's
    lifetime total. A server that ever passes it links from the newest 2000 sessions, which is the
    same answer for anybody who has streamed recently.

14. **`platform_of` was refactored onto the new `platform_of_url`** rather than a second copy of the
    same three lines (checklist **15**). The presence's own `platform` still wins over the address.

15. **NOT done, deliberately:** nothing merged, deployed or pushed to `main`; `TODO.md`, `DONE.md`,
    `deploys.log` and `KNOWN_ISSUES.md` untouched; **`architecture.md` NOT edited** — its *Registry
    keys* line says **294 on `main` at v150** and is correct until this branch merges, at which
    point it is **295** (`len(KEY_TYPES)` measured here); the conductor's docs ritual owns that
    number, and a concurrent branch is adding keys of its own. **`golive-design.md` does not
    exist** — §E names it; the dated line went to
    [`golive-page-design.md`](golive-page-design.md) instead, which is the page this build changes.
    No schema change, so no migration; no new loop; `golive_autolink_presence` ships **true** as its
    registry default, which is what §B asks for, and the brake on the announcement it rides along
    with is `golive_mode`, which is per-guild and already set.

## What was NOT verified

⚠️ **NOTHING IN THIS BUILD HAS MET DISCORD.** No bot was started, no presence was watched, no
announcement was posted and no link was written to the live database. Every claim above is the
suite's, against `FakeGuild` / `FakeMember` / `FakeHelix` / a fake YouTube client, plus one pass of
the site half in a real browser against the local mock. Sweep rows `AL-a` … `AL-d` in
[`../access/sweeps.md`](../access/sweeps.md) are the proof that does not exist yet.

Specifically NOT verified:

- **That a real Discord presence's URL is one this can read.** `extract_stream` takes the URL off
  the activity; Twitch presences carry `https://www.twitch.tv/<login>` and that is what the tests
  hand it, but no real presence has been read. A YouTube presence has never been seen at all, so
  whether it carries a watch URL (unreadable, by Deviation 3) or a channel address is **unknown** —
  the guess is a watch URL, and `AL-b` is the row that settles it.
- **That the live `golive_sessions` table holds anything worth sweeping.** The sweep was never run
  against the production database, so *how many people it would link on the real server* is
  unmeasured. `AL-a` is the row that answers it, and the report sentence is the answer.
- **Any Twitch or YouTube network call.** `helix=None` everywhere (Deviation 4), and the one
  YouTube resolve the tests exercise is a fake. A real handle address in a session URL would fetch
  a channel page; that path has never run here.
- **The `/golive` panel's **Link from history** button.** It is in the button table, the table is
  rendered by `test_the_panel_renders_exactly_the_row_the_table_says`, and **no Discord panel has
  ever drawn it.** Whether row 1 looks right beside **Stop announcing my streams** is a guess.
- **The `golive.history_swept` and `golive.autolink_refused` rows on the Logs page.** Both kinds
  are classified and both are written in the suite; no human has read one.
- **The presence hook against a real go-live.** `test_a_presence_go_live_links_the_member_to_the_
  channel_it_named` drives `_go_live` directly. Nobody has gone live.
- **A member who has left the guild.** `guild.get_member` returning `None` is the test's fake; a
  real departed member is the same call, and has not been watched.
- **The browser console.** The page was driven in Chrome over CDP and the console reader returned
  only claude.ai's own frames — **no 127.0.0.1 messages of any kind, error or otherwise**. So *"the
  page logged no errors"* is NOT something this build measured; what it measured is that the button,
  the confirm, the report sentence and the re-rendered table all drew correctly.
- **A large history.** `link_from_history` walks up to 2000 session rows and makes one
  `get_link` + one `youtube_links` read per member per platform. Fine for this server, unmeasured
  for a big one, and it runs inside one HTTP request with no progress anywhere.
