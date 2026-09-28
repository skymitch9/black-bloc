# Post blocks — a post attaches blocks; the front door is the first kind

> **Audience:** the conductor, reviewers, and the next build that adds a block kind or touches Posts or
> the front door.
> **Status:** TRACKED · 🔨 **BUILT on branch `post-blocks`** (off `main` `d90c9e8c`, v182 live), NOT merged,
> NOT deployed, and the 77 → 78 migration has NOT run on the live database. Schema **77 → 78**, registry
> keys **641 → 645**, contract routes **266 → 271**, no new log kind.
> **Last verified: 2026-09-27** — against the branch's own code by `pytest` (whole suite, `-n 16`: 9206
> passed, 3 skipped), `ruff check .`, `node --check` + `node --input-type=module --check` on every touched JS
> file, `node --test site/mock/*.test.mjs` (25 passed), `node site/mock/check.mjs` against a mock from the
> worktree on 8827 (*22 pages, 271 routes, 26 core settings, all keys present*), and headless renders of the
> Posts page (the Blocks section with the front-door editor, the Welcome drawer's block list, the Add a
> block dropdown on another post, a refused add, Save the words) and the Modmail page's Front door card at
> 1400 px and 390 px — zero console errors, no sideways scroll (the only logged line is the browser's own
> `409` for the add that was forced onto a disabled option to see the refusal).
> ⚠️ **NOT checked:** nothing here met Discord — no boot, no token, no message sent or edited, no button
> pressed in a client, no deploy; `TEST_MODE` and every mode key were left alone.

## The ask (owner, 2026-09-27 23:4x Phoenix, verbatim)

> *"for the appending the modmail to that post, can we make that a check box for all post? set it on for
> the welcome post but default off to any post. or maybe we go further and have an append menu button and
> in that append menu we have some sort of ui selector. probably a drop down with different menus to
> append. such as modmail. also as a further addition we'll need a way to edit the finer points of the
> menus. so lets have a menu section in post. maybe menu isnt the right word so if you can think of better
> wording let me know."* — then *"lets do blocks"*.

The word is **Block**: *Add a block…*, *Blocks*, *Remove Front door*.

## As built

### The kinds registry — `black_bloc/post_blocks.py`

`KINDS` holds one `BlockKind` per attachable kind: `key`, `name_key` (a settings key — the display name),
`name_default`, `exclusive` (one post at a time), `cache_column`, `keys` (what its editor writes),
`parts(bot, guild, row) → (embed, view, stamp) | None`, `turned(...)` (what happens to a message already up
when the block is added or removed) and `redraw(bot, guild)`.

The front door plugs in through the EXISTING door code — no second implementation: `parts` is the cog's
`carried_parts`, `turned` is `posts.turn_carrying` → `door_follows_post`, `redraw` is the door cog's new
`redraw_now`, which runs `_redoor` for that guild under the sweep's own `Reconciler` lock (checklist 37).
**Adding a kind later is one `KINDS` entry + its renderer + its editor in `blockwords.js:BLOCK_EDITORS`.**

### Storage — schema 78

```sql
post_blocks (id, guild_id, post_id → posts ON DELETE CASCADE, kind, position, exclusive, added_at, added_by,
             UNIQUE (post_id, kind))
CREATE UNIQUE INDEX post_blocks_one_holder ON post_blocks(guild_id, kind) WHERE exclusive = 1
```

- **One at a time is held TWICE**: in words by the move (`held_elsewhere` → 409 `block_held_elsewhere`,
  naming the holder) and by the partial unique index, so two presses racing past the check still leave one
  row (`attach` uses `INSERT OR IGNORE` and answers False).
- **Migration** (`Database._backfill_post_blocks`, only when the stored schema is below 78): every post with
  `carries_door = 1` gets one `frontdoor` row (position 0, exclusive, `added_by` = its last editor). It runs
  once — a block removed after the upgrade is never put back by a later boot.
- **`carries_door` is kept, read-compatible, derived.** `post_blocks.keep_cache` rewrites each kind's
  `cache_column` from the table after every block write, and nothing else writes it (`set_carries_door` now
  goes through `post_blocks.set_carried`). Every door path that reads `carries_door` (`door_carrier`,
  `take_door_down`, `_redoor`, `on_post_published`, the preview, the API) works unchanged — nothing live can
  lose its door on upgrade. `door_hash` stays the front door's drawn stamp.
