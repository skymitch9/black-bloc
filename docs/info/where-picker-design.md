# The "Where?" picker — a real place on `/event` Propose, like Discord's own create-event dialog

> **Audience:** whoever maintains the events form. **Status:** TRACKED, 🔨 **BUILT** on branch
> `where-picker` off `main` at `a47e43a`, worktree `C:/lcw/bb-where-picker` — ⚠️ **NOT merged, NOT
> deployed, and NOTHING here has met Discord**: no test can click a Discord button
> ([`../access/testing.md`](../access/testing.md)), `python -m black_bloc` was NOT booted (a worktree
> holds no token), and TEST_MODE deliberately makes no scheduled event at all, so the kind mapping in
> §2 is proven by TESTS ONLY. What IS measured: the suite (**5395 → 5444**, forward and `BB_REVERSE=1`),
> `ruff check black_bloc tests`, and `node site/mock/check.mjs`
> (*ok - 17 pages, 150 routes, 14 core settings, all keys present*). The owner's by-eye rows are
> **329–335** in [`../access/sweeps.md`](../access/sweeps.md). Every departure from what is written
> below is in the **`## Deviations`** foot. Last verified (the header: 2026-09-10 17:30, measured on
> the branch; the body: as at the design) — what existed before the build was read in
> `black_bloc/events.py` (`build_card`, `create_event`, `EventFields`/`checked_fields`,
> `EventDraft`/`draft_lines`, `update_event`, `create_scheduled_event`), `cogs/community/events.py`
> (`build_draft`, `EventTextModal`, the staff `EditModal`), `storage/db.py` (`events` table, schema
> **33**), `api/tools/events.py`, `site/public/assets/page-events.js`, and `site/public/assets/api.js`
> (`/api/ref/channels` is already cached client-side). Sibling: [`when-picker-design.md`](when-picker-design.md)
> — same panel, same rules, `WherePanel` is `ZonePanel`'s twin.

## 1. What the owner asked (2026-09-10 16:11, verbatim)

> "We also need to add the where section like a real discord event for text channel or voice
> channel or other if they want to use a twitch link or something"

Today **Where** is one free-text box (`Where, or a link`, 100 chars) on the Title & details
modal, and every approved event becomes a Discord scheduled event of the **external** kind with
that text as its location (`create_scheduled_event`, `LOCATION_FALLBACK = "Ask in the server"`
when blank). Discord's own dialog asks *where* first: a voice channel, a stage, or "somewhere
else" with a typed place. This build gives the draft the same three doors.

## 2. The three kinds

