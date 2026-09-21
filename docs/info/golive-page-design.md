# The Go-live page, rebuilt — one list of people, whichever platform they stream on

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v142** — merge `e88573d`, release `6a6f8e4`,
> deployed **2026-09-20 17:02** Phoenix, **and RENDERED in a browser by the conductor** (the strip, the live cards, the row drawer with its
> four groups; one gap found and fixed on `main` `4b1731d`: the Streamers list arrived shut). The seventeen `## Deviations` are
> the truth where they depart from the body; sweeps **621–626** are the owner's; verified: boot clean (17:0x), /health ready, /assets/golive-join.js served; the page RENDERED in the browser at 17:0x — the seven-cell strip (Live right now 4, Twitch announcements shadow, YouTube announcements on, Ping roles off, Set up, Watching every 5 min, the Set-up warning cell), four Live-now cards, Recent streams, no console errors on a tracked reload; clicking a Streamers row opened the side drawer with the four groups (Twitch / YouTube / Ping role / Announcements) and the real moves (Unlink · Link their channel · Give them a ping role · Hide · Opt them out). ONE defect seen: the Streamers list arrived SHUT between two open sections (the layout opens only the first) — fixed on main at 4b1731d (open: true), rides v143. Not pressed: any move in the drawer, the search, the chips (rows 621–626 are the owner's). Was: BUILT on branch
> `golive-page` (off `main` `948ff05`), the body plus rulings 2 and 3. Gate green: `ruff` clean,
> `pytest -n 8` 6757 passed / 3 skipped forward **and** under `BB_REVERSE=1`, 35 asset modules parse, `check.mjs`
> 20 pages / 186 routes unchanged, `discordmd` + `labels` + `clipmd` + the new `golive-join` fixtures green.
> Before that: 📐 **REVIEWED by Fable 2026-09-20 16:1x — all five
> calls stand (two with additions, see the rulings at the foot) — and DISPATCHED to Opus as branch `golive-page`.** Was: ⏸️ ready for review, not dispatched. (The owner approved the mock 16:0x and a build was dispatched 15:56; he stopped it a minute
> later — *"dont start it in 4 minutes, we're gonna swap to fable, just prepare it to be reviewed."* — before it
> had written anything. No branch, no worktree, nothing to clean up.) **Read `## For the reviewer` at the foot
> first: five judgement calls this document makes that a reviewer should rule on before any of it is built.** **Last verified: 2026-09-20 15:4x** against `main`
> `3d8ee64` (v141 live): `site/public/assets/page-golive.js` read in full (845 lines, twelve top-level
> sections, the `load()` order at `:716–845`), `ui.js:namespaceSettings` `:1279` / `modeSwitch` `:1366`,
> `logs.js:logsSection` `:202`, and the 36 keys the three namespaces hold, measured by import
> (`golive` 17, `pings` 13, `youtube` 6). ⚠️ Secret NAMES only.

## The ask

