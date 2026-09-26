# An event opens in a drawer — the facts that are set, the decision, the edit folded

> ✅ **2026-09-25 — LIVE as v166 19:30** (merge `0eb2650d`, and `event-links` merge `b0401e0c` in the same release; release commit `b06d4f1d`; boot `database ready` 02:30:22Z, `logged in` 02:30:27Z, no Traceback, `/health` 65 ms — `deploys.log`'s v166 line). No live link clicked; sweeps `ED-a`…`ED-e` are the owner's.
>
> **2026-09-25 (branch `event-links`, off `main` `271ec7f8`, code `b034cde3` + `ea781d6e`) — Deviation 1 CLOSED, 🔨 BUILT, NOT MERGED, NOT DEPLOYED.** Owner: *"make them links"*. The row (list and detail, one helper `api/tools/events.py:event_links`) now carries `announce_url`, `scheduled_event_url` and `review_url` (each `null` when absent); the drawer shows *Announced: announcement ↗*, *Discord event: on the server's Events list ↗* and the review room/post name as a link ↗, **Delete this room/post** still beside it. ⚠️ The row does not store the channel the announcement went to, so `announce_url` uses the `events_announce_channel_id` setting AT READ TIME — if staff move that setting after an event was announced, its link points at the new channel and Discord says the message is not there. With no announce channel set the row keeps `announced: true` and `announce_url: null`, and the drawer falls back to the old words. NOT verified: no link was clicked in Discord (sweep `ED-e`).

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 18:0x Phoenix),
> dispatched to Opus as branch `event-drawer`** off `main` `4b37c659` (v165 live; v166 merged and undeployed).
> **Last verified: 2026-09-25 18:0x** — by LOOKING in Chrome on the mock (`http://localhost:8797/events.html`, Open on
> event #4 *Charity marathon*): Open appends a SECTION *Event #4 — Charity marathon* under the queue (`page-events.js`
> `load()` → `state.open`, `detailCard(row)` ~`:60`, `editCard(row, say)` ~`:136`, `decide(row, say, forum)` ~`:175`) with a
> card **What #4 says** — sixteen label/value rows (Title, What it is, Where, Starts, Ends, How long, Status, Asked by,
> Decided by, Decided, Why not, Now, Review channel, Announced, Scheduled event, Proposed), seven of them `—` or `no`
> for a pending event — then a card **Change it** holding the whole edit form (Title, What it is, Where select, Where
> or a link, Starts + zone, How long, Save) with a one-line warning above it; the decision buttons (Approve / Deny /
> Cancel) live only on the QUEUE row; the *On this page* rail gains a row for the open event. The marathon drawer on the
> same page is a `<dialog>` drawer with cards. Code: `site/public/assets/page-events.js` (329 lines before the marathon
> section joined), `ui.js` (`openDrawer`, `card`, `foldout`, `field`, `askForm`, `badge`, `when`), `api/tools/events.py`
> (`GET /{event_id}`, `PUT /{event_id}`, `approve` / `deny` / `cancel`, `spotlight`, `room/delete`, `forum`),
> `events.py:where_link`. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 18:0x Phoenix)

*"the outer page looks good … now we need to work on the modal that opens when you click on an event"*

**What is wrong, named:** it is not a modal, it is a section that grows the page; it lists every field whether or not it
has a value; the decision is somewhere else (the row); the edit form is always open and as tall as the facts.

## A. The drawer

**Open** on a queue row (and the title link, and `#detail=<id>` / `events.html#event-<id>` deep links — keep `#detail`
working) opens a **drawer** (`openDrawer`, the marathon pattern): title = the event's title; the header line = the
status badge · *asked by {name}* · `<start> – <end>` (`when()` range, the zone word the page already uses).

Cards, in order — **a fact with no value is not drawn**:

