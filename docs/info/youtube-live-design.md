# YouTube live — a poller that catches a linked channel going live, feeding the go-live path

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v126** — merge `99c307c`, release `e537b2c`, deployed **2026-09-17 14:45** Phoenix; `youtube_live_mode` ships OFF (the owner flips it); the `## Deviations` foot is the truth where it departs from the body; sweeps **534–542** are the owner's; KI-30. Was: 📐 DESIGN, dispatching to Opus 13:3x. **Last verified: 2026-09-17 13:29**
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
