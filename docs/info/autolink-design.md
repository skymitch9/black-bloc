# Auto-link — the go-live history links people to the channel they streamed from, and a presence go-live links them from then on

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-21 08:4x), dispatched to
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

*(the build agent writes here what it had to do differently, dated)*
