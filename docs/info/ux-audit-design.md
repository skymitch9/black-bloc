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
