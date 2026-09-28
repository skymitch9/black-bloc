# Blocks convert — several blocks on one message, the block preview, the temp voice lobby block

> **Audience:** the conductor, reviewers, and the builds that add the next block kinds (`blocks-buttons`,
> `blocks-live`).
> **Status:** TRACKED · 🔨 **BUILT on branch `blocks-convert`** (off `main` `4a0e572d`, v183 live), NOT merged,
> NOT deployed, and the 78 → 79 migration has NOT run on the live database. Schema **78 → 79**, registry
> keys **645 → 651**, contract routes **271 → 272**, one new log kind (`post.redrawn`, routine).
> **Last verified: 2026-09-28** — against the branch's own code (`2b2e3e32`) by `pytest` (whole suite,
> `-n 16`: **9251 passed**, was 9209 at `4a0e572d`), `ruff check .` (clean), `node --input-type=module --check`
> on every touched page script, `node --test site/mock/*.test.mjs` (25 passed), the eight `site/mock/*.test.mjs`
> the deploy gate runs (all ok), and `node site/mock/check.mjs` against a mock started from the worktree on
> port 8841 (*22 pages, 272 routes, 26 core settings, all keys present*).
> ⚠️ **NOT checked:** nothing here met Discord (no boot, no token, no message sent or edited, no button
> pressed in a client), and **no page was rendered in a browser** — this build was not allowed to touch a
> browser, so the Blocks section's previews and the new editor have been seen by nobody. `TEST_MODE` and
> every mode key were left alone.

## The asks (owner, verbatim)

> *"Let's make all the blocks you suggested but not post them yet, only the front door should be posted in
> welcome test"* · *"We also need a way to preview what blocks look like, build [that] too"* · *"Will this
> take functionality away from temp voice in the chat? Also let's hold on role menu. It's still getting
> archived due to discord community"* — answered **no**: the temp voice block is additive only. The role
> menu block is ON HOLD and was not built.

## As built

### 1. Several blocks on one message

| Piece | What it does |
|---|---|
| `post_blocks.drawn_hash` (schema **79**) | Each block row carries the stamp of what the message in Discord shows for it. The 78 → 79 upgrade (`ADDED_COLUMNS` + `BACKFILLS`) copies `posts.door_hash` onto the front door's row, and the 77 → 78 backfill now carries it too, so the live welcome post is **not** re-edited on upgrade (tested on a schema-78 and a schema-77 file). |
| `posts.door_hash` | Kept, read-compatible: it is the front door's stamp mirrored by `post_blocks.set_drawn`, so every door path that reads it (`door_drawn`, status pills, `take_down_post`) is unchanged. |
| `posts.message_parts` | The send: the post's own message, then every attached block in `position` order, and each drawn block's stamp by kind. `message_payload` keeps its old `(payload, door_stamp)` shape on top of it. `publish_post` writes every stamp (`set_drawn`). |
| `posts.with_blocks` / `merged_view` | One block → its own view object, untouched (the welcome post goes out exactly as v180/v183 sent it — `test_the_welcome_post_carried_as_a_block_goes_out_exactly_as_v180_sent_it`, now also asserting the stamps and that a sweep does not edit it). Two or more → one view, each block's buttons starting on a row of their own. |
| `post_blocks.redraw_post` | The in-place edit of a carrier: if any attached block's stamp moved (or the door's `door_hash` says it is drawn but is no longer), the message is rebuilt — the post's own part **as it stands in Discord** (`kept_part`), then every block's parts fresh, views merged. The door cog's `redraw_carrier` is now a thin call to it (it still logs `frontdoor.redrawn_on_post`); any other carrier logs `post.redrawn`. |
| `post_blocks.keep_drawn` | The sweep's half for carriers the door does not ride: runs in the door cog's five-minute `_sweep`, under its `Reconciler` lock (checklist 37). |
| `FrontDoor.redraw_blocks_now` | *Save the words* on a non-door block redraws every carrier at once, under the same lock (`BlockKind.redraw = post_blocks.blocks_redraw`). |
| `BlockKind.footprint` + `too_big` | Discord's caps — **10 embeds, 5 action rows, 25 components** — checked when a block is added, against each kind's declared maximum (door `(1, 1, 3)`, temp voice `(1, 1, 5)`) plus the post's own card when it is an embed. Past a cap → 409 `block_too_big`, `BLOCK_TOO_BIG` in words, naming the cap and what it would need. |
| Reorder | Now edits a message already up at once (post-blocks Deviation 4 closed — it was one call): `ORDERED_NOW_SAID`, or the old *next time you press Update the post* if the edit could not be made. |
| Add / remove of a kind with no door-side machinery | `blocks_turned`: a message already up is redrawn whole at once (`DRAWN_NOW_SAID` / `DRAWN_OFF_SAID`, or `DRAWN_LATER_SAID`). The front door keeps its own `turned` (`turn_carrying`). |