| `where_kind` | What the person picks | Scheduled event | Card / announcement **Where** line |
|---|---|---|---|
| `voice` | a voice or stage channel | `entity_type=voice` (or `stage_instance` for a stage channel), `channel=<that channel>`, **no `location`** — members get Discord's Join button | the channel mention `<#id>` |
| `text` | a text channel | Discord has no text-channel event kind, so **external**, `location="#name"` (plain text — mentions do not render inside a scheduled event's location) | the channel mention `<#id>` |
| `other` | a typed place or link (a Twitch URL, "the Discord stage", …) | external, `location=<the text>` — exactly today's behaviour | the text, clamped to `LOCATION_LIMIT` |
| *(unset)* | nothing yet | external, `location=LOCATION_FALLBACK` — exactly today's behaviour | `DRAFT_NOT_SET` on the draft; the card omits the field as it does now |

**Where is optional, as it is today.** A draft with no Where still submits (P-rule: the panel
says what is *still needed*, and Where is never needed). Nothing about "modals never refuse"
changes.

## 3. Storage — schema 33 → 34

`events` gains two columns, both nullable:

```
where_kind        TEXT      -- 'voice' | 'text' | 'other' | NULL
where_channel_id  INTEGER   -- the channel for voice/text, NULL for other
```

`location` keeps the typed text for `other` and stays NULL for the channel kinds — **one fact,
one home**: the channel's name is never copied into `location`, it is rendered from the id at
display time, so a rename shows the new name. Migration is `ALTER TABLE … ADD COLUMN` × 2 in
`storage/db.py`, `SCHEMA_VERSION = 34`, with the migration-test pair the file already keeps.

A `Where` value travels as one small frozen type through the pure half, so the four writers
(`create_event`, `update_event`, the API, the site) cannot disagree on its shape:

```python
class Where(NamedTuple):
    kind: str | None          # WHERE_VOICE | WHERE_TEXT | WHERE_OTHER | None
    channel_id: int | None
    text: str                 # the typed place for `other`, "" otherwise
```

`EventFields` gains `where: Where`; `checked_fields` takes `where=` (replacing `location=`) and
still clamps `where.text` to `LOCATION_LIMIT`. `read_where(row)` builds one from a row.

## 4. The panel — `WhereButton` → `WherePanel`

`build_draft` (`cogs/community/events.py`) has four select rows and one button row
(`Title & details`, `My time zone`, `Submit`, `Back`). **`Where` is a fifth button on that row**
(five is the row cap; it fits exactly). Its label carries the current pick when there is one
(`Where: #general`, `Where: 🔊 Raid Night`, `Where: twitch.tv/…` clamped to `BUTTON_LABEL_LIMIT`),
`Where` otherwise.

`WherePanel(Panel)` — `ZonePanel`'s twin in `black_bloc/when_picker.py` is NOT the home; this is
events-only, so it lives in `black_bloc/events.py` (pure parts) + `cogs/community/events.py`
(the View). It renders:

- row 0: a **`discord.ui.ChannelSelect`** with `channel_types=[voice, stage_voice, text]`,
  placeholder `A voice or text channel…`, `min_values=0, max_values=1`. ChannelSelect is
  Discord's own picker — no 25 cap, no option list to build. Picking a channel stores
  `Where(kind=voice|text by channel.type, channel_id=…, text="")` on the draft and returns to
  the draft panel (`rerender`). The default (pre-selected) value is the draft's channel when set.
- row 1: **`Other — type a place or link…`** button → `WhereModal`, one `TextInput` (`Where, or a
  link`, `max_length=LOCATION_LIMIT`, `required=False`, `default` = the current `other` text).
  Submitting stores `Where(kind=other, channel_id=None, text=<typed>)` — an empty box stores
  `Where(None, None, "")` (clears it). Same modal-never-refuses rule; the modal returns to the
  draft panel, not to the WherePanel.
- row 1: **`Clear`** (only when something is set) → `Where(None, None, "")`, back to the draft.
- row 1: **`Back`** — no change.

The **Title & details** modal (`EventTextModal`) **loses its `Where, or a link` box** — that
is now the WherePanel's job, and a modal with two homes for one fact is the drift this rule
exists to stop. (It had four boxes; it keeps three.)

The draft card line: `**Where** — <#id>` / the text / `DRAFT_NOT_SET`. `draft_lines` renders it
through one `where_line(where)` helper the card and the announcement share.

## 5. Everywhere else the fact is written or shown

| Surface | Today | After |
|---|---|---|
| review card `build_card` | `Where` field = text | `Where` field = `where_line(...)`; omitted when unset (as now) |
| public announcement | links the scheduled event | unchanged, plus the Where line if the announcement embed carries fields today (check; do not add a field the design of the announcement never had) |
| staff **Edit** on the review panel (`EditModal`, `cogs/community/events.py` ~1065) | `location` TextInput | the TextInput goes; Edit gains the same `Where` button → `WherePanel`, storing through `update_event(where=…)`. Staff final say: staff can set any of the three kinds or clear it |
| `create_scheduled_event` | always external | branches on `where.kind` per §2; the voice branch passes `channel=` and NO `location=`; a stage channel uses `EntityType.stage_instance`; a channel that no longer exists (`guild.get_channel` → None) falls back to external + `LOCATION_FALLBACK` and logs `event.where_channel_gone` (a new log kind in `logkinds.py`, one write one log row) |
| **website** `page-events.js` create + edit forms | `Where` text input | a three-way control: a `<select>` of channels from the cached `/api/ref/channels` filtered to voice/stage/text (grouped, with a leading `— somewhere else —` option) plus the existing text input shown only when that option is chosen. Payload: `where_kind`, `where_channel_id`, `location`. `api/tools/events.py` reads all three, validates the kind against the three constants and the channel against the guild, and answers the row with the three fields plus `where_label` (the channel's name, so the page does not need to resolve ids) |
| `api/tools/events.py` row shape (`row["location"]` today) | `location` | + `where_kind`, `where_channel_id`, `where_label` — `site/mock/server.mjs` and `contract.json` gain them so `check.mjs` still says `all keys present` |
| `/settings` | — | **checklist 33: nothing to decide** — there is no default to choose; the three kinds are the person's choice each time. Say so in the report rather than inventing a key |

## 6. Tests (mirror the package)

- `tests/test_events.py`: `Where` round-trips through `create_event`/`update_event`/`read_where`;
  `where_line` for all four cases; `checked_fields` clamps `other` text and refuses nothing new;
  `create_scheduled_event` kwargs per kind — voice passes `channel` and no `location`, stage
  passes `stage_instance`, text passes `#name`, other passes the text, unset passes
  `LOCATION_FALLBACK`, a gone channel falls back and logs `event.where_channel_gone`.
- `tests/cogs/community/test_events.py`: the fifth button renders; ChannelSelect pick stores the
  right kind by channel type and returns to the draft; `Other` modal stores/clears; `Clear` only
  renders when set; `EventTextModal` has three boxes; staff Edit path stores through
  `update_event`; the draft still submits with no Where.
- `tests/storage/test_db.py`: 33 → 34 migration adds both columns, idempotent.
- `tests/api/…events`: create/edit with each kind; an unknown kind or a channel not in the guild is
  refused with a sentence (never a bare status); the row answers `where_label`.
- `node site/mock/check.mjs` stays `ok - 17 pages, 150 routes, 14 core settings, all keys present`.

## 7. What does NOT change

`/raidtrain` (its lineup has its own channel setting); `when_picker.py`; the five When keys;
`LOCATION_LIMIT`; the announcement's shape beyond the Where line; TEST_MODE (no scheduled
event is made under the guard — the kind mapping is proven by tests only, and sweep rows for
the calendar side are owner-side after the lift).

## 8. Docs the build touches

`docs/access/sweeps.md` (new rows after 327: the Where button, a voice pick, a text pick, Other,
Clear, the website form, and one ⚠️ owner-side row for the Join button on a real voice event),
`docs/info/code-notes.md` (a by-NAME section at the foot, like the When picker's),
`docs/info/README.md` (this doc's row → BUILT), `docs/info/architecture.md` (schema 34, key
count unchanged), `docs/TODO.md` (status line on the 🆕 item only — the MOVE to DONE is the
conductor's, at landing).

## Deviations

- **D1 (build) There is no `EditModal`, so staff got a Where BUTTON on the review card instead.**
  §5's table points at "the staff **Edit** on the review panel (`EditModal`,
  `cogs/community/events.py` ~1065)" with a `location` TextInput. No such class exists anywhere in
  the repo — the only staff *edit* of an event's details is the website's `PUT /api/events/{id}`.
  What was built is the same behaviour on the surface staff actually have: a `CardWhereButton` on
  the review card (`build_card` in the cog), staff-only and only while the event is still in an open
  status, opening the same `WherePanel`. Staff can set any of the three kinds or clear it, which is
  what the row asked for.
- **D2 (build) That button writes through a new `events.set_where`, not through `update_event`.**
  §5 says "storing through `update_event(where=…)`". `update_event` rewrites title, description,
  start and end as well, and the card has no business re-writing a start it never showed — a row
  with an unreadable start would have had one invented for it. `set_where` writes the three columns
  Where owns and nothing else, beside `set_status` / `set_review` / `set_scheduled` /
  `set_announced`, which is the grammar this module already uses. The WEBSITE still goes through
  `update_event(where=…)` exactly as written, because there the whole row genuinely is being edited.
- **D3 (build) `create_scheduled_event` branches on the CHANNEL'S LIVE TYPE, not on `where.kind`.**
  §5 says "branches on `where.kind` per §2". A channel can be converted between text, voice and
  stage after an event is proposed, and Discord refuses `entity_type=voice` for a stage channel and
  either for a text one — so a stored kind that has gone out of date would produce a refused
  calendar entry rather than a wrong one. `scheduled_place` asks `guild.get_channel` what the
  channel is *now*: stage → `stage_instance` + `channel=`, voice → `voice` + `channel=`, anything
  else → external with `#name`. `where_kind` still lives on the row, for the website's dropdown and
  for rendering a row with no guild in hand.
- **D4 (build) `checked_where` CORRECTS a kind that disagrees with the channel, and refuses a
  channel an event cannot happen in.** §5 says the API "validates the kind against the three
  constants and the channel against the guild" — two checks. A payload naming a text channel as
  `voice` passes both and would still be wrong, so the channel's own type wins (same argument as
  D3) and the row is stored as `text`; a payload naming a CATEGORY or a forum passes both too, and
  that one is refused, in a sentence, because there is no kind to correct it to. Four refusals
  ship, not two: unknown kind, no channel picked, no such channel here, and not a place an event
  can happen.
- **D5 (build) The Title & details modal keeps TWO boxes, not three.** §4 says "It had four boxes;
  it keeps three." It had three — Title, What is it?, and `Where, or a link` — since the When
  picker landed, so removing one leaves two. Nothing else about the paragraph changed.
- **D6 (build) `build_card` takes `where: Where` in place of its `location: str` parameter.** §5
  only names the field's *value* (`Where` field = `where_line(...)`). Leaving the parameter as text
  would have meant every caller flattening a `Where` on the way in and the card losing the ability
  to render a mention — so the parameter changed shape with the fact. Same for
  `create_event`/`update_event`, which §3 does imply. `selftest_panels.send_events` passes
  `Where(WHERE_OTHER, None, SELFTEST_NOTE)`.
- **D7 (build) A fifth reader of `location` was found and fixed: `knowledge.py:event_section`.**
  §5's table lists four surfaces. The chat's knowledge sections also read `row["location"]` to say
  where an approved event is, and after this change that column is NULL for the two channel kinds —
  so "what's on?" would have silently dropped the Where clause. It now goes through the same
  `read_where`/`where_line`. `chat_data.py:event_place` was deliberately LEFT ALONE: it already
  prefers `card_channel_id` and only falls back to `location`, so its behaviour is unchanged by
  this build and changing it would move a different fact.
- **D8 (build) `BUTTON_LABEL_LIMIT` did not exist and was added.** The brief names it as an
  existing convention; nothing in the repo defined it. It is `80` in `black_bloc/events.py` —
  Discord's own cap on a button label — and `where_button_label` clamps to it.
- **D9 (build) Deselecting the channel picker clears the Where, the same as `Clear`.** §4 gives
  `min_values=0` but says only that picking a channel stores one. An empty selection had to mean
  something; anything other than "nowhere" would have left a control that silently does nothing.
- **D10 (build) The sweep rows are 329–335, not 328 onwards.** The raid-train calendar-name build
  took 328 on `main` the same afternoon, while this branch was in flight. The conductor renumbers
  at the merge either way; this is recorded so the gap is not read as a missing row.

## Follow-up — a channel AND a link together, the link appended to the description

> Written 2026-09-10 17:18 against `main` at `d5c0515` (v105 live). **Status: 🔨 BUILT** on branch
> `where-link` off `main` at `ebe0ead` (commits `08173b7`, `2cfbdbe`) — ⚠️ **NOT merged, NOT deployed, and
> NOTHING here has met Discord**: no test can click a Discord button, `python -m black_bloc` was NOT booted
> (a worktree holds no token), no browser rendered the events page, and TEST_MODE makes no scheduled event at
> all, so **the appended description is proven by TESTS ONLY**. What IS measured: the suite (**5453 → 5473**,
> forward and `BB_REVERSE=1`), `ruff check black_bloc tests`, and `node site/mock/check.mjs`
> (*ok - 17 pages, 150 routes, 14 core settings, all keys present*). Keys **197 → 198**, schema unchanged at
> **34**. The owner's by-eye rows are **336–337** in [`../access/sweeps.md`](../access/sweeps.md). Every
> departure from what is written below is in the **`## Follow-up deviations`** foot.

### What the owner asked (2026-09-10 17:12, verbatim)

> "We need an easy way to set a voice or text channel for an event with the same where box for Twitch
> or something as optional / We then can append the link in the description of the event"

v105 made Where an **either/or**: a channel, *or* a typed place. A raid streamed on Twitch and played
in a voice channel has to choose. The follow-up lets a draft hold **both**: the channel is *where it
happens*, the box is an optional **link or note** that rides along.

### The change, half by half

| Piece | v105 | After |
|---|---|---|
| `Where` type | `text` is only meaningful when `kind == other` | `text` is meaningful for **every** kind: the typed place for `other`, an optional link/note beside a channel for `voice`/`text`. Shape unchanged, `WHERE_UNSET` unchanged |
| storage | `location` NULL for channel kinds | `location` holds the text for **every** kind — **schema unchanged at 34**, no migration, no backfill. `read_where` returns `Where(kind, id, clamp(location))` for a channel row (today it drops the text) |
| `checked_where` | a channel kind discards `text` | a channel kind **keeps** `typed`; the four refusals unchanged; the three empty spellings still collapse to `WHERE_UNSET` |
| `where_line` | mention *or* text | `<#id> · <text>` when both, `<#id>` alone, or the text alone. `where_said` / `where_button_label` the same with words (`🔊 Raid Night · twitch.tv/…`), clamped as now |
| `WherePanel` | `Other — type a place or link…` opens the modal; picking a channel wipes the text | the modal button is always there, labelled **`Link or place (optional)…`** when a channel is set and `Other — type a place or link…` when none is; the ChannelSelect pick **keeps** the current text (`Where(kind, id, previous.text)`); submitting the modal with a channel set stores `Where(kind, id, typed)`, with none set stores `other`/unset as now; deselecting the channel keeps the text as `other` (`Where(other, None, text)`) — nobody loses what they typed; `Clear` still wipes everything; the panel's intro sentence says the box is optional beside a channel |
| the scheduled event | `scheduled_place` gives the channel kinds no `location`; the description is the row's | unchanged place; **the description gets the text appended** for channel kinds — `description + "\n\n" + text`, clamped to `DESCRIPTION_LIMIT` (the text wins if the description has to give — the link is the reason it is there). Gated on a new bool key **`events_where_link_in_description`** (events group, default **true**, checklist 33: the owner decided it in chat, so the Settings page and `/settings set-value` can undo it). For `other` nothing changes: the text is already the location |
| website `page-events.js` `whereControl` | the typed box is shown only for `— somewhere else —` | shown **always**; its hint reads `Optional beside a channel — a Twitch link, say.` when a channel is chosen, `Only used when it is somewhere else.` otherwise (`SOMEWHERE_ELSE` unchanged); the payload sends `location` for every kind; the row's `location` already comes back, so the editor pre-fills it |
| `api/tools/events.py` | — | nothing new: `checked_where` does it; `event_row` already answers `location` |
| `knowledge.py:event_where` | — | nothing new: `where_line` does it |
| the staff card button | — | nothing new: same panel |
| `/settings` + mock | — | the one key above in `settings_store.py` (`KEY_TYPES`, `KEY_HELP`, default resolver), `site/mock/server.mjs`, `labels.js`; keys **197 → 198** |

### Tests (mirror the package)

- `tests/test_events.py`: `read_where` keeps the text beside a channel; `where_line` / `where_said` for
  both-set; `checked_where` keeps `typed` for a channel kind; `scheduled_place` unchanged; the
  `create_scheduled_event` kwargs carry the appended description for a channel kind when the key is on,
  the bare description when it is off, and the bare description for `other`; the append clamps.
- `tests/cogs/community/test_events.py`: the modal button label flips with a channel set; a channel pick
  keeps the text; the modal with a channel set stores both; deselecting keeps the text as `other`;
  `Clear` wipes both.
- `tests/api/tools/test_events.py`: PUT with a channel and a `location` stores both and the row answers both.
- `tests/test_settings_store.py` + `labels.js` total guard: the new key.
- `node site/mock/check.mjs` stays `ok - 17 pages, 150 routes, 14 core settings, all keys present`.

### Docs the build touches

`docs/access/sweeps.md` (two rows after 335: a voice pick plus a link on the draft; the website editor
with both), `docs/info/code-notes.md` (a by-NAME `## Where follow-up` block under the Where section),
`docs/info/architecture.md` (keys 197 → 198), `docs/info/README.md` (this doc's row), `docs/TODO.md`
(status line on the 🆕 item only — the MOVE to DONE is the conductor's).

## Follow-up deviations

- **F1 (build) The modal's TITLE flips as well as the button's label.** The table above names only the
  button (`Link or place (optional)…`). "Somewhere else" over a box that is adding a Twitch link *beside*
  a chosen channel says the wrong thing, so `WHERE_LINK_MODAL_TITLE` (`A link or a note`) is set on the
  instance when a channel is set. The class-level `title=` stays `WHERE_MODAL_TITLE`, so every existing
  test that constructs the modal with no channel is unchanged.
- **F2 (build) The panel's intro GAINED a clause rather than being rewritten.** The table says the intro
  "says the box is optional beside a channel". One sentence was inserted into `WHERE_PANEL_INTRO`
  between the existing two; the **Other** sentence and the "leaving it empty is fine" sentence are the
  words they already were, because they are still true and a rewrite would have moved facts nobody asked
  to move.
- **F3 (build) `scheduled_place` really is unchanged, and that means a GONE channel now falls back to the
  typed link instead of `Ask in the server`.** Its last branch is `clamp(where.text) or
  LOCATION_FALLBACK`, and `where.text` was always `""` for a channel kind before this build. It no longer
  is. The same event's description carries the link too (the stored kind is still `voice`, so the append
  fires), so on that one path the link appears twice. Both were left as they fell rather than special-cased:
  a venue that has vanished is exactly when the link is the most useful thing on the calendar entry, and
  the duplication costs a reader nothing. `event.where_channel_gone` is still logged.
- **F4 (build) The `create_scheduled_event` kwargs tests live in `tests/cogs/community/test_events.py`,
  not `tests/test_events.py`.** The Tests list files them under the pure half's mirror. Making a scheduled
  event needs a bot, a guild, an approval and a store, which are that file's fixtures and where
  `test_the_calendar_entry_follows_the_kind_that_was_picked` already sits — a second copy of that rig in
  the pure file would be the thing that drifts. `described_with_where` itself, which is where the clamp and
  the gate actually live, IS tested in `tests/test_events.py` as written.
- **F5 (build) Two existing tests were re-pointed, because they pinned the behaviour this follow-up
  reverses.** `test_staff_can_set_any_kind_on_a_card_and_the_write_leaves_one_log_row` asserted
  `location is None` after a staff channel pick (it now keeps `the park` and the card reads
  `<#…> · the park`), and `test_an_empty_channel_pick_leaves_the_draft_with_nowhere` started from a typed
  place that deselecting now KEEPS — so it starts from a channel with no text instead, and the "keeps what
  was typed" case is its own new test. Neither was deleted.
- **F6 (build) `— nowhere in particular —` on the website now sends whatever is in the box, so it can
  land as `other`.** The table says "the payload sends `location` for every kind", and the panel's rule is
  that deselecting keeps the text (`Where(other, None, text)`). Doing anything else on the website would
  have made the two doors disagree about the same gesture. Emptying the box is how a person means
  *nothing at all* there, exactly as it is in the modal.
- **F7 (build) `where_button_label` clamps the PAIR, so a long link eats its own tail — and can eat the
  channel name's.** The table says "clamped as now", which for a button is `BUTTON_LABEL_LIMIT` (80) over
  the whole label. The channel is what the button is for, so the trim falling on the end (the link) is the
  right way round; a 100-character link beside a long channel name will show truncated. The card and the
  announcement are unaffected — `where_line` clamps only the text.
- **F8 (docs) Sweep row 334 was left alone and row 337 says it supersedes it.** 334 (a landed, LIVE row)
  ends "The typed box appears ONLY when `— somewhere else —` is chosen", which this build makes false.
  Rewriting a row the owner may already have walked would lose that history, so 337 carries the ⚠️ clause
  instead. If the conductor would rather 334 were corrected at the merge, that is a one-line edit.
