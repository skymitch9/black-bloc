# Marathon feeds — the bot polls GDQ (and ESA on horaro.net) for events itself, so staff never paste a schedule URL

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 14:3x Phoenix),
> dispatched to Opus as branch `marathon-feeds`** off `main` (v164 live, 2026-09-25 14:16 — every marathon build is
> deployed; read the four marathon designs' Deviations before this). **Last verified: 2026-09-25 14:2x** — four live
> fetches: **GDQ** `GET https://tracker.gamesdonequick.com/tracker/api/v2/events/` (70 events, one page, `{count,
> next, previous, results[]}`, each `{id, short, name, datetime, timezone, archived, draft, …}`; ordered by `datetime`
> newest first; every event still ahead is `draft: true`; `datetime` is the first run's start — all three measured by
> the `marathon-next-event` build); **ESA** — `https://esamarathon.com/schedule` says *"The full schedule archive is
> available at horaro.net/esa"*; `GET https://horaro.net/-/api/v1/events/esa/schedules` answers `{data: [{id, name,
> slug, timezone, start, start_t, updated, link, website, twitch, description, setup, columns, items, links}]}` (oldest
> first — 2013 is row one); `GET https://horaro.net/esa/2026-winter1.json` answers `{meta, schedule: {name, slug,
> timezone, start, columns: ["Game", "Player(s)", "Platform", "Category", "Note", "hidden:Layout", "hidden:UserIDs",
> "hidden:ID"], items: [{length, length_t, scheduled, scheduled_t, data: [...], options}]}}` — example `data`:
> `["[Donkey Kong Bananza](https://www.youtube.com/watch?v=…)", "5eil", "Switch 2", "Any%", null, "16x9", "771",
> "BanazaW26"]`. ⚠️ **ESA's player column is a plain NAME, not a Twitch login** (`hidden:UserIDs` are Horaro ids), so an
> ESA run matches our people by name only — the Discord-username rule and staff pairings, never a link. Code (v164):
> `black_bloc/marathon_sources.py` (`read_url`, `RUNS_URL`, `next_gdq_event`, the `Run` / `Person` shapes, the
> `source` column already exists on `marathons`), `cogs/content/marathon.py` (`tick_once`, `create_marathon`,
> `suggest_next` / `add_next` — the suggestion record + persistent-button notice this design generalises),
> `black_bloc/marathon.py` (`match_people`), the Marathons section on `events.html` (`marathons-section.js`), the
> `/event` ▸ Marathons… sub-panel. Live channel rows: GamesDoneQuick `id 3` (Twitch `gamesdonequick`), ESAMarathon
> `id 4` (`esamarathon`, opted out of announcements). ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 14:2x Phoenix)

*"lets add a feature where constantly poll gdq to get events, check if we can do that for any of the other channel
only ones we have. if not GDQ is prio"* — and, 14:3x: *"only do marathons we have in channel though, not random ones"*.

**So a feed is a property of a CHANNEL ROW we already watch, never a free-standing source.** Every feed carries a
`spotlight_id` that must point at a channel row (the Streamers list's channel-only rows: GamesDoneQuick, ESAMarathon
today); the seed makes feeds only for channel rows that exist; **Add a feed…** starts from a channel-row picker, not a
slug box; a channel row that is removed takes its feed with it (the feed's marathons stay, as history). Nothing here
can add a marathon for a channel the server does not already follow.

**The answer to "any of the other channel-only ones":** yes for **ESA** — its whole archive and every future schedule
is on horaro.net with a JSON list and a JSON per schedule (verified above), so an ESA feed is buildable in this same
build with the parked Horaro reader; the one honest limit is that ESA names people instead of linking them, so
matching is by name. GDQ stays first: it is built and verified first, ESA second, and if room runs out ESA is the
part that waits.

## A. The model — a feed per source channel, and marathons it makes

**`marathon_feeds`** (new table): `id, guild_id, source` (`gdq` / `horaro`), `feed_ref` (GDQ: `''`; Horaro: the
event slug, `esa`), `spotlight_id` (the channel row its marathons air on — GDQ `3`, ESA `4`), `name` (*GDQ*,
*ESA*), `action` (`add` / `suggest`), `active INTEGER NOT NULL DEFAULT 1`, `last_checked_at, last_ok INTEGER,
last_error, checks_failed INTEGER NOT NULL DEFAULT 0, added_by, added_at`, `UNIQUE (guild_id, source, feed_ref)`, and **`spotlight_id` is NOT NULL** — a feed without a channel row is refused
in words (*A feed belongs to a channel Black Bloc already watches — add the channel first.*).
`marathons` gains **`feed_id INTEGER`** (nullable; `ADDED_COLUMNS`) so a marathon knows the feed that made it and a
feed lists its marathons. Schema 62 → **63**.

**Seed on first boot** (a boot reconcile, one row per boot): a `gdq` feed on the channel row whose `twitch_login` is
`gamesdonequick`, and a `horaro` feed `esa` on the row whose login is `esamarathon` — each only when that channel row
exists and no feed for that source exists yet; `action` from `marathon_feed_action_default`. **Removing a channel row removes its
feed** (`delete_channel` → the feed row goes, `marathon.feed_removed` with `because: channel_removed`); the marathons
it made stay, as history, with `feed_id` cleared.

## B. The poll — every `marathon_feed_hours` (6), one list read per feed, additive only

On the marathon cog's minute tick, a feed whose `last_checked_at` is older than `marathon_feed_hours` (6, 1–168) is
checked: **GDQ** reads the events list (`next_gdq_event`'s fetch, all pages); **Horaro** reads
`/-/api/v1/events/<slug>/schedules`. Every event / schedule whose start is ahead of now (or ended less than
`marathon_feed_recent_days` = 1 day ago) and is not `archived` (GDQ) and is not already a marathon (by `source` +
`source_ref` — the tracker id / the Horaro `event/slug`) is **new**:

- `action = add` → `create_marathon` exactly as a staff Add does (name = the event's name; schedule URL = the
  tracker event URL / the Horaro schedule `link`; `spotlight_id` = the feed's; `make_event` from
  `marathon_makes_event`; `added_by` NULL with `via: feed`), logging `marathon.feed_added` (**IMPORTANT** — staff
  should see a marathon appear) and posting ONE staff notice *GDQ has a new event: **SGDQ 2027**, 5 Jul — added; it
  will be read from its schedule* with **Pause it** / **Remove it** buttons (the persistent-button template
  `marathon-next-event` built), so the final say is one press away.
- `action = suggest` → the SAME suggestion record and notice `marathon-next-event` built (Add it / Not this one), on
  the feed rather than on an ending marathon: `marathon_feeds.suggested TEXT` (JSON, a LIST of open suggestions —
  several events can be ahead at once), logging `marathon.feed_suggested` (IMPORTANT). A dismissed event is never
  re-suggested by the feed; **Look again** on the feed clears dismissals.

⚠️ **Never twice, never on a downgrade.** The `(source, source_ref)` check is on `marathons` including paused and over
ones; an event the feed already made and staff removed is remembered in `marathon_feeds.ignored TEXT` (JSON list of
refs — written by Remove when the marathon has a `feed_id`) so the feed does not re-add it six hours later; **Forget
ignored** on the feed's card empties it. A fetch failure counts up `checks_failed`, keeps everything, logs
`marathon.feed_failed` (routine, **IMPORTANT** at the third consecutive), and a success resets it. GDQ's events are
drafts until published: adding them early is the point (the schedule build re-reads a 404 until it appears).

**ESA through the Horaro reader (parked in `marathon-schedule-design.md` §E, built HERE).** `read_url` learns
`https://horaro.net/<event>/<schedule>`; `parse_horaro(payload)` reads `schedule.columns` to find the *Game*,
*Player(s)* and *Category* columns by name (case-insensitive; `Runner(s)` / `Player(s)` / `Runners` all count), takes
`scheduled` + `length` for the times, `hidden:ID` (or the item index) as `external_id`, strips markdown links from the
game (`[Name](url)` → `Name`), and splits players on `,` / `&` / ` vs ` / ` and `; a player written as
`[name](https://twitch.tv/login)` yields a login, a bare name yields none. Fixture: ONE captured horaro.net ESA
schedule trimmed to ~10 items under `tests/fixtures/marathon/`. Two ESA schedules (Stream One / Stream Two) are two
marathons on the same channel row — the board and reminders already key off the marathon, so that just works; the
title match (§C of the schedule design) uses whichever marathon's run the title names.

