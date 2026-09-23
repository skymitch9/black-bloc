# The channel catalog — what each channel is for, in staff's words

> **Audience:** whoever touches the channel list the conversation models read, and the reviewer.
> **Status:** TRACKED · **BUILT, NOT MERGED** — branch `channel-catalog`, off `main` `8e4ca731`,
> worktree `C:/lcw/bb-channel-catalog`. Nothing deployed; schema 54 has never run against the
> live database. The draft descriptions for the live channels are in
> [`channel-catalog.md`](channel-catalog.md) and are **not** in the bot.
> **Last verified: 2026-09-23** — against the branch tip by `pytest -n 16` (7427 passed),
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

`hidden_because` is `ignored_category` (on `chat_ignore_categories`, or the modmail category),
`archive`, or `not_visible` (the `chat_visibility_role_id` view cannot read it) — the one test
`open_channels` applies, as `directory.why_hidden`.

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
- The drafts in [`channel-catalog.md`](channel-catalog.md) are the builder's guesses from names
  and categories; the owner approves or rewrites them.
