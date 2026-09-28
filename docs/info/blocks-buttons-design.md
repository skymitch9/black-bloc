# Blocks buttons — four one-button blocks: Marathon role, ping me when they go live, set your birthday, propose an event

> **Audience:** the conductor, reviewers, and the build that adds the next block kind.
> **Status:** TRACKED · 🔨 **BUILT on branch `blocks-buttons`** (off `main` `d418ca13`), NOT merged, NOT deployed.
> ⚠️ **2026-09-28:** the birthday block now goes straight to the date form — branch `birthday-block-modal`, see
> [*Birthday block goes straight to the form*](#birthday-block-goes-straight-to-the-form) (BUILT, NOT merged).
> No migration (schema stays **79**). Registry keys **651 → 671**, contract routes **272 → 276** (the four
> `POST /api/post-blocks/<kind>/redraw` entries — the Python route already took any kind), three new log kinds
> (`marathon.role_joined`, `marathon.role_left` routine; `marathon.role_failed` important by its suffix). Go-live page
> keys **83 → 86** (the three `pings_block_*` keys, in a drawer of their own).
> **Last verified: 2026-09-28** — against the branch's own code (`91d834be`) by `pytest` (whole suite, `-n 16`:
> **9337 passed**), `ruff check .` (clean), `node --input-type=module --check` on all 47 `site/public/assets/*.js`,
> `node --test site/mock/*.test.mjs` (25 passed), the eight `site/mock/*.test.mjs` the deploy gate runs (all ok;
> `golive-join` now places **86** keys), and `node site/mock/check.mjs` against a mock started from the worktree on
> port 8851 (*22 pages, 276 routes, 26 core settings, all keys present*).
> ⚠️ **NOT checked:** nothing here met Discord (no boot, no token, no message sent or edited, no button pressed in a
> client, no role added to anybody), and **no page was rendered in a browser** — this build was not allowed to touch
> one, so the four editors and their previews have been seen by nobody. `TEST_MODE`, every mode key and every ping
> setting were left alone.

## The asks (owner, verbatim)

> *"Let's make all the blocks you suggested but not post them yet, only the front door should be posted in welcome
> test"* — group (B): **get the Marathon role** toggle, **ping me when X goes live** (the pings follow picker),
> **set your birthday**, **propose an event**. Owner decision carried in the brief: the Marathon role block pings
> nobody and changes no ping setting (*nothing pings for now*).

## As built

### One shape, four kinds

Every one of the four is **a card (heading + line) and ONE persistent button**. The shape is shared, the behaviour is
each feature's own:

