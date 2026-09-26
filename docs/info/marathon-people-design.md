# The source is a column, and a marathon opens on its people — BaF first, then everyone, each one linkable or spotlightable

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

The drawer's order becomes **Schedule · People · Runs · Event · The channel · Posts · Pause / Remove** — *People*
replaces *Who is who* and comes before the runs, because it is what staff open the marathon for.

**People** is one list of every person on the schedule (runners, hosts, commentators — `part` shown as a small
word), built from the runs' `people` JSON grouped by person (name + login), in two blocks:

1. **BaF** — everyone matched to a member (by link, by username or by pairing): *display name · @discord · twitch.tv/login ·
   3 runs (1 done, 1 on now) · runner* with the member's avatar, and the moves **Unlink** (when it is a pairing —
   removes it; a link-based match says *matched by their Twitch link* and offers nothing to undo here) and
   **Spotlight…** (below).
2. **Everyone else** — *name · twitch.tv/login (or no link) · N runs · part*, and per row: **Link to a member…** (the
   existing pairing, pre-filled with the name: a member picker → `POST …/people` → the row moves up into BaF at once,
   and the run becomes ours — board, reminders, shoutouts follow), and **Spotlight…**.

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

The list has a filter box and a **BaF / Everyone / All** chip like Runs; BaF is open, Everyone else folds shut when it
is longer than 20 (a `foldout`) — a GDQ schedule has 600 talent slots. The Runs card stays as the schedule view (BaF
runs highlighted) and gains nothing.

**`/event` ▸ Marathons…** gains **People…** on the picked marathon: the BaF block as lines, then a select of everyone
else (name · runs) whose pick opens a small view with **Link to a member…** (a `UserSelect`) and **Spotlight** — the
same functions.

Routes: `GET /api/marathons/{id}/people` grows to answer the grouped people list (`baf[]`, `others[]`, each with
`name, login, user_id, member, parts, runs, done, live, pairing_id, spotlight_id, spotlight_until`) beside the pairings it
answers today; `POST /api/marathons/{id}/people/{login-or-name}/spotlight`, `DELETE …/spotlight`. Contract + mock rows
(AGDQ 2027: 3 BaF, ~10 others, one spotlit).

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
with BaF on top; d: Link to a member moves a runner up and the board gains the line; e: Spotlight a runner → a
channel-only row on the Go-live page with the marathon's dates; f: `/event` ▸ Marathons… ▸ People…). NOT `TODO.md` /
`DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: one small table through the bootstrap.

## Deviations

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