Owner, 2026-09-20 15:3x: *"on the golive page the youtube and twitch experiences are basically different
experiences, this is crap. can we redesign this page to have less menus and a more unified experience?
do a mock or fake page first so we don't effect what the end users see"* → the mock, twice
(<https://claude.ai/artifact/VGiR2jgHui9E4D9MbCKyw6>, v2 inside the real shell) → **16:0x: *"okay i like
that mock, make it happen"***.

**The mock is the specification.** Where this document and the mock disagree, the mock wins on layout and
wording; this document wins on behaviour, data and the guards below.

> ➕ **2026-09-20, branch `spotlight`:** the Streamers list gained rows with **no member behind
> them** — a Twitch channel watched by name (GamesDoneQuick). Its *Member* cell reads *channel
> only*, its *Announced* cell *spotlight · kept* or *spotlight · until 30 Sep*, there is a
> **Spotlight** filter chip beside the others, and the row drawer gains a **Spotlight** group. A
> channel that is ALSO a linked member's login is ONE row — the member's — carrying the spotlight
> facts. `joinStreamers` takes a sixth payload and `placeSettings` gained nine keys (one in the
> strip, eight in *How streams are spotted*), so §A's *"nothing under `black_bloc/` changes"* is
> true of THIS build and not of that one. Design:
> [`spotlight-design.md`](spotlight-design.md).

## A. The single most important fact about this build

⚠️ **It is a front-end rearrangement. Nothing under `black_bloc/` changes.** Every field the new page
shows is already fetched by today's `load()`: `/api/golive/links`, `/api/golive/optouts`,
`/api/golive/sessions?limit=50`, `/api/pings/streamers`, `/api/pings/list`, `/api/pings/onboarding`,
`/api/youtube/links`, `/api/youtube/status`, `settings(true)`. **No new route, no schema change, no
settings key, no log kind, no Python.** If the build finds it needs one, it STOPS and reports rather than
adding it — that is the signal the design was wrong.

Blast radius: `golive` is staff-only (`shell.js:MEMBER_TABS` is `['requests','guides']`) and
`golive_mode` is **shadow**, so a mistake here is seen by staff, not by members.

> 🔴 **AMENDED 2026-09-20 (branch `end-wording`, design [`end-wording-design.md`](end-wording-design.md)):** section 3's
> *Once the stream has ended* card now holds **ONE** end-wording box. `golive_end_suffix` and `golive_end_mode` are
> retired keys, so the suffix row and the **When a stream ends** mode switch are gone from the card, along with the
> Wording card's *golive_end_mode is off, so…* paragraph and `END_UNKNOWN`. The announcement is **always** edited once a
> stream ends. §B's *Everything else* catch-all row still reads `golive_end_*`, and still means the surviving three.

## B. What the page becomes — five sections, in this order

| # | Section | Replaces |
|---|---|---|
| — | the header strip (live count, both mode switches, set-up count, watch cadence) | the mode rows inside two sections, the `Live now` line inside the YouTube status card |
| 1 | **Live now** — a card per open stream | the live rows buried in *Recent streams* |
| 2 | **Streamers** — ONE row per member | *Twitch links*, *YouTube channels*, *Opt-outs*, the streamer list inside *Pings*, and BOTH *Link a member* cards |
| 3 | **The announcement** — one wording, a platform toggle on the preview | *Announcement wording* and its two preview cards |
| 4 | **Recent streams** | unchanged |
| 5 | **Everything else** — five closed drawers | *Go-live settings*, *YouTube settings*, *Ping role settings*, and all three *Logs* sections |

### B1. The streamers join — a pure module, because it must be testable

`site/public/assets/golive-join.js`, exporting `joinStreamers({ links, youtubeLinks, optouts, listing,
streamers, sessions, status })` → one array of rows sorted by display name, each row
`{ user_id, name, twitch, twitch_at, youtube, youtube_id, youtube_at, role, role_wearers, opted_out,
live }` where `live` is `'twitch' | 'youtube' | null`. It is **pure** — no DOM, no fetch — and it is the
one place the platforms meet. Its test is `site/mock/golive-join.test.mjs`, in the shape of
`clipmd.test.mjs`, added to `scripts/deploy.ps1` and `.github/workflows/ci.yml` beside it.

⚠️ **The join's own traps, each pinned by a fixture:** a member with Twitch and no YouTube (the common
case — measured 21 to 1 on the live guild); a member with YouTube and no Twitch; a member who is opted
out AND linked; a member with a ping role and no link at all (they must still appear, or a role goes
invisible); an open session whose `user_id` matches nobody linked (it still shows in *Live now*, named by
the session's own `user_name`); two open sessions for one member on two platforms (ONE row, `live` set
from the session whose `source` is not `presence`, and *Live now* shows the state the mock shows —
announced for one, held back for the other).

### B2. The row and its drawer

