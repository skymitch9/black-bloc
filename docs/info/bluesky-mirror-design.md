# Bluesky mirror — BaF's Bluesky posts land in #bsky-feed

> **Audience:** the build agent, then future sessions. **Status:** TRACKED. **Last verified: 2026-10-27 16:4x**
> (the owner's decisions, the live channel ids read through the operator token 16:2x, the feed shape read from
> the Fly machine 16:0x). ⚠️ NOT verified: nothing is built yet.

Owner, 2026-10-27 15:5x, verbatim: *"I want to pull post from the BaF bluesky account and have it post it a
discord channel. Is that doable"*. Decisions, one at a time: **(b) reposts too** (16:0x); **(a) #bsky-feed** (16:2x).

## The account and the channel (measured)

| Fact | Value |
|---|---|
| Handle | `blackinaflash.bsky.social` — *Black in a Flash!*, did `did:plc:4lijy65gdkw6gwwctvm6kxoc`, 1,060 followers, 940 posts, since 2025-06-04 |
| Channel | `#bsky-feed` `1564779885392699413`, category *Information* `1073710703518683136`, under #announcements |
| API | `https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=<handle>&limit=30` — no login, no key. `app.bsky.actor.getProfile?actor=<handle>` for the display name and avatar |
| Feed mix, last 8 items 16:0x | 3 own (one a bare reply *"seriously though"*), 5 reposts; embeds `images#view`, `video#view`, `record#view` |
| ⚠️ Gotcha | 15:5x–16:02 the API answered **403 *Request forbidden by administrative rules*** to this PC and bsky.app showed *Unable to connect*, while the Fly machine got 200; at 16:02 the PC got 200 again. A 403/5xx/timeout is a **retry with backoff**, never a post or a dropped cursor |

## What it does

One loop (`cogs/content/bluesky.py`, the `PbFeed` cog shape: `tasks.loop` every 60 s, `run_once`, `loop_health`,
restart on error). Each guild is read when `bluesky_interval_minutes` have passed since its last read. A read fetches
the author feed, walks it oldest-first, and for every item not in `bluesky_posts`:

- **kind**: `own` (no `reason`, no `reply`), `repost` (`reason.$type == app.bsky.feed.defs#reasonRepost`), `reply`
  (`record.reply` present). `repost` posts only while `bluesky_reposts`; `reply` only while `bluesky_replies`.
