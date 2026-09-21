# Raid trains — their own dashboard page, and a train that makes an event through the events set-up

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-20 21:2x), dispatched to
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

*(the build agent writes here what it had to do differently, dated)*
