# Phase 2 design — go-live feed (F1 + F2 + the F5 hook)

> ⚠️ **SUPERSEDED IN PART, 2026-09-03 (v70, `0aeed72`) — the slash surface below is gone.** `/golive` and
> `/twitch` and all eight of their subcommands (`logs`, `optout`, `optin`, `status`, `mode`,
> `test`, `link`, `unlink`) were replaced by ONE `/golive` command that opens an ephemeral
> panel; every subcommand is a button, a select or a modal on it. The behaviour this doc
> describes is unchanged — the announcer, the poller, the sessions, the settings and the log
> kinds are all exactly what it says. Only the way in moved:
> [`golive-panel-design.md`](golive-panel-design.md). This doc is NOT rewritten.

> **Audience:** the Phase 2 build agent and the reviewer. **Status:** TRACKED ·
> ✅ **LIVE since 2026-08-26** (shipped in `shadow`) — deployed `2026-08-27T02:19:20Z`
> as `50d896d` (`deploys.log` line 4, `synced 6 app commands`); `DONE.md` → "2026-08-26 —
> Phase 2 live in shadow: go-live feed (F1/F2) + review fixes". The two 2026-08-27 sections at
> the foot (YouTube on the presence path, the announcement card) landed on top of it.
> ⚠️ Fly release numbers were not written into `deploys.log` until **v59** (2026-09-03), so
> this landing has a date and a commit but no `vNN`.
> **Last verified: 2026-09-11 08:45** — re-checked against the tree at `1d090e5`:
> `black_bloc/twitch.py`, `black_bloc/golive.py` and `cogs/content/golive.py` all exist;
> all **eight** `golive_*` keys in the table below are in `KEY_TYPES`, as are `golive_embed`,
> `golive_end_mode` and `golive_end_suffix` added later; `TwitchClient.get_users/get_streams/
> get_games` and `extract_stream`/`render`/`should_announce` all exist. ⚠️ **NOT checked:**
> anything in Discord — no card has been seen rendered, the Helix response shapes are still
> from Twitch's docs, and nothing in this pass met Discord or a browser.
> Before that, **2026-08-26** — incumbent behaviour was measured
> (`archive/current-bots/discord-scan-2026-08-26.md` §G, 199 YAGPDB posts;
> `yagpdb-dashboard-2026-08-26.md`); Twitch API constraints are from the
> vendor docs as summarised in `reference-bots.md` and flagged where they are
> from memory. Depends on Phase 1 (settings store, action log).

## Owner decisions this implements

- **Discord presence is PRIMARY; Twitch is the FALLBACK/enrichment.**
- Both detection paths; opt-out covers both; no stats/leaderboard.
- Channel `#live-now` (`1225457308230746202`); keep the `REGULATORS! Mount
  up!` wording; optional *Live* role; require/ignore role filters.
- Rollout: shadow → watch → on. Test policy applies.

## What the incumbent does (to match or beat)

~8 posts/day, 30 streamers. Template
`REGULATORS! Mount up! **{login}** is currently streaming **{game}**! Check it out: https://www.twitch.tv/{login}`.
Defects to beat: game renders as `****` when unset (4/199); re-posts on
restart/category change; Twitch login ≠ Discord name is invisible to it.

## Shape

```
black_bloc/
├── twitch.py                    ← Helix client: app token (client credentials), get_users, get_streams; fake-able
├── golive.py                    ← pure logic: extract_stream(activities) → StreamInfo|None, render(template, info), debounce decision
└── cogs/content/golive.py       ← the cog: presence listener, poller, commands, announcements
tests/
├── test_twitch.py · test_golive.py · cogs/content/test_golive.py
```

Schema v3 (additive):

```sql
CREATE TABLE IF NOT EXISTS golive_links   (user_id INTEGER PRIMARY KEY, twitch_login TEXT NOT NULL, twitch_user_id TEXT, linked_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS golive_optout  (user_id INTEGER PRIMARY KEY, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS golive_sessions(
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
    source TEXT NOT NULL,             -- 'presence' | 'twitch'
    url TEXT, game TEXT, title TEXT,
    started_at TEXT NOT NULL, ended_at TEXT, announced_message_id INTEGER, mode TEXT NOT NULL  -- 'shadow'|'on'
);
```

Settings keys (registry in `settings_store.py`):

| key | type | default |
|---|---|---|
| `golive_mode` | enum `off|shadow|on` | `shadow` |
| `golive_channel_id` | channel | `test_channel_id` while TEST_MODE, else `1225457308230746202` |
| `golive_template` | text | `REGULATORS! Mount up! **{name}** is currently streaming **{game}**! Check it out: {url}` |
| `golive_live_role_id` | role | none |
| `golive_require_role_id` / `golive_ignore_role_id` | role | none / none |
| `golive_cooldown_minutes` | int | 60 |
| `golive_ping_role_id` | role | none (F5/F14 hook — rendered as `<@&id>` prefix when set) |

