# The dashboard UX audit — good menus and good page content, page by page

> **Audience:** Fable (to review and kick off), then the audit agent, then the per-page builds.
> **Status:** TRACKED · 📐 **REVIEWED by Fable 2026-09-20 16:1x — the six tests in §C stand as written — and
> STAGE 1 DONE** (`docs/info/ux-audit.md`, 20 pages ranked) · **STAGE 2 SHIPPED as twelve in-site PREVIEW pages, v144 2026-09-20 17:34**
> (`site/public/preview/<page>.html`, real shell + real components over static seeds — the owner switched from standalone mocks
> to these 16:4x; each is deleted when its real page ships) · **STAGE 3 done for TWO pages** — go-live (v142, its own
> design) and **posts (branch `posts-page`, 2026-09-20, ⚠️ not merged and not deployed; its preview is deleted and its
> Deviations are at the foot of this file)**;
> the rest wait on the owner's walk of the previews. No other real page has been changed. **Last verified: 2026-09-20 15:3x** against `main` `22753ae`
> (v141 live): 20 pages under `site/public/*.html`, section counts measured per page (table in §B),
> `site/public/assets/page-golive.js` read in full (845 lines, twelve top-level sections).
> ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-20 15:3x)

> *"on the golive page the youtube and twitch experiences are basically different experiences, this is
> crap. can we redesign this page to have less menus and a more unified experience? do a mock or fake
> page first so we don't effect what the end users see"*

and, in the same breath:

> *"after we do this page, we probably should audit all the pages and make sure everything is the best
> ux. We have a great layout and pages, now we need good menus and page content. I know that Pop have
> confusion on verifying the post on posts page. She couldnt tell where to edit existing post."*

**The reading.** The shell is not the problem — the rail, the theme, the tables, the type are all fine
and the owner says so. The problem is one level down: **what each page is made of, in what order, and
how many separate places a person has to visit to do one thing.** This is the structural twin of the
[posted-strings audit](posted-strings-audit.md), which did the same job for the bot's *words*.

## A. The two findings we already have — the audit starts from these, not from taste

**1. A real member could not do a real task (2026-09-20, reported by the owner).** Pop, a staff member,
on the **Posts** page: she could not tell whether the post had gone out, and she could not find where
to edit an existing post. ⚠️ This is the most valuable thing in this document — an observed failure by
somebody who was not looking for one. Whatever the audit recommends, it must explain how Pop's two
minutes would have gone differently. ~~Measured against `page-posts.js`: "changes not yet posted" is text inside that view, not state on the row.~~
⚠️ **CORRECTED by the audit (2026-09-20 16:2x, `ux-audit.md` §4.19):** the status IS on the row (`statusPills`,
`page-posts.js:132`, fed by `status` per row from `/api/posts`). Four RENDERING defects made it invisible: the
status dot is permanently grey (`data-tone` set where the stylesheet keys off `data-state`), *posted* and *not posted*
draw in the same muted micro-caps (`badge(…, 'quiet')` — a tone no stylesheet defines), the sentence is one small
line under a 160-character body preview, and the only way into a post is `button.row-name.link` — a class that
matches no CSS rule, so it takes browser-default chrome with no word saying edit and no chevron — while the bold
**Make it** button sits level with the list heading. The finding survives; the fix is attribute-level and cheaper
than a redesign.

**2. Go-live splits one job across twelve sections.** Measured in `page-golive.js:load()`: Twitch links ·
Opt-outs · Recent streams · Announcement wording · Go-live settings · Go-live logs · YouTube channels ·
YouTube settings · YouTube logs · Pings · Ping role settings · Ping role logs. A single streamer can
appear in **four** of them, there are **two** separate *Link a member* cards, **three** settings blocks
and **three** log blocks — for what a person thinks of as one question: *who gets announced when they
go live?*

**The worked answer** is the mock published 2026-09-20: <https://claude.ai/artifact/VGiR2jgHui9E4D9MbCKyw6>
— five sections instead of twelve, one row per person with both platforms on it, one announcement
wording with a platform toggle, and everything rarely touched folded into one drawer. **Version 2 (16:0x) puts it
inside the REAL shell** — the rail with its four groups and mode dots, the top bar, the on-this-page list with
Expand all / Collapse all, the page head with Refresh and one primary action — so it can be judged as a page
rather than a fragment. It is a picture to react to, not code; nothing in it is wired to the bot. **Treat it as the pattern the audit measures other
pages against, not as a design already approved.**

## B. What is there now (measured 2026-09-20, `main` `22753ae`)

20 pages. Sections counted as top-level `section(` calls; the last column counts `namespaceSettings` +
`logsSection` blocks, i.e. the machinery rather than the work.

