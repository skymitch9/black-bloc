# Phase 16 — YouTube upload announcements (F3)

> ⚠️ **SUPERSEDED IN PART, 2026-09-03 — the slash surface below is gone.** `/golive` and
> `/twitch` and all eight of their subcommands (`logs`, `optout`, `optin`, `status`, `mode`,
> `test`, `link`, `unlink`) were replaced by ONE `/golive` command that opens an ephemeral
> panel; every subcommand is a button, a select or a modal on it. The behaviour this doc
> describes is unchanged — the announcer, the poller, the sessions, the settings and the log
> kinds are all exactly what it says. Only the way in moved:
> [`golive-panel-design.md`](golive-panel-design.md). This doc is NOT rewritten.

> **Audience:** the Opus builder first, reviewers second, the owner for the
> decisions table. **Status:** TRACKED — DESIGN, written 2026-09-02 by the
> Fable session (NEXT WAVE item 2). Secret NAMES only.
> Last verified: **2026-09-02** — the "what exists" rows were read in the code
> today (`cogs/content/golive.py:poll_once`, `twitch.py:TwitchClient`,
> `groq.py` aiohttp pattern, schema 20 + Phase 15's planned 21). ⚠️ NOT
> verified: the YouTube feed/API behaviours below are from the documented
> platform contract, not measured against a live channel — the builder's
> first job is to measure them (§J).

## The ask

TODO F3: *"Youtube maybe"* (owner, 2026-08-26). Go-live via YouTube presence
already works (sweeps row 4). This phase adds **new-upload posts**: "X just
dropped a video" when a linked member publishes.

## What exists (reuse, do not rebuild)

| Piece | Where |
|---|---|
| Poll-loop shape with health, degraded-after-N-failures log line, `loop_health` for the Health tab | `cogs/content/golive.py:poller / poll_once / _poll_failed` |
| Link store + `/twitch link` + dashboard `linkCard` | `golive_links`, `cogs/content/golive.py:link`, `page-golive.js` |
| aiohttp client with injectable `request` for tests | `twitch.py:TwitchClient`, `groq.py` |
| Guarded post + shadow/would_* logging + TEST_MODE refusal | `cogs/content/golive.py:_post`, `events.py:post_to_announce` |
| Ping prefix + `AllowedMentions` | `golive.py:render`, Phase 15's fan roles |
| Config surface | `config.py` (pydantic-settings) — the only reader of `.env` |

## Decisions (defaults chosen 2026-09-02; each is a settings key or env NAME)

| # | Question | Default | Key |
|---|---|---|---|
| D1 | Data source | **The public Atom feed** `https://www.youtube.com/feeds/videos.xml?channel_id=UC…` — no key, no quota, ~15 latest entries. `YOUTUBE_API_KEY` (env, optional) upgrades: handle → channel id resolution, live-vs-upload classification, Shorts detection by duration | env `YOUTUBE_API_KEY` (unset = feed only, never an error) |
| D2 | Who links | **Members link themselves** (`/youtube link`), staff can link anyone from the dashboard; linking IS the opt-in (same as Twitch) | — |
| D3 | Where posts go | `youtube_channel_id`; **blank = the go-live channel** (`golive_channel_id`) | `youtube_channel_id` |
| D4 | Who is pinged | `youtube_ping_role_id` (blank pings nobody) **plus** the uploader's Phase 15 fan role when `youtube_ping_fan_roles` is on (**default on**) | `youtube_ping_role_id`, `youtube_ping_fan_roles` |
| D5 | Shorts | **not announced** by default | `youtube_announce_shorts` bool |
| D6 | Live streams that appear in the feed | **skipped** (go-live presence already covers them); without the API key the feed cannot say, so the fallback rule is "skip an entry while its uploader has an open go-live session on platform `youtube`" | — (documented residual, KI entry if it bites) |
| D7 | Wording | `**{name}** just dropped a new video: **{title}** {url}` — Discord's own link preview is the card | `youtube_template` |
| D8 | Feature mode | **`off`** at deploy → shadow → on per the cutover ladder | `youtube_mode` off/shadow/on |
| D9 | Poll cadence | **10 minutes** (feed is cheap; ETag/If-None-Match honoured so an unchanged feed costs a 304) | `youtube_poll_minutes` int, floor 5 |
| D10 | Backfill | **Never announce history**: at link time the feed's current entries are stored as seen | — |

## A. Storage — schema **22** (additive; 21 is Phase 15's)

```sql
CREATE TABLE IF NOT EXISTS youtube_links (
    user_id     INTEGER PRIMARY KEY,
    channel_id  TEXT    NOT NULL,        -- UC…
    handle      TEXT,                    -- @name if known
    title       TEXT,                    -- channel title from the feed
    linked_at   TEXT    NOT NULL,
    etag        TEXT,
    seeded      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS youtube_videos (
    video_id             TEXT PRIMARY KEY,
    user_id              INTEGER NOT NULL,
    channel_id           TEXT    NOT NULL,
    title                TEXT,
    published_at         TEXT    NOT NULL,
    seen_at              TEXT    NOT NULL,
    kind                 TEXT    NOT NULL DEFAULT 'video',  -- video | short | live | unknown
    announced_at         TEXT,
    announced_message_id INTEGER,
    mode                 TEXT                                -- on | shadow at announce time
);
CREATE INDEX IF NOT EXISTS youtube_videos_user ON youtube_videos(user_id, published_at);
```

## B. `black_bloc/youtube.py` — the client + parsing (pure, testable)

- `parse_feed(xml) -> list[Video]` (`video_id`, `title`, `url`, `published`,
  `channel_id`, `author`), tolerant of a missing entry field.
- `YouTubeClient(api_key: str | None, request=None)`: `fetch_feed(channel_id,
  etag) -> (status, etag, videos)`; with a key: `resolve(handle_or_url_or_id)`
  via `channels.list` (`forHandle` / `id` / `forUsername`), `classify(video_ids)`
  via `videos.list(part=contentDetails,liveStreamingDetails,snippet)` →
  `short` (duration ≤ 60 s), `live` (has `liveStreamingDetails`), `video`.
- `resolve_without_key(text)`: accepts `UC…` ids and `youtube.com/channel/UC…`
  URLs directly; for `@handle` / `youtube.com/@handle` / `/c/` / `/user/` it
  GETs the channel page and reads `"channelId":"UC…"` (or the
  `<link rel="canonical">` channel URL) — best effort, refuses in words when it
  cannot ("I couldn't turn that into a channel id — paste the channel URL that
  starts with youtube.com/channel/UC…, or ask staff to set a YouTube API key").
- `render(template, video, member, *, ping_role_id, fan_role_id)` mirrors
  `golive.py:render` (unknown placeholder → the default template + a warning).
- Errors are `YouTubeError` with a words-first message; HTTP 429/5xx count as
  poll failures (degraded line after 3 in a row, same constant shape as Twitch).

## C. `black_bloc/cogs/content/youtube.py` — the cog

- `tasks.loop(minutes=youtube_poll_minutes)` poller (re-read the setting each
  tick via `change_interval`); `loop_health` for the Health tab; `before_loop`
  waits for ready.
- `poll_once()`: for every link (dedupe by channel_id like the Twitch poller
  warns on double links): fetch with ETag → 304 skip; new entries = ids not in
  `youtube_videos`; first fetch after link with `seeded = 0` stores all as seen
  (`announced_at NULL`, `mode NULL`) and sets `seeded = 1` — announces nothing
  (D10); otherwise classify (API key) or apply the D6 fallback; announce
  `video` (and `short` if D5 on) through the ONE guarded post path; record the
  row before posting (a crash between store and post loses one announcement,
  never duplicates — checklist: status flag travels with the value).
- Announce: mode `off` → nothing; `shadow` → `youtube.would_announce` with the
  rendered text; `on` → post to `youtube_channel_id` or the go-live channel;
  TEST_MODE refusal → `youtube.would_announce reason=test_mode`. Details logged:
  `video_id`, `kind`, `url`, `text`, `channel_id`, `source: feed|api`.
- Member group **`/youtube`** (visible to all): `link <channel>`, `unlink`,
  `status` (my link, last video seen, whether uploads are announced here).
- Staff group **`/uploads`** (manage_messages default perms, like the other
  staff groups): `mode <off|shadow|on>`, `setup [channel] [ping_role]`,
  `link-for <member> <channel>`, `unlink-for <member>`, `list`, `logs`.
- Registered in `bot.py:COGS`; `/help` entry; `chat_data.py` FEATURES line
  ("how do I get my uploads posted? → `/youtube link`").

## D. Settings registry (+ labels.js, mock key list, exact-key-set test)

| Key | Type | Default |
|---|---|---|
| `youtube_mode` | mode | `off` |
| `youtube_log_level` | level | `important` |
| `youtube_channel_id` | channel | blank (= go-live channel) |
| `youtube_ping_role_id` | role | blank |
| `youtube_ping_fan_roles` | bool | `true` |
| `youtube_announce_shorts` | bool | `false` |
| `youtube_template` | str | D7 |
| `youtube_poll_minutes` | int (≥5) | `10` |

Config (`config.py`): `youtube_api_key: str | None = None`. Runbook secret
list + RECOVERY custody row (vault item title `YOUTUBE_API_KEY`) + `.env.example`
line — NAME only.

## E. Dashboard + API

`api/tools/youtube.py`: `GET /api/youtube/links` (member, channel, title,
handle, linked_at, last video), `POST /api/youtube/links {member_id, channel}`
(staff link-for; resolves like the slash command), `DELETE
/api/youtube/links/{member_id}`, `GET /api/youtube/videos?limit=50` (the seen
table with announced/would/skipped state), `GET /api/youtube/status` (key
present yes/no, poll health, feed 304 ratio). A **YouTube uploads** section on
the Go-live page (`page-golive.js`): mode switch, settings namespace
`youtube_*`, link card (member picker + channel text), links table with
Unlink, recent videos table, Logs filtered to `youtube.*`. Mock server +
`contract.json` + `check.mjs` green; the Health tab picks the loop up by
type (KI-7 discovery) — add the cog row to the parametrised
`tests/api/test_status.py`.

## F. Logs (`youtube.*`)

`youtube.link`, `youtube.unlink`, `youtube.seeded` (info, with the count),
`youtube.announce`, `youtube.would_announce`, `youtube.skipped` (info; reason
`short|live|open_session`), `youtube.post_failed`, `youtube.poll_degraded`,
`youtube.resolve_failed`.

## G. Tests (mirror)

`tests/test_youtube.py` (feed parsing incl. a real captured feed sample stored
under `tests/fixtures/`, ETag handling, resolve paths, render), `tests/cogs/
content/test_youtube.py` (seed-then-announce, dedup, shadow, test-mode refusal,
shorts off/on, D6 fallback, degraded counter, double-link warning), `tests/api/
tools/test_youtube.py`, `tests/storage/test_db.py` (schema 22),
`tests/test_settings_store.py`, `tests/test_config.py` (key optional),
`tests/test_bot.py` (COGS), `tests/api/test_status.py` (loop row).

## H. Docs landing with the build

`code-notes.md`; `access/sweeps.md` rows; `cutover-plan.md` ladder row;
`feature-list.md` F3; `architecture.md` counts; runbook boot line + secret
list; `RECOVERY.md` custody row; `.env.example`.

## I. Residuals to record in `KNOWN_ISSUES.md` at landing

- Without `YOUTUBE_API_KEY`, a scheduled/live broadcast that appears in the
  feed while the member has no open `youtube` go-live session will be
  announced as an upload (D6 fallback). What would change it: the key set, or
  1 mis-announcement.
- Feed latency: YouTube's feed can lag a publish by minutes; the poll adds up
  to `youtube_poll_minutes` more. Accepted.

## J. First task for the builder — measure, don't assume

Before writing the cog, fetch one real public channel feed (any large channel)
with `curl -I` / `curl` in the worktree and confirm: the `channel_id=` URL
shape, that entries carry `yt:videoId`, `published`, `title`, `link href`, and
whether a second request with `If-None-Match` returns 304. Record the result
in `code-notes.md` beside `parse_feed`. If the feed no longer behaves this way,
STOP and report instead of building around it.