- The shipped seed's `welcome` entry carries `"blocks": ["frontdoor"]`, applied only when the seed MAKES the
  post (a fresh guild) and only if no other post already holds the door.

### The message

`posts.message_payload(bot, guild, row, kinds)` joins the post's own message with each attached kind's parts
in `position` order (`with_blocks`: embeds appended in order, views merged). `publish_post` reads the kinds
from the table. With the one kind there is, the welcome post's message is byte-for-byte v180's: rules as
content, the door card as the last embed, the three `door:<kind>:<guild>` buttons; pin still per post (off
for `welcome`); shadow still decided by the post's mode (the door's note rides the card's footer). Tested:
`tests/cogs/community/test_frontdoor.py::test_the_welcome_post_carried_as_a_block_goes_out_exactly_as_v180_sent_it`.

### Which buttons show — three new keys

The brief listed *"which buttons show"* among the door's keys; there was none. Added
`frontdoor_show_ticket` / `frontdoor_show_request` / `frontdoor_show_event` (bool, on; filed under modmail).
`frontdoor.shown_kinds` drives `door_view` (the posted door and a carrier) and `build_panel` (`/ask`). The
door's stamp gains a `hidden:` part ONLY when something is hidden, so the deploy does not re-edit every door
message. All three off leaves a card with nothing to press — the editor says so in amber; it is allowed
(staff's call).

### The site

| Where | What |
|---|---|
| Posts ▸ a post's drawer ▸ **Blocks** | The attached blocks, each with **Remove** (and ↑ / ↓ once there are two). **Add a block…** opens a dropdown of the kinds not on this post; an exclusive kind another post holds is disabled and reads *Front door — on Welcome and rules*, with a line under it saying to remove it there first. A block move acts at once (like Post it) and keeps the unsaved draft. The preview draws the blocks under the post (`blocks` sample). The *Carry the front door* switch is gone. |
| Posts ▸ **Blocks** section (between the posts list and Settings and logs) | One card per kind: *one post at a time*, *on Welcome and rules*, an **Open Welcome and rules** button, and a fold **Edit the Front door block**. |
| `site/public/assets/blockwords.js` | THE editor of the front door's words — heading, line, the three labels, which buttons show, the rehearsal note — with a live preview of the draft. **Save the words** writes each changed key through `PUT /api/settings/{key}` (the same path and log rows as the Settings page), then `POST /api/post-blocks/frontdoor/redraw`. |
| Modmail ▸ Doors ▸ **Front door** card | The same `frontDoorWords` component, in a fold **Edit its words** — extracted, not copied. |

### Discord — the `/posts` card

The *Carry the front door* button is gone. The card lists **Blocks: Front door**, one **Remove Front door**
button per attached block (row 1, beside Versions and Back — at most three), and an **Add a block…** select
(row 4) offering the kinds not on the post; a kind another post holds reads *On Welcome and rules — one post
at a time; adding it here is refused*, and picking it is refused in words (Discord cannot disable one
option). Both go through the same `add_block` / `remove_block` as the site.

### API

| Route | Does |
|---|---|
| `POST /api/posts/{slug}/blocks` `{kind}` | adds; already on it → 200 *"already on"*; unknown → 400 `unknown_block`; held elsewhere → 409 `block_held_elsewhere` |
| `PUT /api/posts/{slug}/blocks` `{order: [kinds]}` | reorders; must name each attached kind once, else 400 `bad_order` |
| `DELETE /api/posts/{slug}/blocks/{kind}` | removes; not on it → 409 `block_not_on` |
| `GET /api/post-blocks` | `kinds`: every kind with `name`, `name_key`, `exclusive`, `keys`, `on` (the posts), `where` |
| `POST /api/post-blocks/{kind}/redraw` | redraws every carrier now; answers `redrawn` and the sentence |

Post rows gain `blocks` (`kind`, `name`, `position`, `added_at`, `added_by`); every posts payload gains
`block_kinds`. `PUT /api/posts/{slug}` still takes `carries_door` (read-compatible). Each add / remove /
reorder writes ONE `post.saved` row (`block_added` / `block_removed` / `blocks_order`, plus `carries_door`
for the door — the key v180's rows used), `web.` from the site (checklist 34).

## Deviations

1. **Two extra columns on `post_blocks`: `guild_id` and `exclusive`.** The brief's table was `(post_id, kind,
   position, added_at, added_by)`. `guild_id` is what makes "one post at a time" per guild expressible as a
   partial unique index; `exclusive` is written from the registry so the index does not have to name kinds
   in SQL.
2. **`carries_door` is kept as a derived column, not retired** — the brief allowed either. Retiring it would
   have meant rewriting a dozen synchronous door paths that read it; deriving it keeps them untouched.
3. **`door_hash` stays the front door's stamp** rather than moving onto the block row. A second kind that
   needs its own stamp should get a `drawn_hash` column on `post_blocks`; `redraw_carrier` (the in-place edit
   of a carrier) also still assumes the door is the only block — it keeps the post's own embed and appends
   the door's. Both are the first job of kind two.
4. **Reorder does not edit a message already up** — it says *"The message shows it the next time you press
   Update the post."* With one kind there is nothing to reorder today.
5. **Three new keys the brief called "the same keys as today"** (`frontdoor_show_*`): the brief also asked
   for "which buttons show", and no key existed. Plus `posts_block_frontdoor_name` (the display name as a
   key, as asked). Keys **641 → 645**.
6. **Saving from the editor redraws at once** (the brief's "immediate is better … if cheap"): cheap, because
   the door cog already had the whole path; it runs under the sweep's lock. A door word changed anywhere
   ELSE (Settings page, `/settings`) still reaches a carrier on the ≤ 5-minute sweep, as in v180.
7. **The preview draws the editor's unticked buttons through a sample (`shows`)**, not an override: preview
   overrides must be text keys (`test_every_key_a_renderer_claims_is_a_real_setting`).
8. **Staff answers are module constants, not keys** (`BLOCK_*` in `post_blocks.py`, the card words in
   `posts.py`), following the Posts module's convention (post-carries-door Deviation 1). Nothing new is
   POSTED to members: the door part is still drawn wholly from the door's keys.
9. The three refusal sentences that told staff to *"Turn Carry the front door off"* now say to remove the
   front door block (`DOOR_CARRIED_ELSEWHERE`, `DOOR_RIDES_ELSEWHERE`, `DOOR_OFF_THE_POST_SAID`).
10. The mock seeds `welcome` carrying the front door block (live has since v181), so the contract's action
    kinds gained `web.frontdoor.rides_post` and `web.frontdoor.redrawn_on_post` (both real kinds since v180).

## What was NOT verified

- ⚠️ Nothing met Discord: the combined message, the card's new select and Remove button, `redraw_now` editing
  a real message, a hidden button leaving the posted door — all exercised on fakes only.
- The live database has not run 77 → 78; the migration is tested on a schema-77 file built in a test.
- `rehearsal_note` is a core key; if `settings_core_keys_admin_only` is on, a non-admin's Save the words
  stops at that key with the settings API's own refusal — not exercised.
- The redraw route against the real router answered with `redrawn: false` in tests that do not load the door
  cog (it says the sweep will carry it); `redraw_now` itself is tested through the cog fixture.
- The Settings page's rows for the four new keys were not looked at in a browser.

## Live check steps for the conductor (after merge + migrate + deploy)

1. Logs after boot: `database: 1 post(s) carrying the front door now carry it as a block` (Fly logs).
2. Posts ▸ **Welcome and rules** — the drawer's **Blocks** lists *Front door* with **Remove**; the preview
   draws the card under the rules. #welcome-test (or #welcome) still shows ONE message, unchanged.
3. Posts ▸ **Blocks** ▸ Front door ▸ **Edit the Front door block** ▸ change the heading ▸ **Save the words** —
   the sentence says every carrier is redrawn, and the message's card changes in place within seconds (no
   second message; the rules text untouched). Change it back the same way.
4. Open **When staff are around** ▸ **Add a block…** — *Front door — on Welcome and rules* is disabled with the
   line naming the holder.
5. `/posts` ▸ Welcome and rules — the card shows **Blocks: Front door** and **Remove Front door**; another
   post's card shows the **Add a block…** select.
6. Logs: `web.settings.set` per changed key; no `post.saved` for a words save; `web.post.saved` with
   `block_added` / `block_removed` if a block was moved.
