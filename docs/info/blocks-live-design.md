# Blocks live — who's live now, upcoming events, link buttons

> **Audience:** the conductor, reviewers, and the next build that adds a block kind or touches the
> post sweep.
> **Status:** TRACKED · 🔨 **BUILT on branch `blocks-live`** (off `main` `d418ca13`), NOT merged, NOT
> deployed. **No schema change** (still **79**). Registry keys **651 → 669** (measured:
> `len(settings_store.KEY_TYPES)`), contract routes **272 → 275** (the three redraw entries; no new
> Python route — `/api/post-blocks/{kind}/redraw` already took any kind), one new cog
> (`cogs/community/live_blocks.py`, one new loop), no new log kind.
> **Last verified: 2026-09-28** — against the branch's own code (`f4c4e83c` + this docs commit) by
> `pytest` (whole suite, `-n 16`: **9323 passed**, was 9251 at `d418ca13`), `ruff check .` (*All
> checks passed*), `node --input-type=module --check` on every `site/public/assets/*.js`, the eight
> `site/mock/*.test.mjs` the deploy gate runs (all exit 0), and `node site/mock/check.mjs` against a mock
> started from the worktree on port 8861 (*22 pages, 275 routes, 26 core settings, all keys present*).
> ⚠️ **NOT checked:** nothing here met Discord (no boot, no token, no message sent or edited), and **no
> page was rendered in a browser** — this build was not allowed to touch one, so the three editors and
> the three Blocks cards have been seen by nobody. `TEST_MODE` and every mode key were left alone.

## The asks (owner, verbatim — `TODO.md` ▸ 🧱 Nine more block kinds)

> *"Let's make all the blocks you suggested but not post them yet, only the front door should be posted
> in welcome test"* — group (C) `blocks-live`: **who's live now** (auto-updating), **upcoming events**
> (auto-updating), **link buttons** (staff-set label + URL rows).

All three are attached to **NO post**. The seed is unchanged
(`tests/test_post_blocks.py::test_the_shipped_seed_attaches_none_of_the_live_blocks`).

## As built

### The three kinds (`black_bloc/post_blocks.py:KINDS`, appended after `tempvoice`)

| Kind | Draws | From | Footprint (embeds, rows, components) |
|---|---|---|---|
| `livenow` | a card: heading, one line per stream (`**{name}** — {title}`, the title linked to the stream and cut to `golive_block_title_chars`), at most `golive_block_max` (10); the empty line while nobody is live | the **go-live** sessions (`golive_sessions`, open, `mode = 'on'`) and the **spotlight** sessions (`spotlight_sessions`, open, `mode = 'on'`, not a replay per `golive_replay.is_replay`) — read through each feature's own `open_sessions`; one line per stream URL | (1, 0, 0) |
| `upcoming` | a card: heading, one line per event (`**{title}** — {when} ({relative})`, `{when}` = `<t:…:F>`, `{relative}` = `<t:…:R>`, the title linked to its Discord scheduled event when it has one), at most `events_block_max` (5); the empty line | the events feature's own `events_by_status(db, guild, (APPROVED,))`, kept when `starts_at` is still ahead, soonest first (`events.upcoming_of`) | (1, 0, 0) |
| `links` | a card (heading + line, `posts_block_links_card` on) and one **link button** per row, five to a Discord row | one JSON settings key, `posts_block_links_rows` | (1, 2, 10) |

- **Not exclusive** — any number of posts may carry any of them; nothing is stored per message.
- **Drawn only by the feature's code**: `golive.live_block_look` (pure) ← `cogs/content/golive.py:block_streams` /
  `block_parts`; `events.upcoming_block_look` / `upcoming_of` (pure) ← `cogs/community/events.py:block_events` /
  `block_parts`; `link_buttons.links_look` / `links_parts`. The preview calls the same pure functions.
- **Nothing drawn while the feature is off**: `livenow` while BOTH `golive_mode` and `spotlight_mode` are
  `off`; `upcoming` while `events_mode` is `off`; `links` while there is neither a card nor a button. In
  `shadow`, `livenow` still lists only `mode = 'on'` sessions (a shadow session was never announced, so
  it is not published by the block either) and `upcoming` lists nothing (the empty line).