## C. Doors

**Site — the Marathons section on `events.html`** gains a **Feeds** card above the list: one row per feed (name ·
source · channel · *checks every 6 h · last checked 12 min ago* · action segment **Add / Suggest** · **Pause** /
**Resume** · **Check now** · **Look again** (suggest mode, clears dismissals) · **Forget ignored** with the count ·
**Remove**), **Add a feed…** (FIRST the channel-row picker — only channel-only rows are offered — then the source
select GDQ / Horaro and, for Horaro, the event slug; a channel that already has a feed is refused in words), and, in suggest mode, the open suggestions as Next-up cards (reuse
`nextCard`). A marathon row made by a feed shows *from the GDQ feed* in its drawer's Event card line. Routes:
`GET / POST /api/marathons/feeds`, `PATCH /api/marathons/feeds/{id}` (`action`, `active`, `spotlight_id`, `name`),
`DELETE …/feeds/{id}`, `POST …/feeds/{id}/check`, `POST …/feeds/{id}/look` (clear dismissals + check), `POST
…/feeds/{id}/forget` (empty `ignored`), `POST …/feeds/{id}/add` (`event_ref` — Add it on a suggestion), `PATCH
…/feeds/{id}` with `dismiss: event_ref`. Contract + mock rows (a GDQ feed in `add` mode with two marathons it made; an
ESA feed in `suggest` mode with one open suggestion and one dismissed).

