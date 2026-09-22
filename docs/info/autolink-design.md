# Auto-link — the go-live history links people to the channel they streamed from, and a presence go-live links them from then on

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **Follow-up 2026-09-21 LIVE v153 (12:13)**
> — [**a video link can name the channel (off by default)**](#follow-up-2026-09-21-a-video-link-can-name-the-channel-off-by-default),
> release commit `3d75254`, merge `0b3653d` of branch `youtube-video-link` (built off `main` `bfbd53f`, v152 live),
> 3 commits, 8 deviations, 24 tests, sweeps **734–735**. It closes **Deviation 3**, which stays true wherever the
> new key `golive_autolink_youtube_video` is **off** — and ✅ **off is what is on live, measured**: the deployed
> `/api/settings` answers type `bool`, value `false`, default `false`. ⚠️ Read that section's own
> `### Follow-up deviations` and `### Follow-up — what was NOT verified`; the body below is the v151 build. · ✅ **LIVE v151 (2026-09-21)** — release `c1b83f0`,
> deployed commit `c7ef8f1`, **2026-09-21 09:51** Phoenix; merge `731519e`, 4 commits; sweeps **726–729** (were
> `AL-a` … `AL-d`) are the owner's and **none has been walked**. ✅ **Link from history was run ONCE on live 09:5x** —
> the links count read **29** afterwards; ⚠️ **the report sentence itself was NOT captured**, so what it said about
> kept / skipped / unreadable is unknown. ⚠️ **NOTHING IN IT HAS MET DISCORD** — `golive_autolink_presence` (**true**)
> has never fired, because nobody has gone live since the deploy. Was 🔨 BUILT on branch `autolink` 2026-09-21, off
> `main` `0d83065` (v150 live). Gate green both
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
skipped 2 opted out, 1 login already belongs to somebody else (…), 0 could not be read."* — one ~~IMPORTANT~~
**ROUTINE (2026-09-21 17:3x, branch `quiet-channel-kinds`)**
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

## D. Logging — `golive.history_swept` (~~IMPORTANT~~ **ROUTINE**), `golive.autolink_refused` (routine); `golive.link` gains `because`.

🔇 **Reversed 2026-09-21 17:3x, branch `quiet-channel-kinds`.** Owner, 2026-09-21 17:2x, verbatim: *"okay that works, i dont want log messages appearing in black bloc logs for channel linking or channel spotlight or channel annouce"* — so
`golive.history_swept` is ROUTINE in `black_bloc/logkinds.py` and the sweep posts no embed to
`#blackbloc-logs` at the default `golive_log_level = important`. ⚠️ **The row is unchanged and still on
the Logs page** under the **golive** chip, with the same counts and the same `who` list;
`golive_log_level = all` turns the Discord mirror back up with no deploy. `golive.autolink_refused` was
routine already and is untouched. Design: [`channel-streamers-design.md`](channel-streamers-design.md) ▸
**Follow-up 2026-09-21 (17:2x)**; sweep row `QK-a`.

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

## Follow-up 2026-09-21: a video link can name the channel (off by default)

> ✅ **LIVE v153 (2026-09-21 12:13)** — release commit `3d75254`; `release.json` says `v153` at `0b3653d`. Merge
> `0b3653d` of branch `youtube-video-link` (built off `main` `bfbd53f`, v152 live), **3 commits**, 8 deviations,
> **24 new tests**; the gate shipped on its THIRD run (**7237 passed, 3 skipped**). Sweeps are numbered
> **734–735** (were `YV-a` / `YV-b`) and **neither has been walked** — they need a YouTube presence this server
> has produced **zero** of in **166** live sessions. ⚠️ **Nothing in it has met Discord or YouTube in production,
> and it cannot have: the key is OFF on live** — measured on the deployed `/api/settings`, type `bool`, value
> `false`, default `false`. 🔴 The parser rests on the watch page's **player JSON `channelId`**; the
> `<meta itemprop="channelId">` tag was **ABSENT on both** real watch pages measured, and the measurement was
> taken from THIS machine, never from Fly's datacenter address — where **KI-30** records that YouTube answers a
> bot check. Closes **Deviation 3** above — which is still true wherever the new key is **off**, and that is the
> shipped default.

### The ask

Owner question, 2026-09-21 09:5x, verbatim: *"what can we do about youtube presence? can we just wait for a
go live and then get the channel from it or whats the best way? people have go live messages for youtube?"*

The answer given was a list of downsides, and the owner then said, verbatim (10:5x):
***"Let's build it but keep it off for now"*.** The four downsides are why it ships off:

1. **It is scraping.** The channel id is read out of YouTube's own HTML, which YouTube changes whenever it
   likes and owes nobody notice. `resolve_without_key` already carries that risk for handles; this doubles it.
2. **A presence can carry somebody else's video.** A rich-presence app reports *what is playing*, not *who is
   streaming*. Linking off a watch address can hand somebody a channel that is not theirs.
3. **YouTube may block it.** The same *Sign in to confirm you're not a bot* page the live prober already
   meets (`BOT_CHECKED` in `youtube.py`) can be served here, and repeated page reads invite it.
4. **It is speculative.** MEASURED on live 2026-09-21 09:5x: **166 go-live sessions in history, 159
   presence/Twitch, 5 Twitch poller, 2 presence with no platform, ZERO YouTube addresses ever.** Discord sets
   the Streaming status itself only for Twitch. Nothing in the server's whole history would have used this.

### The fix

`YouTubeClient.resolve_video_channel(video_id) -> (channel_id, title)`, beside `resolve`:

- **With a key** — one unit: `videos?part=snippet&id=<id>`, `snippet.channelId` + `snippet.channelTitle`. An
  empty answer falls through to the page rather than refusing, mirroring `_resolve_with_key`.
- **Keyless** — GET `https://www.youtube.com/watch?v=<id>` with `BROWSER_AGENT`, read by the module function
  `read_video_channel(html)`: `<meta itemprop="channelId" content="UC…">` first, else the player JSON's
  `"channelId"` / `"externalChannelId"`, with `"ownerChannelName"` as the title.
- A page that names nobody raises `YouTubeError` with a sentence, and a `Sign in to confirm` body gets its own
  sentence saying YouTube asked the bot to prove it is not a robot. A non-200 is a `network=True` error.

`video_id_in(text)` sits beside `channel_id_in` / `handle_in` and reads `watch?v=`, `youtu.be/<id>`,
`/live/<id>`, `/shorts/<id>` and `/embed/<id>`.

🔴 **Which page pattern this relies on, and the real pages it was measured against.** Two real public watch
pages were fetched with the bot's own `BROWSER_AGENT` on **2026-09-21** —
`youtube.com/watch?v=jNQXAC9IVRw` (*Me at the zoo*) and `watch?v=dQw4w9WgXcQ`:

| Pattern | On a real WATCH page | On a real CHANNEL page (`@jawed`) |
|---|---|---|
| `<meta itemprop="channelId">` | ⚠️ **absent on both** — YouTube serves no such tag today | absent |
| `"channelId":"UC…"` | **3 hits on one page, 4 on the other, ONE distinct id each — always the owner's** | **10 different ids, NONE the channel's own**; the first is `UCPszuZ…`, the channel is `UC4QobU…` |
| `"externalChannelId":"UC…"` | 1 hit, the owner's | — |
| `<link rel="canonical">` | points at the **watch** URL, so `CANONICAL` is useless here | the channel's own id — which is why `resolve_without_key` uses it |

So **the pattern actually relied on is the player JSON's `"channelId"`**; the meta tag is tried first and has
never yet been seen. The table is also the measurement behind `resolve_without_key`'s docstring warning — the
channel page really does name ten other channels, and the watch page really does not. `read_video_channel`
is therefore a **watch-page reader only**, and `resolve_video_channel` only ever fetches `watch?v=`.

### The key — one, and it ships OFF

**`golive_autolink_youtube_video`** (bool, **default `False`**, group golive). Help, verbatim: *"true lets a
go-live whose Discord status carries a YouTube video link find the video's channel and link the person to it;
false leaves such a link unread. Off by default: it reads YouTube's page, which can change, and a video is not
always the streamer's own"*. Registry (`settings_store.py`), the mock's `SETTING_SPECS` row, `labels.js`,
`golive-join.js:placeSettings` beside `golive_autolink_presence` in *How streams are spotted*, and the
every-key-lands-once fixture. Checklist **33**.

In `link_from_url`, the YouTube branch that used to answer *unreadable* for an address with no channel id and
no handle now asks `channel_behind_video`, which is **the whole brake**: key off → `None`, with the client
never touched and no request made. Key on → the video's channel, and the link continues down the **existing**
YouTube path (`cogs/content/youtube.py:link_channel` with a `/channel/UC…` address), so the same resolve, the
same refusal when the channel belongs to another member, the same one row. Both callers — the presence hook
`_autolink_presence` and the history sweep `link_from_history` — inherit it with no change of their own.

### Follow-up deviations

1. **The row that says `via_video` is `youtube.link`, not `golive.link`.** The brief asked for *"the same
   `golive.link` row with `because` and a `via_video: true` detail"*. There is no such row: the YouTube half
   of `link_from_url` has never written `golive.link` — it writes `youtube.link`, from the YouTube cog's own
   `link_channel`. So that function gained keyword-only `because: str | None = None` and `via_video: bool =
   False`, each written into the details **only when set**, exactly the shape Deviation 11 above chose for
   `golive.link`. Every existing caller's details dict is byte-identical, which is what the exact-dict
   assertions wanted. This also reverses Deviation 11's *"`youtube.link` gains nothing"* — it now carries
   `because` on both autolink paths, which is the fact `golive.link` already carried for Twitch.
2. **`video_id_in` refuses a bare word, and reads `/embed/` as a fifth shape.** An 11-character handle is
   indistinguishable from a video id, and `handle_in` accepts 3–30 characters — so a bare-id form would make
   `@somebodyxyz` a video. Only the address shapes are read. `/embed/` was added because it is the same id in
   the same position and costs one alternation.
3. **The channel the video names is passed to the existing link path as a `/channel/UC…` ADDRESS, not as a
   bare id.** A bare channel id matches `HANDLE`, so `_handle_of` would have stored `UCsXVk…` as somebody's
   handle. The address form makes `handle_in` answer `None`, which is correct.
4. **A `YouTubeError` from the lookup is swallowed and answered *could not be read*, and writes NO
   `youtube.resolve_failed` row.** Same reasoning as Deviation 12: nothing in `_autolink_presence` may disturb
   an announcement that is already posted, and a speculative lookup that fails is not a staff-facing event. It
   is logged at INFO with the sentence YouTube's error carried.
5. **The keyless title is used as the fallback wording.** `link_channel` re-resolves the `/channel/` address
   and, with no API key, gets no title at all — so a link made this way would have read
   `youtube.com/channel/UC…` in the report. The `ownerChannelName` already read off the watch page is used
   instead, so the sweep says *"Moth → Moth Light"*. It is not written to the link row; that stays the
   existing path's business.
6. **A missing YouTube cog answers *unread*, not a crash.** `channel_behind_video` checks `cog_of(bot)` and
   its `client` before asking anything.
7. ⚠️ **`site/mock/golive-join.test.mjs`'s every-key-lands-once fixture went 52 → 53 here, and branch
   `member-optout` bumped the SAME fixture 52 → 53 independently in the same session.** The merged list holds
   **54**, and the assertion, the comment and the printed sentence all have to move together — a merge that
   takes either side alone passes the count and silently loses a key. Deviation 16 above records the identical
   trap one release earlier; it is now the second time.
8. **NOT done, deliberately:** nothing merged, pushed to `main` or deployed; `TODO.md`, `DONE.md`,
   `deploys.log` and `KNOWN_ISSUES.md` untouched; `architecture.md` untouched — its registry-key count is the
   conductor's docs ritual to move (**297** on `main` at v152, **298** with this branch, measured by
   `len(KEY_TYPES)`). No schema change, so no migration. No new route, no new button, no new Discord surface:
   the key is reached through the Settings page and `/settings`, which every registry key gets for free.

