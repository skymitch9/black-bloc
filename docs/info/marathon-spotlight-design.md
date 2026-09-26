# The spotlight follows the marathon — a running marathon spotlights its channel, and pings need the spotlight

> ✅ **2026-09-26 15:53 — LIVE as v174** (release `7a505098`, merge `9f343f75`; boot adds both schema-69 columns, no Traceback — `deploys.log`'s v174 line). No live `marathon.spotlight_set` yet; sweeps `MSP-a…d` are the owner's.

> **Audience:** the conductor, reviewers, and the next session touching marathons or spotlight pings.
> **Status:** TRACKED · 🔨 **BUILT on branch `marathon-spotlight` (off `main` `bbdfb390`), NOT merged, NOT deployed.**
> Schema **68 → 69**, registry keys **493 → 497**, four new log kinds, eighteen deviations below.
> **Last verified: 2026-09-26** — against the branch's own code by the tests (`tests/test_marathon_spotlight.py`,
> `tests/cogs/content/test_marathon_spotlight.py`, the API tests), `check.mjs` on a worktree mock (`MOCK_PORT=8810`:
> *22 pages, 253 routes*), and a headless Chrome render of `events.html#marathon-1` and `golive.html` (zero console
> errors). ⚠️ **NOT checked:** anything against Discord, the live database, the live channel rows (the conductor's
> 13:3x audit is the only reading of them), and the real bot was never run. Secret NAMES only.

## The asks, verbatim (owner, 2026-09-26 13:2x–13:3x Phoenix)

1. *"We also need to add a way to spotlight to match a marathon if that's not already happening"*
2. *"spotlight should only be on for the stuff that's been set to expire this week or GDQ which is perma"*
3. *"Ping marathon when a marathon is going, the channel is in spotlight, and the marathon for that channel is not set
   to opt out"*

**What happened before this build.** A marathon with a channel kept ONE `source='marathon'` ping window on that row
(`cogs/content/marathon.py:sync_window`); it never touched the row's `spotlight` flag. So an unspotlit channel got no
pin and no reminders during its marathon — and, as §B found, its go-live announcement still pinged inside the window.

## B. The ping rule — confirmed, with one gap closed

The owner's three criteria are **`ping_mode = events` on a channel whose marathons follow** — true after this build,
**not before it**:

- **The gate.** Every role mention a channel row makes goes through `black_bloc/spotlight.py:879` `pings_now`. With
  `events` it now answers `is_spotlit(row) and open_window(...)` (`:885`). Its callers: the go-live announcement
  (`cogs/content/spotlight.py:758`, through `pings_for` `:363`), the bump (`:887`, which also needs the spotlight at
  `:857`), the window-open reminder (`:719`, spotlight required at `:727`), the boot reconcile (`:529`) and the
  mode change (`:1856`) that record the answer, and the marathon reminder's channel role
  (`cogs/content/marathon.py:2282`).
