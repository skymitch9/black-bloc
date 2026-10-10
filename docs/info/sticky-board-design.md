# The sticky leaderboard — the board as a post, kept at the bottom of #speed-and-pbs

> **Audience:** the conductor, reviewers, and the next build that touches stickies, post blocks or the point
> system. **Status:** TRACKED · 🔨 **BUILT on branch `sticky-board`** (off `main` `b87ed763`, v219 live), **NOT
> merged, NOT deployed.** Schema **92 → 93**; registry keys **1178 → 1183** (`CORE_KEYS` 346 → 347); contract routes
> **360 → 362**; log kinds **+1** (`sticky.pin_failed`). **Last verified: 2026-10-09** against the branch by the
> hermetic suite, `ruff`, the 15 `site/mock/*.test.mjs`, `scripts/site-gate.ps1` (`check.mjs`) and a headless Chrome
> `--dump-dom` of the branch's mock (Leaderboard and Posts pages). ⚠️ **NOT checked:** nothing here met Discord — see
> *§NOT verified*. Secret NAMES only (none here).

## The ask (owner, Fri 2026-10-09 ~8:3x PM, verbatim)

> *"i want this leaderboard to be a sticky post, can we 1 make it a post, 2 make it sticky, 3 have it be editted by
> the leaderboard function but still appear in the post menu on the website updated as the leaderboard updates? use
> as much reusable code as possible"*

The three decisions, verbatim:

