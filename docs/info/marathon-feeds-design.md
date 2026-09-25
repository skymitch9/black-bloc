# Marathon feeds — the bot polls GDQ (and ESA on horaro.net) for events itself, so staff never paste a schedule URL

> 🔨 **2026-09-25 — BUILT on branch `marathon-feeds` (tracker GDQ + RPGLB, horaro.net; Oengus parked), NOT merged, NOT
> deployed.** Schema 63, keys 475, 28 deviations (⚠️ 1: no ESA seed — ESA opted out; ⚠️ 17: the username match is new;
> ⚠️ 25: SS4C parked with what was tried) and *What was NOT verified* at the foot.

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
> `id 4` (`esamarathon`, opted out of announcements), RPG Limit Break `id 5` (`rpglimitbreak`), Speed Stuff 4 Charity
> `id 6` (`speedstuff4charity`), RetroGamingLiveTV `id 7` (`retrogaminglivetv`). **14:4x, owner: *"check retro and
> rpglimit too"* — checked live:** **RPGLB** runs the SAME tracker software as GDQ — `https://rpglimitbreak.com/schedule`
> redirects to `rpglimitbreak.com/tracker/runs/rpglb2026`, and `GET https://tracker.rpglimitbreak.com/api/v2/events/`
> answers the identical `{count, next, previous, results[]}` shape (newest: id **21** `rpglb2026`, 2026-05-17, not a
> draft; 20 `rpglb2025`; 19 `rpglb2024`); its horaro.net archive (`rpglb`) stops at 2025. **SS4C**'s past events are on
> oengus.io (`oengus.io/marathon/ss4c8`) and the horaro.org archive — an Oengus feed needs the Oengus lines endpoint,
> still unverified (parked in the schedule design). **RGL**: the live title says *!schedule* but no readable source was
> found — `retrogaminglive.tv` does not resolve, the Twitch about panels are script-rendered, no horaro.net or Oengus
> event names it — so RGL gets no feed until someone finds where its schedule lives. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 14:2x Phoenix)

*"lets add a feature where constantly poll gdq to get events, check if we can do that for any of the other channel
only ones we have. if not GDQ is prio"* — and, 14:3x: *"only do marathons we have in channel though, not random ones"*.