## Detection

**Primary — presence.** `on_presence_update(before, after)` in the cog:
`extract_stream(after.activities)` returns `StreamInfo(url, game, title,
platform)` when any activity is `discord.Streaming` (or `type ==
ActivityType.streaming`) — else `None`. Transitions:
- none → stream: candidate go-live.
- stream → none: mark the open session `ended_at` after a **grace of 120 s**
  (a task; cancelled if the stream reappears) — presence flaps.
Bots are ignored. Members in `golive_optout` are ignored. `require_role` /
`ignore_role` filters apply.

**Fallback — Twitch Helix polling** (no EventSub: websocket EventSub needs a
*user* token and webhook EventSub needs a public HTTPS callback — neither
fits this bot; **from vendor docs, re-verify against reference-bots.md**).
Every 60 s, for all `golive_links`, `get_streams(user_login=[…])` in batches
of 100 with the app token. A login that is live and has no open presence
session → candidate go-live with `source='twitch'`; a login that is no
longer live → end its twitch session. Poller is a `tasks.loop`, started only
when `TWITCH_CLIENT_ID`/`SECRET` are set; otherwise the feature logs once
that Twitch enrichment is off and continues on presence alone.

**Enrichment.** On a presence go-live, if the member has a link, call
`get_streams` once for that login to fill `title`/`game` when the presence
lacks them. Discord's own link preview supplies the image — no thumbnail.

## Debounce (beats the incumbent)

`should_announce(user_id, now, last_session)` *(built as
`should_announce(now, last_session, cooldown_minutes)` — `golive.py:299`)* → True only if there is no
open session for the user AND (no previous session OR `now -
last.ended_at ≥ cooldown`). Category/title changes during a stream never
re-announce; a restart of the bot re-derives open sessions from the DB and
does not re-post for streams already announced (`announced_message_id`).

## Announcing

`render(template, info, member)` with `{name}` (member display name), `{game}`
(fallback: `"something"` when empty — never `****`), `{title}`, `{url}`. Post
to `golive_channel_id`; store `announced_message_id`; `log_action("golive.announce")`.
When the session ends, **edit** the message to append ` — stream ended` (no
delete). Live role: add on go-live, remove on end, only when `golive_mode ==
'on'` (role edits are invisible to the guard, so in shadow they are logged
as `would add role`).

**Modes.** `off`: listener inert. `shadow`: everything computed and logged
(`golive.would_announce` with the rendered text) to the log channel, nothing
posted to the feed, no roles. `on`: posts + roles. Default `shadow`; the
owner flips to `on` per the rollout rule after watching a few days of
shadow entries next to YAG's real posts.

## Commands

*(Removed: every command in this section retired at **v70**, 2026-09-03 — `/golive` opens the
panel and each one is a button, a select or a modal on it. See
[`golive-panel-design.md`](golive-panel-design.md).)*

- `/golive optout` · `/golive optin` — anyone; ephemeral confirmation.
- `/twitch link <login>` · `/twitch unlink` — anyone; validates the login
  via `get_users` when Twitch creds exist (plain sentence if not found).
- `/golive status` — staff: mode, channel, counts (links, opt-outs, open
  sessions), whether Twitch polling is running.
- `/golive mode <off|shadow|on>` — staff; logs the change.
- `/golive test` — staff: renders an announcement for the caller as if live
  (into the current channel — the guard keeps it in the test channel).

## Test mode

The guard forces every post into the test channel; `shadow` default means
nothing posts anyway. `/golive test` is how the owner sees the rendering.
Live-role changes are skipped unless mode is `on` AND
`bot.guard is None` — a role change in test mode is refused and logged.

## Tests (offline)

`test_golive.py`: `extract_stream` on synthetic activity objects (streaming,
non-streaming, mixed); `render` with empty game; `should_announce` cooldown
matrix; `test_twitch.py`: token caching + refresh on 401, `get_streams`
batching, with a fake HTTP session; `cogs/content/test_golive.py`: mode
transitions, opt-out filtering, restart re-derivation from DB rows.

## Not in this phase

EventSub; YouTube (F3); the favourite-streamer per-person roles (F14) — the
`golive_ping_role_id` hook is the seam they plug into; the "scan for
inactive streamers" idea (still TBD with the owner).

## Definition of done

