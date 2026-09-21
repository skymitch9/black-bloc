# The date-time picker on the SITE — one `whenField` for every page

> **Audience:** whoever touches a date or a time box on the dashboard.
> **Status:** TRACKED · ✅ **LIVE as v150** (release `575dde2`, deployed 2026-09-20 23:32 Phoenix; sweeps **712–716**, were `WP-a` … `WP-e`, all unwalked) · was BUILT, NOT MERGED, NOT DEPLOYED on branch `when-picker-site`, worktree `C:/lcw/bb-when-picker-site`, off `main` at `4a33938`. **Last verified: 2026-09-20** — measured
> in `chrome-headless-shell` 149.0.7827.22 over raw CDP against this worktree's mock on
> `MOCK_PORT=8780`; the gate lines are in the build's report and repeated under
> [What was NOT verified](#what-was-not-verified). ⚠️ **Nothing here has met Discord or the live
> site**, and no Python changed — every route this touches already took the shape it is now sent.
>
> Companion: [`when-picker-design.md`](when-picker-design.md) is the Discord half (v100, `/event`
> Propose and `/raidtrain` Start as draft panels). Its **D4** said the website's typed date was
> "filed on TODO, not built here". This is that item, built. Sweep rows: `WP-a` … `WP-e` in
> [`../access/sweeps.md`](../access/sweeps.md).

## 1. What the owner asked (2026-09-20, verbatim)

> "for raid train and events and anywhere else we set a date time, put a date time picker"

## 2. The construct — `site/public/assets/ui.js:whenField`

```js
whenField({ label, value, tz, min, help, dateOnly, timeOnly, zoned, zoneWord })
  → { node, input, zone, value(), tz() }
```

- **`node`** is a `.field` built exactly as `field()` builds one — label, control, help — so it
  drops into a `.formrow` and inherits every rule already in `site.css`. Callers append
  `x.node` where they used to write `field('Starts', x, '…')`.
- **the control** is a native `<input type="datetime-local">`, or `type="date"` under `dateOnly`,
  or `type="time"` under `timeOnly`. Nothing is typed as a string any more.
- **the zone** is a `<select>` from `zoneSelect()`, shown for a datetime unless `zoned: false`.
  It is fed from the bot's own `timezone_choices` setting (the same 24 names the Discord
  `ZoneSelect` offers), read once through `settings()` and cached for the page.
- **the help line** always ends with the zone it is read in — `Read in America/Phoenix.` — and
  **re-renders when the zone select changes**, so what the person is told is what is sent.
  `zoneWord` replaces that clause for a field whose route takes no `tz` (polls).
- **`value()`** answers the exact string the routes already take: `YYYY-MM-DD HH:MM` (the
  `T` swapped for a space, seconds dropped), or `YYYY-MM-DD`, or `HH:MM`.
- **`tz()`** answers the IANA name the select is on.

Two smaller exports came out of it: **`zoneSelect(value, { blank })`**, so the one zone list has
one home, and **`localWhen(at)`**, the `YYYY-MM-DD HH:MM` of a browser-local instant, which was
`page-events.js:localStart` and is now shared (raid trains and the events editor both want "now"
for `min`).

### What the routes take — verified, not assumed

| Route | Field | Shape | Read in |
|---|---|---|---|
| `POST /api/raidtrains` | `start` + `tz` | `timezones.parse_start` → `%Y-%m-%d %H:%M` strictly, falling back to `parse_ts` | the `tz` sent |
| `PUT /api/events/{id}` | `start` + `tz` | `events.checked_fields` → the same `parse_start` | the `tz` sent |
| `POST /api/polls` (`kind=date`) | `start` | `polls.parse_day` → `%Y-%m-%d %H:%M` **or** `%Y-%m-%d` | ⚠️ `timezones.DEFAULT_TZ`, a module constant — `poll_plan` calls `date_slots` with **no** `tz_name`, so the route takes no zone for this field |
| `POST /api/polls/recurrences` | `at` + `tz` | `polls.parse_clock` → `%H:%M`; `tz` blank means the server's zone | the `tz` sent, or the server's |
| `GET /api/actions` | `since` / `until` | `YYYY-MM-DD` | day boundaries, no zone |

Because `parse_start` is strict, **the one thing `whenField` must never send is the browser's
`T`**. That is the whole payload change, and it is one `replace` inside `value()`.

## 3. The audit — every date and time field on the site