| Piece | What |
|---|---|
| `black_bloc/button_block.py` | Pure helper: `Words` (the three keys), `look` (saved words, else the shipped ones, clamped to 256 / 4000 / 80), `ButtonLook.stamp`, `custom_id` / `template` (`<head>:<guild_id>`), `parts` (embed, `View(timeout=None)` with the one item, stamp), `said` (a member's private answer from its key, falling back to the shipped words with a log line if a staff template will not fill — checklist 17). |
| Each feature's pure module | `BLOCK_HEAD`, `BLOCK_WORDS`, `block_drawn(store, guild_id)`, `block_look(store, guild_id)`. The preview calls the same two. |
| Each feature's cog | `block_parts(bot, guild, row)` → `None` while the feature is off, else `button_block.parts(...)`; a `SafeDynamicItem` button whose `on_click` is **the same function the feature's command calls**; registered in that cog's `cog_load`. |
| `black_bloc/post_blocks.py:KINDS` | Four entries appended: not exclusive, no cache column, `footprint=(1, 1, 1)`, `turned=blocks_turned`, `redraw=blocks_redraw` — exactly the temp voice pattern. |

| Kind | Name (key, default) | Drawn while | Button → | custom_id |
|---|---|---|---|---|
| `marathonrole` | `posts_block_marathonrole_name` · *Marathon role* | always (see Deviation 3) | `cogs/content/marathon_role.py:toggle_marathon_role` | `marathonrole:toggle:<guild>` |
| `pingsfollow` | `posts_block_pingsfollow_name` · *Ping me when they go live* | `pings_mode` is `on` | `cogs/content/pings.py:open_pings_panel` = the `/pings` panel with its **Follow a streamer…** picker | `pingsblock:open:<guild>` |
| `birthday` | `posts_block_birthday_name` · *Set your birthday* | `birthday_mode` is not `off` | ~~`cogs/community/birthdays.py:open_birthday_panel` = the `/birthday` panel, whose **Set my birthday** raises the date modal~~ → since `birthday-block-modal` (`0b3b2a02`): `open_block_date_modal` = the panel's own date modal, answered privately — see [*Birthday block goes straight to the form*](#birthday-block-goes-straight-to-the-form) | `bdayblock:open:<guild>` |
| `proposeevent` | `posts_block_proposeevent_name` · *Propose an event* | `events_mode` is not `off` | `cogs/community/events.py:open_propose` → the front door's own `open_the_event` (the private hand-off card whose **Propose** is the `/event` draft) | `eventblock:propose:<guild>` |

**Non-exclusive, all four.** Nothing is stored per message and every button is guild-keyed, so two copies cannot
disagree.

### Additive only — what changed in existing feature code

| Feature | The one change | Pinned first (`7eeb3ce7`, passing before and after) |
|---|---|---|
| pings | `/pings`'s body moved into `open_pings_panel(interaction)`; the command calls it. `cog_load` also registers `OpenPingsButton`. | `/pings` the cog's only command; its panel carries the Follow picker on row 0 with the streamer in it; no picker while pings are off. The existing ephemeral / DM / database-down tests. |
| birthdays | `_ready`'s body moved into `birthday_ready(interaction)` (`_ready` calls it) and `/birthday`'s body into `open_birthday_panel`. `cog_load` registers `OpenBirthdayButton` **before** its database check. | `/birthday` the only command; its **Set my birthday** raises the `DateModal` for the member themself. |
| events | New `open_propose`, `ProposeBlockButton`, `block_parts`; `cog_load` makes a second `add_dynamic_items` call. `/event`, `ProposeButton`, `DecisionButton` untouched. | `/event` the only command; the front door's `open_the_event` answers a private `EventHandoff` whose only child is an `EventDoor`. |
| marathon | `cog_load` registers `MarathonRoleButton` **after** the eight it already registered. Everything else is a new module. | The eight existing buttons, in their order. |
| front door | **Nothing.** `open_the_event` is imported, not changed. | — |

### The Marathon role toggle

- **New key `marathon_role_id`** (role, blank). There was none: `DONE.md` ▸ 2026-09-26 records the owner saying the
  Marathon role *"already exists"* while *"no setting the site exposes names it"*. Set on the Settings page ▸ marathon,
  `/settings`, or the block's own editor.
- **A press**: guild check → the guard (`bot.guard.allows_channel`, checklist 1) → `usable_role` → defer (private) →
  `add_roles` / `remove_roles` → one log row → the member's private answer. The role change and the row come before
  the answer (checklist 12). Every answer is `AllowedMentions.none()`; nothing is ever mentioned.
- **Refuses in words, and does nothing,** when no role is picked, the picked role is gone, or it is **unsafe** —
  managed, `@everyone`, or carrying any of `Permissions.elevated()` or `mention_everyone`. All three answer with
  `marathon_block_unset_said` (members do not need the difference); gone / unsafe also write
  `marathon.role_failed` with `reason` so staff see why. A Discord refusal answers with pings' existing `FORBIDDEN`
  sentence (Manage Roles / role order) and writes `marathon.role_failed` with the exception.
- **Words**: `marathon_block_title` / `_text` / `_label` (the card) and `_added_said` / `_removed_said` / `_unset_said`
  (the private answers; `{role}` = the role's name).

### Words — twenty keys, every posted word a key

`marathon_role_id`; `marathon_block_{title,text,label,added_said,removed_said,unset_said}`;
`pings_block_{title,text,label}`; `birthday_block_{title,text,label}`; `events_block_{title,text,label}`;
`posts_block_{marathonrole,pingsfollow,birthday,proposeevent}_name`. Filed under each feature by prefix (marathon,
pings, birthday, events, posts — no `NAMESPACE_OVERRIDE`). Each is in the registry (`BUTTON_BLOCK_DEFAULTS`,
`KEY_TYPES`, `KEY_HELP`), the mock's `SETTING_SPECS`, and `labels.js`. The three pings keys also land on the Go-live
page, in a new drawer **The ping block on a post** (`golive-join.js`), placed before *Ping roles* so that drawer still
holds its ten.

### The site

| Where | What |
|---|---|
| `site/public/assets/blockwords.js:buttonBlockWords(kind)` | ONE editor for all four: heading, line, button label, live preview through `blockPreview({ feature: 'block_<kind>' })`, **Save the words** → `saveSetting` per changed key → `POST /api/post-blocks/<kind>/redraw`. The Marathon role editor adds the role picker (`roleSelect`; *not set* clears the key), an amber line while no role is picked, and the three private answers. |
| `BLOCK_EDITORS` | Four entries appended. Posts ▸ **Blocks** draws a card per kind with **What it looks like in Discord** (unchanged code — it iterates `block_kinds`). |
| Preview | `preview.py:BUTTON_BLOCKS` → four `BLOCK_DRAWS` entries (off → nothing unless `always`) and four renderers `block_<kind>` claiming only the three card keys. Mock twins in `server.mjs` (`previewButtonBlock`). |

## Deviations

1. ~~**Birthday opens the `/birthday` panel, not the date modal directly.**~~ ⚠️ **REVERSED 2026-09-28 by
   `birthday-block-modal` (`0b3b2a02`)** — the owner, asked *"should the birthday block go straight to the date
   form?"*, answered *"Straight to the form"*. The risk below was real and is closed by a separate submit path that
   never edits (see [*Birthday block goes straight to the form*](#birthday-block-goes-straight-to-the-form)). The
   original reasoning, kept so nobody reverts it blind: The brief allowed *"modal or panel"*. A
   modal raised straight from a button on a POSTED message would, on submit, run `date_submit` → `opened()` →
   `response.defer()` → `edit_original_response` — which for a modal raised from a message component edits **that
   message**: the public post would be overwritten with one member's birthday panel. Opening the panel first (ephemeral)
   keeps every later edit on the member's own card, and changes nothing in the birthday code. One extra press.
2. **Propose reuses the FRONT DOOR's `open_the_event`**, so the hand-off card's title/line are the door's constants
   and its Propose button carries `frontdoor_event_label`. It is the only existing function that raises the `/event`
   draft from a posted message safely (the draft replaces the message it was raised from). The block's own button is
   gated on `events_mode` first (`EVENTS_OFF`, events' own sentence) so a press on a stale post never shows a card
   whose button would then refuse.
3. **The Marathon role block is drawn even with no role picked** (the owner: the press *"answers in words that staff
   have not set it up yet"*). *"The preview says so"* is met in the editor — an amber line under the role picker while
   it is blank — not by drawing different words on the card, because the preview must show what Discord would show.
4. **`marathon_role_id` is a NEW key** — none existed (see As built). It ships blank.
5. **A role with a staff permission is never handed out** (not asked for; added because the key is a free role picker
   and a mis-pick would let anyone self-grant a moderator role). Staff keep the final say — they pick the role — but the
   bot refuses to be the door to an elevated one, logs `marathon.role_failed` (`reason: unsafe`), and the key's help
   says so.
6. **Staff-set label lengths are clamped at render (80 / 256 / 4000), not refused at the validator** — the pattern the
   door and temp voice words already follow; the help text says *at most 80 characters*.
7. **Ping block drawn only while `pings_mode` is exactly `on`** (pings has no shadow; `off` refuses every opt-in).
   Birthday and propose draw in `shadow` too, matching their commands, which open in shadow.
8. **Three new log kinds** for the toggle (none existed for a self-served role outside role menus). Classified:
   joined / left routine, failed important. `KNOWN_DYNAMIC` gained the three `marathon_role.py::helpers.*` call sites.
9. **`test_the_golive_page_still_draws_eighty_three_keys` → `…eighty_six_keys`** and the contract's
   `settings.help` gained the three pings keys — the pings namespace IS the Go-live page's.
10. **"Sample data where state is per-member"**: none of the four posted cards carries per-member state (the toggle's
    label is a fixed *Get or drop…*, the pickers open privately), so the previews draw the saved words only.

## What was NOT verified

- ⚠️ **Nothing met Discord.** Every press ran against fakes; the four buttons were pressed by calling `callback` —
  NOT through discord.py's dynamic-item regex dispatch on a real client. No role was added to a real member; the
  role-hierarchy refusal was simulated with a raised `discord.Forbidden`.
- ⚠️ **No page was seen.** The four editors, the role picker's amber line, the Go-live drawer and the Blocks cards'
  previews are syntax- and contract-checked only.
- A post carrying all four at once was tested in fakes (four cards, four buttons, one message, each stamp written);
  Discord's own rendering of that merged view was not seen. The `/posts` card still offers at most `REMOVE_CAP` (3)
  **Remove** buttons (pre-existing); a post with more blocks than that removes the rest from the site.
- Whether the unsafe set matches every role the owner would call "staff": it is discord.py 2.7.1's
  `Permissions.elevated()` (kick, ban, administrator, manage channels / guild / messages / roles / webhooks /
  expressions / threads, moderate members) plus `mention_everyone`. A role holding only e.g. `view_audit_log` or
  `move_members` would still be handed out.

## Live check steps for the conductor (after merge + deploy)

1. Fly logs after boot: nothing new expected (no migration). No post is edited — none carries these blocks.
2. Posts ▸ **Blocks**: six cards now — the four new ones read *on no post yet*, each with **What it looks like in
   Discord**. *Ping me when they go live* draws nothing unless pings are on (the card preview uses `always`, so it does).
3. Posts ▸ Blocks ▸ **Marathon role** ▸ *Edit the Marathon role block*: the role picker says *not set* and the amber
   line shows; type in the heading — the preview changes. Do NOT save a role unless the owner names it.
4. Settings ▸ marathon: *The Marathon role members can take with its block* is listed, blank. Go-live ▸ Settings: a
   drawer **The ping block on a post** holds three words keys.
5. `/pings`, `/birthday`, `/event`, the front door's **Propose an event**: exactly as today.
6. ⚠️ Do NOT add any of the four to a post — the owner said only the front door is posted.

## For the conductor to decide

- **Which role is the Marathon role** (`marathon_role_id`) — the owner's call; blank until then.
- **The propose hand-off wording** (Deviation 2): fine to share the door's, or give the block its own title/line/label
  keys for the hand-off card (would need `event_handoff` to take them — a change to door code, so not done here).
- ~~**Birthday straight to the modal** (Deviation 1): acceptable as panel-first, or build a modal submit path that answers
  on a fresh private message (a change to `date_submit`, so not done here).~~ DECIDED 2026-09-28 (owner: *"Straight to
  the form"*), built on `birthday-block-modal` — see the section below.

## Birthday block goes straight to the form

> **Status:** 🔨 **BUILT on branch `birthday-block-modal`** (off `main` `c9ee1f46`), NOT merged, NOT deployed. No
> migration. Registry keys **689 → 692**. **Last verified: 2026-09-28** against the branch (`8c1cb907`) by `pytest`
> (whole suite `-n 16`, 0 failed), `ruff check .`, `node --input-type=module --check` on every
> `site/public/assets/*.js`, the eight `site/mock/*.test.mjs` the deploy gate runs, and `site/mock/check.mjs` against a
> mock started from the worktree on port 8881. ⚠️ Nothing here met Discord and no page was seen in a browser.

**The ask** (owner, 2026-09-28 06:5x, answering *"should the birthday block go straight to the date form?"*):
*"Straight to the form"*.

### As built

| Piece | What |
|---|---|
| Press | `OpenBirthdayButton.on_click` → `open_block_date_modal`: `birthday_ready` (guild, database) → birthdays off? `birthday_block_off_said`, privately, no modal → `open_date_modal(..., mine=True, private=True)`. The modal is the panel's own `DateModal` — same field, placeholder, 10-character cap, title, prefill of what is stored. |
| Submit | `DateModal.on_submit` with `private=True` → `Birthdays.block_date_submit`: `response.defer(ephemeral=True, thinking=True)` → `db_ready` → birthdays turned off since the press? `birthday_block_off_said` → `typed_birthday` (the same parse + `store_birthday` the panel uses, source `self`, one `birthday.set` row) → `birthday_block_saved_said` or `birthday_block_refused_said` with `{said}` = the panel's own sentence. Every answer goes through `panels.answer` → an ephemeral **followup**. |
| Why it cannot touch the post | A modal raised from a message component answers its submit, by default, by editing that message. The block path never calls `edit_original_response`, `response.edit_message` or a bare `defer()` (which for a modal submit is `deferred_message_update`); its only defer is `thinking=True` + `ephemeral=True` (`deferred_channel_message`, flags 64 — a NEW private message). Proved by `tests/cogs/community/test_birthdays.py` `test_the_block_s_form_saves_and_answers_privately_never_over_the_post` (defer args pinned, no post edit, no original edit, no message edit, the answer an ephemeral followup with no view/embed) and a mutation check: adding one `edit_original_response` to the block path fails two tests. |
| Panel unchanged | `date_submit` now calls `typed_birthday` instead of inlining the parse; `store_birthday` returns `(saved, said)` so the block can tell a save from a refusal (checklist: silent failure distinguishable from success). Pinned first in `adb38464` — the panel's Set → modal → saved → panel re-rendered + private sentence, the refusal still re-rendering, staff *Set their birthday* → card re-rendered — passing before and after. |
| Words | `birthday_block_saved_said` · `birthday_block_refused_said` · `birthday_block_off_said` — registry, mock rows, labels, filed under **birthday** by prefix, in the block's `keys` (`post_blocks.py`) and in the block editor's `said` rows (`blockwords.js`). A broken `{…}` falls back to the shipped wording (`button_block.said`). `birthday_block_label`'s help now says the button asks for the date straight away. |
| Preview | Unchanged — it draws the card and the button, which did not change. |

### Deviations

1. **The birthday Settings group is now over the 25-cap** (28 keys), so `/settings` ▸ birthday shows *25 of 28 — the
   rest are on the site* and a **Find a setting…** button, like chat / core / events / golive / marathon / modmail /
   posts. The brief said file under birthdays; the tests that used birthday as the under-cap example now use pings.
2. **The block's modal has no Try again.** Checklist 36 wants a `render_again`, but there is no private surface to
   re-render (the post must not be). A failure answers the plain private sentence and writes `error.modal` (pinned by
   `test_a_failure_in_the_block_s_form_is_a_private_sentence_and_a_row`); pressing the post's button again is the retry.
3. **Refusal words are the panel's** (`DATE_UNREADABLE`, `date_problem`, `year_problem` — code constants today, as they
   are for `/birthday`), wrapped by the editable `birthday_block_refused_said`. Making the panel's own refusals keys
   was out of scope.
4. **Off at press AND at submit.** The press checks `birthday_mode` (a stale post drawn before birthdays went off); the
   submit checks again, so a form left open while staff turned birthdays off saves nothing.
5. The save's `source` stays `self` (the member set it themself); the action row does not say *via the block*.

### NOT verified

- Nothing met Discord: no press in a client, no modal seen, no ephemeral answer seen, and in particular **Discord's own
  handling of `deferred_channel_message` on a modal submit raised from a posted message** is known from discord.py
  2.7.1's source, not observed.
- No page seen: the block editor's three new rows and the Settings ▸ birthday entries are syntax- and contract-checked
  only.
- The block is on no post (owner: only the front door is posted), so there is nothing live to press yet.

### Live check steps (after merge + deploy, only if the owner puts the block on a TEST post)

1. `/birthday` ▸ **Set my birthday** / **Change my birthday**: exactly as before — the panel re-renders with the date
   and a private sentence follows.
2. Press the block's **Set my birthday** as a non-staff account: the date form opens at once (prefilled if stored).
   Send `08-10`: a private *Your birthday is **August 10**… Press the button again, or use /birthday, to change it.*
   The post itself is unchanged for everyone (check from a second account).
3. Send `next tuesday`: the private refusal ending *Nothing was saved; press the button to try again.*; nothing stored.
4. Set `birthday_mode` to `off` with the form open, send it: the private *Birthdays are turned off…*; nothing stored.
   (Turning birthdays off also removes the block on the next redraw.)
5. Logs ▸ birthday: one `birthday.set` per save, none for refusals.