- **too old**: `indexedAt` (the repost's `reason.indexedAt` for a repost) older than `bluesky_max_age_hours` at first
  sight → row `skipped_old`, nothing posted. This is the backfill guard: the first read after the deploy records
  the account's recent history and posts none of it older than the window.
- otherwise → one Discord message, row `posted` with `message_id`; under shadow the copy goes to `shadow_channel_id`
  with the rehearsal line and the row says `would_post`.

Dedupe key is the post `uri` (`at://did/app.bsky.feed.post/rkey`); a repost's key is the ORIGINAL post's uri, so a
post BaF reposts twice, or reposts after posting, lands once. One conditional INSERT claims the row before the send
(checklist 12); the message id is written after.

**The message**: `bluesky_template` over the post's text with `{text}` `{url}` `{author}` `{handle}` (default
`{text}\n{url}`, cut to 2000), `url` = `https://bsky.app/profile/<author handle>/post/<rkey>`. One embed: author line
(display name · `@handle`, avatar), the text, the first image (`embed.images[0].fullsize`), a video's
`thumbnail`, a quoted post's text under its author (`embed.record`), an external link card's title + uri
(`embed.external`), timestamp = `indexedAt`. A repost carries `bluesky_repost_line` above (`🔁 {account} reposted`,
`{account}` = BaF's display name). `allowed_mentions`: the ping role only when `bluesky_ping_role_id` is set and the
post is real (never under shadow). Links in the text (`facets` of type `app.bsky.richtext.facet#link`) are expanded
to their `uri` so Discord shows the real link, not Bluesky's `…` shortening.

**Errors**: a non-200, a timeout or bad JSON → `bluesky.read_failed` once per streak (details `status`, `why`,
`failures`), backoff `min(interval × 2^failures, 60 min)` (the `pb_feed.backoff_minutes` idea), nothing posted,
the cursor untouched. The next good read clears it. A send that fails (`HTTPException`) → `bluesky.post_failed`,
the row goes back to unclaimed so the next read retries once more; after that `failed`.

## Settings (`bluesky` namespace; every one on the site, checklist 33)

| Key | Type | Default | Help |
|---|---|---|---|
| `bluesky_mode` | enum off/shadow/on | **shadow** | off reads nothing; test reads and sends each new post to the test channel with a line naming where it would have gone; on posts it in `bluesky_channel_id` |
| `bluesky_handle` | text | `blackinaflash.bsky.social` | the Bluesky account mirrored, without the @ |
| `bluesky_channel_id` | channel | null | where posts land while bluesky_mode is on; blank posts nothing and says so once in the log |
| `bluesky_ping_role_id` | role | null | a role mentioned above each post; blank pings nobody; a rehearsal copy never pings |
| `bluesky_interval_minutes` | int 1–60 | 5 | minutes between two reads of the account |
| `bluesky_reposts` | bool | **true** | whether the account's reposts are mirrored too |
| `bluesky_replies` | bool | false | whether the account's replies are mirrored too |
| `bluesky_max_age_hours` | int 1–168 | 24 | a post first seen older than this is recorded and not posted; it is what stops the history being posted after the deploy or a long outage |
| `bluesky_template` | text | `{text}\n{url}` | what the message says; {text} {url} {author} {handle} |
| `bluesky_repost_line` | text | `🔁 {account} reposted` | the line above a repost; {account} |
| `bluesky_rehearsal_line` | text | the posts pattern | the test-channel line naming where the copy would have gone; {channel} |

No `bluesky_shadow_channel_id`: the ONE test channel `shadow_channel_id` (v243). Defaults decided here live in
the registry, never in code paths (`settings_store.py`, its own block like the weekly questions one so parallel
branches merge textually). Mock: `site/mock/server.mjs` rows + `contract.json` + `labels.js`.

## Storage — schema 100 → 101

```
bluesky_posts (guild_id INTEGER, uri TEXT, cid TEXT, kind TEXT, author_handle TEXT, indexed_at TEXT,
               status TEXT, channel_id INTEGER, message_id INTEGER, seen_at TEXT, posted_at TEXT,
               PRIMARY KEY (guild_id, uri))
bluesky_reads (guild_id INTEGER PRIMARY KEY, last_read_at TEXT, last_ok_at TEXT, failures INTEGER, last_error TEXT)
```

Keep the last `bluesky_keep` = 500 rows per guild (a registry int, 100–5000; older `skipped_old`/`posted` rows are
pruned after each read). `storage/db.py` migration in the existing style; `black_bloc/bluesky_store.py` owns the SQL.

## Modules (tests mirror the package)

| File | Holds | Test |
|---|---|---|
| `black_bloc/bluesky.py` | pure rules: `kind_of`, `too_old`, `post_url`, `expanded_text` (facets), `embed_of`, `message_of`, `backoff_minutes`, `mode_of`, key constants | `tests/test_bluesky.py` |
| `black_bloc/bluesky_feed.py` | the httpx reader: `read_feed(handle, limit)` → `(status, items, why)`, `read_profile`; UA `BlackBloc/<version>` | `tests/test_bluesky_feed.py` (respx or a fake transport) |
| `black_bloc/bluesky_store.py` | the two tables | `tests/test_bluesky_store.py` |
| `black_bloc/bluesky_moves.py` | `tick(bot, guild, now)` under a per-guild lock (the `questions_moves` shape): due check, read, claim, send, log | `tests/test_bluesky_moves.py` with fakes like `tests/questions_fakes.py` |
| `black_bloc/cogs/content/bluesky.py` | the loop cog, registered in `bot.py:COGS` | `tests/cogs/content/test_bluesky.py` |
| `black_bloc/api/tools/bluesky.py` | `GET /api/bluesky` (status: mode, handle, channel, last read, last ok, failures, last error, next read; `recent`: last 30 rows) · `POST /api/bluesky/read` (Read now) · `POST /api/bluesky/rehearse` (the newest eligible post to the test channel, whatever the mode, like Post to test) — staff; refusals in words | `tests/api/tools/test_bluesky.py` + `contract.json` |
| `site/public/assets/bluesky-section.js` | a section on `posts.html` (`#sect-bluesky`, title **Bluesky**): a status strip (pill for the mode, *read 2 minutes ago*, the error if any), **Read now** · **Post to test**, the settings panel (`settingsNamespace('bluesky_')`, mode worded off/test/on like the rest), a table of the recent rows (when · kind · text cut to 80 · where · link); through the one search module | `site/check.mjs` steps + the mock |

Fixture: `tests/fixtures/bluesky/author_feed.json`, recorded from the live API (own post with images, a repost with
video, an own reply, a quote post, a post with a link facet). If the API answers 403 from the build machine, record
it through the Fly machine (`flyctl ssh console -a black-bloc -C "python3 -c …"`, stdlib urllib) — see
`docs/TODO.md` 2026-10-27.

Action kinds: `bluesky.posted`, `bluesky.would_post`, `bluesky.skipped_old`, `bluesky.skipped_kind`, `bluesky.read_failed`,
`bluesky.post_failed`, `bluesky.rehearsed`, `bluesky.read_now`, `bluesky.settings` — in `logkinds.py`, each with
`details` naming `uri`, `kind`, `channel`, `message_id` where it has them.

## Rules that apply (from CLAUDE.md and the checklist)

Near-zero comments, explanations in `code-notes.md` keyed `path:line`; no explaining blurbs on the section;
every word the bot posts is a key; shadow first (`bluesky_mode` default shadow); staff final say (`Post to test`,
`Read now`, and the mode are theirs); a person never sees a bare HTTP status; no Discord slash command — the
feature has no member interaction, the site is its door; `git add` by name, `pull --rebase --autostash`, never
`git stash`; only bot code committed; `docs/info/review-checklist.md` items 12 (claim before send), 33 (configurable
both ways), the shadow-first and the allowed-mentions items.

## Post the latest… (owner, 2026-10-27 16:3x)

Owner, verbatim: *"Can we pull the most recent 2 post from the account and post them, then @pawpette so she can see
it"*. A staff move on the section, **Post the latest…**: an ask for how many (1–10, default `bluesky_seed_count` = 2),
where (**the channel** or **the test channel**; the channel choice needs `bluesky_channel_id` set and is refused in
words otherwise — it does NOT need the mode on, it is an explicit staff press). Route `POST /api/bluesky/post-latest`
`{count, where: "channel"|"test"}`.
No note: the owner handles any mention by hand (2026-10-27 17:0x)
The newest `count` eligible items of the feed (kind rules apply, the age guard does NOT — this is the one path that
posts old items on purpose), oldest first so they read in order; items already `posted` are posted again only when
`where` is `test` (a rehearsal), otherwise skipped and the reply says how many were already up. Each real post is
claimed in `bluesky_posts` like a loop post, so the loop never repeats it. Action `bluesky.posted_latest` with
`count`, `where`, `posted`, `skipped`. The Post to test button is this move with count 1 /
where test — keep one implementation.

## What the owner does after the deploy

Set `bluesky_channel_id` to #bsky-feed on the Posts page (Claude cannot write settings — `access/site.md`), watch a
test copy or two in #post-test, then flip `bluesky_mode` to on.

## Deviations (build) — the agent appends here, numbered

1. **The keys file under `posts`, not a `bluesky` group.** `/settings`' group select is at Discord's cap of 25 and `bluesky_` would be the 26th (`tests/test_settings_store.py` pins 25), so `NAMESPACE_OVERRIDE` files all thirteen under `posts` — the sticky precedent, and the page they live on. CORE_KEYS is unchanged (354); KEY_TYPES 1254 → 1267. The section reads `settingsNamespace(all, 'posts')` filtered by the `bluesky_` prefix.
2. **aiohttp, not httpx.** httpx is a dev-only dependency here (`pyproject.toml`); discord.py already ships aiohttp. `bluesky_feed.read_feed` takes a `fetch` so tests (and the api tests' `WebBot`) answer from the recorded fixture. **No `read_profile`:** a repost item carries the account in `reason.by`, which is what `{account}` needs.
3. **`bluesky_posts` gains `text`** (the post's text, for the section's Recent table) and an index on `(guild_id, seen_at)` for the prune. Two statuses beyond the design's: `claimed` (taken, send in flight) and `retry` (one failed send, taken back by the next read).
4. **`skipped_old` / `skipped_kind` are one log row per read** carrying `count` and `uris`, not one row per post — the first read after the deploy would otherwise write ~30 rows.
5. **No `bluesky.settings` kind.** A setting change is already logged by the shared settings path (`settings.*`), checklist 34.
6. **On with no channel (or test with no test channel) reads nothing** and logs `bluesky.post_failed` once (the reason is stored in `bluesky_reads.last_error` and logged only when it changes). Nothing is recorded as unsent, so once the channel is set the next read posts what is still inside `bluesky_max_age_hours`.
7. **Two kinds off the one Post the latest… implementation:** to the test channel (and Post to test) logs `bluesky.rehearsed`; to the channel logs `bluesky.posted_latest`. Same details either way. A test-channel press claims no row.
8. **The test copy's home is `shadow.channel_id`** (the one test channel, else the guard's, else the log channel) — the home every Post to test uses — rather than `shadow_channel_id` alone.
9. **Read now is refused in words while `bluesky_mode` is off**, and a failed read answers 502 with Bluesky's reason in a sentence. `GET /api/bluesky` also carries `test_home` and `seed_count` so the page can draw Post to test and the ask's default.
10. **Post the latest… to the channel retakes any row not already `posted`/`claimed`** (a test copy, too old, not mirrored, failed) — an explicit staff press overrides the loop's decisions; already-up posts are skipped and counted in the reply.

