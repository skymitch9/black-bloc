# The dashboard UX audit — twenty pages against six tests

> **Audience:** the owner, and Fable (to pick what gets a mock next). **Status:** TRACKED
> — `docs/` is in git, so **secret NAMES only** (this file holds none).
> **Last verified: 2026-09-20** against `main` `5afd58c` (v141 live). Measured by reading all
> **20** `site/public/*.html` and all **20** `site/public/assets/page-*.js` (**10,790** lines)
> in full, plus the shared modules they are built from — `ui.js` (1,429), `layout.js` (287),
> `logs.js` (322), `shell.js` (334), `app.js` (314) — and the three stylesheets
> (`site.css`, `status-shell.css`, `estate-theme.css`) for every class the pages hand to
> `el()`. The brief is [`ux-audit-design.md`](ux-audit-design.md); §C's six tests are applied
> verbatim as Fable ruled them at 16:1x.
> ⚠️ **Two docs-only commits landed on `main` while this was being measured** (`948ff05`,
> `64ccfbc` — TODO, the info index and `costream-design.md`). `git diff --stat 5afd58c 64ccfbc`
> touches **nothing under `site/` or `black_bloc/`**, so every `file:line` below is still exact
> against `main` as this commit lands.
>
> ⏸️ **This is a LIST, not a build.** Nothing was changed. No code, no settings, no wording.
> The one file written is this one.
>
> ⚠️ **What was NOT checked, plainly.** **No browser rendered any page** and **no staff member
> was watched using one.** This is a code-structure audit: what each page is made of, in what
> order, what state it puts where, and which CSS rules exist for the classes it uses. It is not
> a usability test. Where a finding depends on what something LOOKS like, it is stated as the
> rule that does or does not exist in the stylesheet, and said to be unrendered. Nothing met the
> live bot, nothing met Discord, `pytest` was not run, and the API was read only where a page's
> claim about its own data had to be checked (`black_bloc/api/tools/posts.py`,
> `black_bloc/posts.py`). **Discord panels are out of scope** (§E) — none was read; one line
> about them is at the foot.
>
> 🔧 **`golive` is being REBUILT in parallel**, to [`golive-page-design.md`](golive-page-design.md),
> on branch `golive-page`. Its section below audits the page **as it is on `main` today**, as the
> baseline the rebuild is measured against, and is marked *rebuild in flight*.

---

## 1. The ranking — worst first

Sorted by severity, then fails-out-of-six, then sections rendered.

| # | Page | Severity | Fails /6 | Sections rendered by `load()` | …of which machinery | §B said |
|---|---|---|---:|---:|---:|---|
| 1 | **golive** 🔧 *rebuild in flight* | 🔴 | 5 | **12** | 6 | 6 / 8 |
| 2 | **posts** | 🔴 | 4 | 3 (+1 orphan card) | 2 | 2 / 2 |
| 3 | **rolemenus** | 🔴 | 4 | 9 (10 editing) | 3 | 9 / 3 |
| 4 | **minutes** | 🔴 | 3 | 4 | 2 | 3 / 2 |
| 5 | **chat** | 🟠 | 4 | 9 | 2 | 8 / 2 |
| 6 | **events** | 🟠 | 4 | 7 (9 with both open) | 4 | 5 / 6 |
| 7 | **automod** | 🟠 | 3 | 5 | 4 | 3 / 4 |
| 8 | **polls** | 🟠 | 3 | 9 | 2 | 8 / 2 |
| 9 | **modmail** | 🟠 | 3 | 6 (7 with a ticket open) | 2 | 5 / 4 |
| 10 | **requests** | 🟠 | 2 | 9 staff / 2 member | 2 | 9 / 2 |
| 11 | **settings** | 🟠 | 2 | **~26** (one per namespace + logs) | ~26 | 1 / 2 |
| 12 | **birthdays** | 🟠 | 2 | 5 | 2 | 3 / 4 |
| 13 | **honeypot** | 🟠 | 2 | 4 | 2 | 2 / 4 |
| 14 | **tempvoice** | 🟢 | 1 | 5 | 2 | 3 / 4 |
| 15 | **health** | 🟢 | 1 | 5 | 0 | 5 / 0 |
| 16 | **moderation** | 🟢 | 1 | 4 (+2 full-width blocks) | 2 | 3 / 2 |
| 17 | **guides** | 🟢 | 1 | 5 hub / 0 detail | 2 | 4 / 2 |
| 18 | **members** | 🟢 | 1 | **0** | 0 | 0 / 0 |
| 19 | **index** (overview) | 🟢 | 1 | **0** | 0 | 0 / 0 |
| 20 | **audit** (Logs) | 🟢 | 0 | 2 | 2 (its job) | 2 / 0 |

### §B's counts, verified — one column is right and one is wrong

⚠️ **§B's *Sections* column is EXACTLY right for all 20 pages** and I reproduce it above in the
last column. It counts `section(` call sites in the page module, which is what it says it does.

⚠️ **§B's *Settings + log blocks* column is INFLATED BY ONE PER IMPORTED NAME** and must not be
used. It counted the `import` line as a call. Measured (`grep -c 'namespaceSettings('` and
`grep -c 'logsSection('`, which exclude imports because imports carry no parenthesis):

| Page | §B said | Measured | Page | §B said | Measured |
|---|---:|---:|---|---:|---:|
| golive | 8 | **6** | modmail | 4 | **2** |
| events | 6 | **4** | moderation | 2 | **1** |
| honeypot | 4 | **2** | minutes | 2 | **1** |
| birthdays | 4 | **2** | guides | 2 | **1** |
| tempvoice | 4 | **2** | posts | 2 | **1** |
| automod | 4 | **2** | settings | 2 | **1** |
| rolemenus | 3 | **2** | polls / chat / requests | 2 | **1** each |

So **§B's headline warning — *"`honeypot` has two sections of work and four of machinery"* — is
wrong.** Honeypot renders **four sections in total**: two of work (Hits, Trap channels) and two
of machinery (Settings, Logs). The ratio is 1:1, not 1:2. The tell §B was reaching for is real
but it lives elsewhere: **`automod` is the worst ratio in the tree — four of its five sections
are machinery** (`page-automod.js:129–135`: Mode, Exemptions, All automod settings and Logs are
all settings or logs; only *Rules* is work). `golive`'s 6 is still the largest absolute count.

The *Sections rendered* column above is a different measurement again, and is the one that
matters to a person: it counts the `section.sect` nodes actually in `#dash` after `load()`,
which includes the sections `namespaceSettings()` and `logsSection()` build (`ui.js:1288`,
`logs.js:208`) and multiplies a `section()` called in a loop. **The `settings` page is the case
that proves the difference: §B credits it with 1 section; it renders about 26**, one per
settings namespace (`page-settings.js:142–148`; the docs tree measures 24 namespaces since
branch `events-group`, 2026-09-20, folded `event` onto `events` — it was 25).

---

## 2. The patterns that repeat

Eight things recur across the twenty pages; each is named here once and cited per page below.

**(1) Sixteen of twenty pages leave their primary-action slot empty.** Every one of the 20
`site/public/*.html` files carries `<div class="page-head-aside" id="page-aside">` beside the
page title. Exactly **four** modules ever write to it — `page-guides.js:1186`,
`page-moderation.js:412`, `page-posts.js:189`/`:486`, `page-settings.js:151`. On the other
sixteen the page's main action is a `button()` inside a card inside a section, competing with
every other button on the page. The mock's "page head with one primary action" is a slot the
shell already has and the pages do not use.

**(2) `layout.js:72–84` opens the FIRST section and shuts the rest — so a primary action below
section 1 costs a scroll and a click.** Nine pages pass `open: true` to override this for at
least one section; **`golive` passes it nowhere at all**, so eleven of its twelve sections are
shut headers on arrival. This is the single mechanism behind most of the test-2 failures.

