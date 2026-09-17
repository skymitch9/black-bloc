# YouTube live — a poller that catches a linked channel going live, feeding the go-live path

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus 2026-09-17 13:3x as
> branch `youtube-live`** (v126, beside `front-door` and `tempvoice-shadow`). **Last verified: 2026-09-17 13:29**
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

*(the build agent writes here what it had to do differently, dated)*