### Follow-up — what was NOT verified

⚠️ **No bot was started and no link was written to the live database.** Every claim about behaviour is the
suite's, against `FakeYouTubeClient` / `FakeMember`.

- **That any of this ever fires.** Zero YouTube presences exist in 166 sessions (the measurement above). The
  key is off, so on the live server this build is currently **unreachable code**.
- **A real `resolve_video_channel` network call.** The parser was measured against two real watch pages saved
  to disk; the client's own request path was exercised only against the fake. Nothing has called YouTube from
  inside the bot on this branch.
- **Whether YouTube serves the same HTML to Fly's IP.** Both real pages were fetched from the owner's machine.
  A datacentre address is exactly where the *Sign in to confirm* page is most likely, and that case is handled
  in words but has never been seen here.
- **Whether the meta tag ever exists.** It is tried first and was absent from both real pages; the branch is
  covered by a synthetic fixture only.
- **A keyed lookup.** `YOUTUBE_API_KEY` is not set on this server, so the `videos?part=snippet` path has run
  against the fake `_Request` and nothing else. Its quota cost (**1 unit**) is YouTube's documented figure,
  not a measured one.
- **The Settings page.** The key was not rendered in a browser; `check.mjs` proves the mock serves it and the
  fixture proves it lands in *How streams are spotted*, which is not the same as somebody having seen it.