- **Member words are drawn plain** (`block_look.plain`): markdown escaped, `[` `]` escaped (no link
  injection from a stream or event title), mentions broken. A member not in the cache is drawn as
  `<@id>` (an embed never pings). Every edit of a carrier still passes `AllowedMentions.none()`.

### A block whose list is read from the database — `BlockKind.load`

`parts` is synchronous (the door, temp voice and every caller of `message_parts` rely on that). The two
live kinds need an async read, so `BlockKind` gained an optional `load(bot, guild)`; `post_blocks.load_kinds`
runs it for every attached kind that has one and keeps the result in `post_blocks.LOADED[(kind, guild)]`,
which the kind's `parts` reads. `load_kinds` is awaited right before `parts_of` in the only two paths
that send a message: `redraw_post` and `posts.publish_post`. The door and temp voice have no `load`, so
those paths are unchanged for them.

### A block may draw no card

`links` with the card switched off draws buttons only. `posts.with_blocks` now skips a `None` embed
(one generator condition); every existing kind always draws an embed, so their messages are byte-for-byte
the same (the welcome-post test is untouched and green).

### Auto-updating — where the sweep lives, and the cadence

**Decision: the sweep and its lock STAY in the door cog; a new small cog owns only the CADENCE.**

- The ONE `Reconciler` stays `FrontDoor._reconciles`. Moving it to a posts-level owner would have meant
  the door's `_sweep`, `redraw_now`, `redraw_blocks_now` and `on_post_published` taking someone else's
  lock — a change to the door, which this build was told to leave byte-for-byte alone. Nothing in the
  door's own paths changed.
- `FrontDoor.keep_live_now(guild)` (new, additive) runs under that same lock (`stamp=False`, so it never
  closes the boot window): if the door's carrier carries a live kind, the door's own sweep half
  (`keep_the_ride`) runs for it; then `keep_drawn(bot, guild, LIVE_KINDS)` — the existing non-door sweep,
  restricted to posts carrying `livenow` or `upcoming`.
- `cogs/community/live_blocks.py:LiveBlocks` (new, appended to `bot.py:COGS`) ticks every **1 minute**
  and, per guild whose `posts_block_live_minutes` (default **1**, 1–60) is up, calls
  `FrontDoor.keep_live_now`. Without the door cog it does nothing (there is no lock to share). It has
  `loop_health`, an `@loop.error` that records and restarts, `wait_ready`, and skips an unavailable guild
  (checklist 25, 28, 32, 37).
- The door's own five-minute sweep still covers every carrier too (unchanged).
- **Rate limits:** `redraw_post` edits only when a block's stamp moved. The stamp is a hash of the drawn
  heading, text and buttons, so it moves only when the rendered list changes — a stream starting or
  ending, a title change, an event added, approved, moved or starting (it then drops off). `<t:…:R>` is
  rendered by the client, so time passing never re-edits the message. Tested:
  `test_the_live_block_is_edited_only_when_who_is_live_changes`.
- **No event-driven hook was added.** Go-live and spotlight start and end sessions at five different
  sites (`start_session` ×2, `end_session` ×5 across two cogs), so there is no single clean hook; a
  one-minute look that edits nothing unless the list moved is the smaller change and keeps go-live
  untouched.

### Link buttons — one JSON key, checked on write

