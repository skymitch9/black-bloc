# YouTube live — a poller that catches a linked channel going live, feeding the go-live path

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v126, the datacenter fix LIVE as v133, the open-session row LIVE as v135** (merge `4b1db3f`, release `2dd8fcd`, 2026-09-17 19:11; deviations 24–26; verified: on the live bot one second after the v135 boot (19:11:12) the Logs page carries row #8100 youtube.live_seen for Pawpette — video_id None, botcheck True, mode on, announced False, because open_session:twitch — exactly the row this build exists for; boot log clean, /health ready.) (merge `858feeb`, release `b20e4dc`, 2026-09-17 18:44 — deviations 15–23 are the truth behind the wall; verified live: the bot's own probe_live, run inside the Fly container 18:5x, read Pawpette as live=True / video_id=None / botcheck=True (the wall page: isLive once, canonical href="undefined"); the site's status showed botcheck true, probed 2, quota 0, live_now 0 — nothing announced because her TWITCH go-live session #139 was still open (the one-announcement-per-person rule), and that path writes no row, so the probe's success was invisible — follow-up dispatched.) · ⚠️ **A FOLLOW-UP is in flight on branch `youtube-live-seen` (off `main` `568c177`, NOT merged, NOT deployed): the open-session path now leaves one `youtube.live_seen` row reading `announced: false` / `because: open_session:<source>`, and `live_health` gained `reading_live` — Deviations ▸ *The silent open-session path*, sweeps `YL-o`/`YL-p`.** · v126: — merge `99c307c`, release `e537b2c`, deployed **2026-09-17 14:45** Phoenix; `youtube_live_mode` ships OFF (the owner flips it); the `## Deviations` foot is the truth where it departs from the body; sweeps **534–542** are the owner's; KI-30. ⚠️ **A FIX is in flight on branch `youtube-live-fix` (off `main` `ddd6fdc`, NOT merged, NOT deployed): from Fly's datacenter address YouTube serves a bot-check page with no canonical link, so v126 announced nothing at all — Deviations ▸ *The datacenter page*, sweeps 586–590, KI-30 rewritten.** Was: 📐 DESIGN, dispatching to Opus 13:3x. **Last verified: 2026-09-17 13:29**
> against `main` `c56962f`: `black_bloc/youtube.py` (`YouTubeClient`, the uploads feed, `youtube_*` keys, the
> linked-channel rows), `cogs/content/golive.py` (`_go_live`, `_go_live_once(member, info, source)`,
> `_end_live`, the Helix poller at ~1137, `source` ∈ {`twitch`, `presence`}), `config.youtube_api_key`, KI-11, and
> today's log: Pawpette's YouTube stream was caught only through her Twitch link (`golive.would_announce`, 13:13).
> ⚠️ Secret NAMES only.

## Owner ask, verbatim (2026-09-17 13:3x)

*"pawpette is currently live on youtube, it didnt seem to grab that, would we have needed to have her opt in for
youtube or what needed to change?"* → today only Discord's Streaming status with a YouTube link catches a YouTube
stream; no poller → *"can we do a youtube grabber for live? is that possible? i dont super care for uploads right now
since so many different people post"*.

## A. How a live stream is detected without burning the quota

The Data API's `search.list(eventType=live)` costs **100 units** per call against a **10,000/day** quota — polling
ten channels every ten minutes would need 144,000. So the detector is two-stage:

1. **Cheap probe, no quota:** `GET https://www.youtube.com/channel/<channelId>/live` (follow redirects, the
   bot's usual UA, 10 s timeout). When the channel is live the page resolves to a watch page whose HTML carries
   `"isLive":true` and a canonical `watch?v=<videoId>`; when it is not, there is no `isLive` (or `isUpcoming`).
   Parse ONLY those two facts with a tolerant regex; anything else on the page is ignored. A page that changes
   shape reads as "not live" and writes one `youtube.probe_unreadable` row per channel per hour, never a raise.
2. **Confirm + enrich, one paid call per detection:** when the probe says live and no open session exists,
   `videos.list(id=<videoId>, part=snippet,liveStreamingDetails)` — **1 unit** — confirms
   `liveStreamingDetails.actualStartTime` is set and no `actualEndTime`, and gives the title, the channel title and
   the thumbnail. Without `YOUTUBE_API_KEY` the confirm is skipped and the announcement uses the probe's video id
   with the title left as *Live now* (the go-live card's `EMBED_NO_TITLE`) — say so in the panel's health line.
   End of stream: the probe flipping to not-live (two consecutive misses, so a hiccup never ends a session), or
   the confirm's `actualEndTime` when a key exists.

The probe is a fallback-free scrape of a page YouTube may change; that is accepted and named in KI form by the
build (a KI-30 entry: *"YouTube live detection reads the /live page; a shape change makes every linked channel read
as offline until fixed"* — WATCHING, what would change it: YouTube exposing a cheap live endpoint).

## B. Who is polled — the linked channels, an opt-in that already exists

The rows the uploads feature keeps (`/youtube` ▸ **Link my channel**, staff **Link for somebody…**) are the list.
No new linking flow: linking a YouTube channel now means "announce my uploads AND my live streams", each behind
its own mode. The owner's *"i dont super care for uploads"* is `youtube_mode` staying off/shadow while
`youtube_live_mode` goes on — two modes, one link.

## C. Keys

| Key | Kind | Default | Help |
|---|---|---|---|
| `youtube_live_mode` | enum off/shadow/on | **off** | *"off, shadow (log what would be announced), or on — a linked YouTube channel going live is announced through the go-live feature, exactly like a Twitch stream"* |
| `youtube_live_poll_minutes` | int 2–60 | **5** | *"how often linked YouTube channels are probed for a live stream"* |
| `youtube_live_end_misses` | int 1–5 | **2** | *"how many probes in a row must read offline before a stream is treated as ended"* |

The announcement itself, the ping prefix, the end-of-stream rewrite, the streamer list, fan roles, cooldown and the
role filters are ALL the go-live feature's: the poller calls `_go_live(member, info, "youtube")` with a
`StreamInfo(platform=YOUTUBE, url=https://www.youtube.com/watch?v=<id>, title, game=None → "something"?, no —
game is left blank and `render` says *something*; the build may pass the channel title as `game` if the wording
reads better — decide and say)`, and `_end_live(guild, member, "youtube")`. `golive_mode` governs whether it posts
(shadow today → `golive.would_announce` with `source=youtube`). `youtube_live_mode` governs whether the poller runs
at all and whether its own rows are would-rows.

## D. Where it lives

`black_bloc/youtube_live.py` (pure: the probe parser, the confirm parser, the miss counter) + the poll loop in the
YouTube cog (`cogs/content/youtube.py` — beside the uploads sweep, same client, same health lines: *last probe*,
*last error*, *channels probed*, *quota used today* if a key exists). The `/youtube` panel's staff block gains
**Live streams are…** (off / shadow / on) beside **Announcements are…**, and its status lines show the live mode
and the last probe. The website's YouTube page gets the same two lines on its existing settings card. One log kind
family: `youtube.live_seen` (routine), `youtube.would_announce` is NOT needed — the go-live row already says
`source=youtube`; `youtube.probe_unreadable`, `youtube.live_confirm_failed` (important).

## E. Tests (mirror the package)

`tests/test_youtube_live.py`: the probe parser on a live page, a not-live page, an upcoming page, garbage; the
confirm parser; the miss counter. `tests/cogs/content/test_youtube.py`: a linked channel going live calls the
go-live path once with `source=youtube` and platform YouTube; a second probe while live calls nothing; two misses
end it; one miss does not; no key → no confirm, title *Live now*; `youtube_live_mode` off → no probe; shadow →
the go-live path still runs (go-live's own mode decides posting); an unreadable page → one row per hour, no
raise. Both orders.

## F. Docs

`code-notes.md`; this doc's `## Deviations`; KI-30; `youtube-*` guide in `guides_seed.json` (a step: *link your
channel, then your live streams are announced too*); `docs/access/RECOVERY.md` / `operator-read.md` only if a
new secret NAME appears (none expected — `YOUTUBE_API_KEY` exists); `sweeps.md` rows `YL-a…`; `cutover-plan.md`
row 3c gains the live half; `architecture.md` fact line for the new module. NOT `TODO.md` / `DONE.md` /
`deploys.log`.

## Deviations

*Written 2026-09-17 by the build agent on branch `youtube-live` (commit `3cec53e` + the docs
commit), off `main` `9c08936`. Everything below is a departure from §A–§F above; where §C left a
choice open it is decided here and marked ✅ DECIDED.*

1. ✅ **DECIDED — `game` is left BLANK, so the card reads *something*.** §C offered the channel
   title as `game` "if the wording reads better". It does not: the shipped template is
   *"REGULATORS! Mount up! **{name}** is currently streaming **{game}**!"*, and the channel title
   there reads *"currently streaming **Lofi Girl**"*, which asserts a category YouTube never gave
   us. `stream_info()` passes `game=None` and `golive.render` fills `GAME_FALLBACK` — *something* —
   which is the same thing a Twitch stream with no category set gets. The guide's *"Your game shows
   as something"* fault now says so out loud for YouTube.
2. **The probe's timeout is the client's existing 15 s, not §A's 10 s.** `REQUEST_TIMEOUT_SECONDS`
   is set once on the shared `aiohttp.ClientSession` in `YouTubeClient`; a per-request 10 s would
   have meant changing `_request`'s signature, which every existing uploads test fakes. Not worth a
   shared-boundary change for 5 s.
3. **A third marker was needed: READABILITY.** §A's two facts cannot tell "not live" from "the page
   changed shape" — both are *no `isLive`*. Without a third reading, `youtube.probe_unreadable`
   would fire on every offline channel, every probe. `read_page` therefore looks for
   `ytInitialData` or a `<link rel="canonical">` first; no match at all is `readable=False`, which
   is what writes the KI-30 row. An offline channel page HAS both, so it reads as a plain, quiet,
   readable *not live*. Verified against the real markers (item 9).
4. **An UNREACHABLE probe is not a quiet probe.** §A says two consecutive misses end a session. A
   network error is not a miss here: it leaves the counter untouched, records `last_probe_error`,
   and the session stays open. Checklist 10 — a check that could not run must not be reported as a
   check that came back negative. An UNREADABLE page IS a miss, exactly as §A says.
5. **`youtube.live_seen` fires on the TRANSITION, not on every live probe.** §D lists it as
   routine; one row per channel per five minutes for the whole length of a stream would be dozens
   of rows per stream. It is written once, when the probe first sees a broadcast the bot has not
   acted on. Its shadow twin is `youtube.would_live_seen` (§C: the live half shadows its OWN rows;
   `golive_mode` still decides whether anything posts, so a shadow live-mode still produces
   `golive.announce` when go-live is on).
6. **Three log kinds, not two.** §D named `youtube.probe_unreadable` and
   `youtube.live_confirm_failed`. Added: `youtube.live_announce_failed` (the go-live cog is not
   loaded — otherwise a stream would be silently dropped, checklist 2) and `youtube.live_mode` (the
   settings write, matching `youtube.mode`). `probe_unreadable` is in `logkinds.IMPORTANT` by hand
   — its name matches no `IMPORTANT_SUFFIXES` entry.
7. **The `/youtube` panel's **Live streams are…** select stands down while staff are picking a
   member.** Discord allows five action rows; the root panel already uses 0–4, and row 4 is
   `WhoPick`'s the moment **Link for somebody…** is pressed. The live select renders on row 4 at
   every other time. A control that renders only when it is valid is the house style; there was no
   sixth row to put it on.
8. **Two public entry points were ADDED to the go-live cog**, `go_live(member, info, source)` and
   `end_live(guild, member, source)` — one line each, wrapping `_go_live` / `_end_live`. The
   alternative was another cog reaching for a private method by `getattr`. `_still_live` also
   gained a `source == "youtube"` branch that asks the YouTube cog `is_live_now(user_id)`; an
   unanswerable probe leaves the session open, exactly as an unanswerable Helix call does
   (checklist 4 — a deploy inside a stream must not strand it or re-announce it).
9. ⚠️ **ONE real probe was made, by hand, to verify the markers exist** —
   `https://www.youtube.com/channel/UCSJ4gkVC6NrvII8umztf0Ow/live` (Lofi Girl) on **2026-09-17
   13:4x**, with the bot's own UA. It answered **200**, **1,257,542 bytes**, and carried
   `"isLive":true`, NO `isUpcoming`, `<link rel="canonical" href="https://www.youtube.com/watch?v=3PFJ9SETS4M">`,
   `"videoId":"3PFJ9SETS4M"` and `ytInitialData`. **No `"isLiveNow"` and no `"liveBroadcastDetails"`
   were present**, so neither is used. The Data API was NOT called (no key here, and the quota is
   the owner's), so ⚠️ **the confirm path is proved by fixtures alone and has never met a real
   `videos.list` answer.** The three test fixtures are hand-written from those markers, not
   captures — a real page is 1.2 MB.
10. **`/api/youtube/status` gained nine fields** rather than a route of its own (§D said the site's
    YouTube page gets "the same two lines"): `live_mode`, `live_minutes`, `live_end_misses`,
    `live_running`, `last_probe_at`, `last_probe_error`, `probed`, `quota_today`, `live_now`. One
    function, `cogs/content/youtube.live_health(bot, guild)`, is the single source for the panel
    AND the page, so the two cannot disagree. `contract.json` and the mock carry all nine.
11. **The guide edit reaches a FRESH seed only, for a new step or fault.** `guides.refresh_seeds`
    zips existing steps by position and rewrites `seed_do`/`seed_expect`; it never inserts a step
    and never touches faults or facts. So on a guild already seeded, the **amended** step 3 text and
    the **amended** *"game shows as something"* fault reach `seed_do`/`seed_expect`, but the NEW
    step 6, the NEW YouTube fault and the NEW `youtube_live_mode` fact do not appear until a guild
    is seeded from scratch. ⚠️ **This is a pre-existing limitation this build did not fix** — it is
    named here rather than worked around.
12. ⚠️ **`docs/info/README.md`'s row for this doc still reads "📐 DESIGN, dispatching to Opus"**,
    which is now false. §F did not list it and the build did not touch it; the conductor updates it
    at the merge.
13. **`golive.embed_footer` became a dict lookup** so a YouTube-sourced card reads *Black Bloc · via
    YouTube* rather than *via Discord activity*, which is what the two-branch version would have
    said. Twitch and presence are unchanged.
14. ⚠️ **KI-26 fired TWICE during this build, and neither time was the hang.** Both were a
    COLLISION: the `front-door` build started its own `pytest -n auto` 4 s (14:52) and 28 s (14:08)
    after mine, putting ~66 workers on the box; both runs wrote nothing for 10+ minutes. Killing
    only my own process tree (`env.exe` → `python.exe` → `python3.12.exe` → workers, by PID, never
    by image name) left the other build's run untouched and it finished normally. **The tell that
    it is a collision and not the hang: two `-m pytest` controllers alive at once with different
    `PYTHONPATH`s in their parent `env.exe` command lines.** A second run at `-n 8` passed in 52 s
    while the other build's `-n auto` was still going — that is the neighbourly setting when two
    builds share the machine.

### The datacenter page (fix) — 2026-09-17, branch `youtube-live-fix` off `main` `ddd6fdc`

*§A's probe was written against a page a HOME machine gets. Measured by the conductor 2026-09-17
18:14–18:20, from the Fly machine (a datacenter address), the same URL answers **200** with
YouTube's **"Sign in to confirm you're not a bot"** page: `ytInitialData` present (so §A item 3's
readability marker says READABLE and no `probe_unreadable` row is written), `"isLive":true` present
**once** for a live channel and **absent** for an offline one (so the live signal SURVIVES the
wall), **no `<link rel="canonical">` at all**, and about **180** `"videoId"` fields belonging to
unrelated videos — the first of which is NOT the live stream. `quota_today` stayed 0 and both
`probe_all` runs reported no error: the feature simply went quiet, which is exactly the shape KI-30
was filed to watch for. The same page from a home machine was 200, ~1.29 MB, `"isLive":true` ×2,
canonical present.*

15. **The `"videoId"` fallback is GONE; `video_id` comes ONLY from the canonical link.** Deviation
    9's original page carried both and the fallback looked free. On the bot-check page it is
    actively wrong — it hands back a stranger's video, which would be announced as the streamer's
    stream. A reading that can be confidently wrong is worse than one that is absent, so
    `read_page` now returns `video_id=None` there and the caller deals with it.
16. **A third probe OUTCOME: *live, id unknown*.** `Probe.announceable` (live AND an id) is
    unchanged, but the cog no longer routes on it — it routes on `probe.live`, and
    `live and not video_id` is its own path. `announceable` stays the honest two-part reading §A
    wanted; the cog is where the two are reconciled.
17. **With a key, ONE `search.list(part=id, channelId, eventType=live, type=video, maxResults=1)`
    — 100 units — on the TRANSITION only.** §A ruled the search out as a POLLER (144,000 units a
    day for ten channels). It is affordable as a one-off: the channel is remembered as live
    (`live_video[channel_id]`, with `LIVE_ID_UNKNOWN` = `"?"` as the sentinel when even the search
    could not say), so the next probe searches nothing. ⚠️ **A day with one linked channel that
    goes live once costs 101 units of 10,000** — 100 for the search, 1 for the existing confirm.
    Ten channels each going live once is 1,010. The row that catches a regression here is sweep
    **`YL-m`**: a quota climbing by 100 per probe is the bug.
18. **Without a key, the announcement is the CHANNEL's own `/live` page.** `channel_info()` builds
    `StreamInfo(url=https://www.youtube.com/channel/<id>/live, title=None, game=None,
    thumbnail_url=None)`, so the card reads **Live now** (`EMBED_NO_TITLE`) over a working link to
    whatever is playing, with no thumbnail — `YOUTUBE_THUMBNAIL` needs a video id and guessing one
    would be the same lie as item 15. This is the keyless shape of Deviation 1, one step further.
19. **`Probe.botcheck` exists, and it is a REPORTING field only.** It never changes what is
    announced. It reaches `live_health()` as `botcheck` (the LAST probe, not a tally), and from
    there both the `/youtube` panel's staff half and `/api/youtube/status`, plus one row on the
    Go-live page's **How live streams are spotted** card — the surfaces were already one function,
    so the field cost one line each. It also travels in the `youtube.live_seen` /
    `would_live_seen` details, which is where a later session will read why an id was missing.
20. **Two log kinds, not one.** §3 of the brief asked for `youtube.live_id_searched` (ROUTINE,
    carrying `channel_id`, `units: 100` and the id). `youtube.live_search_failed` was added beside
    it — IMPORTANT by the `_failed` suffix, no table edit — because a search that refuses falls
    back to the keyless announcement, and a fallback nobody can see is the silent-failure the
    review checklist exists to stop. It mirrors `youtube.live_confirm_failed` exactly.
21. **`is_live_now()` now answers `probe.live`, not `probe.announceable`.** The reconcile asks *is
    this member still live*, and behind the wall the honest answer is yes-with-no-id. Left as it
    was, a restart inside a stream would have read the wall as offline and ended the session —
    the exact failure Deviation 8 and checklist 4 were about, arriving by a different door.
22. **`self.confirms` now counts UNITS, not confirms.** It is what `quota_today` reads, and a
    counter labelled *quota used today* that ignores the 100-unit call would be a measurement
    wearing another's clothes. `_spent(units)` takes the number; the attribute keeps its name so
    nothing else moves.
23. **The two new fixtures are named `youtube_botcheck_live_page.html` and
    `youtube_botcheck_offline_page.html`**, not the brief's `botcheck_live.html` — the family in
    `tests/fixtures/` is `youtube_*_page.html` and one odd name out is how a directory stops being
    scannable. Both are hand-written from the measured markers (1,317 and 1,155 bytes), not
    captures; ⚠️ **no real bot-check page was ever saved to this repo** and this build could not
    reach one — every claim above about the wall is the conductor's measurement, not the build's.

### The silent open-session path (follow-up) — 2026-09-17, branch `youtube-live-seen` off `main` `568c177`

*Measured by the conductor on the LIVE bot at v133, 2026-09-17 18:5x: the bot's own `probe_live`,
run inside the Fly container, read Pawpette's channel as `Probe(live=True, video_id=None,
botcheck=True)` — v133 working exactly as Deviations 15-23 intend. Nothing was announced, correctly,
because her TWITCH go-live session (#139, source `twitch`, `ended_at` null) was still open and the
one-announcement-per-person rule holds. But that branch of `_live_now` stored `live_video[channel_id]`
and RETURNED with no action-log row at all, and `live_health`'s `live_now` counts open go-live
sessions whose source is YouTube only - so `/api/youtube/status` read `live_now 0`, `quota_today 0`
and no `youtube.*` row existed. A probe that worked was indistinguishable from a probe that never
ran.*

24. **The open-session branch writes ONE routine `youtube.live_seen` row, `announced: false`,
    `because: "open_session:<source>"`.** Same kind as the announcing path - and the same ternary,
    so a shadow live half writes `youtube.would_live_seen` (both kinds already exist; nothing was
    added to `logkinds.py`, and its guard wants a STRING LITERAL at the `log_action` call, so the
    two names could not be lifted into module constants). It is written on the TRANSITION only -
    when `live_video` had no entry for the channel - so a five-minute poll through a three-hour
    stream still leaves one row, the same rule Deviation 5 set for the announcing row. Three
    consequences worth naming:
    - **Both rows are now built by one helper, `live_seen_details()`**, so `channel_id`,
      `video_id` (None -> `null`), `botcheck` and `mode` cannot drift apart between the two
      writers. Each caller adds its own tail.
    - **The announcing row gained `announced: true`.** An `announced` key present on one kind of
      row and absent on the other is a field a reader has to guess at; checklist 2 wants a dry run
      and a real one distinguishable at a glance, and this is that argument one level down.
    - ⚠️ **a stream that changes video id WITHOUT going offline writes no second row.** The
      condition is literally "`live_video` had no entry", per the brief; the id-changed case falls
      through to the announcing branch, where the open-session check then returns as before. It is
      the rarest case and it is named here rather than guessed at.
25. **`live_health` gained `reading_live` AND `reading_live_channels`; only the first is
    surfaced.** `reading_live` is `len(cog.live_video)` - how many channels the probe currently
    reads as live, whatever the sessions table says - and it reaches the `/youtube` staff half
    (`**reading live now** - N`, beside `**live now**`), `/api/youtube/status` (`reading_live`) and
    the Go-live page's *How live streams are spotted* card (*Reading live now*), exactly the three
    surfaces Deviation 19 gave `botcheck`. `reading_live_channels` (the sorted ids) stays in the
    health dict for the tests and for a later session; a list of channel ids nobody can click is
    noise on a status card. ⚠️ **`live_now` was NOT changed** - it still counts
    YouTube-source sessions, which is the honest answer to *what did go-live announce*; the new
    number is the honest answer to *what does the probe see*, and the two disagreeing is now
    information rather than a silence.
26. ⚠️ **none of this was verified against the live bot.** The suite proves the row, the
    once-per-stream rule and both health numbers against fixtures and a fake client; the wall
    itself is still unreachable from here (Deviation 23), and no browser rendered the Go-live card.
    Sweeps **594–595** (`YL-o`, `YL-p`) are the proof that is missing, and like 586-590 they can only
    be run on Fly.