Same as Phase 1: green tests, clean ruff, code-notes entries, architecture
tree, three commits on a clean tree (twitch client → pure logic → cog), not
pushed. Live verification is the reviewer's deploy + the owner running
`/golive test` and going live once with mode `shadow`, then reading the log.

## 2026-08-27 — YouTube joined the presence path (F3)

"Not in this phase" above said YouTube was F3 and out of scope. The owner
asked for it on 2026-08-27 and it landed here rather than in a phase of its
own, because presence detection was already platform-agnostic and only the
Twitch-shaped edges needed fixing:

- `StreamInfo.platform` is now carried end to end: stored on the session row
  (`golive_sessions.platform`, schema 12, additive), rendered as the
  `{platform}` template field (blank when unknown, so existing templates are
  byte-identical), listed by `/golive status`, returned by
  `GET /api/golive/sessions`.
- **Twitch enrichment is refused for a named non-Twitch platform.** This was a
  real defect, not a precaution: a member with a `/twitch link` row who
  streamed on YouTube got a Helix lookup whose result overwrote their YouTube
  game and title.
- `_still_live` needed no change — it consults presence first and only asks
  Helix about a `source == 'twitch'` session, so a YouTube session is governed
  by presence alone. Now covered by a test.
- `/golive test` takes an optional `platform` choice (Twitch | YouTube) and
  fakes a `youtube.com/watch?v=…` stream for the second.

⚠️ **Limitation to state to the owner: this is presence-only.** It works when
the member's Discord shows "Streaming on YouTube" — their YouTube account
connected and activity display left on. A YouTube stream Discord does not
advertise is invisible to the bot. The Twitch-style polling fallback for
YouTube (the YouTube Data API over linked channels, plus a `/youtube link`
command) needs an API key nobody has provisioned and was **not** built.

## 2026-08-27 — the announcement became a card (owner ask)

*"can we make our go live message show the streamer name and the game they're
playing instead of their avatar"* (owner, ~10:50, with a streamcord screenshot).

The sentence was never the problem. Black Bloc posted text and only text, so
**Discord's link preview** chose the picture, and for a Twitch link that
preview leads with the streamer's avatar. The announcement is now
`content=<the same sentence> + embed=<a card>`:

| Part | What it holds |
|---|---|
| author line | `{display name} is now live on {platform}!` — **name only, no icon** |
| title / url | the stream title (or "Live now") linking to the stream |
| **Game** field | `info.game`, or the `GAME_FALLBACK` word; never blank |
| image | the game's Twitch box art, else the presence's own artwork, else nothing |
| colour | Twitch purple, YouTube red, unknown blurple |
| footer | `Black Bloc · via Twitch` or `· via Discord activity`, plus a timestamp |

- `golive_template` still owns the wording, because the sentence is unchanged
  and still goes out as the message content. The ping role still prefixes it,
  and `allowed_mentions` is unchanged — embeds do not ping at all.
- **Box art needs a second Helix call.** `/helix/streams` carries `game_id` and
  `game_name` but not the art; `TwitchClient.get_games` fetches it from
  `/helix/games` and caches it per game id forever, since a game's box art does
  not change. Twitch only, gated on the platform, the game id, the setting and
  Helix being configured — **YouTube never triggers a fetch of any kind**.
- A YouTube stream's picture comes from the presence itself
  (`discord.Streaming.assets`), worked out as a string with no request.
- `golive_embed` (bool, default true) turns the card off; off is byte-identical
  to the old behaviour.
- Shadow mode logs an `embed` summary (author / title / game / image) inside
  `golive.would_announce`, so "read the log" still answers what would have gone
  out.
- End of stream edits both halves in one `message.edit`: the sentence keeps its
  `— stream ended` suffix and the card's author line becomes "was live", footer
  gains `· stream ended`, art kept.

⚠️ **One collateral fix that had to land with it:** `golive_embed` is the 26th
value-typed setting and `/settings set-value` listed every one as an
`app_commands.choices` list. **Discord's ceiling is 25**, so the command would
have failed to register the moment the key existed. It now uses an autocomplete
on a plain string parameter. *(Removed: `/settings set-value` retired at **v84**,
2026-09-05 — `/settings` opens the paged panel, which walks the namespaces with 25-option
selects for the same reason. The registry is **202** keys today, not 26.)*

**NOT verified:** none of this has been seen in Discord. No card has ever been
rendered by the real client, the `/helix/games` response shape is from Twitch's
documentation rather than a measured call, and the `youtube:`/`twitch:` presence
asset prefixes are inferred — an address that turns out wrong renders as an
embed with no image, never as a broken announcement. The owner should run
`/golive test` (both platforms) in `#black_bloc-logs` and then go live
once with `golive_mode` on.