The table is Member · Twitch · YouTube · Ping role · Announced. Clicking a row (or Enter / Space on it)
opens an inline panel under it with four groups, each carrying the moves that live in today's four
sections: Twitch (open / unlink / link), YouTube (open / unlink / link), Ping role (make / rename /
remove), Announcements (opt out / announce them again). **Every move calls the route it calls today, with
the confirmation wording it uses today** — copy `ask({...})` bodies across verbatim rather than rewriting
them; rewording is the other audit's job. ⚠️ A row must LOOK clickable at rest (the caret in the mock);
that is finding 1 of [`ux-audit-design.md`](ux-audit-design.md) and this page is where the pattern is set.

### B3. Add a streamer — one form, two destinations

The page head's primary action opens one form: a member picker, then one text field that takes **either**
a Twitch name **or** a YouTube channel address / `@handle`. Routed by shape: `youtube.com/…`, `UC…` or a
leading `@` → `POST /api/youtube/links`; anything else → `POST /api/golive/links`. ⚠️ A value that could
be either is **refused in words** naming both, never guessed. The two existing cards' help text is the
source for the wording.

### B4. The settings drawers — and the guard that stops a key vanishing

Today three `namespaceSettings` calls dump three namespaces. The new page groups **36 keys** by question:

| Drawer | Holds |
|---|---|
| Who gets announced | `golive_require_role_id`, `golive_ignore_role_id`, `golive_cooldown_minutes`, `golive_live_role_id`, `golive_max_session_hours` |
| Where it goes | `golive_channel_id`, `golive_ping_role_id`, `golive_embed` |
| Ping roles | every `pings_*` except `pings_mode` and `pings_log_level`, **plus the two cards that are not settings** — *The shared roles* (`setupCard`) and *Discord onboarding* (`onboardingCard`), moved here whole |
| How streams are spotted | `youtube_live_poll_minutes`, `youtube_live_end_misses`, `youtube_unlink_dms_them`, and the read-only lines from `liveStatus()` |
| Everything else | ⚠️ **the catch-all** — every key of the three namespaces not named above, minus the ones the page renders elsewhere (`golive_mode`, `youtube_live_mode`, `pings_mode` in the strip; `golive_template`, `golive_end_*` in section 3) |

⚠️ **A test asserts every key in the three namespaces lands in exactly one drawer or one named surface.**
Without it, the next settings key anybody adds appears nowhere and nobody notices — the failure this
page's own history is full of. The catch-all is what makes that test satisfiable; it is not an excuse to
leave keys unsorted.

### B5. One log

One **Log** drawer holding the three `logsSection` outputs with chips that switch between them (All ·
Twitch · YouTube · Ping roles). If `logsSection` cannot take more than one feature — read it, do not
assume — the drawer holds three of its nodes and the chips show and hide them. Say which in Deviations.
⚠️ Do not fork `logs.js`; it is shared by nineteen other pages.

## C. What must not change

Every route and its payload · every refusal sentence and confirmation body · every log kind · the guard's
behaviour · `modeSwitch`'s saving path (the strip uses it unchanged) · `logs.js`, `ui.js` and every other
shared module, except additive exports if one is genuinely needed (say so). The page's `<title>`, its
`data-tab` and its place in the rail stay as they are.

## D. Tests and the gate

`site/mock/golive-join.test.mjs` (the six traps in B1, dependency-free, added to `deploy.ps1` + CI) ·
a test that every key in the three namespaces is placed exactly once (B4) · `node site/mock/check.mjs`
unchanged at 20 pages / 186 routes · the ES-module parse of every `site/public/assets/*.js` ·
`ruff check .` and `pytest -n 8` both orders, unchanged and still run, with the bot-shaped env cleared
(`gotchas.md`). ⚠️ KI-26 (ten sightings, one on a `> file` run): a stalled pytest is killed by its own
process tree only, never `taskkill /IM python.exe`.

## E. Docs

This doc's `## For the reviewer — five calls this design makes, each of which could be made differently

