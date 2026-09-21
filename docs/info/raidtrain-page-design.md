# Raid trains — their own dashboard page, and a train that makes an event through the events set-up

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **BUILT on branch
> `raidtrain-page`, 2026-09-20 — ⚠️ NOT MERGED, NOT DEPLOYED, and the migration has NOT run on the live
> database.** Commits `5afbf99` / `69ddebc` / `a31599a` plus the doc sweep; the `## Deviations` foot (14
> items) and `## What was NOT verified` are the BUILD agent's. Gate at the landing: `pytest -n 8` **7098
> passed, 3 skipped** in both orders, `ruff` clean, every `site/public/assets/*.js` parses, `node
> site/mock/check.mjs` **21 pages, 197 routes, 24 core settings**, all six node tests, and the new page
> rendered in `chrome-headless-shell` against the mock.
> Before that: 📐 **DESIGN (Fable, 2026-09-20 21:2x), dispatched to
> Opus as branch `raidtrain-page`** the same turn (owner rule: an ask is the go). **Last verified: 2026-09-20 21:2x** against
> `main` `6738a8d` (v149 live; the tree carries the day's merges): raid trains live as TWO SECTIONS at the foot of the
> Events page — `page-events.js:raidTrainsSection` `:369` (the list with `trainTools` `:313`, the claim/leave slot moves
> `:282`/`:299`, **Start a raid train** `:347` posting `POST /api/raidtrains` — title, start, tz, slots…), plus
> `namespaceSettings('raidtrain', { title: 'Raid train settings' })` and its logs block (`page-events.js:566`); the API is
> `api/tools/raidtrain.py` (`/status` `:152`, list `:175`, one `:185`, create `:196`, slots `:252`, swap `:289`, status
> `:315`); the model is `black_bloc/raidtrain.py`; the Discord door is `/raidtrain` (`raidtrain-panel-design.md`, v76 +
> the v100 draft panel). Events are created by `events.create_event(db, guild_id, requester_id, *, title, description,
> where, starts_at, finishes_at)` `:968` and reviewed/approved through the events flow (`events-panel-design.md`,
> `events-forum-design.md`); `events.where_link` `:276`. The site has 20 pages (`contract.json:pages`), the rail's
> groups are `shell.js:GROUPS` and the tab hrefs `app.js:TABS`.

## The ask, verbatim (owner, 2026-09-20 21:1x)

*"raid train should be in its own page and it should have the option to make an event that ties to the event set up we
use."*

## A. The page — `raidtrain.html` + `page-raidtrain.js`, page 21

Under **Runs the cookout** in the rail, after Events (`shell.js:GROUPS`, `app.js:TABS`; `contract.json:pages` gains
`/raidtrain.html`; the mock serves it; `check.mjs` counts 21). Its sections, in this order, following the audit's six
tests (`ux-audit-design.md` §C — one list, work first, machinery last, `data-span="full"` on the list):

1. **Raid trains** (open) — the list and moves EXACTLY as `raidTrainsSection` draws them today, moved not rewritten
   (the slot claim/leave, the status moves, the search/filter it has), with **Start a raid train** in the section's
   toolbar (right-aligned, the posts/golive construct) instead of below the list.
2. **Settings and logs** (shut) — the `raidtrain` settings block and the `raidtrain` logs block that sit on the Events
   page today, lifted whole.

The Events page loses both raid-train sections and the `raidtrain` logs; its subtitle and any sentence that says raid
trains are "below" change; `ux-audit.md`'s events row gets a dated line (fewer sections) and the raid-train preview tab
in `page-preview-events.js` (the static preview draws raid trains as a second tab) gets one line saying the page moved.
`logs.js:LOG_FEATURES` already has the `raidtrain` chip. Guides that link `events.html#raidtrains` (grep `guides_seed.json`
and `docs/access/guides-capture.md`) point at the new page.

## B. A train that is also an event — one press, the events set-up does the rest

**Start a raid train** gains a checkbox **Also make an event** (default OFF — a key, `raidtrain_event_default`, bool,
so staff can flip the default) and, when ticked, the train's create path ALSO calls `events.create_event` with: title =
the train's title, description = the train's description if it has one else the lineup sentence (`render_lineup`),
where = `Where(kind='text', text=<the first slot's twitch.tv link, or the raid-train channel's name>)` through the same
`Where` the events form builds, starts_at = the train's start, finishes_at = `raidtrain.ends_at(train)` (the last slot's
end) — and then puts the new event through the SAME review path a proposal from the site takes (`events_review_mode`
room/forum, the card, the buttons), with `requester_id` = the staff member who started the train. The event is **linked**:
`raidtrains` gains `event_id INTEGER NULL` (`ADDED_COLUMNS`, schema 50 → **51**) and `events` gains nothing (the link is
one-way; an event's card says *from raid train #N* through its description's first line, which is the events feature's
own convention for origin). Cancelling the train cancels its event through `events.cancel_for` (the one door both the
card and the API use — the spotlight build wired the same hook); the train's row and drawer show **Event #N · status**
with a link to the Events page's row. An existing train can make its event later: **Make an event for it** in the
train's tools (staff), the same function, refused in words when it already has one. Every posted word the event carries
is the events feature's (its keys); the raid-train side adds none.

