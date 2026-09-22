# A spotlight is a DATE RANGE — a start as well as an end

> **Audience:** whoever touches a spotlight's dates next, and the reviewer.
> **Status:** TRACKED · ✅ **LIVE as v155** — merge `fad98c9e` (branch `spotlight-dates`, off
> `main` `f560ffa0`), release commit **`a285afc7`**, deployed **2026-09-22 13:35** Phoenix
> (**20:35:31Z**); `release.json` answers `v155` at `6d5f5841`. `spotlight_mode`
> is untouched and still ships **shadow**; no key was flipped.
> **Last verified: 2026-09-22 (the deploy)** — the migration ran itself on boot: the log line
> `database: added spotlight_channels.starts_at` at **20:35:23Z**, then `database ready`
> 20:35:23Z, `synced 33 app commands`, `logged in as Black_Bloc` **20:35:26Z**, no Traceback;
> `/health` ready 20:35:58Z; `release.json` **v155** at `6d5f5841`; and the operator read of
> `GET /api/golive/spotlight` (20:36:11Z) answers **`starts_at` on all four live rows** — all
> `null`, i.e. *started already* — beside the new derived `scheduled` (false on all four) and
> `range` fields, which is the live proof that both the column and the route change shipped.
> The v155 deploy gate was green on the FIRST run: **7,316 passed + 3 skipped**, ruff clean,
> `check.mjs` ok 21 pages / 198 routes, six node tests green.
> ⚠️ **NOT checked at the deploy:** nothing met Discord (below is still true in full), no
> browser rendered the live Go-live page or the new Settings drawer, `check.mjs` was not
> re-run after the deploy, and no `starts_at` has ever been WRITTEN live — the operator read
> is read-only. Before that, **2026-09-22 (the branch)** — measured on the branch: `pytest -n auto` **7,316 passed +
> 3 skipped** (7,253 + 3 on `main` at the v154 gate; collected **7,256 → 7,319**, so **+63**
> tests), `ruff check black_bloc tests site`
> clean, `node site/mock/check.mjs` **ok — 21 pages, 198 routes, 24 core settings, all keys
> present** against a mock on `MOCK_PORT=8791`, all six node tests green, and the Go-live and
> Settings pages RENDERED in `chrome-headless-shell` 149.0.7827.22 over raw CDP against that
> mock (what was seen is under [What was verified](#what-was-verified)).
> `SCHEMA_VERSION` **52 → 53**, registry **299 → 307** keys, `/api/golive/spotlight` routes
> unchanged in COUNT (the three that existed gained fields).
> ⚠️ **NOT verified:** **nothing here has met Discord or Helix.** The live site and a real
> database HAVE now been met, but only as far as the deploy reached: the column exists on
> `/data/black_bloc.sqlite3` and the live route serves `starts_at` + `scheduled` — no modal has
> been opened, no **Set dates…** pressed, no date SAVED, no backwards range refused in
> production, and no scheduled row has reached its start, so `golive.spotlight_started` has
> never been logged for real. See [What was NOT verified](#what-was-not-verified). Sweep rows
> `SD-a` … `SD-d` in [`../access/sweeps.md`](../access/sweeps.md) are the proof that does not
> exist yet.
>
> Companions: [`spotlight-design.md`](spotlight-design.md) is the feature this extends (the
> row, the poll, the three posts, the expiry); [`channel-streamers-design.md`](channel-streamers-design.md)
> is why the row is the CHANNEL record and `spotlight` is a toggle on it;
> [`when-picker-design.md`](when-picker-design.md) and
> [`when-picker-site-design.md`](when-picker-site-design.md) are the two date-entry
> conventions this follows — and the site one's **audit row #12** named this build as the
> thing that would turn the spotlight's *Days to keep it* number box into a real picker.

## 1. The ask, verbatim (owner, 2026-09-22 10:29 Phoenix)

> *"in golive when i set a spotlight i can extend a week or keep forever. let me set a date
> range for start and end time"*

What existed: a `spotlight_channels` row had **`expires_at`** only (NULL = kept for ever), and
the moves were **Extend a week** / **Keep for ever** / **Let it expire**. There was no way to
say *"this marathon starts on the 25th"* — a row added early started being announced the
moment the channel next went live.

## 2. The model — one nullable column, and one new state

| | |
|---|---|
| **The column** | `spotlight_channels.starts_at`, `TEXT` ISO UTC, nullable, through the `ADDED_COLUMNS` list. `SCHEMA_VERSION` **52 → 53**. **NULL means started already**, so every row that exists today keeps behaving exactly as it did — that is the whole reason the column is nullable rather than defaulted. |
| **The state** | A row whose `starts_at` is still ahead is **scheduled**. It is on the list, it is watched, staff can see and edit it — and **nothing of its is announced, pinned or reminded** until the start has passed. |
| **The range** | `starts_at` + `expires_at` read together: *from 25 Sep to 30 Sep*, *from 25 Sep · kept*, *until 30 Sep*, *kept*. The last two are exactly today's wording, which is what a row with no start still shows. |
| **Expiry** | Unchanged. `is_expired` never looks at the start. |

### What the poller does

`Spotlight.poll_once` gained one call, `sweep_starts(guild, rows)`, beside `sweep_expiries`:

- **`_seen` gates the ANNOUNCEMENT, not the row.** If a row is scheduled *and has no open
  session*, `_seen` returns before anything — no session opens, nothing is posted, nothing is
  pinned, no reminder is due. If a session **is** open, the tick runs as it always did.
- **`sweep_starts` writes one `golive.spotlight_started` row** the first tick after a start
  passes. It is **ROUTINE** (registered in `logkinds.ROUTINE` beside the rest of the
  `golive.spotlight_*` family, which the owner made quiet on 2026-09-21), so nothing about it
  reaches `#blackbloc-logs` at the default level.

## 3. Where a date is typed, and how it is read

| Door | The two boxes | Read in |
|---|---|---|
| **Discord** — `/golive` ▸ **Channels…** ▸ **Add a channel** | `Starts` / `Ends`, typed `YYYY-MM-DD` or `YYYY-MM-DD HH:MM` (⚠️ the **Ends** box also still takes a bare number of days) | the person's own stored zone, falling back to the guild's `default_timezone` |
| **Discord** — the same panel's **Set dates…** button on a picked row | the same two boxes, **pre-filled** with what is stored | the same |
| **The site** — the Go-live page's row drawer ▸ **Dates** card | two `ui.js:whenField` pickers (`datetime-local` + a 24-name zone select) and **Save dates** | the zone the picker's select is on, sent as `tz` |
| **The site** — **Spotlight a channel** | the same two pickers; **Ends** opens on today + `spotlight_default_days` | the same |

**Every blank means something, and nothing refuses a blank:** a blank **Starts** is *now*, a
blank **Ends** is *for ever*. Both are stored as NULL.

⚠️ **A start already gone by is ACCEPTED and stored exactly as typed** — it is never silently
rewritten to "now", and it is never refused. The only thing refused is a range that runs
backwards, and a date nobody can read.

The pure half lives in `black_bloc/spotlight.py`: `is_scheduled`, `range_words`,
`announced_words`, `typed_moment`, `read_moment`, `read_end`, `range_problem`,
`bad_date_said`, `end_before_start_said`, `dates_said`, plus the label/word readers. The cog's
`read_dates` + `set_dates` are the ONE door the modal, the drawer and the route all pass
through — the validation has a single home.

## 4. The routes

| Route | What changed |
|---|---|
| `GET /api/golive/spotlight` | each row gains `starts_at`, `scheduled` (bool), `range` (the worded range) and `announced` (the Announced cell, with the scheduled word on it). `until` and `kept` are unchanged, so nothing that read them broke. |
| `POST /api/golive/spotlight` | takes `starts_at` and `expires_at` as dates, plus `tz`. `days` and `keep` still work unchanged. |
| `PATCH /api/golive/spotlight/{id}` | takes `starts_at` (a null or a blank CLEARS it) and `expires_at` as a date, plus `tz`. |
| both | **422 with the WORDS** on a backwards range (`end_before_start`) or an unreadable date (`bad_date`). Never a bare status — the page prints the sentence. The staff gate is untouched. |

## 5. Eight new words, and all eight are keys

Standing rule (owner, 2026-09-17): *every word the bot posts is editable on the site.* Each of
these is a registry entry in `settings_store.py` with `NAMESPACE_OVERRIDE → golive`, a plain
help line, a `labels.js` label, a mock row and a `contract.json` help entry.

| Key | Default | Fills |
|---|---|---|
| `spotlight_range_template` | `from {start} to {end}` | `{start}`, `{end}` |
| `spotlight_range_kept_template` | `from {start} · kept` | `{start}` |
| `spotlight_scheduled_word` | `scheduled` | — |
| `spotlight_dates_button` | `Set dates…` | — |
| `spotlight_starts_label` | `Starts — blank means now` | — (clamped to 45 chars, Discord's modal-label cap) |
| `spotlight_ends_label` | `Ends — blank means for ever` | — (same clamp) |
| `spotlight_end_before_start` | the backwards-range sentence | `{start}`, `{end}` |
| `spotlight_bad_date` | the unreadable-date sentence | `{given}` |

Validators refuse a placeholder the renderer cannot fill, and refuse ANY placeholder in the
four that stand in for nothing. A template that somehow still fails to render falls back to the
shipped default rather than showing an empty cell.

They live in their own named Settings drawer on the Go-live page, **What a spotlight's dates
say** (`golive-join.js:DRAWERS`), so the *Everything else* catch-all stays empty — which is
what `golive-join.test.mjs` asserts. The namespace count went **54 → 62**.

## 6. Decisions this build had to make (the brief left each one open)

1. ⚠️ **The Add-a-channel modal's `days` box was REPLACED, not joined.** Discord caps a modal
   at **five** components and the form already held four (channel, spotlight yes/no, YouTube,
   days). Starts + Ends would have made six. So the **Ends** box takes *either* a date *or* a
   bare whole number of days — `spotlight.read_end` tries the number first. The old gesture
   ("7") still works, there is no second field to disagree with, and the brief's "a typed end
   wins over days / refuse when they disagree" question never arises.
2. **A scheduled row with an OPEN session is left alone.** `_seen` gates the announcement only.
   Setting a start on a channel that is live right now would otherwise strand the post that is
   already out (no end, no unpin, no past-tense edit). The row goes quiet at the *next* start,
   not by abandoning the current stream. Guarded by
   `test_a_start_set_mid_stream_never_strands_the_announcement_that_is_out`.
3. **`golive.spotlight_started` is remembered in MEMORY, not on the row.** `Spotlight.scheduled`
   is a set of ids the process has SEEN as scheduled; a row only logs *started* when it leaves
   that set. The alternatives were worse: clearing `starts_at` at the start would destroy the
   range the drawer shows, and a `started_at` column would be a second schema change for one
   log line. The cost, stated plainly: **a restart between a row being scheduled and its start
   passing means that row's `started` line is never written.** Nothing depends on the line —
   the announcement is driven by `is_scheduled`, which reads the clock.
4. **A start in the past is stored as typed.** The brief said "accepted, do not silently
   rewrite, never refuse" and that is exactly what `read_moment` does. `range_problem` only
   compares the two dates with each other, never with now.
5. **`range_problem` treats end == start as backwards.** A zero-length range is a row that
   expires the instant it starts, which is indistinguishable from a mistake.
6. **Extend a week and Let it expire now go through `set_dates`.** Both compute a new END, and
   on a row with a far-off start either could land before it. They get the same refusal as a
   typed one rather than quietly writing a backwards range.
7. **The site's Add form is the "Spotlight a channel" drawer, not "Add a streamer".** The brief
   said "*Add a streamer* for a channel-with-no-member: the *until* field becomes Starts +
   Ends". There is no until field on **Add a streamer** — it takes a member and a login and
   nothing else. The *Days to keep it* box the brief means is on **Spotlight a channel**, and
   that is where the two pickers went. The channel-with-no-member path through **Add a
   streamer** sends no dates, so it takes the defaults, exactly as before.
8. **The Announced cell now says something for a spotlight row that is not live.** It read
   *ready* before; it now reads the range and badges a scheduled row. The `Expires` column
   reads the range too, so a row with a start no longer shows only its end. A row whose
   spotlight is OFF still reads `—`.
9. **A new filter chip, *Scheduled*, beside *Spotlight*.** The brief asked that the Spotlight
   chip include a scheduled row, which it does (`spotlightChip` never looked at the dates).
   The extra chip is what makes "what have we got queued up" one click.
10. **Placeholders are NOT keys.** `2026-09-30 19:00` and `2026-10-07 23:00, or 7` are examples
    of the SHAPE, not wording, and the file's existing placeholders (`gamesdonequick`,
    `@GamesDoneQuick`) are constants for the same reason. Named here so the next audit does not
    re-open it.
11. **The mock reads a zoned naive stamp with `Intl`, twice.** `site/mock/server.mjs` has no tz
    database; `zonedInstant` asks what the wanted zone's clock reads at a guessed instant and
    corrects, which converges in two passes for every real offset. It mirrors
    `timezones.parse_start` closely enough for the contract, and it is the mock, not the bot.

## 7. Follow-ups — named, not built

1. ⚠️ **Event-created spotlights keep `starts_at` NULL.** `POST /api/events/{id}/spotlight` and
   the event card's **Spotlight this stream** still set only `expires_at` (the event's end plus
   `spotlight_event_slack_hours`). Giving them the event's START is one argument and is the
   obvious next move — deliberately out of scope here, because it changes what an approved
   event does the moment it lands and deserves the owner's word first.
2. ⚠️ **The spotlight panel's OTHER labels are still constants**, not keys: `Extend a week`,
   `Keep for ever`, `Let it expire`, `Bump now`, `Remove`, `Spotlight on` / `off`, `Opt out` /
   `Opt back in`, the panel intro and the `Add a channel…` button. This build keyed the words it
   ADDED and did not widen scope to re-key the ones that were there. A one-pass job for whatever
   touches that file next; the pattern to copy is §5.
3. **The site's row drawer and the Discord panel print the range through different code.** The
   page reads the route's `range` / `announced` strings (so the keys reach it), but the
   drawer's `spotlightSaid` still composes *Runs out X. Starts Y.* from raw timestamps with the
   page's own `when()`. One of the two should go; the route's worded fields are the one to keep.
4. **`spotlight_default_days` still drives the site's Ends default only.** The Discord Add modal
   opens with both boxes BLANK, which means *now* and *for ever* — not *now* and *seven days*.
   That is deliberate (a blank box that silently means seven days is the thing the owner's ask
   was about), but it is a difference between the two doors and is written down here so nobody
   "fixes" one to match the other by accident.

## What was verified

**Measured 2026-09-22 on this branch, all local:**

- `pytest -n auto -q` — **7,316 passed, 3 skipped** (the 3 are KI-31, the absent voice-receive
  extension). `main` at `f560ffa0` collects **7,256**; this branch collects **7,319**, so this
  build adds **63** tests. The v154 gate on `main` read 7,253 + 3.
  ⚠️ The suite needs a CLEARED environment (`ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `TWITCH_*`,
  `POLL_VOTE_SECRET`, `DEV_GUILD_ID` unset) or the nine "no key" tests go red —
  [`../access/testing.md`](../access/testing.md).
- `ruff check black_bloc tests site` — clean.
- `node site/mock/check.mjs` against a mock on `MOCK_PORT=8791` — **ok, 21 pages, 198 routes,
  24 core settings, all keys present**.
- All six node tests green, including `golive-join.test.mjs` with the new scheduled fixture and
  the 62-key placement assertion.
- ⚠️ **Falsified first:** `test_a_scheduled_row_is_not_announced_before_its_start` and
  `test_a_start_that_passes_leaves_one_routine_started_row` both FAIL on the un-fixed cog
  (guard removed, re-run, 2 failed / 5 passed). The tests bite.
- **Rendered** in `chrome-headless-shell` 149.0.7827.22 over raw CDP against that mock:
  - `/golive.html` — the seeded scheduled row **GDQ Hotfix · channel only** is in the Streamers
    list, a **Scheduled** filter chip is beside the others, the range wording is on the page,
    **zero console errors**.
  - **Spotlight a channel** — labels `The name after twitch.tv/`, **Starts**, **Ends**; the two
    date boxes are `datetime-local`, Starts blank, Ends pre-filled `2026-09-29T10:59` (today +
    7, the key's default), each with a 24-option zone select, each help line ending *Read in
    America/Phoenix.*
  - **the GDQ Hotfix row's drawer** — seven cards, `Spotlight` · **`Dates`** · `Twitch` ·
    `YouTube` · `Ping role` · `Announcements` · `Remove`; the Dates card holds both pickers
    pre-filled from the row and a **Save dates** button; the card's line reads *Scheduled — its
    start has not arrived, so nothing of its is announced, pinned or reminded yet.*
  - **the refusal, end to end** — typing Starts `2026-12-20 10:00` and Ends `2026-12-01 10:00`
    and pressing **Save dates** printed, in the drawer:
    *"That range ends before it starts — 1 Dec comes before 20 Dec — so nothing was changed. Put
    the end after the start, or leave the end blank to keep the channel on the list for ever."*
    Correcting Ends to `2026-12-28` and pressing it again printed *"gdqhotfix runs from 20 Dec
    to 28 Dec. Nothing of its is announced, pinned or reminded before that start — the row sits
    on the list until then."* The 422 shows in Chrome's network log and **not** to the person.
  - `/settings.html` — all **eight** new keys are present as `[data-key]` rows (306 keys drawn),
    zero console errors.

## What was NOT verified

> 📌 **Amended 2026-09-22 at the v155 deploy (13:35 Phoenix / 20:35Z).** Two of the bullets
> below were written on the branch and the deploy has since answered them — they are marked
> ✅ in place rather than deleted, so the reading and its date stay visible. **The other three
> stand unchanged**, and the first two are the ones that matter: nothing has met Discord or
> Helix.

- ⚠️ **Nothing here has met Discord.** No modal was opened, no **Set dates…** button was
  pressed, and no spotlight has been announced, skipped or started anywhere but in the suite
  against `FakeInteraction` / `FakeHelix`. `../access/testing.md` says it plainly: no API can
  click a Discord button.
- ⚠️ **Nothing has met Helix or a real clock.** Every scheduling test moves `starts_at` in the
  database and polls again. No start has actually arrived while the bot was running, and
  `golive.spotlight_started` has never been written by a real tick.
- ✅ **ANSWERED at the v155 deploy — ~~The migration has not touched a real database~~.** It
  has now: the boot log says `database: added spotlight_channels.starts_at` at **20:35:23Z**
  and the Fly volume is at schema **53**. The argument held — one additive nullable column
  through `ADDED_COLUMNS`, applied by `Database.connect` on boot, no backfill — but it is a
  measurement now, not an argument. *Was, on the branch:* Schema 53 was applied in the suite's
  `tmp_path` files only; the Fly volume had never seen the column.
- ✅ **PARTLY ANSWERED at the v155 deploy — ~~The live site was never opened~~.** The live API
  was **read**: `GET /api/golive/spotlight` through `scripts/read.ps1` (20:36:11Z) answers
  `starts_at` on all four live rows — all `null`, i.e. *started already* — beside `scheduled`
  (false) and `range`. ⚠️ **No BROWSER has rendered the live page**, the real `/api/settings`
  was still never read, and every browser measurement above is still this branch's mock.
- **Nothing was checked in a browser that is not Chromium**, no screenshot was taken, and no
  narrow-width layout check was made of the two-picker `formrow`.
- **Decision 3's cost was not exercised**: no process was restarted between a row being
  scheduled and its start passing, so the missed `started` line has been reasoned about and
  not observed.
- **`spotlight_mode` was not flipped** and nothing was deployed. `deploys.log`, `release.json`
  and `TEST_MODE` are untouched.
