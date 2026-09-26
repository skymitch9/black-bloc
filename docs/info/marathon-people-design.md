# The source is a column, and a marathon opens on its people — BaF first, then everyone, each one linkable or spotlightable

> ✅ **2026-09-25 — LIVE as v166 19:30** (merge `afba30b2`; release commit `b06d4f1d`; boot `database ready` 02:30:22Z, `logged in` 02:30:27Z, no Traceback, `/health` 65 ms — `deploys.log`'s v166 line). Migration: schema **64 → 65**, `marathon_spotlights` is a NEW TABLE, so the boot log has no `database: added` line for it (it names added columns only); `SCHEMA_VERSION` 65 read at HEAD. Nothing has met Discord by hand; sweeps `MP-a`…`MP-f` are the owner's.
>
> ➕ **2026-09-25 (branch `marathon-drawer-lite`, 🔨 BUILT, NOT MERGED): the drawer is now two header lines · People · a shut *Settings for this marathon* · a Posts line · Read it now / Pause / Remove** — the Schedule, Event, The channel and Posts cards are gone. [`marathon-drawer-lite-design.md`](marathon-drawer-lite-design.md).

> 🔨 **BUILT 2026-09-25 on branch `marathon-people` (worktree `C:/lcw/bb-marathon-people`), NOT MERGED, NOT DEPLOYED** — see *Deviations* and *What was NOT verified* at the foot.
>
> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 17:1x Phoenix)
> — dispatches to Opus as branch `marathon-people` AFTER `shadow-home-per-feature` merges** (same files:
> `marathons-section.js`, the marathon cog cards). **Last verified: 2026-09-25 17:0x** against `main` `b5427c62`
> (v165 live; `marathon-ux` merged, not deployed): `site/public/assets/marathons-section.js` — the Marathons section
> after `marathon-ux` (the table *Marathon · Dates · State · BaF runs · Schedule · Event*, Add a marathon, the strip, the
> **Where marathons come from** foldout with the feed rows and the feed drawer), the marathon drawer (Schedule · Runs ·
> Who is who · Event · The channel · Posts · Pause / Remove); `marathon-words.js` (the reading line, `BAF`);
> `black_bloc/marathon.py` (`match_people`, `people_of`, `is_ours`, the `people` JSON per run: `[{name, login, user_id,
> part}]`), `cogs/content/marathon.py` (the pairing routes' functions, `runs_of`), `api/tools/marathons.py`
> (`GET/POST …/{id}/people`, `DELETE …/people/{person_id}`), `cogs/content/spotlight.py:add_channel` `:110` and
> `spotlight_channel(...)` `:1223` (the one path that makes a channel-only row — login, dates, pin, note),
> `api/tools/golive.py` `POST /spotlight` (the same path from the site), `cogs/content/marathon_feeds.py` (the feed
> rows and drawer). Live: four GDQ marathons (unpublished), feeds GDQ + RPGLB. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 17:1x Phoenix)

*"hm for the events page maybe we need to get rid of there where marathon comes from and just put that as a column
in the marathons setion. we also need to be able to click into it and see which runners are running in a list with the
top section of that list set aside for BaF members. that way we can manually click other runners to link them and
mark them as BaF runners or just spotlight other runners"*

## A. The source is a column; the feeds lose their section

- The marathon table gains **Source** (after *Marathon*): *GDQ tracker* / *RPGLB tracker* / *horaro.net* / *Oengus*
  with *· feed* after it when a feed made the row (the words `marathon-words.js` already has). The **Where marathons
  come from** foldout goes.
- The feeds keep their controls, reached two ways and no longer a section: a **Sources…** quiet button beside **Add a
  marathon** opens a drawer listing the feed rows exactly as the foldout did (a row opens its feed drawer, unchanged);
  and the marathon drawer's Schedule line *found by the GDQ feed* becomes a link that opens that feed's drawer. The
  strip *N marathons have a next event waiting* stays; a feed's open suggestions render inside the Sources drawer.