**(3) Four pages answer a click by re-rendering the whole page and putting the answer somewhere
you cannot see.** `minutes` (`page-minutes.js:147–151` → `:171`, a section with no `open: true`)
and `rolemenus` (`page-rolemenus.js:1199–1203` → `:1292–1303`, the editor appended *after* both
log sections) both press a button, rebuild `#dash`, and leave the reader looking at exactly what
they were looking at before. `events` (`:550`) and `modmail` (`:428`) do the same thing
correctly, with `open: true` — which is what makes the other two a defect and not a house style.
**Nothing anywhere scrolls to the thing it just opened**, though `layout.js:204` (`openSection`)
and `page-requests.js:1190` (`flashLinked`) both exist and do exactly that.

**(4) A class that carries the "this is clickable" promise has no CSS rule.** `.link` —
`page-posts.js:129` and `:494` — **matches nothing in any of the three stylesheets.** `.rowlink`
— `page-members.js:96` — likewise **matches nothing**. `.cell-member` (`page-members.js:98`) is
an `<a>` with layout rules only, no colour, no underline, no hover. Against this,
`button.grid-row` (moderation) and `.guidecard` (guides) each have hover and focus rules
(`site.css:908–919`, `2059–2072`). The rows that look clickable are clickable; the rows that
were *meant* to look clickable were never given the rule.

**(5) Two pages split one subject by platform or source into separate sections** — test 5, the
go-live defect. `golive` is the case (Twitch links / YouTube channels / Pings, plus three
settings blocks and three log blocks: `page-golive.js:818–839`). `events` is the second and
nobody has called it out: **raid trains are a whole second feature bolted onto the Events page**
with their own settings section and their own logs section (`page-events.js:564–566`). By
contrast the Logs page proves the right answer — `logs.js:163–166` makes every one of 21
features a **chip**, not a section.

**(6) Every page ends with the same two sections, and three pages end with four or six.** One
settings section and one logs section per page is the house pattern and is fine. `golive` has
three of each; `events` has two of each; `rolemenus` has one settings and **two** logs sections
(`:1289–1290`). On top of that, **eight pages carry a second settings surface higher up** —
`page-automod.js:96`/`:122`, `page-chat.js:1026` (memory settings inside the Memory section),
`page-rolemenus.js:1126` (application settings inside the Applications section),
`page-moderation.js:446`, `page-minutes.js:181`, `page-polls.js:745`, `page-requests.js:1285`,
`page-guides.js:358` — so "where do I change this?" has two answers on the same page, plus a
third on `/settings.html`.

**(7) Tone words that no stylesheet defines.** `badge(text, 'quiet')` is used on
`page-posts.js:104` (and again at `:135`) and `page-golive.js:212`; `site.css` defines `.badge[data-tone]` for `ok`,
`warn`, `danger` and `info` only (`:1337–1339`, `:1891`). A `quiet` badge is indistinguishable
from a badge with no tone at all — so on the Posts list, **`posted` and `not posted` render in
the same colour**. Same family: `page-posts.js:124` puts `data-tone="warn"` on a `.row`, but
`status-shell.css:287–290` keys the row's state off **`data-state`** — so the amber row and the
amber dot for "changes not yet posted" **never appear**.