- **Sweeps `YV-a` and `YV-b`** in [`../access/sweeps.md`](../access/sweeps.md) are the proof that does not
  exist yet — and ⚠️ **both need a YouTube presence, which nobody on this server has ever produced.**

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

15. **NOT done, deliberately:** nothing deployed or pushed to `main`; `TODO.md`, `DONE.md`,
    `deploys.log` and `KNOWN_ISSUES.md` untouched; **`architecture.md` NOT edited** — its *Registry
    keys* line says **294 on `main` at v150**; with `channel-streamers` and this branch both in it
    is **296**, measured (`len(KEY_TYPES)`), and the conductor's docs ritual owns that number.
    **`golive-design.md` does not
    exist** — §E names it; the dated line went to
    [`golive-page-design.md`](golive-page-design.md) instead, which is the page this build changes.
    No schema change, so no migration; no new loop; `golive_autolink_presence` ships **true** as its
    registry default, which is what §B asks for, and the brake on the announcement it rides along
    with is `golive_mode`, which is per-guild and already set.

16. **`origin/main` was MERGED INTO this branch on 2026-09-21, at the conductor's explicit
    instruction, after the build was already committed and pushed.** The brief said never to merge
    and that the conductor resolves it; the conductor then asked for the merge by name, because
    `main` had since taken the `channel-streamers` build (which touches five of the same files) and
    a one-line fix to `discordmock.test.mjs`. Seven conflicts, all resolved by keeping BOTH sides:

    - `black_bloc/golive.py` — `main` renamed `SPOTLIGHT` to **Channels…**; that label is kept and
      `LINK_HISTORY` sits beside it. `STAFF_BUTTONS` is now four, and row 2 is still at five.
    - `site/public/assets/page-golive.js` — both constant blocks kept; `streamerDoors` auto-merged
      and still carries the sweep door.
    - `tests/api/tools/test_golive.py`, `docs/access/sweeps.md` — both appended blocks kept.
    - `docs/info/code-notes.md` — both appended sections kept, and ⚠️ its header is a STACK of dated
      lines where git took only one: `channel-streamers`' line was put back by hand under this
      build's.
    - `docs/info/README.md` — this design's BUILT row and `channel-streamers`' BUILT row, both kept.
    - `site/mock/golive-join.test.mjs` — ⚠️ **both branches bumped the every-key-lands-once fixture
      49 → 50 independently**, so the merged list holds 51 and the assertion, the comment and the
      printed sentence all moved to **51**. A merge that took either side alone would have passed
      the count and silently lost a key.

    The gate was re-run whole on the merged tree: **7178 passed / 3 skipped** both orders, ruff
    clean, 39 modules parse, `check.mjs` 21 pages / 198 routes, all six node tests green —
    `discordmock` included, which is `main`'s fix for a date-dependent fixture that failed on the
    base commit from 2026-09-21 onward (confirmed pre-existing in a throwaway worktree of
    `0d83065` before the merge). The site half was re-rendered in a browser against the merged mock.

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