1. **The event** — *What it is* (the text, as a paragraph); *Where* (a channel mention or the link, as a link; the
   *Spotlight this stream* move beside it when Where is a `twitch.tv` URL and the event is approved — the existing
   `POST /{id}/spotlight`); *When* (`start – end · how long · zone`); *Review* (forum: *post ↗*; room: *#channel*, with
   **Delete this room** when the existing move applies); *Announced* (only when yes: the message link); *Discord event*
   (only when one exists: its link). The proposer's avatar + name on the header line, not a row.
2. **Decide** — the three moves the queue row has (**Approve** / **Deny…** with the reason dialog / **Cancel…** with a
   confirm), rendered only when the status allows them (the same allowed-transition rule the row uses); a decided
   event shows *Decided by {name}, {when}* and *Why not: {reason}* here instead of buttons.
3. **Marathon** — only when linked: *AGDQ 2027 — 3 BaF runs · [Open ↗]* (`events.html#marathon-<id>`); and the *marathon
   run* line when the event is a run's (from the event-modes build: `marathon: {id, name, line}` on the row).
4. **Change it** — a **shut `foldout`** holding the existing edit form unchanged (Title, What it is, Where, link, Starts +
   zone, How long, Save); the warning sentence becomes the foldout's help line. **Save keeps the drawer open** and redraws
   it with the fresh row (the `redrawRow` pattern from `page-golive.js`: re-read `GET /api/events/{id}`, `openDrawer`
   again with the same notice).
5. A quiet foot: *Proposed {when}* · *#{id}*.

Every write (approve / deny / cancel / save / spotlight / delete room) redraws the drawer and refreshes the queue
underneath; the `say` notice stays in the drawer. The **section** and its rail row go; the *On this page* rail is
back to *Events · Marathons · Settings and logs*.

## B. Nothing else changes

No routes, keys, schema or bot-side change. The queue row keeps Open and its three moves (they are the fast path;
the drawer is the full one). The Events page's other sections are untouched. Words are constants (page words).

## C. Tests, docs, gate

`node --check`, the existing node tests, `check.mjs`; a headless render of `events.html` with an event open
(`#detail=4` or the Open press) at 1400 and 390 px, zero console errors, and LOOK: no `—` row, Decide in the drawer,
Change it shut. The Python suite is unaffected (run it once anyway, `-n 8`). Docs: `code-notes.md`; this doc's foot;
`docs/info/README.md` (one row); one dated line at the top of `events-forum-design.md` and `marathon-ux-design.md`;
`sweeps.md` rows `ED-a…` (a: Open on a pending event → a drawer with the facts that are set and Approve / Deny /
Cancel; b: Change it is shut, opens, Save keeps the drawer open; c: an approved Twitch event shows Spotlight this
stream; d: a linked marathon shows its line). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.

## Deviations

Built on branch `event-drawer` (off `main` `ac4e79e2`), code commit `847874ed`. 🔨 **BUILT, NOT MERGED, NOT DEPLOYED.**

1. ✅ **CLOSED 2026-09-25 by `event-links` (see the dated line at the top).** **Announced, Discord event and a forum post show as words, not links.** The event row carries only `announced` /
   `scheduled` booleans and the review place's id, and the site knows no guild id, so a message / event / post URL
   needs a route change (§B forbids one). *Announced* reads *yes — the announcement is up*, *Discord event* reads
   *made — it is on the server's Events list*, the review place is its name (`nameNode`) as the section showed it.
2. **Delete this post as well as Delete this room.** `POST /{id}/room/delete` removes either kind (`NO_PLACE`), so the
   button follows the kind (staff final say). Its confirm carries the route's optional `note` (*A line the host is sent
   (if the event is still open)*, the Discord card's own label) and says an open event is called off with it.
3. **Move to the forum sits beside the review channel**, not in Decide — it is a move of the room, not a decision. The
   queue row keeps it too. The two share `event-drawer.js:forumMove`.
4. **A decided event shows *Decided by …* AND the moves still allowed** (an approved event keeps **Cancel…**), not the
   decision *instead of* buttons — dropping Cancel from the drawer would lose a move. *Why not* shows only when set.