`posts_block_links_rows` is a **text** key holding a JSON list (`[{"label": …, "url": …}]`), validated by
`settings_store.checked_links` on every write path (Settings page, `/settings` panel's key card, the
editor): at most **10** rows (two Discord rows of five — 10 of the message's 25 components), exactly the
keys `label` and `url`, a label of 1–80 characters, a url of at most 512 characters that starts
`https://` and names a host, no spaces. A bad row is **refused in words naming the row number**; nothing
is stripped. Blank = no buttons (`TEXT_MAY_BE_BLANK`). A stored value that stops checking draws no
buttons and logs a warning (`link_buttons.rows_of`).

### Keys — 18 new (651 → 669), every posted word one of them

| Key | Type | Default | Filed under |
|---|---|---|---|
| `golive_block_title` / `_line` / `_untitled` / `_empty` | text | *Live now* / `**{name}** — {title}` / *watch the stream* / *Nobody is live right now. This card updates itself when someone is.* | posts (override) |
| `golive_block_max` / `_title_chars` | int | 10 (1–25) / 60 (10–200) | posts (override) |
| `events_block_title` / `_line` / `_empty` | text | *Coming up* / `**{title}** — {when} ({relative})` / *Nothing is on the calendar yet. This card updates itself.* | events |
| `events_block_max` | int | 5 (1–20) | events |
| `posts_block_links_rows` | text (JSON) | blank | posts |
| `posts_block_links_title` / `_text` | text | *Links* / *Handy places, one press away.* | posts |
| `posts_block_links_card` | bool | on | posts |
| `posts_block_live_minutes` | int | 1 (1–60) | posts |
| `posts_block_livenow_name` / `_upcoming_name` / `_links_name` | text | *Who's live now* / *Upcoming events* / *Link buttons* | posts |

The line templates accept only their own placeholders (`checked_fields`); headings and empty lines
accept none (`checked_plain`). Mirrored in `site/mock/server.mjs` (rows + `NAMESPACE_OVERRIDE` twin) and
`site/public/assets/labels.js`; the contract's `settings.min` / `max` regenerated.

### The site

| Where | What |
|---|---|
| Posts ▸ **Blocks** | Three more cards (*Who's live now*, *Upcoming events*, *Link buttons*, each *on no post yet*), each with **What it looks like in Discord** (sample streams / sample events / the staff's links, or two sample links while none is set). |
| `blockwords.js:liveListWords` → `liveNowWords`, `upcomingWords` | Heading, line, empty line and the numbers; a tick draws the preview **empty**; a blank field is cleared back to its shipped words (`DELETE /api/settings/{key}`); **Save the words** writes each changed key, then `POST /api/post-blocks/<kind>/redraw`. |
| `blockwords.js:linkButtonsWords` | Rows of label + address with ↑ / ↓ / **Remove** and **Add a link** (hidden at ten, with a line saying why), the card tick, heading and line; live preview of the draft; the rows are saved as ONE `PUT /api/settings/posts_block_links_rows`, so a bad row is refused with its number and nothing is saved. |
| `/settings` (Discord) | Every one of the 18 keys has its key card (configurable both ways, checklist 33). |

### Preview

`preview.BLOCK_DRAWS` gains `livenow`, `upcoming`, `links`; renderers `block_livenow`, `block_upcoming`,
`block_links` (posts.html) claim only their text keys. Sample lists: two streams (`live: none` draws the
empty line), two events two and five days out at 20:00 UTC (`events: none`), and for links the stored
rows (the Blocks card substitutes two sample links while none is stored; the editor draws exactly the
draft). The mock twins all of it (`PREVIEW_DRAW.block_*`, `PREVIEW_BLOCK_DRAWS`, `checkedLinks`).

## Deviations

1. **The who's-live words are filed under `posts`, not `golive`** (a `NAMESPACE_OVERRIDE`). Filed by prefix
   they land on the Go-live page, whose drawer placement is pinned at 83 keys by
   `site/mock/golive-join.test.mjs` / `test_the_golive_page_still_draws_eighty_three_keys`; they are block
   words edited in Posts ▸ Blocks. The upcoming words stay under `events` by prefix.
2. **"Reuse its existing upcoming query"** — there was none. The events feature's existing
   `events_by_status(…, (APPROVED,))` is the query; the "still ahead, soonest first, capped" step is a new
   pure `events.upcoming_of`, not a second store.
3. **Who counts as live** — the brief said "as the Go-live feature already knows them"; both go-live
   (members) and spotlight (featured channels) keep open sessions, so both are listed, one line per stream
   URL (a spotlight channel that is also a member going live is listed once). Only sessions whose `mode`
   is `on` (announced) and, for spotlight, not a replay.
4. **Cadence is 1 minute by default, not the 5-minute door sweep**, from a new cog (see above). No
   event-driven hook. The door's 5-minute sweep still runs over all carriers.
5. **A shadow-mode feature**: `livenow` lists no shadow session; `upcoming` lists nothing while events are
   in shadow (draws the empty line), nothing at all while `off`. Decided here for safety — a public card
   must not publish what the feature itself is only rehearsing.
6. **`BlockKind.load` + `post_blocks.LOADED`** — a module-level snapshot per (kind, guild), written just
   before each draw. It is the smallest way to keep `parts` synchronous; it is not a cache anything reads
   later.
7. **`posts.with_blocks` skips a `None` embed** — one condition in shared code, needed for links with the
   card off. No existing kind returns `None` for its embed.
8. **Blank editor field = restore the shipped words** (the editor calls `clearSetting`), because the text
   keys refuse a blank value. The temp voice editor does not do this; not changed.
9. **Staff answers are the existing post-blocks constants** (`REDRAWN_SAID` etc.); the refusal sentences
   of `checked_links` are module constants (Posts convention, post-blocks Deviation 8). Every word POSTED
   to members is a key.
10. **A stream title is cut to `golive_block_title_chars` and the card keeps whole lines up to 4000
    characters** — a list longer than one card silently drops its last lines (with the defaults, 10
    lines × ~200 characters, it never does).

## What was NOT verified

- ⚠️ **Nothing met Discord.** Every send, edit, link button and `<t:…>` timestamp ran against fakes. How
  Discord renders `[title](url)` inside bold, and a `<@id>` of a member it has not cached, in an embed —
  not seen.
- ⚠️ **No page was seen.** The three Blocks cards, the three editors (the link rows' layout at 390 px in
  particular — they reuse `.formrow`, no CSS added) — syntax- and contract-checked only.
- The `LiveBlocks` loop running on a real client (it was exercised by calling `sweep` and `_live_error`).
- `FrontDoor.keep_live_now` against a real door carrier that carries a live block — tested with the
  carrier and `keep_the_ride` faked.
- Spotlight sessions whose `url` is null fall back to `https://www.twitch.tv/<login>` — a YouTube-only
  spotlight with no session url would link to a Twitch page that may not exist. Not a live case measured.

## Live check steps for the conductor (after merge + deploy)

1. Fly logs after boot: `loaded cog black_bloc.cogs.community.live_blocks`. Status page ▸ loops: a
   `LiveBlocks · _live_loop` row with a recent last-ok. #welcome-test's welcome post is unchanged and
   NOT edited (no `frontdoor.redrawn_on_post` / `post.redrawn` row appears from the new loop).
2. Posts ▸ **Blocks**: five cards — Front door, Temp voice lobby, **Who's live now**, **Upcoming events**,
   **Link buttons** — the new three *on no post yet*, each with **What it looks like in Discord**.
3. Posts ▸ Blocks ▸ Who's live now ▸ **Edit…**: change the line to `{name} · {title}` — the preview
   changes; tick *Show it as it looks when the list is empty* — the empty line shows. Leave without saving.
4. Posts ▸ Blocks ▸ Link buttons ▸ **Edit…**: **Add a link**, type `Site` / `http://example.org`, press
   **Save the words** — refused in words (*Link button 1's address must start with `https://`…*), nothing
   saved. Fix it to `https://…` only if you mean to keep it (it is attached to nothing, so a save changes no
   message).
5. ⚠️ Do NOT add any of the three to a post unless the owner says so. When he does: add *Who's live now* to
   a test post in #welcome-test, press **Post it**, go live (or wait for a spotlight) — the card lists the
   stream within about a minute, and edits once more when it ends.

## For the conductor to decide

- **The default cadence (1 minute)** — fine, or match the door's 5? One key, `posts_block_live_minutes`.
- **Shadow behaviour** (Deviation 5) — keep, or list shadow sessions/events while rehearsing?
- **The who's-live words under `posts`** (Deviation 1) — or move them onto the Go-live page (re-pin the
  83-key fixture and give them a drawer).
