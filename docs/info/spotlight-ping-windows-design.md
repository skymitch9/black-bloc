# A spotlight is split from its ping — a channel pings always, never, or only during events

> **2026-09-25 — the `marathon` source of a window is LIVE in code** (branch `marathon-schedule`, not merged): each marathon with a channel keeps ONE `source='marathon'`, `source_id=<marathon id>` window from its first run's start − `marathon_window_slack_hours` to its last run's end + slack, note = its name; pause, remove and a lost channel drop it. See [`marathon-schedule-design.md`](marathon-schedule-design.md).

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 10:5x Phoenix),
> dispatched to Opus as branch `spotlight-ping-windows`** off `main` `a959ebfe` (v163 live).
> **Last verified: 2026-09-25 10:5x** against `main` `a959ebfe`: `cogs/content/spotlight.py` — `announce_info` `:555`
> (renders with `ping_role_id=store.get(guild.id, PING_KEY)` and the row's fan role from
> `pings.announced_spotlight_fan_role` `:565`), the bump at `:677–683` (`pinging` decides the `ping_prefix`), `_post`
> `:1050` (takes `fan_role_id` + `pinging`), `_mentions` `:1153` (the one place the mention set is built — the global
> `golive_ping_role_id` and the row's fan role, both dropped when `pinging` is false), `DatesModal` `:1900` (two
> `TextInput`s read by `read_dates` — the pattern for typing a date range in Discord), `SpotlightMoveButton` `:1731`,
> `run_spotlight_move` `:1796`; `black_bloc/spotlight.py` — `read_moment` `:528`, `range_problem` `:558`,
> `is_scheduled` `:466`; `storage/db.py` — `spotlight_channels` `:879` (schema **58**, `ADDED_COLUMNS` `:1057`);
> `api/tools/golive.py` — `PATCH /spotlight/{id}` `:449`; `site/public/assets/page-golive.js` — `spotlightMoves`
> `:791`, `datesCard` `:837` (the row drawer's Dates card, the pattern for a date-range card), `addPingRole` `:610`;
> `site/mock/golive-join.test.mjs` (KI-36: the hand-typed key count). `settings_store.py` `SPOTLIGHT_*_KEY` `:1780–1797`
> (`NAMESPACE_OVERRIDE` → golive). Live rows (operator read 10:4x): GDQ `id 3` spotlight ON, no ping role yet; ESA `id 4`
> opted out. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 10:4x Phoenix)

*"I want to have a spotlight split from its ping role, for example I want GDQ to always be spotlighted, but I only want
it to ping the marathon role (which I will set later) during events. I want this to be customizable, its a lot of
moving parts."*

**What happens today (v163).** A channel row's spotlight (pin + reminders) and its pings are one thing: every
announcement mentions the global `golive_ping_role_id` AND the row's own fan role, and a bump mentions them too when
`spotlight_bump_pings` is on. GamesDoneQuick's Twitch channel is live almost continuously with reruns, so "spotlight on"
means a pinned, reminded rerun — and once it has a ping role, a pinged rerun. The owner wants the pin and the reminders
always, and the pings only while a marathon is on.

**The marathon role is the row's own ping role.** Nothing new: the Go-live page drawer's **Add a ping role… ▸ Use an
existing role** already lets staff hand GDQ the server's *Marathons* role (or any role). This design decides WHEN that
role — and the global one — is mentioned. It does not add a second role field.

## A. The model — a ping mode on the row, and a list of ping windows