5. **Spotlight this stream is decided on the page** by a mirror of `spotlight_login` (approved, Where is *somewhere
   else*, one `twitch.tv/<login>` address). The route still decides; a refusal shows its sentence.
6. **The mock gained `POST /api/events/{id}/spotlight`** so the move can be pressed there; it answers in words and logs
   `web.golive.spotlight_added` but does NOT add a Go-live row. `contract.json` has NO entry for it (the real router
   would need the spotlight path faked — not attempted). The contract's `GET /api/events/{event_id}` nested list grew
   by the eleven keys the drawer reads (all already in `event_row`); `read_by` labels moved to `event-drawer.js`.
7. **Code shape:** the drawer is its own module, `site/public/assets/event-drawer.js` (the `marathons-section.js`
   pattern); `whereControl` and the editor moved there unchanged. `page-events.js` went from 401 to 188 lines.
8. **A settled event gets a quiet sentence** (*This one is settled…*) where Change it would be, not a foldout that
   opens onto a refusal.
9. **After Save the drawer redraws with Change it shut** — the fresh facts show the edit and the outcome sits at the
   top of the drawer. A refused Save shows its sentence under Save, inside the fold, with every field as typed.
10. **A redraw keeps the old content until the fresh row lands** (no *Getting the event…* flash); only a first open
    shows it.
11. **`openEvent` yields one task before drawing** (`event-drawer.js:tick`), so the marathon drawer's own `close`
    handler runs first and forgets its id; otherwise *Open ↗* from an event back to the marathon it came from would be
    ignored (its hash would equal the marathon section's stale `shown.id`). The round trip was pressed and works.
12. **Where shows the channel and the typed place together** when both are set (a channel with a Twitch link beside
    it), and a one-word address becomes a link (a loose mirror of `events.py:where_link`: `http(s)://…` or a bare
    host).
13. **Commit shape:** one code commit and one docs commit, not the four boundaries the brief listed — the cards, the
    fold, the redraw and the deep links were built and rendered together.

## What was NOT verified

- **Nothing met the real bot or Discord.** Every press was against this worktree's mock (`MOCK_PORT=8803`, default
  `MOCK_TEST_MODE`) in `chrome-headless-shell` 149.0.7827.22 over raw CDP.
- **Pressed on the mock:** the row's Open (#4), `#detail=4` (rewritten to `#event-4`), `#event-5`, **Approve** on #4
  (the drawer redrew as *approved* with *Decided by*, Cancel and Spotlight this stream; the queue's count fell under
  it), **Deny** with a blank reason (the route's sentence shown in the drawer) and with a reason (*Why not* shown,
  Change it replaced by the settled line), **Save** on #3 (title changed, drawer stayed open, queue updated),
  **Spotlight this stream** on #5 (the route's words), the Marathon card's **Open ↗** (the AGDQ drawer), the marathon
  drawer's Event **Open ↗** into #5 and back, and Close (the hash cleared).
- **Not pressed:** Cancel… and Delete this room from the drawer, Deny… and Cancel… on the row after this change (they
  are the same `eventMoves` code), browser Back while a drawer is open.
- **Never rendered:** *Move to the forum* in the drawer (the mock's review mode is not `forum`), an event with *Now*
  (`moved_word`) or *Announced* set, a marathon-**run** event. A forum **post** WAS rendered once (after `check.mjs`
  moved #3 into the mock forum): *Review post* with the post's id (the mock cannot name it) and **Delete this post**.
  The settled sentence was rendered as a dashed `sayNothing` box, then made a quiet help line — that last form was not
  re-rendered.
- **Mock quirks seen, not changed:** seed #4 ends before it starts (*0m*); Save moves the start by the zone offset
  because the mock reads `start` as UTC and ignores `tz` — the editor code is unchanged from before. #5's description
  shows a raw `<#…>` mention, as the section did.
- Light theme, a browser zone other than America/Phoenix, and keyboard focus order inside the drawer were not checked.