| Page | Sections | Settings + log blocks |
|---|---:|---:|
| rolemenus | 9 | 3 |
| requests | 9 | 2 |
| polls | 8 | 2 |
| chat | 8 | 2 |
| golive | 6 | 8 |
| modmail | 5 | 4 |
| health | 5 | 0 |
| events | 5 | 6 |
| guides | 4 | 2 |
| tempvoice | 3 | 4 |
| moderation | 3 | 2 |
| minutes | 3 | 2 |
| birthdays | 3 | 4 |
| automod | 3 | 4 |
| posts | 2 | 2 |
| honeypot | 2 | 4 |
| audit | 2 | 0 |
| settings | 1 | 2 |
| index (overview) | 0 | 0 |
| members | 0 | 0 |

⚠️ **CORRECTED by the audit (2026-09-20 16:2x):** the *Settings + log blocks* column above counted each `import`
line as a call, so it is inflated by one per imported name — `honeypot` is 2 work / **2** machinery, not 2 / 4, and the
same for `birthdays` and `tempvoice`. The defect this paragraph was reaching for is real but lives on **`automod`
(four of its five sections are machinery)** and `golive` (six). The *Sections* column was right for all 20. The
audit's own table in [`ux-audit.md`](ux-audit.md) §1 is the measured one; this table stays as the pre-audit estimate.

## C. What "good" means here, concretely enough for an agent to judge

Six tests. Each is answerable from the code without opinion, and each traces to one of the two findings.

1. **The state of a thing is visible where the thing is listed** — not inside it, and never only inside a
   settings block. (Pop, finding 1: a post's row must say *posted* / *not posted* / *changed since it was
   posted*.)
2. **The primary action is reachable without learning the page.** Name each page's one primary action and
   count what stands between arriving and doing it. A row that must be clicked to reveal anything must
   look clickable.
3. **One subject, one place.** Count how many sections a single person / post / poll / request appears in.
   More than one is the go-live defect.
4. **Machinery does not outnumber work.** Settings and logs are reference, not the page. One settings
   surface and one log surface per page, closed by default, is the target.
5. **Platform, source and mode are attributes of a row, not reasons for a new section.** (Twitch vs
   YouTube is the case that proves it; `via=discord` vs `via=website` is the same trap elsewhere.)
6. **Nothing is explained twice and nowhere is it explained zero times.** A refusal, an empty state and a
   "this is in shadow" note each belong in exactly one place on the page.

## D. How to run it — three stages, and only the first is dispatched now

**Stage 1 — the audit, read-only, one agent, no code changes.** Produces
`docs/info/ux-audit.md`: one section per page with (a) the section list in load order, (b) the page's one
primary action and the count of what stands before it, (c) each of the six tests as pass / fail with the
evidence, (d) a one-paragraph proposal, (e) a severity call. Plus a table at the top ranking all 20 pages
so the owner can pick. Same shape and discipline as the strings audit: measured, no fixes, nothing else
touched. ⚠️ It must open `page-*.js` for every page, not infer from the counts above.

**Stage 2 — mocks for the pages the owner picks.** One published artifact per page, built from the
page's real data shape, marked as a mock. He reacts; nothing ships. Go-live's mock already exists and is
stage 2 done for one page.

**Stage 3 — builds, one page per branch**, each with its own short design doc, the usual gate, sweeps
rows and a deploy. Never more than one page's structure in flight at once — these change what staff see.

## E. Guards

- **No page is changed until the owner picks it**, and the mock comes first. His words: *"do a mock or
  fake page first so we don't effect what the end users see."*
- **The bot's Discord panels are OUT of scope here** — they have their own rule (one command, one panel)
  and their own program doc. If the audit finds a Discord panel with the same defect, it says so in one
  line and moves on.
- **Wording is the other audit's job.** If a fix needs new words, name the key and leave it to
  [posted-strings-audit.md](posted-strings-audit.md); do not key strings in a structure build.
- **`events`, `requests` and `modmail` are LIVE to members** (test mode lifted 2026-09-18). A structure
  build on those three pages changes what staff see the same day it deploys.

## Deviations

*(the audit agent and each build write here, dated)*

**2026-09-20, branch `posts-page`, off `main` `552af36` — STAGE 3 for `posts`.** The preview the
owner approved is the page now (`site/public/assets/page-posts.js`), live against the real API;
`site/public/preview/posts.html` and `assets/page-preview-posts.js` are deleted, per *each preview
is deleted when its real page ships*. Fourteen deviations, in the order they would surprise a
reader of the preview.