**`spotlight_channels.ping_mode TEXT NOT NULL DEFAULT 'always'`** (`ADDED_COLUMNS`, schema 58 → **59**). Three values,
constants in `black_bloc/spotlight.py`: `always` (today's behaviour, the default so every live row is unchanged),
`never` (announce and remind with no role mention at all), `events` (mention roles only inside a ping window).

**A ping window** is a date range during which an `events` row pings. New table through the `SCHEMA` bootstrap:

```
CREATE TABLE IF NOT EXISTS spotlight_ping_windows (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    spotlight_id INTEGER NOT NULL,
    starts_at    TEXT    NOT NULL,
    ends_at      TEXT    NOT NULL,
    note         TEXT,
    source       TEXT    NOT NULL DEFAULT 'staff',
    source_id    INTEGER,
    added_by     INTEGER,
    added_at     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS spotlight_ping_windows_by_channel ON spotlight_ping_windows (spotlight_id, starts_at);
```

`source` is `staff` for a typed window; the marathon-schedule build (next, [`marathon-schedule-design.md`](marathon-schedule-design.md))
writes `source = 'marathon'` with `source_id` = its row and keeps that window in step with the schedule. This build
knows nothing about marathons beyond leaving the two columns and treating a non-`staff` window as read-only on the
doors (it renders with its source word; Remove is not offered for it — the marathon's own page owns it). Windows are
never deleted by time; a past window is history the drawer folds away (`spotlight_window_keep_days`, below, is the
sweep that purges them).

**The gate — one pure function, one caller per post.** `black_bloc/spotlight.py`:

```
def pings_now(row, windows, now=None) -> bool     # always → True; never → False; events → any window open at now
def open_window(windows, now=None) -> row | None  # the window that is open now, else None
def next_window(windows, now=None) -> row | None  # the soonest future window, else None
def ping_state_words(row, windows, now, **wording) -> str   # "Pings: always" / "Pings: never" /
                                                             # "Pings: during events — open until 19 Jan 23:00" /
                                                             # "Pings: during events — next 12 Jan 15:00 – 19 Jan 23:00" /
                                                             # "Pings: during events — no window set"
```

Every place that decides `pinging` for a channel row goes through `pings_now`: `announce_info` (`:555`) and the bump
(`:677`). ⚠️ **Announce, pin and remind are UNTOUCHED by the mode** — only the mention set changes. `_mentions` and
`ping_prefix` already take `pinging`; the builder passes the gate's answer instead of a constant. The bump keeps its
own `spotlight_bump_pings` key AND the gate: a bump pings only when both say yes.

**The window-open reminder — the case the owner's example actually hits.** GDQ is usually live BEFORE a marathon starts
(reruns), so no offline → live announcement fires at the moment the window opens and nothing would ever ping. On the
poll tick where a row's `events` gate flips from closed to open **while the row has an open session**, the cog posts
one bump through the existing bump path WITH the pings (`pinging=True`, ignoring `spotlight_bump_pings` for this one
post — the key governs the periodic reminders, not this) and resets `last_bump_at`, logging `golive.spotlight_bumped`
with `because: window_opened` and `window_id`. Governed by **`spotlight_window_open_reminder`** (bool, true). The flip
is detected by remembering, per open session, the last gate answer (`spotlight_sessions.pinging_last INTEGER` — one
nullable column, `ADDED_COLUMNS`, same schema bump), NOT by clock arithmetic, so a restart mid-window does not re-post
(the boot reconcile writes the current answer without posting). Window closing posts nothing.

## B. Doors — staff only, both, every move a button that renders only when valid

**The site — the Go-live page row drawer** (`page-golive.js`). A channel row's drawer gains a **Pings** card beside
Dates: the state line from `ping_state_words`, a three-way segment **Always / Never / During events** (`PATCH
/api/golive/spotlight/{id}` with `ping_mode`), and — shown only for `events` — the windows list (each: the range, the
note, the source word for a marathon window, **Remove** for a staff one) and **Add a window…** (a form dialog like
`addPingRole`: starts, ends, note; dates typed through the SAME control `datesCard` uses, read by the same route
parsing). The Streamers list's Announced cell gains ` · pings during events` / ` · no pings` after the spotlight word
for those two modes (nothing for `always`, the common case). `golive-join.js`: the spotlight payload carries
`ping_mode`, `ping_state`, `windows[]`; its test gains the fixture (an `events` row with one open and one future window;
a `never` row). Routes: `PATCH /api/golive/spotlight/{id}` accepts `ping_mode`; `GET /api/golive/spotlight/{id}/windows`,
`POST …/windows` (`starts_at`, `ends_at`, `note`; refuses end-before-start and a bad date in the existing words), `DELETE
…/windows/{window_id}` (refuses a non-`staff` window in words: *That window comes from the marathon schedule — change it
there.*). Contract rows + mock rows (GDQ → `events` with one future window named *AGDQ 2027*; ESA → `always`).

**Discord — `/golive` ▸ Channels… sub-panel** (`SpotlightMoveButton` / `run_spotlight_move`). The picked channel's card
gains the state line and three moves that render only when they change something: **Pings: always** / **Pings: never**
/ **Pings: during events** (the current one is not drawn), and, for an `events` row, **Add a ping window…** (a modal
shaped like `DatesModal`: starts, ends, note — three `TextInput`s, read by `read_moment` with the actor's zone the way
`read_dates` does) and a **Remove a window…** select listing the staff windows (a marathon window is listed disabled
with its source word). Nothing a member can press.

## C. Keys — six, prefix `spotlight_`, `NAMESPACE_OVERRIDE` → golive, registry + mock + label + `placeSettings` (the *How streams are spotted* drawer) + the join fixture (KI-36: bump the hand-typed count, or take the ride-along and derive it)

| Key | Type | Default | What |
|---|---|---|---|
| `spotlight_ping_mode_default` | enum `always` / `never` / `events` | `always` | the mode a NEW channel row gets |
| `spotlight_window_open_reminder` | bool | true | post one pinged reminder when a window opens on a live channel |
| `spotlight_window_keep_days` | int 1–365 | 30 | a window whose end is older than this is purged on the expiry tick (`golive.spotlight_window_purged`, routine) |
| `spotlight_pings_always_words` | text | `Pings: always` | the state line |
| `spotlight_pings_never_words` | text | `Pings: never` | the state line |
| `spotlight_pings_events_words` | text | `Pings: during events — {window}` | the state line; `{window}` is *open until {end}* / *next {start} – {end}* / *no window set* (three more keys: `spotlight_window_open_words`, `spotlight_window_next_words`, `spotlight_window_none_words`) |

Nine keys in all with the three `{window}` fillers. Every word a person reads from the bot is a key (owner rule); the
button labels are constants in `black_bloc/spotlight.py` beside `SPOTLIGHT_ON`. Enum validation refuses an unknown mode
in words.

## D. Logging

`golive.spotlight_announced` and `golive.spotlight_bumped` rows gain `ping_mode` and `pinged: true/false` (the bump row
already has `pinged`); the window-open reminder writes `because: window_opened`. New kinds, all under `golive`, all
ROUTINE (the 2026-09-21 rule: nothing in the spotlight family reaches `#blackbloc-logs` at the default level):
`golive.spotlight_ping_mode_set` (`from`, `to`, `via`), `golive.spotlight_window_added`, `golive.spotlight_window_removed`,
`golive.spotlight_window_purged`. No new feature, no new Logs chip. The `logkinds` count guard moves by four.

## E. Tests, docs, gate

`tests/test_spotlight.py` (pure: `pings_now` for the three modes, an open / future / past window, the boundary at
`ends_at`; `ping_state_words` all five shapes), `tests/cogs/content/test_spotlight.py` (an `events` row announces WITHOUT
a mention outside a window and WITH both roles inside one; `never` mentions nothing even inside a window; a bump under
`events` pings only inside a window and only when `spotlight_bump_pings` is on; the window-open reminder fires once on
the flip, not on the next tick, not after a restart mid-window, and not when the key is off; `always` is byte-for-byte
today's behaviour — the existing tests must not change), `tests/api/tools/test_golive.py` (the mode PATCH, the three
window routes, the staff gate, the marathon-window refusal), `tests/api/test_contract.py`, `tests/storage/test_db.py`
(59), `golive-join.test.mjs` (the fixtures), the key / kind count guards. Both `pytest -n 8` orders, `ruff check
black_bloc tests site`, the ES-module parse, `check.mjs` on a port of the builder's own (8797 is the conductor's), the
six node tests, env cleared per `access/deploy.md`. ⚠️ KI-26 and KI-37 as documented. Docs: `code-notes.md` (every
non-obvious line, keyed `path:line`); this doc's `## Deviations` + `## What was NOT verified`; `architecture.md`
(schema 59, keys); `docs/info/README.md` (one row); `spotlight-design.md` and `spotlight-pings-design.md` one dated
line each at the top; `sweeps.md` rows (a: set GDQ to *During events* on the Go-live page → the drawer says *no window
set* and GDQ's next announcement mentions no role; b: add a window covering now → the next poll posts one reminder
that pings; c: a bump inside the window pings only with `spotlight_bump_pings` on; d: *Never* → nothing is mentioned;
e: `/golive` ▸ Channels… shows the same three moves). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`
— the conductor owns those. ⚠️ Migrate before deploy: a column, a table and an index through the bootstrap;
`Database.connect` applies them at boot.

## Deviations

*(written by the build agent, 2026-09-25, branch `spotlight-ping-windows` off `main` `84f94347`; commits `27edccce`
… `d32efb57` plus this docs commit. Schema **58 → 59**, registry keys **419 → 428**, Go-live page keys **62 → 71**,
four new ROUTINE kinds, tests collected **7,810 → 7,875**.)*

1. **The three mode words live in `settings_store.py`** (`PING_ALWAYS` / `PING_NEVER` / `PING_EVENTS` / `PING_MODES`,
   beside the enum that validates `spotlight_ping_mode_default`) and `black_bloc/spotlight.py` imports them. §A said
   "constants in `black_bloc/spotlight.py`", but `spotlight.py` already imports `settings_store`, so the reverse import
   would be circular — and a second copy would break *one fact, one home* (checklist 15).
2. **The nine keys get their own Settings drawer, *When a channel pings*** (`golive-join.js` `DRAWERS` id
   `pingwindows`), not *How a stream is spotted*. That drawer is Discord presence, the YouTube probe and linking; the
   `spotlight-dates` build set the precedent of a drawer per word family.
3. **A marathon window in the Discord Remove select is listed, not disabled.** Discord cannot disable one option of a
   select, so the option carries its source words (*from the marathon schedule*) as its description, and picking it
   answers *"That window comes from the marathon schedule — change it there."* and removes nothing. The site draws the
   source word instead of a Remove button, as designed.
4. **A MODE change writes the open session's gate answer too** (`set_ping_mode`), not only the boot reconcile. So
   *Never → During events* while a window is already open posts nothing; the window-open reminder fires only when a
   WINDOW opens (or is added covering now — sweep `PW-b`). Without this, switching a live channel to *events* inside an
   open window would post a reminder saying nothing had opened.
5. ~~The window-open reminder checks `announces(row)` but not `is_spotlit(row)`.~~ **Closed at review (Fable, 2026-09-25 11:5x):** the guard now requires `is_spotlit(row)` too — spotlight OFF means *no reminders* (§A of `channel-streamers-design.md`), and this reminder is one; `test_a_window_opening_on_a_live_channel_with_spotlight_off_posts_nothing` covers it (the gate answer is still recorded, so nothing posts later either).
6. **Window times are written in the guild's `default_timezone`** (`19 Jan 23:00`) in the Discord card, the state line
   the route returns, and the bot's sentences; §A did not name a zone. The site's own windows list renders `when()` in
   the browser, like every other date on the page. The Discord modal and the site dialog READ in the person's own
   zone, like the Dates boxes.
7. **The window modal / dialog labels are constants, not keys** (*Pings start*, *Pings stop*, *What it is for*), like
   the button labels §C already made constants. §C named exactly nine keys; the Dates build's two box labels are keys
   because they are shared by two forms, which these are not.
8. **Both window ends are read by `read_moment`** — there is no bare-number-of-days shortcut (the Dates end box's
   `read_end`), and no blank-means-for-ever: a missing end is refused 422 `needs_both` in words (*"A ping window needs
   a start AND an end…"*). Backwards reuses `spotlight_end_before_start`; unreadable reuses `spotlight_bad_date`.
9. **The window-open flip is detected on the Twitch poll path only** (`_seen`). A session a YouTube probe opened still
   goes through the gate at its announcement (`announce_info` is the one door both sweeps use), but no window-open
   reminder is posted for it.
10. **A window-open reminder that fails to post is not retried.** The flip is recorded before the post (checklist 12),
    so a failure is one `golive.spotlight_post_failed` row and the next poll does not try again — otherwise a missing
    channel would retry every tick for the whole window.
11. **A row leaving the list takes its windows with it** (`delete_channel`), marathon ones included — Remove, expiry
    and an event cancel all go through it. Windows are otherwise never deleted by time except by the keep sweep.
12. **The Discord card draws at most FIVE window lines** (`WINDOWS_SHOWN`) — the embed description is capped at 4,096
    characters and already carries up to 25 channel lines. The Remove select still lists up to 25.
13. **The route rows carry one extra field, `pinging`** (the gate's answer now), and the two window WRITE routes
    answer with the whole spotlight row (+ `window`, or `removed` / `window_id`) so the drawer can redraw from one
    answer. DELETE of a marathon window is **409** `not_staff_window`; a window on another row or already gone is
    **404** `no_window`; an unknown mode on PATCH is **422** `bad_mode`, checked before anything is written.
14. **KI-36 ride-along TAKEN.** `site/mock/golive-join.test.mjs` no longer hand-types its key list or its count: it
    reads `Object.keys(contract.json settings.help)`, which `tests/api/test_contract.py` already pins to the
    registry's golive / pings / youtube keys. The Python guard `test_the_golive_page_still_draws_seventy_one_keys` is
    still a hand-typed number (bumped 62 → 71); that one only ever conflicts loudly, it cannot drop a key.
15. **Discord shows the state line only for the PICKED channel** (`**login** · Pings: …` under the list), not on every
    list line, to keep the 25-line list inside the embed.
16. **Sweep rows are lettered `PW-a` … `PW-e`**, the convention every section since `SD` uses (*"Rows lettered; the
    conductor numbers them"*), rather than numbered after 739.

## What was NOT verified

- ⚠️ **Nothing met Discord or Helix.** The announcement / bump mention sets, the window-open reminder, the panel
  buttons, the modal and the Remove select were exercised only against the suite's fakes (`FakeChannel`, `FakeHelix`,
  `FakeInteraction`); Discord's own rendering, its component-row limits and its modal label limits were not.
- ⚠️ **No browser rendered the Go-live page.** The Pings card, the segment, the Add-a-window dialog and the Announced
  suffix were checked by `node --check`, the join test (`pingSuffix` and the fixtures), `check.mjs` (shapes of all 219
  mock routes) and hand `curl`s against the mock on port 8792 (PATCH mode, POST/DELETE window, the three refusals,
  one `web.golive.spotlight_ping_mode_set` row for a mode-only PATCH). Nobody clicked anything.
- **The schema 59 migration** was proven on a fresh file and on a file downgraded to 58
  (`tests/storage/test_db.py::test_a_schema_58_file_gains_ping_mode_windows_and_the_session_gate`), not on the live
  volume.
- **Real time**: the reminder was tested by calling `poll_once` twice, not by waiting a poll interval on Fly; nor under
  `spotlight_mode = shadow` against the real shadow channel.
- **The marathon schedule** does not exist yet: `source = 'marathon'` windows were only ever seeded by hand in tests.
- **Timezones** beyond UTC and America/Phoenix in the pure tests; the mock's `windowWhen` is Intl-based and was eyeballed
  once (*Sep 30 00:05*-style parts), not tested.
- **Cost per poll**: `pings_for` is one `SELECT` of a row's windows per announce, bump and live row per tick; not
  measured, assumed small beside the Helix call.