**Discord:** `/raidtrain` ▸ Start a raid train's draft panel gains the same **Also make an event** toggle (a button that
flips, panels-over-slash style), and a train's card gains **Make an event** for staff — the same functions.

**Routes:** `POST /api/raidtrains` accepts `make_event: true`; `POST /api/raidtrains/{id}/event` makes one for an
existing train; both answer the train row with `event_id` and `event_status`; `GET /api/raidtrains` rows carry them.
Contract rows + mock rows (one seeded train with an event, one without) + `test_contract.py`.

## C. Keys — one, `raidtrain_event_default` (bool, false, group raidtrain): registry + mock + label + the Settings page.

## D. Logging — `raidtrain.event_made` (IMPORTANT; `train_id`, `event_id`), `raidtrain.event_cancelled` (routine, when
the train's cancel cancels it). The events feature logs its own `event.proposed` as it does for any proposal.

## E. Tests, docs, gate

`tests/test_raidtrain.py` (the event fields derived from a train: title, description fallback, where from the first
slot, start/finish), `tests/cogs/content/test_raidtrain.py` (create with the toggle → an event exists in review;
without → none; Make an event later; refused when one exists; cancel cascades), `tests/api/tools/test_raidtrain.py` (the
two routes + gate + refusals), `tests/api/test_contract.py` (page 21 + rows), `tests/storage/test_db.py` (51), the key
and kind guards, `site/mock/check.mjs` (21 pages). Both `pytest -n 8` orders, `ruff`, ES parse, `check.mjs`, the six node
tests, env cleared. A headless render of the new page (list, drawer, Start a raid train with the toggle) and of the
Events page (no raid-train sections left) with the console read; 390 px overflow check. Docs: `code-notes.md`; this doc's
`## Deviations` + `## What was NOT verified`; `raidtrain-panel-design.md` and `events-panel-design.md` one dated line
each; `architecture.md` (pages 21, schema 51, keys, kinds, routes); `docs/info/README.md`; `ux-audit.md` events row;
`sweeps.md` rows `RT-a…` (a: the rail has Raid trains under Runs the cookout and the Events page has no raid-train
section; b: Start a raid train with *Also make an event* → a train AND an event in review, the event's card names the
train; c: Make an event for it on an existing train; d: cancel the train → the event is cancelled; e: `/raidtrain`'s
toggle does the same). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: an
added column through `ADDED_COLUMNS`.

## Deviations

Written by the BUILD agent, **2026-09-20**, on branch `raidtrain-page` off `main` `e177b27`
(commits `5afbf99` the backend, `69ddebc` the page, `a31599a` the tests, plus this doc sweep).
Everything not listed here was built as §A–§E say.