**(8) The best constructs in the tree are each used on exactly one page.** The drawer
(`ui.js:669`, used only by `page-moderation.js:391`), the legal-moves table
(`page-requests.js:128–150`, `:480–504`), the live outcome sentence
(`page-polls.js:477–516`, `page-requests.js:924–933`), the hub-and-detail hash route with a
styled card (`page-guides.js:175`, `:1192`). Nothing is wrong with any of them; they have simply
never been copied. **The go-live rebuild is the first page to adopt one deliberately** (the
row-opens-a-drawer pattern, blessed by Fable's ruling 4).

---

## 3. The three pages to do after go-live

1. **Posts** — it is the only 🔴 with a named, observed victim, the fixes are four small ones in
   one 562-line file, and three of them are CSS-attribute bugs rather than design work. It is the
   cheapest way to prove the audit was worth running.
2. **Rolemenus** — the biggest structural knot left after go-live: one menu lives in three
   sections, the Edit button's answer lands below two log tables, and an entire second feature
   (Applications, with its own mode switch, cards, forms table, per-form panels, per-form rosters
   and its own settings panel) is crammed inside one section at `page-rolemenus.js:1078–1139`.
3. **Chat** — nine sections, and *Intents* renders **every intent's full editor expanded inline**
   (`page-chat.js:437` + `:359–433`: name box, kind, answering switch, every trigger chip, every
   line row, delete). `searchOver()` is used on Knowledge and Personality (`:756`, `:868`) and
   **not** on Intents, which is the longest list on the page. One cheap change (collapse to a row
   per intent, open on click) shortens the page more than anything else in the tree.

---

## 4. Page by page

Sections are listed in `load()` order. "Distance" counts what stands between arriving on the page
and doing its one primary action, given `layout.js:72–84` (first section open, rest shut).

---

### 1. index — the Overview · 🟢 · 1 fail

**(a) Sections.** None. `page-overview.js:236–243` puts three blocks straight into `#dash`:
`todayStrip` (one sentence: what failed, what is waiting on a person, how many features are in
shadow or off), then a `twocol` holding **Features** (one row per feature, each with a live mode
switch and a chevron to its page) and **Last actions** (the last ten important log lines).
`mountSections` finds no `section.sect`, so the "On this page" rail is hidden (`layout.js:227`).

**(b) Primary action.** *Change a feature's mode.* Distance: **0 sections, 1 click** — the
switch is on the row (`:60–67`, `modeSwitch`). This is the best primary-action distance in the
tree.

**(c) The six tests.** T1 pass · T2 pass · T3 pass · T4 pass · T5 pass ·
**T6 FAIL** — the open counts are stated twice on one screen. `todayStrip` names them as links
(`:18–22` `NEEDS`, "3 events waiting on a Lead"), and the Features rows name the same numbers
again (`:10–16` `OPEN_NOTE`, "3 events waiting"). The comment at `:129–133` says this strip is
"the ONE home for *what wants a person*" and that it replaced a counter card saying "the same
numbers a second time" — `OPEN_NOTE` is that second time, still there.

**(d) Proposal.** Keep the strip as the only place a *queue* is counted; let the Features row say
what the feature IS rather than what is waiting in it (mode, and whether it is set up). One fact,
one home, without changing a single word the bot posts.

**(e) Severity: 🟢** — fine as it is, with one duplicate number.

---

### 2. members · 🟢 · 1 fail

**(a) Sections.** None. `page-members.js:227`: a five-tile stat strip, then one card holding the
toolbar (search + All/Staff/Bots/New chips), the grid, the footer and the pager.

**(b) Primary action.** *Find a member.* Distance: **0 sections, 0 clicks** — the search box is
the first control in the card head (`:136–149`), and it keeps the caret across the re-render
(`:207–214`).

**(c) The six tests.** T1 pass (joined, roles with their remaining days, case count, all on the
row) · **T2 FAIL** on the secondary move: the row is `div.grid-row.rowlink` (`:96`) and
**`.rowlink` has no rule in any stylesheet**; the name is an `<a class="cell-member">` whose only
rules are `display:flex` and gaps (`site.css:942–950`) — no colour, no underline, no hover; the
hover rules that exist are `a.grid-row` and `button.grid-row` (`site.css:908–909`), which a
`div` never matches. So "open this member's cases" is a click on something with no styled
affordance. The comment at `:89–93` explains correctly why the row is a `div`; the styling that
a `div` row then needs was never added · T3 pass · T4 pass · T5 pass · T6 pass.

**(d) Proposal.** Give `.rowlink` the hover and focus rules `a.grid-row` already has, and let the
name read as a link. No structure change.

**(e) Severity: 🟢.**

---

### 3. audit — the Logs page · 🟢 · 0 fails

**(a) Sections.** Two (`page-audit.js:303–307`): **Logs** — every filter the route takes (search,
important/all, CSV export, a chip per feature plus an Errors chip, from/to dates, a kind box, two
member pickers, Clear filters) over a paged table that reloads only itself (`:169–201`); and
**Settings audit** — every settings change with its key, value, who and via (`:89–96`).

**(b) Primary action.** *Narrow the log to the thing you are looking for.* Distance: **0
sections, 0 clicks** — the tools are the first thing inside the first (open) section.

**(c) The six tests.** T1 pass · T2 pass · T3 pass · T4 pass with a note — both sections are
reference surfaces, but reference IS this page's work, so the test does not bite ·
**T5 pass, exemplary** — feature and kind are **chips** over one table (`:163–166`,
`logs.js:19–46`), which is precisely what `golive` does with sections · T6 pass.

**(d) Proposal.** None. Copy it.

**(e) Severity: 🟢** — the cleanest page in the tree.

---

### 4. health · 🟢 · 1 fail

**(a) Sections.** Five (`page-health.js:310–317`): **Health** (gateway, latency, version, plus
the five open counts) · **Self-test** (run it, the latest run, its failures, older runs in a
foldout, and a 15-second self-poll while one is running, `:225–290`) · **Costs** (this month's
total, a row per cost, what the models charged, and secret NAMES in a foldout, `:151–182`) ·
**Loops** · **Last 50 actions**.

**(b) Primary action.** *See whether the bot is well.* Distance: **0 sections, 0 clicks** —
section 1 is open and holds the answer. The secondary action, *Run the self-test*, is section 2:
1 scroll + 1 expand.

**(c) The six tests.** T1 pass · T2 pass · T3 pass · T4 pass (no settings section, no logs
section — the only page besides Logs and the two section-less ones with zero machinery) · T5
pass · **T6 FAIL** — the five open counts are on this page (`:69–74`, `COUNT_LABELS`) *and* on
the Overview's `todayStrip` *and* in the Overview's Features rows. Three homes for one set of
numbers.

**(d) Proposal.** Let Health own "is it well" (gateway, loops, self-test, money) and drop the
open counts from it; they belong to the Overview, which already leads with them.

**(e) Severity: 🟢.**

---

### 5. moderation · 🟢 · 1 fail

**(a) Sections.** Two full-width blocks then four sections (`page-moderation.js:451–453`): a stat
strip · the **cases card** (search, five kind chips, the grid, the pager) · **Take an action**
(member picker, kind, reason, timeout length) · **Only one member** (a picker that filters the
whole page; opens itself when a filter is on, `:438`) · **Settings** (one key, `mod_log_level`) ·
**Logs**. The Automod and Honeypot mode switches sit in the page head aside (`:412`).

**(b) Primary action.** *Open a case and act on it.* Distance: **0 sections, 1 click** — the
cases card is above the first section, and `caseRow` (`:144–166`) is a `button.grid-row` with a
trailing chevron that opens the case in the right-hand drawer (`:391–396`, `ui.js:669`). The page
under it does not move. ⚠️ **This is the house pattern the go-live rebuild is adopting, and it
already exists, working, here.**

**(c) The six tests.** T1 pass (kind, a shadow pill, a voided badge, the reason struck through,
all on the row) · T2 pass · T3 pass (a case is in exactly one place; the drawer is not a section)
· **T4 FAIL, narrowly** — two of the four sections are machinery, and the *Settings* section
exists to hold **one** key (`:442–449`); a section for one setting is a section too many when
that key also has a home on `/settings.html` · T5 pass · T6 pass.

**(d) Proposal.** Fold the one-key Settings section into the page-head aside beside the two mode
switches that are already there, and the page is three sections with a drawer. Nothing else to
do.

**(e) Severity: 🟢** — the model page.

---

### 6. guides · 🟢 · 1 fail

**(a) Sections.** Two shapes from one module. **Hub** (`page-guides.js:319–367`): a "Right now"
strip, then **Guides** (filter chips + a grid of guide cards, `open: true`), and for editors
**Screenshots to re-shoot** · **New guide** · **Settings** · **Logs**. **One guide**
(`:1192–1212`): no sections at all — a head with breadcrumb, title, goal, pills and a Copy-command
button; then the steps, the "If it did not work" table, the two foot buttons, and a right-hand
rail (who it is for, where it happens, the values it reads, related guides, when it was edited).

**(b) Primary action.** *Open the guide for what you are trying to do.* Distance: **0 sections,
1 click** — `hubCard` (`:175`) is a real `<a class="guidecard" href="#slug">` with hover and
focus rules (`site.css:2059–2072`). *Edit this guide* is a named button in the **page head
aside** (`:1186–1189`). Both halves of Pop's question — "which one" and "where do I change it" —
are answered by construction here.

**(c) The six tests.** T1 pass (audience, feature mode, not-published, stale-picture count, all
on the hub card, `:174–188`) · T2 pass · T3 pass · **T4 FAIL, narrowly** — for an editor the hub
is five sections of which two are machinery, and the *Screenshots to re-shoot* section is a
maintenance list that few sessions need open · T5 pass (in-Discord vs on-this-site is a **chip**,
`:96–100`, not a section — the right answer again) · T6 pass.

**(d) Proposal.** Put *Screenshots to re-shoot* and *New guide* behind the page-head aside that
already holds *Edit this guide*, and the editor's hub is two sections. ⚠️ **Otherwise this page
and Moderation are the two to copy from.**

**(e) Severity: 🟢.**

---

### 7. tempvoice · 🟢 · 1 fail

**(a) Sections.** Five (`page-tempvoice.js:210–216`): **Open now** (a live row per temporary
channel — owner, who it was made from, how many are in it, cap, locked/hidden, and Rename · Cap ·
Lock · Hide on the row, `:163–172`) · **Setup** (run it, and the lobby channels each with a
Forget) · **Channel naming** (the `{user}` template with a live preview) · **Settings** ·
**Logs**.

**(b) Primary action.** *Change a room that is open right now.* Distance: **0 sections, 0
clicks** — the room list is section 1 and every move is a button on the row.

**(c) The six tests.** T1 pass (`roomState`, `:102–108`, puts locked/hidden on the row) · T2 pass
· T3 pass · **T4 FAIL, narrowly** — three work sections to two machinery, and *Channel naming*
is one setting given a section of its own · T5 pass · T6 pass.

**(d) Proposal.** Fold *Channel naming* into the Settings section (its preview card can live
beside the row) and the page is Open now · Setup · Settings · Logs.

**(e) Severity: 🟢.**

---

### 8. honeypot · 🟠 · 2 fails

**(a) Sections.** Four (`page-honeypot.js:90–95`): **Hits** (when, member, trap, the mode at the
time, what happened, what they posted, and a *Ban now* button on rows the trap only logged,
`:37–62`) · **Trap channels** (one card, one button: *Run setup*) · **Settings** (the whole
`honeypot` namespace) · **Logs**.

**(b) Primary action.** *Carry out a ban the trap only wrote down.* Distance: **0 sections, 1
click** — the button is in the row's last column, drawn only for `would_` rows (`:46`), which is
the "never draw a control that would refuse" rule done right.

**(c) The six tests.** T1 pass · T2 pass · T3 pass · **T4 FAIL** — two work sections to two
machinery, and one of the two work sections (*Trap channels*) contains a single button; the page
is half reference · **T6 FAIL** — "in shadow the trap only writes down what it would have done"
is the section note (`:83`), and the same fact is re-stated by the *Mode then* column on every
row (`:41`) and again by the `would_` badge (`:23–28`). Three tellings, none of them the settings
key that controls it.

**(d) Proposal.** One section: the hits, with a strip above them saying the mode and whether the
trap channel exists, and *Run setup* as the page-head action. Settings and Logs behind it. Two
sections instead of four, and the setup button stops being a section.

**(e) Severity: 🟠** — the job is doable; the page is mostly not about the job.

---

### 9. birthdays · 🟠 · 2 fails

**(a) Sections.** Five (`page-birthdays.js:212–218`), and note the order: **Add or change one**
(a member picker + month/day/year, and the Birthday-Bot import) comes **first**; then **By
month** (twelve cards, one per month, each a table with opt-in and Remove per row, under one
search) · **Birthday wording** (the template with a live preview) · **Settings** · **Logs**.

**(b) Primary action.** *Look up or fix somebody's birthday.* Distance: **1 scroll + 1 expand** —
because the list is section 2 and only section 1 opens by default (`layout.js:82`). The page
opens on a form for adding one instead.

**(c) The six tests.** T1 pass (opted-out is a button on the row that says its own state,
`:145–157`) · **T2 FAIL** — the list is behind a shut header while the *add* form is open;
arriving at this page shows you a blank form, not the birthdays · T3 pass (a person is in exactly
one month card) · **T4 FAIL** — three work sections to two machinery, and *Birthday wording* is
one key with a preview · T5 pass · T6 pass.

**(d) Proposal.** Swap the order: the twelve months first with the search above them, *Set a
birthday* as the page-head action opening a small form, the import as a rarely-used drawer, and
the wording preview inside Settings. Two sections plus machinery.

**(e) Severity: 🟠.**

---

### 10. settings · 🟠 · 2 fails

**(a) Sections.** One `section()` call site, **about 26 rendered** (`page-settings.js:142–148`):
one collapsible group per settings namespace — *The basics* first, then the rest alphabetically
by their human names (`:22–38`) — each holding its keys as `settingRow`s under one shared save
bar (`:139`), laid out in two balanced columns (`:54–72`); then **Logs**. The filter box, the key
count and the *Show keys* switch are in the page head aside (`:151`) — one of the four pages that
uses it.

**(b) Primary action.** *Find and change one setting.* Distance: **0 sections, 1 keystroke** —
the aside filter box opens the groups that match and shuts the rest (`:74–103`), and a
`#key` link or the command palette jumps straight to a row, opens its group and flashes it
(`:109–121`). That is genuinely good.

**(c) The six tests.** T1 pass (a changed row wears CHANGED and a left border, `ui.js:1016`,
`:1051–1058`) · T2 pass · T3 pass · **T4 FAIL by construction** — every section is machinery;
this is the machinery page, so the test is arguably not applicable, but it is recorded as a fail
because **the effect on a reader is real**: 26 shut headers with one open. · T5 pass ·
**T6 FAIL** — four namespaces get a note pointing at the page that really owns them (`:15–20`:
automod's JSON box, the Costs card, the Pings section); the other twenty-one namespaces whose
keys *also* have a second editor on a feature page say nothing. The rule is applied four times
out of the ~13 places it applies.

**(d) Proposal.** Group the namespaces under the four rail headings the sidebar already uses
(`shell.js:8–46`: Overview / Runs the server / Runs the cookout / The desk) so 26 headers become
4, and give every namespace whose keys have a feature-page editor the same one-line pointer the
four already have.

**(e) Severity: 🟠** — reachable by filter, unreadable by scrolling.

---

### 11. requests · 🟠 · 2 fails

**(a) Sections.** Staff see **nine** (`page-requests.js:1290–1301`): a toolbar card (search,
Anybody/Nobody yet/On me chips, the open+in-progress count, CSV export) above everything; then
**Open** · **In progress** · **Ready to check** · **On hold** — all four `open: true`
(`:823`, `:839`, `:870`, `:854`) — then **Done** and **Declined** (each a section wrapping a
closed foldout), **File a request**, **Settings**, **Logs**. A member sees **two**: *File a
request* and *Your requests* (`:1244–1255`).

**(b) Primary action.** Staff: *move a request along.* Distance: **0 sections, 1 click** — the
first section is open and every legal move is a button on the card. Member: *file one.* Distance:
**0 sections** — it is section 1.

**(c) The six tests.** T1 pass (status pill, was-parked-from pill, who-asked-them-to-check pill,
due-date chip, all in `headBlock`, `:250–264`) · T2 pass · T3 pass — a request is in exactly one
status section, and a deep-linked one is *pinned above* rather than duplicated (`:1148–1161`) ·
**T4 FAIL, narrowly** — nine sections is a very long page even though only two are machinery;
with four sections force-opened it is four full card lists stacked · T5 pass ·
**T6 FAIL** — the "they are sent exactly what you type" promise is written **six times** in six
different sentences (`:137`, `:147`, `:496` hint, `:535`, `:596`, `:983`). It is the most
important sentence on the page and it has no single home.

**(d) Proposal.** Keep the status split — it is a queue, and it is the one thing on this page
nobody should touch. Make *Done* and *Declined* one **Closed** section with a chip for which,
and let the four open sections collapse to counts when empty rather than each printing its own
empty state. Seven sections, same behaviour.

**(e) Severity: 🟠** — it works; it is simply very long.

✅ **STAGE 3 SHIPPED 2026-09-20, branch `requests-page` off `main` `53a0ba3` — and the proposal in (d) was NOT what was built.** The owner ruled on the page before the proposal reached him: *"the request page is too much, we cant see that many request at once, it needs to show a list with filters and then click on one to open it"* — so the status split is **gone**, not kept: nine sections are **two** (**Requests**, one `button.grid-row` list under a toolbar of six counted status chips, and a shut **Settings and logs**), and a row opens the request in `ui.js:openDrawer`. **T4 and T6 both pass now** — two sections, and the *"sent exactly what you type"* promise is written **once**, above the moves in the modal, instead of six times. ⚠️ The preview this row's proposal fed (`/preview/requests.html`, seven sections) is **deleted**. Deviations, with the six-test tally: [`ux-audit-design.md`](ux-audit-design.md) ▸ Deviations ▸ the 2026-09-20 `requests-page` entry. ⚠️ **Not merged and not deployed when this line was written**, and nothing in it has met Discord.

---

### 12. modmail · 🟠 · 3 fails

**(a) Sections.** Six, seven with a ticket open (`page-modmail.js:449–456`): **Tickets** (a
show-filter and a table; *Open* is a button in the last column) · **Ticket N** when one is open,
`open: true` (`:428`) · **Snippets** · **Blocks** · **Doors** — which holds **three** different
posted messages: the *Front door* (three buttons, with a live preview of its own title, text and
labels, `:306–354`), the *Ticket button* (`:206–251`) and the *Ticket forum* (`:253–276`) ·
**Settings** · **Logs**.

**(b) Primary action.** *Open a ticket and reply to it.* Distance: **0 sections, 1 click** — the
table is section 1, and the detail arrives as an opened section right under it. Correct, and the
exact thing `minutes` and `rolemenus` get wrong.

**(c) The six tests.** T1 pass (status badge and how it came in, on the row, `:412–413`) · T2
pass · **T3 FAIL** — an open ticket is in two places at once: its row in *Tickets* and the whole
*Ticket N* section below it · **T4 FAIL, narrowly** — *Doors* is a section of three cards about
three unrelated posted messages, which is a folder, not a subject · T5 pass ·
**T6 FAIL** — the front door's relationship with the ticket button is explained **three** times
in three near-identical paragraphs that differ only by mode (`:51–56` `DOOR_SHADOW_FOLLOWS` and
`DOOR_ONE_PER_CHANNEL`, plus `:39–41` `BUTTON_HELP`), and which one you see depends on the mode
(`:350`).

**(d) Proposal.** Split *Doors* — the front door is a subject of its own (it owns three flows and
three labels) and the ticket button and forum belong with Tickets. Open a ticket in the drawer
Moderation already uses, so it is not a second section. Four sections plus machinery.

**(e) Severity: 🟠.**

---

### 13. polls · 🟠 · 3 fails

**(a) Sections.** Nine (`page-polls.js:750–760`): **Polls** (the mode switch, on its own) ·
**Pending review** (`open` when there is anything, `:301`) · **Open polls** (`open: true`,
`:226`) · **Repeating** · **Closed** (paged cards with result bars) · **Archive** (a section
wrapping a closed foldout) · **Create a poll** (`open: true`, `:703`) · **Settings** · **Logs**.

**(b) Primary action.** *Create a poll.* Distance: **6 scrolls, 0 clicks** — it is `open: true`,
so no expand, but it is the **seventh** section; three sections above it are open too, one of
which is a paged list of finished polls with a bar chart each. The two empty states that offer
*Create a poll* (`:89`, `makeOne()`) call `goToSection('create-a-poll')`, which opens and scrolls
— so the page already knows the create form is hard to reach.

**(c) The six tests.** T1 pass (kind, surface-with-a-reason-in-its-title, votes, where, closes-in
— all on the row, `:228–239`; `surfaceChip` at `:170–180` is a small masterpiece) · **T2 FAIL**
— six sections stand between arriving and the page's one creative act · T3 pass (a poll is in
exactly one state section) · T4 pass (seven work sections to two machinery — the best ratio of
any long page) · T5 pass — *native* vs *panel* is a **chip on the row with its reason in the
title**, not a section. ⚠️ **This is the exact construct `golive` needs for Twitch vs YouTube,
and it is already written, here** · **T6 FAIL** — why a poll becomes a panel rather than a
Discord poll is explained in `surfaceChip`'s title (`:172–177`), again in `outcomeOf`'s sentence
(`:489–495`), and a third time in the Create form's field help (`:691–692`).

**(d) Proposal.** Move *Create a poll* to the page-head aside as the primary action (a form in a
drawer), and make *Closed* and *Archive* one section with a chip. Six sections, and the thing the
page is for is the first thing you can press.

**(e) Severity: 🟠.**

---

### 14. automod · 🟠 · 3 fails

**(a) Sections.** Five (`page-automod.js:129–135`): **Mode** (one settings row: `automod_mode`) ·
**Rules** (the rule book — a card per rule with its window, threshold, timeout, actions and, for
word rules, its word list, under one search, `:101–117`) · **Exemptions** (the `automod_exempt*`
keys) · **All automod settings** (the whole namespace minus what is already homed, `:133`) ·
**Logs**.

**(b) Primary action.** *Change a rule.* Distance: **1 scroll + 1 expand** — *Mode* is section 1
and takes the open slot; the rule book, which is the entire point of the page, is behind a shut
header.

**(c) The six tests.** T1 pass (each rule card shows its own enabled switch and numbers) ·
**T2 FAIL** — the page opens on a single settings row · T3 pass · **T4 FAIL, the worst in the
tree** — **four of the five sections are settings or logs**; only *Rules* is work. `:127` builds
an `omit` list precisely so keys are not shown twice, which is right, but it means three separate
settings surfaces exist on one page to make that necessary · T5 pass ·
**T6 FAIL** — the mode is explained in the *Mode* section note (`:93–94`), and `automod_mode`
also appears on the Moderation page's head aside (`page-moderation.js:35`, `:412`) and on
`/settings.html`, where `page-settings.js:17` warns that `automod_rules` has its own editor here.

**(d) Proposal.** One work section (the rule book), with the mode as a switch in the page head
beside the title, exemptions as a drawer inside the rule book, and one Settings section for
everything left. Two sections plus logs, instead of five.

**(e) Severity: 🟠.**

---

### 15. events · 🟠 · 4 fails

> 🔧 **2026-09-20 — the page LOST raid trains and is three sections, not seven.** Two builds did
> it. First branch `events-trims` (merged `6738a8d`): *Remove its room/post* went and the forum
> card folded into **Settings**. Then branch `raidtrain-page` (⚠️ built, NOT merged, NOT deployed;
> design [`raidtrain-page-design.md`](raidtrain-page-design.md)): **Raid trains**, **Train #N**,
> **Raid train settings** and **Raid train logs** are all gone from this page and are
> `/raidtrain.html` instead. What is left, measured in `chrome-headless-shell` against the mock:
> **Queue · Settings · Logs**. So **T5 is answered at the cause** — one page, one subject — and
> **T4** is two blocks of machinery across three sections rather than four across seven.
> ⚠️ **T3 and T6 are NOT answered here:** an opened event is still its queue row plus an
> *Event #N* section, and the duplicated *times are read in …* / `YYYY-MM-DD HH:MM` sentences that
> survive are still written twice. Those wait on the Events page's own stage 3. §B's table above
> is the pre-trim reading and was NOT re-run.

**(a) Sections.** Seven, nine with both details open (`page-events.js:559–567`): **Queue** (a
show-filter and the event table, with Open/Approve/Deny/Cancel/Move-to-the-forum/Remove-its-room
as buttons in the last column, `:188–278`) · **Event #N** when open, `open: true` (`:550`) ·
**Events forum** (`open: true`, `:556`) · **events settings** · **events logs** · **Raid trains**
(a scope picker, the trains table, a *Start a raid train* form, `:397–484`) · **Train #N** when
open · **Raid train settings** · **Raid train logs**.

**(b) Primary action.** *Decide an event that is waiting.* Distance: **0 sections, 1 click** —
Approve and Deny are buttons in the queue row, drawn only for pending rows (`:193`).

**(c) The six tests.** T1 pass (status badge, decided-by, why-not, all on the row) · T2 pass ·
**T3 FAIL** — an opened event is in two sections at once, its queue row and *Event #N*; a train
likewise · **T4 FAIL** — **four of the seven sections are machinery**, and there are two of each
kind because two features share the page · **T5 FAIL** — *raid trains* are a separate feature
given their own sections, their own settings block and their own log block on the Events page.
This is the same defect as `golive`'s Twitch/YouTube split, one level up: not two platforms for
one subject, but two subjects sharing one page and each bringing a full set of machinery ·
**T6 FAIL** — "times are read in `<your zone>`" is written twice (`:178`, `:387`), the
`YYYY-MM-DD HH:MM` format three times (`:155`, `:182`, `:390`), and the forum's behaviour is
explained in `FORUM_NOTE` (`:42–46`), again in `MOVE_BODY` (`:39–41`) and again in the two
`sayNothing` lines of `eventForumCard` (`:503–506`).

**(d) Proposal.** ⚠️ **Raid trains want their own page** — they are a different job done by
different people at a different time, and splitting them removes four sections and one whole
settings/logs pair from Events. Then Events is: the queue (opening a row into a drawer rather
than a section), the forum card folded into Settings, one Settings, one Logs.

**(e) Severity: 🟠** — every job is doable; the page is two pages.

---

### 16. chat · 🟠 · 4 fails

**(a) Sections.** Nine (`page-chat.js:1043–1053`): **Try it** (`open: true`, `:507` — type a
message, see which intent it lands on and the exact line it would answer with; a dry run) ·
**Intents** (`open: true`, `:437` — **every intent's full editor, expanded**: name box, kind
badge, Answering/Quiet switch, every trigger phrase as a removable chip, every answer line as a
row, a token-help line and Delete, `:359–433`) · **New intent** · **Knowledge** (notes, under a
`searchOver`, `:756`) · **Personality** (the voice pool, under a `searchOver`, `:868`) ·
**Memory** (per-person profiles, plus **eight settings keys of its own**, `:1026`) ·
**Spend & tiers** · **Settings** (sixteen keys) · **Logs**.

**(b) Primary action.** *Change what the bot answers to something.* Distance: **1 scroll, 0
clicks** — *Intents* is section 2 and `open: true`. But the section it lands in is the longest
list on the page with **no search over it**, every member fully expanded, paged at 50.

**(c) The six tests.** T1 pass (each intent card shows its kind and its Answering/Quiet state) ·
**T2 FAIL** — reaching *one* intent means scrolling past every other intent's full editor;
`searchOver()` is imported and used twice on this page (`:756`, `:868`) and not on the list that
needs it · T3 pass · **T4 FAIL** — two settings surfaces (the Memory section's eight keys at
`:1026` and the Settings section's sixteen at `:939`) plus logs; and *Spend & tiers* is a
read-only report, so three of nine sections are reference · T5 pass ·
**T6 FAIL** — the three intent kinds are explained in `INTENTS_NOTE` (`:68–70`) and again in
`KIND_SAID` on every single card's Kind field (`:113–117`, `:425`); the monthly cap is explained
in `SPEND_NOTE` (`:82–84`), in the `CAP_LIVES_IN_SETTINGS` line (`:95`) and again by its own
settings row.

**(d) Proposal.** Collapse *Intents* to one row per intent — name, kind, Answering/Quiet, trigger
count — with a search above it and the editor opening in a drawer (the Moderation pattern). Merge
*New intent* into that section's primary action. Fold Memory's eight keys into Settings, leaving
Memory the profile list. Six sections, and the longest one becomes a table.

**(e) Severity: 🟠.**

---

### 17. minutes · 🔴 · 3 fails

**(a) Sections.** Four (`page-minutes.js:186–191`): **Meetings** (a table: number, where,
started, by, how it stands, whether it was posted, and an **Open/Close** button in the last
column, `:136–153`) · **The meeting you opened** (the notes box, *Save the notes* / *Write the
notes again* / *Post again* / *Delete*, and the full transcript, `:171–177`) · **Settings**
(the `minutes_*` keys, filed under the `events` namespace, `:179–184`) · **Logs**.

**(b) Primary action.** *Read and fix a meeting's notes.* Distance: **1 scroll + 1 expand, and
no sign that either is needed.**

**(c) The six tests.** T1 pass (how it stands, and whether it was posted, are both on the row) ·
🔴 **T2 FAIL — pressing the page's one button appears to do nothing.** `:147–151`: *Open* sets
`openMeeting` and calls `refresh()`, which re-runs `load()` and rebuilds `#dash`. The meeting
then renders inside `section('The meeting you opened')` at `:171` — **which is not given
`open: true`**. `layout.js:72–84` therefore leaves it **shut**, because it is not the first
section and nothing is remembered for it yet. Nothing scrolls. The only visible change anywhere
on the page is that the button's own label flips to *Close*. Compare `page-events.js:550` and
`page-modmail.js:428`, which are the same construct **with** `open: true` — so this is a missed
argument, not a house style. It corrects itself forever after the first manual expand (the
`toggle` listener at `layout.js:251` writes `true` into `localStorage`), which makes it **a
first-time-only failure — exactly the class of failure Pop hit** · T3 **FAIL** — an open meeting
is in two sections at once · T4 pass, narrowly (two work, two machinery) · T5 pass · T6 pass.

**(d) Proposal.** One section. The meetings table, and a row opens the notes and transcript in the
drawer — or, at minimum and for nothing, `{ open: true }` on `:171` plus a `scrollIntoView`.
Settings and Logs behind it.

**(e) Severity: 🔴** — a staff member who presses *Open* and sees nothing happen cannot do this
page's job without being told to scroll down and click a closed header.

---

### 18. rolemenus · 🔴 · 4 fails

**(a) Sections.** Nine, ten while editing (`page-rolemenus.js:1280–1303`): an optional
member-filter banner · **Role selection** (the on/off switch) · **Requests** (pending role
requests as cards, decided ones in a foldout) · **Timed roles** (the grants table, plus a *Hand
roles out* form and a *Grant a timed role* form, `:614–631`) · **Menus** (the menus table, with
Edit and Delete per row, plus *New menu* and *Seed defaults*) · **Post a menu** (one card **per
menu**, each with a channel picker and Post/Un-post, `:1249–1266`) · **Settings** ·
**Applications** (an entire second feature: its own mode switch, pending application cards, a
decided foldout, *New form*, a forms table, then **per form** an *Apply button* card and a
roster foldout, then its own settings panel, then the form editor, `:1078–1139`) ·
**rolemenu logs** · **Application logs** · and, when editing, **Editing `<name>`** appended last.

**(b) Primary action.** *Change a menu.* Distance: **4 scrolls + 1 expand to reach the Menus
table; then the answer arrives off-screen.**

**(c) The six tests.** 🔴 **T2 FAIL, twice over.** *Menus* is the fifth section and shut on
arrival. Worse: *Edit* (`:1199–1203`) sets `state.editing` and calls `refresh()`, and the editor
section is **pushed onto the end of the node list at `:1292–1303`** — after *Post a menu*, after
*Settings*, after the whole *Applications* section, and after **both** log sections. It carries
`open: true`, so it is open; it is simply nine sections below where the click happened, and
nothing scrolls to it · **T3 FAIL** — one menu appears in **three** sections at once: its row in
*Menus*, its own *Post `<name>`* card in *Post a menu*, and *Editing `<name>`* at the foot. A
form in the Applications section appears in three places too (the forms table, its *Apply button*
card, its roster foldout) · **T4 FAIL** — one settings section, **two** log sections, plus a
second settings panel inside *Applications* (`:1126`); and the page carries two mode switches
built two different ways (`:153–181` hand-rolled Turn on/Turn off for rolemenus, `:1055–1076`
segments for applications) where `ui.js:1366` `modeSwitch` exists for exactly this ·
**T6 FAIL** — "nobody loses a role" is promised five times in five sentences (`:41`, `:44–45`,
`:323`, `:919`, `:1207`), and "posting again makes a new message; the old one stops handing out
roles" three times (`:307–309`, `:1249`, and the save message at `:256–257`).

T1 pass (mode, asks-first, runs-out, options, posted-in, all on the menus row, `:1169–1196`) ·
T5 pass.

**(d) Proposal.** ⚠️ **Applications is a page, not a section** — lift it out whole and the
remaining page loses a settings panel, a log section and roughly half its height. Then: one
**Menus** section where a row opens a drawer holding the editor *and* that menu's post/un-post
control (killing *Post a menu* entirely, and with it the one-menu-three-places problem), plus
**Requests** and **Timed roles**, plus one Settings and one Logs. Four sections instead of nine.

**(e) Severity: 🔴** — pressing *Edit* and seeing the page apparently not change is the same
failure as Minutes, on the page with the most to edit.

---

### 19. posts · 🔴 · 4 fails — **Pop's two minutes**

> 🔧 **STAGE 3 SHIPPED 2026-09-20 (branch `posts-page`, off `main` `552af36`).** The approved preview
> IS the page now, live against the real API, and `site/public/preview/posts.html` +
> `assets/page-preview-posts.js` are **deleted**. All four fails below are answered: **T1** — the row
> carries a `dot-sm[data-tone]` (a rule that exists) and pills toned `ok` / `info` / `warn` / `danger`
> instead of the undefined `quiet`, with the *Channel* sentence as its own column; **T2** — the whole
> row is a `button.grid-row` ending in a `chevronRight`, opening `ui.js:openDrawer`, and *New post* has
> moved out of the column flow into the section's own toolbar; **T4** — two sections, one of them all
> the machinery, both `data-span="full"` so `mountColumns` cannot reorder them (step 5's defect, fixed
> at the cause); **T6** — the shadow behaviour is written once (the API's note, rendered in the section
> head) and the logs and settings blocks keep their own notes instead of the page repeating them. The
> body below is the measurement that produced the fix and is kept as written. ⚠️ **Nothing here has met
> Discord, and nobody has watched a staff member use the new page** — sweeps `PP-a` … `PP-f`.

**(a) Sections.** The list view renders three sections and one orphan
(`page-posts.js:202–210`): **The posts** (`open: true`, `:192` — a `.row` per post) · *A new
post* — **a bare `card()`, not a section** (`:151–175`), so it is absent from the "On this page"
rail · **Settings** (three keys) · **Logs**. The mode switch is in the page head aside (`:189`).
The detail view renders **no sections** (`:489–535`): a head with a breadcrumb, the title and the
status pills; then one card holding title, channel, style, pin, the message box, a live Discord
preview, the "what pressing this will do" line, and the buttons.

**(b) Primary action.** *Edit an existing post.* Distance: **0 sections, 1 click — on a control
with no styled affordance and no word saying what it does.**

**(c) Pop's two minutes, step by step against `page-posts.js`.**

Two things have to be said first, because the received account in
[`ux-audit-design.md` §A](ux-audit-design.md) is wrong on one of them and it changes the fix.

> §A says: *"'changes not yet posted' is text inside that view, not state on the row."*
> **Measured: it IS on the row.** `listCard` calls `statusPills(row)` at `:132`, inside
> `row-head`, beside the title. `GET /api/posts` sends `status` for every row
> (`black_bloc/api/tools/posts.py:68` via `post_row`, used by `posts_index` at `:180`), and
> `black_bloc/posts.py:329–338` builds it as `posted` / `posted (shadow)` / `pinned` /
> `changes not yet posted` / `not posted`. The row also carries a whole sentence —
> `postedLine()` at `:115–121` — reading *"Posted in #welcome. It is pinned."* or *"Not posted
> anywhere yet."*

**So the information was on Pop's screen. Three separate rendering defects made it invisible,
and a fourth hid the way in.**

**Step 1 — she looked at the coloured dot, because that is what the eye goes to.** Every row
opens with `el('span', { class: 'dot' })` (`:125`). `status-shell.css:278–290` colours that dot
from the **row's `data-state`** attribute — `ok` green, `warn` amber, `danger` red — and gives it
a matching halo. `listCard` sets **`data-tone`**, not `data-state` (`:124`). There is **no
`.row[data-tone]` rule in any of the three stylesheets** (`site.css`, `status-shell.css`,
`estate-theme.css` — `.dot-sm[data-tone]` exists, `.row[data-tone]` does not). **Every post's dot
is therefore the same muted grey, whatever the post's state**, and the amber tint the code
intends for "changes not yet posted" never appears on the row either.

**Step 2 — she looked at the pills, and they were all the same colour.** `statusPills` at
`:103–105` passes tone `'warn'` for `changes not yet posted` and **`'quiet'` for everything
else**. `site.css` defines `.badge[data-tone=…]` for `ok`, `warn`, `danger` (`:1337–1339`) and
`info` (`:1891`) — **there is no `quiet` rule**, so a `quiet` badge falls through to the base
`.badge`: `color: var(--et-muted)`, `font-size: var(--et-text-micro)`, uppercase
(`status-shell.css:297–306`). **`POSTED` and `NOT POSTED` render identically** — same muted grey,
same tiny caps — and differ only by the word. That is the question she was asking, answered in
the page's quietest typography, in a colour that says "this is metadata".

**Step 3 — she read the sentence, and it was two sizes smaller than the preview text.**
`postedLine` lands in `.row-detail` (`:137`), then two `.row-note` lines follow it (`:138–146`):
the first 160 characters of the post's body, then "Last saved 3 days ago by …". `.row-detail` is
`--et-text-small` and `.row-note` is `--et-text-micro` (`status-shell.css:312–313`). The
did-it-post sentence is one small line in a stack of four, with the body preview — the longest
and most eye-catching text in the row — directly under it.

**Step 4 — she looked for something that said "edit", and there is nothing on the page that
does.** The only way into a post is its **title**, which is
`el('button', { class: 'row-name link', … })` at `:128–133`. Measured:
`status-shell.css:295` gives `.row-name` a single rule, `font-weight: 700`. **`.link` has no rule
in any stylesheet** — I grepped all three for `.link` and it appears nowhere. There is **no
global `button` reset** anywhere in the CSS (`* { box-sizing }` at `status-shell.css:80` is the
only universal rule), so this control renders with the **browser's own default button chrome**,
which matches nothing else on the dashboard. Every other button on the page is `.btn` from
`ui.js:325`. There is no chevron, no "Edit", no hover rule of the site's own, and no second
control on the row. ⚠️ **What this actually looks like was not rendered and cannot be claimed
here** — what is certain is that the site styles it **not at all**, deliberately or otherwise,
and that it is the only such control on the page.

**Step 5 — the thing that DID look like a button made a new post.** `#dash`'s children go through
`mountColumns()` (`layout.js:179–201`), which balances a run of non-wide blocks into two columns.
None of `say`, `list.node`, `newPostCard` or `options.node` matches `WIDE` (`layout.js:138`) or
contains a `.table-scroll` / `.grid-table` / `table`, so all four join one run; only the logs
section (which holds a table) breaks it. The greedy balance at `:154–170` therefore puts the tall
posts list in one column and **the *A new post* card, with its bold *Make it* button, at the top
of the other — level with the list's heading.** ⚠️ **Unrendered**: this is what the layout code
does with these four blocks, not a screenshot. The point stands regardless of which column lands
where: the most button-looking control beside the list of posts creates a *new* one.

**Step 6 — had she clicked the title, she would have been fine.** The detail view is good: a
breadcrumb back (`:494`, `.crumb` **is** styled, `site.css:2219–2229`), the status pills again in
the head (`:500`), the message beside a live Discord preview, `willPost()` (`:276–293`) printing
a whole sentence saying exactly what *Post it* will do including shadow mode, and the button
labelled from the bot's own `move_label` — *Post it* or *Update the post*
(`black_bloc/posts.py:341–342`). **Nothing was wrong past the front door. The front door had no
handle.**

**(d) The six tests.** **T1 FAIL** — the state is *present* on the row and *invisible* on it: a
dead `data-tone` on `.row` (`:124`), an undefined `quiet` badge tone (`:104`), a permanently grey
dot (`:125`) · **T2 FAIL** — the primary action is an unstyled `button.row-name.link` (`:129`)
with no word saying what it does · T3 pass (a post is in exactly one place) · **T4 FAIL** — two
of the three sections are machinery, and *A new post* is not a section at all, so the rail lists
two reference surfaces and one list · T5 pass · **T6 FAIL** — the "one message, edited in place,
never a second copy" promise is written three times: `LIST_NOTE` (`:34–35`), the Channel field's
help (`:505`) and `WILL_UPDATE` (`:48`); and the shadow behaviour is written by the page
(`:52–55`) **and** by the API as a note (`api/tools/posts.py:28–32`), both of which render, one
above the other, at `:203` and `:204`.

**(e) Proposal.** Give the row the state it already has: `data-state` instead of `data-tone`
(one word), a defined tone for `posted` and `not posted` so they differ, and a trailing chevron.
Make the row itself the control the way `page-moderation.js:144` does — a `button.grid-row`,
which already has hover, focus and cursor rules — so the whole row is the way in and looks it.
Move *A new post* out of the column flow and into the page-head aside beside the mode switch,
where `:189` already writes. That is one section of work with two drawers behind it, and Pop's
two minutes become two seconds. ⚠️ **No new words** — every sentence above already exists;
wording is [`posted-strings-audit.md`](posted-strings-audit.md)'s job.

**(f) Severity: 🔴** — observed, by name, on 2026-09-20.

---

### 20. golive · 🔴 · 5 fails — 🔧 *rebuild in flight*

Audited as it stands on `main` at `5afd58c`, as the baseline. The rebuild to
[`golive-page-design.md`](golive-page-design.md) is on branch `golive-page` and replaces
everything below with five sections.

**(a) Sections.** **Twelve** (`page-golive.js:818–839`), in this order: **Twitch links** (the
link table + a *Link a member* card) · **Opt-outs** (the opt-out table + an *Opt somebody out*
card) · **Recent streams** (50 sessions; a live one is a badge in the *Ended* column, `:798`) ·
**Announcement wording** (the live template with a preview, the ended template and its author
line, a rewrite-or-suffix toggle, and a *Wording* card that asks the bot to render both messages,
`:297–332`) · **Go-live settings** · **Go-live logs** · **YouTube channels** (a mode switch, a
nine-row probe-status card, the link table, a second *Link a member* card) · **YouTube settings**
· **YouTube logs** · **Pings** (a mode switch, the streamer list, the ping-roles table, *The
shared roles*, *Create for a streamer*, *Discord onboarding*) · **Ping role settings** ·
**Ping role logs**.

⚠️ **Not one of the twelve passes `open: true`.** On arrival, *Twitch links* is open and
**eleven shut headers** follow it.

**(b) Primary action.** *Add a streamer so they get announced.* Distance: **depends which
platform, which is the defect.** Twitch: 0 sections (the *Link a member* card is inside the open
first section). YouTube: **6 scrolls + 1 expand** to a second card with the same title. Neither is
named anywhere as the page's action, and the page-head aside is empty.

**(c) The six tests.** T1 pass, narrowly — a session's live state is a badge on its row (`:798`),
a ping role's state is on its row (`:546`), a streamer's listed/hidden is on its row (`:412`);
but **no row anywhere says whether that person is set up on the other platform** ·
**T2 FAIL** — the page's one action has two doors, one of them six shut sections down ·
**T3 FAIL** — one streamer can appear in **four** sections at once (Twitch links, Opt-outs,
Recent streams, and both tables inside Pings), and there are **two** cards titled *Link a member*
(`:115` and `:660`) · **T4 FAIL** — **three** `namespaceSettings` and **three** `logsSection`,
six machinery sections against six of work · **T5 FAIL, the founding case** — Twitch and YouTube
are the same question (*who gets announced when they go live?*) answered by two disjoint stacks
of three sections each · **T6 FAIL** — what the mode does is explained in `MODE_HELP` (`:352`),
`CHANNELS_MODE_HELP` (`:600–602`), `SWITCH`-style notes and `LIVE_NOTE` (`:606–607`); and
`golive_mode`'s authority over YouTube posts is stated at `:601–602` **and** `:607`, two sections
apart.

**(d) Proposal.** Already written and approved: five sections, one row per person carrying both
platforms, one wording with a platform toggle, machinery in drawers
([`golive-page-design.md` §B](golive-page-design.md)). The only thing this audit adds is that
**the row-opens-a-drawer pattern the rebuild is inventing already exists and works on
`page-moderation.js:391`**, and that **the platform-as-a-chip-with-its-reason-in-the-title
pattern already exists on `page-polls.js:170–180`** — neither needs designing from scratch.

**(e) Severity: 🔴** — 🔧 rebuild in flight.

---

## 5. What pages already do RIGHT — copy these, do not reinvent them

| Construct | Where it lives | Why it is the answer |
|---|---|---|
| **A row that is a button, with a chevron, opening a drawer** | `page-moderation.js:144–166` + `:391–396`, `ui.js:669–689`, CSS `site.css:908–919` | The page under it does not move, the row has hover and focus rules, and the chevron says "there is more". **This is what go-live is about to re-derive.** ⚠️ **2026-09-20, branch `centre-modal`:** the "drawer" `ui.js:openDrawer` opens is now a floating, centred modal, not a right-docked panel — owner: *"lets swap the left hand modals for floating center modals"* (the Discord mock inside it was unreadable at 30rem). Same construct, same function names, same callers; only `site.css` changed. Not merged. |
| **A hub card that is a real `<a>`** | `page-guides.js:175`, CSS `site.css:2059–2072` | Hover, focus, and the browser's own link behaviour for free — the opposite of Posts' unstyled `button.row-name.link`. |
| **The page-head aside as the page's own action slot** | `page-guides.js:1186` (*Edit this guide*), `page-posts.js:189`/`:486`, `page-settings.js:151` (filter + key count + Show keys), `page-moderation.js:412` (two mode switches) | The slot is in all 20 HTML files. Four pages use it; sixteen have it empty. |
| **Buttons built from the row's own legal-moves list** | `page-requests.js:128–150` + `:480–504`, mirroring `black_bloc/requests.py:TRANSITIONS` | A control that would be refused is **never drawn**. The single best construct in the tree, and the cleanest possible answer to the "a person must never see a bare refusal" rule. |
| **A live sentence under the button saying what pressing it will do** | `page-polls.js:477–516` (`outcomeOf`), `page-requests.js:924–933`, `page-posts.js:276–293` (`willPost`) | Rebuilt on every keystroke, including which surface Discord will get and what shadow mode will do with it. |
| **Platform / kind as a CHIP with its reason in the `title`** | `page-polls.js:170–180` (`surfaceChip`: *panel*, titled "because it is anonymous") | Test 5 solved, already, in eleven lines. |
| **Filters as chips over ONE table, never a section per filter** | `page-audit.js:135–167` + `logs.js:19–46` — 21 features and an error kind, all chips | The whole of `golive`'s problem, already solved on the Logs page. |
| **One shared logs block, one shared settings block** | `logs.js:206–322`, `ui.js:1279–1295` — used by 16 and 8 pages | Consistency for free; `omit` (`ui.js:1278`) is how a key that has its own editor higher up keeps one home. |
| **Every empty state carries one thing to do** | `ui.js:134–139` `sayNothing(text, action)`; `page-polls.js:89`, `page-requests.js:768–784`, `logs.js:219–241` | Never a blank box, and the action always undoes whatever narrowed it. |
| **Reading the render from the bot instead of re-implementing it** | `page-golive.js:252–295` (`/api/golive/preview`), `page-birthdays.js:36–58`, `ui.js:1308` (`fillTemplate` mirrors Python's `format_map`, and returns null rather than lying) | The preview cannot drift from what Discord gets. |
| **A deep link that opens everything shut above it, then waits a frame** | `page-requests.js:1190–1202` (`flashLinked`), `page-settings.js:109–121` (`jumpToKey`) | The comment at `:1182–1189` records both traps measured the hard way. **The two pages that fail test 2 by re-rendering (`minutes`, `rolemenus`) need exactly this and do not call it.** |
| **The caret put back after a re-render** | `page-members.js:207–214`, `page-requests.js:1041–1048` | A search box that survives its own results. |

---

## 6. What I could not classify

- **`audit` and `settings` are machinery pages, so test 4 does not mean the same thing on them.**
  I recorded `settings` as a T4 fail because 26 shut headers is a real cost to a reader, and
  `audit` as a pass because two log surfaces IS the Logs page. Both calls are judgement, not
  measurement, and a reviewer could flip either.
- **`index` and `members` render no `section.sect` at all**, so tests 4 and 6 have almost nothing
  to bite on and the "On this page" rail is hidden (`layout.js:227–230`). Their scores are not
  comparable with a nine-section page's, and the ranking should not be read as "the Overview is
  nearly as good as the Logs page" — it is a different kind of page.
- **`posts`, `guides` and `requests` each have two page shapes from one module** (list/detail by
  hash, staff/member by role). I audited the shape a staff member meets first and said so; the
  detail views have **zero sections**, so the six tests were applied to the list view only.
- ⚠️ **Whether `button.row-name.link` (`page-posts.js:129`) reads as "clickable" or as "broken"
  I cannot say** — no browser rendered it. What is measured is that `.link` has no rule anywhere
  and there is no global button reset, so the control takes user-agent styling and matches nothing
  else on the page. A ten-second look in a browser settles it; this audit could not.
- **Two-column balancing (`layout.js:154–201`) changes reading order on a wide window** and its
  result depends on measured block heights, which only exist once rendered. Every claim I made
  about it (the Posts case, step 5) is about what the algorithm does with those blocks, not about
  a screenshot.
- **Whether `requests`' five force-open sections are too long is a taste call**, so I scored it
  T4-fail on section count and left the severity at 🟠. A queue that shows all four live states at
  once may be exactly right for the people using it; nobody has been watched using it.
- **Discord panels: none was read** (§E puts them out of scope) and I noticed no panel defect in
  passing while reading the page modules, because the page modules do not touch them. The one
  adjacent observation: `logs.js:103–126` (`viaCell`) already treats *done in Discord* vs *done on
  this dashboard* as a **pill on a row**, which is the same lesson test 5 draws — so if the panel
  program ever splits a feature by `via`, the answer is already in the tree.

---

## Deviations

*2026-09-20 — the audit agent.* §B's *Settings + log blocks* column was found to be inflated by
one per imported name and is corrected in §1; §B's *Sections* column reproduces exactly and is
confirmed. §A's second sentence about the Posts row ("state is not on the row") was found to be
wrong on the measurement and is corrected in §4.19 with the API and CSS evidence; the finding it
supports survives the correction, with different causes and therefore a different fix. No other
deviation; no file but this one was written.
