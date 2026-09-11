# The "Where?" picker — a real place on `/event` Propose, like Discord's own create-event dialog

> **Audience:** whoever maintains the events form. **Status:** TRACKED, ✅ **LIVE as v105** — branch
> `where-picker` off `main` at `a47e43a`, merge **`3205c0f`**, deployed **2026-09-10 17:09** Phoenix
> (`../deploys.log`); **schema 33 → 34** (`events.where_kind`, `events.where_channel_id`). The
> worktree `C:/lcw/bb-where-picker` and the branch have been removed. ⚠️ **NOTHING here has met
> Discord**: no test can click a Discord button
> ([`../access/testing.md`](../access/testing.md)), `python -m black_bloc` was NOT booted (a worktree
> holds no token), and TEST_MODE deliberately makes no scheduled event at all, so the kind mapping in
> §2 is proven by TESTS ONLY. What IS measured: the suite (**5395 → 5444**, forward and `BB_REVERSE=1`),
> `ruff check black_bloc tests`, and `node site/mock/check.mjs`
> (*ok - 17 pages, 150 routes, 14 core settings, all keys present*). The owner's by-eye rows are
> **329–335** in [`../access/sweeps.md`](../access/sweeps.md). Every departure from what is written
> below is in the **`## Deviations`** foot. **Last verified: 2026-09-11 08:50** (the header: the
> merge, the deploy and the follow-up status lines re-read against `../deploys.log` and `../DONE.md`
> on `main` at `f3ae743`; the body: as at the design, not re-measured this pass). ⚠️ **NOT checked
> this pass:** anything in Discord or a browser, and none of §1–§8 or the four follow-up bodies were
> re-measured — only their STATUS lines were, which is what was stale. Before that (the header:
> 2026-09-10 17:30, measured on
> the branch; the body: as at the design) — what existed before the build was read in
> `black_bloc/events.py` (`build_card`, `create_event`, `EventFields`/`checked_fields`,
> `EventDraft`/`draft_lines`, `update_event`, `create_scheduled_event`), `cogs/community/events.py`
> (`build_draft`, `EventTextModal`, the staff `EditModal`), `storage/db.py` (`events` table, schema
> **33**), `api/tools/events.py`, `site/public/assets/page-events.js`, and `site/public/assets/api.js`
> (`/api/ref/channels` is already cached client-side). ⚠️ **The FOUR follow-up sections below this one are each their own
> build with their own status line and their own deviations foot** — §1–§8 and the `## Deviations`
> foot describe the FIRST build only, and the header above is that build's. **All four are LIVE:**
> follow-up 1 as **v106** (merge `6c10b9d`, 17:41), follow-ups 2+3 as **v107** (merge `ac43a20`,
> 23:41), follow-up 4 as **v108** (merge `73e2e44`, 2026-09-11 00:37). The newest is
> **`## Follow-up 4`**, built 2026-09-11 00:21 on branch `where-smart` off `main` at `9fc3a33`
> — ⚠️ never seen in Discord; measured there: suite **5502 → 5546**
> forward and `BB_REVERSE=1`, `ruff` clean, `node site/mock/check.mjs` *ok - 17 pages, 150 routes,
> 14 core settings, all keys present*, registry keys **199 → 202**, schema unchanged at **34**.
> ⚠️ NOT re-verified for follow-up 4: everything in §1–§8 and in follow-ups 1–3, which were read
> but not re-measured. Sibling: [`when-picker-design.md`](when-picker-design.md)
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

> The FIRST build's foot. **Status: ✅ LIVE v105 — merged `3205c0f`, deployed 2026-09-10 17:09.**
> ⚠️ Nothing here has met Discord.

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

> Written 2026-09-10 17:18 against `main` at `d5c0515` (v105 live). **Status: ✅ LIVE v106**
> (2026-09-10 17:41, merge `6c10b9d` of `where-link`; built off `main` at `ebe0ead`, commits
> `08173b7`, `2cfbdbe`) — ⚠️ **NOTHING here has met
> Discord**: no test can click a Discord button, `python -m black_bloc` was NOT booted
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

> Follow-up 1's foot. **Status: ✅ LIVE v106 — merged `6c10b9d`, deployed 2026-09-10 17:41.**
> ⚠️ Nothing here has met Discord.

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

## Follow-up 2 — a typed link LOOKS like a link (owner, 2026-09-10 ~23:09, verbatim: "Is there a way to make them look like links in the events slash" → "Do A + B")