| # | Where | Was | Is now | Why |
|---|---|---|---|---|
| 1 | `page-raidtrain.js:333` — Start a raid train ▸ **Starts** | typed `2026-09-14 19:30` | `whenField` + zone select, `min` = now | the owner's first named case |
| 2 | `page-events.js:149` — an event's **Change it** ▸ **Starts** | typed, `tz` hard-wired to the browser | `whenField` + zone select, seeded from `starts_at`, `min` = now | the owner's second named case; the zone is now the person's to pick rather than whatever their laptop says |
| 3 | `page-polls.js:528` — Create a poll ▸ **First slot** | typed `2026-09-05 or 2026-09-05 19:00` | `whenField`, **no** zone select | the route reads it in the server's own zone and takes no `tz` (table above); the help says so in words rather than showing a select that would be a lie |
| 4 | `page-polls.js:537` — recurrence ▸ **Time of day** | typed `19:00`, `maxlength: 5` | `whenField` `timeOnly` | a time box the owner's grep would find; `parse_clock` takes exactly what `type=time` produces |
| 5 | `page-polls.js:538` — recurrence ▸ **Timezone** | typed IANA name, `placeholder: America/Phoenix` | `zoneSelect` with a blank **the server's own zone** first option | not a date box, but it is the zone half of #4; the blank option keeps today's "blank means the server" behaviour exactly |
| 6 | `page-audit.js:63` — Logs ▸ **From** / **To** | already `type: 'date'`, its own `dateBox` | `whenField` `dateOnly` | one construct; the local `dateBox` helper now just wraps `whenField` and keeps the change listener |
| 7 | `page-preview-events.js:355` — preview ▸ event **Starts** | typed | `whenField`, `zoned: false`, `tz: HERE` | mirrors #2 in the /preview lane |
| 8 | `page-preview-events.js:681` — preview ▸ train **Starts** | typed | `whenField`, `zoned: false`, `tz: HERE` | mirrors #1 |
| 9 | `page-preview-polls.js:751` / `:760` — preview ▸ **First slot**, **Time of day** | typed | `whenField`, `zoned: false` / `timeOnly` | mirrors #3 and #4 |

### Found and deliberately LEFT — with the reason

| # | Where | What it is | Why it stays |
|---|---|---|---|
| 10 | `page-events.js` — **How long** | `2h`, `1h30m`, `45m` | a DURATION, not a time. The route takes `duration` and parses those words; there is no finish-time field on the form to pick. The brief's "if the form takes a duration instead, leave the duration" |
| 11 | `page-polls.js` — **Open for, hours** | a number, 1–768 | the same: a duration, and the poll's close is derived from it. There is no "closes at" field to pick |
| 12 | `page-golive.js:1012` — Spotlight a channel ▸ **Days to keep it** | a number; blank = for ever | ⚠️ **The conversion is one line but it is not honest in one line.** `spotlight.expiry_in_days` stores `now + N days` — an INSTANT computed from the clock, not a midnight. A picked calendar date can only be approximated by a whole number of days, so the row would then read *"Runs out Oct 2, 10:41 PM"* under a field that said *Keep it until Oct 1*. **What would change it:** `POST /api/golive/spotlight` accepting `expires_at` the way `PATCH /spotlight/{id}` already does (`api/tools/golive.py:343`) — then the picker is exact and this becomes a date field |
| 13 | `page-rolemenus.js` — **Days**, **Days to add** | numbers | the same family as #12, and *Days to add* is explicitly relative to the grant's existing end ("pushed back from where it is now, not from today"), which no calendar can express. Not named by the owner; left for consistency with #12 |
| 14 | `page-birthdays.js:60–63` — **Month** / **Day** / **Year** | a select + two numbers; the year is OPTIONAL | ⚠️ A native `type=date` **cannot express a birthday with no year**, and the route takes `{month, day, year\|null}` with `year: null` meaning "do not show an age". Forcing a year, or inventing one, would silently change what `birthday_show_age` does. It is also already a picker — nothing is typed as a date string. ⚠️ **Separate finding, not fixed here:** `day`'s `max` is a flat `31` whatever the month is, so `Feb 31` is selectable on the form and refused by the server |
| 15 | `page-automod.js:35–37`, `page-moderation.js:258` | windows, timeouts, lengths in seconds | durations |
| 16 | `page-requests.js:938` — **Due date** | already `type: 'date'` | ⚠️ **OUT OF SCOPE** — the `requests-page` agent is rebuilding that file in parallel. It is already a picker; moving it onto `whenField` is a one-line follow-up once that branch lands |
| 17 | `page-preview-requests.js:860` — **Due date** | already `type: 'date'` | the preview twin of #16, left with it so the pair stays in step |
| 18 | `page-preview-birthdays.js:246–247` | the birthday twin of #14 | left with #14 |

