# The channel catalog — what each channel is for, in staff's words

> **Audience:** whoever touches the channel list the conversation models read, and the reviewer.
> **Status:** TRACKED · ✅ **LIVE as v159** (2026-09-23 **14:07** Phoenix, release commit `c54f14a8`; merge `3acc8a83`, and the Channels page follow-up merge `654be0c8`).
> **Verified live at the v159 boot:** the boot log read `database ready` 21:07:23Z (schema 56: `channel_notes`,
> `channel_drafts`); action 10103 `chat.channel_drafts_seeded count=94, notes=2` at 21:07:27Z; read at the ritual through
> the operator token, `GET /api/chat/channels` answers `review {total: 94, reviewed: 2, drafts_left: 92}`,
> `budget {used: 1454, cap: 4096, trimmed: []}`, the two owner notes (#general-chat, #speed-and-pbs) live as `used`;
> **23** of 94 channels carry a Discord topic and **24** reach the directory (65 `not_visible`, 4 `archive`,
> 1 `ignored_category`) — the two unknowns under *What was NOT verified* are now readable on the page.
> ⚠️ **NOT verified live:** no Discord button (`/chat` ▸ Channel notes…), no browser on the Channels page, no staff
> review move, real staff names in the chips. **Until the deploy the status read:** BUILT, NOT MERGED — branch `channel-catalog`, off `main` `8e4ca731`,
> worktree `C:/lcw/bb-channel-catalog`. Nothing deployed; schema 54 has never run against the
> live database. The draft descriptions for the live channels are in
> [`channel-catalog.md`](channel-catalog.md) and are **not** in the bot.
> **Follow-up 2026-09-23 (branch `channel-visibility`, NOT merged, NOT deployed):** *channel reach* at the foot of this page — opt-in roles count, a staff override per channel, schema 57.
> **Last verified: 2026-09-23 14:1x** — the status lines above only, at the v159 docs ritual; the body was not re-read.
> Before that, **2026-09-23** — against the branch tip by `pytest -n 16` (7427 passed),
> `ruff check black_bloc tests site` and `node site/mock/check.mjs` (21 pages, 201 routes), and
> the Chat page drawn in headless Chrome against the mock. ⚠️ Nothing met live Discord.

## 1. The ask, verbatim (owner, 2026-09-23)

> "the bot thinks speed-and-pbs is the general chat, its not, that the channel for talking about
> speed running records. #general-chat is the general chat"

then

> "lets catalog every channel in the discord and the description to help the bot get a better
> feel for each channel"

## 2. Why it happened

The conversation models are handed a channel list with every answer
(`directory.py:directory_block`, one line per readable text channel, `#name — <topic>`). The
Discord **topic** was the only thing that said what a channel is for. Most channels on the live
server have no topic, so the model guessed from the name — and *speed-and-pbs* read as a
general channel. The daily knowledge read (`knowledge.py:channel_sections`) had the same blind
spot: a channel with no topic got no section of its own.

## 3. The model

- **Schema 54** — `channel_notes(guild_id, channel_id, note, set_by, set_at)`, PK
  `(guild_id, channel_id)`, a new table in the additive style (`CREATE TABLE IF NOT EXISTS`, no
  data moves). Helpers in a new `black_bloc/channel_notes.py` beside `directory.py`:
  `notes_for`, `notes_or_nothing`, `get_note`, `set_note`, `clear_note`, `clean_note`.
- **A note beats the topic.** `directory.description_of(channel, notes)`: the note (cut at
  `NOTE_CHARS` = 240), else the topic (cut at `TOPIC_CHARS` = 160), else the bare name. The same
  order feeds the daily knowledge read, so the directory and the knowledge base never disagree
  about a channel.
- **The budget is unchanged**: 4 KB, and over it the longest DESCRIPTION goes first (a note or a
  topic, whichever is longer), exactly as topics did.
- `directory_preview(bot, guild, notes)` returns the exact block plus `used`, `cap` and the
  channels whose description fell off — the site draws it.
- **One write.** `chat_panel.save_channel_note` / `clear_channel_note` are the only writers; the
  API and the `/chat` panel both call them (checklist 34: the route passes `via=website`, one
  action row per write). Log kinds `chat.channel_note_set` / `chat.channel_note_cleared`,
  ROUTINE. A blank note is a clear, never an empty row.

## 4. The doors

| Door | What it does |
|---|---|
| `GET /api/chat/channels` | Every text channel (not only the readable ones) with `id, name, category, category_id, topic, note, shown, hidden_because, position`, in Discord's order (loose channels, then category by category); `directory` (the block), `budget {used, cap, trimmed}`, `note_chars`, `counts` |
| `PUT /api/chat/channels/{id}` `{note}` | Staff (`writer`). Empty = clear. Over 240 → **422** `note_too_long` in words. Not a text channel of this guild → **404** in words |
| `DELETE /api/chat/channels/{id}` | Clears; clearing nothing says so (200) and writes no row |
| Chat page ▸ **Channel directory** | *What the bot sees* card (the block verbatim, bytes used of 4096, a meter, which descriptions were left off), then one row per channel — `# name · Category` (the `channelLabel` helper), the reason badge, the Discord topic dim or *no topic in Discord*, the note inline with Save / Clear — and a fold with the eleven words below |
| `/chat` ▸ **Channel notes…** | A card listing the notes, Discord's own searchable channel picker, a form prefilled with the current note; a blank box clears |

~~`hidden_because` is `ignored_category` (on `chat_ignore_categories`, or the modmail category),
`archive`, or `not_visible` (the `chat_visibility_role_id` view cannot read it) — the one test
`open_channels` applies, as `directory.why_hidden`.~~ **Superseded 2026-09-23 (branch
`channel-visibility`, commit `16b69f1a`):** the one test is now `directory.reach_in`, a
self-assignable role's view counts as well as the Member role's, staff can override one channel
either way, and `hidden_because` gains `hidden_by_staff` — see *Follow-up — channel reach* below.
`why_hidden` no longer exists.

## 5. Eleven words, all keys (checklist: every posted word is editable)

`chat_channel_note_saved`, `_cleared`, `_nothing`, `_too_long`, `_no_channel`,
`chat_channel_notes_button`, `_title`, `_intro`, `_placeholder`, `chat_channel_note_modal`,
`_label` — registry `KEY_TYPES`/`KEY_HELP`, defaults in one table
(`settings_store.CHANNEL_NOTE_WORDS`), placeholder checks through `TEXT_CHECKS`, a label each in
`labels.js`, a mock row each. The `chat` namespace already existed, so the `/settings` group
select (the 25-namespace cap in `posted-strings-audit.md`) gains nothing; the group itself goes
from 28 to **39** keys and was already past the 25-option picker, so **Find a setting…** reaches
them (the two tests that counted 28 now count 39).

## 6. Decisions and deviations

1. **`NOTE_CHARS` is a constant, not a key** — as the brief said. A longer note would eat the
   4 KB block; the cap is the budget's guard, not a preference.
2. **Helpers live in `channel_notes.py`, not `directory.py`** — the directory stays sync and
   pure (it takes a `notes` mapping); `chat_llm.conversational_reply` loads the notes with
   `notes_or_nothing`, which never raises, so an unreadable table costs a note and never an answer.
3. **The knowledge ingest reads notes too** (the conductor's clarification, 2026-09-23).
4. **No 25-per-page picker.** The brief asked for the repo's paging pattern; the repo's pattern
   for channels is `discord.ui.ChannelSelect` (15 uses), which Discord itself searches across
   every channel, so there is nothing to page.
5. **Editing is inline, not in the row drawer** — one input and two buttons per row; a drawer
   would add a click for no extra field.
6. **The `/chat` Settings card no longer lists the eleven word keys** — full sentences would
   swamp it; they are edited on the Settings page, `/settings` ▸ chat ▸ Find, and the Channel
   directory fold.
7. **The mock gained `#general-chat` (The Hole in the Wall) and `#speed-and-pbs` (Gaming)** so
   the owner's two notes could be seeded on channels of those names; its other channels are
   fixtures, so DRAFT notes are seeded only on `#welcome` and `#announcements`, whose names
   match live channels.
8. **Forums are not catalogued** — the directory reads `guild.text_channels` only, so a note on
   one of the five live forums would change nothing the model reads.
9. The live channel count is **94 text + 5 forum in 14 categories**, not the ~60 / ~10 the
   brief estimated (measured with `scripts/read.ps1 -Path /api/ref/channels`, 2026-09-23).

## What was verified

- `tests/test_directory.py` — note beats topic; blank note falls back to topic then name; the
  note's own 240 cap; over budget the longest description goes first; the preview is the exact
  block; each hidden reason.
- `tests/storage/test_db.py` — a schema 53 file gains the empty table, keeps its rows, reads 54.
- `tests/test_channel_notes.py`, `tests/test_knowledge.py`, `tests/test_chat_llm.py` (a stored
  note reaches the model's system text in place of the topic).
- `tests/test_chat_panel.py` and `tests/api/tools/test_chat.py` — set / clear / nothing-to-clear
  / 422 / 404 / staff gate / one row per write, `web.`-headed from the site.
- `tests/cogs/content/test_chat.py` — the button, the picker, the prefilled modal, the blank
  clear, the refusal, staff's own wording.
- The Chat page rendered in headless Chrome against the mock: the section and its rail entry,
  the block (423 of 4096 bytes), ten rows with the right badges, and a Save that answered
  *"The note for #free-nitro-here is saved…"* and put the line into the block.

## What was NOT verified

- Nothing met live Discord: not the `/chat` button, the picker, the modal, nor a real answer.
- The live topics — the operator API does not expose them, so the catalog's topic column is
  unknown until the page is opened after a deploy.
- Which live channels the Member view can read, so the catalog cannot say which drafts would
  actually reach the model.
  *(Measured at v159: 24 reach the directory. The channel-reach follow-up below found 8 of the 65
  `not_visible` are channels the owner says members DO see.)*
- The drafts in [`channel-catalog.md`](channel-catalog.md) are the builder's guesses from names
  and categories; the owner approves or rewrites them.

## Follow-up, 2026-09-23 — the Channels page: staff review the drafts on the site

> **Status:** **BUILT, NOT MERGED** — branch `channels-page` off `main` `d6709d48`, worktree
> `C:/lcw/bb-channels-page`. Nothing deployed; schema 56 has never run against the live database.

**The ask, verbatim (owner, 2026-09-23):** *"make that a page on the website and i will have the
staff do it"* → *"make it editable too so they can adjust the text"* — said of the 92 drafts in
[`channel-catalog.md`](channel-catalog.md).

### What was built

- **Schema 56** — `channel_drafts(guild_id, channel_id, draft, status, decided_by, decided_at)`,
  PK `(guild_id, channel_id)`, `status` ∈ `draft | used | rewritten | none`. Additive
  (`CREATE TABLE IF NOT EXISTS`, no data moves). ⚠️ Numbered **56**, not 55, because the
  concurrent `personality-tones` build takes 55 (`chat_voice`); the conductor may renumber — the
  table creation is idempotent and does not read the version.
- **The seed** — `black_bloc/channel_drafts_seed.json`, **94 rows** keyed by channel id
  (`name`, `category`, `draft`, `final`), generated once from the catalog table; 2 `final`
  (`#general-chat`, `#speed-and-pbs`), 92 drafts. `channel_drafts.seed_drafts` inserts only the
  rows for channels this guild HAS, with `INSERT OR IGNORE`, so a decided row is never touched
  and a re-seed is a no-op. It runs on the chat cog's ingest tick (first tick after ready, then
  every `INGEST_HOURS`), before the knowledge read, and logs `chat.channel_drafts_seeded` once.
- ⚠️ **The two finals become real notes on first boot.** A final row seeds as `used` AND is
  written through `channel_notes.set_note` — only when that seed actually inserted the row and
  no note exists yet. So the live bot reads the owner's two sentences from the first boot after
  the deploy; if staff later clear one, a restart does NOT bring it back (the row already exists).
  A note staff wrote before the seed is kept.
- **The model still reads ONLY `channel_notes`.** A draft nobody decided is never read.
- **One write path.** `channel_drafts.save_wording` is the save for BOTH doors (the site's
  `PUT` and the `/chat` ▸ Channel notes modal). A drafted channel records the decision (`used` when
  the words equal the draft, `rewritten` otherwise; blank = no note); a channel with no draft
  row falls through to `chat_panel.save_channel_note` unchanged. `use_draft` / `no_note` /
  `reset_draft` write the note with the existing helpers (`set_note` / `clear_note`). One
  action row per decision (checklist 34): `chat.channel_draft_used` / `_rewritten` / `_none` /
  `_reset`, ROUTINE, `web.`-headed from the site.
- **Status is derived against the note** (`channel_drafts.effective`): a note equal to the draft
  reads `used`, any other note `rewritten`; no note reads `draft` if nothing was decided, else
  `none`. So a note changed outside the page never leaves a chip that lies.
- **API** — `GET /api/chat/channels` rows gain `draft`, `status`, `decided_by {id,name}`,
  `decided_at`, and a top-level `review {total, reviewed, drafts_left}` (drafted channels only).
  `POST /api/chat/channels/{id}/use`, `/none`, `/reset` (staff, `writer`); `PUT` as above;
  `DELETE` on a drafted channel is the no-note decision. Every answer carries `review`.
  Refusals in words: 404 `no_such_channel`, 404 `no_draft`, 422 `note_too_long`.
- **Four new word keys** in `settings_store.CHANNEL_NOTE_WORDS`: `chat_channel_draft_used`,
  `_none`, `_reset`, `_missing`. The `chat` group goes **39 → 43**.
- **The page** — `site/public/channels.html` + `assets/page-channels.js`, in the rail right
  after Chat under *Runs the cookout*. Head: *Reviewed N of 94 · M drafts left* and **Next
  draft**. **Review** section: a filter (Drafts left / Reviewed / All, a category select, a
  search), then one card per channel — `# name · Category`, the status chip (*Draft / Used /
  Rewritten / No note · by whom · when*), the told/left-out badge, the Discord topic or *no topic
  in Discord*, the words in an editable box (the note when one exists, else the draft), **Use
  this** (only while the box equals the draft), **Save my wording** (when it differs), **No
  note**, **Reset to the draft** (only when decided), and an `n / 240` counter. A move updates
  its own card, the block and the progress in place; the card stays in view until the filter
  changes. **What the bot sees** (the block, bytes of 4096, trimmed names) and **Words** (the
  fifteen channel-note keys) sit beside it. The Chat page's *Channel directory* section is now a
  one-line link to the Channels page — one home.

### Decisions and deviations

1. **A fourth key, `chat_channel_draft_missing`** — the brief said three (39 → 42). `use` and
   `reset` on a channel made after the catalog must refuse in words, and every sentence the API
   answers with is a key. 39 → **43**.
2. **A fifth kind, `chat.channel_drafts_seeded`** — the boot seed writes rows, so it leaves one
   row, like `guide.seeded`.
3. **`logkinds.FEATURE_PAGES` unchanged** — it maps a FEATURE to a page, and the draft kinds are
   `chat` kinds, so they link to `chat.html`. Channels is not a feature of its own.
4. **The seed JSON carries `category`** beside `name/draft/final` — the mock needs it to place
   the 94 channels in their categories.
5. **The mock reads the seed JSON at start** (`site/mock/server.mjs` `CHANNEL_DRAFTS_SEED`), adds
   the 94 channels and their 14 categories to its channel list, and mirrors every move. Its old
   fixture `#general-chat` / `#speed-and-pbs` rows were removed (the real ids replace them), so
   the mock lists 102 text channels: the 94 plus 8 fixtures; `#welcome` and `#announcements`
   appear twice (fixture + seed) — a mock artefact only. The mock seeds `#qotw` as rewritten and
   `#gif-spam` as no-note so every chip is on screen (Reviewed 4 of 94 at start).
6. **Contract** gains `POST …/{drafted_channel_id}/use|none|reset`; `{drafted_channel_id}` is the
   seed's `#welcome` on the mock and a row the contract seed inserts on the real router.
7. **No Logs section on the page** — the chat kinds already have their Logs section on the Chat
   page; a second would be two log surfaces for one feature.

### Verified (2026-09-23, branch `channels-page`)

- `tests/test_channel_drafts.py` (26): 94 seed rows, 2 finals, every draft ≤ 240; only channels
  this guild has; finals become notes once and never again; a pre-existing note is kept; a
  decided row survives a re-seed; each move's status, `decided_by`, note and single log row;
  blank save = no note; the undrafted path; refusals; staff wording; the derivation table.
- `tests/storage/test_db.py` (54 → 56 additive), `tests/api/tools/test_chat.py` (the moves over
  HTTP, review counts, gate, refusals), `tests/cogs/content/test_chat.py` (the modal records the
  decision; the ingest tick seeds), `tests/test_logkinds.py`, key counts.
- The page against the mock in headless Chrome (CDP) at 1400 and 400 px: no horizontal scroll
  (`scrollWidth == clientWidth` at 400); **Use this** on `#welcome` moved the progress 4 → 5 of
  94, wrote the used-words sentence on the card, set the chip *Used · by Nick · <time>* and put
  `#welcome — Where new members land…` into the block; typing on `#roles` showed **Save my
  wording** + **No note** and hid **Use this**; the Reviewed filter showed the five decided rows.

### NOT verified

- ⚠️ Nothing met live Discord or the live database: not the boot seed against the real 94
  channels, not the finals landing as notes, not the `/chat` modal's decision row.
- Real staff names in the chip (the mock's member is *Nick*).
- The live topics — still unknown until the page is opened after a deploy.

## Follow-up, 2026-09-23 — channel reach: opt-in roles count, and staff have the final word

> **Status:** BUILT, NOT MERGED, NOT DEPLOYED — branch `channel-visibility`, worktree
> `C:/lcw/bb-channel-visibility`, off `main` `645ac862` (v160 live, schema 56). Commits
> `16b69f1a` (the rule, the table, the API, tests) and `3f700cd6` (the page, the mock, the
> contract). **Last verified: 2026-09-23** against the branch by `pytest -n 16`, `ruff`,
> `node site/mock/check.mjs` and the page in headless Chrome against the mock. ⚠️ Nothing met
> live Discord.

### The asks, verbatim (owner, 2026-09-23)

> "The channels page seems to think the Chat Category #Hole-in-the-wall isn't visible my
> members, it is fix that"

> "Same with gaming section"

> "Make sure the basement is still not referenced" *(relayed by the conductor mid-build)*

### Measured before the build (operator token, 2026-09-23 14:3x, v160)

`chat_visibility_role_id` IS the Member role (`1073741054563602532`), yet `GET /api/chat/channels`
marked `not_visible`: in *The Hole in the Wall* — `#landing`, `#qotw`, `#shows-and-movies`,
`#sports-ball`, `#music-recommendations`, `#recipes-and-food-pics` (6 of 13); in *Gaming* —
`#knuck-up`, `#rpg` (2 of 6); **65 of 94** overall. Whole categories hidden: The Basement 9/9,
Back to Black 2025 / 2026 / 2027 (11 / 17 / 12), ModMail 7/7, archive 4/4.

### Why (the hypothesis — unproven until the deployed page shows it)

`directory.everyone_sees` called `channel.permissions_for(<Member role>)`. For a `Role`,
discord.py 2.7 (`abc.py` `permissions_for`, the Role branch) applies the guild base, then
`@everyone`'s overwrite, then **that role's** overwrite only. A channel members reach through a
second role reads as private. Six of the eight line up with the interest roles the seeded
`interests` menu hands out — `#qotw` ↔ QOTW, `#shows-and-movies` ↔ Shows, `#sports-ball` ↔
Sports, `#music-recommendations` ↔ Musichead, `#recipes-and-food-pics` ↔ Foodie, `#rpg` ↔ RPGer.
⚠️ **Two do not:** `#landing` ("the first stop after the rules") and `#knuck-up` match no menu
role. The operator API cannot read overwrites, so what hides them is unknown — `#landing` may
deny the Member role on purpose (members graduate out of it). If the deployed page still reads
them *left out — members cannot see it*, **Tell the bot anyway** is staff's answer, not a further
code change.

### The rule (`directory.reach_in` — one helper, every reader)

In order, first match wins:

| # | Test | Answer |
|---|---|---|
| 1 | In a category on `chat_ignore_categories`, or the `modmail_category_id` category | hidden, `ignored_category` |
| 2 | A staff override is stored for the channel | shown → visible via `override`; hidden → `hidden_by_staff` |
| 3 | In a category whose name contains *archive* | hidden, `archive` |
| 4 | The `chat_visibility_role_id` role can read it | visible via `member` |
| 5 | Any **self-assignable** role can read it — `role_menu_options` of every non-`staff`-mode menu of this guild, resolved through `guild.get_role` | visible via `role:<name>` |
| 6 | otherwise | hidden, `not_visible` |

Readers: `open_channels` → the directory block and `channel_names` (the reply guard's
vocabulary); `knowledge.server_sections` (the daily ingest); the Channels page rows. No second
implementation. The self-assignable set and the overrides are read by `channel_reach.refresh` at
each ingest tick, each LLM reply, each page read and after each staff move, and kept per guild
for the sync readers; nothing read yet is the plain member rule (the pre-branch behaviour, never
wider).

`rolegrants` hands out no role of its own: every grant comes from a menu (`menu` / `approval`) or
from staff (`staff` / `manual`), so the menu options are the whole self-assignable set.

### Staff final say — a per-channel override

Table `channel_reach(guild_id, channel_id, shown, set_by, set_at)`, schema **56 → 57**,
additive. `PUT /api/chat/channels/{id}/reach {shown: true|false}` and
`DELETE /api/chat/channels/{id}/reach` (back to the rule), staff `writer` gate, refusals in words
(404 not a text channel, 409 `ignored_category`, 422 `reach_unclear`). GET rows gain
`reach {visible, via, override}` and keep `shown` / `hidden_because`; the move answers also carry
`counts`. Kinds `chat.channel_reach_set` / `chat.channel_reach_cleared` (ROUTINE, feature `chat`).

The page: the badge reads *told about it*, *told about it — members reach it through the Sports
role*, *shown by staff*, *left out by staff*, *left out — members cannot see it*, *left out — in
an ignored category*, *left out — archive*; one Reach button per card — **Tell the bot anyway**
(hidden by the rule), **Hide from the bot** (visible by the rule), **Back to the rule**
(overridden) — and none on an ignored-category card, which says to change the list instead. The
head gains *Told about N of M channel(s)*; it, the card and *What the bot sees* repaint in place.

### Decisions

1. ✅ **DECIDED — the ignored-category list and the ticket category beat BOTH the opt-in-role
   rule and a staff override.** Staff chose those on purpose, and the list is where they change
   it (the Settings page). An override on such a channel is **refused in words** (409), never
   stored silently. **The ignore list is the guard for The Basement** — the category named
   *The Basement* (9 text channels, all hidden at v160) must never reach the directory, the
   knowledge ingest or a chat answer. The conductor is adding its category id to
   `chat_ignore_categories` on the live site (2026-09-23); without that entry, The Basement's
   safety would rest only on no Member or self-assignable role reading it. Guarded by
   `tests/test_directory.py::test_the_basement_is_never_referenced_even_when_only_an_opt_in_role_reads_it`
   and `tests/test_channel_reach.py::test_the_basement_cannot_be_shown_by_staff_and_the_refusal_says_why`.
2. ✅ **DECIDED — an override DOES beat the archive rule.** An archive is recognised by a word in
   the category name; without the override staff could only bring one archived channel back by
   renaming the whole category.
3. ✅ **DECIDED — a `staff`-mode menu's roles do not count** (Runner, Live Runner, Commentator):
   nobody gives those to themselves. Approval menus DO count — a member can ask.
4. **Each opt-in role is tested alone** with the same `permissions_for(role)` call, not combined
   with the Member role: the question is *could somebody who picked this role read it*.
5. **Five sentences, all keys** — `chat_channel_reach_shown`, `_hidden`, `_cleared`, `_nothing`,
   `_ignored` in `settings_store.CHANNEL_NOTE_WORDS`, a label each in `labels.js`, a mock row
   each, in the Channels page's words fold. The `chat` group goes **70 → 75** keys; it was already
   past the `/settings` key picker's 25 and reached through **Find a setting**, which is
   unchanged; no new namespace, so the 25-group select gains nothing. Registry **361 → 366**.
6. **The page's badge and button words are page constants**, like every other word on the
   Channels page — site text, not words the bot posts.
7. **`chat_visibility_role_id`'s help** now says opt-in roles count and staff can override on the
   Channels page (mock row mirrored).
8. ⚠️ **No Discord door for the override** (`/chat` ▸ Channel notes… is unchanged). Checklist
   item 33 asks for both doors on a per-item choice; the brief scoped this build to the site. A
   follow-up if the owner wants it.

### Verified (2026-09-23, branch `channel-visibility`)

- `tests/test_directory.py` (33): Member reads it → via member; only an opt-in role reads it →
  via that role; a role nobody can pick opens nothing; a vanished role is skipped; no role →
  hidden; an override wins both ways and beats archive; The Basement and the ticket category beat
  an opt-in role and an override; the sync readers see the last refresh.
- `tests/test_channel_reach.py` (8): store / replace / clear; the self-assignable set is this
  guild's non-staff menu roles; refresh and its fallback; both moves, idempotence, log rows; the
  Basement refusal; the missing channel.
- `tests/storage/test_db.py` (56 → 57 additive), `tests/api/tools/test_chat.py` (row shape, the
  role via, both moves over HTTP, 409 / 422 / 404, the staff gate), `tests/test_knowledge.py`
  (the ingest reads by the same rule), `tests/test_logkinds.py`, the key-count mirrors,
  `tests/api/test_contract.py` (the two moves).
- The page against the mock in headless Chrome (CDP, 390 px wide, no horizontal scroll): 102
  rows, *Told about 93 of 102*; `#landing` *shown by staff* with **Back to the rule**;
  `#free-nitro-here` *left out by staff*; `#sports-ball` / `#rpg` *told about it — members reach
  it through the Sports / RPGer role*; **Hide from the bot** on `#general` → *left out by staff*,
  the sentence on its card, *Told about 92*, `#general` gone from *What the bot sees*; **Back to
  the rule** → 93 again and back in the block. No console errors.

### NOT verified

- ⚠️ **The opt-in-role hypothesis is unproven** until the deployed Channels page shows
  `#qotw`, `#shows-and-movies`, `#sports-ball`, `#music-recommendations`,
  `#recipes-and-food-pics` and `#rpg` as *told about it — members reach it through the … role*.
  Nothing here read a live overwrite.
- `#landing` and `#knuck-up` — no explanation; see *Why*.
- That the live role menus still carry those role ids (the ids were read from the seed in the
  code, not from the live table).
- No live Discord, no live database, no real staff move, no Discord-side door.