1. ⚠️ **`ui.js:saveBar` is NOT used in the drawer.** It docks itself into `#dockzone` at the foot
   of the PAGE, and `openDrawer` is a modal `<dialog>` — the dock would render behind the backdrop
   in an inert document and could never be pressed. The three things it did are in the drawer
   instead: a **Save Changes** button, a **Discard** button drawn only while something is dirty,
   and an *N changes pending* line. The docked bar is still what the Settings fold uses, because
   that one is on the page.
2. **Save with nothing changed is now a refusal in words** — *"Nothing has changed, so nothing was
   saved."* Today's page sent the `PUT` regardless and said *Saved.* The over-limit refusal keeps
   its own sentence and moves from the dock into the drawer's notice.
3. **The editor's two-column `postgrid` is stacked inside the drawer** by one inline
   `grid-template-columns` declaration (through `ui.js:el`, so the CSSOM, so `style-src 'self'`).
   The drawer is `min(30rem, 100vw)`; the stylesheet's own single-column rule keys off the
   VIEWPORT at 900 px, so on a wide window the box and the Discord preview would have been two
   224 px columns. **`site.css` is untouched by this build.**
4. **The Logs fold holds the REAL shared `logsSection('posts')`, demoted** — its `.sect-inner`
   children are lifted into `ui.js:foldout`, so the block keeps its search, its Important/All
   switch, its kind chips and its pager while the *On this page* rail still lists exactly two
   sections. One step further than `page-golive.js:unsection`, which only strips the class.
5. ⚠️ **View a version draws INSIDE the drawer, not in a second one.** `openDrawer` owns a single
   `<dialog>` and replaces its contents, so the nested call today's page makes would have destroyed
   the editor behind it. The version renders under a *Version N of <title>* heading with a **Hide**
   beside it.
6. **`ui.js:ask` DOES stack over the drawer** — it is a different `<dialog>` — so the Delete and
   *Use this version* confirmations are unchanged. Measured in `chrome-headless-shell`, not
   assumed: the confirm opened and the drawer stayed open under it.
7. **The hash deep link survives.** `posts.html#welcome` opens that post's drawer on arrival,
   clicking a row writes the hash, closing clears it. ⚠️ `forgetHash` checks the dialog is
   genuinely shut first, because `close` is dispatched a task LATE: measured, the *New post →
   create → open the new post* path had its hash wiped by the previous drawer's close event
   landing on the new drawer's handler.
8. **The mode is a read-only `modeChip` in the section head, not a `modeSwitch` in the page head**
   (the page-head button goes, as the design asked). `posts_mode` is one of the three keys in the
   Settings fold, so it is still changeable on this page — nothing is lost, it moved.
9. **The API's notes and the test-mode sentence render through `ui.js:boldParts`**, not with their
   `**` stripped as the preview did. Same words, and the emphasis the bot writes survives.
10. **`site/public/posts.html` is UNCHANGED.** Diffed against the preview's shell: only the
    `<title>`, the subtitle and the `<script src>` ever differed, and all three were already right
    for the real page.
11. **The Settings fold keeps today's three-key filter.** `posts_versions_keep` and
    `posts_versions_summary_chars` are still reachable only from the Settings page — that is the
    state this build inherited, and widening it was out of scope for a structure change. Named
    here so the next pass does not have to re-measure it.
12. **`page-previews.js:previewCard` now draws the *Open the preview* door only for a page that has
    not shipped.** Posts gets the `live` badge and its **Live today** door alone. Side effect, and a
    defect fix on the same page: go-live's card had been pointing at `/preview/golive.html`, which
    has not existed since that preview was deleted.
13. **`site/mock/contract.json` — one `read_by` label renamed** (*"page-posts.js save bar"* →
    *"page-posts.js row drawer ▸ Save Changes"*). `read_by` is read by neither `check.mjs` nor
    `tests/api/test_contract.py`; the route table is otherwise byte-identical, and `check.mjs`
    still reports 20 pages / 192 routes.
14. **No Python changed**, and `ui.js`, `layout.js`, `postversions.js`, `clipmd.js`, `logs.js`,
    `api.js`, `app.js` and `site.css` are all untouched — verified by `git diff --stat`, which is
    the one claim here that is measured rather than read.