## Deviations

- **D1 — the signature gained `timeOnly`, `zoned` and `zoneWord`.** The brief named
  `{ label, value, tz, min, help, dateOnly }`. `timeOnly` is what audit row #4 needs (a `19:00`
  box is a date-time field the owner's words cover, and a `datetime-local` would be wrong for it).
  `zoned: false` is what rows #3 and #7–#9 need — a zone select on a field whose route takes no
  `tz` would be a control that does nothing. `zoneWord` lets such a field still say, in words,
  which zone it IS read in. The alternative was three near-duplicate constructs, which is the
  thing the owner asked against.
- **D2 — `min` is set on the two Starts fields, and it does NOT replace the worded refusal.**
  Chrome greys earlier days in the calendar popup but still accepts a typed-in past value
  (`validity.rangeUnderflow` goes true and nothing enforces it), so the server's sentence is
  still what a person sees. Measured: typing `2020-01-02T10:00` and pressing **Start it** gave
  *"2020-01-02 10:00 has already gone by, so nothing was submitted. Pick a time in the future."*
  — which is sweep row `WP-e`. `min` is deliberately NOT set on the polls first slot (a date poll
  may legitimately start in the past) or on the logs From/To (people filter backwards).
- **D3 — the "Times are read in X" page notes are GONE from the events editor and the raid-train
  form.** The field now names its own zone, and the zone can now differ from the browser's, so a
  page-level sentence claiming the browser's zone would contradict the field under it. The rest of
  each note (`NOT_RESENT`, the lineup sentence) is untouched. Both pages' own `HERE` constant went
  with it.
- **D4 — the zone list arrives LATE.** `zoneSelect` renders with the wanted zone as its only
  option and appends the other 23 when `settings()` answers. A failed settings read is caught and
  leaves the select holding the one correct zone rather than breaking the form. It is never empty
  and never wrong; it is briefly short.
- **D5 — the two preview-lane copies got the picker WITHOUT the zone select.**
  `page-preview-events.js` opens with *"Static data; no api() call lives here"*, and `zoneSelect`
  reads `/api/settings`. Keeping that contract was worth one difference from the live page; the
  preview's help line names `HERE`, which is exactly what its page note said before. The preview
  polls page's **Timezone** box stays typed for the same reason.
- **D6 — polls' `First slot` lost the "a date, OR a date and a time" choice.** A
  `datetime-local` always carries a time. `date_slots` already treats local midnight as
  "no time on the labels" (`first.astimezone(zi).time() != datetime.min.time()`), so picking
  00:00 reproduces the old date-only behaviour exactly — and the help line now says so instead of
  asking the person to know it.
- **D7 — spotlight and the timed-role grants keep their `days` boxes.** Audit rows #12 and #13,
  with the arithmetic reason and the one-line change that would settle it.

## What was NOT verified

- ⚠️ **Nothing here has met Discord, the live site, or the real API** — every measurement is this
  worktree's mock (`MOCK_PORT=8780`) in `chrome-headless-shell`. The real `/api/settings` is
  assumed to carry `timezone_choices` with the same `{ key, value, default }` shape the mock
  serves; that shape was read in `site/mock/server.mjs:keyRow`, not against the bot.
- **No Python changed**, so `ruff` and `pytest` were **not run** — there was nothing for them to
  cover. The Python files named in the table were READ to establish the payload shapes.
- **The preview lane's events EDIT card** was opened and read (row #7 verified: label `Starts`,
  help `When it begins. Read in America/Phoenix.`, no zone select). The preview raid-train drawer
  and the preview polls drawer likewise. Nothing on the preview lane was SUBMITTED, because those
  forms post nothing by design (`wouldDo`).
- **No screenshot was taken**, and no colour or focus-ring check was made — the 390 px evidence is
  bounding boxes and `scrollWidth`, not pixels.
- **Nothing was checked in a browser that is not Chromium.** `datetime-local` and `time` render
  differently in Firefox and Safari; the payload cannot change, but the control's look can.
- **`page-requests.js` was NOT opened or edited** (audit row #16) — another agent holds it.