**So a feed is a property of a CHANNEL ROW we already watch, never a free-standing source.** Every feed carries a
`spotlight_id` that must point at a channel row (the Streamers list's channel-only rows: GamesDoneQuick, ESAMarathon
today); the seed makes feeds only for channel rows that exist; **Add a feed…** starts from a channel-row picker, not a
slug box; a channel row that is removed takes its feed with it (the feed's marathons stay, as history). Nothing here
can add a marathon for a channel the server does not already follow.

**The answer to "any of the other channel-only ones", per channel row we have:**

| Channel row | Source | Feed? | How |
|---|---|---|---|
| GamesDoneQuick (3) | GDQ tracker | **yes, first** | the events list, already read by `next_gdq_event` |
| RPG Limit Break (5) | the SAME tracker software at `tracker.rpglimitbreak.com` | **yes, free** — the GDQ reader with a different base URL | a `tracker` source whose `feed_ref` is the tracker's base (`https://tracker.gamesdonequick.com/tracker`, `https://tracker.rpglimitbreak.com`); `read_url` learns the RPGLB forms (`rpglimitbreak.com/schedule`, `…/tracker/runs/<short>`, the tracker event URL) |
| ESAMarathon (4) | horaro.net | **yes, second** | the Horaro reader parked in the schedule design, built here; people match by NAME only (ESA writes names, not Twitch links) |
| Speed Stuff 4 Charity (6) | oengus.io | **maybe, last** | only if the builder can verify the Oengus lines endpoint on a live marathon in a few minutes; otherwise recorded as parked with what was tried |
| RetroGamingLiveTV (7) | none found | **no** | no readable schedule source found (see the header); the row stays a plain channel |

GDQ first, RPGLB with it (same code), ESA second, SS4C only if cheap, RGL not at all. If room runs out, the order
above is the order things wait in.

## A. The model — a feed per source channel, and marathons it makes

**`marathon_feeds`** (new table): `id, guild_id, source` (`tracker` / `horaro` / `oengus` — `gdq` marathons keep
their `source` word; a feed's `tracker` source covers GDQ and RPGLB alike), `feed_ref` (tracker: the base URL;
Horaro: the event slug, `esa`; Oengus: nothing — it would list by organiser, which the builder finds or parks), `spotlight_id` (the channel row its marathons air on — GDQ `3`, ESA `4`), `name` (*GDQ*,
*ESA*), `action` (`add` / `suggest`), `active INTEGER NOT NULL DEFAULT 1`, `last_checked_at, last_ok INTEGER,
last_error, checks_failed INTEGER NOT NULL DEFAULT 0, added_by, added_at`, `UNIQUE (guild_id, source, feed_ref)`, and **`spotlight_id` is NOT NULL** — a feed without a channel row is refused
in words (*A feed belongs to a channel Black Bloc already watches — add the channel first.*).
`marathons` gains **`feed_id INTEGER`** (nullable; `ADDED_COLUMNS`) so a marathon knows the feed that made it and a
feed lists its marathons. Schema 62 → **63**.

**Seed on first boot** (a boot reconcile, one row per boot): a `tracker` feed (`https://tracker.gamesdonequick.com/tracker`)
on the channel row whose `twitch_login` is `gamesdonequick`, a `tracker` feed (`https://tracker.rpglimitbreak.com`) on
`rpglimitbreak`, and — ⚠️ **NOT any more: owner, 2026-09-25 15:0x, verbatim *"yes have esam opted out for marathons"*** — ~~a `horaro`
feed `esa` on `esamarathon`~~ (the Horaro reader is still built here, for any channel row staff give a Horaro feed by
hand; the ESA row gets no seeded feed) — each only when that channel row exists and that row has no feed yet; `action` from `marathon_feed_action_default`. **Removing a channel row removes its
feed** (`delete_channel` → the feed row goes, `marathon.feed_removed` with `because: channel_removed`); the marathons
it made stay, as history, with `feed_id` cleared.

## B. The poll — every `marathon_feed_hours` (6), one list read per feed, additive only

On the marathon cog's minute tick, a feed whose `last_checked_at` is older than `marathon_feed_hours` (6, 1–168) is
checked: a **tracker** feed reads `<base>/api/v2/events/` (`next_gdq_event`'s fetch, all pages, the base from `feed_ref`); **Horaro** reads
`/-/api/v1/events/<slug>/schedules`. Every event / schedule whose start is ahead of now (or ended less than
`marathon_feed_recent_days` = 1 day ago) and is not `archived` (tracker) and is not already a marathon (by `source` +
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
`sweeps.md` rows `MF-a…` (a: the Feeds card shows GDQ, RPGLB and ESA after the first boot; b: Check now on GDQ adds the
tracker's future events as marathons and posts the notice; c: Pause it on the notice pauses the marathon; d: an ESA
schedule's runs list our people by name after a pairing). NOT `TODO.md` / `DONE.md` / `deploys.log` /
`KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: one table + one column through the bootstrap.

**Build order (commit at each):** storage → the tracker base URL (RPGLB) → the Horaro reader + fixture → the pure feed logic → the cog (seed, poll,
add / suggest, notice, ignore) → routes → the Feeds card + mock → the panel → docs. GDQ + RPGLB first end to end, ESA second, SS4C last and only if the Oengus lines endpoint verifies in minutes;
if room runs out, that is the order things wait in, and the report says so.

## Deviations

*(written by the build agent, 2026-09-25, branch `marathon-feeds` off `main` `05fbd0e6`. Schema **62 → 63**
(`marathon_feeds`, `marathon_feed_seeds`, `marathons.feed_id`), registry keys **469 → 475**, real routes **+8**
(`/api/marathons/feeds` …; the contract carries **9** entries because `PATCH` is listed twice — the Add/Suggest/Pause
write and the `dismiss` write — so `check.mjs` reads *22 pages, 246 routes*), log kinds **+20** bare (below). Cogs,
pages, top-level commands and log features unchanged. **Sources shipped: tracker GDQ, tracker RPGLB, horaro.net
(ESA-capable). Parked: Oengus (SS4C) — Deviation 25. Not built: RGL (no source).**)*

1. ⚠️ **No ESA seed — owner 2026-09-25 15:0x: ESA opted out of marathons** (relayed by the conductor mid-build as a
   narrowing). The boot seed makes only the two tracker feeds (GDQ on `gamesdonequick`, RPGLB on `rpglimitbreak`).
   The Horaro reader and the `horaro` feed source are built exactly as §B says, so staff can give any channel row a
   horaro.net feed by hand (**Add a feed…** ▸ horaro ▸ slug `esa`); the ESA fixture and its tests stay. The mock has
   no ESA feed either; its suggest-mode sample is RPGLB (§C asked for ESA).
2. **Marathon `source` words: `gdq` (unchanged), `rpglb` and `horaro` (new).** A feed's `tracker` source maps to a
   marathon source through `marathon_sources.TRACKER_BASES` (`tracker_source(base)`), so an unknown tracker base is
   refused rather than read blind. **Add a feed** therefore offers three picks — *GDQ tracker / RPG Limit Break tracker
   / horaro.net (+ slug)* — not §C's two (*GDQ / Horaro*) and not a free base URL.
3. **`rpglimitbreak.com/schedule`** (a 302 to the current event, no id in it) reads as ref `latest`, resolved once to
   the newest event the RPGLB list carries. `…/tracker/runs/<short>`, `tracker.rpglimitbreak.com/(event|runs|index)/<id
   or short>` read as the GDQ forms do. Verified live: `tracker.rpglimitbreak.com/api/v2/events/21/runs/?limit=500` →
   55 runs, one page, the GDQ shape; talents carry `stream` (`http://twitch.tv/sanjan_`), several are blank; its
   `twitch_name` is a numeric Twitch category id (`"509663"`), not a name. Fixtures `rpglb2026_runs.json` (8 runs) and
   `rpglb_events_list.json` (3 events).
4. **Seeding is once per channel, ever — a second table, `marathon_feed_seeds (guild_id, twitch_login)`.** §A said
   "only when that row has no feed yet", which would re-seed a feed staff removed on the very next boot (staff final
   say). A marker per channel login is written whether a feed was made or one already existed; a channel row that
   appears later is seeded on the next boot. Seeding runs inside the tick (under the `Reconciler`), once per process,
   and only while `marathon_feeds` is on and `marathon_mode` is not `off`.
5. **One feed per channel is a DB constraint too** — `UNIQUE INDEX marathon_feeds_one_per_channel (guild_id,
   spotlight_id)` behind the refusal in words (checklist 6).
6. **Six keys, not five: `marathon_feed_suggest_template`** (*{feed} has a new event: **{event}**, {when}
   ({relative}). Add it?*). §D reused `marathon_next_template`, whose default reads *"{marathon} is over — the next GDQ
   event is …"* — wrong words for a feed, and every posted word is a key. Both feed templates take `{feed} {event}
   {when} {relative} {url} {channel}`. `marathon_unknown_site`'s default changed to *I can read the GDQ and RPG Limit
   Break trackers and horaro.net schedules — that link is none of them.* (a staff override, if any, is kept).
7. **The third consecutive failure is its own kind, `marathon.feed_stale` (IMPORTANT)**; every `marathon.feed_failed`
   is routine — the `marathon.schedule_stale` precedent (schedule design Deviation 6).
8. **Kinds beyond §E:** `feed_created` (staff Add a feed), `feed_changed` (action / name / channel), `feed_looked`,
   `feed_dismissed`, `feed_taken` (Add it on a suggestion), `would_feed_suggest` (the shadow twin §E did not name),
   `feed_add_failed` (IMPORTANT by suffix — an event the feed could not add). The 20: IMPORTANT `feed_added`,
   `feed_suggested`, `feed_stale`; routine `feed_changed`, `feed_checked`, `feed_created`, `feed_dismissed`,
   `feed_failed`, `feed_forgot`, `feed_ignored`, `feed_looked`, `feed_paused`, `feed_removed`, `feed_resumed`,
   `feed_seeded`, `feed_taken`; shadow `would_feed_add`, `would_feed_suggest`; suffix `feed_add_failed`,
   `feed_notice_failed`. ⚠️ **There is no `via: feed` in a row**: `actionlog` normalises `via` to discord / website,
   so the automatic rows carry **`automatic: true`** (and `marathon.added` carries `feed_id`) instead.
9. **"Recent" for a tracker is by START**, not end: a tracker event has only `datetime` (the first run). An event
   counts as new while it starts ahead or started within `marathon_feed_recent_days`; a horaro.net schedule uses its
   last item's end (`horaro_span`).
10. **Shadow still ADDS** (a marathon row is a database write, not a post) and logs `would_feed_add` /
    `would_feed_suggest`; the notice goes to the shadow home with the rehearsal note. **`off`** checks nothing (the
    tick does not run feeds); the staff moves still work; a notice is skipped silently in `off` (no failure row).
11. **Adoption (not in the design):** an event the list already has as a marathon (same source + ref) with no feed
    gets the feed's id on the next check (`feed_checked` counts `adopted`), so the Feeds card lists it and a Remove
    ignores it. Live today that is any GDQ marathon staff added by hand for 71–74.
12. **Add a feed checks at once** (so staff see what it found); that check and the one inside **Look again** run as
    automatic rows, so each web write leaves one `web.` row (checklist 34).
13. ⚠️ **Add it on a suggestion leaves two web rows**: `web.marathon.added` (from `create_marathon`) and
    `web.marathon.feed_taken` — two events, the next-event build's Deviation 14 precedent. Flagged for the reviewer.
14. **A Remove of a feed-made marathon logs `marathon.feed_ignored` as an automatic (bare) row**, from any door, so a
    web `DELETE` still leaves one `web.` row. The ref is appended with one atomic `json_insert … WHERE NOT EXISTS`
    UPDATE, so it needs no feed lock (no lock-order question with a running check).
15. **Notice buttons: `marathon:feed:<feed_id>:<ref>:<pause|remove|add|dismiss>`** (`FeedButton`, a `DynamicItem`
    registered in `cog_load`, KI-20). Pause it / Remove it carry the MARATHON id as the ref; Add it / Not this one the
    event ref (`74`, `esa/2026-summer2`). A ref over 60 characters (or with a character outside `A-Za-z0-9_./-`) posts
    its notice with no buttons — the page and the panel still reach it. A folded notice keeps its words, gains the
    outcome line (*Paused by @x*, *Removed by @x — the feed will not add it again*, *Added by*, *Dismissed by* — the
    last two struck through where it was dismissed/removed) and **loses** its buttons (`view=None`); next-event keeps
    them disabled instead.
16. **Remove it on the notice is one press, no confirm** (§B: "the final say is one press away"); the panel's Remove
    *feed* has the shared confirm card, the page's has `ask`.
17. ⚠️ **The Discord-username match did not exist; built.** `match_people` gained a third step: a person with NO login
    (after pairings, after the Twitch link) matches a non-bot guild member whose Discord username is exactly that name,
    case-insensitive (`usernames_of(guild)`). It applies to every source, not only ESA. And the header's premise is
    only half true: **ESA's 2026 summer schedules DO link most players** (`[hypnoshark](https://twitch.tv/hypnoshark)`;
    winter 2026 had bare names), so the reader turns a linked player into a login and ESA matches by link where it
    gives one — the username step only ever sees the bare names.
18. **Horaro `external_id`** is the `hidden:ID` cell, else `#<item index>` — an item inserted above a no-id row shifts
    the index, which the diff reads as one dropped + one new run.
19. **Horaro marathon names are `<feed name> <schedule name>`** (*ESA 2026 - Summer (Stream Two)*); a tracker event
    keeps its own full name.
20. **Horaro is read from the `.json` export** (`horaro.net/<event>/<schedule>.json`). Its meta calls it *"a living
    document … use the API for stable output"*, but the v1 API hides hidden columns, i.e. `hidden:ID`. The events
    list is the v1 API (`/-/api/v1/events/<slug>/schedules`, which inlines each schedule's items, so the end is known
    without a second read).
21. ⚠️ **Checklist 33 gap: a feed's `name` and `spotlight_id` are PATCH-only** — §C drew no control for either. The
    action (Add / Suggest) and Pause / Resume have both doors; so do Check now, Look again, Forget ignored, Remove,
    Add it and Not this one.
22. **Site:** the waiting events are `suggestionCard`, a sibling of `nextCard` with the same card shape (`nextCard` is
    bound to a marathon row's `.next` and its routes). **Add a feed** on the page is ONE form (channel · read from ·
    slug · name · Add/Suggest); in Discord it is two steps (a channel select, then a modal with the pick guessed from
    the login). The marathon drawer's Event card says *Added by the **GDQ** feed.* (§C: "from the GDQ feed").
23. **Mock:** the reader learned the RPGLB tracker and horaro.net links (`marathonReadAny`); the seed's URLs are
    literal strings because `seedState` runs before the `FEED_*` constants exist (a TDZ error found on first start).
24. **Tests mirror the package** (the repo rule wins over §F's file names): `tests/test_marathon_feeds.py` (pure),
    `tests/cogs/content/test_marathon_feeds.py` (the cog side), `tests/api/tools/test_marathon_feeds.py` (routes);
    the readers are in `tests/test_marathon_sources.py` as §F said.
25. ⚠️ **SS4C / Oengus: PARKED** (the brief's ~15 minutes). **Verified:** the LINES endpoint exists —
    `GET https://oengus.io/api/v2/marathons/ss4c8/schedules/for-slug/1` → `{id: 325, lines: [{game, category,
    console, date, estimate, setupTime, setupBlock, runners: [{runnerName, profile: {connections: [{platform:
    "TWITCH", username}]}}]}]}` (found in the site bundle `main-BSJLLA3W.js`, `getBySlug` → `${id}/schedules/for-slug/
    ${slug}`), and it exposes Twitch usernames. `GET …/marathons/ss4c8/schedules` → `[{id: 325, slug: "1", published:
    true}]`; `GET /api/v1/marathons/ss4c8` carries `twitch: "speedstuff4charity"`. **Not found: a way to LIST a
    channel's marathons** — `/api/v2/marathons/search?name=`, `/api/v2/users/<name>/marathons` → 404; only
    `/api/v2/marathons/for-home` (`live` 5 / `next` 5 / `open` 19) exists, and no SS4C marathon is on it today, so a
    feed would be guessing ids (`ss4c9` …). Also tried and dead: `…/schedules/325/lines` (404), `…/schedules/325?
    withCustomData=true` (no lines), `/api/v1/marathons/ss4c8/schedule` (`{id: 0, lines: null}`), `/api/v2/
    schedules/325` (404), `…/export?format=json` (needs `locale`). **The next build:** an Oengus reader over
    `for-slug` (+ `read_url` for `oengus.io/marathon/<id>[/schedule[/<slug>]]`), and a feed that reads `for-home` and
    keeps the marathons whose v1 `twitch` is the channel's login.
26. **RGL:** nothing built (no source, as the design found).
27. **The Discord panel landed with the cog commit** (`95f078a6`), not as its own build-order step.
28. **Sweep rows `MF-a` … `MF-e`** (`e` is the SS4C/horaro-by-hand check).

## What was NOT verified

- ⚠️ **Nothing met Discord.** The staff notices, the four persistent buttons (`FeedButton`), the folds, `/event` ▸
  **Marathons…** ▸ **Feeds…** and its channel select + modal ran only against the suite's fakes. **KI-20 restart
  survival** is shown only by `FeedButton.from_custom_id` rebuilding from a regex match of a posted custom id.
- ⚠️ **No feed has run under the bot.** The seed, the 6-hour cadence, the first-boot check and "never twice" were driven
  by an injected clock and fresh cog instances standing in for boots. ⚠️ **On the first boot after deploy with
  `marathon_feeds` on and `marathon_mode` not off, the GDQ feed will ADD every GDQ event ahead (71 *Games Done
  Hitless*, 72 *GDQx 2026*, 73 *Halo Fest*, 74 *AGDQ 2027* as measured 2026-09-25) that is not already a marathon
  (those are adopted), each with a staff notice and — with `marathon_makes_event` on — a waiting event wish.** RPGLB
  finds nothing (2026 was in May).
- **Live reads from the build machine only**, 2026-09-25 14:4x–15:1x: the GDQ and RPGLB events lists, RPGLB event 21's
  runs, horaro.net `esa` schedules list and two `.json` exports, and the Oengus endpoints above. **Not from Fly**
  (KI-30's datacenter wall untested on any of these hosts). The bot's own `ScheduleClient` was NOT run against the
  live RPGLB or horaro.net hosts — only curl / urllib with a browser User-Agent; the parsers are proven on the
  captured fixtures.
- **Schema 63** was proven on a fresh file and a file downgraded to 62, not on the live volume.
- **Shadow** was tested against the fake shadow channel, not `#welcome-test`.
- **The page was rendered headless** (Chrome 149 `--dump-dom`, mock on port 8796): the Feeds card (GDQ · *checks every
  6 h · last checked 12m ago* · Add/Suggest · Pause · Check now · Forget ignored (1) · Remove; RPG Limit Break with
  Look again), the RPGLB *Next up* card, and AGDQ 2027's drawer line *Added by the **GDQ** feed.* **Nothing was
  clicked in a browser** and console errors were not read; the writes were checked by `check.mjs` and the route tests.
- **Cost:** one events-list GET per feed per 6 h (+ per added event, one resolve GET and the schedule reads that any
  marathon costs). Not measured.
