# The Go-live page, rebuilt — one list of people, whichever platform they stream on

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **REVIEWED by Fable 2026-09-20 16:1x — all five
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

## A. The single most important fact about this build

⚠️ **It is a front-end rearrangement. Nothing under `black_bloc/` changes.** Every field the new page
shows is already fetched by today's `load()`: `/api/golive/links`, `/api/golive/optouts`,
`/api/golive/sessions?limit=50`, `/api/pings/streamers`, `/api/pings/list`, `/api/pings/onboarding`,
`/api/youtube/links`, `/api/youtube/status`, `settings(true)`. **No new route, no schema change, no
settings key, no log kind, no Python.** If the build finds it needs one, it STOPS and reports rather than
adding it — that is the signal the design was wrong.

Blast radius: `golive` is staff-only (`shell.js:MEMBER_TABS` is `['requests','guides']`) and
`golive_mode` is **shadow**, so a mistake here is seen by staff, not by members.

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

*(the build agent writes here what it had to do differently, dated)*