### 2. The block preview — one component

| Where | What |
|---|---|
| `black_bloc/preview.py:BLOCK_DRAWS` | One draw per kind, each through its own feature's code: `door_block` (the existing `door_parts`), `voice_block` (the temp voice cog's `block_look`). The `post` renderer draws every block in the `blocks` sample through it, in order, one row of buttons per block. A new sample key `always` draws a block whose feature is off (the Blocks section shows what it WOULD look like). |
| `site/public/assets/blockpreview.js:blockPreview` | THE client component. The post drawer's preview, a version's preview, each Blocks card's **What it looks like in Discord** (lazy, from the saved keys, `always`) and both block editors draw through it. It wraps the existing `discordMock`, so the Discord look is the same one every page uses. |
| Editors | A draft needs overrides, and an override must be a text key claimed by exactly ONE renderer (`test_the_features_map_names_one_feature_per_key_and_no_key_twice`), so an editor draws with its kind's own renderer — `frontdoor` (existing) and the new `block_tempvoice` — still through `blockPreview({ feature, draft })`. |
| Mock | `PREVIEW_BLOCK_DRAWS` twins `BLOCK_DRAWS`; `block_tempvoice` joins `PREVIEW_FEATURES`. |

### 3. The temp voice lobby block (`tempvoice`)

- **Not exclusive** — any number of posts may carry it: its buttons are URL links and one guild-keyed button,
  nothing is stored per message, so two copies cannot disagree.
- **Draws** a card (heading + line explaining join-to-create) and one row: a **link button per written-down
  lobby** (`tempvoice_creator_ids`, the lobbies that still exist, at most **4**) to
  `https://discord.com/channels/<guild>/<lobby>`, then **My voice channel**, which opens the **same `/voice`
  panel** (ephemeral, every gate and refusal of `/voice`). Nothing is drawn while `tempvoice_mode` is `off`.
- **Only the temp voice feature draws it**: `cogs/community/tempvoice.py:block_parts` → `helpers.block_look`
  (pure, `black_bloc/tempvoice.py`) → `block_view`. The preview calls the same `block_look`.
- **Additive only.** The one edit to existing temp voice code: the body of `/voice` moved into
  `open_voice_panel(interaction)`, which `/voice` now calls — and so does the block's button. `cog_load` also
  registers the new `OpenVoiceButton` (`tvblock:open:<guild>`). Pinned FIRST, in their own commit
  (`7834684f`), and passing both before and after: join the lobby → room made, member moved, controls
  posted with the eleven `tempvoice:*` custom ids; `/voice` the only command; the eight existing keys and
  their types; the seven `/api/tempvoice/*` routes.