- `/event` ▸ Marathons… ▸ Feeds… is unchanged.

## B. A marathon opens on its people

The drawer's order becomes **Schedule · People · Event · The channel · Posts · Pause / Remove** — *People* replaces
both *Who is who* and *Runs*, because it is what staff open the marathon for.

**Owner, 17:2x, verbatim:** *"we should also sort runners by days or something, so 2 list sections, a top list with BaF
members, a bottom list with all members with collapses by days/dates. This should help make it less unruly. Also we
should do it by timeslot/game slot. That way if its a 4 player race they share a row and we can click in to link them
instead of it being super long and hard to manage."*

**People** has two blocks:

1. **BaF** — a flat list, sorted by each person's NEXT run (on-now first, then soonest, then people whose runs are all
   done): *avatar · display name · @discord · twitch.tv/login · their runs as short chips (`Sun 12 Jan 15:15 Super Metroid`,
   the on-now one lit, done ones dimmed) · part*, and the moves **Unlink** (a pairing) / *matched by their Twitch link* /
   **Spotlight…** (below). Never folded; it is the point of the card.
2. **The schedule** — every SLOT (one row per run, races share the row), grouped by **day** in the guild's
   `default_timezone`, each day a `foldout` titled *Sun 12 Jan · 18 slots · 2 BaF* (today's day open, past days shut, future
   days shut unless they hold BaF — say so in Deviations if the rule is changed). A slot row: *15:15 · Super Metroid ·
   Any% · 0:43 · [Casey ✦BaF] [TheKing] [Peas ✦BaF] · runner chips first, then hosts/commentators in a quieter tone ·
   state* (on now lit, done dimmed, moved shows the old time). **Clicking a slot opens it** (a sub-view inside the drawer,
   or an inline expansion — the builder picks the one the site's `drawer` supports and says which): each person in
   that slot on their own line with **Link to a member…** (the pairing, pre-filled; the line turns ✦BaF at once, the
   run becomes ours) / **Unlink** / **Spotlight…** / *already on the Go-live page ↗*. A 4-player race is one row and one
   click, four lines inside.
   A filter box above the schedule matches names, logins and games and opens the days that hold a hit.

The Runs card is retired — the schedule block IS the runs view now (it carries everything Runs did: the moved-from
note, the states, and the staff run moves *Shout it now / Mark it upcoming / Mark it live* on the opened slot).

**Spotlight…** on any row (with a Twitch login) makes a channel-only spotlight row for that runner through the ONE
existing path (`spotlight_channel` / `POST /api/golive/spotlight`): login = theirs, starts = the marathon's start (or
the person's first run − `marathon_spotlight_lead_hours`, 2), ends = the marathon's end (or their last run's end +
`marathon_spotlight_slack_hours`, 2), spotlight ON (pinned + reminded while they stream, exactly as any spotlit
channel), announce ON, note *{name} at {marathon}*, `event_id` NULL; the marathon remembers it
(`marathon_spotlights(marathon_id, login, spotlight_id)`, a small table, so the row shows *Spotlit until 12 Jan* and
offers **Open on Go-live** and **Stop spotlighting** — which removes the channel row the same way the Go-live page
does). A runner already a channel row (any reason) shows *already on the Go-live page* and the open link instead.
Keys: `marathon_spotlight_lead_hours` (2, 0–48), `marathon_spotlight_slack_hours` (2, 0–48), `marathon_spotlight_note_template`
(*{name} at {marathon}*). Log `marathon.runner_spotlit` / `runner_unspotlit` (routine) beside the spotlight's own
`golive.spotlight_*` rows.

**`/event` ▸ Marathons…** gains **People…** on the picked marathon: the BaF block as lines (members see this block
and nothing more — *who from BaF is on, and when*), then, for staff, a day select → a slot select (time · game ·
people) → the slot view with a person select and **Link to a member…** (a `UserSelect`) / **Spotlight** — the same
functions. The marathon notice (§E of the shadow-home design) gains a **People…** button beside **Manage…** that opens
the same view, so linking happens from the notice too.

Routes: `GET /api/marathons/{id}/people` grows to answer the grouped people list (`baf[]`, `others[]`, each with
`name, login, user_id, member, parts, runs, done, live, pairing_id, spotlight_id, spotlight_until`) beside the pairings it
answers today; `POST /api/marathons/{id}/people/{login-or-name}/spotlight`, `DELETE …/spotlight`. Contract + mock rows
(AGDQ 2027: 3 BaF, ~10 others, one spotlit).

## B2. Suggestions folded in (Fable, 17:2x — the owner asked for them; each is small and rides here)

1. **Day headers count BaF** (*18 slots · 2 BaF*) so a busy day is visible shut.
2. **Near-miss names.** When a schedule is read, names that are one edit away from a Discord username (`Bobbeigh` /
   `bobbeigh`, `gz` / `gz_hero`) are shown in the slot view as *looks like @bobbeigh — Link?* (one click, the same
   pairing); the exact-username rule already links by itself.
3. **A race shouts once.** When two BaF people share a slot, the shoutout and the reminder name both and post once
   (verify `{member}` joins names; a test).
4. **The member view is the BaF block only** — `/event` ▸ Marathons… ▸ People… for a member answers *who from BaF is on
   and when*, nothing else; staff see the schedule below it.
5. **The notice carries People…** (above), because the moment a marathon appears is when staff want to link.
6. **Spotlight from the slot honours the slot's time**: a runner spotlit from a slot gets that run's window (lead/slack),
   from the BaF block their whole span; the design's §B already says both.

## C. Tests, docs, gate

`tests/test_marathon.py` (grouping people across runs, parts joined, BaF vs others, run counts), `tests/cogs/content/
test_marathon.py` (Link to a member moves the person into BaF and makes the run ours; Spotlight makes the channel row
with the marathon's dates through the spotlight path and remembers it; Stop spotlighting removes it; an existing
channel row is recognised; the panel's People… view), `tests/api/tools/test_marathons.py` (the grouped people answer,
the two spotlight routes, the staff gate, refusals in words: no Twitch login, already spotlit), `test_contract.py`,
`test_db.py` (the small table), the key/kind guards, the node tests (`marathon-words.test.mjs` for the source words),
`check.mjs`, a headless render of the drawer (People first) with zero console errors — LOOK at it. Both `pytest -n 8`
orders, `ruff`, ES parse. Docs: `code-notes.md`; this doc's foot; `architecture.md` (the table, the keys, the routes);
`docs/info/README.md` (one row); one dated line at the top of `marathon-ux-design.md` and `spotlight-design.md`;
`sweeps.md` rows `MP-a…` (a: the table's Source column; b: Sources… opens the feeds; c: a marathon opens on People
with BaF on top and the schedule by day below, today open; d: a 4-player race is one row and opening it lists four
people; Link to a member on one moves them into BaF and the board gains the line; e: Spotlight a runner → a
channel-only row on the Go-live page with the marathon's dates; f: `/event` ▸ Marathons… ▸ People…). NOT `TODO.md` /
`DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: one small table through the bootstrap.

## Deviations

*(build agent, branch `marathon-people`, 2026-09-25 — 🔨 BUILT, NOT MERGED, NOT DEPLOYED. Commits `3f270ed7` (Python:
table, keys, the people answer, Spotlight, the panel's People…, the notice's People…) and `b72c32a8` (the site and the
mock); docs in the commit after.)*

1. **The slot view is an INLINE EXPANSION**, not a sub-view: each slot is a native `<details class="mx-slot">` inside its
   day's `foldout()`. `openDrawer` has no view stack — a sub-view would replace the drawer body and lose the open day and
   the scroll. Opening a slot lists each person on their own line (name · ✦BaF · part · twitch.tv/login · how they
   matched · the moves), then the run's own staff moves (*Shout it now / Mark done / Mark it live / Mark it upcoming /
   Make it now / the event*, the retired Runs card's `runTools`). Open slots survive the redraw a move causes
   (`shown.slots`) and the slot a move came from is scrolled back into view (`shown.focus`).
2. **Two new modules, not a longer `marathon.py`**: `black_bloc/marathon_people.py` (pure — grouping, the BaF order,
   how a member matched, the near-miss rule, the spotlight span, days and slots, the words) and
   `black_bloc/cogs/content/marathon_people.py` (the table, `people_state`, `spotlight_runner`, `unspotlight_runner`, the
   panel's People views, the notice's `PeopleButton`). The tests mirror them (`tests/test_marathon_people.py`,
   `tests/cogs/content/test_marathon_people.py`) rather than the §C file names; the §B2.3 race tests did land in
   `tests/test_marathon.py` and `tests/cogs/content/test_marathon.py`.
3. **The spotlight's dates** read §B with §B2.6: from the BaF block, first run − `marathon_spotlight_lead_hours` → last
   run's end + `marathon_spotlight_slack_hours`; from a slot, that one run; the marathon's own dates only when the person
   has no run times at all. A start already gone by is stored as NULL (spotlit now) rather than a date in the past, and
   an end already gone by is **refused in words** (`runs_over`, 409) — a new refusal the design did not list.
4. **Pin follows `spotlight_pin`** (`spotlight_channel(pin=None)`), announce and spotlight are forced ON — "exactly as
   any spotlit channel". `spotlight_pin` defaults on, so the row IS pinned unless staff turned that setting off.
5. **`GET /api/marathons/{id}/people` changed shape**: a list of pairings → `{marathon_id, timezone, pairings, baf[],
   others[]}`. Nothing read the old list (the drawer reads `pairings` from `GET /{id}`). `timezone` (the guild's
   `default_timezone`) is what the site groups days by. Each person carries, beyond §B's list: `key`, `member_name`,
   `username`, `avatar_url`, `first_at`, `last_end`, `matched_by` / `matched_word`, `channel_id` (ANY Go-live row for
   their login), `spotlight_starts`, `looks_like`. `spotlight_id` is set only when THIS marathon remembers the row and
   the row still exists with that id — a row removed on the Go-live page is simply not shown as spotlit.
6. **"Who is who" is retired on the site with nothing lost**: a pairing for a name on the schedule shows on that person
   (*linked by staff · Unlink*); a pairing for a name NOT on the schedule (an every-schedule pairing, or a name the
   schedule dropped) lands in a foldout *Links to names not on this schedule · N* with Unlink, so no stored decision
   becomes unreachable (staff final say). The free-text *Pair a runner…* form is gone from the site — linking starts
   from a person on a slot, pre-filled. The panel keeps its *Pair a runner…*.
7. **Sources…**: the feed rows, *Add a feed…* and the open suggestions render inside a drawer titled with
   `sourcesTitle` (*Where marathons come from · 2 sources · next check in …*). Because that drawer is shut until pressed,
   a waiting suggestion also puts a strip line under the table — *1 new event from a source is waiting for staff:
   Sources…* — the `marathon-ux` Deviation 3 rule (a decision for staff is never folded away). A move made inside the
   drawer reopens it with the outcome.
8. **Open on Go-live** links `golive.html#streamers` (the Streamers section). The Go-live page has no per-row deep link;
   building one was out of scope.
9. **Link to a member… is offered for everyone a staff link did not decide**, members matched by their Twitch link or
   Discord name included (a staff link beats the automatic match — staff final say). The BaF block shows how each
   member matched and **Unlink** only when a pairing decided it.
10. **The panel**: members reach People… through a new root select *Who from BaF is on… pick a marathon* (a member had
    no marathon pick before); staff through **People…** on the card (row 4, beside Back). Staff: the BaF lines, then a
    day select (*Fri 25 Sep · 12 slot(s) · 4 BaF*) → a slot select (time · game, the people as the description; 25 a
    day, and the card says so past that) → the slot view: a person select, then a `UserSelect` *Link to a member…* and
    **Spotlight** / **Stop spotlighting** / **Unlink** / **Link @near-miss** buttons, drawn only when they apply. The
    run moves are NOT repeated in the panel's slot view — the card's run pick keeps them.
11. **The notice's People…** is one persistent `DynamicItem` (`marathon:people:<id>`, KI-20), added by one helper
    `marathon_feeds.people_on` on the feed-ADDED notice only (a suggest notice has no marathon yet). It opens the People
    view privately; a member who presses it gets the BaF-only view. It sits beside Pause it / Remove it on `main`; the
    `shadow-home-per-feature` merge should keep `people_on(...)` around whatever view its §E builds.
12. **Merge collisions to expect**: `SCHEMA_VERSION` 64 → **65**; `tests/test_settings_store.py` key count 482 → **485**
    (three keys, the KI-36 shape); `Marathons.cog_load` registers `PeopleButton` beside `NextButton, FeedButton`; the
    mock's AGDQ 2027 now ends ~2 days out (was +440 min) and carries five more runs (15–19), channel row 6
    (`flyingludicolo`) and one `marathonSpotlights` row.
13. **Near-miss rule, as built** (§B2.2): a person who is not a member, whose schedule name or Twitch login has the same
    letters as a guild member's username ignoring case and punctuation, or is one edit from it (4+ letters), or is the
    head of an underscored/dotted username (`gz` / `gz_hero`). The exact-username rule still links by itself (and still
    only for a name with no Twitch link).
14. **§B2.3 needed no code**: `run_fields` already joins every BaF mention and a run posts once. Two tests prove it.
15. **Day folds** follow §B exactly (today open, past shut, future shut unless it holds BaF), plus: a day holding an open
    slot stays open across a redraw.
16. **Commit shape**: two build commits (Python; site + mock) and one docs commit, not the nine boundaries the brief
    listed — the storage, the answer and the shared functions landed and went green together.

## What was NOT verified

- **Not against the real bot or Discord.** The panel's People views and the notice's People… button were checked only
  by the test suite (embed text, the components drawn, the custom id round-trip); nothing was clicked in a Discord
  client, and no notice was posted anywhere.
- **Not every site move was pressed.** Rendered in `chrome-headless-shell` 149.0.7827.22 over raw CDP against this
  worktree's mock on `MOCK_PORT=8801`, zero console errors on every render: `events.html` (the Source column,
  *Sources…*), `events.html#marathon-1` (Schedule · People · Event · The channel · Posts; BaF · 3; *Fri 25 Sep · 12 slots
  · 4 BaF* open, *Sat 26 Sep · 2 slots · 1 BaF* open, *Sun 27 Sep · 2 slots · 0 BaF* shut), the race slot opened (five
  lines: Casey ✦BaF, TheKingsPride, QuietKid *looks like @quietkid — Link?*, Peas, Moth ✦BaF), the Sources drawer, and
  the race at 390 px. **Pressed:** Spotlight… on a slot → confirm → *Spotlit until …* with Open on Go-live and Stop
  spotlighting; the near-miss *Link?* → QuietKid became ✦BaF and joined the BaF block; Link to a member… OPENED
  (pre-filled with @quietkid) but was not confirmed. **Not pressed:** Stop spotlighting, Unlink, Spotlight… from the
  BaF block, typing in the schedule filter, any feed move inside the Sources drawer, the Open on Go-live link. The
  routes behind them are exercised by `check.mjs` (mock) and the API tests (real routers).
- **Light and other themes** were not rendered; only the default dark theme at 1400 px and 390 px.
- **A browser in a zone other than the guild's** was not rendered: days and slot times use `default_timezone`, the
  *Spotlit until* words use the browser's zone.
- **A real GDQ-sized schedule** (≈150 runs, ≈250 people) was not timed: `people_state` reads every channel row once per
  call and walks every guild member per stranger for the near-miss rule; the panel recomputes it on every press.
- **The merge with `shadow-home-per-feature`** was not tried.
