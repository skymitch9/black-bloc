# The "When?" picker — `/event` Propose and `/raidtrain` Start as draft panels

> **Audience:** whoever maintains the two forms. **Status:** TRACKED, ✅ **BUILT** — branch
> `when-picker` off `main` at `ef54e60`, commits `446f191` (the module), `567d33b` (the five
> settings keys), `6c0768d` (`/event`), `869e57a` (`/raidtrain`) and this docs commit.
> ⚠️ **NOT merged, NOT deployed, and NOT seen in Discord** — no test can click a Discord button
> (`../access/testing.md`), so what is proven here is the suite (**5286 → 5395**, green forward
> and `BB_REVERSE=1`), `ruff`, and the mock (`ok - 17 pages, 150 routes, 14 core settings`).
> The sweep rows a person still has to run by eye are **323–327** in
> [`../access/sweeps.md`](../access/sweeps.md). Every departure from what is written below is in
> the **`## Deviations`** foot. Last verified: **2026-09-10** — the design below was verified
> against `main` at `c3f842b` before the build (what existed then was read in
> `black_bloc/cogs/community/events.py`,
> `black_bloc/cogs/content/raidtrain.py`, `black_bloc/events.py`, `black_bloc/timezones.py`,
> `black_bloc/settings_store.py`; nothing here has been run yet). Pattern reference:
> [`panels-program.md`](panels-program.md) §4 (`Panel`, `answer`, `capped_placeholder`,
> `panel_minutes`, the generic `NoteModal`). Earlier decision it revises:
> [`events-panel-design.md`](events-panel-design.md) chose a typed `My time zone` modal because
> "598 zones cannot fit a 25-option select" — this doc keeps the typed door as the 25th option.

## 1. What the owner saw and asked (2026-09-10 ~15:00, verbatim)

> "A few bad experiences right away using /events I apparently made an error and the form went
> away to be refilled We also need to solve this auto select timezone thing or at least make it a
> dropdown Same for time and date Can we get drop down there too"

He typed `2026-09-11` into `Start — YYYY-MM-DD HH:MM`; `checked_fields` refused it (the
`start_error` sentence) and, because a modal-submit interaction cannot be answered with another
modal, the ephemeral refusal was all he got — title, description, location, gone.

Decided with the owner, one question at a time (2026-09-10 15:08–15:10):

- **Q1 = "A"** — Propose becomes a **draft panel + text modal**, not a modal with selects inside.
- **Q2 = "Yes, same build"** — `/raidtrain` Start gets the same picker in this build.

## 2. The one rule that fixes ask (1): modals never refuse

**A modal only ever stores what was typed into the draft and re-renders the panel.** All
validation moves to the panel: it shows what still needs fixing in words, and the **Submit /
Start button renders only when everything passes** (P-rule from `panels-program.md`: moves
render only when valid). Nothing typed can be lost, because the panel holds it and a modal has
no failure path. This is also why no "Try again, pre-filled" button is needed — the modal's
`TextInput.default` is filled from the draft every time it opens, so *editing* is the same
gesture as *retrying*.

Discord constraints this respects: a modal holds ≤ 5 components; a select holds ≤ 25 options; a
View holds ≤ 5 action rows; a modal-submit cannot answer with a modal; Discord exposes no user
time zone to a bot (so "auto" = *remembered*, §5).

## 3. The shared module — `black_bloc/when_picker.py`

Pure state + option builders + the four `discord.ui.Select`s, owned by neither cog. Both draft
panels import it. Near-zero comments; notes go to `docs/info/code-notes.md`.

```python
@dataclass
class WhenDraft:
    zone: str                      # IANA name, always known
    day: date | None = None        # local date in `zone`
    hour: int | None = None        # 0–23
    minute: int | None = None      # 0–59, a multiple of the step
    later_text: str = ""           # what "Later…" typed, kept even when unreadable

    def start_text(self) -> str | None   # "YYYY-MM-DD HH:MM" or None when incomplete
```

| Builder | Options (≤ 25) | Notes |
|---|---|---|
| `day_options(zone, now, count)` | `Today · Thu Sep 10`, `Tomorrow · Fri Sep 11`, `Sat Sep 12` … (count = 24) + **`Later — pick a date…`** | computed in the draft's zone; a `later_text` date that parses is shown as its own selected option in place of the 24th |
| `hour_options()` | `12 AM`, `1 AM` … `11 PM` (24) | value = `0`–`23` |
| `minute_options(step)` | `:00`, `:15`, `:30`, `:45` at step 15 | `step` = setting `time_step_minutes` (5–60 → ≤ 12 options) |
| `zone_options(choices, stored, guild_default, now)` | the `timezone_choices` list (≤ 24) + **`Other — type it…`** | label `America/Phoenix · now 3:07 PM`; the member's stored zone, if absent from the list, replaces the 24th; the selected default is stored → guild default |