**The six tests of §C, against the page that shipped.** **T1 pass** — the state is on the row:
`dot-sm[data-tone]` (a rule that exists, unlike the old `.row[data-tone]`), a *Status* column of
pills toned `ok` / `info` / `warn` / `danger` instead of the undefined `quiet`, and a *Channel*
column that is the whole *"Posted in #welcome. It is pinned."* sentence. **T2 pass** — the primary
action is *edit an existing post*, and the distance is **0 sections, 1 click on a control that
looks like one**: the row IS a `button.grid-row` with hover, focus and cursor rules and a trailing
chevron. **T3 pass** — a post is in exactly one place, and the separate detail page that was its
second home is gone. **T4 pass** — two sections, work first and open, machinery second and shut;
one settings surface and one log surface, one fold each. **T5 pass** — *posted in shadow* is a
pill on the row and a chip in the head, never a second section; the four chips filter one table.
**T6 pass** — the shadow behaviour is written once (the API's note, rendered in the section head,
with the page's own copy of it gone), the logs and settings blocks keep their own notes instead of
the page repeating them, and every empty state is written exactly once.
### 2026-09-20 — the columns reordered every page (branch `small-fixes`, fix 1 of 4)

`layout.js:mountColumns` balanced each run of blocks **greedily**: every block joined whichever
column was shorter at that moment. That is the right answer for two columns of equal height and
the wrong one for reading order — a page's main list is usually its tallest block, so it pushed
everything after it into the left column and landed itself on the right.

**Measured before**, mock `requests.html` in a headless browser (`chrome-headless-shell`
149.0.7827.22 over CDP, mock on `MOCK_PORT=8792`): left column *In progress · Ready to check ·
On hold*, right column **Open** · Done · Declined · File a request · Settings, then Logs full
width. `polls.html`: left *Polls*, right *Pending review*, then the full-width pair, then left
*Closed · Archive*, right *Create a poll · Settings · Logs*.

**The rule chosen: document order with ONE break.** `columns.js:columnSplit(heights)` returns the
one index that makes the two column heights most even; the left column is the first `n` blocks and
the right column is the rest. Every other rule considered (a `data-span` opt-out, a list of
"machinery" section slugs, a "never demote the first block" patch on top of the greedy pass) needs
the code to KNOW which section is the main one — a fact only the page has, spelt differently on
every page. A prefix split needs to know nothing: whatever the page rendered first is on the left,
because a prefix is a prefix.

**Measured after**, same browser, same mock: `requests.html` left column **Open** (under the page's
own intro card), right column In progress · Ready to check · On hold · Done · Declined · File a
request · Settings. `polls.html` left *Polls* / right *Pending review*, then *Closed · Archive* /
*Create a poll · Settings · Logs* — source order in both columns.

**Deviations.**

1. **The columns are less even than they were.** Greedy minimises height; a prefix split minimises
   it *subject to* keeping the order. On `requests.html` that is a left column of two blocks against
   a right column of seven, because the Open list is about half the run's height. That is the trade,
   and it is deliberate: an even page that reads wrong is worse than an uneven page that reads right.
2. **`columnSplit` lives in its own file**, `site/public/assets/columns.js`, not in `layout.js`:
   `layout.js` imports `ui.js`, which touches `document` at module scope, so a node test importing
   `layout.js` cannot even load it.
3. **Ties go to the earlier break** (strict `<` on the gap), so the left column is the shorter one
   when two splits are equally even. Nothing depends on it; it is written down so it is not a
   surprise later.
4. **What was NOT verified:** nothing was looked at by a person, in a real browser, at a real width,
   or against the live site. The `wide()` / `data-span` half of `mountColumns` was not changed and
   not re-measured. Only `requests.html` and `polls.html` were measured; the other eighteen pages
   were not opened.

### 2026-09-20 — every page logged a 400 on the rail badge (branch `small-fixes`, fix 2 of 4)

`shell.js:featureRequestTally` — the badge beside **Requests** in the left rail, which every page
draws — asked `/api/requests?status=pending&per_page=1`. **`pending` is not a state a request can
be in.** `black_bloc/requests.py:STATUSES` is `open, in_progress, review, hold, done, declined,
withdrawn, moved`, and `wanted_statuses` refuses anything else, so the route answered **400
`unknown_status`** and the badge fell to `null` on every page in the site. Measured before, mock in
a headless browser: `golive.html`, `polls.html` and `requests.html` each logged exactly one
`HTTP 400 …/api/requests?status=pending&per_page=1` and one red console line.

**Which side was wrong: both halves, differently.**

- **`status=pending` is the caller's mistake.** A request waiting on an answer is `open` — that is
  the state the route's own `open` count uses and the state the Requests page's first section
  lists. `shell.js` now asks `status=open`.
- **`per_page` was not the cause of the 400 — it was being ignored**, which is its own small bug:
  `requests_index` hard-coded `API_PAGE` for the limit, the offset and the answer, so a badge that
  wanted one row was served twenty and `page-requests.js` asked for `per_page=SHUT_PER_PAGE` (10) on
  the Done and Declined lists and silently got pages of 20 with a pager computed off the server's
  number. The route now takes `per_page` and clamps it, exactly as `api/tools/polls.py` does
  (`wanted_per_page`: a digit string, at least 1, at most `API_PAGE`, anything else the default).

**Measured after**, same browser, same mock: `golive.html`, `polls.html`, `requests.html` — *no 4xx,
no failed load, no console error* on any of the three.

**Guards so it cannot drift back:** a contract row for `/api/requests?status=open&per_page=1` in
`site/mock/contract.json` (so `check.mjs` AND the bot's own
`tests/api/test_contract.py::test_every_route_answers_with_the_keys_the_pages_read` fetch the
badge's exact URL and require a 200), and three tests in `tests/api/tools/test_requests.py`: the
badge's call is answered with one row, the page size is clamped, and `status=pending` is still
refused in words.

**Deviations.**

1. **`per_page=0` clamps to 1, not to the default** — `wanted_per_page` is copied from the polls
   route deliberately, and that is what the polls route does. One shape, two routes.
2. **`/api/requests/mine` was NOT given `per_page`**, and the mock was not either: the bot's route
   does not take it, and the mock must not accept what the bot ignores.
3. **Honouring `per_page` changes what the Requests page's Done and Declined lists show** — ten rows
   a page now, which is what the page was asking for all along, with the pager and the *Showing
   n–m of t* line agreeing for the first time. Nobody has looked at that in a real browser.
4. **What was NOT verified:** the real route was never called by the real site — everything here is
   the mock plus the bot's test client. The other two badges (`requestTally`, `pollTally`) were read
   and left alone: `/api/rolemenus/requests?status=pending` is a DIFFERENT route with its own status
   words, where `pending` is correct, and `/api/polls?status=open&per_page=1` already works.

### 2026-09-20 — `events` had a huge gap and a bunched left column (branch `events-spacing`)

The owner, looking at the mock at ~1512 px wide: *"the events page is too crowded, huge gap in the
middle and the left is bunched, space this out."* Two events pages exist on the mock
(`site/public/events.html` and the audit's static `site/public/preview/events.html`); only the real
one has the defect — the preview's every `#dash` child is already `wide()` (the banner is
`data-span="full"`, the tab switch is a `.bar`, and both `Queue` and `Reference` carry a table), so
`layout.js:mountColumns` never pairs anything into a `.twocol` there. Measured in
`chrome-headless-shell` at 1512×802, fresh load, no localStorage:

`site/public/events.html` `#dash` children in order: **Queue** (wide, table, 228 px, standalone) ·
**a `.twocol` pairing `Events forum` (348 px — forced `open: true`, `page-events.js:556`) against
`Settings` (34 px — collapsed by default, the ordinary state)**. `columnSplit` on a run of exactly
two blocks always puts one per column (`columns.js:columnSplit` only has one candidate split point
when `heights.length === 2`), so document order alone decided the pairing, not the heights — and
`Events forum`'s `open: true` means it is *always* taller than a `Settings` block nobody has opened
yet. That produced a 314 px gap under `Settings` on every fresh load, not just this one seed. Below
that: `Logs` (34 px, standalone) · `Raid trains` (34 px, standalone) · a second `.twocol` pairing
`Raid train settings` / `Raid train logs` (34/34, both collapsed, already even).

**Fix:** `page-events.js:557` — `forumBox.node.setAttribute('data-span', 'full')`, the same
attribute `page-guides.js` and `page-posts.js` already use to pin a block out of the balancer
(`code-notes.md:6451`, `:7468`). `Events forum` now stands full-width like `Queue`/`Logs`/`Raid
trains` around it; `Settings` is left alone in its run (below `RUN_MIN`) and also renders
full-width instead of pairing lopsided. No change to `columns.js` or `layout.js` — both are owned
by other agents right now and the defect did not require touching either.

**Measured after**, same page, same browser: no `.twocol` before `Raid train settings`/`Raid train
logs`; `Queue` 228 px, `Events forum` 287 px (full width lets its paragraph re-wrap shorter),
`Settings`/`Logs`/`Raid trains` each 34 px standalone, the trailing pair still 34/34. Zero console
messages. 390 px wide: `scrollWidth` equals `innerWidth` (390) on both `events.html` and
`preview/events.html` — no horizontal overflow either page.

**What was NOT verified:** the owner's own browser window, not chrome-headless-shell 149 at a
simulated 1512×802 — nothing here reaches Discord, and none of it needed to.

### 2026-09-20 — `events` loses Remove its room and the Events forum card (branch `events-trims`)

Owner, looking at the mock: *"we dont need the remove its room option, that'll happen after it
ends or is denied. whats the point of the events forum section?"* → (told it is the review-mode
card with the two settings controls) → *"yes make them settings"*. Two changes, one page,
`site/public/assets/page-events.js` only.

1. **The `Remove its room` / `Remove its post` staff button is off every event row.** The room or
   post is still removed by the bot's own end and deny paths (`black_bloc/events.py`, untouched) —
   only the website's `POST /api/events/{id}/room/delete` door and the `REMOVE_PLACE` wording are
   gone from the page. The route itself is left alone server-side, out of scope for a page-only
   build.
2. **The standalone `Events forum` card (`eventForumCard`, `forumBox`) is deleted.** Both things it
   explained — `events_review_mode` and `events_forum_channel_id` — were already rows in
   `namespaceSettings('events')`; the card was a second place showing the same two decisions,
   which is the duplicate-surface defect §C exists to catch. Its one non-duplicate part, **Make the
   forum**, now renders beside the `events_forum_channel_id` row (found by the `data-key` attribute
   `settingRow` already stamps on every row) and only while that key is blank — `namespaceSettings`
   and `section` give no per-row or head action slot, and neither was edited to add one; the row's
   returned DOM is extended in place instead, the same technique yesterday's spacing fix already
   used on a `namespaceSettings` return value.
3. `FORUM_NOTE`'s wording is dropped rather than folded into `events_review_mode`'s help — that
   help lives in `black_bloc/settings_store.py` (Python), out of scope for this page-only build; the
   existing `EVENTS_REVIEW_MODE_KEY` help already covers the room/forum distinction and "Make the
   forum on `/event` first", so nothing load-bearing was lost, though it does not repeat
   `FORUM_NOTE`'s line about the post being the review card's first message or the forum's own
   archive being the list's ceiling. Named here as a departure, not a decision.

**Measured after**, removing `Events forum` also removed the reason yesterday's fix (`data-span`
on `forumBox`) existed: with the card gone, `Settings` is alone in its run (`Queue` and `Logs` are
both wide, so nothing pairs with it) rather than being forced full-width — the same visual result,
reached because the lopsided pair no longer exists rather than because it is pinned. In a real
Chrome tab (`claude-in-chrome`, against the local mock, fresh load, no localStorage) at whatever
width the session's window happened to be: `#dash` children in order — `Queue` 210 px standalone
(has a table), `Settings` 33 px standalone (collapsed), `Logs` 33 px standalone, `Raid trains` 33
px standalone, then the pre-existing `.twocol` pairing `Raid train settings` / `Raid train logs`
(33/33) — no `Events forum` section, no lopsided pair, zero console messages before or after
pressing **Make the forum**. `node --input-type=module --check` on every `site/public/assets/*.js`,
`MOCK_PORT=8788 node site/mock/check.mjs` (20 pages, 194 routes, 24 core settings, all keys
present) and the five `site/mock/*.test.mjs` files all pass.