The owner has approved the mock's **look**. What follows are the decisions underneath it that he did not
rule on, in the order they would hurt if they are wrong. Ruling on them is the point of this review;
nothing needs rewriting unless a ruling changes it.

**1. The settings drawers replace a mechanical rule with a curated map.** Today three
`namespaceSettings` calls dump three namespaces — nobody maintains that, and a new key appears on its own.
§B4 sorts 36 keys by question into five drawers, which reads far better and must be maintained by hand for
ever. The catch-all drawer and the every-key-lands-once test stop a key vanishing; they do not stop a key
landing in a silly drawer. **The alternative:** keep namespace-shaped groups and spend the effort on their
labels and help text instead. ⚠️ This is the call that the other 19 pages will copy.

**2. Two cards that are NOT settings get buried in a closed drawer.** *The shared roles* and *Discord
onboarding* carry real actions, and §B4 moves them into the Ping-roles drawer. That is in tension with the
audit's own second test — the primary action must be reachable without learning the page. **The
alternative:** they stay a visible section, and the page has six, not five.

**3. *Live now* is a section AND a filter chip on the Streamers table.** One fact, two places, which is
what §C test 3 forbids elsewhere in this same document. It is defensible — the section is a glanceable
summary, the chip is navigation — but it is the design's own exception to its own rule and should be
named as one or removed.

**4. A row that opens an inline drawer becomes the house pattern.** It is the direct answer to Pop's
finding, and this page is where it gets set for every other page that copies it. Worth blessing or
rejecting deliberately rather than by precedent. ⚠️ It has a known cost this document does not solve:
KI-20 says an ephemeral panel's buttons die on a restart, and an expanded row holds state that a refresh
throws away.

**5. The join lives in the browser, not in Python.** `joinStreamers` merges five payloads client-side so
the build touches no route and no Python — which is why the blast radius is small and the gate is fast.
But every other join in this estate lives next to its cog, and the site is meant to be a view. **The
alternative:** one `GET /api/golive/streamers` that returns joined rows, which is a bigger build, needs a
contract row and a Python test, and moves this out of front-end-only territory.

**Rulings (Fable, 2026-09-20 16:1x) — all five stand, two with an addition:**

1. **Stands.** Namespace-shaped groups are the twelve-section defect in miniature — *Go-live settings /
   YouTube settings / Ping-role settings* is exactly the platform split the owner called crap. The
   maintenance cost is real and the catch-all + the every-key-lands-once test is the answer to it. And
   "one fact, one home" is satisfied by the **Settings page**, which still shows every key by namespace:
   that is the canonical home; the drawers here are the feature's own door, the same relationship every
   feature page already has with it.
2. **Stands, with an addition.** The audit's test 2 is about the PRIMARY action, which on this page is *Add
   a streamer*; the shared-roles and onboarding cards are setup done rarely. They stay in the drawer, but
   **the drawer's summary line must name them** (*Ping roles · 8 settings · the shared roles · Discord
   onboarding*) so they are findable without opening it, and **when setup is incomplete** (no events role,
   onboarding drifted — both states the cards already know) **the header strip shows a warning that opens
   that drawer.** State visible where listed, test 1, without a sixth section.
3. **Stands, named as the deliberate exception.** The section answers *what is happening now*; the chip
   answers *show me only those rows*. Different questions, so not one fact in two places — but the build
   writes one line in `code-notes.md` saying so, so nobody "fixes" it later.
4. **Stands.** The expanded row holds no unsaved input — every move in it is a button that acts at once
   with its own confirm — so a refresh closing it costs nothing. KI-20 is about Discord's ephemeral panels
   and does not transfer; the cross-reference is withdrawn. This IS the house pattern from here.
5. **Stands, for this build.** Pure + tested in the browser is what makes this safe to ship today, and
   today this page is the join's only consumer. The route becomes the right answer the day a second
   consumer appears (the Members page, or the Discord `/golive` panel wanting the same rows) — that is
   the trigger, recorded here, not a judgement call to re-argue.