> **Status: ✅ LIVE v107** (2026-09-10 23:41, merge `ac43a20`; built on branch `where-links` off `main` at `8adbc75`, commit `a8a1210`; review `2386050` dropped the draft's button) — ⚠️ **never seen in Discord**. Measurements and every departure are the **`## Follow-up 2+3 deviations`** foot.

Today a typed `https://twitch.tv/mitchland` beside a channel renders as raw text in the draft (an embed
description, `draft_lines`) and in the card's Where field (`card_for`, an embed field). Discord auto-links a
bare URL in both places, but shows the whole scheme-and-all string, and nothing on the card is a real
link control.

**A — masked link in the text.** `black_bloc/events.py` gains:

- `where_link(text) -> str | None` — the URL if the typed text IS one link and nothing else: after `strip()`,
  a single token (no whitespace) that starts with `http://` or `https://`, or with `www.` (then `https://`
  is put in front for the href). Anything else (a place, a sentence, two links) → `None`. No other
  guessing — `the.bar at 8` is not a link.
- `where_shown(text) -> str` — the masked form for embeds: `[twitch.tv/mitchland](https://twitch.tv/mitchland)`.
  The label is the href without its scheme and without a trailing `/`, clamped to `LOCATION_LIMIT`; a
  `]` or `)` in the label is dropped so the markdown cannot break. Non-links come back unchanged.
- `where_line(where, *, linked=True)` — `linked=True` renders the text through `where_shown`;
  `linked=False` is the plain form for `knowledge.event_where` (the chat LLM reads words, not markdown)
  and any other non-embed reader. The draft (`draft_lines`) and the card (`card_for`) use the default.
- `where_said` (button labels) is untouched — a label cannot carry a link. The scheduled event's
  description (`described_with_where`) keeps the BARE url: Discord auto-links it there and masked links in
  event descriptions are not reliable.

**B — an "Open link" button on the card.** `build_card` adds
`discord.ui.Button(style=discord.ButtonStyle.link, label=WHERE_OPEN_LINK_BUTTON, url=where_link(where.text), row=1)`
— the `SITE_BUTTON` / `REVIEW_ROOM_BUTTON` pattern — for EVERY viewer (not staff-only), whenever
`where_link(read_where(row).text)` is not `None`. `WHERE_OPEN_LINK_BUTTON = "Open link"`. If row 1 is full
(five items) the button goes on the next row with room; if none has room it is skipped and noted as a
deviation. The draft panel gets the same button on its Where row only if that row has a free slot —
otherwise A alone covers the draft.

Tests: `tests/test_events.py` — `where_link` (https, http, www, a place, two tokens, empty), `where_shown`
(scheme stripped, trailing slash stripped, a bracket dropped, clamped), `where_line` both `linked` values,
the card's Where field carries the masked form, `described_with_where` still bare;
`tests/cogs/community/test_events.py` — the card view has a link-style item with the url when the text
is a link and none when it is a place; `tests/test_knowledge.py` — `event_where` is plain.

Nothing to decide, so no settings key (checklist 33 satisfied by absence: a link that looks like a link is
not a policy).

## Follow-up 3 — test rooms go after five minutes, and denied rooms count from the decision (owner, 2026-09-10 ~23:09, verbatim: "For test ones let's delete them after 5 minutes"; earlier "for a denied event do we have a timer before it's auto deleted?")

> **Status: ✅ LIVE v107** (2026-09-10 23:41, merge `ac43a20`; built on branch `where-links` off `main` at `8adbc75`, commit `0e765d5`) — ⚠️ **never seen in Discord**. Measurements and every departure are the **`## Follow-up 2+3 deviations`** foot.

Measured 23:05: `EventsCog._sweep_finished` deletes a DONE / DENIED / CANCELLED event's review channel once
`now - ends_at >= events_channel_retention_days` (live 7). Two things are wrong with that for the owner:

1. It anchors on the event's scheduled END even when the event was denied or called off — a denied
   proposal for next month keeps its room until next month plus seven days. **Fix, both modes:** the
   anchor is `decided_at` for DENIED and CANCELLED (falling back to `ends_at` when `decided_at` is NULL,
   then to `created_at`), and `ends_at` for DONE. Helper `swept_anchor(row) -> datetime | None` in
   `black_bloc/events.py`, tested for all three statuses and the NULL fallbacks.
2. Under TEST_MODE every event is a test one, and seven days of test rooms is clutter. **New key**
   `events_test_retention_minutes` (int, events group, default **5**, bounds 1–1440, help: "minutes a
   finished or refused event's review room is kept while the bot is in test mode; the real retention
   is `events_channel_retention_days`") — registered in `KEY_TYPES`, `KEY_HELP`, the default resolver,
   `NUMBER_BOUNDS` / the min-max tables with the two refusal sentences, the mock `server.mjs`, `labels.js`,
   and `contract.json` if keys are listed there (keys 198 → 199). `_sweep_finished` reads
   `guard is not None and guard.enabled` (whatever `black_bloc/guard.py` exposes as "test mode is on" —
   use the existing predicate, do not add a second) and, when it is, uses
   `timedelta(minutes=events_test_retention_minutes)` instead of the days. The `event.channel_deleted`
   log row carries `kept_minutes` in that case instead of `kept_days`. The `would_delete_channel` branch
   stays exactly as it is — the guard still decides WHERE the bot may delete; this only decides WHEN.
   The reconcile loop runs every `RECONCILE_MINUTES = 5`, so "after 5 minutes" lands between 5 and 10 —
   say so in the key's help and in the owner guide line.

Tests: `tests/cogs/community/test_events.py` — a denied row is swept `decided_at + N`, not `ends_at + N`;
a done row still uses `ends_at`; with the guard on, the minutes key is what counts and `kept_minutes` is
logged; with it off, the days key; `tests/test_settings_store.py` — the new key's type, default, bounds
and both refusal sentences. Docs: `docs/access/OWNER_GUIDE.md` events section (one line), sweep rows.

Two commits on the build branch: Follow-up 2 first, Follow-up 3 second, each with its tests green.

## Follow-up 2+3 deviations

> Written at the build, 2026-09-10 ~23:30, on branch `where-links` off `main` at `8adbc75`
> (commits `a8a1210`, `0e765d5`; G4 reversed at review, `2386050`). **Status: ✅ LIVE v107** 23:41, merge `ac43a20` — ⚠️ **NOTHING
> here has met Discord**: no test can click a Discord button, `python -m black_bloc` was NOT booted
> (a worktree holds no token), no browser rendered the Settings page, and TEST_MODE makes no
> scheduled event at all. What IS measured: the suite (**5473 → 5503**, forward and `BB_REVERSE=1`),
> `ruff check black_bloc tests`, and `node site/mock/check.mjs` (*ok - 17 pages, 150 routes, 14 core
> settings, all keys present*). Keys **198 → 199**, schema unchanged at **34**. The owner's by-eye
> rows are **338–342** in [`../access/sweeps.md`](../access/sweeps.md).

- **G1 (build) `where_link` refuses a bare scheme.** § Follow-up 2 says a single token "that starts
  with `http://` or `https://`". `https://` on its own passes that test and would mask to
  `[](https://)` — an empty label, which renders as nothing clickable. Something has to follow the
  scheme (and `www.`) for it to count as a link.
- **G2 (build) `where_shown` returns the BARE text when the href itself contains a `)`.** The spec
  drops `]` and `)` from the LABEL only. The label is safe to edit; the href is not, because editing
  it changes where the reader lands. Discord's parser ends a link destination at the first `)`, so a
  URL carrying one (a Wikipedia article, say) would render as half a link plus loose text. Bailing
  out whole gives Discord's own auto-linking instead, which is correct and visibly a link.
- **G3 (build) The "Open link" button is added LAST in both builders, so its row is counted after
  everything else.** § Follow-up 2 B says `row=1` with a fall-through to the next row with room.
  `add_open_link` counts `view.children` to decide, which only works once the rest of the view
  exists — hence the call at the foot of `build_card` and `build_draft` rather than beside the Where
  button. The card tries rows 1, 2, 3, 4 in that order; in practice row 1 always has room (Where,
  Back and the review-room link make three of five).
- **G4 (build → REVERSED at review) The DRAFT gets no Open link button at all.** § Follow-up 2 B said the draft gets it "only if that row has a free slot". The button row holds Title & details · Where · Time zone · Back, and **Submit** joins them the moment the draft passes — five, Discord's cap. The build put the button there while something was still missing and let Submit displace it; the conductor removed the draft call before the merge (`build_draft` no longer calls `add_open_link`; one test replaces two) because a control that appears only while the draft is incomplete and vanishes when it is ready is worse than no control. The masked Where line carries the link on the draft; the card keeps the button.
- **G5 (build) `ROW_ITEM_CAP = 5` was added to `black_bloc/events.py`.** Nothing in the repo named
  Discord's per-row item cap; `SELECT_CAP` is the 25-option one, which is a different number for a
  different thing. It sits beside `BUTTON_LABEL_LIMIT`, which was added by the same argument in the
  first Where build (D8).
- **G6 (build) `where_line` gained a `linked=` FLAG rather than a second function.** The Where
  section of `code-notes.md` argues that `where_line` and `where_said` are deliberately two
  functions. `linked` is not that case: it does not change what is said, only whether the same text
  wears markdown, and the plain caller wants the identical channel-and-join logic. A second function
  would have been that logic copied.
- **G7 (build) `swept_anchor` falls back through THREE columns, and a row with none readable is
  left standing.** § Follow-up 3 gives `decided_at` → `ends_at` → `created_at`, which is what was
  built. What it does not say is what happens when all three are unreadable: the helper returns
  `None` and `_sweep_finished` skips the row, which is exactly what it already did for an
  unparseable `ends_at`. Deleting a room because its timestamps are broken would be the one
  irreversible reading of a bad row.
- **G8 (build) "Test mode is on" is `guard is not None`, with no `enabled` to read.** § Follow-up 3
  writes `guard is not None and guard.enabled`, hedged with "whatever `guard.py` exposes". It
  exposes no such attribute: `TestModeGuard` is installed or it is not, and `events_category`,
  `card_channel` and `rename_channel` all ask exactly `getattr(bot, "guard", None)`. The brief's own
  instruction — use the existing predicate, do not add a second — is what was followed.
- **G9 (build) The channel-delete REASON flips with the window, not just the log row.**
  § Follow-up 3 names only `kept_minutes` in the `event.channel_deleted` details. The reason string
  handed to `channel.delete` said "kept N day(s)", which would have been a false sentence in
  Discord's own audit log every time test mode swept a room. `SWEEP_KEPT_DAYS` /
  `SWEEP_KEPT_MINUTES` live in `events.py` beside the statuses, because the cog is not the home of
  any fact.
- **G10 (docs) The key's min/max reasons say "every five minutes" in words rather than importing
  `RECONCILE_MINUTES`.** `settings_store.py` importing from a cog would be a new arrow between
  layers for one number in one sentence. The number is stated in prose in three places (the key's
  help, its floor refusal, and the owner-guide line) and owned in code by
  `cogs/community/events.py:RECONCILE_MINUTES`.
- **G11 (docs) Sweep rows are 338–342 — five, where § Follow-up 3 implies fewer.** One row per thing
  the owner has to see by eye: the masked link and the card button (338), the draft row's cap (339),
  a place that is not a link (340), the denied room's new anchor (341, the one that needs ten
  minutes of waiting), and the new key with both refusals (342).

## Follow-up 4 — a SHORTHAND becomes a link, and the link is checked first (owner, 2026-09-10 23:5x, verbatim: "Can we do some smart work to make it a link / Like twitch.tv/skyaiva or ttv/skyaiva or yt skyaiva / We go and make those into links / Maybe even curl them first?")

> **Status: ✅ LIVE v108 (2026-09-11 00:37, merge `73e2e44` of `where-smart`)** (commits `6e81d83` part A,
> `a876540` part B, `af63b63` docs, `1d9a515` review fix) — ⚠️ **never seen in Discord.**
> Measurements and every departure are the **`## Follow-up 4 deviations`** foot.

Follow-up 2 only recognises `https://…`, `http://…` and `www.…` (`where_link`). The owner types
`twitch.tv/skyaiva`, `ttv/skyaiva` or `yt skyaiva` and wants each to become the link it obviously means —
and, since the bot is going to hand people a link, to have tried opening it once.

**A — three more shapes are links.** All three are the WHOLE typed text after `strip()` (a sentence with a
link inside it is still not a link — `the.bar at 8` stays words). Case-insensitive throughout.

1. **A bare host, with a path or not** — one token, `^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}(/\S*)?$`
   (`twitch.tv/skyaiva`, `youtube.com/@skyaiva`, `discord.gg/baf`, `kick.com`). The TLD must be letters
   and at least two of them, so `8.30` and `e.g` are not links. `https://` goes in front for the href.
   This rule lives in **`where_link` itself**, so rows stored before this build render as links too.
2. **An alias and a handle** — `ttv/skyaiva`, `ttv skyaiva`, `yt @skyaiva`: exactly two parts split on
   the FIRST `/` or run of whitespace; the first part is an alias in the table below, the second a handle
   matching `^@?[a-z0-9._-]{1,64}$` (a leading `@` is stripped before the template is filled, so a
   template that carries its own `@` never renders `@@`). Anything else (three parts, a handle with a
   space, an unknown alias) is words.
3. The table is a **settings key**, so it is staff-editable both ways (checklist 33):
   `events_where_link_aliases` — type `text`, events group, the `timezone_choices` shape (comma-separated
   entries, a checker that drops what it cannot read and refuses in words when nothing is left). Each
   entry is `alias=https://host/path/{handle}`; the checker keeps an entry only when the alias is
   `^[a-z0-9]{1,16}$`, the template starts with `https://` and contains `{handle}` exactly once, and the
   first spelling of an alias wins. Default:
   `ttv=https://twitch.tv/{handle}, twitch=https://twitch.tv/{handle}, yt=https://youtube.com/@{handle},
   youtube=https://youtube.com/@{handle}, kick=https://kick.com/{handle}, tiktok=https://tiktok.com/@{handle},
   ig=https://instagram.com/{handle}, instagram=https://instagram.com/{handle}, x=https://x.com/{handle},
   twitter=https://x.com/{handle}, discord=https://discord.gg/{handle}`.
   Constants `WHERE_ALIASES_KEY`, `WHERE_ALIASES` (the default string), `WHERE_ALIAS_MAX = 32` entries.

Where the alias rule runs is **at entry, once**: a new `where_typed(text, aliases) -> str` in
`black_bloc/events.py` returns the href when the text is shape 2, else the text unchanged. It is called in
`WhereModal.on_submit` (both the beside-a-channel and the somewhere-else branches) with the live table, and
in `checked_where` (the website's door, which gains an `aliases` keyword defaulting to `WHERE_ALIASES`).
So the STORED `location` is the full `https://twitch.tv/skyaiva`, and everything Follow-up 2 built —
the masked line, the card's **Open link** button, the description — needs no second table. Shape 1 is
render-time in `where_link`, and `described_with_where` appends `where_link(text) or text` so a bare
host typed before this build still reaches the scheduled event's description with its scheme.
The draft shows the normalised form (the masked `twitch.tv/skyaiva`), which is the point.

**B — the link is tried before it is kept.** New module `black_bloc/linkcheck.py` (tests in
`tests/test_linkcheck.py`), nothing Discord in it:

- `async def link_answers(url, *, seconds, fetch=None) -> str` — one `GET` with `allow_redirects=True`,
  a browser-shaped `User-Agent` (a bare aiohttp UA gets WAF-blocked — global gotcha), no body read,
  bounded by `aiohttp.ClientTimeout(total=seconds)`; `fetch` is the injectable request (the `groq.py`
  `request or self._aiohttp_request` pattern) so tests never touch the network. Returns one of
  `LINK_OK` (any status that is not the two below — a 403 from Cloudflare means *reachable, refuses
  bots*, not missing), `LINK_MISSING` (404 / 410), `LINK_UNREACHABLE` (timeout, DNS, connection error,
  5xx). ⚠️ `twitch.tv` answers 200 for ANY channel name (it is a single-page app), so a wrong Twitch
  name passes; `youtube.com/@…` does 404 a wrong handle. Say so in the owner guide, not the UI.
- Two more settings keys, events group: `events_where_link_check` — enum `off` / `warn` / `refuse`,
  default **`warn`**; `events_where_link_check_seconds` — int, 1–3, default **2** (a modal must answer
  Discord inside three seconds, and the panel still has to render after the check).
- In `WhereModal.on_submit`, after `where_typed`: when the result is a link and the mode is not `off`,
  `await link_answers(...)`. `LINK_OK` → nothing. Otherwise **`warn`** keeps the link and puts a note on
  the draft — `EventDraft` gains `where_note: str = ""`, `draft_lines` appends it to the Where line as
  ` — ⚠️ {note}` (`WHERE_NOTE_MISSING = "that page answered 404 — check the name"`,
  `WHERE_NOTE_UNREACHABLE = "{host} did not answer within {seconds} s — the link is kept as typed"`);
  the note is cleared whenever Where is set again, and it never reaches the stored event (no schema
  change — the card and the description do not carry it; the proposer saw it when it mattered).
  **`refuse`** answers the modal in words through `AnswersErrors` (`WHERE_REFUSED_MISSING`,
  `WHERE_REFUSED_UNREACHABLE`, each naming the link and the fix) and leaves the draft as it was.
  The website's `checked_where` does NOT check (it is synchronous and its caller already answers in
  words); noted as a deliberate difference on the dashboard doc's Where line.
- `linkcheck` never runs against a non-link, and never under `pytest` — every test injects `fetch`.
  TEST_MODE is about Discord posting, not outbound HTTP, so the check runs live in test mode too.

**C — everywhere it shows.** `where_shown`'s label for a bare host is the host and path as typed
(`twitch.tv/skyaiva`); for an alias form it is the filled template's host and path
(`youtube.com/@skyaiva`). The knowledge line (`linked=False`) says the href in plain words.

**Tests (mirror the package).** `tests/test_events.py`: `where_link` for a bare host with / without a
path, a digits-only TLD, a one-letter TLD, a host inside a sentence; `where_typed` for `ttv/x`, `ttv x`,
`yt @x` (no `@@`), an unknown alias, three parts, a handle with a slash, an alias typed in capitals,
a custom table; `described_with_where` carries the scheme for a bare host; `checked_where` normalises.
`tests/test_settings_store.py`: the three keys with defaults and bounds, the aliases checker drops a
bad entry and refuses an empty result in words, the enum refuses an unknown mode in words.
`tests/test_linkcheck.py`: each verdict from an injected `fetch`, a timeout is `LINK_UNREACHABLE`, the
UA header is sent, the body is never read. `tests/cogs/community/test_events.py`: the modal with an
injected `fetch` — `warn` puts the note on the draft and keeps the link, `refuse` answers in words and
keeps the previous Where, `off` never calls `fetch`, a non-link never calls `fetch`, the note clears
when Where is set again.

**Mock / labels / contract.** The three keys go in `site/mock/server.mjs`, `site/public/assets/labels.js`
and `site/mock/contract.json` like `events_test_retention_minutes` did.

**Docs the build touches.** `access/OWNER_GUIDE.md` (one line: shorthand that becomes a link, the check
and its Twitch caveat), `access/sweeps.md` (rows 343+: `ttv/skyaiva` beside a channel renders
`twitch.tv/skyaiva`; `yt skyaiva` → `youtube.com/@skyaiva`; a bare `twitch.tv/skyaiva`; a typo'd
`youtube.com/@no-such-handle-xyz` shows the 404 note in `warn`; `refuse` answers in words; `off` is
silent; the aliases key edited on Settings; the old-row case), `info/code-notes.md` (keyed by NAME),
`info/architecture.md` (the new module), `info/README.md` row.

**What does NOT change.** Schema 34. `where_said`, `add_open_link`, the guard, the sweep,
`knowledge.event_where` (still `linked=False`). No new log kind — the check logs at `debug` only.


## Follow-up 4 deviations

> Written at the build, 2026-09-11 00:2x, on branch `where-smart` off `main` at `9fc3a33`
> (commits `6e81d83` part A, `a876540` part B, `af63b63` docs). **Status: ✅ LIVE v108 — 2026-09-11 00:37,
> merge `73e2e44`; the review probed the real link check (H16, H17).** ⚠️ **NOTHING here has met Discord**: no test can click a Discord button,
> `python -m black_bloc` was NOT booted (a worktree holds no token), no browser rendered the
> Settings page, TEST_MODE makes no scheduled event at all, and — new for this build — **no link was
> ever actually opened**: every test injects `fetch`, and `tests/conftest.py:no_test_ever_opens_a_link`
> turns a real GET into an `AssertionError`, so the aiohttp path in `linkcheck.py` is the one piece of
> this build that has never been executed at all. What IS measured: the suite (**5502 → 5546**,
> forward and `BB_REVERSE=1`, both green), `ruff check black_bloc tests` (clean), the JS asset parse
> the deploy script runs, and `node site/mock/check.mjs` (*ok - 17 pages, 150 routes, 14 core
> settings, all keys present*). Keys **199 → 202** by `len(KEY_TYPES)`; schema unchanged at **34**.
> The owner's by-eye rows are **343–350** in [`../access/sweeps.md`](../access/sweeps.md).

- **H1 (build) `fetch` is injected through a MODULE-LEVEL hook, `cogs/community/events.py:LINK_FETCH`,
  and the brief's choice is recorded here.** The brief offered a module hook or a cog attribute. The
  modal is built by Discord from a button callback — `WhereModal(self.view)` — so no test can reach
  its constructor to pass anything in, and the cog instance is not on the path either
  (`WhereModal.on_submit` has `interaction.client` and `self.previous`, not the cog). A module
  attribute is the smallest seam that both of those can see: `LINK_FETCH: Any = None` beside
  `CARD_LINK_ROWS`, handed straight to `link_answers(..., fetch=LINK_FETCH)`, which falls back to
  `linkcheck.aiohttp_status` when it is `None`. Tests set it with
  `monkeypatch.setattr(events_cog, "LINK_FETCH", fetch)` in an autouse `link_check` fixture.
- **H2 (build) A SECOND, suite-wide guard was added that the spec did not ask for:
  `tests/conftest.py:no_test_ever_opens_a_link`.** § Follow-up 4 B says "every test injects `fetch`",
  which is a rule prose cannot enforce — and it was already being broken before the fixture existed:
  the pre-existing cog test `test_other_types_a_place_and_an_empty_box_clears_it` types
  `twitch.tv/blackbloc`, which part A turns into a link, which the default `warn` mode then tried to
  open for real. The autouse fixture replaces `linkcheck.aiohttp_status` with one that raises, so a
  test that forgets to inject fails loudly instead of quietly reaching the internet. Mechanical guard
  over written advice, per the global rule.
- **H3 (build) `checked_where` normalises the ALIAS shape but leaves a bare host exactly as typed.**
  § Follow-up 4 A says shape 1 is "render-time in `where_link`" and shape 2 runs "at entry, once", so
  this follows the spec — but it is worth stating because the two doors then store different strings
  for what a person would call the same thing: `ttv/skyaiva` is stored as
  `https://twitch.tv/skyaiva`, while `twitch.tv/skyaiva` is stored verbatim and only grows its scheme
  when it is drawn. That is deliberate: rewriting stored text would need a migration to be
  consistent, and shape 1 exists precisely so old rows need none.
- **H4 (build) The three constants live in `settings_store.py`, not `events.py`, and there are more
  of them than the spec names.** § Follow-up 4 A asks for `WHERE_ALIASES_KEY`, `WHERE_ALIASES` and
  `WHERE_ALIAS_MAX = 32`. They sit in `settings_store.py` beside `EVENTS_SCHEDULED_NAME_KEY` /
  `EVENTS_SCHEDULED_NAME_TEMPLATE`, which is the existing pattern for a key whose default is a
  string, and `events.py` imports them (the arrow already exists; the reverse one does not). The
  build also added `HANDLE_PLACEHOLDER`, `WHERE_CHECK_KEY`, `WHERE_CHECK_OFF` / `WHERE_CHECK_WARN` /
  `WHERE_CHECK_REFUSE` / `WHERE_CHECK_MODES` / `WHERE_CHECK_MODE`, `WHERE_CHECK_SECONDS_KEY`,
  `WHERE_CHECK_SECONDS`, `WHERE_CHECK_MIN_SECONDS` and `WHERE_CHECK_MAX_SECONDS` — the spec named the
  values but not the constants, and the cog comparing `mode != "off"` against a bare string is
  exactly what the registry exists to stop.
- **H5 (build) The alias TABLE PARSER is `settings_store.where_alias_table`, shared by the checker
  and by `where_typed`.** § Follow-up 4 A describes the checker only. Writing the parse twice — once
  to validate, once to use — is the near-duplicate the review checklist warns about, and the two
  copies would have disagreed the first time a rule changed. `where_alias_table` is lenient (drop
  what cannot be read, first spelling of an alias wins, stop at 32); `checked_aliases` is the thin
  half that calls it and raises `NO_LINK_ALIAS` when nothing survives.
- **H6 (build) The template is rejected unless its placeholders are EXACTLY `["handle"]`, which is
  stricter than "contains `{handle}` exactly once".** A template like
  `x=https://x.com/{who}/{handle}` contains `{handle}` exactly once and would pass the spec's test —
  then raise `KeyError` inside `.format` at the moment a person typed `x/someone`, turning a settings
  value into a crash at use time (checklist 17). Comparing the whole placeholder list rejects strays
  and duplicates together.
- **H7 (build) `where_typed` asks `where_link` FIRST, before it tries to split.** The spec does not
  say in what order the two shapes are tried. Asking `where_link` first makes "a thing that is
  already a link is never rewritten" true by construction rather than by accident of the alias table
  not containing `twitch.tv`.
- **H8 (build) The draft note is carried on the WherePanel and copied onto the draft by
  `take_draft_where`, which is what makes it clear itself.** § Follow-up 4 B says `EventDraft` gains
  `where_note` and that "the note is cleared whenever Where is set again", without saying how the
  modal — which holds a `WherePanel`, not an `EventDraft` — reaches it. `WhereModal.on_submit` writes
  `self.previous.where_note`; `WherePanel.__init__` sets it to `""`; `take_draft_where` copies it
  unconditionally. Every other Where move (the channel select, **Clear**) goes through the same
  copy with the panel's empty default, so clearing is automatic rather than remembered.
- **H9 (build) `where_note` and `where_refused` are functions in `events.py`, not strings formatted
  in the cog.** § Follow-up 4 B names four constants. The cog is not the home of any fact (the same
  argument as G9 in the previous build), so the verdict → sentence mapping lives beside the
  constants, and the cog reads `where_note(verdict, url, seconds)`.
- **H10 (build) The refusal sentences are longer than the spec's sketch, and name the SETTING.** The
  brief requires "what happened, what it needs, and how to get it". Each refusal says the link
  answered 404 (or did not answer in N seconds), that nothing was saved and the old place was kept,
  and that a Lead can set `events_where_link_check` to warn. The `warn` note is the short form,
  because a draft line has no room for three clauses.
- **H11 (build) `linkcheck.aiohttp_status` builds and closes a session per call, unlike
  `groq.py`.** `groq.py` keeps a session because it talks to one host continuously. This makes at
  most one request per modal submission, so a cached session would be a lifecycle to own — and a
  loop-bound object to worry about — in a module that otherwise has no state at all.
- **H12 (build) `link_answers("")` is `LINK_UNREACHABLE` and never calls `fetch`.** The spec does not
  say what an empty url does. It cannot happen from the modal (the check only runs when `where_link`
  returned an href), but returning `LINK_OK` for nothing would be the wrong default for the one case
  where a caller is confused.
- **H13 (build) Eight pre-existing assertions changed, because `twitch.tv/bb` is now a link.** Three
  tests in `tests/test_events.py` and three in `tests/cogs/community/test_events.py` used a bare host
  as an example of "typed text", which part A promotes to a link: the Where line is now masked, and
  the scheduled event's description now carries `https://twitch.tv/bb`. The stored `location` is
  unchanged in every one of them (see H3), which is the assertion that proves no migration is needed.
- **H14 (docs) Sweep rows are 343–350 — eight, where § Follow-up 4 sketches roughly eight cases but
  bundles some.** One row per thing the owner has to see by eye: the four shorthand spellings (343),
  a bare host including the old-row case (344), the things that only look like hosts (345), the
  shorthand that does not resolve (346), the 404 note in `warn` (347, the one that needs a real
  internet connection), `refuse` / `off` / the seconds bounds (348), the aliases key edited on
  Settings (349), and a shorthand beside a channel with the **Open link** button (350).
- **H15 (could NOT do) The three-second budget is UNTESTED against the real thing.** The check runs
  before the modal is answered, so a slow link eats into Discord's three-second window and then the
  panel still has to render. `events_where_link_check_seconds` is capped at 3 and defaults to 2 for
  that reason, but nothing here measured how long the render actually takes — no bot was booted. If
  the owner sees "This interaction failed" on a slow link, the first move is
  `events_where_link_check_seconds` → 1, and the second is `events_where_link_check` → off.
- **H16 (build → MEASURED at review) The `twitch.tv` caveat was asserted by the build; the review
  measured it.** The build could not open a link (the network is off limits under pytest), so the
  owner guide and sweep row **347** carried the caveat as a thing to confirm. The review (2026-09-11
  00:3x, the real `aiohttp_status` from the worktree, `seconds=2`) opened each default alias host with
  a real handle and a made-up one. Measured: **`twitch.tv`, `kick.com`, `tiktok.com`, `instagram.com`,
  `x.com` and `discord.gg` answer 200 for ANY name** (single-page apps — the 404 happens in the
  browser, not in the response); **`youtube.com/@…` answers 404 for a missing handle and 200 for a
  real one**; a dead host is `ClientConnectorDNSError` → `unreachable` in 0.02 s. So under the default
  table the check catches a typo'd HOST and a wrong YouTube handle, and nothing else; a wrong Twitch,
  Kick, TikTok, Instagram, X or Discord name passes. Also measured: `kick.com` timed out once at 2 s on
  its first probe and answered in 0.14 s afterwards, so a spurious "did not answer" note on Kick is
  possible and the note's wording ("the link is kept as typed") is honest about it. And
  `youtube.com/@skyaiva` — the owner's own example — answered **404**: that handle does not exist on
  YouTube, so `yt skyaiva` will show the note until the owner types the handle YouTube actually has.
- **H17 (review fix) `x.com` needed the header limits raised, or every X link was "did not
  answer".** aiohttp's default `max_field_size` is 8190 bytes, and `x.com` sends a response header
  (its 200 for a handle that does not exist, and the redirect from `twitter.com`) longer than that,
  so the GET raised `ClientResponseError: 400, Got more than 8190 bytes when reading …` — which
  `link_answers` classified as `unreachable`, a false "did not answer" for a host that had answered.
  Fix: `aiohttp_status` builds its session with `max_line_size` and `max_field_size` at
  `HEADER_BYTES = 65536`; re-probed, `x.com` is `ok` in 0.28 s for a missing handle and 0.46 s for a
  real one. Nothing else changed; the fix cannot be unit-tested (the conftest guard forbids a real
  GET, and an injected `fetch` never sees the session), so it is recorded here as a measurement.