- ⚠️ **The gap (Deviation 5).** `announce_info` (`cogs/content/spotlight.py:752`) announces EVERY row that takes
  announcements, spotlit or not — the spotlight only decides the pin and the reminders. Before this build an
  unspotlit `events` row pinged on its go-live announcement inside a window, so criterion 2 (*"the channel is in
  spotlight"*) was not enforced. The one line at `:885` closes it; `always` and `never` are untouched.
- **A marathon's window is the only window a feed-found marathon makes.** `spotlight_ping_windows` is written in two
  places only: staff **Add a window…** (`cogs/content/spotlight.py:329` `add_window`) and `sync_window`
  (`cogs/content/marathon.py:1999`, the INSERT at `:2047` with `source = WINDOW_MARATHON`). A feed-found marathon is
  created and read through the same `create_marathon` → `refresh` → `sync_window` path, so it makes exactly one
  window. (A STAFF window on the same row also opens pings — that is staff's say, and the only way "exactly" bends.)
- **An opted-out channel's marathons make no window.** Opting out runs `hold`
  (`cogs/content/marathon_channels.py:67`): every active marathon on the row is paused (`:86`) and re-synced (`:88`),
  and `sync_window` drops the window of an inactive marathon (`keep` at `cogs/content/marathon.py:2009`). Adding a
  marathon to, or moving one onto, an opted-out channel is refused; `seed_feeds` skips it.
- **"A marathon is going"** is the window (the run span ± `marathon_window_slack_hours`), and now the spotlight too
  (§A), so all three hold together while it runs.

## A. The design, as built

**Model.** `marathons.spotlight_mode TEXT` (`follow` / `off`; NULL reads as follow) and — Deviation 1 —
`spotlight_channels.spotlit_by_marathon INTEGER` (the marathon holding a spotlight it turned on). Both through
`ADDED_COLUMNS`, schema **69**, no backfill.

**Keys (four, Marathons group, registry + mock row + label):**

| Key | Type | Default | What |
|---|---|---|---|
| `marathon_spotlight` | bool | on | while a marathon on the list is running, its channel is spotlit and the spotlight expires at its end |
| `marathon_spotlight_lead_minutes` | int 0–240 | 15 | minutes before the first run that the spotlight turns on |
| `marathon_channel_ping_mode_default` | enum `always`/`never`/`events` | `events` | the pings a NEW seeded marathon channel row starts on |
| `marathon_channel_ping_help` | text | *On a marathon channel, During events pings only while one of its marathons is running — the marathon sets that window from its schedule, and the channel is spotlit for it.* | the help line on a marathon channel's Go-live Pings card |

**The follow** (`black_bloc/marathon_spotlight.py:plan`, pure; written by
`cogs/content/marathon_spotlight.py:follow_spotlight`). Runs after every successful schedule read (`refresh`, beside
`sync_window`) and on every minute tick of an active marathon. It acts when the key is on, `marathon_mode` is not
`off`, the marathon is active and following, the row takes marathons, and the span (first run's start → last run's
end) holds now or starts within the lead:

| The row | What happens | Log |
|---|---|---|
| spotlight ON, no expiry (*kept* — GDQ) | nothing | nothing |
| spotlight ON, expiry at or after the span end | nothing | nothing |
| spotlight ON, expiry before the span end | `expires_at` = span end (not marked — staff's row) | `marathon.spotlight_extended` (routine) |
| spotlight OFF | `spotlight = 1`, `expires_at` = span end, `spotlit_by_marathon` = the marathon; a live stream is pinned | `marathon.spotlight_set` (**important**) with the marathon and the span |

**The end.** The ONE expiry sweep (`cogs/content/spotlight.py:sweep_expiries`) lifts a held row — spotlight off,
`expires_at` NULL, holder NULL, a live post unpinned, `marathon.spotlight_lifted` (`because: marathon_over`) — and
purges every other expired row as before.

**Staff final say.**
- **Spotlight off** on the row (Go-live PATCH or `/golive` ▸ Channels…) while a following marathon on it is in reach
  sets that marathon's `spotlight_mode = off` (`marathon.spotlight_mode_set`, `because:
  staff_turned_the_spotlight_off`) and the answer adds *"**AGDQ 2027** will not spotlight it again."* A row the
  marathon held also gives back its dates.
- **The per-marathon switch** — the drawer's Settings foldout *Spotlight the channel while it runs* On/Off (rides
  Save; `PATCH /api/marathons/{id}` `spotlight_mode`) and the `/event` ▸ Marathons… card's one button (*Stop
  spotlighting it* / *Spotlight while it runs*, plus a state line beside the channel). Off lifts a spotlight this
  marathon holds; On spotlights at once when in reach.
- **Staff dates** on a held row (Dates, Keep, Let it expire, Extend) clear the holder: the row is theirs.
- **Per channel:** the existing Go-live **Marathons: off** — an opted-out channel is never followed.

**New channel rows** (`cogs/content/spotlight.py:spotlight_channel`, every door): a row whose login a marathon feed is
seeded for (`marathon_feeds.SEEDS`), and that takes marathons, starts on `marathon_channel_ping_mode_default`; every
other row keeps `spotlight_ping_mode_default`. No existing row is changed by code.

## Deviations

1. ⚠️ **The expiry sweep PURGES a row; it does not turn a spotlight off.** Verified: `sweep_expiries` →
   `_expire` → `delete_channel`, `drop_fan_role`, `drop_feeds_of_channel`. A marathon writing `expires_at` on SS4C or
   RPGLB would have deleted the row, its ping role and its feed at the marathon's end. Built instead: the holder
   column `spotlight_channels.spotlit_by_marathon` (a second column in the same schema bump) and one branch in the
   SAME sweep that lifts a held row back to off-and-kept. No second sweep.
2. **`starts_at` is never written.** On this code `starts_at` gates the row's whole ANNOUNCEMENT (`_seen` returns
   before announcing while `is_scheduled`), not only the spotlight — writing the span start would silence a channel
   that is announced today for the lead minutes. The spotlight is simply on from `lead` before the start.
3. **The follow also runs on the minute tick**, not only after a fetch: reads are 30 minutes apart while near, so a
   15-minute lead could be missed entirely. Idempotent — a second pass logs nothing.
4. **Shadow does not hold it back; `marathon_mode = off` does.** The ping window is written in shadow too, and the
   spotlight's own posts follow `golive_mode`. ⚠️ Live `marathon_mode` is `shadow`, so after deploy a running
   marathon spotlights its channel for real.
5. ⚠️ **`pings_now` for `events` now needs the spotlight** (§B). Side effect, intended: a spotlight turning on inside
   an open window flips the remembered gate, so a channel that is already live gets the one window-open reminder
   (pinged) at that moment — the marathon's first ping on a 24/7 channel. The existing test
   `test_a_window_opening_on_a_live_channel_with_spotlight_off_posts_nothing` now asserts the recorded answer is 0.
6. **The mode words are the code's `always` / `never` / `events`**, not `windows` — `PING_MODES` is one home.
7. **`marathon_channel_ping_mode_default` keys on the seeded logins**, read in `spotlight_channel` (so the Go-live
   add route, the bot's Add a channel modal, the event card and the People card all agree). The brief's "channel-only
   with marathons on" would match every new row — `marathons` defaults on — and put every streamer channel on
   `events` with no window, silencing it. ESA (`OPTED_OUT_SEEDS`) counts as not taking marathons.
8. **The lead is its own key.** `marathon_ping_minutes` (15) is the run reminder that pings — reusing it would make
   one knob move two things; `marathon_spotlight_lead_hours` (2 h) is the People card's RUNNER-channel lead. The new
   key mirrors `marathon_ping_minutes`' default and range.
9. **An earlier expiry carried to the end logs `marathon.spotlight_extended`** (routine) and leaves the row unmarked
   — staff's row, so it is purged at the new date as staff's dates always were, just later.
10. **The span is the run span, without the window's slack.** The window stays ± `marathon_window_slack_hours`.
11. **Staff turning off a held row clears its dates**, so a later **Spotlight on** is an ordinary kept spotlight,
    not a hidden purge date.
12. **Removing, pausing or re-channelling a marathon mid-span leaves the spotlight it set** until the span end, when
    the sweep lifts it. The per-marathon switch (Off) lifts it at once.
13. **The key turned off does not lift** spotlights already set; they run to their end.
14. **The answer sentences are constants** in `black_bloc/marathon_spotlight.py` (panel and page words, the repo's
    pattern); the one sentence shown ON a row, the Pings help line, is the key. Nothing new is posted to a channel.
15. **The drawer switch shows on a marathon with no channel** too; the setting is kept and applies once a channel is
    picked. The Discord card draws its button only with a channel.
16. **The mock stores the switch and its words only** — it has no tick, so it never spotlights a channel by itself.
    It mirrors the gate, the new-row default and `ping_help`.
17. **`tests/cogs/content/test_spotlight.py`'s fixture pins `marathon_channel_ping_mode_default = always`**: its
    fixtures add `gamesdonequick`, which is now a seeded marathon login; the tests are about the general default.
18. **A race is closed, not tested concurrently**: a tick could re-spotlight between the staff write and the hook;
    the hook re-reads under the marathon lock and lifts. The sequential tests cover the hook, not the interleaving.

## What was NOT verified

- **Nothing met Discord.** The `/event` ▸ Marathons… button and state line are tested at `card_moves` and by
  import; the rendered panel was not seen. `/golive` ▸ Channels… *Spotlight off* was exercised through
  `run_spotlight_move`, not a real interaction.
- **The pin on turn-on with a live session** goes through the existing `_brighten`; the new tests do not register the
  spotlight cog with an open session, so the pin itself is covered only by the spotlight tests.
- **The live database migration** (schema 69) has not run. **The live rows** were not read by this build; the
  conductor's 13:3x audit says GDQ (kept), RGL and SS4C (until 28 Sep) are spotlit, ESA and RPGLB off.
- ⚠️ **Once staff add `fastestfurs`, `fastpacedevents` or `ladyarcaders`** (the owner's 12:5x rule — only staff do),
  their marathons WILL spotlight them while running unless the switch or the key is off — e.g. Fastest Furs Fall Fest
  2026-10-08 → 10-11. Not decided here; the conductor should say so to the owner.
- The browser render covered the drawer's Settings foldout (switch drawn, Off + Save answered and stored
  `spotlight_mode = off`) and the GDQ Pings card (help line drawn). No other page, no phone width.