- **Words** — six new keys, each in the registry, the mock, `labels.js`, and editable on the site
  (Posts ▸ Blocks ▸ Temp voice lobby ▸ *Edit the Temp voice lobby block*, `blockwords.js:voiceLobbyWords`):
  `tempvoice_block_title`, `_text`, `_lobby_label` (`{lobby}` = the lobby's name, default `🔊 {lobby}`),
  `_controls_label`, `_show_controls` (bool, on) — filed under tempvoice by prefix — and
  `posts_block_tempvoice_name` (default *Temp voice lobby*, filed under posts beside the door's).
- **Attached to NO post.** The seed is unchanged (`test_the_shipped_seed_attaches_the_lobby_block_to_nothing`).

## Deviations

1. **The post's own part is kept as it stands in Discord, not re-rendered from the row.** The brief said to
   rebuild *"post's own part + every block's parts"*. Re-rendering the post's words from the row would
   publish an unsaved or pending edit without anyone pressing **Update the post**; so the edit leaves
   `content` alone and keeps the post's own card (`kept_part`), and every BLOCK is rebuilt fresh. The
   existing door tests already pinned *"the post's own words are left exactly as they were posted"*.
2. **A removed block has no stamp left** (its row is deleted), so removing a non-door kind forces the redraw
   at once. If that one edit fails, the card stays until **Update the post** — the sweep cannot see it. The
   front door is unaffected: `posts.door_hash` is its tombstone and the sweep still catches it.
3. **`cache_column` became optional** (`""` = none). The temp voice block has none; only the door keeps a
   derived column on `posts`.
4. **The caps are checked against a kind's declared maximum**, not what it draws today, so a door that is
   switched off still counts. They are checked only at *Add* (the only way a block gets on a post).
5. **The sweep for non-door carriers lives in the door cog** (`FrontDoor._sweep` → `keep_drawn`), because that
   cog owns the `Reconciler` every post redraw must share. Without the FrontDoor cog loaded, a temp voice
   words save answers *"picked up on the next sweep"* and no sweep runs — it cannot happen with `bot.py:COGS`
   as it is.
6. **New log kind `post.redrawn`** (routine) for a carrier the door does not ride; `KNOWN_DYNAMIC` gained the
   `post_blocks.py::done_kind` / `failed_kind` call sites (door carriers still write
   `frontdoor.redrawn_on_post` / `frontdoor.post_failed`).
7. **The Blocks card preview uses the `post` renderer with an empty body**, not a renderer of its own, so
   the card and the post drawer are literally the same server drawing and the same client component.
8. **"Sample data for live lists"**: a lobby list is configuration, not a live list — the preview draws the
   lobbies that are set up, and ONE sample lobby (named by `tempvoice_creator_name`) only when none is.
9. **The block's controls button is new persistent machinery** (`OpenVoiceButton`, `tvblock:open:<guild>`):
   temp voice had no persistent entry button, only `/voice`. It adds nothing but a second way to open the
   same panel. Its prefix is deliberately NOT `tempvoice:` so it can never collide with the in-room
   controls' persistent view.
10. **Default lobby label `🔊 {lobby}`**, not *Join {lobby}*: the shipped lobby is called *join to create a
    channel*, so *Join join to create a channel* read badly.
11. **Staff answers are module constants** (`BLOCK_TOO_BIG`, `DRAWN_*`, `ORDERED_NOW_SAID`), following the
    Posts convention (post-blocks Deviation 8). Every word POSTED to members is a key.

## What was NOT verified

- ⚠️ **Nothing met Discord.** Every send, edit, merged view, re-rowed button and the `OpenVoiceButton` press
  ran against fakes. The button was pressed by calling its callback — NOT through discord.py's
  dynamic-item regex dispatch on a real client.
- ⚠️ **No page was seen.** The Blocks cards' *What it looks like in Discord*, the new temp voice editor, the
  drawer preview after the switch to `blockPreview`: syntax-checked and contract-checked only. No CSS was
  added; the new pieces reuse `.preview`, `.field`, `.blockwords`.
- A Discord link button to a VOICE channel: whether a press opens the channel, or joins it, on desktop /
  mobile / web — not tried.
- ~~While `tempvoice_mode` is **shadow**, the block still draws its lobby links~~ — **settled 2026-09-28 02:2x**
  (owner, verbatim: *"Show nothing"*): the block draws nothing unless `tempvoice_mode` is `on`
  (`tempvoice.shows_block`); the preview and the mock follow the same rule.
- The live database has not run 78 → 79; the migration is tested on schema-78 and schema-77 files built in
  tests.

## Live check steps for the conductor (after merge + deploy)

1. Fly logs after boot (info level, if shown): `database: added post_blocks.drawn_hash`. No `frontdoor.redrawn_on_post` in the first
   sweep (the welcome post's stamp was carried over, so it is not re-edited).
2. #welcome-test: the welcome post is unchanged — rules, the door card, three buttons, ONE message.
3. Posts ▸ **Blocks**: two cards — *Front door (on Welcome and rules)* and *Temp voice lobby (on no post
   yet)*; each shows **What it looks like in Discord**. The temp voice one shows the real lobby as a link
   button and **My voice channel**.
4. Posts ▸ Blocks ▸ Temp voice lobby ▸ **Edit the Temp voice lobby block**: type in the heading — the preview
   changes; untick *Carry the voice controls button* — the button leaves the preview. Do NOT save unless you
   mean it (it is attached to nothing, so a save changes no message).
5. Posts ▸ Welcome and rules ▸ **Add a block…** now lists *Temp voice lobby* — ⚠️ do not add it; the owner
   said only the front door is posted.
6. Temp voice as today: join the lobby → a room, you are moved, the controls are posted in its chat; `/voice`
   opens the same panel as before.

## For the conductor to decide

- ~~**Shadow mode and the temp voice block**~~ — settled 2026-09-28: draw nothing until temp voice is `on`.
- **Where the non-door sweep lives** (Deviation 5): fine in the door cog, or move the `Reconciler` to a small
  posts-level owner when `blocks-live` adds the auto-updating kinds (which will want their own cadence).