**What was NOT verified:** ⚠️ **1512×802 and 390 px were not measured** — `resize_window` reported
success but `window.innerWidth` never moved off the session's own (much larger) window size in
this session, and a same-origin iframe sized to those dimensions could not be read back
(`SecurityError: Blocked a frame with origin … from accessing a cross-origin frame`, from the
extension's own execution context rather than the page). No CSS changed and the only DOM addition
is a button + a `.setrow-say`-classed notice appended inside the existing flex-wrap `.setrow`, so
overflow risk is low, but that is reasoning, not a measurement — say so rather than claim the
number. Nothing here reached Discord.

### 2026-09-20 — the drawer becomes a floating centred modal (branch `centre-modal`, off `main` `e177b27`)

Owner, looking at the posts drawer with the Discord mock under the editor: *"for post the side
modal is cool but its hard to see the how this will render in discord section, lets swap the left
hand modals for floating center modals."* `ui.js:openDrawer`/`closeDrawer` (`:677`–`:697`) is the
shared construct every caller uses (`page-posts.js`, `page-golive.js`, `page-moderation.js`,
`page-modmail.js`, `postversions.js`); only `site/public/assets/site.css` changed — `dialog.drawer`
(was `:1477`, now `:1480`) and its inner classes. **No page file was touched.**

**The fix is CSS-only.** The old rule pinned the `<dialog>` to the right edge and full height
(`margin: 0 0 0 auto; height: 100dvh`). Removing that pin and giving the box its own size
(`width: min(64rem, 96vw); height: auto; max-height: min(90vh, 100dvh); margin: auto`) lets the
browser's own default `<dialog>` centring — `position: fixed; inset: 0` from the UA stylesheet,
never overridden by this file — do the centring; nothing in `ui.js` reasons about position. The
backdrop-click-closes test (`event.target === drawerNode`) and `showModal()`/`close()` are both
agnostic to where the box sits on screen, so `openDrawer`/`closeDrawer` needed **zero changes** —
every caller is untouched and no signature moved.

**Measured**, `chrome-headless-shell` 149.0.7827.22 over raw CDP (no `puppeteer` package in this
tree; driven with Node's native `WebSocket`/`fetch` against `--remote-debugging-port`), against the
worktree's own mock (`MOCK_PORT=8785`):

- **1512×802, `posts.html?as=staff`, a post opened:** dialog rect `left: 244px, right: 244px`
  (equal — centred), `width: 1024px` (`min(64rem, 96vw)` resolves to the 64rem cap at this width),
  `height: 721.8px` = exactly `90vh` (802 × .9) — the modal hit its height cap on a real post's
  content, so `.drawer-body`'s existing `overflow-y: auto` is doing real work, not just standing by.
- **The Discord mock inside is 945px = 59.06rem wide** — well past the 40rem floor — but it still
  draws BELOW the editor, not beside it: `page-posts.js:558` hard-codes
  `style="grid-template-columns: minmax(0, 1fr)"` on `.postgrid` (dated from when the drawer was
  30rem and two columns would have been 224px each — `code-notes.md:7508`, corrected in the same
  session), and that inline declaration outranks `site.css`'s 900px breakpoint at any width. **Left
  as-is on purpose** — `page-posts.js` is out of this branch's scope (no page file). A stacked
  64rem-wide column is already far more legible than a 30rem-wide one; making it two columns is a
  `page-posts.js` change for whichever branch owns that file next.
- **Escape closes it**: measured via `Input.dispatchKeyEvent` (a real key event through CDP, not a
  JS-dispatched `KeyboardEvent`, which a native `<dialog>`'s `cancel` handling ignores) — `dialog.open`
  is `false` after.
- **`ask()` stacks above the drawer, verified not assumed:** opened a post, pressed *Delete this
  post*, then read both dialogs' `.open` (both `true`) and called
  `document.elementFromPoint()` at the centre of the `ask` dialog's own rect — it returned a node
  the `ask` dialog contains, i.e. the drawer is not painting over it. Neither dialog sets
  `z-index`; the browser's top-layer stacking (most-recently-`showModal()`-ed wins) is what both
  the old and new CSS relied on.
- **Go-live's row drawer and a moderation case drawer** both opened at the same centred `1024px`
  width with real content (`.drawer-body` non-empty) and zero console errors.
- **390px phone width, `posts.html`, a post opened:** dialog rect `left: 0, width: 390` (edge to
  edge) and `document.documentElement.scrollWidth === window.innerWidth === 390` — no sideways
  scroll. This is `@media (max-width: 600px)` reverting the modal to the old drawer's full-bleed
  shape (`100vw`/`100dvh`, no margin, no radius) rather than shrinking a centred box onto a phone
  screen.
- **Zero console errors** on every page and width checked above (`posts`, `golive`, `moderation`).

**Motion.** The only animation added is an entrance fade + `scale(.97 → 1)` via `@starting-style`
on open; close stays instant (native `close()`, unchanged — matches "same Escape / backdrop / close
behaviour" from the brief). `@media (prefers-reduced-motion: reduce)` kills the `transition`
entirely, the same one-rule pattern `site.css:369`'s rail slide-in already uses.

**Deviations.**

1. **`ui.js` was not touched at all**, despite the brief scoping it as an editable file. The
   centring, sizing, motion and phone behaviour are all reachable from CSS alone because
   `openDrawer`/`closeDrawer` never reasoned about the dialog's screen position — verified by
   reading both functions in full before starting. Zero JS risk, and every caller's `openDrawer(title,
   body)` / `openDrawer(title, placeholder)` → `openDrawer(title, real)` "opened twice" pattern is
   unchanged because it was never touched.
2. **The `drawer` / `drawer-inner` / `drawer-head` / `drawer-title` / `drawer-body` class names are
   unchanged** — no alias needed, since nothing renamed them. Every page's CSS keeps applying with
   no changes on their side.
3. **`page-posts.js`'s inline single-column override on `.postgrid` was left in place** — see the
   measured section above. Named as a deviation because the brief asked to "measure the posts
   drawer's contents and pick" a width that fits "an editor column and the Discord mock beside or
   under it" — the mock ends up under, not beside, and that is a `page-posts.js` fact this branch
   cannot change.
4. **What was NOT verified:** headless only — nothing here has met a real browser window or actual
   Discord. The owner's own device/DPI was not checked. `ask()`'s stacking was verified by hit-testing
   (`elementFromPoint`), not by a human eye. The go-live and moderation drawers were opened and read
   for "does it still work", not audited row-by-row the way the posts drawer was.

### 2026-09-20 — the posts editor's `postgrid` goes two columns inside the modal (branch `posts-two-col`, off `main` `65e225b`)

The `centre-modal` deviation above (deviation 3) named the gap it left: the modal is wide enough for
the message box and the Discord mock to sit side by side, but `page-posts.js:558`'s inline
`style="grid-template-columns: minmax(0, 1fr)"` forced one column regardless, and `site.css`'s own
`.postgrid` breakpoint (`@media (max-width: 900px)`) keyed off the outer PAGE viewport, not the
dialog — a `900px`-wide browser window and a `900px`-wide dialog on a much wider window both trip
the same rule, even though the dialog in the second case has plenty of room. Files touched: only
`site/public/assets/site.css` and `site/public/assets/page-posts.js` (one line each change to the
latter — the inline `style` attribute removed).

**The fix: a container query, not a media query.** `.drawer-body` (`ui.js:openDrawer`'s wrapper,
shared by every page that opens a drawer) gets `container-type: inline-size`, so `@container`
queries inside it read the DIALOG's own rendered width. `.postgrid` is now mobile-first — one
column by default, two above `@container (min-width: 56rem)` — and the inline JS override is gone,
so CSS alone decides. Chosen over JS measurement (`ResizeObserver` + a `data-span`-style attribute)
because the fact being asked — "is the box holding this grid wide enough for two columns?" — is
exactly what a container query answers natively; JS measurement would have meant a listener, a
resize handler and a value to keep in sync with a rule CSS can already express.

**Measured**, `chrome-headless-shell` 149.0.7827.22 over raw CDP (no `puppeteer` package in this
tree), against the worktree's own mock (`MOCK_PORT=8783`):

- **1512×802, `posts.html?as=staff#welcome`, a post opened:** dialog `1024px` wide (`min(64rem,
  96vw)`'s 64rem cap, as `centre-modal` measured). `.postgrid`'s computed `grid-template-columns`:
  `479.5px 479.5px` — each column ≈ 30rem, well past the 26rem floor. The message box
  (`#post-body`)'s column and the `.dcmock` mount sit side by side with a 16px gap and no overlap
  (`left`/`right` edges: message column `261–740.5`, mock column `756.5–1236`).
- **Typing a character in the message box repaints the mock live:** appended text to `#post-body`,
  dispatched `input`, and the mock's rendered content included the new text ~250ms later (the
  existing debounced `discordMock`/`paintPreview` path — untouched by this build).
- **390px phone width:** `.postgrid`'s computed columns collapse to one (`358px`, no second value);
  `document.documentElement.scrollWidth === window.innerWidth === 390` — no horizontal overflow.
- **Zero console errors** at both widths on `posts.html`.
- **Smoke-checked `golive.html` and `settings.html`** (both also open a `dialog.drawer`) at
  1512×802 after the `.drawer-body` change: both rendered with zero console errors. Neither page
  queries a container, so `container-type: inline-size` (which only constrains the inline axis) had
  nothing to affect there.

**Deviations.**

1. **Container query (`@container (min-width: 56rem)` on `.postgrid`, `container-type: inline-size`
   on `.drawer-body`) over `ResizeObserver`/JS measurement** — see above. This is the "which" the
   brief asked to name.
2. **`.postgrid`'s breakpoint moved from a max-width media query to a min-width container query**,
   and the default flipped from two-column-collapsing-to-one to one-column-expanding-to-two
   (mobile-first). Same visual result at the widths tested; written down because a future reader
   diffing the rule against the old one will otherwise wonder why the comparison operator flipped.
3. **`container-type: inline-size` was added to `.drawer-body`, not to a `.postgrid`-specific
   wrapper** — every `dialog.drawer` user (go-live, moderation, modmail, post versions) now shares
   one query container. No other page currently uses `@container`, so nothing else changed, but the
   next build wanting a container query inside a drawer gets one for free instead of needing to add
   its own.
4. **What was NOT verified:** headless only, same as every other entry in this file — no real
   browser window, no real Discord, no human eye on the two-column layout. The owner's own
   device/DPI was not checked. Only `posts.html` was measured at both widths; `golive.html` and
   `settings.html` were smoke-checked for console errors only, not measured pixel-by-pixel. The
   `discordMock` repaint was confirmed by reading the DOM's text content, not by a screenshot.
