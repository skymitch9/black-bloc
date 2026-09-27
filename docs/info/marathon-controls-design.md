# Marathon controls — a ping switch per marathon, a spotlight that follows the extended schedule, and the channel's spotlight controls on the marathon

> **Audience:** the conductor, reviewers, and the next session touching marathons, their pings or the spotlight.
> **Status:** TRACKED · 🔨 **BUILT on branch `marathon-controls` (off `main` `70edbad9`), NOT merged, NOT deployed** —
> it ships with the merged, undeployed `marathon-inbox` as one deploy. Schema **71 → 72**, registry keys **543 → 552**,
> contract routes **261 → 262**, one new log kind, eighteen deviations below.
> **Last verified: 2026-09-26** — against the branch's own code by the tests (`tests/test_marathon_ping.py`,
> `tests/cogs/content/test_marathon_ping.py`, `tests/test_marathon_spotlight.py`,
> `tests/cogs/content/test_marathon_spotlight.py`, the card tests in `tests/cogs/content/test_marathon.py`, the API
> tests), `check.mjs` on a worktree mock (`MOCK_PORT=8813`: *22 pages, 262 routes*), and a headless Chrome render over
> CDP of `events.html#marathon-1` (the Spotlight card, the ping switch, a held spotlight, a Pin press, phone width) and
> of the GamesDoneQuick Go-live drawer against a second mock built from `origin/main` (0 differences of 102 lines
> except the mock's clock-relative seed times). ⚠️ **NOT checked:** anything against Discord, the live database, the
> live marathons and channel rows, and the real bot was never run. Secret NAMES only.

## The asks, verbatim (owner, 2026-09-26 16:5x–17:3x Phoenix)

1. *"can we make sure we have an option in each marathon to ping marathon role on or off"* + *"have it off by default"*
2. *"also make sure it has spotlight controls that match our existing spotlight controls for the channel. we can also
   have the marathon dynamically set the timing for the spotlight"*
3. *"also if the events get extended make sure we extend the spotlight, maybe by like an extra hour"*

## A. The ping switch, as built

**Model.** `marathons.ping_role INTEGER NOT NULL DEFAULT 0` through `ADDED_COLUMNS` (schema **72**, mirrored to
`marathons_archive` at boot). Every existing marathon reads **0 — off** after the migration, so SS4C #6 and Fall Fest #7
stop mentioning roles until staff turn it on.

**Keys (nine, Marathons group, registry + mock row + label):**

| Key | Type | Default | What |
|---|---|---|---|
| `marathon_ping_role_default` | bool | **off** | what a NEW marathon's switch starts at — staff-made and feed-made alike (`create_marathon` is the one door) |
| `marathon_ping_role_on_said` / `_off_said` / `_same_said` | text `{marathon}` | *…pings again…* / *…pings no role now…* / *…already has that…* | the answers, both doors |
| `marathon_ping_role_button_on` / `_off` | text | *Ping the role* / *Stop pinging* | the `/event` card's one button, drawn as the next state |
| `marathon_ping_role_line_on` / `_off` | text | *Pings the role* / *Pings no role* | the `/event` card's header line |
| `marathon_spotlight_tail_minutes` | int 0–720 | **60** | §B |

**Off means** (`black_bloc/marathon_ping.py:pings_role`):
- `Marathons._ping_roles` answers **no role at all** — neither the runner's own fan role nor the channel's spotlight
  role. It is the one function both the run reminder and the live shoutout ask, so both post with no mention
  (Deviation 1).
- `Marathons.sync_window` keeps **no** marathon ping window for it (the existing one is deleted and
  `marathon.window_dropped` logged), so an `events`-mode channel does not ping its go-live announcement for this
  marathon either. On makes the window again at once.

**The doors.** The marathon drawer's Settings foldout (*Ping the marathon role* On/Off, rides **Save**); the `/event` ▸
Marathons… card (one button, row 2, whose label is the next state, plus the header line); `PATCH /api/marathons/{id}`
`{"ping_role": true|false}`. All three call `cogs/content/marathon_ping.py:set_ping_role` — under the marathon lock,
re-reads the row, writes, re-syncs the window, then logs `marathon.ping_role_set` (routine; `web.` head from the site,
checklist 34) with `from` / `to` / `spotlight_id`. A malformed value is refused 422 `bad_ping_role` in words.

## B. The spotlight follows the extended schedule, plus a tail

**Verified first, as asked.** The *follow* already used the live span: `Marathons.follow_spotlight` re-reads the
marathon row on every schedule read (`refresh`) and every minute tick, and `apply` rewrites `starts_at` / `ends_at`
from the runs on every successful read. The *lift* did **not**: `Spotlight.sweep_expiries` gave a held spotlight back
on its stored `expires_at` alone, never asking the marathon. Fixed — the held branch now calls
`cogs/content/marathon_spotlight.py:settle_held`, which takes the holding marathon's lock, re-reads it, runs the follow
(which extends when the current span plus the tail reaches past the stored end) and lifts only when it still has
nothing to extend and the row is due.

**The tail.** `marathon_spotlight_tail_minutes` (default 60, 0–720) is added to the span end by `reach_end` and used by
`plan` (the end written on the row), `in_reach` (so the follow still acts during the tail) and `dimmed_during` (staff
Off during the tail still stops that marathon's follow). `0` is exactly the v174 end.

**The log.** A later end on a spotlit row still logs `marathon.spotlight_extended` (routine) once per move — the plan
only writes when the new end is later than the stored one — now with `held` and `tail_minutes` in its details.

## C. The Spotlight card on the marathon, as built

**One component.** `site/public/assets/spotlight-controls.js` holds what the Go-live drawer drew for a channel's
spotlight — `spotlightMoves` (on/off, Extend a week, Keep for ever / Let it expire, Bump now, Pin), `datesCard`,
`pingsCard` (with **Add a window…**), `spotlightQuiet`, `spotlightCard`, `announceMoves` and `announcedSaid`. The code
moved out of `page-golive.js` whole; both pages import it, pass the channel row and an `after(done)` redraw. Every write
goes to the same `/api/golive/spotlight/{id}` routes with the same bodies, so the answers are the same sentences.

**The marathon drawer** (`marathons-section.js:spotlightBlock`), right under the header:
- a **state line** with a badge — *Spotlit by this marathon until {end + tail} — its last run plus 60 minutes, and it
  moves if the schedule does.* / *Spotlit and kept for ever* / *Spotlit until {date}, on staff dates* / *Scheduled* /
  *Not spotlit yet — it turns on {start − lead}* / *Not spotlit.* (+ *Following is off…* or *off for marathons*);
- **Follow the schedule** On/Off — the marathon's `spotlight_mode` (v174), moved here from the Settings foldout and
  written at once;
- the channel's own controls from the shared component, the announce state and switch, and one quiet line: *These are
  the channel's own controls — every change here shows on the Go-live page too.* **Open on Go-live ↗**;
- the shared **Pings** card below it.
- A marathon with **no channel** shows one sentence instead (*No channel yet, so there is nothing to spotlight…*).
- Every write keeps the drawer open and redraws it with the answer (`after` → `openMarathon`).

**The data.** `GET /api/marathons/{id}` carries `channel_spotlight` (`api/tools/golive.py:one_spotlight` — the Go-live
row, same shape) and `spotlight_state` (`black_bloc/marathon_spotlight.py:state_of` via
`cogs/content/marathon_spotlight.py:state_for`: `state`, `line`, `until`, `starts`, `held_by_this`, `follows`,
`tail_minutes`). The sentence has `{until}` / `{starts}` left in it for the reader's own clock — the site fills them with
its local time, Discord with `<t:…:f>` (`discord_line`).

**The `/event` card.** The header line reads the same state; **Spotlight…** (row 2, only with a channel) opens a
Spotlight view: the state, the follow line, the follow switch, **The channel's spotlight…** (the `/golive` ▸ Channels
card itself, picked on this channel) and **Back**.

**Staff final say.** Unchanged from v174 and kept on the new card: staff dates or Spotlight off on a held row make it
theirs (Deviation 11 of v174); Follow Off gives back a spotlight the marathon holds.

## Deviations

1. **Off silences the shoutout too, and both roles.** The brief said *reminders*; the gate is in `_ping_roles`, the
   one function the reminder and the live shoutout share, so a marathon with its switch off mentions no role anywhere
   — neither the runner's fan role nor the channel's spotlight role (the go-live role was never in either).
2. **A STAFF window on the same channel still opens pings** for that channel's go-live announcements — the switch only
   removes the marathon's own window (staff's say, as v174 §B already noted).