**Discord — `/event` ▸ Marathons… (staff half)** gains **Feeds…** → the same rows as a select + the moves as
buttons, **Add a feed…** (a select of the channel-only rows, then a modal: source word, Horaro slug). The staff notice's buttons are the two moves above.
Nothing a member can press.

## D. Keys — five, namespace `marathon_`

`marathon_feeds` (bool, true — the whole feature's switch), `marathon_feed_hours` (6, 1–168),
`marathon_feed_action_default` (enum `add` / `suggest`, **`add`** — the owner's *"get events"*), `marathon_feed_recent_days`
(1, 0–30), `marathon_feed_added_template` (text: *{feed} has a new event: **{event}**, {when} — added. It will be read
from its schedule.*); the suggest wording reuses `marathon_next_template`. Registry + mock + labels + the Marathons
settings group. Keys 469 → 474.

## E. Logging

`marathon.feed_seeded`, `feed_added` (IMPORTANT), `feed_suggested` (IMPORTANT), `feed_checked` (routine, counts),
`feed_failed` (routine → IMPORTANT at three), `feed_paused` / `feed_resumed` / `feed_removed` / `feed_ignored` /
`feed_forgot`, `feed_notice_failed` (IMPORTANT by suffix), `would_feed_add` in shadow. Under the `marathon` feature.

## F. Tests, docs, gate

`tests/test_marathon_sources.py` (`parse_horaro` against the fixture: columns found by name, times, ids, markdown
stripped, players split, a linked player yields a login; the Horaro events-list reader; `read_url` for the horaro.net
form), `tests/cogs/content/test_marathon.py` (the seed makes two feeds once and not twice; a check adds a new event
in `add` mode with the channel and the make-event wish, and never the same ref twice; a removed feed-made marathon is
ignored thereafter, Forget ignored re-adds; `suggest` mode records and notices, dismiss sticks, Look again clears; a
failed check counts and the third is IMPORTANT; paused → nothing; shadow → the shadow home; an ESA schedule's people
match by Discord username and by pairing, never by link), `tests/api/tools/test_marathons.py` (the feed routes, the
staff gate, the refusals in words: unknown source, a slug that does not answer), `tests/api/test_contract.py`,
`tests/storage/test_db.py` (63), the key / kind guards, `check.mjs`. Both `pytest -n 8` orders, `ruff`, ES parse, node
tests, a mock port of the builder's own. Docs: `code-notes.md`; this doc's foot; `architecture.md` (schema 63, the
table, the routes); `docs/info/README.md` (one row); `marathon-schedule-design.md` (§E's parked Horaro paragraph
gains a dated *BUILT for ESA by `marathon-feeds`* line) and `marathon-next-event-design.md` (one dated line);
`sweeps.md` rows `MF-a…` (a: the Feeds card shows GDQ and ESA after the first boot; b: Check now on GDQ adds the
tracker's future events as marathons and posts the notice; c: Pause it on the notice pauses the marathon; d: an ESA
schedule's runs list our people by name after a pairing). NOT `TODO.md` / `DONE.md` / `deploys.log` /
`KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: one table + one column through the bootstrap.

**Build order (commit at each):** storage → the Horaro reader + fixture → the pure feed logic → the cog (seed, poll,
add / suggest, notice, ignore) → routes → the Feeds card + mock → the panel → docs. GDQ first end to end, ESA second;
if room runs out, ESA's reader and feed are what wait, and the report says so.

## Deviations

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
