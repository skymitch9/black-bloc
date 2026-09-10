# The "Where?" picker — a real place on `/event` Propose, like Discord's own create-event dialog

> **Audience:** whoever maintains the events form. **Status:** TRACKED, DESIGN — written
> 2026-09-10 16:13 against `main` at `3609b3e` (v102); nothing here has been run. Build dispatched
> to an Opus agent the same afternoon; every departure goes in a **`## Deviations`** foot the build
> appends. Last verified: **2026-09-10 16:13** — what exists today was read in
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
