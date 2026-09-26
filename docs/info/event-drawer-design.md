# An event opens in a drawer — the facts that are set, the decision, the edit folded

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

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