1. ⚠️ **The list is a `grid-table` whose ROW is the button, and a row opens a DRAWER — §A's
   *"moved not rewritten"* could not survive §A's own six tests.** Today's construct is a
   `table()` with an **Open** button that grows a SECOND section (`Train #N — …`) under the list.
   That fails audit test 2 (nothing about the row looks clickable) and test 3 (one train in two
   places on one page). So the list is `page-posts.js:postRow`'s construct — `button.grid-row`
   with a chevron — and the detail is `ui.js:openDrawer`. **Every move is the same move**: the
   slot Take off / Put somebody in, Change two slots round, Lock / Open it for sign-ups, Call it
   off, all against the same routes with the same words. Nothing was dropped; only the door
   changed.
2. **The scope control is a chip bar, not a `Show` select.** Chips are what the audit's own
   worked example uses and what `page-posts.js` shipped, and they read at 390 px without a
   `select` popup. The three scopes are unchanged (`upcoming` / `past` / `all`).
3. **`Also make an event` is a `ui.js:segment` (Yes / No), not a checkbox input.** There is no
   checkbox anywhere on this site and no stylesheet rule for one; `segment` is what every `bool`
   settings row already renders as, so the tick box looks like every other yes/no on the
   dashboard. It still starts wherever `raidtrain_event_default` points.
4. ⚠️ **The event's `Where` is `Where('other', None, <the twitch.tv link>)`, not §B's
   `Where(kind='text', text=…)`.** A row with `where_kind='text'` and `where_channel_id` NULL is
   a shape `events.read_where` cannot read back — it falls through to `WHERE_OTHER` anyway — so
   writing it would have stored a lie. With nobody on the lineup yet the fallback is the real
   thing: `events.where_of_channel(<the lineup channel>)`, which gives `text` AND the channel id,
   the same value the events form writes when somebody picks a channel.
5. **`events.propose_from` is NEW, in `cogs/community/events.py`, and `submit_draft` now calls
   it too.** §B says the train's event takes "the SAME review path a proposal from the site
   takes". `submit_event` is that path, but its two view factories (`handoff_review_view`,
   `moving_notice_view`) live in the events COG, so calling it from the raid-train cog would
   have meant a second place that knows how a review card is wired. One door, one home; the
   raid-train side imports it lazily, the way `events.drop_spotlight` imports the spotlight cog.
6. ⚠️ **`cancel_linked_event` re-reads the event AFTER `cancel_for` instead of trusting its
   return.** `cancel_for` does the state change first and the channel RENAME last, and the rename
   is not wrapped — a cosmetic failure there throws out of a cancel that has already happened.
   Checklist 12 says the cosmetic must not abort the state change, so the row is written on what
   the database says afterwards, not on whether the call returned. Caught by the fake guild,
   which had no `channel.edit`.
7. **`POST /api/raidtrains` now answers the COG's sentence**, not the router's own `CREATED`
   (which is deleted). The event's sentence is appended to the train's by `create_and_publish`,
   so a router that re-wrote the first half would have thrown the second half away. The site's
   *is up with N slot(s) of M minutes* wording is unchanged inside it.
8. **The drawer's link to the event is `/events.html`, not a deep link to its row.** The Events
   page has no hash deep link (`page-events.js` keeps `state.open` in memory), so there is
   nothing to point at. The line beside it names the event by number and status, which is what a
   person needs to find it. An `events.html#<id>` deep link is a one-line follow-up on that page.
9. **No guide linked `events.html#raidtrains`** — measured, zero hits in `guides_seed.json` and
   `docs/access/guides-capture.md`. Guides reach a feature's page through
   `logkinds.FEATURE_PAGES`, which this build re-points (`raidtrain` → `raidtrain.html`), and the
   mock's own copy (`server.mjs:GUIDE_FEATURE_PAGES`) with it. That one edit also moves the
   `/raidtrain` panel's **Open on the site** button and the action-log footer, so the guides side
   needed no edit at all.