`DaySelect`, `HourSelect`, `MinuteSelect`, `ZoneSelect(discord.ui.Select)` each write one field
of `view.draft` and call `view.rerender(interaction)`. `Later — pick a date…` sends
`LaterModal` (one `TextInput`, label `Date — YYYY-MM-DD`, `default=draft.later_text`), whose
`on_submit` stores the text and re-renders (rule §2). `Other — type it…` sends the existing
`ZoneModal` (`events.py:775`) with `previous=` the draft panel so it re-renders there.

`resolve(draft, now)` returns `(start_text, problem)`; the cogs then pass `start_text` through the
validation they already have (`checked_fields` for events, the train's own) so the DST-gap,
ambiguous, past and duration rules stay in ONE place. The panel line comes from that same
function's sentence, unchanged.

## 4. The two draft panels

### `/event` → Propose → `EventDraftPanel(Panel)` (ephemeral, `panel_minutes` timeout)

```
Propose an event — draft
Title:     Cookout at the park        ← "(needed)" when empty
When:      Fri Sep 12 · 7:00 PM, read in America/Phoenix   ← "(pick a day, hour and minute)"
How long:  2h
Where:     (not set)
What:      first 120 chars of the description, or "(nothing yet)"
Still needed: a title                 ← one line, omitted when nothing is
[ Day ▾ ] [ Hour ▾ ] [ Minute ▾ ] [ How long ▾ ]
( Title & details ) ( Time zone ) ( Submit ) ( Back )      ← Submit only when valid
```

- **Title & details** → `EventTextModal` (3 fields: Title, What is it?, Where or a link —
  `default=` from the draft). Stores, re-renders. Never refuses (length is clamped as today).
- **How long ▾** → `duration_options()`: 30m, 45m, 1h, 1h30m, 2h, 2h30m, 3h, 4h, 5h, 6h, 8h,
  12h, All day. Default = new setting `events_default_minutes` (replaces the hard-coded
  `DEFAULT_DURATION_MINUTES = 120` at `events.py:47`; `parse_duration`'s default reads it).
- **Time zone** → `ZonePanel` (§5) which comes back to the draft.
- **Submit** → exactly what `Events.submit` does today from `checked_fields` onward
  (`submit_event`, the ephemeral sentence + `when_line`, the DM'd card). Then the panel retires
  with the same sentence. One write, one `event.submitted` row — unchanged.
- **Back** → the `/event` panel, draft discarded (say so in the button's confirmation line? No —
  the draft is seconds of work; just go back. Deviation D1).

### `/raidtrain` → Start a raid train → `TrainDraftPanel(Panel)`

Same shape. `TrainTextModal` fields: Title, What is it?, **Minutes per slot**, **How many
slots** (4 fields; numbers are stored as typed, the panel says `Minutes per slot: "abc" is not a
number` and holds Start back until both pass the existing `run_setup`/`submit_train` rules).
Rows: `[ Day ▾ ] [ Hour ▾ ] [ Minute ▾ ]` + `( Title & details ) ( Time zone ) ( Start ) ( Back )`.
Start → what `submit_train` does today from validation onward. The organizer gate
(`still_organizer`) stays on the button and on Start.

`EventModal` (`events.py:862`) and `TrainModal` (`raidtrain.py:745`) are **removed**, along with
`MODAL_ZONE_HINT` in both `events.py:269` and `raidtrain.py:88` if nothing else uses them.

## 5. Time zone — ask (2), as far as Discord allows

Discord gives a bot no user time zone, so **"auto" = the last pick is remembered** (already
true: `user_timezones`). What changes:

- `ZonePanel(Panel)`: one `ZoneSelect` + `( Other — type it… ) ( Back )`. Reached from the
  `/event` panel's **My time zone** button (replacing the direct `ZoneModal`) and from both
  draft panels' **Time zone** button; `previous` decides where Back goes. Picking stores via
  `store_zone` (its sentence and log row unchanged) and returns.
- A member who has never chosen sees, on the draft panel: `read in America/Phoenix — the
  server's default; press Time zone if that is not yours`. Once stored, the hint drops.
- New settings keys (checklist 33), both `text`, registered in `settings_store.py` with the
  usual kind / default / description / label entries so the Settings page and
  `/settings set-value` reach them:
  - `default_timezone` — default `America/Phoenix`; validated with `timezones.is_known` on set
    (refuse with a sentence naming the closest `suggest()`); `timezones.get_timezone(db,
    user_id, fallback)` gains the fallback argument and every caller passes the guild's value
    (`cogs/community/events.py:534`, `cogs/content/raidtrain.py:1631`,
    `api/tools/events.py:157`, `events.py:1304 stored_zone`). `DEFAULT_TZ` stays as the
    module-level last resort for callers with no guild (`polls.py`, `requests.py`,
    `chat_data.py` — out of scope, leave them).
  - `timezone_choices` — comma-separated IANA names, default the 24 below; each validated with
    `is_known`, at most 24 kept (the 25th slot is `Other`).

Default `timezone_choices` (24): `America/Phoenix, America/Los_Angeles, America/Denver,
America/Chicago, America/New_York, America/Anchorage, Pacific/Honolulu, America/Toronto,
America/Vancouver, America/Mexico_City, America/Sao_Paulo, Europe/London, Europe/Paris,
Europe/Berlin, Europe/Madrid, Europe/Moscow, Asia/Tokyo, Asia/Seoul, Asia/Shanghai, Asia/Kolkata,
Asia/Dubai, Australia/Sydney, Australia/Perth, Pacific/Auckland`.

Third key: `time_step_minutes` (`int`, 5–60, default 15) — the Minute dropdown's step. With
`events_default_minutes` (§4) that is four new keys: 191 → **195** (verify the starting count
in `tests/test_settings_store.py` first — 191 is the v96 figure).

## 5b. The scheduled event's name — added 2026-09-10 15:11 (owner: "Can we make it also say '{Event Name} Feat. BaF' when it post the discord events after")

`create_scheduled_event` (`black_bloc/events.py:716`) names the Discord scheduled event
`clamp(row["title"], EVENT_NAME_LIMIT)`. New `text` key **`events_scheduled_name_template`**,
default **`{title} Feat. BaF`**, rendered with `.format(title=…)` (an unknown placeholder or a
template without `{title}` is refused on set, in words) and clamped to `EVENT_NAME_LIMIT` after
rendering so a long title never makes Discord refuse the event. Applies to the scheduled event
only — the review card, the announcement and the DM keep the plain title (they already say whose
server it is). Raid trains' `raidtrain_scheduled_event` keeps its own name; if the owner wants
the suffix there too that is one more key, not a shared one. Owner, 15:12: "Also make that standard name format something changeable on the website" — it
is a registry key, so the Settings page (https://blackbloc.heygabi.ai/settings.html, Events
group) and `/settings set-value` both edit it; the agent verifies the key renders there in the
mock (`check.mjs`) and names the group in its report. Key count → **196**. One test in
`tests/test_events.py` (`.format` result, clamp, the refusal on set in `test_settings_store.py`).
Sweep row: approve an event outside TEST_MODE and read the calendar name — owner-side, since
TEST_MODE makes no scheduled event (`event.would_create_scheduled`).

## 6. What does NOT change

- Validation sentences (`start_error`, `DST_GAP`, `DST_AMBIGUOUS`, `START_IN_THE_PAST`,
  `BAD_DURATION`, `NO_TITLE`) — reused verbatim on the panel line.
- `submit_event`, `submit_train`, the review card, approvals, the scheduled event, the DM.
- The website's Events / Raid-train create forms and `POST /api/events` (typed `start` + `tz`
  stay; a `datetime-local` input there is a later item, filed on TODO).
- TEST_MODE: panels are ephemeral interaction responses, already allowed today.

## 7. Tests (mirror the package)

- `tests/test_when_picker.py` — every builder at the 25 cap; day list across a month boundary
  and a DST change in `America/New_York`; `later_text` that parses / does not; `resolve` on an
  incomplete draft; zone list with a stored zone outside the choices; step 5 / 15 / 60.
- `tests/cogs/community/test_events.py` — the draft panel: Submit absent until title + when +
  duration; a bad `Later…` date keeps the title; Submit produces exactly one event row and one
  `event.submitted` row; Back discards; the ZonePanel stores and returns.
- `tests/cogs/content/test_raidtrain.py` — the same for Start; `"abc"` slot minutes held on the
  panel with the sentence, title kept.
- `tests/test_settings_store.py` — the three keys (count, kinds, defaults, `default_timezone`
  refuses an unknown zone, `timezone_choices` drops unknowns and caps at 24).
- `tests/test_timezones.py` — `get_timezone` fallback.
- `site/mock/check.mjs` must still print `ok - 17 pages, 150 routes, 14 core settings`.

## 8. Docs the build touches

`docs/info/code-notes.md` (new module + the two panels, keyed `path:name`),
`docs/info/README.md` (this row → BUILT), `docs/access/sweeps.md` (rows **323+**: propose with a
bad Later date and see the title kept; pick a zone from the dropdown; start a train with `"abc"`
slot minutes; the Settings page shows the three keys), `docs/TODO.md` item → `DONE.md` at the
landing (conductor does the move), `docs/info/settings-registry.md` or wherever the key table
lives (the agent greps for `logs_important_only` to find it).

## Deviations

- **D1** Back discards the draft without asking — a draft is seconds of typing and the confirm
  would be a second question for every cancel.
- **D2** The draft lives in the View's memory, not a table: the panel's `panel_minutes` timeout
  retires it with the usual "this panel has expired" line. Poll drafts got a table because they
  are saved on purpose; these are not. If a person hits the timeout mid-draft that is the
  first thing to revisit (a `when_drafts` table keyed on (guild, user, feature)).
- **D3** Dates further than 24 days out are typed, not scrolled — a second page of days would
  cost a row the panel does not have.
- **D4** The website forms keep their typed date; filed on TODO, not built here.
- **D5** (build) **The zone line never disappears; only the "the server's default" half does.**
  §5 says the hint drops once a zone is stored. It does — but a member with a stored zone and no
  time picked yet would then see no zone at all on the draft, which is the confusion the whole
  change exists to end. `events.DRAFT_ZONE` replaces `DRAFT_ZONE_HINT` once stored: one clause,
  naming the zone and the button that changes it.
- **D6** (build) **The `Later…` modal takes a DATE only, so the old `YYYY-MM-DD HH:MM` sentence
  is gone from that path.** §3's `LaterModal` is one `Date — YYYY-MM-DD` box, so a typed
  `next tuesday` is answered by a new sentence (`when_picker.BAD_DAY`) naming what was typed and
  the shape wanted, not by `start_error`. `start_error` is untouched and still says
  `YYYY-MM-DD HH:MM` on the paths that take a whole timestamp — the website's form, and the
  train's `draft_check` when a resolved string somehow fails to parse.
- **D7** (build) **`Events.submit` went with `EventModal`.** §4 only names the modal, but the cog
  method existed solely to be called by it, and P4 says the panel calls the shared function. The
  panel's `submit_draft` does what it did, from `checked_fields` onward. The 65 tests that drove
  `submit(...)` now drive `submit_draft`, so the propose path is still covered end to end.
- **D8** (build) **`read_numbers`, `BAD_NUMBER` and `OUT_OF_RANGE` moved from the raid-train cog
  into `black_bloc/raidtrain.py`.** Not asked for; forced by §4 putting the numbers in the same
  gate as the time, which lives in the pure half. The sentences are byte-identical, which is why
  the four parametrised refusal tests kept their expectations.
- **D9** (build) **`TrainModal` was broken before it was deleted.** It was handed a `RaidPanel`
  and called `self.cog.submit_train(...)`, which no class in the file defines, so a real
  `Start a raid train` would have raised. Nothing in the suite touched it. Recorded because it
  means §4's "what `submit_train` does today" had no `submit_train` to point at — the behaviour
  reused is `run_create`'s, which the panel's `start_draft` now carries.
- **D10** (build) **Two bounds were added that §5 does not mention**, both mirrored into
  `site/mock/contract.json`: `time_step_minutes` 5–60 (the design's own range, made enforceable)
  and `events_default_minutes` 5–10080 (checklist 22 — a default above `MAX_DURATION_MINUTES`
  would refuse every proposal that left How long alone).
- **D11** (build) **`events_default_minutes` replaces `DEFAULT_DURATION_MINUTES` in exactly the
  two places §4 and §5b name** — the propose path's seed and `create_scheduled_event`'s fallback.
  `parse_duration`'s own default argument is untouched: it is a pure function with no store, and
  changing its signature would have moved the default for `POST /api/events` too, which §6 says
  does not change.
- **D12** (build) **The `/event` draft's `Back` discards without asking (D1 above), and so does
  the train's.** §4 only settles it for events; the same argument applies.
