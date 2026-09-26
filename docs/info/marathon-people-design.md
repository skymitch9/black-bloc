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

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