**Dispatched 2026-09-20 16:1x as branch `golive-page`, exactly as the body describes plus rulings 2 and 3.**

## Deviations` (dated) and `## What was NOT verified` · `code-notes.md` for the join's
non-obvious choices · `docs/info/README.md` row · `docs/access/sweeps.md` rows `GP-a…` (a: the table shows
one row per person with both platforms; b: a row opens and its moves work; c: Add a streamer takes a
Twitch name and a YouTube address and refuses an ambiguous one in words; d: the two mode switches in the
strip still save; e: every setting that was on the old page is reachable; f: the log chips switch
between the three features). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.

## Deviations

**2026-09-20, branch `golive-toggle`:** *The announcement* is now ONE card, **The wording**, with a `Starting` / `Ending` segment in its head (`ui.js:segment`, in `card`'s `actions`): each side holds its own wording box, its own top-line box and its own Discord mock, and the *Preview as Twitch / YouTube* chips stay above both. The two stacked cards (*While they are live* / *Once the stream has ended*) are GONE, `golive_end_keep_mention` stays on the Ending side, and the Starting side gained the new `golive_live_author` box beside `golive_template`. Both editors and both mocks are built at load and the toggle only flips `hidden`, so a draft survives a trip to the other side. Owner, 20:1x: *"instead of a stack have a toggle for starting and ending since theyre duplicates and we can save space"*; see [`end-wording-design.md`](end-wording-design.md) ▸ §C2 ▸ C2 deviations. This page's own deletion of `GET /api/golive/preview` landed here too.

**2026-09-20, branch `discord-mock`:** *The announcement*'s two wording editors now carry a LIVE **Discord mock** each (`ui.js:discordMock` → `POST /api/preview/message`), and the **Wording** card, `drawCard`, `botLine`, `withRoleNames` and `wordingPreview` are GONE — there is one rendering per message now, it is the bot's own, and it sits under the box that writes it. The *Preview as Twitch / YouTube* chips set the BOT's sample platform rather than a client-side fill, so the address and the card colour follow. This page no longer reads `GET /api/golive/preview`; see [`discord-mock-design.md`](discord-mock-design.md) ▸ Deviations 1 and 8.

*(the build agent writes here what it had to do differently, dated)*

**2026-09-20, branch `golive-page`, off `main` `948ff05`.** Seventeen, in the order they would
surprise a reader of the body.

1. ⚠️ **A row opens the RIGHT-HAND DRAWER, not an inline panel under it.** §B2 and ruling 4 both
   say inline. The UX audit landed mid-build with a measured finding that changed it: the
   construct already exists and works — `page-moderation.js:144` builds each case row as a
   `<button class="grid-row">` ending in a `chevronRight`, and `:391`'s `showCase` opens
   `ui.js:openDrawer` (a native modal `<dialog>`, so Escape, the focus trap and the backdrop are
   the platform's). The conductor directed this build to use it rather than write a second one,
   which is the audit's whole point. The BEHAVIOUR the design asked for is unchanged — a row
   opens a panel holding the four groups of moves — and *looks clickable at rest* is met by the
   chevron plus `button.grid-row:hover`. Enter, Space and focus come free from a real `<button>`
   instead of a hand-rolled `keydown`. The cost: the panel is modal, so the page under it does
   not move and two people cannot be open side by side.
2. **The Streamers list is `.grid-table` / `.grid-row`, not `ui.js:table()`.** `table()` renders
   one `<tr>` per row and `filterRows` counts every `tbody` child, so a row that opens something
   is not a shape it has. `.grid-table` already carries a second column template
   (`.grid-table.members`); `.grid-table.streamers` is the same additive extension. `table()` is
   untouched and still draws *Recent streams*.
3. **The header strip has SIX cells, not the mock's five.** §B4 places `pings_mode` "in the
   strip" while the mock shows only the two announcement switches, so a **Ping roles** cell was
   added. Without it that key would have had to go in a drawer, which §B4's own exclusion list
   forbids.
4. **The set-up warning is a SEVENTH cell, a `<button class="stat">`** (ruling 2). It is drawn
   only when `golive_ping_role_id` is unset, or when onboarding is managed and community and has
   never been written. Pressing it opens *Everything else*, opens the Ping-roles drawer and
   scrolls to it.
5. **The Ping-roles drawer's summary is ruling 2's own line**, with the measured number:
   *Ping roles · 11 settings · the shared roles · Discord onboarding*. Eleven, not the ruling's
   illustrative eight — `pings` holds **13** keys, minus `pings_mode` (the strip) and
   `pings_log_level` (the catch-all).
6. **`ui.js:foldout()` was NOT used for the drawers.** Its summary is an uppercase label
   (`text-transform: var(--et-label-transform)`), which turns that sentence into a shout, and its
   count slot is mono. A page-local `drawer()` plus three CSS classes give the mock's bold title
   and muted line, and are not a shared-module change.
7. **The Log drawer holds THREE `logsSection` nodes and the chips show and hide them** — read,
   not assumed, as §B5 required. `logs.js:logsSection(feature, …)` takes ONE feature and fetches
   `/api/actions?feature=…`; there is no multi-feature call and no combined route, so **All**
   shows all three stacked. ⚠️ The chips are labelled from `logs.js:LOG_FEATURES` — **Go-live**,
   not the mock's *Twitch* — because the `golive` feature's log covers both platforms and calling
   it Twitch would be a lie.
8. **A `logsSection` node is demoted before it goes in the drawer** (`unsection`). It returns a
   `section.sect`, and `layout.js:mountSections` finds sections by DESCENDANT query, so three
   nested ones would have added three entries to the *On this page* rail and broken "five
   sections". `logs.js` is not forked.
9. **There is no RENAME of a ping role.** §B2 lists "make / rename / remove"; the routes are
   `POST /api/pings/streamers` and `DELETE /api/pings/streamers/{id}` and nothing else, and this
   build adds none. The group offers **Give them a ping role** (with the existing *use this role
   instead* select), **Remove**, and **Hide**/**Restore** — the streamer-list move section 2
   absorbs from *Pings*.
10. **Two confirmation bodies are verbatim and now point at nothing.** The YouTube unlink body
    still ends *"…a Lead can link it for them below"* and there is no card below it any more (the
    form is in the same panel). Kept verbatim per §B2 — rewording is the other audit's job — and
    flagged here for it. Two OTHER bodies were changed by one word, *below* → *in Everything
    else*, because the settings they name genuinely moved.
11. **`badge(mark, 'quiet')` became `badge(mark, null)`** in the Wording card. Measured by the
    audit: `.badge[data-tone="quiet"]` matches no rule in any stylesheet, so the tone was a no-op.
    Same appearance, no longer claiming something the CSS does not do.
12. **Recent streams is unchanged except one cell:** *How* reads `source + also_source` when the
    co-stream fields are present. The mock's five-column Recent table was NOT adopted — the
    design's own table says "unchanged", and today's seven columns carry strictly more (Title,
    Mode then).
13. **`joinStreamers`'s `live` can be `'both'`,** which §B1's row shape
    (`'twitch' | 'youtube' | null`) does not list. Required by the co-stream brief. Rows also
    carry three fields §B1 does not name — `listed`, `last_live_at`, `live_count` — because the
    Hide/Restore move and the panel's footer line need them.
14. **A second pure export, `liveStreams(sessions)`,** builds the *Live now* cards, and a third,
    `routeTyped(value)`, is §B3's shape routing. Traps 5 and 6 and the ambiguous-value refusal are
    all behaviours worth a fixture, and a fixture needs a pure function.
15. **An open session whose user matches nobody gets a Streamers ROW as well as a Live-now card.**
    §B1 only requires the card, but a person the *Live now* chip filters to has to exist in the
    list it filters.
16. **`site.css` grew 79 lines** — the strip's note line and pressable stat, the live cards, the
    platform pill, the streamers column template, the drawer. Tokens only, no raw colours.
    `ui.js`, `logs.js`, `api.js`, `app.js` and `layout.js` are untouched, and `contract.json`'s
    diff is zero.
17. **The page head's subtitle is written from JS.** `golive.html` is untouched (its `<title>`,
    `data-tab` and rail place stay as §C requires), so the new one-line subtitle is set into
    `#subtitle` on load rather than in the markup.

**KI-26 fired, sighting ELEVEN, and it was a `> file` run** (the second such): the `BB_REVERSE=1`
`pytest -n 8` stalled at **87 %** with the log untouched for over seven minutes. Killed by its own
process TREE — identified by the `PYTHONPATH=C:/lcw/bb-golive-page` in the `env -i` command line,
because a second agent's suite was running beside it — and green in **83 s** on the retry. This
build did not touch `KNOWN_ISSUES.md`; the count is reported to the conductor.

## What was NOT verified

> **Superseded 2026-09-20 17:0x by the conductor, after v142 shipped and was opened in a real browser:** the strip (seven cells), the four Live-now cards, Recent streams and the Streamers row drawer with its four groups all RENDERED, with no console errors on a tracked reload; one gap was found and fixed on `main` `4b1731d` (the Streamers list arrived shut because `layout.js` opens only the first section — six other pages already pass `open: true` to their main list; this page was the odd one out). **Still not verified:** no move in a row's drawer was pressed, *Add a streamer*'s ambiguous-value refusal was never seen, the search and the five chips were never used, the co-stream fields are fixture-only until `costream` lands — rows 621–626. The paragraph below was true when written.

⚠️ **NO BROWSER HAS RENDERED THIS PAGE. Not once, at any width, in any theme.** Every claim above
about how it looks is a reading of `site.css`, not a screenshot — the strip, the live cards, the
six-column streamers grid, the drawer, the chips and the whole small-screen story are unproven.
Sweeps `GP-a` … `GP-f` are the only proof that will ever exist.

- **Not merged, not deployed, no key flipped**, and nothing here met Discord or the live bot.
- **No move in the row panel was ever pressed.** Every route call is a copy of the call today's
  page makes, checked by reading; not one was exercised against the mock or anything else.
- **`node site/mock/check.mjs` was run** (20 pages / 186 routes, unchanged) — but it checks routes
  and page loads, not rendering, and **no page was opened in a browser against the mock**.
- **The co-stream fields are fixture-only.** `also_source` and `also_url` do not exist in any
  payload yet; the two fixtures pin what the join will do when the `costream` build lands them,
  and nothing has proved the field names will be those.
- **The every-key-lands-once test's 36-key list is a DATED FIXTURE**, measured 2026-09-20 off
  `settings_store.KEY_TYPES`. It does not read the registry live, so a key added later is caught
  by the catch-all at runtime (which IS tested) rather than by that list.
- **Nobody has tried the page with 21 real rows**, and whether a modal drawer beats an inline
  panel for that list is an untested judgement (Deviation 1).
- The **search box and the five filter chips** were never typed into or pressed; the filter
  functions are untested code.
- `golive.html`, `contract.json` and every shared asset module are unchanged — **verified by
  `git diff`**, which is the one claim here that was measured rather than read.

---

**2026-09-20 (branch `boot-sweep`)** — the *How streams are spotted* drawer gained a tenth control,
`golive_boot_sweep` (bool, default true): whether a restart walks every member's Discord presence
and announces anyone already streaming with no session. Nothing else on the page moved — the key
goes through `placeSettings` and `settingsPanel` like the nine beside it, and the every-key-lands-once
fixture in `golive-join.test.mjs` went **48 → 49**. Design: [`golive-boot-sweep-design.md`](golive-boot-sweep-design.md).