3. **Six existing tests opt in per test** (`marathon_ping_role_default = true` at their top) rather than in the shared
   fixture, so each says it depends on the switch: four in `test_marathon.py`, one in `test_marathon_inbox.py`, one
   API test.
4. **The drawer's switch rides Save** in the Settings foldout, as `spotlight_mode` did there; the `/event` button and
   the API are instant.
5. **The refusal for a malformed value is a constant** (`BAD_PING_ROLE`), like v174's `BAD_MODE` — an API-input error,
   not a word the bot posts. Everything a person reads on a panel or in an answer is a key.
6. **The follow was already live; the lift was not** (§B). An overrun the organiser does NOT publish into the schedule
   is still not seen — the tail is what covers it.
7. **The tail counts in `in_reach` and `dimmed_during`**, not only in the written end — otherwise a marathon inside its
   tail would stop extending and a staff Off during the tail would not stop its follow.
8. **`settle_held` re-checks the row is due by the marathon cog's clock** (returns `kept` otherwise). In production the
   sweep's wall clock and the cog's clock are the same; the guard exists for the tests and for a race where the follow
   already moved the end.
9. **`marathon.spotlight_extended` gains `held` and `tail_minutes`** and is still logged for an unheld staff row carried
   later (v174 Deviation 9 kept).