- **Q1 — the channel:** *"speed and pbs as soon as we turn shadow mode off"* → `points_channel_id` (default
  #speed-and-pbs `1076003845232148580`); while `points_mode` is shadow the copy goes to the points rehearsal home like
  every other points post.
- **Q2 — the size and the look:** *"i think top 10 but let it be changeable with /pb settings and on the website. also
  use the same kind of text mark up styling we use for other post such as welcome post so its in that discord box"* →
  `points_top_n` (10; 5/10/15/20/25 on `/pb`, 1–25 on the site), the post's style `embed`.
- **Q3 — the cadence:** *"i want it to be a little less annoying, have it post after 5 messages but if there is an
  ongoing conversation wait until there has been silence for 5 minutes"*, and on the conductor's ceiling: *"lets do an
  hour, and also make sure we pin the message each time and delete the message about something being pinned like we
  do in go live when something is spotlighted. that way it cant be lost"*. Between re-posts the copy is EDITED in
  place whenever the board changes.

## What was reused and what was added

| Need | Reused | Added |
|---|---|---|
| The board drawn in a post | `post_blocks.BlockKind` / `KINDS` / `load_kinds` / `parts_of`, `block_look.Look` + `parts_of` (the embed box), `points_panel` board lines (`lines_of`, `heading_of` — split out of `board_lines` / `title_of`), `points_view.order_of` / `place_row`, `points_moves.board` / `top_of` / `said` / `name_of` | `post_blocks.LEADERBOARD` (a LIVE kind, footprint (1, 0, 0)); `black_bloc/points_post.py` `board_look` / `block_rows` / `block_parts` |
| Redrawn when the board moves | the door cog's `Reconciler` via `FrontDoor.keep_live_now` (`LIVE_KINDS` now includes `leaderboard`, so the `LiveBlocks` minute loop is the safety net), `redraw_post` (edits only when the stamp moved) | `points_post.redraw` (`live_blocks.keeper_of`), called by `points_tickets.settle` — the one follow-through of approve / reject / remove / edit / recompute from both doors — and by store hooks in the `Points` cog for `points_top_n`, `points_board_order`, the four board words and `points_mode` |
| The post itself, on the Posts page | `posts.make_post`, `posts.set_posted` / `set_shadow_posted` / `clear_posted`, `post_blocks.attach` / `set_drawn`, the Blocks section card + preview | `points_post.ensure_post` (slug `leaderboard`, title `points_board_post_title`, style embed, `pin` 0, the block) |
| The post kept at the bottom | `sticky_posts.Desk` whole: locks, counts, one timer per channel, `_target` / `_take_down` / `_failed` / `_unsend` / settle / outage handling, the `/sticky` panel, the Posts page's Sticky section, `/api/sticky` | `sticky_messages.post_id` (schema 93); `sticky_posts.post_message` (the post + its blocks, fresh) and `owner_rule`; `Desk.save_post`, `repost`, `_post_copy`, `_pin`, `_let_go` |
| Pinned, notice removed | `quiet_pins` (the `QuietPins` listener deletes the bot's own *pinned a message* notice while `quiet_bot_pins` is on — the same path go-live's spotlight pins use) | `Desk._pin` after every send (`sticky_pin_copies`) |
| The doors | `cogs.core.set_key` (one `settings.set` row), `points_panel.BoardPanel` / `Move`, `sticky.row_line`, `sticky-section.js` | `black_bloc/points_board_panel.py` (`/pb` ▸ **Settings…**), `points_post.pin_board` / `board_state`, `GET` / `POST /api/points/board-post`, `sticky-section.js` exports `stateLine` / `stickyMoves`, the Leaderboard page's pin row |

## How it works

1. **The block.** `leaderboard` draws ONE card: `points_board_title` (or `points_board_xp_title` by
   `points_board_order`) over one `points_board_line` per place, top `points_top_n` (at most 25 — 25 lines of the
   longest names fit one 4000-character card, `test_a_board_of_twenty_five_fits_one_card`), or `points_board_empty`.
   Nothing is drawn while `points_mode` is off. Any post may carry it; it is not exclusive.
2. **A post as the sticky.** A `sticky_messages` row with `post_id` set posts THE POST instead of `text`: its own
   card when the body has words (a blank body draws no card of its own, so the leaderboard post is just the board's
   box), then every block's card and buttons, drawn fresh at each move (`post_message`). After the send the copy is
   pinned, its id is written on the sticky row AND on the post (`message_id`, or `shadow_message_id` when it rehearses)
   with the blocks' stamps, so `redraw_post` finds and edits the current copy. `posts.posted_message` reads the
   sticky's copy for a sticky's post; `posts.reconcile_posts` leaves those posts to the sticky.
3. **The one mode rule (no double shadowing).** `sticky_mode = off` stops every sticky (staff final say). Otherwise a
   post whose blocks name an OWNER (`BlockKind.owner`; the leaderboard's is `points_mode` / `points`) follows that
   feature's mode and rehearsal home (`points_shadow_channel_id`, else `shadow_channel_id` …); every other sticky —
   text or post — follows `sticky_mode` and the sticky home. So the leaderboard rehearses exactly where points
   rehearse, and goes to #speed-and-pbs the moment `points_mode` is on, whatever `sticky_mode` says above off.
   `posts_mode` is not consulted for a sticky's post. A change of `points_mode` or `points_shadow_channel_id` settles
   every sticky at once (`MOVES_THE_COPIES`).
4. **The quieter move (every sticky).** After `sticky_after_messages` (5) counted messages the move waits until the
   channel has been quiet for `sticky_quiet_seconds` (300) since the last counted message, but never longer than
   `sticky_max_buried_minutes` (60) after the count was reached; `sticky_min_seconds` (30) since the last copy stays
   the floor under both (`sticky.quiet_left`, `sticky.due_in`, pure). One timer per channel: it sleeps again while
   people are still talking (`Desk._later`). **The defaults ARE the new behaviour for every sticky staff already
   have** — the owner's rule; `sticky_quiet_seconds = 0` is the old rule (move as soon as the count and the gap
   allow). An outage retry owes no quiet.
5. **Between moves the copy is edited in place**: every run move (`settle`), every board setting, and the
   `LiveBlocks` minute loop call the door cog's live redraw; the message is edited only when the drawn board changed.
6. **Pin the leaderboard here** (`points_post.pin_board`, both doors): makes the post once (slug `leaderboard`,
   title `points_board_post_title`, style embed, the block), keeps it as the sticky in `points_channel_id`. Pressing
   it again answers *already*; if the channel changed, the old sticky is removed and a new one made there; if that
   channel already keeps ANOTHER sticky, it refuses in words naming it, and **Replace it** (`replace: true`) is staff's
   final say.

## The doors

| Where | What |
|---|---|
| `/pb` ▸ **Settings…** (staff) | `Leaderboard settings`: Top N (select 5/10/15/20/25), the order (the two board headings), the channel (`ChannelSelect`, shown as `#name · Category`), **Pinned** (the sticky's own state line: live / rehearsing / paused / stopped, when, moved N×), and **Already there** when another sticky holds the channel. Buttons that render only when they work: **Pin the leaderboard here** or **Replace it**, **Pause** / **Resume** / **Try again**, **Back**. Every write is one `settings.set` row (`cogs.core.set_key`). |
| Leaderboard page ▸ Settings (staff) | Under the mode switch: *Pinned in #speed-and-pbs* + the Sticky section's state line, **Pin the leaderboard in #channel** / **Replace the sticky message in #channel**, and the Sticky section's own Pause / Resume / Try again (`stickyMoves`). The keys stay in the folded settings below. |
| Posts page ▸ Sticky messages | **New sticky message** asks *Words* or *A post*; a post row shows the post's title (a link to it) and **Change the post** instead of **Edit**. |
| Posts page ▸ the post | The `leaderboard` post is listed like any post; **Update the post** moves a fresh copy to the bottom (`Desk.repost`), **Take it down** pauses the sticky. |
| Posts page ▸ Blocks | A **Leaderboard** card with its preview (a three-member sample board). Its words are edited on the Leaderboard page (the `points_*` keys), so it has no editor of its own. |
| `/sticky` | A **Keep a post at the bottom of a channel…** select (then a channel); a post's card has **Keep a different post here…** and no **Edit…**. |

## Keys (5 new; 1178 → 1183)

| Key | Type | Default | Filed |
|---|---|---|---|
| `sticky_quiet_seconds` | int 0–3600 | 300 | posts |
| `sticky_max_buried_minutes` | int 0–1440 (0 = no ceiling) | 60 | posts |
| `sticky_pin_copies` | bool | on | posts |
| `posts_block_leaderboard_name` | text | *Leaderboard* | posts |
| `points_board_post_title` | text (`POINTS_WORDS`) | *Leaderboard* | core |

Reused: `points_channel_id`, `points_shadow_channel_id`, `points_mode`, `points_top_n`, `points_board_order`,
`points_board_title`, `points_board_xp_title`, `points_board_line`, `points_board_empty`, `sticky_mode`,
`sticky_after_messages`, `sticky_min_seconds`, `sticky_silent`, `quiet_bot_pins`, `rehearsal_note`.

## Log kinds

Reused: `sticky.set` / `sticky.edited` (a post save carries `post` and `post_id`), `sticky.posted` /
`sticky.would_post`, `sticky.paused` / `resumed` / `removed`, `sticky.post_failed`, `post.created`,
`post.redrawn`, `settings.set`, `quiet_pins.deleted`. **New:** `sticky.pin_failed` (important by its suffix) — once per
channel per boot when a copy could not be pinned; the copy stays up and stored. No `points.board_redrawn`: `post.redrawn`
already records every edit.

## Routes (2 new; contract 360 → 362)

`GET /api/points/board-post` (staff) and `POST /api/points/board-post` (`{"replace": true}` optional; staff writer):
`{channel_id, channel, post, sticky, other, message}`. `PUT /api/sticky/{channel}` also takes `{"post": "<slug>"}`;
every sticky row carries `post` and `words`.

## Decisions the build made beyond the brief

1. **`sticky_quiet_seconds` allows 0** (the brief said 10–3600): 0 is the old rule, so staff can turn the quiet wait
   off both ways (checklist 33); the existing sticky tests pin the old mechanics at 0, new tests pin the quiet rule.
2. **The old copy is deleted BEFORE the new one is sent**, as the sticky always has (never two copies); deleting it
   removes its pin, so there is no separate unpin call.
3. **The notice is removed by `QuietPins`**, not a second implementation: it already deletes every *pinned a message*
   notice the bot causes while `quiet_bot_pins` is on. With `quiet_bot_pins` off the notices stay.
4. **Rehearsal copies are pinned too** — `sticky_pin_copies` is one rule for every sticky, and a rehearsal should
   rehearse the pin.
5. **No new block words**: the board reuses the four `points_board_*` words, so one edit changes `/pb`, the site and
   the post together. No *updated …* footer: a timestamp would be an explaining line, and the card only changes when
   the board does.
6. **A blank-bodied post draws no card of its own** in a sticky, so the leaderboard post is one box (the board), not a
   title box over a board box.
7. **A post may be a sticky only if** it does not carry the front door (that keeps its own place), is not already a
   sticky elsewhere, is not posted already (take it down first), and has words or a block — each refused in words.
8. **The Posts page's Update / Take it down on a sticky's post** go through the desk (a fresh copy at the bottom /
   pause), never `publish_post`'s edit-in-place, so the sticky stays the one owner of its copy.
9. **A sticky's post is redrawn whole** (content, cards, buttons) rather than keeping the posted part: the sticky
   reposts it fresh at every move anyway, and the rehearsal note rides as content.
10. **`/pb` ▸ Settings… is gated on staff** (as the Leaderboard page is), not on the `/settings` panel's core-key admin
    gate (`settings_core_keys_admin_only`), although the `points_*` keys are core keys. ⚠️ Reviewer: say if the core
    gate should apply here too.
11. **Bounty changes do not redraw**: they do not move the board until **Recompute** (points L1 decision 11), which
    does.
12. **The `/pb` Settings and `/sticky` post-pick labels are constants** (staff chrome, the `/honeypot` and points L2
    precedent); everything the bot POSTS is a key.
13. **A rehearsal home for the leaderboard is the points one**, but a stopped row's sentence still names
    `sticky_shadow_channel_id` (`TROUBLE_NO_HOME` / `TROUBLE_HOME_GONE` kept verbatim because `settle` revives rows by
    matching that wording).

## Not built

- A per-sticky cadence (the quiet / ceiling / pin keys are server-wide, as `sticky_after_messages` is).
- Pinning while the sticky is paused, or a pin of a post that is not a sticky (posts keep their own `pin`).
- A guard against a redraw racing a move: a redraw that edits the copy the sticky deleted a moment earlier gets a
  404, logs one `post.post_failed`, and the next tick edits the new copy.
- A board in a thread or forum post (stickies are text and announcement channels only).

## NOT verified

- **Nothing met Discord.** No copy was posted, pinned, unpinned by deletion or edited; no *pinned a message* notice
  was deleted (QuietPins was not exercised with a real notice); the silent flag, the `ChannelSelect` with a
  `discord.Object` default, the `/pb` Settings door and the `/sticky` post pick were exercised through fakes only.
- **The quiet timer** was tested with a fake clock and fake sleeps, never in real time.
- **Schema 93** ran on test databases only (a fresh file and a 92 file), not the live database.
- **The pages** were seen only as a headless Chrome `--dump-dom` of the branch's mock: the Leaderboard page rendered
  *Pinned in #speed-and-pbs · rehearsing · Pause*, the Posts page rendered the post sticky with **Change the post**
  and the Leaderboard block card; no console error was logged. NOT clicked: Pin / Replace, Pause / Resume, the
  Words / A post switch in **New sticky message**, **Change the post**. Phone width and other themes not looked at.
- Rate limits for a delete + send + pin every few minutes in a busy channel — reasoned, not measured.