10. **`tests/api/conftest.py`'s `WebChannel` gained a `channels` list on a CATEGORY row, and
    `tests/cogs/content/test_raidtrain.py`'s fakes gained `create_text_channel`, `channel.type`
    and `channel.edit`.** `events.events_category` tells a category from a channel by
    `hasattr(…, "channels")`, and the review room is a real `create_text_channel` call — without
    those the contract entry for the new route could only ever be a 409. The category attribute
    is deliberately NOT given to text rows, so `not_a_category` is still reachable.
11. **`tests/api/test_contract.py`'s seed sets `events_category_id`.** Same reason: the route's
    contract entry has to answer 200, and a review room needs somewhere to go.
12. **`Make an event` sits on card row 3, beside `Call it off…`, not row 2.** Row 2 already
    reaches four controls in the worst case (Give back #N · Put somebody in… · Change two slots
    round… · Lock the lineup); a fifth would have been exactly Discord's ceiling with no room
    left. Row 3 tops out at four. There is a parametrised test on the ceiling.
13. **`page-preview-events.js` keeps its raid-train tab**, with its `previewWas` line rewritten
    to say the page moved. §A asked for "one line saying the page moved" and that is the line;
    the tab itself is the record of what the Events page used to carry, and the preview is
    deleted whole when the Events page ships its own stage-3 build.
14. **The mock seed has THREE trains, not two.** `POST /api/raidtrains/{id}/event` is exercised
    by `check.mjs` against `raid_train_id = 1`, so train 1 must NOT already carry an event; a new
    train 3 (*Charity marathon*, open, upcoming) carries event #4 instead, so the list shows one
    train with an event and one without in the default `upcoming` scope. `nextRaidTrain` moves
    3 → 4.

## What was NOT verified

- ⚠️ **Nothing has met Discord.** No bot token was looked for and none was used. The
  `/raidtrain` draft toggle, the card's **Make an event** button and the review card the event
  lands on were exercised only through the test fakes — no panel was opened in a real client, no
  review room was created in a real guild, and no raid train has ever run in production
  (`raidtrain_mode` has been `off` since the v76 landing, and this build did not read the live
  store).
- ⚠️ **The migration has NOT run on the live database.** `raid_trains.event_id` exists in
  `ADDED_COLUMNS` and is applied by `Database.connect`, and a 50 → 51 file was migrated in a
  test — but only against a temporary sqlite file, never against the database on Fly. Nothing
  is deployed from this branch.
- **The rendering was against the local MOCK**, `127.0.0.1:8786`, in
  `chrome-headless-shell` 149.0.7827.22 driven over CDP — never against the real API.
- **The 390 px check measured the PAGE, not every inner box.** `documentElement.scrollWidth`
  is 390 and equals `clientWidth`, so there is no horizontal page scroll; the `grid-table`
  inside `.table-scroll` is wider than that on purpose and scrolls inside its own box, exactly
  as the Posts page's does. Whether that side-scroll is COMFORTABLE on a real phone was not
  judged.
- **No screenshot was taken and no colour, spacing or dark-mode rendering was looked at** —
  the render read the DOM (rail, section titles, row cells, drawer contents, the outcome
  sentence), not pixels.
- **`python -m black_bloc` was not run** (no token). The substitutes are the import check
  (`black_bloc.bot`, `black_bloc.api.tools.raidtrain`, `black_bloc.cogs.content.raidtrain`,
  `black_bloc.cogs.community.events`) and the full suite.
- **The command tree did not move**, so `tests/test_bot.py`'s count was neither re-measured nor
  edited — this build adds no command.
- **`docs/access/OWNER_GUIDE.md` was not touched** and still has no raid-train page row; it was
  out of this build's scope and is a named gap rather than an oversight.