10. **The follow-On answer now names the tail** (*…to 60 minutes after its last ends.*), a constant in
    `marathon_spotlight.py` as in v174.
11. **`spotlight_mode` left the Settings foldout** for the Spotlight card as *Follow the schedule*, written at once
    rather than on Save; the foldout keeps the ping switch.
12. **`announcedSaid` and its two sentences moved too.** `page-golive.js:announcedSaidFor` was dead code (defined, never
    called); its words now live once, in the shared module, and the marathon card uses them. Go-live keeps its own
    `after` callbacks: its announce switch still closes the drawer and refreshes as before; the marathon card redraws.
13. **Not on the marathon card:** Twitch, YouTube, Ping role, Remove and the channel's *Marathons: on/off* — they are
    the channel's, not its spotlight's; **Open on Go-live ↗** leads there.
14. **Pings is its own card below Spotlight** (the same component Go-live draws), not nested inside it.
15. **Discord: the channel's controls are the `/golive` ▸ Channels card itself.** Row 2 of the marathon card is full
    (Read, Pause, Board, Ping, Spotlight…), so v174's follow button moved into the Spotlight… view, and **The channel's
    spotlight…** renders `render_spotlight` picked on the channel — one component, never a copy. Its **Back** returns to
    `/golive`, not to the marathon card.
16. **The state sentences are constants** (`marathon_spotlight.py:STATE_LINES`), served to the site as `line` — one home
    for both doors. They are panel and page words, never posted to a channel.
17. **The mock:** AGDQ 2027 is seeded with its switch **on** (the only seeded marathon window stays), every other
    seeded marathon off. The mock now mirrors the follow on the switch only — On spotlights the channel at once when in
    reach, Off gives back its own hold, staff dates or Off clear the holder — still with no tick (v174 Deviation 16
    narrowed, not reversed).
18. **Found by the render, fixed before the commit:** `page-golive.js` already declared `announceMoves` (the member
    opt-out), so the new import collided — a `SyntaxError` at module link, the Go-live page blank. ⚠️ **`node --check`
    on the file did not catch it**; `node --input-type=module --check < file` does. The gate's undefined-identifier gap
    (TODO 🧪) has a cousin here.

## What was NOT verified

- **Nothing met Discord.** The `/event` card's ping button, header lines and Spotlight… view were exercised through
  `FakeInteraction` (`tests/cogs/content/test_marathon.py`), not a real interaction; the Channels card rendered inside a
  marathon panel message was never seen.
- **The live migration** (schema 72) has not run; the live marathons were not read. After deploy every marathon —
  including SS4C #6, which the owner wants tracked — pings **no role** until its switch is turned on.
- **A real extended schedule** was not watched: the extension is proven with a canned schedule gaining a run and with
  `ends_at` moved by hand; the lift with the sweep and the marathon clock driven by the tests.
- **The Settings page** rendering the nine new keys was not looked at (labels and help are checked by the tests and
  `check.mjs` only).
- **Phone width** was rendered for the marathon drawer only (no horizontal scroll); Go-live at phone width was not.
