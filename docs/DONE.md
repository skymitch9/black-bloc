# Black Bloc — DONE (dated archive, newest first, append only)

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-08-31** — the HEADER only. The entries below are an
> append-only archive and were deliberately NOT re-verified or edited; a wrong
> one gets a superseding entry, never a correction in place.
>
> Entries are moved here WHOLE from [`TODO.md`](TODO.md), never summarised, and
> never edited afterwards. A wrong entry gets a superseding one above it.

## 2026-09-05 — Honeypot panel: `/honeypot` is one command, seven subcommands become controls (v79, `361eaa2`)

**Landing:** Opus build in its own worktree (314k), merged clean `fa845a6`, landing edits `aebcc02` (sweep rows
`H1`–`H12` numbered 188–199, guide count 187 → 199, KI-21 widened to the honeypot's generic-route bypass),
deployed `361eaa2` as v79 at 07:39 together with `info/settings-panel-design.md` (`361eaa2` is the design's
merge commit). 4593 tests, ruff clean, `check.mjs` 17 pages / 142 routes, `commands synced` 36 → 36 measured (a
Group was already one slot). Boot verified from the Fly log: database ready 14:39:15Z, synced 36, `/raidtrain`
hidden, logged in 14:39:19Z, no traceback. **NOT verified:** the panel opened in Discord, a trap created, a role
picked, a modal submitted, whether a real client submits an EMPTY `min_values=0` RoleSelect (**Exempt nobody** is
the fallback that makes that safe), the dashboard Settings row for `honeypot_panel_minutes`. Forks F-H1/F-H2/F-H3
were built on the design's recommendation, all (a), each reversible in one small local change (design doc
§ Build deviations) — the owner's confirmation is still owed, one at a time. What was built, in full, is the
design doc's `## Build deviations` foot and `docs/access/sweeps.md` rows 188–199. Review: `/honeypot` in
`#mute-me-bot-test-spam`; https://blackbloc.heygabi.ai/honeypot.html is unchanged.

**The item, moved whole from `TODO.md`:**

- 🆕 **Honeypot → ONE slash command (owner, 2026-09-04, clock read 20:50 after the ask: "All of honeypot should be 1 slash
  commands Let's combine").** Today `honeypot.py:417` is a Group (`logs`, `setup`, `status`, `mode`,
  `forget`) with a nested `exempt` group (`add`, `remove`) — 7 subcommands. Becomes `/honeypot` →
  panel: status card, Setup…, mode select, Exempt roles (role select), Forget, Logs — the wave-3
  shape (`info/panels-program.md`). Folds into the second audit; one build, own design doc.
  **DECIDED (owner, 2026-09-04, audit proposal 1 of 6, "Yes"):** root card = today's `status`; buttons
  Setup… (name modal), mode select, Exempt roles (role multi-select replaces `exempt add`/`remove`),
  Forget (renders only when a trap is recorded), Logs. Est. 250–320k Opus. Design doc next, then build.

## 2026-09-05 — Hide commands when off: a feature turned off on the portal takes its `/command` with it (v78, `baede2a`)

**Landing:** Opus build in its own worktree (185k), merged `0fcbac2`, conductor's carve-out commit `e00c9bf`,
deployed v78 07:05 Phoenix. Live proof in the boot log: `35 command(s) in guild; hidden: raidtrain` — the one
mode that is `off` on the live guild lost its command on the first sync. **14 features hide, not the 15 the
build first shipped: `/memory` keeps fork I-M1 ("open it", 2026-09-03)** — memory off deletes nothing and the
site is staff-only, so the panel is a member's only door to notes held about them (KI-14); hiding it would have
left members no way in. New bool `hide_commands_when_off` (default true) reachable from the Settings page and
`/settings set-value`; `/help` names how many are hidden and both ways back; one `commands.visibility` row per
sync naming hidden + shown again. `NEVER_HIDDEN` = settings, help, about, ping. Sweeps 183–187; rows 53, 108,
130, 174 rewritten. NOT verified at landing: a portal flip re-syncing within 60 s, the dashboard row, the `/help`
note as rendered. Design: `docs/info/code-notes.md` § *Hide commands when off*.

**The item, moved whole from `TODO.md`:**

- 🆕 **A feature turned OFF on the web portal hides its /command (owner, 2026-09-04 20:45: "Can we expand
  the app so if we turn a feature off on the web portal the /command is hidden? Like I want to turn off
  YouTube videos for now. Can we have that make the /youtube command not appear until it turns back on").**
  Measured 20:45: the mechanism EXISTS — `black_bloc/command_visibility.py` removes a top-level command
  from the dev guild's tree whenever a key in `HIDDEN_WHEN_OFF` reads `off`, debounced 5 s / re-synced at
  most once a minute, and it is wired to `store.on_change`, so the portal's Settings page already
  triggers it (`api/settings_api.py` writes through `store.set`). The table only names `rolemenu_mode` and
  `request_mode` (the role-menus build deletes the first). **The build:** the table grows to every mode key
  whose choices include `off` → its top-level command — golive, youtube, pings, tempvoice → `voice`,
  honeypot, events → `event`, poll, birthday, automod, rolemenu, request, chat, chat_memory → `memory`,
  raidtrain, applications → `apply` (modmail has no off; `settings`, `help`, `about` never hide);
  `shadow` is NOT off (youtube is `shadow` today — the owner sets it `off` on the portal and the command
  goes). Configurable both ways (33): one new bool key `hide_commands_when_off` (default **true**)
  that the Settings page and `/settings set-value` reach; `hidden_names` reads it. ⚠️ **Trade-off to
  say out loud:** with a command hidden, staff turn the feature back on from the portal or
  `/settings set-value <feature>_mode on`, not from the panel — the panels program's P9 "mode-off panel
  still opens and says so" survives only for the ≤60 s sync lag. `/help` already follows `hidden_names`.
  Tests: `tests/test_command_visibility.py` (the role-menus build re-pointed it at `request_mode`),
  `tests/test_settings_store.py`, `labels.js` row, `feature-list.md`, OWNER_GUIDE, a sweeps row, code-notes.
  **Order: AFTER the role-menus merge (v77)** — that branch edits `command_visibility.py` and its test.
  Est. 120–180k Opus, one build, then v78.

## 2026-09-04 — Role menus panel: `/rolemenu` is one window (wave 3 FOURTH and LAST landing, v77, `43312b9`)

Release **v77** (`43312b9`, 20:51; `deploys.log` line 76). Merge `--no-ff` of
`worktree-agent-ace2086f9f7cfa541` — **four commits off `4523118`** (`8cdbdd3`, `12b296b`,
`18b132c`, `05a9a87`). Built by one Opus agent for **529k against a 420–500k estimate** (dispatched
16:03 in parallel with raidtrain, landed second at 16:53), Fable-reviewed **approve**. Design:
`info/role-menus-panel-design.md` (header flipped to SHIPPED; its `## Deviations` foot lists 14).

**What it is.** The `rolemenu` and `role` staff groups' eighteen leaf subcommands are retired for
ONE staff `/rolemenu` that opens an ephemeral panel: the root lists the menus (a select picks one)
and a Lead sees **Setup…**, **Grants…** and **Logs** plus the mode select; a menu card (row 0
exactly five) carries **Add a role**, **Hand roles out**, **Post it**, **Edit** (F-R3 (a) — an edit
re-posts a posted menu) and the waiting-on-staff sub-panel (F-R1 (a) — the pending-requests queue
lives in the panel); the grant card carries **Extend** and **End it now**, which makes the phantom
`/role revoke` (named in four docs, never built) real; F-R2 (a) — a grant with no end date is `0 =
never`. **The owner's §I-amend Grants audit** is built: `active_grants`, `grant_order`, `time_left`
and `grant_lines` in the pure `black_bloc/rolemenus.py`, soonest-ending first, no-end-date LAST,
`AUDIT_MAX` 25. Grant/extend were reconciled from two divergent implementations (cog inline vs
`roles.py`) into one — and `tests/api/tools/test_roles.py` is UNCHANGED, which is the proof the
reconciliation did not move the site. Seven bare log kinds gained `kind_via`; `web.rolemenu.*` was
renamed `web.role_menu.*` with `HEADS["rolemenu"]` kept so old rows still label. `guarded()` keeps
`guard.allows_channel` on every role-changing move (TEST_MODE holds). `role_menus.option_label`
collides by name with `panels.option_label` — import aliased. New key `rolemenu_panel_minutes`
(int, 10). `HIDDEN_WHEN_OFF["rolemenu_mode"]` deleted (hiding the command hid the only way on; the
table now names `request_mode` alone — the hide-when-off item on the TODO grows it back on purpose,
behind a bool). `commands synced` **37 → 36, measured at boot**.

**The merge.** **Eight append-shaped conflicts**, every one resolved both-sides HEAD-then-branch
(`settings_store.py` block + default, `tests/test_settings_store.py`, `tests/test_bot.py` — three
group asserts kept and the pin set 37 → **36** —, `OWNER_GUIDE.md` — the branch's `/rolemenu` row
added above "Test something", count 172 → **182** —, `site/mock/server.mjs`, `labels.js`,
`code-notes.md` foot, `sweeps.md` — branch header first, newest first). The branch wrote its sweep
rows as **`M1`–`M10`, letters on purpose**, and the conductor numbered them **173–182** at the merge,
after raidtrain's 163–172. The design doc's deviation 13 was updated to say so. `docs/info/code-notes.md`'s
`# Role menus panel (wave 3)` section was re-keyed to the merge. **4465 → 4529 tests.**

**Review findings, non-blocking, deferred to the fold sweep:** `ready()` is another cog-local copy
of the opened/confirm triplet (seventh confirm copy overall); the `test_every_feature_group_has_a_logs_command`
re-expression is still on the TODO.

**Verified:** ruff clean; 4529 passed; boot clean at 03:51:09Z (`database ready` / `synced 36` /
`logged in`, no Traceback). **NOT verified:** `/rolemenu` was not opened in Discord — no menu posted,
no role handed out or ended, the Grants audit was not opened, `rolemenu_mode`'s state was not read.
Sweeps **173–182** are the owner's to run, in `#mute-me-bot-test-spam`, as a Lead.

**With this landing WAVE 3 is COMPLETE and the panels program is DONE** — the program item follows,
moved whole from `TODO.md`.

---

## 2026-09-04 — Panels over slash commands — the program (waves 1–3 COMPLETE with v77; moved whole from `TODO.md`)

Moved WHOLE, unedited, from `docs/TODO.md` at the v77 landing (20:54). The status paragraphs inside it
are the running record, newest at the bottom of each wave; every landing it names has its own entry above.

- 🆕 **Panels over slash commands — the rest of the app (owner, 2026-09-03: "then carry it
  through the rest of the app"; confirmed ~11:25: "do the change to all / commands. I like
  how request works").** Audit every command group (44 commands synced; `cogs/core.py:88`
  lists them) and convert each feature to one command + panel the same way: `/event`,
  `/poll`, `/raidtrain(s)`, `/applications`, `/voice`, `/twitch`, `/birthday`, `/memory`,
  `/settings`, the moderation set. One feature per build, requests as the template
  (`info/requests-panel-design.md`); each gets its own design doc with the button table per
  state. Scope is now ALL commands — the sequence is the conductor's to plan, the design
  calls still go to the owner one at a time. Status: **PLANNED** (2026-09-03 11:10) — the
  program is written: [`info/panels-program.md`](info/panels-program.md) (§2 the 17
  invariants every panel inherits from `/request`, §3 the measured inventory — ~177
  subcommands over 44 top-level commands → ~21 commands, §4 **wave 0 = extract
  `black_bloc/panels.py` from the requests cog** so the three review defects cannot recur
  seventeen times, §5 four waves, §6 the three owner forks: F1 mod commands, F2 modmail's
  in-thread `/reply` set, F3 `/settings`). **Wave 0 is MERGED** (`1861923`, 2026-09-03 ~11:50:
  `black_bloc/panels.py` + `tests/test_panels.py`, 26 tests, the requests cog now inherits
  `Panel`; 160k Opus / 20 min; `code-notes.md` re-keyed at the merge) **and LIVE in v60**
  (2026-09-03 11:39; the wave-0 record itself is in `DONE.md` that date). **Wave 1 design
  docs IN FLIGHT** (owner "Build all, keep going", 2026-09-03 ~12:40): three Opus design
  agents writing `info/events-panel-design.md`, `info/polls-panel-design.md`,
  `info/birthdays-panel-design.md` (sweep rows reserved: events from 73, polls from 80,
  birthdays from 87; 66–72 belong to the two feature builds). `applications-panel-design.md`
  waits until `feat/applications-no-role` lands — its cog is being rewritten. **All three
  LANDED and REVIEWED against §2** (2026-09-03 ~12:15; 171k / 185k / 197k Opus). The
  staff-final-say rule settled three of five forks in-doc (polls `denied → open`, events
  `denied → approved` + a DM'd cancel note, no draft rows). F-B1 DECIDED 12:20 (keep today's behaviour: member lookup on, creator may end own poll).
  **The fourth wave-1 design exists:** [`info/applications-panel-design.md`](info/applications-panel-design.md)
  (2026-09-03, written against `9891f71` after the no-role merge — 17 subcommands over two groups
  collapse into one member-visible command; sweep rows 94–102; `denied`/`removed` → `approved`
  and the member's own list settled by the standing rules). Forks: **I-A1 DECIDED 13:35 — the
  command is `/apply`** ("it's gamer lingo"; the `applications` Group goes); **I-A2 DECIDED 13:47 —
  "Visible"** (`/apply` stays when the mode is off; the `HIDDEN_WHEN_OFF` entry goes); **I-A3 DECIDED
  14:12 — "Build the question sub panel"** (§C's Questions sub-panel as designed). Applications
  build landed 14:55 (401k), merged `853776c`, **live in v66 15:00** (43 → 42 commands). **WAVE 1
  COMPLETE** — four landings in `DONE.md` 2026-09-03. Waves 2–4 remain (§5 of the program).
  **Wave 2 design docs ALL LANDED 15:50–15:54** (five Opus design agents, one file each:
  `info/golive-panel-design.md` 205k, `info/voice-panel-design.md` 210k, `info/youtube-panel-design.md`
  192k, `info/pings-panel-design.md` 199k, `info/memory-panel-design.md` 204k — ⚠️ the 60k estimate was
  off 3×; calibrate design docs at ~200k). Golive REVIEWED against §2 15:52 (consistent: 4 rows in caps,
  member/staff split, one function per move with `via`, one key, no Settings sub-panel with the reason).
  The other four await Fable review. **All eight owner forks DECIDED 16:10–16:15 (owner asked for them
  rapid-fire in one form, 16:05 — a one-time exception to one-at-a-time):** golive I1 = **`/golive`**;
  golive I2 = **build the staff `Streamers…` sub-panel**; voice F1 = **leave the in-channel control post
  as it is**; pings I1 = **keep today's — a streamer may always take their own ping role away**; pings
  I2 = **two Events toggles when the two keys differ, one when they agree**; youtube F-Y1 = **keep
  `/youtube` and `/golive` separate**; youtube F-Y2 = **flip `youtube_mode` to shadow at the panel's
  landing** (operational, the conductor does it via the site); memory I-M1 = **open it — `/memory`
  stays visible with the mode off, the Forget controls keep working**. Builds in worktrees in cost
  order: memory → golive → youtube (230–300k) → pings (300–360k) → voice (420–480k); each brief
  carries its decided forks. **Memory LANDED 16:42 (329k — the 120–180k estimate was 2× off; a
  wave-2 build is ~2× its estimate, calibrate the rest up), merged `cb941d9`, live in v68 `cb941d9`
  16:48** (3710 → 3744 tests, 42 commands) — landing entry in `DONE.md` 2026-09-03; sweeps
  104–108 are the owner's to run (`chat_memory_mode` is still off live, so 104–107 need it on plus
  a conversation first). **Golive LANDED 17:05 (464k against a 230–300k estimate — again ~2×; four commits off `8cbe453`),
  Fable-reviewed approve, merged `0aeed72` (four append-only conflicts with the memory merge), live in
  v70 17:25** (3750 → 3796 tests, `commands synced` **42 → 41 measured at boot**) — landing entry in
  `DONE.md` 2026-09-03; sweeps 109–117 are the owner's to run. **Youtube LANDED 17:10 (371k against a
  180–250k estimate — ~2× again; three commits off `ea252bd`), Fable-reviewed approve, merged `b764757`
  (six append-only conflicts with the golive merge; its sweeps rows renumbered 130–137 → 118–125), live in
  v71 17:37** (3796 → 3872 tests, `commands synced` **41 → 40 measured at boot**), **F-Y2 done 17:42**
  (`youtube_mode` off → shadow on the Go-live page, PUT logged 00:42:53Z) — landing entry in `DONE.md`
  2026-09-03; sweeps 118–125 are the owner's to run. **Pings LANDED 18:25 (379k against a 300–360k
  estimate; four commits off `85e14c4`), Fable-reviewed approve with one merge-time fix, merged `a5ad521`
  (clean, no conflicts), live in v72 18:30** (3872 → 4050 tests, `commands synced` **40 → 39 measured at
  boot**) — landing entry in `DONE.md` 2026-09-03; sweeps 126–134 and the rewritten 38–42 are the owner's
  to run. **Voice is the last wave-2 panel** — F1 RE-CONFIRMED by the owner 21:20 ("Leave it as is" = (a),
  the in-channel control post stays untouched); design Fable-reviewed against §2 21:25 (consistent on
  P1–P17; drift since it was measured, carried in the brief: 39 → 38 commands not 42 → 41, sweeps start
  at **135** not 104, `panels.site_page_url(origin, "tempvoice")` now exists so no copy, `panel_minutes`
  takes a key, `voice_panel_minutes` also gets its `labels.js` + `server.mjs` label like golive/pings).
  **Voice LANDED 21:55 (385k against a 420–480k estimate — the first to land UNDER; five commits off
  `2854d74`), Fable-reviewed approve with one merge-time fold (`clamped` into `panels.py`), merged
  `4d64b36` (clean, no conflicts), live in v73 22:08** (4050 → 4265 tests, `commands synced` **39 → 38
  measured at boot**) — landing entry in `DONE.md` 2026-09-03; sweeps 135–143 are the owner's to run.
  **WAVE 2 COMPLETE.** Owner 2026-09-04 09:05 "Keep going" → **wave-3 design docs DISPATCHED 09:15**
  (four Opus agents in parallel, one doc each — `info/raidtrain-panel-design.md`,
  `info/role-menus-panel-design.md`, `info/chat-panel-design.md`, `info/automod-panel-design.md` —
  ~200k each, read-only on code, no commits). **All four LANDED 09:21–09:33 and Fable-reviewed APPROVE**
  (raidtrain 595 lines / 250k; role menus 622 / 230k; chat 533 / 241k; automod 626 / 209k — see the
  `info/README.md` rows). `commands synced` after all four: 38 → **36** (raidtrain −1, role menus −1, chat and
  automod 0). **Conductor prep DONE 09:50:** `still_allowed(interaction, ok, refusal)` is on `main` in
  `panels.py` (raidtrain §F), `still_staff` is a two-line call to it, three tests in `tests/test_panels.py`,
  code-note at `panels.py:31` — wave-3 builds branch from this commit or later and USE it, never copy it; the
  numbers-modal validator (role menus §F) and the confirm helper (automod §F, youtube `open_confirm` + pings
  deviation 8 + automod = three copies) are FOLDED AT MERGE, not pre-built. **13 forks go to the owner ONE AT
  A TIME, in this order:** raidtrain F-R1/F-R2/F-R3 · role menus F-R1/F-R2/F-R3 · chat F-C1/F-C2/F-C3/F-C4 ·
  automod F-A1/F-A2/F-A3 (every recommendation is (a); chat F-C3 recommends NO confirm on the money
  switch while automod F-A1 recommends a confirm on arming — different reasons, both stated). Answers are
  recorded here as they come — **DECIDED 2026-09-04 between 09:32 and 15:08 Phoenix (the clock was read at those two ends, not per
  answer — earlier per-answer stamps here were inferred and have been removed):** raidtrain F-R1 = (a) no lineup-post button ("Leave it"); F-R2 = (a) upcoming trains only in the picker; F-R3 = (a) one claim select, no
  next-open-hour button — RAIDTRAIN FULLY DECIDED. Role menus F-R1 = (a) build the Waiting-on-staff
  sub-panel; F-R2 = (a) `0` days = no end date **PLUS an owner amendment to the design
  (verbatim: "let's have an audit menu that shows durations of active roles")** — the `Grants…` sub-panel
  opens as an AUDIT of every active timed role in the guild (member · role · time left / end date, or
  `no end date`; soonest-ending first; 25-capped with `capped_placeholder`), and the "Whose roles?"
  `UserSelect` NARROWS that list rather than being the only way in; the embed body lists them as lines so
  the count is readable even when the select is capped. Goes in the role-menus build brief as §I-amend.
  F-R3 = (a) every edit re-renders the posted panel in place — ROLE MENUS FULLY DECIDED.
  Chat F-C1 = (a) read-only numbers + one `Limits…` modal for all five; F-C2 = (a) `Edit…` on the note
  card; F-C3 = (a) one click to turn chat on, no confirm — the spend cap is the brake;
  F-C4 = (a) both mood-pool guards on both doors, one implementation in `chat_panel.py` — CHAT FULLY
  DECIDED. Automod F-A1 = (a) confirm before arming, `automod_arm_needs_confirm` default true; F-A2 = (a) one
  prefilled paragraph field for bad words, over-4000 says use the website; F-A3 = (a) no controls for
  `automod_warn_threshold` / `mod_dm_on_action`, read-only lines pointing at the Moderation page —
  **ALL 13 FORKS DECIDED, every one (a), plus the role-menus Grants audit amendment. Builds may start.**
  Then builds in cost order (automod ~300–360k, chat ~300–360k, raidtrain
  380–450k, role menus 420–500k), each Opus in its own worktree off `main`, layer-boundary commits, sweeps
  numbered from 144 at build time; usage read before each dispatch; weekly cut-off 90%.
  **DISPATCHED 2026-09-04 15:10 Phoenix: automod AND chat builds IN PARALLEL** (Opus, own worktrees
  off `5db58fb`; usage at dispatch session 2% / weekly 0% / Fable 1% — the weekly had reset with a "50% higher
  through September 13" boost on the page). **Automod LANDED (370k against a 300–360k estimate; three
  commits off `5db58fb`), Fable-reviewed approve with one merge-time relabel (the Settings toggle says what it
  will do), merged `0b1b2bf` (clean, no conflicts), live in v74 15:45** (4265 → 4332 tests, `commands synced`
  **38 → 38 measured at boot**) — landing entry in `DONE.md` 2026-09-04; sweeps 144–154 are the owner's to run.
  **Chat LANDED (441k against 300–360k; five commits off `5db58fb`), Fable-reviewed approve, merged
  `251dd14` (five append-shaped conflicts against automod, all resolved HEAD-then-branch; sweeps `C1`–`C8`
  numbered 155–162 at the merge), live in v75 15:58** (4332 → 4402 tests, `commands synced` **38 → 38
  measured at boot**) — landing entry in `DONE.md` 2026-09-04; sweeps 155–162 are the owner's to run.
  **Raidtrain LANDED (473k against 380–450k; four commits off `4523118`), Fable-reviewed approve, merged
  `2dd2689` (clean, no conflicts; sweeps 163–172 numbered on the branch; owner-guide count 162 → 172),
  live in v76 16:56** (4402 → 4465 tests, `commands synced` **38 → 37 measured at boot**) — landing entry
  in `DONE.md` 2026-09-04; sweeps 163–172 are the owner's to run; `raidtrain_mode` still off.
  **Role menus LANDED 16:53 (529k against 420–500k; four commits off `4523118`), Fable-reviewed approve
  (§I-amend Grants audit built: `active_grants`/`grant_lines` in the pure module, soonest-ending first,
  no-end-date last, 25-cap; `tests/api/tools/test_roles.py` unchanged is the proof the reconciliation did
  not move the site; `web.rolemenu.*` → `web.role_menu.*` kinds renamed, `HEADS["rolemenu"]` kept), merged
  `43312b9` (eight append-shaped conflicts, all resolved both-sides; `M1`–`M10` → sweeps 173–182;
  owner-guide count 172 → 182; `tests/test_bot.py` pin 37 → 36), live in v77 20:51** (4465 → 4529 tests,
  `commands synced` **37 → 36 measured at boot**) — landing entry in `DONE.md` 2026-09-04; sweeps 173–182 are
  the owner's to run. **WAVE 3 COMPLETE — the panels program's 17 features are all one command + panel.**
  DISPATCHED 2026-09-04 16:03 Phoenix: raidtrain AND role menus builds IN PARALLEL (Opus, own worktrees
  off `251dd14`; usage at dispatch session 12% / weekly 3% / Fable 3%; raidtrain numbers sweeps from 163 with
  digits, role menus writes `M1…` and the conductor assigns digits at the merge, as chat did; both pin
  `tests/test_bot.py` at what THEIR branch measures — 37 each — and the conductor reconciles to 36 at the
  second merge; role menus carries the owner's §I-amend Grants audit). If this session dies: `git worktree list` /
  `git branch --list 'worktree-agent-*'` finds a branch; merge only one whose FINAL commit is a doc/string
  sweep with a passing full suite.
  Events I2 DECIDED 12:40 (`/timezone` retired).
  **Wave-1 builds all landed 13:40–13:50** (birthdays merged `58974e1`; events on
  `worktree-agent-a448c7ab780ed3c2b`, polls on `worktree-agent-aa735ab092d13477d`, both under Fable
  review); the applications build follows once I-A3 is answered. Merge in wave order, re-key
  `code-notes.md` per merge, deploy per landing. ⚠️ The v63 deploy REFUSED at the gate 13:52 on the
  rate-limit flake — fixed by freezing the clock in the test (`code-notes.md` →
  `tests/api/test_settings_api.py:221`), three `-n auto` runs green; **v63 live 13:58, v64
  (events, `e670542`) live 14:05** — both landings recorded in `DONE.md` 2026-09-03. Polls merged
  `27452ac` (3644 tests), **live in v65** (`d13e1a4`, 14:14) — landing entry in `DONE.md`.

---

## 2026-09-04 — Raid train panel: `/raidtrain` is one window (wave 3 THIRD landing, v76, `2dd2689`)

Release **v76** (`2dd2689`, 16:56; `deploys.log` line 75). Merge `--no-ff` of
`worktree-agent-aba5d44f8e27a8e28` — **four commits off `4523118`** (`3e54d52` the pure half,
`f584676` the cog and the shared functions, `4bb059c` the routes and the tests, `656e771` the
doc sweep). Built by one Opus agent for **473k against a 380–450k estimate** (dispatched 16:03
in parallel with role menus, landed first), Fable-reviewed **approve**. Design:
`info/raidtrain-panel-design.md` (header flipped to SHIPPED; its `## Deviations` foot lists 14).

**What it is.** The `raidtrains` staff group and the `raidtrain` member group's fifteen leaf
subcommands are retired for ONE member-visible `/raidtrain` that opens an ephemeral panel: the
root lists the upcoming trains (a select picks one; F-R2 (a) — past trains stay on the site), a
Lead sees **Setup…**, **Logs** and the mode select; a train card shows the lineup with **Take a
slot** (one claim select, F-R3 (a) — `may_claim` is the ONE place the who-may-take rule lives,
read by the select's options and by the refusal), **Give back**, **Mine**, and for organizers
**Put in**, **Take somebody off**, **Swap**, **Lock the lineup** / **Open it for sign-ups** and
**Call it off** (a reason is required, through `NoteModal`). No lineup-post button (F-R1 (a)).
Every move is an async shared function in `cogs/content/raidtrain.py` carrying `via`
(`claim_slot`, `release_slot`, `assign_slot`, `unassign_slot`, `swap_slots`, `move_train`,
`create_and_publish`, `set_mode`, `save_setup`), each writing ONE `log_action(kind_via(...))`
row; `api/tools/raidtrain.py` calls the same functions with `via=VIA_WEBSITE` through
`answered(outcome)` → `Refused(status, code, message)`, so the recorded Via-labelling gap is
closed and **`web.raidtrain.cancel` is written for the first time**. `Outcome` and `refusal`
moved UP into `black_bloc/panels.py` (`chat_panel.py` now imports them from there — the fold
the chat landing asked for, done here). New key `raidtrain_panel_minutes` (int, 10) in its own
`settings_store` block. `commands synced` **38 → 37, measured at boot**.

**The merge.** Clean — no conflicts (role menus was still on its branch). The branch numbered
its sweep rows **163–172** with digits (it was told chat's 155–162 were fixed); the conductor
moved the `OWNER_GUIDE.md` count 162 → 172. `docs/info/code-notes.md`'s `# Raidtrain panel
(wave 3)` section was re-keyed to the merge. **4402 → 4465 tests.** Deviations worth knowing
(the foot has all 14): the card's buttons and selects are split into `card_buttons` /
`card_selects` so the lineup row stays ≤5; **Take somebody off** is gated on open/locked;
option labels are plain `%H:%M UTC` (no markdown inside a select option); `NOBODY_THERE` stays
in the cog; `move_train` covers live AND done; `FEATURE_OFF` was deleted; the `phase18-design.md`
superseded banner (which wrongly described `/golive`/`/twitch`) and `cutover-plan.md:45` were
fixed in passing; the optional labels/mock rider was skipped.

**Review findings, non-blocking, deferred to the fold sweep:** `opened()` is a SECOND cog-local
copy (automod has the first; chat inlines the triplet 14×); and
`tests/test_bot.py::test_every_feature_group_has_a_logs_command` now covers five groups only —
already on the TODO to re-express against the panels' Logs button.

**Verified:** ruff clean; 4465 passed; boot clean at 23:56:13Z (`database ready` / `synced 37`
/ `logged in`, no Traceback). **NOT verified:** `/raidtrain` was not opened in Discord — no
hour claimed, no train cancelled from the site, no DM sent; `raidtrain_mode` is still **off**
everywhere, so row 163 (the panel with the mode off) is the first thing the owner sees. Sweeps
**163–172** are the owner's to run, in `#mute-me-bot-test-spam`, as a Lead.

---

## 2026-09-04 — Chat panel: `/chat` is one window (wave 3 SECOND landing, v75, `251dd14`)

Release **v75** (`251dd14`, 15:58; `deploys.log` line 74). Merge `--no-ff` of
`worktree-agent-ab33797d235cf0d96` — **five commits off `5db58fb`** (`d08994d` the pure half
`black_bloc/chat_panel.py`, `99dd8d5` the cog, `e4304e1` the logkinds table, `b0b62b1` a note
card keeping the filter words, `1767109` the doc sweep). Built by one Opus agent for **441k
against a 300–360k estimate** (dispatched 15:10 in parallel with automod, landed second),
Fable-reviewed **approve**. Design: `info/chat-panel-design.md` (header flipped to SHIPPED).

**What it is.** The `chat` group's eight leaf subcommands are retired for ONE staff-only
`/chat` that opens an ephemeral panel: the status block at the root (mode, the two tiers, the
turns and money — hidden by `chat_status_admin_only` for non-administrators — and the notes
count), then **Personality…** (the voice select and the two mood selects), **Knowledge…** (the
note picker, **Write one down…**, **Edit…**, **Remove** behind a confirm, **Find…**),
**Settings** (read-only numbers plus **Limits…**), the two mode toggles and **Logs**. The
forks landed as decided, every one (a): **F-C1** Settings WRITES through one five-field
`LimitsModal` (five is Discord's ceiling); **F-C2** a note is edited in the SAME
`NoteFieldsModal` prefilled; **F-C3** turning the models on is one press — the monthly cap is
the brake; **F-C4** the two mood-pool guards moved onto the Discord door, and the ONE place
they live is `chat_panel.mood_options` / `mood_refusal`, read by both the select (which never
offers a move the function would refuse) and `set_mood` itself. Every move is an async shared
function in `black_bloc/chat_panel.py` carrying `via`; `api/tools/chat.py` now calls the same
functions with `via=VIA_WEBSITE`, which is how the two doors stay one implementation
(checklist 15/17). New key `chat_panel_minutes` (int, 10) in its own `settings_store` block;
log kinds `chat.mode` and `chat.settings` classify ROUTINE; the chat row left `LOGS_GROUPS`.
`commands synced` **38 → 38, measured at boot** (a group already counted as one slot).

**The merge.** Five conflicts, all append-shaped, because both wave-3 branches appended at the
same anchors: `settings_store.py` (three hunks — the first two interleaved the automod and chat
KEY_HELP blocks around a shared help-text tail, resolved by splitting them back into two whole
blocks, automod first; the defaults hunk keeps all three `if key ==` lines), `labels.js`,
`tests/test_settings_store.py`, `sweeps.md` and `code-notes.md` (HEAD then branch, byte for
byte). The branch wrote its sweep rows as `C1`–`C8` on purpose — two builds numbering from 144
concurrently — and the conductor numbered them **155–162** at the merge and moved the
`OWNER_GUIDE.md` count 154 → 162. `docs/info/code-notes.md`'s `# Chat panel (wave 3)` section
was re-keyed to the merge. **4332 → 4402 tests** (`tests/test_chat_panel.py` is new;
`tests/cogs/content/test_chat.py` rewritten around the panel).

**Review finding, non-blocking, deferred to the fold sweep:** the `still_staff` / `defer` /
`db_ready` triplet is repeated **14×** in `cogs/content/chat.py` where automod has a cog-local
`opened()` helper — fold an `opened()` into `black_bloc/panels.py` in the same sweep as the
confirm helper, of which this build adds the **sixth** copy (`RemoveYesButton` / `KeepItButton`).
Cosmetic, not acted on: the **Settings** button lacks the ellipsis every other sub-panel
opener carries.

**Verified:** ruff clean; 4402 passed; boot clean at 22:58:25Z (`database ready` / `synced 38`
/ `logged in`, no Traceback). **NOT verified:** `/chat` was not opened in Discord — no note
written, no model called, no mood moved, the Limits modal not submitted, and the website chat
page not exercised after its routes moved onto `chat_panel`. Sweeps **155–162** are the
owner's to run, in `#mute-me-bot-test-spam`, as a Lead.

## 2026-09-04 — Automod panel: `/automod` is one window (wave 3 FIRST landing, v74, `0b1b2bf`)

Release **v74** (`0b1b2bf`, 15:45; `deploys.log` line 73). Merge `--no-ff` of
`worktree-agent-ae7bb4ba9c5540ad4` (Opus build, **370k** against a 300–360k estimate; three commits off
`5db58fb`: `8c5bee9` pure module, `d0fa2c9` cog, `220cacc` docs) after Fable review — approve with one
merge-time relabel: the Settings toggle read "Arming asks twice" / "Arming is one press" (the current
state) and now reads **Stop asking before arming** / **Ask before arming** (what it will do — the
standing button rule). **Clean merge, no conflicts.** The eight `/automod` leaf subcommands became one
staff panel: the pure `black_bloc/automod.py` holds the tables (`PANEL_MOVES`, `card_buttons`,
`root_buttons`, `settings_buttons`, `confirm_buttons`, `mode_options(current, may_arm)`,
`needs_confirm`, `rule_field_labels`, `exempt_options`, `typed`, `panel_minutes`, `arm_needs_confirm`;
`_as_words` learned newlines so the Words… modal matches the site's textarea) and the cog routes every
press through `opened()` (still_staff + defer + db_ready) to `run_rule` / `run_mode` / `run_exempt` /
`run_settings`; `arming_refusal` is read by both the mode select (so `on` is never offered while it
would be refused) and `set_mode` (so offer and verdict cannot disagree); the confirm card sits behind
`automod_arm_needs_confirm` (default true, owner fork F-A1 = a) and going quieter is one press;
bad words is one prefilled paragraph field, over 4000 chars says use the website (F-A2 = a);
`automod_warn_threshold` / `mod_dm_on_action` are read-only lines pointing at the Moderation page
(F-A3 = a). Enforcement untouched — `punish`, `do_delete`, `do_timeout`, `_answer_for` byte-identical.
Deviations at the design doc's foot (a Settings sub-panel exists, for the two new keys' Discord door —
checklist 33). Keys `automod_panel_minutes` (10) and `automod_arm_needs_confirm` (true) with their
`labels.js` + `server.mjs` rows; `LOG_LEVEL_COMMANDS["automod"]` and the `LOGS_GROUPS` automod row
retired. Verified: boot clean (22:45:04Z database ready / **synced 38** (38 → 38 as measured) /
22:45:08Z logged in, no Traceback), ruff clean, **4332 tests** (4265 + 67, none lost). NOT verified:
`/automod` has not been opened in Discord, no button pressed, no rule or exemption changed, no message
judged — sweeps 144–154 (`access/sweeps.md`) are the owner's. Review link: `/automod` in
`#mute-me-bot-test-spam`; the site's Automod page is unchanged at
<https://blackbloc.heygabi.ai/automod.html>. Deferred to their own items on `TODO.md`: the confirm
helper is now FIVE copies (memory, birthdays, youtube, pings, automod `build_confirm`/`confirm_buttons`)
— a fold sweep, not a merge-time edit; the settings-API-can-arm defect is **KI-21**; `LOG_LEVEL_COMMANDS`
is stale for eight features. The chat build was in flight in its own worktree when this shipped.

## 2026-09-03 — Voice panel: `/voice` is one window (wave 2 COMPLETE, v73, `4d64b36`)

Release **v73** (`4d64b36`, 22:08; `deploys.log` line 72). Merge `--no-ff` of
`worktree-agent-a386d425f5527fe95` (Opus build, **385k** against a 420–480k estimate — the first wave-2
build to land UNDER its estimate; five commits off `2854d74`: `128c716`, `492fe16`, `1f7fedd`, `c35fac6`,
`377dbcb`) after Fable review — approve, no defect; one merge-time fold per the build's own deviation 8:
`clamped()` and `DESCRIPTION_LIMIT` now live once in `black_bloc/panels.py` and the copies in the pings
and tempvoice cogs are gone. **Clean merge, no conflicts.** The 22 `/voice` + `/tempvoice` subcommands
became one ephemeral panel: the pure `black_bloc/tempvoice.py` holds the state table
(`panel_state` → blocked/none/owner/orphan/guest, `card_buttons`, `people_controls`, `undo_options`,
`named_regions` = 25 so no select is capped) and the cog's `VoicePanel` routes every press to the
existing `do_*` helpers (`act_on_own` re-reads ownership on every press, `ready_to_move` defers +
`db_ready`); staff moves (Setup, Forget a lobby…, join-to-create on/off, Logs, the staff card's
Hand it over… with a DM to the new owner) re-ask `still_staff` on every press; the in-channel control
post is untouched (owner fork F1 = "Leave it as is"). 13 deviations at the design doc's foot, all
P-consistent (Forget a lobby lists stored ids only — a stray cannot be forgotten, so it is not offered).
Key `voice_panel_minutes` (10) with its `labels.js` + `server.mjs` rows. Verified: boot clean
(05:08:39Z database ready / **synced 38** (39 → 38 as measured) / 05:08:43Z logged in, no
Traceback), ruff clean, **4265 tests** (4050 + 215, none lost). NOT verified: `/voice` has not been
opened in Discord, no button pressed, no channel renamed/locked/moved, no DM sent — sweeps 135–143
(`access/sweeps.md`) are the owner's. Review link: `/voice` in `#mute-me-bot-test-spam`. Cost note for
the calibration table: memory 329k, golive 464k, youtube 371k, pings 379k, voice 385k — the ~2× pattern
held for the first two and not the last three.

## 2026-09-03 — Decision: YouTube lives stay with `/golive`; uploads stay on shadow (no build)

Owner asked at 17:59 to announce a linked channel *going live* on YouTube by default and make
"every upload" an opt-in switch, off by default. Fable's read: the uploads sweep deliberately skips
live broadcasts (`cogs/content/youtube.py` `_skipped` → "live") because `/golive` already announces
YouTube lives from Discord presence (`golive.py` `platform_of`), and without `YOUTUBE_API_KEY` (not
set on Fly, measured 18:00) the public feed cannot tell a live from an upload (phase 16 D6). Told
that, the owner withdrew it at 18:05: **do not add live detection to `/youtube`; keep `youtube_mode`
on shadow for now; going on is a staff decision** — which it already is (Setup on the `/youtube`
panel and the Go-live page switch are both staff-gated). Nothing changed in code or settings;
`youtube_mode` is `shadow` since 17:42 (F-Y2). If uploads are ever wanted on, staff flip the switch;
if YouTube lives ever need catching without presence, that is the withdrawn design plus the API key.

## 2026-09-03 — Pings panel: `/pings` is one window (wave 2, v72, `a5ad521`)

Release **v72** (`a5ad521`, 18:30; `deploys.log` line 71). Merge `--no-ff` of
`worktree-agent-a86e71fd801362ca2` (Opus build, **379k** against a 300–360k estimate — the first wave-2
build to land near its estimate; four commits off `85e14c4`: `ec1a54e` extractions, `cb73075` the cog,
`13450dd` strings and docs, `cf70ec8` the checklist sweep) after Fable review — approve, one defect fixed
at the merge: `run_settings` appended the Names… modal's "Saved. A streamer's ping role will be called…"
echo even when `save_settings` had refused a value, so a failed save read as a success; the echo now
follows only a `SETTINGS_SAVED` answer. **Clean merge, no conflicts** (the branch was cut after golive
and youtube were both in). Verified: boot clean (01:30:29Z database ready / **synced 39** / 01:30:33Z
logged in), ruff clean, **4050 tests** (3872 + 178, none lost). This deploy also applied the staged
`OPERATOR_READ_TOKEN` (see the entry below). NOT verified: `/pings` has not been opened in Discord, no
button pressed, no select submitted, no role moved — sweeps 126–134 and the rewritten 38–42
(`access/sweeps.md`) are the owner's. Whether a real Discord client submits an EMPTY `RoleSelect`
(`min_values=0`) is the one open question; both paths are built (the confirm button also means "make
one"), so either answer works.

What shipped. `/pings` is a single member-visible command opening an ephemeral panel; the `pingroles`
group and the twelve `pings`/`pingroles` subcommands are retired — both decided forks built as decided
(**I1 = (a)** a streamer may always take their own ping role away, whatever `pings_fan_role_creation`
says; **I2 = (b)** one Events toggle while the go-live and event keys agree or either is unset, two
labelled toggles once they point at different roles). Members: **Follow a streamer…** / **Stop
following…** selects (25-capped, the placeholder says so), the Events toggle(s), **Start my own ping
role** (only when they stream and creation is not staff-only), **Take my ping role away** behind
**Keep it / Yes, take it away**, **Refresh**; unfollowing is never mode-gated. Staff: **Streamers…**
(lines with follower counts, a streamer picker to a card with **Remove their ping role** behind a
confirm and **Make the role again** when Discord no longer has the role, **Give somebody a ping role…**
user-select into the shared role-pick step), **Set up the Events role** (the same role-pick step:
`RoleSelect` `min_values=0`, empty means make one), **Settings** (mode / who may start one / on-unlink
selects, a delete-too toggle, **Names…** modal for the Events role name, the streamer template and the
panel minutes — the template is echoed as it will RENDER, checklist 17), **Logs**, **Open on the site**.
The button table is `panel_buttons(PanelState, staff=)` in `black_bloc/pings.py`, proved as data by a
128-case parametrised test (deviation 1: a composing function over a NamedTuple, not a dict, because I2
makes the events half variable-length). New shared moves `follow_streamer`, `set_event_pings`,
`start_own_fan_role(streams=)`, `stop_own_fan_role`, `save_settings` (validates every key with
`coerce_value` before the first write; new `pings.settings` log kind), `notification_lines`,
`streamer_lines`, `counts_of`, `template_preview`. `panels.site_page_url(origin, feature)` is now the one
home; applications/polls/events/golive/requests delegate, the youtube cog's copy deliberately left
(returns `""` and uses its own `SITE_PAGE` — folding it would change a just-landed file). Key
`pings_panel_minutes` (10), checklist 33; a second `LABEL_LIMIT = 100` deleted (checklist 15); two test
doubles repaired (`FakeGuild.create_role` reused ids after a deletion). Design
[`info/pings-panel-design.md`](info/pings-panel-design.md) (seventeen deviations at its foot);
`OWNER_GUIDE.md` 125 → 134 rows; `code-notes.md` pings keys point by anchor on the branch (NOT re-keyed
against `a5ad521`). Review link: `/pings` in `#mute-me-bot-test-spam`; the Go-live tab of
https://blackbloc.heygabi.ai/golive.html shows the same ping roles.

## 2026-09-03 — Operator read token: minted, deployed, door verified (v72)

Code shipped in v67 `285b5e3` (16:04; the build record is the entry below). The mint was blocked twice
by the permission classifier (the `flyctl secrets set` command at 16:15; the session editing
`~/.claude/settings.json` at 16:30), so at 17:55 the owner ordered the session to do both ("Do this:
\scripts\mint-operator-token.ps1 in ~/.claude/settings.json, then say retry"): the rule
`PowerShell(.\scripts\mint-operator-token.ps1:*)` went under `permissions.allow`, the script ran at
17:56 (python mints, `flyctl secrets set --stage`, HKCU `BLACK_BLOC_OPERATOR_TOKEN`; value never
printed), `flyctl secrets list` showed **Staged** (digest 6158ac0c…). v72 (`a5ad521`, 18:30) applied it —
**Deployed** — and the door was measured at 18:31: `GET /api/settings` with the bearer **200**, the same
request anonymous **401**; `/api/health` is not a route (404 — the health door is `/health`). NOT
verified: the `web.operator.read` Core log row (`operator_read_log`) was not looked for. Runbook:
`access/operator-read.md`. History as it stood in `TODO.md` at landing:


- **Operator read token — MINTED 17:56, STAGED, goes live at the next deploy (the pings release);
  moves to `DONE.md` once a bearer read is verified live.** (Code live v67 `285b5e3` 16:04; the build
  record is in `DONE.md` 2026-09-03.) 17:55 the owner ordered the session to add the rule itself
  ("Do this: \scripts\mint-operator-token.ps1 in ~/.claude/settings.json, then say retry") — rule added,
  script ran, `flyctl secrets list` shows `OPERATOR_READ_TOKEN` **Staged** (digest 6158ac0c…),
  `BLACK_BLOC_OPERATOR_TOKEN` set for the user (64 chars), value never printed. Verify after the
  deploy: `/api/health` with the bearer answers, and `operator_read_log` writes one Core row. History: The blind mint (`docs/access/operator-read.md`, one command: python mints,
  `flyctl secrets set --stage`, HKCU `BLACK_BLOC_OPERATOR_TOKEN`, value never printed) was approved by
  the owner 16:00 ("Yes") but the permission classifier BLOCKED the command at 16:15. Owner chose the
  permission-rule route (16:30: "Add a permission rule for flyctl secrets set … and tell me to retry");
  the classifier ALSO blocked the session editing `~/.claude/settings.json`, so the owner adds the rule
  himself — `PowerShell(.\scripts\mint-operator-token.ps1:*)` under `permissions.allow` — then the
  session retries `.\scripts\mint-operator-token.ps1` (the mint wrapped as a script so a rule has a
  stable prefix to match; `access/operator-read.md`). Until the secret is set the door does not exist
  (`/health` + a bearer answer `not_signed_in`, verified live by the builder). `--stage` means it
  applies at the NEXT deploy — v68.

## 2026-09-03 — YouTube panel: `/youtube` is one window (wave 2, v71, `b764757`)

Release **v71** (`b764757`, 17:37; `deploys.log` line 70). Merge `--no-ff` of
`worktree-agent-a74823f4d9293d080` (Opus build, **371k** against a 180–250k estimate — the third wave-2
build to run ~2× its estimate; three commits off `ea252bd`: code `7809b57`, tests `7f800cb`, docs) after
Fable review — approve, no blocking defect (one path per move with `via`; `LinkRefused` keeps the site's
400/409; `still_staff` gates every non-mine path; the DM'd reason is a key; both keys registered). Six
merge conflicts, every one an append-only collision with the golive merge (`personas.py` both panel
lines; `settings_store.py` both key blocks; `phase16-design.md` both SUPERSEDED banners; `sweeps.md` —
the branch wrote its rows as 130–137 because golive had reserved 109–129, so they were **renumbered to
118–125 at the merge** and row 47's cross-reference with them; `OWNER_GUIDE.md` 125 rows; `code-notes.md`
header). Both branches had pinned `tests/test_bot.py` at 41 for their own drop; together it is **40**, so
the test now says 40. Verified: boot clean (00:37:42Z database ready / **synced 40** / 00:37:45Z logged
in), ruff clean, **3872 tests** (3796 + 76, none lost). **F-Y2 done 17:42**: `youtube_mode` flipped
off → shadow from the Go-live page's "Whether the bot posts new YouTube uploads" switch — `PUT
/api/settings/youtube_mode 200` on Fly at 00:42:53Z, `/api/settings` reads `shadow`. (The first two
attempts, clicked by accessibility ref, never reached the switch's handler and the tree then misreported
"on" as pressed — the value was checked at the API before and after, and a real DOM click did it.) NOT
verified: `/youtube` has not been opened in Discord, no button pressed, no modal submitted, nothing
fetched from YouTube — sweeps 118–125 (`access/sweeps.md`) are the owner's.

What shipped. `/youtube` is a single member-visible command opening an ephemeral panel; the `youtube`
and `uploads` groups and their nine subcommands are retired — both decided forks built as decided
(**F-Y1 = `/youtube` and `/golive` stay separate**, **F-Y2 = shadow at landing, by the conductor on the
site**, owner 16:15). Members: **Link my channel** (one-line modal; **Relink** afterwards, prefilled) and
**Unlink** behind a **Keep it / Yes, forget it** confirm, from a `card_buttons(linked, mine, staff)`
table keyed `(mine, linked)`. Staff: the health block inline (`health_lines` — sweep running, last good
sweep, last error, counts, API key set or not), the linked list as lines beside a linked-member picker
(deviation 3), **Link for somebody**, **Relink for / Unlink for** on their card (the unlink DMs the
member the reason via `tell_unlinked` when `youtube_unlink_dms_them` is true — a member unlinking their
own is never DMed), **Setup** (upload channel, ping role, off/shadow/on select, words, numbers, and a
**Forget…** view with Back — deviation 4) and **Logs**. One function per move with `via`
(`link_channel/unlink_channel/set_mode/save_setup`) serves BOTH doors: `api/tools/youtube.py` now calls
them with `via=VIA_WEBSITE`; `link_channel` raises `LinkRefused(status=, code=)` and returns
`(said, row, counted)` so the site keeps its exact 400/409 bodies without a second YouTube resolve
(deviation 1); `save_setup` validates every value with `coerce_value` before writing any (deviation 9);
`YouTubeError` carries a `network` flag decided at the raise site (deviation 7). Keys
`youtube_panel_minutes` (10) and `youtube_unlink_dms_them` (true), checklist 33. §K finding 1 fixed
because checklist 10 forced it (a link whose feed did not answer no longer claims "0 counted as seen");
findings 2, 3, 4, 6 reported and left, 5 moot. Design
[`info/youtube-panel-design.md`](info/youtube-panel-design.md) (eleven deviations at its foot);
`OWNER_GUIDE.md` and `code-notes.md` youtube keys point by anchor on the branch (NOT re-keyed against
`b764757` — anchor text is authoritative). Review link: `/youtube` in `#mute-me-bot-test-spam`; the
YouTube uploads section of https://blackbloc.heygabi.ai/golive.html shows the switch on shadow.

## 2026-09-03 — Go-live panel: `/golive` is one window (wave 2, v70, `0aeed72`)

Release **v70** (`0aeed72`, 17:25; `deploys.log` line 69). Merge `--no-ff` of
`worktree-agent-a87a00d41b8dc47d1` (Opus build, **464k** against a 230–300k estimate — the second wave-2
build to run ~2× its estimate; four commits off `8cbe453`: code, tests, the cross-feature string sweep,
docs) after Fable review — approve, no blocking defect. Four merge conflicts, every one an append-only
collision with the memory merge (`settings_store.py` both `*_panel_minutes` blocks; `sweeps.md` memory
rows 104–108 then golive rows 109–117 — the numbering held, nothing renumbered; `OWNER_GUIDE.md` 117 rows
plus the golive row; `code-notes.md` header, both sentences kept). Verified: boot clean (00:25:01Z
database ready / **synced 41** — the 42 → 41 drop the build measured through `tests/test_bot.py` is now
measured at a real boot / 00:25:05Z logged in), ruff clean, **3796 tests** (3750 + 46, none lost). NOT
verified: `/golive` has not been opened in Discord, no button pressed, no Helix call made —
sweeps 109–117 (`access/sweeps.md`) are the owner's.

What shipped. `/golive` is a single member-visible command opening an ephemeral panel; the `golive` and
`twitch` groups and their eight subcommands (`/twitch link`, `/twitch unlink`, `/golive optout`,
`/golive optin`, `/golive status`, `/golive mode`, `/golive test`, `/golive logs`) are retired — both
decided forks built as decided (**I1 = `/golive`**, **I2 = the staff `Streamers…` sub-panel**, owner
16:10). Members: **Link my Twitch channel** (one-line modal; **Change my channel** afterwards,
prefilled), **Unlink**, and exactly one of **Stop announcing my streams** / **Announce my streams
again** from a `panel_buttons(linked, opted_out, staff)` table proved by a parametrised test. Staff: the
whole of the old status embed inline (mode, stream end, channel, cooldown, twitch polling, last good
poll, last poll error, counts, who is live now — in test mode the channel line SAYS when
`golive_channel_id` is not the test channel), **Logs**, **Streamers…** (unlink or opt out somebody else,
the same moves the Go-live page makes), **Preview an announcement…** (ephemeral, never pings, never
posts) and an **off / shadow / on** select. One function per move with `via`
(`link_channel/unlink_channel/opt_out/opt_in/set_mode`) serves BOTH doors: `api/tools/golive.py` now calls
them with `via=VIA_WEBSITE`, so the fan-role step (`pings.maybe_auto_create` / `pings.on_streamer_left`)
finally runs on the website too — it was the configured behaviour the site was quietly not honouring
(deviation 3). `checked` now means *a Helix lookup confirmed the channel* (`twitch_user_id is not None`);
the old `helix is None` expression would have written `checked: true` into `action_log` beside a route
body saying `false` — found by `tests/api/tools/test_golive.py`, not by reading (deviation 1). One key
`golive_panel_minutes` (default 10, checklist 33; `labels.js` entry). Design
[`info/golive-panel-design.md`](info/golive-panel-design.md) (eight deviations at its foot); rows 12,
19, 31, 49 of `sweeps.md` and the Phase 2 appendix rewritten in place; `OWNER_GUIDE.md` gains the
"Link your Twitch" row; `code-notes.md` golive keys re-pointed by anchor on the branch (NOT re-keyed
against `0aeed72` yet — anchor text is authoritative). Findings left open, small: the Logs button loses
`/golive logs`'s `count`/`important_only` (same as every wave-1 panel; a modal if wanted back); the
four earlier `*_panel_minutes` keys (event/poll/birthday/request) still lack `labels.js` /
`site/mock/server.mjs` labels (🔧 in `TODO.md`). Review link: `/golive` in `#mute-me-bot-test-spam`.

## 2026-09-03 — The request card is the Discord record of a move (v69, `5a97a19`)

Release **v69** (`5a97a19`, 17:14; `deploys.log` line 68). Built in the main loop — one flag
through three files. Verified: boot clean (00:13:53Z database ready / synced 42 / 00:13:57Z
logged in). NOT verified: no request moved in Discord after the deploy — the proof is accepting
one in `#mute-me-bot-test-spam` and seeing the card alone. The item, whole:

- 🆕 **The request card is the official Discord close format, not the raw `request.done`
  box (owner, 2026-09-03 ~17:00, with a screenshot of `#mute-me-bot-test-spam`: "I don't want
  the request.done part in discord I want the other box as the official close format").**
  Diagnosis: the raw box is the action-log mirror (`log_channel_id`, `request_log_level`
  default `important`, `request.done` in `IMPORTANT`); the green card is the request's own
  status post (`notify_move` → `request_status_channel_id`/`request_notify_channel_id`). Both
  were pointed at the test channel, so every move showed twice. Design: `log_action(...,
  carded=True)` skips the raw embed at `important` when the caller is posting its own card
  (`requests.card_will_post` = move enabled in `request_channel_moves` AND a status channel
  set); the DB row and the Logs page are untouched; `request_log_level = all` still restores
  the raw line beside the card (configurable both ways, checklist 33); `notify=True` still
  outranks it. Status: **BUILT in the main loop ~17:10** (Fable, small) — `logkinds.should_post`,
  `actionlog.log_action`, `requests.card_will_post`, the cog's `apply_decision` /
  `resume_request` / `ask_check`; +6 tests (3750); **SHIPPED v69 `5a97a19` 17:14**.

## 2026-09-03 — Memory panel: `/memory` is one window (wave 2, v68, `cb941d9`)

Release **v68** (`cb941d9`, 16:48; `deploys.log` line 67). Merge `--no-ff` of
`worktree-agent-aaaa13e778f0ba65a` (Opus build, **329k** against a 120–180k estimate — wave-2 builds
run ~2× their estimate; five commits off `8cbe453`) as `cb941d9` after Fable review — no blocking
defect. `/memory` is a single command opening an ephemeral panel: every fact numbered (`Fact` layer in
`chat_memory.py`: name, notes, threads, DM-learned lines marked), a `Forget one of these…` select
capped at 25 that re-reads the line by text before dropping it (a distillation can land between render
and click → `PROFILE_MOVED`, nothing wrong is ever dropped), `Forget by words…` modal only above the
cap, `Forget everything` and `Stop remembering me` behind an Are-you-sure, `Remember me again`,
`Refresh`. Moves come from the fact count, never the consent, so the forget controls work with
`chat_memory_mode` off — **fork I-M1 = OPEN IT** (owner 16:12), the `HIDDEN_WHEN_OFF` entry for
`memory` removed. The web Forget now routes through the cog's `forget_profile(via=)` so both doors are
one write + one log row (checklist 34; the route's hand-built `web.` kind is gone and the logkinds AST
guard now asserts zero unchecked computed kinds). `db_up` moved from `applications.py` into
`panels.py` (checklist 17). One key `memory_panel_minutes` (default 10, checklist 33; labels.js
entry). Every re-render carries `allowed_mentions=none()`. 3710 → **3744 tests**, ruff clean, `commands
synced` 42 (the group was already one slot). Design
[`info/memory-panel-design.md`](info/memory-panel-design.md) (fifteen deviations at its foot); sweep
rows 104–108 (`access/sweeps.md`); `OWNER_GUIDE.md` sweeps count corrected 95 → 108 (two builds
stale). Verified: boot log 23:47:54Z database ready, 23:47:55Z synced 42 app commands, 23:47:58Z logged in, no Traceback. **NOT verified:** nothing opened in Discord — the five sweep rows
are the owner's; `chat_memory_mode` is off live so 104–107 need it on plus a conversation first.
Findings left for the next touch of each file: `api/tools/chat_memory.py` `CONTENTS_ARE_PRIVATE` and
its mock copy still name `/settings set chat_memory_staff_view full` (a subcommand that takes a
channel); four wave-1 `_panel_minutes` keys still lack a `labels.js` entry; five wave-1 panels edit
without `allowed_mentions`.

## 2026-09-03 — Operator read token: the session's read-only door (v67, `285b5e3`)

Release **v67** (`285b5e3`, 16:04; `deploys.log` line 66). Merge `--no-ff` of
`worktree-agent-aa960a4c8635193e0` (Opus build, 268k, four commits off `c790efb`) after Fable review —
no blocking defect: `operator_session` runs before the cookie path and returns `None` when no bearer is
offered or none is configured (an unconfigured server is byte-for-byte today's behaviour, verified live
by the builder: `/health` + a bearer answered `not_signed_in`); `hmac.compare_digest` on the token; a
dedicated 30/min bucket per client IP consumed on every bearer request; GET/HEAD only, anything else
`403 operator_read_only` in words; one `web.operator.read` Core row per request guarded by
`request.state.operator_noted` (checklist 34) and switchable by `operator_read_log` (bool, default true,
`CORE_KEYS` 5 → 6, registry 162 → 163 — checklist 33); the identity is `{"id": "0", "name": "operator",
"staff": True, "member": False}` so `/api/requests/mine` is deliberately unreadable. Third Via word
**Operator token** (`VIA_WORDS`, a Logs-page pill). `scripts/read.ps1 -Path /api/…` is the one command a
session reads live state with (env var, falling back to the HKCU User variable so a long-running parent
shell sees a fresh mint). 3697 → **3710 tests**, ruff clean; `commands synced` 42 unchanged. Design
[`info/operator-read-design.md`](info/operator-read-design.md) (six deviations at its foot), access
[`access/operator-read.md`](access/operator-read.md); sweep row 103; `RECOVERY.md` names the secret.
The builder's GET-route audit: no `current_session` GET writes; the two OAuth GETs never see the bearer.
Verified: boot log 23:04:42Z database ready + synced 42, 23:04:46Z logged in, no Traceback. **NOT
verified / NOT done: the secret is not set.** The owner approved the blind mint 16:00 ("Yes"); the
permission classifier blocked the command at 16:15, so the mint moved back to `TODO.md` as owed. The
door does not exist live until `OPERATOR_READ_TOKEN` is set AND the next deploy runs (`--stage`).

The item as it stood on `TODO.md`, moved whole:

> 🆕 **Operator read access for the session (owner, 2026-09-03 14:24: "Make apis that you can
> access so you can see things. Or use my explicit permission to check it").** Today a live
> read means `flyctl ssh console` + SQLite, which the permission classifier blocks about half
> the time. Proposed (awaiting owner yes/no): one `OPERATOR_READ_TOKEN` (Fly secret, name only
> here) accepted as a bearer on GET-only `/api/*` — the same JSON the dashboard reads, no new
> endpoints, no writes; every use logged with Via: operator; rate-limited like a session.
> ~40k Opus build. Interim: the owner's explicit permission in chat, then retry the `flyctl ssh`
> read. **DECIDED YES (owner, 2026-09-03 15:07: "Yes do it") — build DISPATCHED 15:10** (Opus,
> own worktree; design in the brief → `info/operator-read-design.md`; access doc
> `access/operator-read.md`; the token is minted and set by the owner, never seen by a session).

## 2026-09-03 — Panels wave 1 COMPLETE, fourth landing: `/apply` is one command (v66, `853776c`)

Release **v66** (`853776c`, 15:00; `deploys.log` line 65). Merge `--no-ff` of
`worktree-agent-abf063b9177e02f17` (Opus build, 401k, nine commits) after Fable review — no blocking
defect: every staff move `still_staff` → defer → `db_ready`, member moves and Back buttons re-render
against the actor, the persistent card buttons still pass `may_decide`, one log row per write
asserted by count. Two doc conflicts (`OWNER_GUIDE.md`, the design header), both sides kept;
**3697 tests** green under `-n auto`; `commands synced` **43 → 42** on the boot log — the Group
drop §B predicted. All three owner forks built as decided: **I-A1 `/apply`** ("gamer lingo",
13:35), **I-A2 Visible** (`HIDDEN_WHEN_OFF["applications_mode"]` gone, the off-panel says so in
words, 13:47), **I-A3 the Questions sub-panel** (select → Edit / Remove, plus Add; reorder stays
on the site, 14:12). Both the `apply` and `applications` groups and their seventeen subcommands
are gone; `denied` / `removed` gained the `Approve after all` / `Put them back on the list` exit
(staff final say). Design: [`info/applications-panel-design.md`](info/applications-panel-design.md)
(15 deviations at its foot — headline: `update_form` clears four id columns from the `NO_ROLE`
sentinel, a `db_up` gate for reads before a defer). Sweep rows 94–102; rows 53–57 and 69–72
rewritten. Keys `applications_panel_minutes` / `applications_panel_own_list`. Site: two label
strings on https://blackbloc.heygabi.ai/rolemenus.html#applications. Verified: boot log 22:00:05Z
database ready + synced 42, 22:00:08Z logged in, no Traceback. NOT verified: nothing by eye in
Discord; the empty-select submit edge (§C) is still unverified on every panel that has one.

**Wave 1 is complete** — `/birthday` v63, `/event` v64, `/poll` v65, `/apply` v66, all in one
afternoon (13:58–15:00), 44 → 42 commands, 3442 → 3697 tests. The panels program item stays on
`TODO.md` for waves 2–4 (`info/panels-program.md` §5). Filed request #2 (Twitch Team form via the
bot) is what this landing delivers; it sits in *review* on the Requests page for the owner to mark
done.

## 2026-09-03 — Panels wave 1, third landing: `/poll` is one command (v65, `d13e1a4`)

Release **v65** (`d13e1a4`, 14:14; `deploys.log` line 64). LANDING entry — the panels item stays
on `TODO.md` until applications lands. Merge `--no-ff` `27452ac` of `worktree-agent-aa735ab092d13477d`
(Opus build, 458k). Four conflicts against the events landing (`settings_store.py`, `sweeps.md`,
`info/README.md`, `code-notes.md`), every one resolved by keeping both sides; 3644 tests green
under `-n auto`. Fable review at pattern level found no blocking defect (`still_staff` 9 sites,
defer 15, `db_ready` 10, `retire` 5, `allowed_mentions` 11, `log_action` 30; the `LATER_KINDS`
deviation is not a regression). Notes on `TODO.md`: `draft` status is never written, no
create-recurrence web route. What shipped: `/poll` opens one panel (Create · Find # · Refresh, plus
Settings · Logs for staff); create is a two-step modal → preview, nothing written until **Post it**;
picking a poll IS the results card with End / Cancel / Approve / Deny rendered only when valid;
a denied poll keeps **Post it anyway** (staff final say); recurrence cards run the same code as the
dashboard. `commands synced` **43 unchanged** (`/poll` was already one slot). Design:
[`info/polls-panel-design.md`](info/polls-panel-design.md) (9 deviations at its foot). Sweep rows
80–86 (rows 6, 8, 9, 27 rewritten). Keys `poll_panel_minutes` / `poll_creator_may_end` on
https://blackbloc.heygabi.ai/settings.html. Verified: boot log 21:14:17Z database ready, 21:14:18Z
synced 43 app commands, 21:14:23Z logged in, no Traceback/Error. NOT verified: nothing by eye in
Discord or on polls.html.

## 2026-09-03 — Panels wave 1, second landing: `/event` is one command, `/timezone` retired (v64, `e670542`)

Release **v64** (`e670542`, 14:05; `deploys.log` line 63). LANDING entry — the panels item stays
on `TODO.md` until polls and applications land. Merge `--no-ff` of `worktree-agent-a448c7ab780ed3c2b`
(= `feat/events-panel`; Opus build, 433k). Six merge conflicts against the birthdays landing
(`settings_store.py`, `tests/test_bot.py`, `OWNER_GUIDE.md`, `sweeps.md`, `architecture.md`,
`code-notes.md`), every one resolved by keeping both branches' blocks; 3560 tests green under
`-n auto` before the commit. Fable review found no blocking defect — the one note: the
`confirm_cancel` Yes button trusts the panel's opener pin instead of re-running `may_cancel`
(on `TODO.md`). What shipped: `/event` opens the member panel (Propose, `My time zone` modal,
`Call one off…`) or the staff panel; the whole `/timezone` group is gone, the program's first
real `commands synced` drop (44 → 43); the shared layer moved to `black_bloc/events.py`
(`apply_decision`, `cancel_for` — which now also renames the review channel — `card_buttons`,
`option_label`, `list_lines`). Design: [`info/events-panel-design.md`](info/events-panel-design.md).
Sweep rows 73–79. Keys `event_panel_minutes` / `event_panel_own_list` on
https://blackbloc.heygabi.ai/settings.html. Verified: boot log 21:05:00Z database ready,
21:05:01Z synced 43 app commands, 21:05:04Z logged in, no Traceback/Error. NOT verified: nothing
by eye in Discord or on events.html.

## 2026-09-03 — Panels wave 1, first landing: `/birthday` is one command (v63, `616adb3`)

Release **v63** (`616adb3`, 13:58; `deploys.log` line 62). This is a LANDING entry, not a
move — the panels item stays on `TODO.md` until events, polls and applications have landed
too. Merge `--no-ff` `58974e1` of `worktree-agent-a19bdce15408f8243` (Opus build, 412k; Fable
review found no defect: `still_staff` before every `defer()`, `db_ready` after, `retire(previous)`
on every re-render, `allowed_mentions=none()` on every send, one `log_action` per write with the
kinds unchanged, `DateModal` reads its prefill before acknowledging so the modal can follow).
Design: [`info/birthdays-panel-design.md`](info/birthdays-panel-design.md) (14 deviations at its
foot). Sweep rows 87–93. Keys `birthday_panel_minutes` / `birthday_panel_next_for_members` /
`birthday_panel_lookup` on https://blackbloc.heygabi.ai/settings.html.

**The gate refused the first attempt (13:52)** on
`tests/api/test_settings_api.py::test_writes_are_rate_limited_per_session` — the wall-clock flake
both wave-1 build agents had reported: `TokenBucket` refills one token a second, so sixty PUTs
that take over a second under `-n auto` let the sixty-first through. Fixed in `616adb3` by
stubbing `auth.time` to one instant for that test (`code-notes.md` →
`tests/api/test_settings_api.py:221`); three consecutive whole-suite runs green before the redeploy.
Verified: boot log 20:58:15Z database ready, 20:58:16Z synced 44 app commands, 20:58:20Z logged
in, no Traceback/Error. NOT verified: nothing by eye in Discord or on settings.html.

## 2026-09-03 — Applications without a role: keep a list instead (v62, `9891f71`, schema 28)

Release **v62** (`9891f71`, 12:48; `deploys.log` line 61). Merge `--no-ff` of `feat/applications-no-role` after `feat/requests-check` (`SCHEMA_VERSION` 27 → 28 resolved at the merge); Fable review found no defect and reworded `REMOVE_IS_FOR_LISTS` (a `/role revoke` ends the grant, the approval stays on record — nothing in the revoke path touches `applications`). 3442 tests, ruff clean. Boot log 19:47:59Z: `rebuilding application_forms so a form may have no role` (the C1 rebuild ran on the live DB), logged in 19:48:03Z, no errors. ⚠️ NOT verified by eye: owner sweeps 69–72. The 🔧 item moved here whole:

- 🆕 **Applications without a role — "let's have the bot store the info!" (owner, 2026-09-03
  ~12:10, relaying a member's Discord question verbatim: "is there a way for the twitch team
  app to be done without a role? if not we may wanna think of adding a stream team role (which
  might just be a good reference point to see who's applied and who would need to show up on
  the team page)" → owner: "we can do no role and have the bot store the information or … a
  temporary role … let's have the bot store the info! that way we can check the site and the
  official team page").** Measured at `46e3ba4`: **not possible today** —
  `application_forms.role_id` is `NOT NULL` (`storage/db.py:576`), `/applications create`
  takes `role: discord.Role` as a required option (`cogs/community/applications.py:877`), and
  `_hand_over` (`:461`) always grants. The applications themselves ARE already stored
  (`applications` table: answers, status, who decided, when), so the roster exists in the DB
  today — what is missing is (1) a form that grants nothing, (2) a roster on the site to
  compare with the official Twitch team page. Design: `info/applications-no-role-design.md`
  — role optional on create/edit (slash AND dashboard editor, checklist 33), schema **28**
  makes `role_id` nullable (SQLite table rebuild, the `mod_cases` precedent at
  `db.py:660–664`), approve on a role-less form skips `_hand_over` and the "hand it over with
  `/role grant`" fallbacks and DMs `approved_text` + `next_step` as today, an **Approved
  roster** per form in the Applications section of the Role menus page (name · approved when
  · Twitch login from `golive_links` when linked, so it reads against twitch.tv/team/…) with
  a plain-text copy. Status: **BUILDABLE** (2026-09-03 ~12:20) —
  [`info/applications-no-role-design.md`](info/applications-no-role-design.md) written: role
  optional per form (slash `role`/`no_role` on edit + the dashboard editor's "No role — keep a
  list"); roster = approved applications, one home; new terminal status `removed` with a DM'd
  reason (the only way off a no-role list — D2); `GET /api/applications/roster`, `POST
  /{id}/remove`, roster foldout per form with Twitch login + Copy as text; one setting
  `applications_roster_shows_left` (default true). ⚠️ Gotcha caught in design: the table
  rebuild must run BEFORE `PRAGMA foreign_keys=ON` or `DROP TABLE application_forms`
  cascade-deletes every question (§C1). Different cog from the "ask them to check" item, so
  the two builds can run beside each other; both bump `SCHEMA_VERSION` — second to merge
  re-keys. Owner answered the one question 2026-09-03 ~12:30: **"Always give staff final say
  and permission"** — staff removal stays in, and the sentence is now a `CLAUDE.md` rule.
  Then "Build all, keep going" → Opus build dispatched on `feat/applications-no-role`
  (2026-09-03 ~12:35), beside `feat/requests-check` — which merged first (`44170f4`, v61,
  schema 27). **BUILT** on that branch (2026-09-03,
  four commits, `SCHEMA_VERSION` 28): 3414 tests pass, ruff clean, `check.mjs` 17 pages /
  141 routes; five deviations at the foot of the design doc. ⚠️ **NOT merged, NOT deployed,
  and not exercised against Discord or the live site** — `access/sweeps.md` rows **69–72**
  are the owner's by-eye checks. Still open: merge (whichever of the two branches lands
  second re-keys `SCHEMA_VERSION` and `code-notes.md`), deploy, then the sweep. This item
  moves whole to `DONE.md` when it is live, not before.

**SHIPPED** 2026-09-03 12:48 in v62. Design: [`info/applications-no-role-design.md`](info/applications-no-role-design.md) (five build deviations at its foot). Review link: https://blackbloc.heygabi.ai/rolemenus.html#applications

## 2026-09-03 — Requests sixth pass: "Ask them to check" (v61, `44170f4`)

Release **v61** (`44170f4`, 12:29; `deploys.log` line 60). The 🔧 item moved here whole:

- 🆕 **"We also need a way to ping the requester from the request app. I want to have it
  message the requesters to check the work." (owner, 2026-09-03 11:15).** A staff move on the
  request card (panel AND the site's request card — one shared function, one log row) that
  tells the person who asked that the work is ready for THEM to try: a DM built from the same
  `request_embed` (built + how-to-test filled in) with a sentence asking them to check it and
  say so, falling back to a mention in the request channel when their DMs are closed. Which
  states offer it, whether it is its own state or a flag on `review`, and the fallback are
  design calls — the owner said "Keep building", so no fork went to him. Status:
  **BUILDABLE** (2026-09-03 ~12:05) — [`info/requests-check-design.md`](info/requests-check-design.md)
  written: an ACTION on the review card, not a state (§B); `check_asked` look + DM, channel
  ping fallback (`request_check_fallback_channel`, default on), `request_check_on_ready`
  (default off), schema 27, `POST /api/requests/{id}/check`; six owner-flippable calls in §D.
  Owner 2026-09-03 ~12:30: "Build all, keep going" → Opus build dispatched on
  `feat/requests-check` from `main` ≥ `fbb1191` (~12:35), beside `feat/applications-no-role`.
  Status: **BUILT, not merged, not deployed** (2026-09-03, branch `feat/requests-check`, four
  commits) — `ask_check` shared by the panel button and `POST /api/requests/{id}/check`, the
  `check_asked` card, the channel-ping fallback, both settings, schema 27, 28 new tests
  (3399 pass, ruff clean, mock 17 pages / **140** routes). Owner checks are sweeps
  [66–68](access/sweeps.md). ⚠️ Both this branch and `feat/applications-no-role` bump
  `SCHEMA_VERSION` to 27 — whichever merges second re-keys to 28. Nothing here has been seen
  in live Discord or on the deployed site.
  **SHIPPED** (2026-09-03 12:29, v61 `44170f4`): merged first, so this one kept schema **27**
  and the applications build already carries 28. Fable review found one defect — `moment()`
  stamped the DM'd check card with `decided_at` (the ready time) instead of `check_asked_at` —
  fixed at the merge with a column map and a test line. 3399 tests in the gate, release 15 s
  after exit, boot log 19:29Z clean (synced 44 commands). By eye NOT done: sweeps 66–68 are the
  owner's.

## 2026-09-03 — Panels wave 0 (`black_bloc/panels.py`) and the deploy gate that fits inside a tool call

Landed together in release **v60** (`46e3ba4`, 11:39; `deploys.log` line 59). Three things,
two of them 🔧 items moved here whole below.

**Wave 0 of the panels program** (`info/panels-program.md` §4): `black_bloc/panels.py` extracted
from the requests cog so the three fourth-pass review defects (a replaced view never stopped;
`on_timeout` editing through a stale token; staff not re-checked before a move) live in ONE
place before seventeen panels inherit them. `Panel(AnswersErrors, discord.ui.View)` with
`interaction_check`, `on_timeout` guarded by `self.replaced`, the `went_quiet` footer;
`NoteModal` storing its callback as `takes_note` (NOT `on_submit`, which would shadow
`Modal.on_submit`); `answer`, `still_staff`, `retire`, `db_ready`, `capped_placeholder`,
`panel_minutes(store, guild_id, key)`. The requests cog re-based on it — `RequestView(Panel)`,
`NoteModal(PanelNoteModal)` — behaviour identical, 163 requests tests unchanged, 26 new in
`tests/test_panels.py`. Built by Opus on `feat/panels-library` in a worktree (160k / 20 min),
Fable-reviewed (no defect; five deviations from the brief all accepted), merged `1861923`
~11:50. `code-notes.md` third- and fourth-pass sections re-keyed by ANCHOR at the merge, seven
rows now pointing into `panels.py` with "was … until wave 0" notes.

- 🆕 **"Let's fix that" (owner, 2026-09-03 ~11:25) — `scripts/deploy.ps1` outruns the
  10-minute tool ceiling.** Measured the same morning: pytest alone took **8:27** for 3345
  tests (single process on a 32-core machine), so the wrapper was killed during the image
  build and the orphaned `flyctl deploy` hung at "Waiting for depot builder" with a dead
  stdout pipe; no release was made. Fix in two halves: (1) **`pytest-xdist`** in the dev
  extras and `-n auto` in `deploy.ps1` — the tests are SQLite-per-`tmp_path`, so they should
  parallelise; measure the wall time and that the count is still 3345; (2) a
  `docs/access/deploy.md` gotcha titled for the symptom ("the deploy printed nothing after
  Waiting for depot builder") saying to run the script detached (`Start-Process … -PassThru`)
  and watch the pid, never inside a tool call with a ceiling. Status: **BUILT, awaiting the
  deploy that proves it** (2026-09-03 ~11:55) — (2) landed in `06ace58`'s neighbour that
  morning; (1) measured: `-n auto` on the 32-logical-core machine runs **3371 tests in 54 s**
  (was 8:27 for 3345), count holds; `pytest-xdist>=3.6` in the dev extras, `-n auto` in
  `deploy.ps1`. Moves to DONE when a deploy has run through the new gate.
  **→ PROVED 11:39: the v60 deploy ran the whole script in 2:50 wall (pytest 1:22 inside the
  gate beside the image build), still launched detached per the gotcha.**

- 🆕 **A defect this build found and fixed on the way, worth knowing about
  separately: `site/public/assets/labels.js` had not parsed since `7b1c592`**, so
  `LABELS` never loaded and **every dashboard page rendered blank**. The Phase 19 merge
  pasted the applications labels after the `LABELS` object's closing brace. Fixed on
  `feat/requests-third-pass` as its own commit (`1d7d84d`), shipped in the third-pass
  deploy 2026-09-03. ⚠️ **Nothing in the test suite reads `labels.js`.** Measured
  2026-09-03 06:40: `node --check site/public/assets/labels.js` **PASSES the broken
  file** — a `.js` path is parsed as CommonJS, where the stray `key: 'value'` lines are
  legal labels; the browser loads it as an ES module and dies at `labels.js:160
  SyntaxError: Unexpected token ':'`. The guard that catches it is the module parse:
  copy to `.mjs` and `node --check` that, or `node --input-type=module --check <
  labels.js`. Add it to `deploy.ps1` beside ruff, pytest and `check.mjs` — for EVERY
  `site/public/assets/*.js` (they are all modules). Small, own commit; not done in the
  build because it is a deploy-pipeline change and the build had no brief for one.
  **BUILT 2026-09-03 ~11:50**: `deploy.ps1` now runs `node --input-type=module --check <
  file` over every asset after pytest; proved on a scratch file with the Phase 19 shape
  (module parse exit 1, plain `--check` exit 0) and clean on all 29 current assets. Moves
  to DONE with the "Let's fix that" item once a deploy has run through the gate.
  **→ the v60 gate ran it over all 29 assets, green.** Gotcha for the next person: piping
  `node --check` into `findstr` masks the exit code (shows 0) — redirect to `>nul 2>&1`
  when proving a guard by hand.

## 2026-09-03 — Requests, fifth pass: the panel's own list is staff-only; the done card stops posting

Two owner orders minutes after the fourth pass deployed (`ba5cb99`, 10:04), both moved here
whole (the items are reproduced below). **Both were already settings or became one**, so
each goes back the other way from the Settings page or `/settings set-value` (checklist 33).

**1. "We need to make the view request thing staff only" (~10:10).** One clarifying
question; the owner picked "Viewing requests on the panel". Members keep `File a request`
and `Take one back…` (the withdraw select is still built from their own rows), but the
embed no longer lists their own requests unless the new **`request_panel_own_list`**
(bool, default **off**) is on; staff see their own list whatever the key says. Opus built
it on `feat/requests-panel-own-list` (`dd7c788` code, `bda45da` docs) — gate at
`cogs/community/requests.py:511` `if staff or panel_shows_own_list(store, guild.id):`,
helper `requests.py:477`, registry `settings_store.py:877/898/1307`; no wording was added
for the hidden list (the intro still reads honestly; deviation 12 in
`info/requests-panel-design.md` says why). Three existing tests asserted the overturned
behaviour and were rewritten to turn the key on. The build also corrected sweep rows 14–15
(not 58–64 as the brief guessed), added row 65, and fixed two stale doc lines it was already
editing (OWNER_GUIDE's "42 rows", feature-list F18 "not yet merged"). Merge **`c4420cc`**.
Cost: 152k Opus tokens, 18 minutes.

**2. "Let's suppress the request.done box in discord, it's redundant information. This
should be in website logs only" (~10:17).** Located in a few greps: the done card was
already gated by `request_channel_moves` (`requests.py:521` `posts_a_card`, third pass) and
the live DB held **no** stored `request_*` row (measured over `flyctl ssh`), so the whole
fix is the DEFAULT: `REQUEST_CARD_DEFAULT` = every move but `done` (`settings_store.py:870`,
`:1302`); the choices still list all seven so `done` can be ticked back on — a single edited
tuple would have made the Settings checkbox and `/settings set-value` REFUSE it. The
requester's DM on done is untouched (it goes to the asker, not the channel). Done on `main`
after the merge by the conductor (a default flip, not a build), shipped in the same deploy.
Deviation 15 in `info/requests-embeds-design.md`; sweep row 62 amended.

**Proof:** ruff clean; 3345 tests on the branch, the full suite re-run by `deploy.ps1`
(`deploys.log` has the count); `check.mjs` 17 pages / 139 routes, site untouched.
⚠️ **NOT verified by eye in Discord** — no panel opened, no Accept pressed. The owner's sweep
is rows 14–15 (member sees no list), 62 (Accept posts no channel card), 65 (the key puts
the list back).

**The TODO items, whole:**

- 🆕 **"We need to make the view request thing staff only" (owner, 2026-09-03 ~10:10, minutes
  after the panel deploy `ba5cb99`).** Clarified ~10:12 — the owner picked "Viewing requests
  on the panel": members keep `File a request` and `Take one back…`, but the list of their
  own requests in the panel embed becomes staff-only (staff see everything as now). The
  site's request reads were already staff-only (`api/writes.py:126` `reader_dependency`
  wraps `staff_dependency`; only `/mine` is a member route). Per checklist 33 the gate is a
  setting, **`request_panel_own_list`** (bool, default **off**), so the Settings page and
  `/settings set-value` can put the list back. Build: Opus, branch
  `feat/requests-panel-own-list`, worktree `.claude/worktrees/agent-own-list`; the brief
  also asks for design-doc deviation 12, code-notes rows, OWNER_GUIDE / feature-list /
  sweeps corrections. Status: **BUILDING** (dispatched 10:15) → landed, see below.

- 🆕 **"Let's suppress the request.done box in discord, it's redundant information. This
  should be in website logs only" (owner, 2026-09-03 ~10:17).** The done card the bot posts
  to Discord when a request is accepted duplicates the website log row. Locating the poster
  and confirming which message is meant; configurable both ways (checklist 33) — a setting
  that defaults to off, so the card can come back. Status: **LOCATING** → located and landed, see below.

## 2026-09-03 — Requests, fourth pass: `/request` is ONE command that opens a panel

Moved whole from `TODO.md` (the item is reproduced below the summary). Owner's ask ~06:50
("The flow seems tough, and request set and request ready seem overlapping"), then the
standing direction ~06:55 ("minimize slash commands and maximize interactive windows …
Request first") — now a `CLAUDE.md` rule and the pattern for every later feature. Design:
[`info/requests-panel-design.md`](info/requests-panel-design.md) (11 deviations — 9–11 are
the reviewer's findings). **Sonnet 5 built it** on `feat/requests-panel` (`7b4d120`,
`4743b01`, `39dfe17`) after Opus returned 529 Overloaded four times (07:44–08:35, nothing
written each time); Fable reviewed; **Opus fixed the three findings** (`79548c1`,
`7aaf24a`); merge **`ba5cb99`**, deployed the same commit — see `deploys.log`.

**What shipped.** `/request` is a single command, no subcommands: one ephemeral message,
an embed plus a `discord.ui.View`. Members see their own requests, `File a request` (the
existing modal — hidden, with a line saying why, when filing is staff-only or requests are
off), `Refresh`, `Open on the site`, and a "Take one back…" select with a Yes/Keep confirm.
Staff additionally see a counts line, a "Pick a request…" select over the open statuses
(capped at 25, placeholder "25 of N — the rest are on the site"), and `Logs`. Picking a
request renders the card — the SAME `request_embed` the channel and DMs get — with ONLY
the moves valid from its state as buttons (open: Pick up / Hold / Decline; in progress:
Ready to check / Hold / Decline; ready to check: Accept (only when `may_accept`) / Send
back / Hold / Decline; on hold: Resume / Decline; final states: none, the footer says so)
plus `Back`. Every move calls the shared function that already existed (`apply_decision`,
`mark_ready`, `accept`, `send_back`, `resume_request`), `via` at its Discord default —
the panel never writes a row or a log line itself. `withdraw_request` was extracted so the
panel's confirm and the site's withdraw route are one implementation with one log row
(`kind_via`). New setting `request_panel_minutes` (int, default **10**). `commands synced`
stays **44** — a `Group` was already one top-level slot (deviation 7 corrected the design's
"drops by nine"). 3338 tests, ruff clean, `check.mjs` 17 pages / 139 routes.

**Review findings, all fixed before merge (verified against the installed discord.py, not
reasoned).** F1: `ViewStore.add_view` (`ui/view.py:940–968`) overwrites the message's view
without stopping the old one, so a replaced panel's timeout would later overwrite the live
card with a disabled stale one — now `retire()` stops the previous view before every
replacing edit. F2: the "gone quiet" footer could not be written at the old default of 15
minutes (an `InteractionMessage` token dies at 15, and non-rendering clicks refresh the
timeout without refreshing the token) — buttons would have died silently; now `on_timeout`
edits through the freshest interaction's token, the default is 10, and the help text says
15+ loses the footer (KI-20 names it). F3: the ten subcommands called `require_staff` on
every call, the panel only at render — `still_staff` now re-asks before every move and
modal submit. The build's deviation 2 ("only the last view reaches on_timeout") was wrong
and is marked superseded. The reviewer's own suggested guard (`is_finished()` in
`on_timeout`) was also wrong — `_dispatch_timeout` marks the view finished BEFORE calling
`on_timeout` — the fix agent measured it and used an explicit `replaced` flag instead.

⚠️ **NOT verified:** anything by eye in Discord — no panel has been opened live. The
owner's sweep is `access/sweeps.md` rows 58–64: `/request` in `#mute-me-bot-test-spam`,
pick #1, Accept — that posts the first done card.

**The TODO item, whole:**

- 🆕 **Simplify the request slash flow — owner, 2026-09-03 ~06:50, verbatim: "The flow
  seems tough, and request set and request ready seem overlapping."** Measured: after the
  third pass `/request` has TEN subcommands and two ways to make most moves —
  `set status:review` vs `ready`, `set status:done` vs `accept`, `set status:hold` vs
  `hold`, `set status:in_progress` (from review) vs `sendback` (`cogs/community/requests.py:631–778`,
  `STAFF_STATUSES` is every reachable status). Proposal put to the owner: ONE mover,
  `/request set`, with `review` opening the built/how-to-test modal, `done` from review =
  accept, `in_progress` from review requiring the note (= send back); delete `ready`,
  `accept`, `sendback`, `hold`, `resume`. Site buttons unchanged. **Owner ~06:55, going
  further:** *"Let's also have /request open a menu maybe. Let's try and minimize slash
  commands and maximize interactive windows"* → *"Let's start this process with request
  then carry it through the rest of the app. Request first."* Decided: `/request` becomes
  ONE command that opens an ephemeral panel (embed + buttons + selects + modals); the nine
  subcommands go. Design → [`info/requests-panel-design.md`](info/requests-panel-design.md);
  rule added to `CLAUDE.md`. Status: **BUILDING** (Opus, `feat/requests-panel`, cut from
  `3e18e4a`), 2026-09-03 ~07:05.

## 2026-09-03 — Requests, third pass: the review state, the embeds and the site link

Moved whole from `TODO.md` (the item is reproduced below the summary). Owner's ask
~00:50, two decisions ~01:00 (the `review` state; "Yes, build it that way"), the data
order ~03:55 ("Move the 2 done ones to ready to check, leave the other as hold"). Opus
build on `feat/requests-third-pass` (12 commits, `2fac43b` … `c6064f9`), merge
**`355d6e9`**, conductor's post-merge anchor fix **`70a6720`**, deployed **`70a6720`**
2026-09-03 06:34 — see `deploys.log`. Design and its 14 deviations:
[`info/requests-embeds-design.md`](info/requests-embeds-design.md).

**What shipped.** The state machine grows `review` ("ready to check"):
`open → in_progress → review → done`, `done` reachable ONLY from `review`, `built`
required to enter it, Accept moves it to `done`, Send back (note required) returns it to
`in_progress` — a LOOK, not a state, remembered in `sent_back_reason`. `hold` / `declined`
stay side states. Every request notification is ONE embed builder (`request_embed`, seven
looks) used by the channel line and the requester DM, with a link button to
`{origin}/requests.html#r-N`. Schema 26: `requests.built` / `how_to_test` / `ready_by` /
`sent_back_reason`, nullable, no backfill. Settings: `request_channel_moves` (a new
`enums` registry type — which moves post to the channel) and `request_review_by_other`
(default off — the accepter need not differ from the person who marked it ready).
Routes `POST /api/requests/{id}/ready|accept|sendback`, slash `/request
ready|accept|sendback`, log kinds `request.review` / `request.sent_back` (IMPORTANT),
one row per web write through `kind_via` (checklist 34). Requests page: a Ready-to-check
section with editors for built / how-to-test, per-card `#r-N` anchors that open the
section they land in. 3310 tests, ruff clean, `check.mjs` 17 pages / 139 routes.

**Found on the way.** `site/public/assets/labels.js` had not parsed since the Phase 19
merge `7b1c592` — every dashboard page rendered BLANK from 00:31 to 06:34. Fixed in
`1d7d84d`; the guard that would have caught it is an open TODO item (the module parse,
not `node --check`). And the design's own link, `/requests#r-N`, 404s on the static
mount — deviation 14, `REQUEST_ANCHOR` now takes the page from `logkinds.FEATURE_PAGES`.

**Landing data step, run 06:41 against the live volume:** #1 and #2 `done → review`
(`ready_by` = the staffer who had marked them done, `done_at` null, `built` = the old
decision note, `how_to_test` = the sweep rows 48–52 / 53–57); #3 untouched, `hold`.
Verified on https://blackbloc.heygabi.ai/requests.html: Ready to check 2, On hold 1,
Done 0, no console errors. ⚠️ **NOT verified:** any card by eye in Discord — the one-off
posts nothing; the first real staff move (an Accept on #1, say) posts the first card to
`#mute-me-bot-test-spam`. The slash paths and the DM look are on the sweep list.

**The TODO item, whole:**

- 🆕 **Request notifications as embeds, with "what was built" + "how to test" + a site
  link — owner, 2026-09-03 ~00:50, verbatim: "We probably should also add how to test the
  feature and a short explanation of what was built too. Also let's get a standard
  appealing template for the output. Maybe use one of the discord info boxes with a
  description, how to test if applicable, and a link to the request on the website. When
  someone makes a request we should also post that same request link in discord too. So a
  message at the start to confirm task is made and then once at the end when done. Also
  one for the in hold or declined states."** Today every request line is plain text
  (`black_bloc/requests.py:149–159` `NOTIFY_*`, `:132–147` `DM_*`) and no per-request URL
  exists (`page-requests.js` renders cards with no anchor). Design →
  [`info/requests-embeds-design.md`](info/requests-embeds-design.md). Touches the same
  files as the double-logging fix, which merged as `df393ab` (`DONE.md` 2026-09-03) —
  the build cuts from that or later and follows checklist item 34 (pass `via`, never
  a second `note()`). Owner decisions 2026-09-03 ~01:00: asked whether "what was built" is required
  on Done, he answered *"Do we need an acceptance pending so a staffer can check if
  something is done?"* → a **`review` ("ready to check") state**, `in_progress → review →
  done`, built + how-to-test required to enter review, Accept / Send back,
  `request_review_by_other` default off ("Yes, build it that way"). Owner ~03:55:
  *"Move the 2 done ones to ready to check, leave the other as hold"* → not possible
  until `review` exists (`done` is final today); recorded as the build's LANDING DATA
  STEP in the design (#1 and #2 `done → review` by a one-off on the live DB, #3 stays
  `hold`). Status: ⚠️ **BUILT on `feat/requests-third-pass`, 2026-09-03 — NOT merged,
  NOT deployed, and the landing data step NOT run.** 3260 tests pass, ruff clean,
  `check.mjs` 17 pages / 139 routes, and the page was rendered against the mock; nothing
  has been verified against live Discord or the live dashboard. What is left for the
  conductor, in order: **(1)** merge and deploy (schema 26 migrates on boot — four
  nullable columns, no backfill); **(2)** run the landing one-off in the design doc's
  `## Deviations` foot (#1 and #2 `done → review`, #3 untouched) — it is idempotent and
  was dry-run against a throwaway schema-26 file, but it must run AFTER the deploy;
  **(3)** post one card of each of the seven looks to `#mute-me-bot-test-spam` and judge
  "appealing" by eye — §J measured the shapes (worst look 2004 of Discord's 6000) but
  nobody has seen one rendered. Move this item WHOLE to `DONE.md` at landing.

## 2026-09-03 — One web write leaves one log row (owner bug report, the same night as the 17/18/19 landing)

Moved whole from `TODO.md`. Owner ~00:40, on seeing the three request flips in the
test channel: *"The app double posted all messages with a web.request and a request"*.
Root-caused in the main loop (AST survey, 8 route files), owner chose "All 8
features" over requests-only at ~00:43, Opus build in a worktree, merge **`df393ab`**
(branch `fix/web-write-double-log`: `5f7cc1e` code, `19d2f7d` docs), deployed the
same morning — see `deploys.log`.

**What was wrong.** A dashboard write went through a shared bot function that
already logged the event, and the route then `note()`d a `web.<kind>` line on top
of it. One click left TWO `action_log` rows and posted TWO embeds. `logkinds.bare()`
collapsed the pair for *classification*, so nothing ever noticed; it surfaced now
because `request.done/hold/declined` are IMPORTANT and post at the default level,
and tonight was the first real traffic through the site. Present in 8 route files —
requests, events, honeypot, mod, modmail, polls, rolemenus, tempvoice — across 20
shared functions; it pre-dated Phase 17 (`f7199a5` already had it).

**The fix.** One canonical `logkinds.kind_via(kind, via)` (`bare()` read backwards)
replaced SIX hand-built `f"{WEB}."` heads (`pings.head` deleted; `rolemenu_panels`,
`applications` ×2, `role_menus`, `tempvoice.panel_log`). Every shared function a
route calls takes keyword-only `via: str = VIA_DISCORD`, logs one row through
`kind_via`, and records `details["via"]`. Each route passes `via=VIA_WEBSITE` and
its redundant `note()` is gone. Slash commands take the default and are unaffected.
`note()` survives only where the route is the sole logger (`web.request.filed` /
`updated`, comments, withdraw, raid-train and role-menu CRUD); bot-emitted
consequences (`request.dm_failed`, `modmail.place_kept`) keep their bare kinds.
**Three survey hits were false positives and kept deliberately:** `rename_channel`
and `send_reply` log only failures, so `web.event.edited` and `web.modmail.reply`
are the route's own lines; `staff_assign` already took `via`.

**Consequences.** Where the shared kind differed from the note kind the web row now
carries the shared one (`web.event.cancelled`, `web.honeypot.banned`,
`web.mod.warned/timed_out/…`, `web.automod.rule`, `web.poll.closed`, …). Eight
now-unemitted `ROUTINE` entries were removed — the repo's own
`test_no_classification_entry_is_dead` required it; historical rows keep their
kinds and `honeypot.ban` old rows now read *important* — **KI-19**. Two rows move
page: automod rule changes and Apply-now now land on the Automod log, matching what
the Discord button already produced.

**Guarded so it cannot come back:** checklist item **34**, plus an AST walk in
`tests/test_logkinds.py` (`test_a_route_never_notes_an_event_its_shared_path_already_logged`)
that fails if a route both calls a shared logger and notes the same bare kind —
proven by re-introducing the defect, which failed by name — a "no second
head-builder" test, and a `via`-default test. `tests/api/conftest.py:one_web_row`
asserts exactly one `web.*` row per route write; the old tests asserted both kinds
were *present*, which is precisely what a double post looks like.

**Measured:** 3244 tests (was 3238), `ruff` clean, mock 17 pages / 136 routes; the
mock and `contract.json` emitted the old kind strings and were updated in the same
commit (`check.mjs` only tests emitted ⊆ listed, so a stale mock passes silently).
**NOT verified** by the build: anything against live Discord or the live dashboard.
**Still open:** `raidtrain.cancel_train` logs one row but labels a web cancel
Via = Discord — a Via-labelling gap, not a double post (on `TODO.md`).

The item as it stood on `TODO.md`:

- 🔴 **Every web write through a shared path logs TWICE — owner, 2026-09-03 ~00:40,
  verbatim: "The app double posted all messages with a web.request and a request".**
  Seen on the three request flips at the 17/18/19 landing: each produced a
  `request.done` embed (from `apply_decision`, `cogs/community/requests.py:220`) AND a
  `web.request.done` embed (from the route's own `note()`, `api/tools/requests.py:273`).
  `logkinds.bare()` already calls the two "the same event, logged from two places"
  but only for classification — nothing dedups the post or the row. Surveyed
  2026-09-03 (scratchpad `survey_double_log.py`, AST walk): the same shape is in
  **8 route files** — events (`apply_decision`/`cancel_event`/`rename_channel`),
  honeypot, mod (`_punish` ×6, case apply, rule), modmail (reply/close), polls
  (create/decide/end/cancel), requests (decide/resume/status), rolemenus
  (`staff_assign`), tempvoice — plus roles per the `bare()` docstring. Pre-dates
  Phase 17 (`f7199a5` already had it); it surfaced now because `request.done/hold/
  declined` are IMPORTANT and post at the default level. Fix = the convention the
  newer code already uses (`pings.py:head(via)`, `rolemenu_panels.note(via=)`,
  applications): the shared path takes `via`, logs ONE row with the `web.` head
  when `via == VIA_WEBSITE`, and the route drops its second `note()`. Status:
  **waiting on the owner's go-ahead for the 8-file sweep** (recommended) vs
  requests-only.

## 2026-09-03 — Phases 17/18/19: chat memory + requests state machine, raid trains, applications — NEXT WAVE items 3, 6, 7

Moved whole from `TODO.md`. The three phases were **built in parallel** by three Opus
worktree builders (owner 2026-09-02 22:25: "Can we start doing some of this in parallel?")
under §K of each design — shared files append-only, pre-assigned schema numbers 23/24/25,
merge order 17 → 18 → 19, the reviewer resolves. Phase 17 (`info/phase17-design.md` +
`info/requests-states-design.md`, branch tip `44f4a9b`) merged `6d61994`; Phase 18
(`info/phase18-design.md`, tip `8999d6e`) merged `0bb3835`; Phase 19
(`info/phase19-design.md`, tip `dcba425`, ~575k tokens) merged `7b1c592`. Conflicts were
all additive (the `SCHEMA` foot, `SCHEMA_VERSION`, registry defaults, log kinds, COGS,
the mock contract — `contract.json` had to be merged structurally because keep-both
produced invalid JSON; `tests/storage/test_db.py`'s two schema-22 upgrade tests were
rebuilt verbatim from both branches after the textual merge interleaved them). Merged tree:
**3238 tests**, ruff clean, 17 pages / 136 routes, 19 cogs, 44 commands, 17 features,
schema **25**. **Deployed `7b1c592` 2026-09-03 00:31 Phoenix** via `scripts/deploy.ps1`.
Verified live: boot log at 07:31:27Z shows **19 cogs** loaded incl. `content.chat_memory`, `content.raidtrain`, `community.applications`; **44 app commands synced**; `/memory` and `/apply` hidden by command visibility (both modes off); logged in; birthdays import ran; no error or traceback line. NOT verified: the schema number on the live volume (the boot log does not print it), any dashboard section in a browser.
All three modes ship **off** (`chat_memory_mode`, `raidtrain_mode`, `applications_mode`).
Findings worth keeping: Phase 17's §J measured 29/29 distillations parseable on
`openai/gpt-oss-120b` (median 0.77 s) and moved `/memory` out of the staff-only `/chat`
group (deviation 1 of 6); Phase 18's §J found Phase 4's calendar helper NOT reusable — it
writes to the `events` table — so `raidtrain_scheduled_event` ships `false` with a
creator of its own (D13); Phase 19 found `change_roles` is module-level and remembers its
own edits, so the reconciler never reports an approval as by-hand and `role_menus.py` was
never touched (9 deviations at the foot of its design). Requests ride-along: the owner's
state machine landed as data (`TRANSITIONS`), `hold` remembers `held_from` and resume
returns there (a request held from `open` resumes into `in_progress`, because resuming IS
starting work — noted in the design's Deviations), `pending`/`approved`/`planned` migrated
to `open`, `request_auto_approve_staff` retired (owner: "Even a staff request can be bad"),
requester DM + `request_status_channel_id` line on every staff move. At landing: request
#1 and #2 → `done` (DM to Pawpette), #3 → `hold` with the owner's note. Residuals
KI-14 … KI-18. Owner's sweep rows 48–57 open. ⚠️ NOT verified: any of the three features
against live Discord — no profile distilled, no train posted, no form filled. Also this
session: `DONE.md` had been double-encoded whole by the Phase 16 landing commit `31b1689`
(333 mojibake sequences) — repaired by rebuilding it from `0229da0` plus the Phase 16 entry,
proven lossless (27 additions, 0 removals against `0229da0`).

- NEXT WAVE item 3, verbatim:
3. **Chat long-term memory** — GABI-style distilled member profiles (her design:
   cheap-model distillation when a conversation goes quiet, ≤2KB per person,
   injected as a memory block; see `catalog-platform` gabi-memory-design.md).
   Privacy decisions needed from the owner BEFORE building (what is remembered,
   member opt-out, retention). **DRAFT DESIGN 2026-09-02 17:10 →
   [`info/phase17-design.md`](info/phase17-design.md)**: tier 1 already
   exists (`chat_window`); adds schema 23 profiles distilled on the hourly
   sweep, `/chat memory`, a Memory section on the Chat page. ✅ **ALL FIVE
   DECIDED 2026-09-02 17:20–18:38, one at a time** (D1 opt-out · D2
   preferences with a written definition · D3 180 d, no raw archive · D4
   separate DM/server scopes · D5 counts only) — **BUILDABLE**; builder
   dispatches after Phase 16 (schema 23 follows 22).
- NEXT WAVE items 6 and 7 (with the requests ride-along), verbatim:
6. **Raid trains (member request #1, Pawpette)** — owner 2026-09-02 20:10:
   "build, also start wave 6" then "i want memory starting first". So: Phase 17
   memory dispatches first (schema 23), raid trains = **Phase 18, schema 24**.
   **DESIGNED 2026-09-02 22:30 → [`info/phase18-design.md`](info/phase18-design.md)**
   (from [`info/raid-train-capture.md`](info/raid-train-capture.md): ASKED +
   FIT buckets; LATER stays later; 15 decisions as 13 `raidtrain_*` keys).
   **Owner 2026-09-02 22:25: "Can we start doing some of this in parallel?"
   → Phase 18 builds BESIDE Phase 17** (Phases 5/6/7 precedent: shared files
   append-only, §K of the design; merge order 17 → 18, reviewer resolves).
   Request #1 set to `in_progress`, priority 2, with the decision note, on the
   Requests page; flips to `done` at landing (DM to Pawpette).
7. **Twitch Team application form (member request #2, Pawpette)** — owner
   2026-09-02 20:14: "build next" → **Phase 19**. **DESIGNED 2026-09-02 22:40
   → [`info/phase19-design.md`](info/phase19-design.md)** as general
   *applications* (staff-defined forms, ≤5 questions, grant a role on
   approve; the Team form is the first one the owner creates — nothing
   Team-specific hard-coded); schema 25; the twitch.tv invite stays a named
   team-owner click (`owner_user_id` + `next_step` per form). Builds **in
   parallel** with 17/18 (§K; merge order 17 → 18 → 19). Request #2 set to
   `in_progress`; flips to `done` at landing (DM to Pawpette).
   ✅ **BUILT 2026-09-02 23:27** on branch `worktree-agent-aecc5822942fd3a56`
   (8 commits `f0fa493`…`dcba425`, builder ~575k tokens; 2989 green at
   `3ff5bb2`, +2 single-test commits after; check.mjs 17 pages / 126 routes;
   9 deviations listed at the foot of the design). **Reviewed by Fable 23:35:
   mergeable** — waits its turn behind 17 and 18. Merge conflicts expected
   only on `SCHEMA_VERSION` + the foot of `SCHEMA` in `storage/db.py`.
   **Ride-along (owner 2026-09-02 20:19: "when a request finishes can we
   message the channel and dm the person who made the request saying its
   done"):** the DM half EXISTS (`DM_DONE`, gated by `request_dms_on_decision`);
   the channel half does not — `notify()` only posts `NOTIFY_LINE` at filing.
   Add a done line ("Request **#N** from @who is done: what", no pings) posted
   to `request_done_channel_id` (new key, blank = falls back to
   `request_notify_channel_id`), a `request_done_template` key, guard-checked,
   `request.done_notify_failed` logged on failure. Registry sync points
   (labels.js, mock server, exact-key-set test).
   **Plus (owner 2026-09-02 20:27, request #3 music bot: "put this one in
   pending/hold … make sure we dm the person and post it chat that we marked
   something as hold and why"):** there is NO hold state — staff moves are
   forward-only (approved/planned/in_progress/done/declined; the API refused
   `pending` in words). **Owner redesigned the state machine 2026-09-02
   20:33 (verbatim): "add a new status for open and then change pending to
   hold. so it goes from open -> planned -> in prog -> done with hold and
   declined as side states. Declined is a final state like done and hold can
   be anywhere in the process. we should also mark what state it was
   previously for my own sake."** Then 20:36: **"lets also get rid of planned
   since we'll hold or decline anything no need for planned."** So:
   - **Main line:** `open` (a request arrives here; replaces `pending`) →
     `in_progress` → `done` (final). Nothing else on the line.
   - **Side states:** `hold` — from `open` or `in_progress`, reason
     REQUIRED, stores **`held_from`** (shown on the page and in the DM;
     "resume" returns it there by default, staff may pick the other);
     `declined` — final, reason required, from `open`, `in_progress` or
     `hold`. `withdrawn` stays (requester's own final state, from `open` or
     `hold`).
   - **`approved` AND `planned` are RETIRED.** Starting work = the
     `open → in_progress` move. `requests_auto_approve` loses its meaning
     (there is no approve step) — Claude's reading: retire the key too;
     every filing, staff or not, arrives `open`. Data migration in schema
     23: `pending → open`, `approved → open`, `planned → open`
     (`in_progress`/`done`/`declined`/`withdrawn` unchanged).
   - **Notifications on EVERY staff move** (in_progress, hold, done,
     declined): requester DM + channel post, reason/note in the text, no
     pings; guard-checked; failures logged. Today only
     approve/decline/done DM and nothing posts to a channel after filing.
   - Touch list: `requests.py` (`STATUSES`, `STATUS_WORDS`, `DM_TEXT`,
     transitions table — encode the machine as data, one place), the cog,
     `api/tools/requests.py`, Requests page (filter, status control, held_from
     badge, resume button), `/request set` choices, mock contract,
     settings registry (drop `requests_auto_approve`;
     `request_status_channel_id` + `request_status_template`), tests.
   **Must ship BEFORE the first request lands (Phase 18) — folded into the
   Phase 17 builder brief** as a bounded add-on. At landing: flip #3 to
   `hold` with the owner's note so PT gets the DM (the channel post stays
   TEST_MODE-blocked until the lift).
   Meanwhile #3 sits `approved` with the note "ON HOLD (owner, 2026-09-02):
   youtube player is currently unreliable. Will do further research on this."
   ⚠️ **Owner rule 2026-09-02 20:14: every accepted request stays
   `in_progress` on the Requests page until it ships; flipping it to `done`
   is part of that phase's landing ritual.**

## 2026-09-02 — Phase 16: YouTube uploads (F3), NEXT WAVE item 2

Moved whole from `TODO.md`. Designed 17:05 (`25a9411`, `info/phase16-design.md`),
built by one Opus worktree builder (~505k tokens, four clean-boundary commits
`79508de` `a743577` `ded574f` `4e36858`; §J measured first — no ETag ever served,
Shorts free from the `/shorts/` link, feed answers ~50% → KI-11/12/13), Fable-reviewed
against the design + checklist, merged `7295f61`, **deployed `049881b` 22:18
Phoenix** via `scripts/deploy.ps1` (2865 tests, ruff clean, 17 pages / 116 routes).
The first deploy run died at `git push` on a PowerShell-5.1 stderr quirk after the
push had landed — fixed in `049881b` (`cmd /c … 2>&1`), gotcha in `access/runbook.md`,
gate rerun in full. Verified live: boot log shows 16 cogs incl. `content.youtube` (feed-only notice — no key), 39 app commands synced, logged in, no error/traceback lines. âš ï¸ NOT verified: any real YouTube
channel (`youtube_mode` ships off; no channel linked; no API key minted), the Go-live
page section in a browser. Residuals accepted at review: no retry backoff on the feed
sweep (KI-12 covers the miss rate); the cog floors the poll interval at 1 min while
the registry says 5.

- NEXT WAVE item 2, verbatim: **F3 — YouTube upload announcements**: go-live via YouTube presence already
   works (sweeps row 4); this adds NEW-UPLOAD posts, which needs the YouTube
   Data API (owner mints an API key — free quota) + a channel-link store like
   `/twitch link` + a poll loop like the Twitch one. **DESIGNED 2026-09-02
   17:05 → [`info/phase16-design.md`](info/phase16-design.md)**: the public
   Atom feed is the primary source (NO key needed); `YOUTUBE_API_KEY` is an
   optional upgrade (handle resolution, live/Shorts classification) — the owner
   may mint one at their pace. Ten defaults taken as settings keys. Builder
   dispatches after Phase 15 lands (schema 22 follows 21).
- Feature-table row, verbatim: | F3 | **YouTube** — *maybe* | Go-live via YouTube presence WORKS (sweeps row 4); uploads = 🚀 NEXT WAVE item 2. | next wave |

## 2026-09-02 — Phase 15: ping roles (F14), NEXT WAVE item 1

Moved whole from `TODO.md`. Designed 16:45 (`d293193`, `info/phase15-design.md`),
built by one Opus worktree builder 16:50–17:35 (509k tokens, four clean-boundary
commits `55990db` `68e422a` `37407bd` `4357c1d`), Fable-reviewed against the design +
checklist, merged `c577b06`, **deployed `d777f57` 17:43 Phoenix** via the gated
`scripts/deploy.ps1` (2714 tests, ruff clean, 17 pages / 111 routes). Verified live:
boot log shows 15 cogs incl. `content.pings`, the Ping roles section (7 keys) on
Settings and the Pings section on the Go-live page both render; `pings_mode` flipped
**on** from the dashboard 17:47 (persisted across reload). ⚠️ NOT verified: any live
Discord role create/assign/delete, the two-role ping prefix on a real announcement —
those are the owner's sweep. Builder's four deviations accepted at review: self-serve
follow/unfollow logged routine (role-menu precedent); no `pings.would_*` kinds (off
means refuse-in-words, nothing to emit); `/pingroles setup` works while the mode is
off (so it can be prepared before the flip); `_fill_menu` clears before re-adding
(`add_option` preserves position). Residual: the old process logged `asyncio:
Unclosed client session` at shutdown during the rolling deploy — pre-existing, not
from this build; watch.

- NEXT WAVE item 1, verbatim: **F14 — ping roles** (the last unbuilt item from the original 2026-08-26 list):
   an opt-in **Events** role pinged on go-live/event announcements, and
   **per-streamer favourite roles** ("people that want to see SuperNamu only …
   can get her pings") wired into announcements + the role menus. Everything it
   needs exists: role menus (incl. approval/staff modes), `golive_ping_role_id`
   / `events_ping_role_id`, the announcement paths. **DESIGNED 2026-09-02 16:45
   → [`info/phase15-design.md`](info/phase15-design.md)**; the seven small
   decisions (who creates a fan role, its name, one Events role for both feeds,
   keep-on-unlink, delete-on-remove, mode off at deploy, three opt-in surfaces)
   were taken with defaults and are ALL settings keys, so the owner flips them
   on the dashboard rather than in chat. **Opus worktree builder dispatched
   2026-09-02 ~16:50.**
- Feature-table row, verbatim: | F14 | **Ping roles** (owner, 2026-08-26): an opt-in **Events** role for go-live/event pings, and **favourite-streamer roles** — per-streamer opt-in pings ("people that want to see SuperNamu only … can get her pings"). Wire into F1/F5 announcements and the role menus. | 🚀 NEXT WAVE item 1 |

## 2026-09-01 — The chat-hardening wave: an afternoon of live findings, one deploy

Moved whole from `TODO.md` (every bullet below was a live finding the owner or a member
made while talking to the newly-enabled LLM chat; all landed in `1ab76f8`, deployed
2026-09-01 19:01 Phoenix — three Opus builds: who-has `cf11cdc` ~212k, guardrails
`ed2710c` ~436k/7 items, four-pack merge ~418k/4 items; **2606 tests**, 17 pages /
107 routes; verified after deploy: /health ok, 35 commands synced, **the re-run ingest
kept all 6 leaked rows out (0 returned) and wrote 36 role-holder notes**):

- **STATUS 2026-09-01 ~17:5x: who-has (`cf11cdc`) and the full guardrails package (`ed2710c`, 2567 tests) are MERGED on main, NOT deployed** — ⚠️ deploy still held until the follow-up four-pack (tier threshold + self-knowledge + Costs card + persona play-tune, **Opus builder dispatched ~17:55**) lands, then ONE deploy ships the whole day. Guardrails highlights at review: the ingest filter is enforced by signature (no path skips it, fails closed), the reply guard fails OPEN (a crash never turns an answer into silence), the no-ping hole did not exist (measured), 24 commands locked below Aunties/Uncles + 11 visible with runtime gates, all four new keys render-proven on both pages.

- **Owner 2026-09-01 ~15:0x, verbatim: "the bot cant currently find roles, I want the bot to know who has what role so it can help escalate. so I can say hey @black_bloc tell me who's a lead or a mentor or something"** → a `who_has` DATA intent (deterministic, live gateway cache, display names never pings, ≤25 listed, staff-role answers end with the escalate pointer) + role-holder sections in the daily knowledge ingest for roles ≤25 humans so the Haiku tier grounds odd phrasings. Status: **Opus builder dispatched ~15:10 in a worktree.** (Same session, earlier: `/chat status` admin-locked behind `chat_status_admin_only` `45176ed`; managed role renamed `role_black_bloc` via the API — both live.)

- **Owner 2026-09-01 ~15:2x: the bot invented `#black-support-hub` in a live reply** ("make sure it references real channels, this was a great call by the bot to do this though"), then ~15:3x: "i think we need to read the desc of every channel and use that to help guide the bot". ⚠️ Also the first confirmed LIVE model conversations. Fix (queued behind the in-flight who-has builder — same files): (1) a **channel directory on EVERY model call** (both tiers): name + trimmed topic from the live gateway cache, ⚠️ PUBLIC channels only (@everyone-visible — never leak staff/private names into member answers), byte-capped, positioned cacheably in the system stack; (2) persona-core rule: point people only at directory channels; name no channel/role/member absent from directory, grounding or the conversation; (3) deterministic post-check backstop — unknown `#channel` tokens swapped for `chat_home_channel_id` (new key, channel, blank default = de-channel the sentence gracefully) and logged (`chat.reply_channel_fixed`, routine) so hallucination frequency is measurable; (4) 🔴 **MEASURED 2026-09-01 ~15:45 — the ingest takes EVERY text channel with a topic** (`knowledge.py:373`, no visibility or category filter): `#black-support-hub` turned out to be REAL but in the `archive` category (the bot recommended a dead channel it faithfully read), and **five incumbent-Modmail ticket channels leaked in with topics carrying member ids** — a privacy leak into LLM grounding. Immediate mitigation done: the 6 rows deleted from the live DB (re-ingest would return them in ~24h; the fix must land first). The fix: ingest AND the per-call directory take only channels @everyone can view, excluding categories whose name contains "archive" and the modmail category, plus a `chat_ignore_categories` key (both doors) for anything else; the who-has intent gets the same scoping. (5) **Owner 2026-09-01 ~16:0x (live exchange: "im looking for a mod can I trust @Pawpette" → the bot claimed not to know and suggested "ping @Admin"): member-trust answers by the CANONICAL staff check** ("can we check by permission levels" → `store.is_staff`, the one rule everything else uses — Lead qualifies): (a) a deterministic member-lookup intent — "is @X a mod / can I trust @X" answers from live roles + is_staff ("Pawpette holds Lead — yes, staff, they can help"); (b) every LLM call is grounded with the roles + staff-status of any members the message mentions; (c) the post-check guard covers invented @role suggestions like channels; (d) "looking for a mod" joins the modmail-route triggers so it never reaches the model at all. (6) **Owner 2026-09-01 ~16:1x, verbatim: "also need to not let it ping roles too often. maybe i'll have it output 2 online people for a role if someone ask. so if i ask for an admin or a lead output Pawpette and PT because they have the roles. dont @ them though, let the user do that part"** → (a) chat replies send with `allowed_mentions` stripped (roles/everyone/users) so the bot can NEVER ping from a conversational answer — transport-layer, not prompt; (b) escalation-shaped asks name up to `chat_escalation_names` (new int key, default **2**, both doors) ONLINE holders of the relevant staff role as plain display names, the user does the @-ing; none online → say so + modmail pointer; full-roster "who has X" keeps the complete no-ping list. (7) **Owner ~16:2x: "let the bot ping roles if an aunties/uncles or higher initiates it"** → the allowed-mentions strip gets a staff exception: when the INITIATOR passes the canonical `is_staff` (Aunties/Uncles is its floor), role mentions go through in the reply; `@everyone`/`@here` never do for anyone; gated by `chat_staff_can_ping_roles` (new bool key, default on, both doors). Owner decision open, no rush: which channel `chat_home_channel_id` should point at. Status: **queued behind the who-has builder.**

- **Owner 2026-09-01 ~16:4x: "the groq web portal says 0 api calls have been made using the key"** → MEASURED on the live ledger: 8 calls, ALL `anthropic/important/ok`, zero Groq attempts, zero errors (~$0.01 total). Root cause: `tier_for`'s "any knowledge hit → IMPORTANT" rule + the search's OR-fallback ≈ everything matches something in 29 server notes, so the simple tier is never chosen. Fix: only a STRONG hit (AND-pass / score threshold) counts toward tier promotion; weak hits still ride as grounding without upgrading the call. Status: **queued behind the in-flight guardrails builder (same files); small enough for a Fable-reviewed direct change when it lands.**

- **Owner 2026-09-01 ~16:5x (live): "i want to host an event, can you show me how to do that" → the bot said "hit up @Admin"** instead of naming its own `/event create` ("meh didnt pull up the event form"). The bot has no knowledge of its own features. Fix (same follow-up build as the tier threshold): (a) deterministic intents for the self-service features — host/create an event → `/event create` + the review flow in one sentence; file a request → `/request`; link Twitch → `/twitch link`; set a birthday; pick roles (the role menus); (b) a compact "what Black Bloc itself can do" block (the /help content, member-visible commands only) in the system stack on every model call — stable, cacheable — so novel phrasings land on its own commands instead of "ask staff". Status: **queued with the tier-threshold fix.**

- **Owner 2026-09-01 ~17:0x: "on the dashboard somewhere can put a cost breakdown for the hosting, apis keys, models, etc. so we can track spend"** → a **Costs card on the Health page** as THE one home for money: measured LLM spend from the ledger (month-to-date + per provider/model, Groq shown at $0.00 on free tier), hosting as a configured `cost_hosting_usd` key (Fly exposes no billing without a token on the machine — same risk class as the parked deploy button; owner fills it from the invoice, both doors), the free-tier items named ($0), and the secret inventory by NAME + set/unset. The Chat page's Spend section repoints its dollar figure here (link) and keeps tier liveness — one number, one home. Status: **queued in the follow-up build (tier threshold + self-knowledge + costs).**

- **Live 2026-09-01 ~16:50 (member PT): "who is the strongest DBZ character" → the bot deflected** ("way outside my wheelhouse… you'd get better arguments in #off-topic… Who's your pick?") and the member called it out ("have the bot at least pick a character"). Persona bug, not knowledge: the cookout core over-weights "I'm just here for the cookout" into topic-dodging. Fix (persona core text, follow-up build): fun/opinion questions get a REAL answer — take a pick, give one playful reason, in voice; never bounce the question back as the whole reply; channel redirects become an aside, not the answer; deflection reserved for things it should not do. (Noted: it named real channels this time — the pattern held even before the directory ships.) Status: **queued in the follow-up build.**

**The finding that explained everything:** the four-pack builder measured that the
bot's own `<@mention>` token entered the knowledge search, so the strict AND-pass
could never match a real @-mention and EVERY live call fell to the loose OR pass →
`any hit → IMPORTANT` was unconditional → 9/9 calls billed Haiku, Groq never chosen.
Fixed by stripping the mention before search + a strong-hit rule (AND-pass + title-
weight score + whole-word terms). Also in the wave: /chat status admin-locked
(`45176ed`), the managed role renamed `role_black_bloc`, and the live purge of the 6
leaked knowledge rows ahead of the fix. **NOT verified: no real model has read the
new persona rules or FEATURES block** — the owner's retest is the measurement.

## 2026-09-01 — Phase 14: the bot can really talk (three tiers, knowledge, personas — shipped dormant)

Moved whole from `TODO.md`:

- **Owner 2026-09-01 ~11:00, verbatim: "lets do the parked items"** → F10 chat step 3 un-parked. Four decisions taken one at a time (§0 of the design): three tiers ("can we do a mix of 1 and 3 to help save token cost?" → intents free / "groq/llama for simple things and then Haiku for more important things" / "We'll do a context ingestion like we did for Gabi"), cap "$20/month", personality "start with 1 [Cookout] but port over all the other personalities too. we can start building a global personality pool". GABI survey (Opus explore, catalog-platform) fed the design: lexical-not-vector knowledge, deterministic routing before any model call, independent fuses, worded refusals, affirmative-only gates. Design = `info/phase14-design.md`. Status: **14a (core+bot) and 14b (dashboard) Opus builders dispatched ~11:30 in parallel worktrees; ships with `chat_llm_mode off`.**

**Landed as merge `a49e77d`, deployed 13:21 Phoenix** (`deploys.log`; verified: `/health`
ok, chat cog loaded, 35 commands, logged in 20:21:23Z). Three Opus builds: **14a**
(~473k, 8 commits): schema **20** (knowledge_sections/personality_tropes/chat_window/
llm_ledger), `llm.py` (anthropic SDK, Haiku 4.5, 400 max_tokens, prices pinned) +
`groq.py` (aiohttp, `chat_simple_model` default llama-3.3-70b-versatile), `tier_for`
(one pure function: knowledge hit / long question / live conversation / staff topic →
IMPORTANT; important never falls back to the cheap model), knowledge store + lexical
port + daily server ingest + `/chat knowledge`, personas (core + cookout + 11 GABI
tropes as data with provenance; drift derived not stored), fuses (20/person/hr,
200/day, $-cap vs ledger; cap 0 = zero calls by pinned test), 6 registry keys, wired
behind affirmative-only `chat_llm_mode`. **14b** (~383k, 3 commits): 9 staff-gated
`/api/chat` routes (tier liveness measured mode→key→cap, refusals in sentences),
the Chat page's Knowledge/Personality/Spend sections, contract to **17 pages / 106
routes**. **Integration** (~227k, 4 commits): 14b's stand-in store deleted and routes
repointed at 14a's canonical modules; `UNIQUE(guild_id, source, title)` index added
(ingest writes INSERT OR IGNORE against duplicate channel names); persona mode
collapsed onto the `chat_personality` registry key (website switch-off now busts the
trope cache — a real bug the stand-in hid); one base kind per decision (`web.` head
tells the doors apart); mock registers all 13 chat keys with enum choices derived
from the pool; two auto-merge defects fixed (duplicated ROUTINE entries, split kind
names). `cozy` vs `cosy`: checked against GABI's `personality.ts` — canonical key and
label are `cozy`; 14a was right. **2451 tests** (+186 net), ruff clean, check.mjs
17/106. **NOT verified: no real model call has EVER been made by this code** — both
keys are unset everywhere; the first `/chat status` after the owner's switch-on is
the first real cost figure. Owner go-live steps on TODO; sweeps rows 33–35.
Peer README rewrite + deploy-button decisions landed the same morning (see TODO
session log): README `91b3ab7`, deploy button stays parked.

## 2026-09-01 — Go-live hardening, requester-in-channel, the settings audit, nightly backups

Moved whole from `TODO.md`:

- **F4 follow-ups (owner, 2026-08-26):** (a) add the requesting user to their
  own event channel so they can post updates / answer mod questions — or show
  them a ticket page on the F12 site; (b) the approver-roles / event-category /
  create-scheduled-event toggle all become F12 site settings.
- **F5 follow-ups (owner, 2026-08-26):** announce channel + ping role editable
  in the options menu now and on the F12 site later.
- **Go-live follow-ups from the review fixer (2026-08-26):** (a) `live_role_added`
  is a 0/1 flag — store the role *id* so a mid-stream change of
  `golive_live_role_id` cannot strand the old role; (b) session age-out only ticks
  when Twitch creds exist (the poller) — add a creds-independent tick; (c) a failed
  Helix live-check leaves a session open (age-out is the backstop). None block shadow.

**Landed as merge `5f22c20`, deployed 2026-09-01 09:16 Phoenix** (Opus ~242k, four
commits; 2265 tests, ruff, 17/98 green; migration `added golive_sessions.live_role_id`
seen in the Fly logs). (a) schema **19**: the session stores the role id that was
actually added; removal reads it first, legacy rows fall back to the setting.
(b) was a REAL gap with a different root than written: the sweep body already ran
pre-Helix-check, but `cog_load` only STARTED the poller when creds existed — now it
starts unconditionally and `/golive status` says "the sweep still runs and still ages
sessions out" on a credential-less deploy. (c) `golive.poll_degraded` (routine) after
exactly 3 consecutive TwitchErrors — one line per outage naming failures + open
sessions; nothing is closed on a failed check. (F4a) requesters get an explicit
view/send/history overwrite on their own review channel, surviving renames (verified
by reading `rename_channel`, tested through a `done-` rename); access deliberately
stays after decision. (F4b/F5) **audit result: all five toggles already existed** as
registry keys reachable both ways (`staff_channel_id`, `events_category_id`,
`events_create_scheduled`, `events_announce_channel_id`, `events_ping_role_id`) —
nothing was missing; one nuance: the category is set on Discord via `/event settings
category:` because generic `/settings set` takes text channels only. **Same deploy:**
`black_bloc/dbsnapshot.py` shipped and the **nightly backup went end-to-end**
(scheduled task "BlackBloc DB backup", daily 04:00; test pull 311,296 bytes, "ok" in
`backup.log`) — RECOVERY's backup gap CLOSED with the machine-state residual recorded.
**NOT verified live:** no real role add/remove, no real credential-less deploy, no
real Twitch outage, no requester has posted in a review channel. Owner sweep rows
31–32.

## 2026-08-31 — Owner bug report: empty Requests queues said "null"

Owner, ~13:20, verbatim: *"https://blackbloc.heygabi.ai/requests.html it says null
since 0 records, fix this up to say something about this particular queue being
empty"* → measured in the owner's own browser (screenshot): each empty queue showed
its correct per-queue sentence ("Nothing is waiting on an answer…") **plus the
literal word `null`** and a dead `Previous · Page 1 · 0 shown · Next` row. Root
cause: `page-requests.js:footFor` returned `null` and `body.append(null)` renders
the WORD — the exact trap the file's own line-365 note documents for
`replaceChildren`; the call sites didn't filter. Fix `d2516aa`, deployed 13:28:
`footFor` returns an empty fragment (covers staff + member views), and
`ui.js:pager` renders nothing on page 1 with zero shown and no more pages (all
pages benefit). **Verified live by screenshot after deploy** — sentences only, no
null, no dead pager. 2257 tests, ruff, `check.mjs` 17/98 all green.

## 2026-08-31 — Restyle R2 live: the site wears Black Bloc

Moved whole from `TODO.md`:

- **Site restyle R2 — the skin** (R1 is LIVE `0c49257`, see `DONE.md`; brief =
  `info/site-restyle-design.md`): the "Black Bloc" theme dark+light as the new
  default (existing 5 themes stay), wordmark + display face, the sentence-voice
  copy pass (C's group names and labels), table toolbar/drawer furniture, Ctrl+K
  command palette, show-keys toggle. Status: **R2 Opus builder dispatched
  2026-08-31 ~12:35 in a worktree.**

**Landed as merge `c334922`, deployed 13:14 Phoenix** (Opus ~417k, 8 commits
`a28caef`..`090a593`; 2257 tests, ruff clean, 17 pages / 98 routes). What shipped:
the **Black Bloc theme** as default (`data-default-theme="blackbloc"` on all 17
pages; a stored choice still wins) with a measured contrast table — worst ratio
**4.51**, four §4C palette values darkened to clear 4.5, danger deliberately the
one COLD hue so Ban never wears the warmth; **Bangers** wordmark + page titles
(already on disk, OFL — Bricolage would have needed vendoring) via a
`--bb-title-font`/`--bb-chrome-font` split that leaves the six estate themes
untouched; **sentence-voice pass** — group captions "Runs the server / Runs the
cookout / The desk", all 90 labels rewritten (key set byte-identical), the
Overview TODAY sentence with each clause a link (it REPLACED the "Needs a human"
card — one fact, one home); **table furniture** — toolbars, ⓘ heads,
"Showing 1–N of M" feet (which absorbed four duplicate counters), a Cases
right-hand drawer (native dialog; Requests renders cards, no drawer — the
brief's escape hatch), plus two found defects fixed (opaque `--et-transit-bg`
was blacking out every theme's modal backdrop and the mobile scrim → `--bb-scrim`);
**Ctrl+K palette** (`palette.js`) over pages/settings-by-label-and-key/actions,
exercised end-to-end (anchor jump needs `behavior:'auto'` — smooth scroll gets
cancelled by the next layout); **Show keys** toggle, per-browser, no flash,
palette still finds hidden keys. Rendered: all 17 pages × both modes (34
screenshots), Cyberpunk + Discord regression-checked. Deviations accepted by
Fable at merge: seven themes in the dropdown (discord was already a sixth),
Bangers, no Requests drawer, TODAY replacing the card, `estate-theme.css`/
`theme.js` edited with precedent. **Verified live after deploy:** `/health` ok,
35 commands synced, `palette.js` 200, blackbloc default on the live index.
**NOT verified:** no real member-only session, no narrow viewport, no real-API
browser pass; contrast computed from hexes. Owner sweep rows 28–30. Known
cosmetic: "RUNS THE COOKOUT" wraps in Cyberpunk's rail (its own type scale) —
owner's call, on TODO.

## 2026-08-31 — code-notes.md re-keyed: 1215 of 1817 anchors were wrong

Moved whole from `TODO.md`:

- **`code-notes.md` re-key** — measured 2026-08-31: 88 files / 22,333 insertions
  since the last re-key (`666dd8e`); 4 of 4 spot-checked `bot.py` keys miss.
  A build-sized diff-driven pass (the file carries a red warning meanwhile).
  Three more builds appended sections today — re-key covers through `ef8a7a1`.
  Status: **re-key Opus agent dispatched 2026-08-31 ~12:35, editing in place,
  uncommitted for Fable review.**

**Landed `b22d44b`** (Opus ~274k): 1817 in-scope keys checked, **1215 updated**, 590
already correct, 12 GONE (marked in place with section banners, constructs deleted by
later phases — the pager guard, `classify` in chat, four mock fixtures, two retired CSS
rules, cyberpunk's neon `--et-info` pair, the golive preview command). Method: one base
commit fitted per section, keys mapped base→HEAD only along diff-equal lines, residue
anchor-hunted; two path-resolution bugs in the file's own reference style found and
fixed; two automated anchor-jump passes tried and REJECTED on dry-run evidence (clearly
wrong jumps beat no jumps). Cold 20-key samples: 45% exact before repair → **70% exact /
80% usable at delivery**, found misses then repaired (all were stale before `666dd8e`).
Integrity: 1629/1632 final keys land on a real construct line, 0 out of range. Residue
recorded in the file: 3 keys too vague to place confidently (`ui.js:415`, `bot.py:41`
deliberate, `birthdays.py:423`), and the false cyberpunk-accent note superseded in place
by Fable. CLAUDE.md's KNOWN-STALE warning replaced with the re-key rule.

## 2026-08-31 — KI-6/KI-9 closed and restyle R1 live in one deploy

Moved whole from `TODO.md` (both dispatched ~11:45 in parallel worktrees, merged and
deployed together as `0c49257` at ~12:20 Phoenix; `deploys.log` has the two lines —
the secret-set restart and the deploy; **2257 tests**, ruff clean, 17 pages / 98 routes):

- **KI-6 / KI-9 thresholds CROSSED by Phase 13** (found by the docs audit
  2026-08-31): the dashboard now admits any signed-in guild member, so KI-6's
  ">1 site user" trigger (sessions table + a per-session id in the cookie +
  revocation on logout) and KI-9's (HMAC poll-vote hashing with a
  `POLL_VOTE_SECRET`) are due. Status: **Opus builder dispatched 2026-08-31 ~11:45 in a worktree** (schema 17 sessions + per-poll hash scheme; expect a one-time sign-out for site users at deploy).
- **Site restyle R1** (of the R1 + R2 item; owner decisions 2026-08-31, all six
  taken; brief = `info/site-restyle-design.md`): R1 shell — grouped nav + icons,
  width-filling grid, docked dirty save bar, human labels. R2 stays on TODO.

**KI-6** (`90afc3e`, Opus ~219k for both security items): schema 17 `sessions` table,
`sid` in the signed cookie, live check on every authenticated request (30 s in-process
verdict cache, bounded 4096; logout poisons the cache BEFORE the DB write), logout
revokes. Old cookies = one-time sign-out at deploy (sweeps row 25). Documented
fail-open: DB down → signature + expiry only, because every data route already
refuses via `require_db`. **KI-9** (`272ea66`): schema 18 `polls.vote_scheme` stored
per poll at creation — an open poll NEVER changes scheme (no double votes); new polls
use HMAC-SHA256 keyed by `POLL_VOTE_SECRET` (via `config.py` only; minted and set on
Fly + `.env` by the session ~12:15, value never displayed); a keyed poll with the
secret missing refuses in words, never double-counts; unset secret = old scheme + one
startup warning, never a broken deploy. Deliberately NOT a registry key (a MAC key
the dashboard can show is not a MAC key) — recorded against checklist 33.
KNOWN_ISSUES: both entries superseded → CLOSED with residuals recorded.

**R1** (`b6a1fb3`→`87108ec`, Opus ~323k): the builder first measured that the top bar,
4-group rail and settingsEditor/saveBar plumbing had ALREADY shipped 2026-08-27
(`666dd8e`) — the restyle brief's "nothing built yet" was stale; corrected. Newly
built: one SVG-sprite icon per nav item (`icons.js`, currentColor, 3.46–10.69:1
across all 12 theme/mode pairs), width-filling 2-up grid (`layout.js`; tables go
full-width), docked dirty save bar everywhere `settingsEditor` runs (per-field
Save/Clear gone; ⌫ reset per row), `labels.js` with **90/90 registry keys** mapped
(checked programmatically against `settings_store.py`), empty-cell `—` / sentence +
action empty states, 24px title cap — plus a found-by-measuring shell bug: the docked
bar sat OFF-SCREEN in 5 of 6 themes (`grid-template-rows` auto vs `minmax(0,1fr)`),
invisible in the one theme being tested. All 17 pages rendered in Chrome against the
mock, zero console errors; permission machine / pager / search / section memory
re-checked live. **Verified live after deploy:** `/health` ok, 35 commands synced,
`added polls.vote_scheme` migration in the Fly logs, sessions table + vote_scheme
present on the live DB, R1 assets serving 200. **NOT verified:** no real browser has
signed in since the deploy (the one-time sign-out has not been SEEN), no anonymous
poll exists to prove an `hmac` row, the sub-1100px single-column layout was verified
by forcing the media query, not a narrow window. Owner sweep rows 25–27.

## 2026-08-31 — DB backup drilled: the first dated drill line in RECOVERY.md

Moved whole from `TODO.md`:

- **DB backup drill** (RECOVERY gap re-opened by the docs audit 2026-08-31):
  the live volume now holds real rows (38 birthdays + settings + cases) and
  RECOVERY.md's own threshold — "the first table with real data" — has passed.
  Need: a dump path off the Fly volume (`flyctl ssh sftp` or a scheduled
  export), drilled once, documented in `access/RECOVERY.md`.

**Landed 2026-08-31 ~11:35 Phoenix, run by Fable from the session:** consistent
snapshot via `sqlite3.backup()` on the machine (no sqlite3 CLI in the image —
python3 does it; a raw copy of the live WAL-mode file can tear), pulled with
`flyctl ssh sftp get` to `%USERPROFILE%\black-bloc-backups\backup-2026-08-31.sqlite3`
(290,816 bytes), **verified by opening it**: 30 tables, birthdays 38, chat_intents 15,
settings 6; drill file removed from the volume after. Procedure + three gotchas
(MSYS path rewriting, the bogus "handle is invalid" exit, never store a backup in
the tracked repo) written into `access/RECOVERY.md`, whose header now carries its
first dated drill line. **Residual, owned by the RECOVERY gap table:** the pull is
manual — nothing schedules it yet.

## 2026-08-31 — B4–B8: the last five audit leftovers, live

The 2026-08-27 site-feature audit's open tail (`info/site-feature-audit.md` §2), queued for
the post-reset resume and dispatched the morning the owner returned ("lets get started with
whats left on our todo list", ~10:13). One Opus builder (~485k), one commit per item off
`7b7840b`, merged `3cae955`, **deployed 11:32 Phoenix** (`deploys.log`); verified live:
`/health` ok, 35 commands synced, logged in 18:31:58Z. **2227 tests** (+65), ruff clean,
`check.mjs` 17 pages / **98 routes** (+9).

- **B4** `4f0f399` — temp-voice rooms get Rename / Cap / Lock / Hide on the dashboard.
  `do_rename`/`do_limit`/`do_privacy` refactored off `Interaction` onto a `Doer` NamedTuple
  (client, guild, user, via) that an Interaction already satisfies — panel and `/voice` call
  sites unchanged, ONE implementation; helpers return `Said` (a str carrying `ok`) so the API
  can pick 200 vs a refusal. Place-gated by `may_act_in` (test mode = only rooms in the test
  category, `409` in words). Skipped on purpose: region + kick (each needs a per-row picker;
  nothing blocks adding them).
- **B5** `47628b7` — `POST /api/rolemenus/{name}/unpost` + an Un-post button + **`/rolemenu
  unpost`** in Discord (checklist 33). Goes through `rolemenu_panels.unpost`, NOT
  `clear_message` (which would forget the id and leave the panel live — the KI-8 trap);
  guard asked twice to tell `409 test_mode` from `409 panel_stuck`; `note()` gained `via` so
  website panel actions log under a `web.` head (also fixes the same residual on `move_panel`).
- **B6** `2c65db0` — `POST /api/rolemenus/seed` + Seed defaults button; `created`/`skipped`
  as lists; `seed_summary` is the one wording both surfaces show; never rewrites an existing
  menu. New kind `role_menu.seeded` (routine).
- **B7** `d8f44c7` — staff assign from the site (`POST /api/rolemenus/{name}/assign`).
  `staff_assign` = the select callback's body lifted whole; the extraction fixed a
  checklist-12 ordering bug (the select answered the clicker BEFORE writing `role_grants` +
  the action line, so a failed reply ate the record). `role_diff` untouched — only menu-owned
  roles ever move. Deliberately NO test-mode refusal (roles aren't a channel; `/rolemenu
  assign` behaves identically today). Deviation: the form offers every menu with roles, not
  only `staff`-mode ones, matching the slash command; options labelled `name — mode`.
- **B8** `379b0c1` — `GET/PUT /api/events/{id}`: detail card + "Change it" for
  pending/approved events. `checked_fields` = the modal's whole validation chain shared, so
  the two doors cannot drift; the body names its IANA zone (browser zone shown above the
  field, staffer's `/timezone` as fallback); review channel renames via the guard-aware
  helper; an already-posted announcement or scheduled event keeps its old details and
  `notes` says so in words. New kind `event.edited` (routine).

**NOT verified live:** nothing ran against real Discord — no room renamed, no panel
deleted, no role granted, no event edited, no page rendered in a browser (contract + parse
checks only). Owner sweep = `access/sweeps.md` rows 21–24. Builder process notes worth
keeping: `pytest | tail` returns tail's exit code (check the summary line), and editing
source during a background full-suite run produces spurious `test_logkinds` failures.

## 2026-08-31 — Post-trip bookkeeping sweep: landed 2026-08-26/27 items moved off TODO

Moved whole from `TODO.md` (every item below was verified shipped by the 2026-08-31 docs
audit — ancestors of the live `8036918` per `git merge-base`, or otherwise measured; the
residual owner checks were consolidated into `access/sweeps.md` rows 18–20 and its new
phase-script appendix, which is now the ONE home for un-exercised items). Entries whose
text also appears inside the Phase 12/13 landing entries below are superseded by these
fresher copies (statuses advanced to DEPLOYED). The round-1 findings section and the
detailed phase click-scripts moved to `access/sweeps.md` rather than here, since their
only open half is owner verification. Standing rules moved here (90%-weekly stop,
configurable-both-ways) remain IN FORCE via memory / `CLAUDE.md` / checklist 33 — the
move only records that the *task* of establishing them is done:

### Owner test sweep — round 1 findings (2026-08-26 ~22:55) — moved whole

Four findings, all four **fixed on `main`, committed, and since DEPLOYED**:
`8fe0677` (temp voice) and `9d948ca` (role menus + `/twitch link`) — both are
ancestors of the live commit `8036918` (verified 2026-08-31 with
`git merge-base --is-ancestor`), so all four fixes have been live since
2026-08-27 at the latest. 817 tests passed at the time (the suite is now
**2158**). The still-open half — live re-verification by a person — is
`access/sweeps.md` row 19 (showall / twitch-link picker / lobby repair) and the
Loops row check.

| # | Owner's words | Fixed by | Residual owner check |
|---|---|---|---|
| 1 | *"we need a /rolemenu showall to display all role menus"* | `9d948ca` — `/rolemenu showall`, chunked at 1900 chars, ephemeral, no pings | run it (sweeps row 19) |
| 2 | *"for /twitch link it should say channel name not login, login sounds more concerning"* | `9d948ca` — parameter renamed to `channel`, no user-facing sentence says *login* | re-read the picker (sweeps row 19) |
| 3 | *"it made a locked channel i cant get into. its just a lock icon."* | `8fe0677` — explicit overwrites (allowed role + resolved staff + the bot), and `/tempvoice setup` now REPAIRS the lobby it already has | `/tempvoice setup` says **repaired**, lobby renamed, Member + staff connect (sweeps row 19) |
| 4 | 8a merge left `TempVoice._reconcile_loop` with no `@loop.error` and no health | `8fe0677` — handler + `last_ok_at`/`last_error` + `loop_health()` | status page Loops row shows `_reconcile_loop` |

⚠️ **Root cause of the `join` name, measured not guessed:** nothing in the cog
truncates a channel name. `channel_name` is the only string handling in the file
and is not on the setup path; the command's `name` parameter introspects as
optional with default `None` (`Command._params["name"].required is False`), so an
unsupplied name renders the full default. The only way to get `join` is Discord
having sent `name: join` — a value typed into the optional field. The fix is
therefore a real setting (`tempvoice_creator_name`) plus a repair path, not a
truncation bug fix: there was no truncation to fix.

### The moved bullets

- **Owner 2026-08-27 ~08:40, verbatim: "It's still not quite the look and
  feel I want. Can you research some other bot sites for inspiration and then
  make a mock"** → (1) research agent: Carl.gg, MEE6, Dyno, YAGPDB, Wick,
  ProBot, Sapphire dashboards — layouts, nav, module cards, colour, density,
  toggles → `info/dashboard-inspiration.md` with 2–3 candidate directions
  — **LANDED 2026-08-27:** [`info/dashboard-inspiration.md`](info/dashboard-inspiration.md)
  (11 sites surveyed; Carl, YAGPDB, Discord, Linear, Vercel/Geist and the
  Cloudflare dashboard read live, the rest marketing-only; three directions
  — A "Discord-native", B "Ops console", C "Cookout" — with dark+light
  palettes, self-hostable type stacks and ASCII wireframes; recommendation =
  A's shell + B's tables, mock A and C). **The four owner questions DECIDED
  2026-08-31 ~10:30 (asked one at a time): direction = "I want a A/C hybrid" ·
  "Both, dark default" · "Keep all 5 themes" · nav "Icons + text".** Step (3)
  unblocked: Fable writes the restyle brief (`info/site-restyle-design.md`),
  build queued AFTER the B4–B8 builder lands (both touch `site/`);
  (2) a design-canvas mock (artboards: Overview, a feature page, Settings) in
  the candidate directions for the owner to react to — **LANDED 2026-08-27 ~09:35:** canvas https://claude.ai/code/artifact/ad76df70-49f4-4fcd-a66a-07c8969d0ddd (A + C × Overview/Moderation/Settings, 1440×900, dark only; working `.dc.html` files live in the session scratchpad `mock/`, not the repo); (3) the winner becomes
  the site restyle brief (estate theme snapshot may be replaced — owner's
  call; site stays disconnected from heygabi).

- **Owner 2026-08-27 ~06:35, three asks (verbatim).** Asks (1) the site URL in
  the bot's bio and (2) the "Cookout attendees" status **landed 2026-08-27 —
  moved whole to [`DONE.md`](DONE.md)**. Still open: (3) "The ux is a lot of input boxes per
  page, maybe some page treeing and side tabs to make each page less dense,
  some search stuff, sections that condense" → batch 5 UX pass: per-page left
  sub-navigation (tree), collapsible sections (collapsed by default except
  the first), a search box on every table and on Settings, remember last tab
  + open sections, denser → grouped cards.

- **Owner 2026-08-27 ~06:30 on the dashboard, verbatim: "Website looks okay,
  ui good with options maybe slightly better ux".** → a UX pass (batch 5),
  aimed once the owner names what felt clunky (tabs / forms & saving / tables
  & filtering / sign-in). Candidate improvements regardless: remember the last
  tab, loading skeletons instead of blank tiles, inline save feedback next to
  the field, table search boxes, sticky nav, keyboard focus order, mobile
  layout check.

- **Owner 2026-08-27 ~06:00, verbatim: "would like a way to save a channels
  changed details so the next time the same user makes one it keeps their old
  name and set up".** Measured: already implemented for name, limit, lock,
  hide (+ bitrate in `6b75c11`) via `tempvoice_prefs` — saved on each change,
  re-applied in `_create_for`. **Batch 4:** also remember `region` and the
  permitted/banned member lists (TempVoice does), re-apply on spawn; `/voice
  info` shows what is remembered; `/voice reset` clears it. Owner confirmed
  `/help` and `/tempvoice status` work (2026-08-27 ~06:00).

- **Site sign-in VERIFIED by the owner 2026-08-26 ~23:00** ("i went to the site
  and i now see a health dashboard") — 8a fully closed.

- **8b MERGED and reconciled into `main` 2026-08-27** — `178fe69` (API) then
  `6bf4669` (pages), then one reconcile commit. **1105 tests, ruff clean**, and
  `node site/mock/check.mjs` reports 13 pages / 49 routes with every key the
  pages read present. ✅ **DEPLOYED since** — `178fe69` is an ancestor of the live
  commit `8036918` (2026-08-27 20:15); 8b first shipped in `5da62b3` at
  2026-08-27 06:14. *(Was "NOT pushed, NOT deployed"; corrected by the docs
  audit 2026-08-31. The mock now reports **17 pages / 89 routes**, not 13/49.)*
  Batch 3 (below) also merged.
  ⚠️ **NOT verified: any page against the real API in a browser** — only
  against the mock, whose shapes are now checked against the same table
  (`site/mock/contract.json`) the routers are. Nothing has run against live
  Discord. Open items from the reconcile:
  - **Nine shape mismatches were found and fixed** (see `DONE.md`); the fix that
    matters longest is `site/mock/contract.json` + the two checkers, because
    without it the next shape change drifts the same way silently.
  - `modlog`, `mod` and `carl` settings keys now serve in the **`automod`**
    namespace via `settings_api.py:NAMESPACE_OVERRIDE`. A new moderation key
    with a new prefix needs a line there or it grows its own one-key group.
  - Was: **8b dispatched 2026-08-26 ~23:05** (owner: "the who category … we need
    to resolve that to discord username. same with target … health can get
    shoved to a different tab but we need all the moderation tool menus"):
    design + API/page contract in `info/phase8b-design.md`; Builder A (API) and
    Builder B (pages, with a Node mock server) in parallel worktrees.

- **Test-sweep batch 4 LANDED on `main` 2026-08-27 and is DEPLOYED** (`47634b8` is an ancestor of the live `8036918`; verified 2026-08-31 — was "NOT pushed and NOT deployed")
  — three commits, all three owner asks done, **1173 tests, ruff clean,
  `node site/mock/check.mjs` clean**:
  - `47634b8` — **the incumbent bot and the parity tool are gone** (owner: "Carl
    bot has no actions or setup, lets remove the mentions and parity to it").
    `/automod parity`, `GET /api/mod/parity`, the dashboard's parity card, the
    mock route, the contract entry and the `carl_modlog_channel_id` setting all
    removed; `/rolemenu seed-from-carl` is now **`/rolemenu seed-defaults`** (the
    seed data is untouched). `grep -ri carl black_bloc site` is **empty**. The
    automod rules are unchanged — mention-spam armed, the rest log-only — and the
    **cut-over criterion is now the owner's judgement from the shadow log**
    (`info/feature-list.md`, F7). ⚠️ `SettingsStore.load` now ignores a stored
    row whose key has left the registry and warns once, so the live volume's
    `carl_modlog_channel_id` row cannot crash a start.
  - `7b487cf` — **temp voice remembers the whole set-up** (owner: "would like a
    way to save a channels changed details so the next time the same user makes
    one it keeps their old name and set up"). Schema **11**: `tempvoice_prefs`
    gains `region`, `permitted_ids` and `banned_ids` beside name/limit/lock/
    hidden/bitrate. `/voice info` now also lists what is remembered, and
    **`/voice reset`** forgets it.
  - `6f45299` — **favicon**. `site/public/favicon.ico` (a hand-written 32×32 ICO)
    plus a `<link rel="icon">` on all thirteen pages, so the `GET /favicon.ico
    404` on every page load stops.
  - ⚠️ **Owner test after the deploy:** `/rolemenu seed-defaults` (the old name is
    gone from the picker), `/automod status` (no parity line), then in a temp
    channel `/voice permit @someone` + `/voice ban @someone-else` + `/voice
    region us-west` → leave so it deletes → re-join the lobby and check the new
    channel has the same region and the same two people set; `/voice info` shows
    both halves; `/voice reset` clears it. And the dashboard tab icon.

- **Batch 3 MERGED into `main` `6b75c11` 2026-08-27** (see `DONE.md`) — the panel
  now posts into the test channel and `/voice` exists. **1134 tests, ruff clean,
  `node site/mock/check.mjs` clean.** ✅ **DEPLOYED** — `6b75c11` is an ancestor of
  the live `8036918` (verified 2026-08-31; was "NOT pushed, NOT deployed"). Still
  to do: review the merged `tempvoice.py`, then the
  owner tests the panel in `#mute-me-bot-test-spam` (press Rename and Lock from
  there — the click has to find its way back to the voice channel) and
  `/voice info` / `/voice bitrate` / `/voice region`. Owner also had the stale
  `🍯-do-not-post-here` trap deleted (2026-08-26 23:33) — `/honeypot setup`
  recreates it.

- **Test-sweep batch 2 FIXED on `main` and DEPLOYED** (was "NOT pushed and NOT
  deployed"; corrected by the docs audit 2026-08-31 — it is in the live
  `8036918`, and the owner confirmed `/help` works 2026-08-27 ~06:00) (see
  `DONE.md`, 2026-08-27): `/help` and temp-voice lobby adoption. Still to do:
  (a) run `/help` and `/help filter:temp` and check
  the `(staff)` marks, (b) run `/tempvoice status` — it should name any lobby it
  is not keeping track of — and `/tempvoice setup`, which should say it **took
  it over** rather than making a second channel.

- **Test-sweep findings, batch 1 (owner, 2026-08-26 ~22:55) — fixer dispatched:**
  (1) "we need a /rolemenu showall to display all role menus"; (2) "/twitch
  link it should say channel name not login, login sounds more concerning";
  (3) "it made a locked channel i cant get into. its just a lock icon" —
  measured: `/tempvoice setup` made a voice channel named **"join"** (name
  truncated) inheriting *The Basement*'s overwrites (`@everyone` deny connect;
  staff roles have view+manage but no connect) → nobody can connect. Fix =
  full name + explicit view/connect allows for the allowed role and staff on
  creator and spawned channels, and `setup` repairs in place. (4) TempVoice
  loop health + `@loop.error` (from the 8a merge).

- **OAuth redirect `https://black-bloc.fly.dev/api/auth/callback` saved by the owner 2026-08-26 21:38; `DISCORD_CLIENT_SECRET` in `.env` validated against Discord (client-credentials token issued).**

- **Decisions made autonomously 2026-08-26 ~21:20 (owner may overturn):**
  (a) `/untimeout` and `/unban` are refused while TEST_MODE, like the other
  destructive commands — lifting a punishment changes the live server and is
  access-increasing (global rule: confirm access-increasing actions); (b)
  `/settings show` is chunked to stay under Discord's 2000-char limit (43 keys
  after Phase 7); (c) Phase 8a dispatched in parallel since `wrangler login`
  landed. All three are in the Phase 6/8a fix or build briefs.

- **Q14 DECIDED 2026-08-26 ~21:55 — Option A:** the Fly app serves the site
  itself under ONE hostname (`blackbloc.heygabi.ai` → CNAME to
  `black-bloc.fly.dev`, DNS-only); no Cloudflare Pages; cookie stays
  `SameSite=Lax`. Owner's words: "seems cut and dry". Done on Fly 2026-08-26 ~22:00: cert requested
  (`flyctl certs add blackbloc.heygabi.ai`), IPs allocated (shared v4
  `66.241.125.10`, v6 `2a09:8280:1::17c:d6fb:0`). **Owner actions:** (1)
  Cloudflare DNS, proxy OFF: `A blackbloc → 66.241.125.10` and `AAAA blackbloc
  → 2a09:8280:1::17c:d6fb:0` (or `CNAME blackbloc → 3ppe323.black-bloc.fly.dev`);
  (2) Developer Portal → OAuth2 → add redirect
  `https://blackbloc.heygabi.ai/api/auth/callback` (keep the fly.dev one).
  **DONE 2026-08-26 ~22:25:** both DNS records added via the Cloudflare
  dashboard (Claude drove it; the owner's password-manager popup blocked
  keystrokes so values were set via form_input), public DNS resolves the A
  record, second OAuth redirect added by the owner. Remaining: `flyctl certs
  check blackbloc.heygabi.ai --app black-bloc` must say verified before the
  8a deploy (auto-validates once Fly sees the records). Known trade-off: if the bot process is down the page is
  down too (B would have shown an "API unreachable" notice) — accepted.

- **Follow-up from the 8a merge:** `TempVoice._reconcile_loop` records no loop
  health and has no `@loop.error` handler (checklist 28 gap on main) — add it.
  `site/README.md` points at the gitignored `docs/access/site.md` — either inline
  the deploy steps or accept.

- **Phase 8a unblocked (2026-08-26 21:10):** owner ran `npx wrangler login`
  (Cloudflare account `nbaslamking@gmail.com`, Node v24.11.1); `wrangler
  whoami` works from the session. 8a = read-only status page on Cloudflare
  Pages at `blackbloc.heygabi.ai` (design: `info/phase8-design.md`) — dispatch
  after Phase 7 merges, or earlier if the core queue stalls. Creating the Pages
  project + the DNS record happens at deploy time.

- **Fly secrets gotcha (2026-08-26):** piping python output into `flyctl secrets
  import` from PowerShell prepends a UTF-8 BOM to the first key name ("\ufeffTWITCH_…
  is not a valid secret name"). Write an ASCII temp file and redirect it with
  `cmd /c "flyctl … < file"`. → move to `access/deploy.md` (done below) and gotchas.

- **Back up `docs/` off this machine** — it is local-only now (RECOVERY gap).

- **Bot access RESOLVED 2026-08-26 ~18:00:** owner gave `Black_Bloc` the `Bots`
  role (carries Administrator — owner accepted: "it'll need to do moderation
  roles eventually"). Rescan then read 128/128 channels.

- **Role menus (new feature row needed at design time):** Carl's 5 reaction-role
  panels with measured emoji→role maps are in `archive/current-bots/discord-scan-2026-08-26.md`
  §D (gotchas: skin-tone emoji in text vs plain in reactions; 🧑‍🍳 is a ZWJ
  sequence). YAGPDB has NO role menus despite "7 role commands" on its dashboard.

- **Owner 2026-08-27 ~12:09, verbatim: "Stop at 90 weekly so we can save some headroom"** → project rule: no new agent dispatch at ≥ 90% weekly (global rule says 93); builds in flight land, nothing new starts; saved to memory. Status: **in force (weekly 83% at 12:02).**

- **Owner 2026-08-27 ~17:27, verbatim: "im getting on a plane tomorrow morning (friday and im not back until sunday night after reset) so we have wiffle"** → the 90% weekly stop is lifted for THIS window only (owner away Fri 08-28 → Sun 08-30 night; weekly resets Sun 16:00): spend the remainder on 12b now (parallel with 12a); at the Sunday reset, a one-shot wake-up resumes with the audit leftovers B4–B8 (temp-voice per-room actions, role-menu un-post/seed/staff-assign, event detail/edit) unless the owner has said otherwise. The 90 rule returns after the reset. Status: **12b dispatched 17:28 in parallel; Sunday 16:05 wake-up scheduled.**

- **Owner 2026-08-27 ~17:33, verbatim: "yes start keeping the docs up to date every task and creating our normal set of access docs. temporarily committ the docs folder so i can use it while away, and any scripts i'll need"** → `docs/` force-added and pushed as a TEMPORARY exception to the local-only rule (secret scan clean: names only); `access/runbook.md` + `access/sweeps.md` added; `scripts/doctools/move_done.py` committed (the folder was `scripts/docs/` until `7b7840b`, 2026-08-31 — it tripped the session-start docs-shape hook). Status: **committed + pushed 17:35. ✅ RESOLVED 2026-08-31: the owner chose to KEEP `docs/` tracked permanently** ("actually lets keep it tracked", `1eb8870`, which also dropped `docs/` from `.gitignore`); no history purge. The temporary exception is now the rule — see `DOCS_STANDARD.md` §9.

- **Owner 2026-08-27 ~17:37, verbatim: "committ anything i'll need. also i probably need a copy of the .env on my laptop… can we store the .env in a firebase or something safely and then write it to a local file with a script?"** → decided: no Firebase (a service-account key is a second secret to protect); `scripts/env-lock.sh` / `scripts/env-unlock.sh` (OpenSSL AES-256-CBC + PBKDF2, passphrase-only) committed; `.env.enc` allowed by `.gitignore`; the owner runs `lock` in their own terminal and commits `.env.enc` — Claude never handles the values. Laptop checklist in `access/runbook.md`. Status: **scripts + docs committed 17:40; the owner runs `sh scripts/env-lock.sh` and commits `.env.enc` before leaving.**

- **Usage 18:03 Phoenix: weekly 90% (session 16, Fable 33).** The 90 stop is reached; per the owner's away-window override the four in-flight builds (12a, 12b, 13a, 13b) land and get merged/tested/deployed; NOTHING NEW is dispatched before the Sunday 16:00 reset. Expect weekly ~94–96 after they land; merges/deploys are cheap. If a build dies on a limit: its commits survive in `.claude/worktrees/`, `git worktree list` shows them; resume from the Sunday wake-up.

- **Owner 2026-08-27 ~18:17, verbatim: "lets mute all the would calls too, keep that in discord logs"** → read as: every `would_*` (shadow) kind is ROUTINE — never posted to the Discord log channel under the default `important` level, always kept in the DB / website Logs / `/… logs`. Matches the Phase 12 design; pinned to 12a explicitly. (`all` per feature still shows them in Discord for a test sweep.) Status: **confirmed to 12a 18:18.**

- **Defect found by 13b (18:25), Sunday: the pager scroll-to-top does not work.** `ui.js:pager` — `#dash` `replaceChildren` resets the scroller to 0 before the helper runs, so its "already at the top" early return always fires; the page lands at the top of the PAGE, not the list (11b's "25923 → 276.67" does not reproduce). Fix: scroll AFTER the new rows render (requestAnimationFrame / after `onPage` resolves) to the list block's top minus the top bar, unconditionally. Affects Polls, Chat, Members, Requests. Also from 13b: outcome sentences render `**bold**` literally (one shared fix in `ui.js:run`); `foldout()` had no CSS since 10b (13b styled it); Requests page owes `await logsSection('request')` once 12b is merged. Owner 18:31: "fixs the defects now" → Status: **LANDED in `a4e7fcd`** on the integration branch (off `main` @ `16c5781`), after `641e53b` merged 13b. All three: `ui.js:pager` now scrolls unconditionally AFTER the rows render — two rAFs racing a 60 ms timer, because rAF does not fire in a backgrounded tab at all (measured: Requests 9340 → 930 with the list top at 8.18px, against 938.18px unfixed; Members and Polls likewise); `**bold**` becomes `<strong>` through `ui.js:boldParts` in `notice()`'s `say`, text nodes only, never innerHTML; `await logsSection('request')` is at the foot of the Requests staff view. `foldout()`'s CSS came in with 13b's own commit. **DEPLOYED** — shipped in `8036918`, live 2026-08-27 20:15 (`deploys.log`); status line corrected by the docs audit 2026-08-31. Not yet exercised by a person: see `access/sweeps.md` rows 14–17.

- **Owner 2026-08-27 ~18:28, verbatim: "no you're correct, just mak sure all decisions we make here can be configured in dashboard and with bot"** → (1) confirms the `would_*` muting reading; (2) standing rule: every decision is a registry key or has both a slash path and a dashboard control — added to `CLAUDE.md`, review-checklist item 33, and memory. Status: **rule in force; audit of existing decisions = every `*_mode`, `*_log_level`, poll/request/chat keys are registry keys; per-item fields have both paths (9a `/rolemenu edit` + 9b editor; 10 `/poll create` + create form; 13 `/request set` + board).**

- **Owner 2026-08-27 ~18:52, verbatim: "yes lets be done when this lands, we'll save the last 9% for bugs"** → after the integration build lands: merge, test, deploy, docs, STOP. The remaining weekly budget (~9%) is reserved for bug fixes only until the Sunday 16:00 reset; the Sunday wake-up (B4–B8 on fresh budget) stays scheduled. Status: **in force.**

- **Owner 2026-08-27 ~18:51, verbatim: "also in the logs we should add how someone has set a setting, if they set it in discord or on the website"** → the settings audit + Logs rows show **Via: Discord / website** — derived today from the kind prefix (`web.settings.set` vs `settings.set`), and made explicit as `details.via` on every write path (`/settings set-value` → discord, `settings_api` → website); `/… logs` lines carry it too. Status: **LANDED** on the integration branch. `logkinds.via_of` is the one home (recorded word wins, `web.` head decides the rest); `actionlog.log_action` stamps `details['via']` on EVERY row so no writer can forget, and the two settings doors pass it explicitly as well. `GET /api/actions` rows, the CSV and the Settings audit rows all carry `via`; the Logs table and the Settings audit table have a **Via** column; `/… logs` lines end `· via Discord` outside the 100-character cap. ⚠️ Residual, accepted: a website path that logs a BARE feature kind (`apply_decision`) reads Discord, with its `web.` twin beside it reading Website — settings have no such pair. **DEPLOYED** — shipped in `8036918`, live 2026-08-27 20:15 (`deploys.log`); status line corrected by the docs audit 2026-08-31. Not yet exercised by a person: see `access/sweeps.md` rows 14–17.

## 2026-08-27 — Phase 13: Requests (/request, member sign-in, the Requests page) + integration night fixes

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~17:42, verbatim: "we should also make a /request command so we can stop using the google doc, also put it on the website"** → F18 Requests: a `/request` slash (modal) that replaces the Google doc members currently fill, stored in the DB, listed/triaged on a dashboard **Requests** page (status open / accepted / done / declined, assignee, notes, reply to the member), with the same review pattern as events/role requests. **Owner ~17:46: "its just the initial doc that I gave you, its an idea on paper, we should make our request form more robust for sure. no need for name just collect who ask, get the what, the why, and a due date if needed. review can be on the site but its its a mod or higher auto approve it. have it go to a pending features list"** → F18 = feature-request intake: `/request` modal (What, Why, Due date optional; requester recorded automatically), status pending → approved → planned → in progress → done / declined; a mod-or-higher requester is auto-approved; dashboard **Requests** page = the pending-features list (filters, assignee, notes, decide, DM the requester). Design `info/phase13-design.md`. Status: **owner "just send them now… so when we get back we can go to work" (17:52) → 13a + 13b dispatched 17:53 in parallel off `40b7782` (weekly 89; owner override for the away window).**
- **Owner 2026-08-27 ~17:53, verbatim: "also let people put request on the dashboard too"** → the dashboard admits ANY signed-in guild member: non-staff land on a member-only **Requests** view (file a request, see and withdraw their own) with the staff nav hidden; staff keep the full dashboard; every other API route stays staff-gated. Relayed to 13a (auth: member sessions, `GET /api/requests/mine`, `POST /api/requests` member-gated + rate-limited) and 13b (member mode of the page, shell hides staff nav, gate copy). Status: **relayed 17:54 to both in-flight builders.**
- **Defect found by 13b (18:25), Sunday: the pager scroll-to-top does not work.** `ui.js:pager` — `#dash` `replaceChildren` resets the scroller to 0 before the helper runs, so its "already at the top" early return always fires; the page lands at the top of the PAGE, not the list (11b's "25923 → 276.67" does not reproduce). Fix: scroll AFTER the new rows render (requestAnimationFrame / after `onPage` resolves) to the list block's top minus the top bar, unconditionally. Affects Polls, Chat, Members, Requests. Also from 13b: outcome sentences render `**bold**` literally (one shared fix in `ui.js:run`); `foldout()` had no CSS since 10b (13b styled it); Requests page owes `await logsSection('request')` once 12b is merged. Owner 18:31: "fixs the defects now" → Status: **TONIGHT, immediately after 12a/13a land and the four branches are merged (the fix touches `ui.js`, which 12b and 13b also change) — one small Opus build: pager scroll after render, `**bold**` rendering in outcome sentences, `logsSection('request')` on the Requests page; then deploy.**
- **Owner 2026-08-27 ~18:50, verbatim: "also the cyber punk theme on the dashboard hs strayed more from cyber punk and way more ito neon. copy the ones we use on other gabi platforms and tighten that up, we look like a neon circus out here."** → restore the estate's Cyberpunk palette (the values the other gabi sites use = the pre-neon block in `estate-theme.css` before commit `b936b96`), keeping the later nav-head / level-field tokens; drop the magenta headings and the extra neons; keep blue/cyan lead only where the estate has it. Status: **LANDED in `f10260d`.** `git diff b936b96^` over `estate-theme.css` is now nothing but the later `--et-nav-head-*` tokens and the note; cyan leads, yellow wears the headings and the wordmark, magenta is danger only, `--et-info` inherits the accent again, and `--et-focus-ring` was re-derived to cyan. ⚠️ Two LIGHT-mode contrast figures are below 4.5:1 (accent 4.46 on the page ground, heading 3.54) — they are the estate's own values and the neon set beat both; recorded, not quietly improved. **Still to deploy.**
- **Owner 2026-08-27 ~18:51, verbatim: "also in the logs we should add how someone has set a setting, if they set it in discord or on the website"** → the settings audit + Logs rows show **Via: Discord / website** — derived today from the kind prefix (`web.settings.set` vs `settings.set`), and made explicit as `details.via` on every write path (`/settings set-value` → discord, `settings_api` → website); `/… logs` lines carry it too. Status: **in tonight's defect-fix build.**

**Landed as Phase 13 + the integration night** (`info/phase13-design.md`): 13a merge `7343a03` (Opus ~424k, +130 tests; `/request create|list|withdraw|set`, schema 16, five `request_*` keys, `writes.member_dependency` on exactly three routes with a 10/min bucket, `auth/me` gains `member`), 13b built on its branch (Opus ~359k) and merged by the integration build `8036918` (Opus ~494k; 31 conflict hunks reconciled — the real router won the contract; 13b's 30-row fixture and member gating kept in the mock; `app.js`/`shell.js` kept both 12b's Logs and 13b's Requests). Same merge: request kinds classified + `request_log_level` (13th) + `/request logs`; command tree pinned at 35; pager now lands on the list (measured: Requests 9340→930 with the list top at 8 px; note rAF never fires in a background tab — a 60 ms backstop is what actually ran); `**bold**` rendered via text nodes; Logs section on Requests; **Cyberpunk restored to the estate palette** (`git diff b936b96^` on the theme file = only the later nav-head tokens; light-mode accent 4.46 and heading 3.54 are the estate's own sub-AA values, kept on purpose); **Via** column (Discord / Website) on settings audit rows, Logs rows and `/settings logs`, from `details.via` on every write path with the kind prefix as fallback. `main` 2158 tests + ruff green; `check.mjs` 17 pages / 89 routes. Deployed 20:15 Phoenix by Claude (`deploys.log`); **verified live:** 35 commands synced, logged in 03:14:49Z, `/health` ok, Requests page rendered signed in. Accepted residual (code-notes): a website decision that also logs a bare feature kind (`request.approved` beside `web.request.approved`) shows the bare twin as "Discord" — settings themselves are correct. **NOT verified live:** no `/request` filed by a person, no member (non-staff) sign-in seen, no DM, no `/request logs`; pager only measured in a backgrounded tab. Owner sweep in `access/sweeps.md`.

## 2026-08-27 — Phase 12: Logs — quiet Discord, loud website, /… logs everywhere

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~17:14, verbatim: "i think we need to pipe a lot of the logs to the website and a logs command per function and keep the discord spam to a minimum"** → Phase 12 "Logs": (1) every action still lands in the DB (the action log already does) but the Discord log channel only gets **important** kinds — a per-feature `<feature>_log_level` (`off` / `important` / `all`, default **important**) with "important" = acted on a member (warn/timeout/kick/ban/role grant/approve/deny/expire) or FAILED; shadow `would_*`, housekeeping (imports with 0, panel reposts, reminders, sweeps, `chat.*`, `poll.created`) stay off Discord; (2) website: a per-feature **Logs** section on every feature page (recent actions by kind prefix, search, kind chips, pager) + a global Logs page (all kinds, actor/target filters, CSV export) — the Audit tab becomes that page; (3) slash `/<feature> logs [count]` (ephemeral, last N from the DB) on every feature group. **Decision (owner ~17:17): "a is fine, also any approvals need to make notifications still"** → default "important" = acted on a member OR failed; and every approval REQUEST (role requests, poll reviews, event proposals) still posts its card/ping to its approval channel regardless of log level — those are notifications, not log lines, and are never filtered. Status: **owner "send it now" (17:23, weekly 88 — overriding the reset hold) → 12a dispatched 17:24 off `0090fd8`; 12b when 12a lands if weekly < 90, else after the Sunday 16:00 reset.**
- **Owner 2026-08-27 ~18:17, verbatim: "lets mute all the would calls too, keep that in discord logs"** → read as: every `would_*` (shadow) kind is ROUTINE — never posted to the Discord log channel under the default `important` level, always kept in the DB / website Logs / `/… logs`. Matches the Phase 12 design; pinned to 12a explicitly. (`all` per feature still shows them in Discord for a test sweep.) Status: **confirmed to 12a 18:18.**

**Landed as Phase 12** (`info/phase12-design.md`): 12a merge `07fcea2` (Opus ~471k, +76 tests) and 12b merge `5fd44ae` (Opus ~365k), built in parallel on the owner's away-window override (weekly 89→91); mock-file conflicts resolved for the real router; `main` 2017 tests + ruff green; `check.mjs` 16 pages / 81 routes. Deployed 18:38 Phoenix by Claude (`deploys.log`); **verified live:** 34 commands synced (`/mod`, `/chat` new), logged in 01:38:07Z, `/health` ok; Logs page and per-page sections seen on the mock. **What shipped:** `black_bloc/logkinds.py` — 269 emitted kinds classified, 88 important / 181 routine, a test that fails on any unclassified new kind; every `.would_` kind routine BY RULE (owner 18:17); twelve `<feature>_log_level` keys (off/important/all, default important; `mod_log_level` namespaced to automod); the gate in `log_action` (row always written; Discord line only when `should_post` or `notify=True`; approval cards untouched — tested with `rolemenu_log_level = off`); `/<feature> logs [count] [important_only]` on twelve groups (per-guild top-level count 34/100, `/voice` 18/25); `GET /api/actions` gains feature/q/since/until/important/actor/target, paging, `kinds`, per-row `feature`/`important`/`summary`, 5000-row scan cap reported in `notes`, `export.csv` (not in the contract by design); dashboard `assets/logs.js:logsSection` on twelve pages + Settings, the Audit tab renamed **Logs** (file name kept), Overview's Last actions important-only, a 390 px overflow fix. Side effects worth knowing: `core` and `chat` have NO important kinds so they are silent on Discord by default; `golive` drops to failures only; a web approval can log two important lines (`web.poll.approved` + `poll.approved`) — pre-existing. 12a also re-keyed ~540 stale `path:line` references in code-notes (1045/1046 verified). **NOT verified live:** no Discord line has been observed suppressed or posted under the gate; no `/… logs` run in Discord; owner sweep = flip `golive_log_level` all → `/golive test` → back to important → `/golive test`, and `/golive logs`.

## 2026-08-27 — Phase 11: Chat 2 — editable intents and lines, data intents, routing, manners, the Chat page

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~14:12, verbatim: "yes lets do all of those,"** (F10 step 2, after being shown the canned lines and five suggestions) → build, in order, as one phase (`info/phase11-design.md` to write): (1) **Chat page** on the dashboard: intents with their trigger words and lines, add/edit/remove lines and whole intents (stored in a `chat_intents`/`chat_lines` table seeded from today's `chat.py` tables; the code table becomes the fallback); (2) **data intents**: who is live (open go-live sessions), what is next (next approved event with a HammerTime stamp), birthdays (next few), how many of us (attendee count), my roles (menus the member can pick from), what time is that for me (F4 timezone conversion); (3) **routing**: "I need a mod" / "help me" → opens or explains modmail; (4) **manners**: `chat_ignore_channels` setting, optional emoji reaction instead of a reply to a bare greeting (`chat_greeting_reaction` on/off); (5) later: the real conversation backend behind `reply_for`, persona prompt built from the lines. Status: **owner "Do it" (~15:55) → 11a dispatched 16:09 off `ebf99a2`; owner "Dispatch anyway" (16:18, weekly 87 — overriding the headroom hold) → 11b dispatched 16:19 in parallel off `ebf99a2`, building against the design's routes + its own mock entries; contract/mock conflicts expected at merge.**

**Landed as Phase 11** (`info/phase11-design.md`): 11a merge `dc4985c` (storage schema 15 `chat_intents`/`chat_lines` with a `slot` column filled/empty/attendee, per-guild seed of 15 intents with the code tables as fallback, classification over guild rows, six data intents, `need_a_mod` routing, manners settings, `/api/chat` eight routes; Opus ~399k, +122 tests) and 11b merge `e03176b` (the Chat page — Try it, per-intent cards with trigger chips and inline lines, New intent, settings section; Opus ~299k) built IN PARALLEL on the owner's "Dispatch anyway" (weekly 87→88); the two halves met on a six-point contract clarification relayed mid-build (`tokens` per intent, `message` on writes, settings row shape, bool manners keys, route precedence for "help me", contract fixture ids). Conflicts at merge: exactly the two mock files, resolved contract = 11a's (router truth), `server.mjs` = 11b's (page-validated) + one action-kind rename to `web.chat.line_deleted`. `main` 1941 tests + ruff green; `check.mjs` 16 pages / 80 routes after the mock `try` gained `slot`. Deployed 17:05 Phoenix by Claude (`deploys.log`); **verified live:** chat cog loaded, `chat: seeded 15 intent(s) for guild …` in the Fly logs, 32 commands synced, `/health` ok. Deviations recorded in code-notes: `reply_for` is now a coroutine (data intents read the DB) with `answer_for` beneath it as the step-3 seam; `GET /api/chat/intents` seeds a guild that has none (a write on a read, so the page is never blank); built-ins cannot be deleted, only disabled. **NOT verified live:** no @-mention answered from an edited line yet, no data intent asked in the server, no 👋🏿 reaction, no staff-channel route note; `time_for_me`'s bare "7pm = Phoenix" assumption untested on a person. Owner sweep: `@Black Bloc how many of us`, `who's live`, `what's next`; edit a greeting on /chat.html and say hi.

## 2026-08-27 — Phase 10: polls (native Discord polls wrapped, panel surface, recurring, Polls tab)

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~10:46, verbatim: "can we also have a poll app, copy polly or any other popular polling app in discrd"** → feature **F15 Polls** (already on the feature list as "Future (found)"). Step 1: research agent (Polly, Easypoll, Simple Poll, Discord native polls via discord.py `Poll`) → `info/polls-research.md` with a feature matrix and a recommended design; step 2: owner decisions one at a time; step 3: `info/phase9-design.md` + build (shadow-free feature, but test-channel only under TEST_MODE). **Research LANDED 10:58** → [`info/polls-research.md`](info/polls-research.md): Polly is a Slack/Teams product, not a Discord app — the Discord equivalents are EasyPoll / Simple Poll; Discord NATIVE polls (10 answers, 1 h–32 d, multi-select, live bars) are the free voting surface and discord.py 2.7.1 + our intents already support them; the paid features everywhere are the wrapper (scheduling, recurrence, reminders, history, export, dashboard) which Black Bloc already has patterns for; typed answers are affordable via 2.7.1's modal CheckboxGroup/RadioGroup except DATES (no picker anywhere in Discord → generated slots). Test-mode gap: `poll.end()` and interaction-response sends bypass the guard — the cog must check by hand. Build = two slices (9a native ~250–350k, 9b wrapper ~200–300k). ⏸ **15 owner decisions in §7, to be asked one at a time; first: answer types in v1.** Status: **all 15 decisions taken 12:16 (see the decisions entry below); design doc + build after Phase 9 lands.**
- **Owner 2026-08-27 ~10:49, verbatim: "also in that poll let them set a data type for the box so if they pick date or checkbox etc it changes how the poll functions"** → poll creation has a per-poll (or per-option) answer TYPE that changes the mechanics: choice (single), checkbox (multi-select), date / date-range (availability, When2meet-style), free text, number / rating scale, yes-no. Native Discord polls only cover choice + multi-select; the other types need Black Bloc's own buttons/modals/select menus. Folded into the F15 research + design. Status: **relayed to the research agent.**
- **Polls (F15) — owner decisions, 2026-08-27:** D1 answer types in v1 → **single choice, checkbox, yes/no, rating scale, date/availability** (free text, number, ranked = v2) — "Yes go with your rec" (~11:46). D2 who may create → **staff only** ("Staff only", ~11:53). D3 staff review before posting → **no by default, but a switch (`poll_review_mode` off/on) changeable from both `/poll settings` and the dashboard** ("Make polls need approval as no but should be editable in the bot and the ui", ~12:02). D4 default duration → **24 h**, per-poll override, 32 d ceiling ("24h", ~12:03). D5 anonymous votes → **the poll creator chooses per poll (anonymous on/off at creation)**; when on, the poll runs on Black Bloc's own panel (native polls expose voters) and the UI says so ("Let poll creator set if anonymous is allowed", ~12:04). D6 results visibility → **creator chooses per poll, default live**; "hide until close" forces the panel (native cannot hide) ("Also set by creator live by default", ~12:05). D7 channel → **the channel the command was run in**; `poll_channel_id` as the dashboard-create default ("Yes channel it was created in", ~12:06). D8 ping on open → **none by default; `poll_ping_role_id` setting + per-poll override** ("Yes your call", ~12:07). D9 reminder → **60 min before close, in the poll's channel, no ping; `poll_reminder_minutes`, 0 = off** ("Yes", ~12:08). D10 recurring polls in v1 → **yes, staff-only, daily/weekly/monthly** ("Yes", ~12:10). D11 weighted votes → **no** ("No", ~12:11). D12 reopen closed polls → **no** ("No", ~12:12). D13 auto-thread → **off by default, `poll_auto_thread` setting** ("Your call", ~12:13). D14 results retention + export → **after 365 days a poll is ARCHIVED, not deleted: the summary (question, options, totals, close date) is kept forever; per-vote rows may be dropped at archive time; archived polls sit in a collapsed "Archive" section on the dashboard with export still available; `poll_archive_days` default 365** ("Maybe not forever but like a year" then "Or we archive after a year but keep it", ~12:15). CSV export yes. D15 priority → **after the current phase; not urgent** ("Your call, it's not an urgent feature", ~12:16). **All 15 decided → design [`info/phase10-design.md`](info/phase10-design.md). Owner 13:37: "do polls" → 10a builder dispatched 13:38 off `6e08223`. **10a LANDED 2026-08-27** on branch `worktree-agent-aa83500e6aae1280f`, four commits `033e1c7` → `a0fe975` → `d3d1234` → `09d8654`: storage (schema 14, four tables), the pure module + ten settings keys, the cog (`/poll create|end|cancel|results|list|settings`, the review switch, the last-call + close + archive loop, the raw vote listeners) and the staff-gated API + contract + mock. `pytest -q` 1738 passed (1596 before), `ruff` clean, `check.mjs` 14 pages / 68 routes clean. ⚠️ **Not merged and nothing has run against Discord — no poll has ever been posted by this code.** ⚠️ **The `<t:…>`-in-an-answer-label question is STILL OPEN**: the library sends the label unescaped and the docs say nothing, so only a posted poll can settle it — 10b must post one in the test channel first. **10b still to do:** the panel surface (anonymous, hide-until-close, > 10 date slots, free text / number), recurrence, `POST /api/polls`, the dashboard tab (`polls.html` + `page-polls.js` + the nav entry) and the pager scroll-to-top from the 14:01 ask.**
- **Polls status 14:47:** **10a LIVE in `3eb7e4f`** (1738 tests, schema 14, 32 commands synced; no poll posted yet — owner sweep: `/poll create` each kind in the test channel, vote, `/poll end`, results embed). **10b dispatched 14:47 off `3eb7e4f`** (panel surface, date kind, recurring, `POST /api/polls` + dashboard tab, pager scroll-to-top). ⚠️ open: `<t:…>` inside a native answer label — 10b posts one test poll (message id in its report) for the owner to look at; `poll_date_labels` setting flips the label style either way.
- **Owner 2026-08-27 ~14:01, verbatim: "for each page that has pagination make sure on hitting next page it scrolls back to the top of the list"** → every pager (Moderation cases, Members, Audit, Health last-50 if paged, Modmail tickets, Role menus Requests/Timed roles, Birthdays by month if paged, Polls in 10b) scrolls the table/list top edge into view (`scrollIntoView({block: "start"})` on the table-block, minus the top bar height) after Previous/Next/page change, once the new rows have rendered; one shared helper in `ui.js` (the pager component) so every page gets it. Status: **queued into the 10b site build (10a owns no pages; 10b owns `site/`).**

**Landed as Phase 10** (`info/phase10-design.md`; design from `info/polls-research.md` + the 15 owner decisions taken one at a time): 10a merge `3eb7e4f` (storage schema 14, `black_bloc/polls.py`, the cog, the 5-min loop, raw vote listeners, review switch, results history, archive job, API; Opus ~391k, +142 tests) deployed 14:45; 10b merge `ebf99a2` (panel surface for anonymous / hide-until-close / date slots > 10, `kind:date` with generated slots, `/poll recur` daily/weekly/monthly, `POST /api/polls` + the **Polls** tab as the 15th page with create form / open / pending / closed / archive / recurring / CSV export, and the shared pager scroll-to-top from the 14:01 ask; Opus ~513k, +81 tests) deployed 15:44. `main` 1819 tests + ruff green; `check.mjs` 15 pages / 72 routes; 32 commands synced. **Measured:** discord.py 2.7.1 dispatches only the RAW poll-vote events reliably (non-raw need a cached message) — the cog listens raw only; the `guild_polls`/`dm_polls` intents were already on; the API stores `<t:…>` inside an answer label unescaped (test poll message `1542651824950218792` in the test channel) — **whether the client renders it is still for the owner's eyes**, so date labels default to plain text with `poll_date_labels` to flip; `RadioGroup`/`CheckboxGroup` cap at 10 options (a `Select` carries longer lists). Eleven `poll_*` settings; `poll_mode` on by default (no shadow: a poll punishes nobody); test-mode enforced by hand at every acting site because `poll.end()` and interaction responses bypass the patched send. Deviations recorded in code-notes: recurrence reuses `schedule_id` (no schema bump), `polls.auto_thread` per poll, cancelled→archived allowed, panel bars divide by distinct voters, anonymous votes stored as a per-poll truncated SHA-256 (**KI-9**). One shared CSS fix on the way: `.field > .seg { justify-self: start }` (segments had been stretching since 9b, visible on Role menus' Approval field). **NOT verified live:** no poll created by a person, no vote cast on either surface, no reminder/close/recurrence fired against Discord, no client render of the timestamp label seen, CSV never saved by a click. Owner sweep: `/poll create` each kind in the test channel; look at the test poll's first answer (renders as a date or as literal `<t:…>`?) and say which; vote; `/poll end`; results embed; dashboard Polls tab.

## 2026-08-27 — Owner verified live: @-mention replies and the go-live card

Owner, 13:59, verbatim: "we've tested @ing the bot, we tested golive we've not tested rolemenu yet". Supersedes the NOT-verified-live caveats in the entries "Black Bloc answers when @-mentioned" and "Go-live announcement is a card" above — both exercised in the real server by the owner. Still unverified live: Phase 9 role approval / timed roles / reconciliation (owner sweep pending), temp-voice panel in the voice chat, YouTube presence, daily import beyond the log line.

## 2026-08-27 — Two questions answered: no other bot imports to cron; the Live role already exists

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~09:53, verbatim: "are there any imports or stuff we're gathering from other bots as commands that we can turn into crons?"** → survey of every command that imports/gathers; answer in chat, decisions one at a time.
- **Owner 2026-08-27 ~11:24, verbatim: "also as a side feature lets add a way to dynamically assign a role like streaming when live (keep off for noww)"** → ALREADY BUILT in Phase 2: `golive_live_role_id` (F2 "optional *Live* role") — the bot adds the role when a session opens and removes it when the stream ends; it is off whenever the setting is unset (it is unset in production today). No build needed; stays off until the owner points the setting at a role. Status: **answered; nothing to do.**

**Answered, nothing to build.** (1) Imports/gathering from other bots as commands → only `/birthday import` existed (now a daily loop, see the entry above); the seven loops already cover Twitch polling, birthdays, events, presence, panels, visibility; setup/repair commands stay manual on purpose (a cron would fight the owner's deliberate deletions); F2's "scan for inactive streamers" is the one future cron-shaped item, still TBD. (2) A dynamic "streaming" role while live already exists from Phase 2 — `golive_live_role_id`, unset in production, so off exactly as asked; point it at a role in Settings to turn it on.

## 2026-08-27 — Go-live wording section owns the stream-end mode

Moved whole from `TODO.md`:

- **Follow-up found by the stream-end builder (12:39):** `site/public/assets/page-golive.js:140` previews the "once the stream ends" wording unconditionally; with `golive_end_mode` now off by default it previews an edit that will not happen. Fix: read `golive_end_mode` and show the preview only in `edit` (with a one-line "stream-end edit is off" note otherwise); `/golive status` should also print the end mode. Status: **Opus builder dispatched 13:19 off `271b42a`.**

**Landed:** merge `6e08223` (builder commits `607d268`, `2e4f58f`; Opus ~162k). `main` 1596 tests + ruff green; `check.mjs` 14 pages / 61 routes. Deployed 13:33 Phoenix by Claude (`deploys.log`); `/health` ok. The Go-live page's Announcement wording section now owns `golive_end_mode` as a segment beside "Playing a game": in `edit` the ended preview renders, in `off` one honest sentence replaces it; a missing key renders neither (checklist 10); the key is omitted from that page's accordion (one home per page) and stays on global Settings. `/golive status` prints `**stream end** — off (left as posted)` / `edit ("…")`, echoing the stored value rather than assuming. Mock gained the key and mirrors `NOT_A_FEATURE`. **NOT verified live:** the status line has not been read in a real ephemeral reply; browser check was mock-only, Chrome, Discord dark.

## 2026-08-27 — Phase 9: approval-gated role menus, timed roles, reconciliation (bot + dashboard)

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~11:12, verbatim: "todo: certain roles menus like runner-status we want to have be on approval basis, so you select a role and it pings a mod to approve it"** → role menus gain a per-menu (or per-option) **approval** mode: picking the role creates a pending request, pings the staff/approver role in the staff channel with Approve / Deny buttons (same shape as the events review queue), the member is told the outcome, the grant is logged; dashboard shows pending requests. Depends on role menus being switched back on (`rolemenu_mode` is off). Status 12:27: **9a LIVE in `a46b7ff`** (merge `e792bfa`; 1441 tests on the branch, 1565 on main; schema 13; `/rolemenu edit`, `/role grant`, `/role extend`, hourly `_expiry` loop, `on_member_update` reconciliation; withdraw = pick the pending role again). **9b pending** (dashboard: editor fields incl. per-menu channel, Requests + Timed roles sections, Members chip expiry, contract routes) — dispatch when the site polish builder lands. Owner sweep: make `runner-status` approval-gated with 7-day expiry via `/rolemenu edit`, pick it, approve, watch the DM; bot needs View Audit Log for the by-hand actor.
- **Owner 2026-08-27 ~11:16, verbatim: "we also need a recolciliation step so if someone is manually given a role it reflects on our portal and the bot knows"** → role reconciliation: (a) `on_member_update` listener records role adds/removes made by hand (audit-log actor when readable) into the role-menu/pick store and the action log; (b) a periodic sweep (hourly) diffs live guild roles against what the bot believes for every menu-managed role and fixes the record, never the member; (c) the Members page and Role menus page read the reconciled truth. Pairs with the 11:12 approval-mode ask — one role-menu design note covers both. Note: the Members tab already shows LIVE roles from the gateway cache, so manual grants are visible there today; the gap is the bot's own records. Status: **LIVE in `a46b7ff` (9a); dashboard view in 9b.**
- **Owner 2026-08-27 ~11:24, verbatim: "we also need a way for certain roles to be time limited. the same runner status roles. so we can set someone to have it for a week."** → time-limited role grants: a per-menu default duration (`expires_after` on the menu, e.g. 7 d) that staff can override when approving (and a `/role grant @user @role 7d`-style staff command + dashboard field); a `role_grants` table (member, role, granted_by, granted_at, expires_at, source: menu/approval/manual/staff); an hourly sweep removes expired roles, DMs the member, logs `role.expired`; extend/renew from the dashboard; the Members page shows "expires in N d" on the chip. Ties into the reconciliation ask (a manual grant of a timed role gets a record with no expiry unless staff set one). Status: **LIVE in `a46b7ff` (9a); dashboard Extend/End in 9b.**
- **Owner 2026-08-27 ~11:30, verbatim: "also in that same editor menu we need to be able to change which channels theyre posting in"** → the Role menus editor gets a per-menu **Channel** picker (the menu row already stores `channel_id`, set today only by `/rolemenu post`); saving a different channel on a posted menu takes the old panel down and posts it in the new channel (reuse `rolemenu_panels` reconcile), and the Post card shows the channel it will use. Status: **deferred to Phase 9b (the 9a builder is editing the role-menu files now).**
- **Role-menu approval — decisions (owner, 2026-08-27):** Q1 approval granularity → **"per menu"** (~11:20). Q2 who approves / where → **any staff role approves; requests post in a channel set by a NEW setting `rolemenu_approval_channel_id` (default = `staff_channel_id`), Approve/Deny buttons, optional ping role `rolemenu_approver_role_id` (default none)** — owner: "yes that works, just make sure we can set the channel where they post later in settings" (~11:22). Q3 pending experience → **ephemeral "Sent to staff for approval — you'll get a DM when it's decided", option shows as pending, pick again to withdraw, approve = role + DM, deny = DM with reason** (owner: "yes your choice is good", ~11:40). Q4 denial cooldown → **7 days per menu (setting), denial DM says when they can retry, staff can grant by hand any time** (owner: "yes go with suggested", ~11:41). **All four decided → design note `info/phase9-design.md`, then build.**

**Landed as Phase 9** (`info/phase9-design.md`): 9a merge `e792bfa` (bot, storage schema 13, API; Opus ~366k) deployed 12:26 in `a46b7ff`; 9b merge `271b42a` (dashboard; Opus ~416k) deployed 13:17. `main` 1592 tests + ruff green; `check.mjs` 14 pages / 61 routes. Both deploys by Claude under the owner's authorisation (`deploys.log`); `/health` ok; migration `added role_menus.retry_days` seen in the Fly logs; panels re-registered on boot. **What shipped:** per-menu `approval` / `expires_days` / `retry_days` (via `/rolemenu edit` and the dashboard editor), request cards with persistent Approve/Deny in `rolemenu_approval_channel_id` (default staff channel) + optional `rolemenu_approver_role_id` ping, pending/withdraw (pick again)/DM-on-decision, 7-day retry refusal sentence, `role_grants` for every bot-made grant with expiry, `/role grant|extend`, hourly `_expiry` loop (Health tab), `on_member_update` reconciliation (`role.changed_by_hand` with the audit-log actor when `View Audit Log` is granted) + hourly record sweep that never touches members; dashboard Requests (pending first, decided collapsed) + Timed roles (Extend / End now / Grant form) sections, sidebar pending count, per-menu **Channel** picker that moves a posted panel (`PUT /api/rolemenus/{name}` accepts `channel_id`), Members chips show "· N d" from `roles[].expires_at`. Two 9a design deviations recorded in code-notes: withdraw = pick the pending role again (a shared select cannot show per-member selection); decide-then-add ordering with `role.approve_failed` + no grant row if Discord refuses. Settings-store merge conflicts (keys added by parallel builds) resolved keep-both twice; `site.css` conflict (the level-field grid written twice) resolved for `main`'s measured version. **NOT verified live:** no request card, button press, DM, expiry or panel move has happened in the real server; the by-hand actor needs **View Audit Log** on the Bots role (unchecked); audit rows B5–B7 (un-post / seed / staff assign) remain open. Owner sweep: `/rolemenu edit runner-status approval:on expires_days:7` → pick → Approve (Discord or dashboard) → DM → `/role extend` → Members chip.

## 2026-08-27 — Stream-end edit is a setting, off by default

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~12:30, verbatim: "Let's have stream end announcement by optional and off by default"** → new setting `golive_end_mode` (off / edit), default **off**: when off the original announcement (sentence + card) is left untouched when the stream ends (the session still closes, the Live role still comes off); when `edit`, today's behaviour (suffix + "was live" card). Status 12:40: **merged `e5d890e`, deploying** — `golive_end_mode` off/edit default off; session still closes and the Live role still comes off; `api/status.py` excludes it from the feature-mode list (it names no feature).

**Landed:** merge `e5d890e` (builder commit `7e46a81`, Opus ~140k). `main` 1573 tests + ruff green. Deployed 12:42 Phoenix by Claude (`deploys.log`); `/health` ok. `golive_end_mode` enum off/edit, default **off**: at stream end the session still closes, the Live role still comes off and `golive.end` logs `"announcement": "left"`; nothing is fetched or edited unless the mode is `edit` (then byte-identical to before). Both end paths (`_end_live` and the reconcile/age-out `_close_session`) go through the one gate. Side fix: `api/status.py:mode_keys()` now excludes `golive_end_mode` (it names no feature) so the Overview would not grow a bogus "Golive_end" row. **Live behaviour change:** every guild gets the new default — set `golive_end_mode = edit` to get the old marking back. **NOT verified live** (no stream ended since deploy). Follow-up queued: the Go-live page previews the ended wording regardless of the mode (`page-golive.js:140`), and `/golive status` does not print the mode.

## 2026-08-27 — Site polish: neon Cyberpunk, sidebar headers read as headers, every field group level

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~11:08, verbatim: "the theme needs more neon blue and othe neon colors"** → assumed = the **Cyberpunk** theme (the one the owner was viewing; Discord stays the approved mock). Palette pass on `:root[data-theme="cyberpunk"]` (dark + light) in `estate-theme.css`: neon blue as the primary accent, a second/third neon (magenta, green) on ok/warn/info/pills/nav-active/focus ring, glow via `--et-focus-ring`/`--et-card-shadow`, keep contrast readable. Status: **site polish builder dispatched 11:59 (item 1).**
- **Owner 2026-08-27 ~11:27, verbatim: "for the headers on the left side on the webite, its hard to tell which ones are header and which are clickable. make the headers bigger and maybe bold"** → sidebar group headers (OVERVIEW / MODERATION / COMMUNITY / SERVER / ON THIS PAGE): bigger (body size rather than micro), bold, higher-contrast colour, more space above; clickable items stay as they are so the two read differently at a glance. Token-only (`--et-nav-head-size/-weight/-color`) so every theme follows; Discord theme deviates from the mock here ON PURPOSE (owner call). Status: **site polish builder dispatched 11:59 (item 2).**
- **Owner 2026-08-27 ~11:29, verbatim: "the editting a menu page on the website on the rolemenu has offset boxes, name, title, desc mode are not level"** → Role menus page, "New menu / Editing X" editor (`page-rolemenus.js` `editor`): the Name / Title / Description / Mode fields sit at different heights — align them on one grid row (labels above, controls level; the textarea gets the same top edge; wrap to two rows at phone width). Status: **deferred to Phase 9b (the 9a builder is editing the role-menu files now).**
- **Owner 2026-08-27 ~11:44, verbatim: "go ahead and make sure every set of text boxes that are next to each other are all level, it seems to be around when there are subtext beneath or above the box that pushes the default offline"** → site-wide: every side-by-side field group (`.field-row` / form grids in `ui.js` `field()` and the page-level forms — Role menus editor, Birthdays set form, Moderation action form, Modmail snippets/blocks, Events settings, Go-live link form) uses one shared layout: CSS grid with `grid-template-rows: auto auto auto` (label / control / help) and `align-items: start` (or subgrid where supported), so a field with help text above or below no longer pushes its control off the line of its neighbours; the control row is what aligns. Token-only. Add a mock-server check page or a test that renders each form and asserts the controls share a top edge. Supersedes the 11:29 role-menu-editor item (that becomes one instance). Status: **site polish builder dispatched 11:59 (item 3).**

**Landed:** merge `c176cd2` (builder commits `b936b96` neon, `8424c60` nav heads, `6b7ab62` level fields; Opus ~243k). `main` 1565 tests + ruff green; `check.mjs` 14 pages / 54 routes. Deployed 12:33 Phoenix by Claude (`deploys.log`); `/health` ok; Fable eyeballed Moderation + Role menus in Cyberpunk on the mock before merging. **Measured:** Cyberpunk changes confined to its two theme blocks (18 hunks between old lines 718–858) + one cyberpunk-scoped wordmark rule; contrast table in `info/code-notes.md` § "site polish" — every text role ≥ 4.5:1 in both modes, every light-mode figure better than before; accent `#3d8bff`, headings `#ff3df0`, ok `#2bff88`, yellow kept only for warn, old cyan became info. Nav heads: four new tokens at all 13 sites, each theme's head one size step above its nav item, bold. Field alignment: 19 → 28 groups measured, misaligned 12 → **0** (worst had been the Role menus editor at 40 px and modmail at 92 px); root cause `.formrow { align-items: flex-end }`; fixed at the shared `field()`/formrow grid (subgrid + explicit-rows fallback), plus the UA checkbox margin and one `.bar` offset. **NOT verified live:** only Chrome; four of twelve theme×mode pairs by eye (the rest by computed style); no label-wrap case provoked; contrast computed from hexes, not sampled pixels.

## 2026-08-27 — Stream-ended wording setting, no prefix-command noise, dark-skin emoji

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~11:53, verbatim: "Make black bloc use dark skin emotes"** → every human-gesture emoji the bot sends (wave, thumbs up, clap, raised hands, flex, pray, point, ok-hand, and people emoji) carries a skin-tone modifier — default **dark 🏿** (`U+1F3FF`), with `emoji_skin_tone` setting (none / medium-light … dark) so it can be tuned; one helper `black_bloc/emoji.py` (`toned("👋")`) used by chat lines, birthday/event/go-live/modmail copy and embeds; non-human emoji untouched. Sweep = grep every emoji literal in `black_bloc/**`. Status: **bot batch builder dispatched 11:59 (item 3).**
- **Noise in the logs (found 11:49):** `discord.ext.commands.errors.CommandNotFound: Command "hi" is not found` at 18:40:55Z — `commands.Bot` treats "@Black Bloc hi" as a prefix-command attempt (mention prefix) and logs the miss; the chat cog answers via `on_message` regardless. Fix: an `on_command_error` that swallows `CommandNotFound`, or a prefix that can never match. Status: **bot batch builder dispatched 11:59 (item 2).**

**Landed:** merge `a46b7ff` (builder commits `853aee3`, `ec7b345`, `046a54a`; Opus ~170k). `main` 1565 tests + ruff green. Deployed 12:26 Phoenix by Claude together with Phase 9a (`deploys.log`); verified: 31 commands synced, logged in 19:26:26Z, `/health` ok. (1) `golive.py:ended_text`/footer read `golive_end_suffix` — the key added by the site follow-up now has one home. (2) The "hi" noise: measured root cause — `command_prefix` was `when_mentioned_or("!")` with zero prefix commands in the tree, so every mention became a `CommandNotFound`; now `black_bloc/prefix.py:no_prefix_commands` returns `[]` and `get_context` never dispatches (`discord/ext/commands/bot.py:1319` `startswith(())` is False); reproduced both ways in tests; `settings.command_prefix` kept because modmail reads it to ignore other bots' commands. (3) Emoji: `black_bloc/emoji.py` (`SKIN_TONES`, `toned`, `toned_text`, `tone_for`, Unicode `Emoji_Modifier_Base` set) + `emoji_skin_tone` setting default **dark**; census of 47 literals found exactly ONE tone-capable output emoji (👋 in `chat.py`) — hearts, status glyphs, arrows and the user-configured role-menu emoji take no modifier by design; every chat reply passes through `toned_text` at send time so future lines get it for free. **NOT verified live:** no toned emoji seen in Discord yet (owner check = `@Black Bloc hi` → a 👋🏿 line eventually); button-label tone support is inferred from `PartialEmoji.from_str` round-tripping, not measured against the API; the modifier-base list was transcribed, not generated.

## 2026-08-27 — Dashboard: controls instead of displays, cache-busted assets, avatars, one sign-in check

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~10:31, verbatim: "on the website, in the go-live area, can we update the annoucement wording to be a changable text field instead of just a display. also audit all the ssite features. we dont want any displays showing what the bot can do, we want ways to interact and change."** → (1) Go-live page: the announcement template becomes an editable field (writes `golive_template` through the settings store, with the preview kept beside it); (2) audit of all 13 pages: every read-only "what the bot can do" panel becomes a control or goes. Audit landed → `info/site-feature-audit.md`. Status: **site follow-up builder dispatched 11:03 (items 3, 5, 8–12).**
- **Owner 2026-08-27 ~10:37, verbatim: "https://blackbloc.heygabi.ai/birthdays.html on this page make month day year all on the same line"** → the set-a-birthday form's month / day / year controls sit in one row. Status: **site follow-up builder dispatched 11:03 (item 6).**
- **Owner 2026-08-27 ~10:39, verbatim: "also every new page refresh is giving me the message, checking to see if oyure logged in, thats too much. it should happen on itial page load only"** → cache the last successful `/api/auth/me` result in `sessionStorage` (user, staff flag, checked-at); on later page loads render straight from the cache and re-verify silently in the background, showing the "checking" state only when there is no cache or the silent re-check fails (then the existing signed-out / not-staff gates take over). Never trust the cache for writes — the server still gates every call. Where: the gate text "Asking the bot whether you are signed in." (`site/public/*.html` `#gate-message`) shown until `app.js:158` `/api/auth/me` resolves. Status: **site follow-up builder dispatched 11:03.**
- **Owner 2026-08-27 ~10:41 asked what "Creator / tempvoice_creator_ids" is on the Temp voice page** → it is the list of join-to-create voice channels (the "join" lobby); the label "Creator" is unclear. Fix: human label "Join-to-create channels" with the help line "Join one of these and Black Bloc makes you your own channel" (`settings_store.py:181` help + the site label map). Status: **site follow-up builder dispatched 11:03.**
- **Owner 2026-08-27 ~10:46, verbatim: "do we even need the creator section? i dont get its usecase so lets rm it unless oyu can say why we need it"** → decision put to the owner (one question): the setting itself must exist (it is how the bot knows which voice channel is the lobby) but the dashboard section can go, with the lobby shown as one line on the Set-up card. Supersedes the 10:41 relabel note. **Owner 2026-08-27 ~10:52: "rm it."** → the Creator / `tempvoice_creator_ids` section comes off the Temp voice page; the Set-up card shows one line "Lobby: #join" with Set up / repair and Forget beside it. The setting itself stays (the bot needs it). Status: **site follow-up builder dispatched 11:03 (item 7).**
- **Found live 11:02 (Members page after the 188acf3 deploy):** (1) returning browsers rendered the page with a STALE cached `site.css` (name/username and role chips ran together, stat strip wrapped) — a hard reload fixed it: assets carry no `Cache-Control` and no version in their URLs, so every deploy shows old CSS/JS to anyone who visited before; fix = `?v=<build id>` on every asset URL + `Cache-Control: no-cache` (ETag revalidation) on `/assets`. (2) avatars are broken images: CSP `img-src 'self' data:` (`api/server.py:32`) blocks `cdn.discordapp.com`; fix = allow `https://cdn.discordapp.com https://media.discordapp.net` AND fall back to the initial letter on `img` error. Status: **site follow-up builder dispatched 11:03 (items 1–2).**
- **Site feature audit LANDED 10:50** → [`info/site-feature-audit.md`](info/site-feature-audit.md). 🔴 Found a live bug: Automod page Mode + Exemptions sections render `[object Object]` and save nothing (`page-automod.js:95,119`). The site follow-up build brief = audit A1–A8, B1–B3, B9, C1–C4, prose cuts + the queued asks (Birthdays one-line date, sign-in cache, Creator section per owner answer). B4–B8 held for a later batch.
- **Owner 2026-08-27 ~11:06, verbatim: "move the go live template from setting to the annoucement wording tab and let that be editable"** → same as the 10:31 ask; = site follow-up item 5 (audit A1 + C2): `golive_template` editor lives in "Announcement wording" with the live preview, and the row is REMOVED from the Go-live page's Settings accordion (it stays on the global Settings page). Status: **in the builder dispatched 11:03; reiterated to it.**

**Landed:** merge `a28e132` (twelve builder commits `adfb5e7`→`dab62c8`, one per item, Opus ~463k — the largest dispatch of the project; conflict in `cogs/core.py`/`tests/cogs/test_core.py` resolved by keeping `main`'s `/settings set-value` autocomplete from `8b8f792`). `main` 1425 tests + ruff green; `check.mjs` 14 pages / 54 routes. Deployed 11:55 Phoenix by Claude (`deploys.log`). **Verified live:** every asset URL carries `?v=<version>-<hash>`, assets `Cache-Control: no-cache`, HTML `no-store`, CSP `img-src` allows Discord's CDN, `/health` ok, logged in 18:56:12Z. Build id = package version + sha256 of `site/public` (not a git sha — the container has none); `?v=` cannot reach ES-module imports so `no-cache` is the real fix and the stamp the belt. Sign-in: `sessionStorage` cache, display only, server still gates every call; warm load never shows the gate (measured in the mock: `/api/auth/me` moved from first to last request). Go-live wording: textarea editor + live preview (ping role, `{platform}`, empty-game word, literal unknown tokens), omitted from that page's accordion, kept on global Settings; `golive_end_suffix` key added but `golive.py:ended_text` does NOT read it yet (next bot batch). Creator section gone; `Lobby: #… [Forget]` line via new `POST /api/tempvoice/forget` sharing `forget_creator` with the slash command (a shadowed `FORGOTTEN` constant found and renamed on the way). Audit rows A1–A8, B1–B3, B9, C1–C4 and the §4 prose cuts marked "Done in <commit>" in `info/site-feature-audit.md`; **still open there: B4** (temp-voice per-room actions, refactor first), **B5–B7** (role-menu un-post / seed / staff assign — 9b territory), **B8** (event detail/edit). **NOT verified live:** an avatar actually loading from the CDN in the browser; the gate behaviour in the real site (mock only); one Fly proxy `PU03 unreachable worker host` on `/assets/site.css` at 18:56:35Z during the restart — three follow-up fetches returned 200.

## 2026-08-27 — Black Bloc answers when @-mentioned (F10 step 1: canned intents)

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~11:33, verbatim: "we need to also add basic conversation and replies to the bot when people @ it and say hi, we can set up true covnersation"** → F10 step 1: an `@Black Bloc …` mention handler with a small intent table (greeting / thanks / how-are-you / what-can-you-do / help / unknown) and several canned lines per intent in the bot's voice, randomised, replying in-channel (guard: test channel + DMs only under TEST_MODE), per-user cooldown, `chat_mode` off/on setting (default **on** in test), logged as `chat.reply`; the handler is a single `respond(text, member) -> str | None` seam so a real conversation backend (LLM) can replace the intent table later without touching the cog. Note: message content for messages that @mention the bot arrives WITHOUT the privileged Message Content intent (builder to verify from discord.py 2.7.1). Status: **Opus builder dispatched 11:34.**

**Landed:** merge `1899f6e` (builder commits `047f48d`, `e0aa2d6`; Opus ~156k). `main` 1389 tests + ruff green. Deployed 11:48 Phoenix by Claude (`deploys.log`); verified: `loaded cog black_bloc.cogs.content.chat`, logged in 18:48:37Z. Shape: `black_bloc/chat.py` (pure: `classify`, `respond`, the `reply_for` seam for a future conversation backend) + `cogs/content/chat.py` (`on_message`: ignores bots/webhooks, needs the bot's mention, `chat_mode` on/off default on, guard checked first at debug level, per-user `chat_cooldown_seconds` default 20 stamped only after a reply lands, `reply(mention_author=False, allowed_mentions=none)`; only `insult` writes an action row `chat.insult`). Measured: a message that @mentions the bot carries `content` without the privileged intent (`discord/flags.py:1256–1262`), though `intents.py:9` already enables it for automod. Voice = first draft, 5–6 lines per intent, one emoji max, `unknown` → `/help`. **NOT verified live:** no reply has been observed in a channel yet — owner check = `@Black Bloc hi` in the test channel. Follow-up noted in TODO: `CommandNotFound: Command "hi" is not found` logged at 18:40:55Z when the owner @mentioned the bot before this shipped — the prefix-command dispatcher still treats "@bot word" as a command attempt (noise only).

## 2026-08-27 — Go-live announcement is a card: streamer, game and the game's art, no avatar

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~10:50, verbatim (with a screenshot of another bot's go-live embed — streamcord: author line "PopNoTarts is now live on Twitch!" with avatar icon, stream title as a link, a "Game" field, the game's box art as the image): "can we make our go live message show the streamer name and the game they're playing instead of their avatar"** → replace the plain-sentence post (+ Discord's link preview of the streamer) with an embed: title "{name} is now live on {platform}!", the stream title linking to the stream, a **Game** field, and the game box art (Twitch Helix `games` endpoint → `box_art_url`; YouTube: the stream thumbnail if known, else no image); the `golive_template` sentence stays as the message text above the embed. Status: **Opus builder dispatched 10:54 off `74f06b5`** — text stays the template sentence; embed = "{name} is now live on {platform}!" author (no avatar), title→stream link, Game field, box art via Helix `games` (cached) or the activity thumbnail, platform colour, end-of-stream edit; `golive_embed` bool setting (default on).

**Landed:** merge `8b8f792` (four builder commits `6a38357`→`b00521c`, Opus ~203k, reviewed by Fable: `announcement_embed` sets no `icon_url`/thumbnail anywhere). `main` 1329 tests + ruff green. Deployed 11:14 Phoenix by Claude (`deploys.log`); verified: 30 commands synced, logged in 18:14:32Z, `/health` ok. The card: author "{name} is now live on {platform}!", stream title → link, **Game** field (never blank — `GAME_FALLBACK`), image = Helix `games` box art (cached; a Helix failure degrades to no image, never blocks the post) or the presence asset; Twitch purple / YouTube red; footer names the source; end-of-stream edits the card to "was live" + "· stream ended". `golive_embed` bool (default on) restores the old sentence-only post when off. Side effect that had to land: the 26th value-typed key hit Discord's 25-choice cap on `/settings set-value`, so that command's `key` is now autocomplete (`cogs/core.py`). **NOT verified live:** the card has never rendered in the real client; the `/helix/games` shape and the `twitch:`/`youtube:` presence-asset prefixes are from docs/inference — owner check = `/golive test` (Twitch, then YouTube) in the test channel, then one real stream. Code-notes: the new section names `74f06b5` as the base; five already-keyed files moved lines and were NOT re-keyed (next docs pass).

## 2026-08-27 — Batch 7: themes restyle everything · Members tab · YouTube go-live · temp-voice panel in the voice chat

Moved whole from `TODO.md` (four owner asks, all landed in `188acf3`, deployed 11:00 Phoenix by Claude under the owner's 10:25 standing authorisation — `deploys.log`):

- **Owner 2026-08-27 ~10:18, verbatim: "make sure that the other themes work and dont just change the background color, make sure it applies to all CSS"** → audit `site.css`/`shell.js`-drawn CSS for anything the five old themes cannot override (font faces, radii, shadows, borders, control heights); every such value must go through an `--et-*` token that each theme sets. Audit 10:20 (measured live, Cyberpunk + Retro): colours and the body face switch, but cards, pills, radii, borders and the whole type scale stay Discord's — `site.css` hardcodes 64 `font-size` px, `border-radius: 4px`, 1px borders, weights/tracking. Status: **Opus builder dispatched 10:23 (Part 1 of a two-part brief, same worktree as the Members ask): tokenise everything, Discord keeps the mock values, each old theme sets its own; pass = computed-style table shows ≥4 old themes differing on face/radius/size.**
- **Owner 2026-08-27 ~10:18, verbatim: "also show server users, server user count also somewhere in the moderation area."** → a member count + a members list in the MODERATION group of the dashboard (likely a Members page or a panel on Moderation: name, joined, roles, case count). Needs an API route (`/api/members`, paginated, staff-only, from the bot's member cache). Design settled 10:22: `GET /api/members` (staff-only, search/filter/sort/paginate, cases count grouped, staff from `resolved_staff_roles`), a **Members** page under MODERATION with stat strip + B-style table, sidebar count, and a fifth **Members** stat on Moderation linking to it. Status: **Opus builder dispatched 10:23 (Part 2 of the same brief).**
- **Owner 2026-08-27 ~10:34, verbatim: "we also need to get youtube going live stuff too, go let the streaming activity work for youtube"** → the Discord streaming-activity detector (`golive.py`) must treat a YouTube stream the same as Twitch (Discord's Streaming activity carries `platform`/`url`); announce with the YouTube link; F3 in the feature list moves from "maybe" to decided. Finding 10:36: presence path is already platform-agnostic, but `_enrich` Twitch-looks-up any stream when the member has a Twitch link (can overwrite YouTube data), no `{platform}` template field, `/golive test` is Twitch-only, sessions may not store the platform. Status 10:53: **merged to main (`git log -1`), pushed, 1266 tests green on the branch; DEPLOY PENDING — ships with the temp-voice panel change in one deploy; first live check = owner runs `/golive test platform:YouTube` in the test channel.** Limitation for the owner: works only when Discord itself shows "Streaming on YouTube" (YouTube connection + activity display on). Was: (enrich only Twitch, `{platform}` field, platform on sessions/status/API, test command choice; YouTube API fallback out of scope — presence only).
- **Owner 2026-08-27 ~10:44, verbatim: "also lets move the controls for the join to create from the #test channel into the channel txt of the voice chat that was made like the other bot does it"** → the temp-voice owner control panel posts into the created voice channel's own text chat (`VoiceChannel.send`) instead of `#mute-me-bot-test-spam`; the test-mode guard gets a NARROW allowance for channels Black Bloc itself created (rows in the tempvoice table), nothing wider — this is the owner scoping the test policy, recorded here verbatim. Finding 10:39: `panel_home` already prefers the voice chat and only falls back to the test channel because the guard refuses it. Status: **Opus builder dispatched 10:40** — in-memory `owned_channel_ids` allowance on the guard (rows in `tempvoice_channels` only), restore on boot, prune on delete, interactions allowed there, copy updated.

**Landed, measured:** merges `7534d26` (themes + Members, Opus ~367k), `74f06b5` (YouTube, ~174k), `188acf3` (temp-voice panel, ~212k); `main` 1292 tests + ruff green with the venv; `check.mjs` 14 pages / 49 routes at `7534d26`. Themes: 25 tokens added at all 13 declaration sites; computed-style table shows ALL five old themes differ from Discord on font-family, radius and type size, and Discord proved unchanged by a 55-selector × 21-property diff (`info/code-notes.md` § "site — theme tokens"). Members: `GET /api/members` (search/filter/sort/paginate, cases grouped, staff from `staff_role_ids`, bots never staff), 15 tests, two real bugs caught by tests (undated members sorted first; mock's 'new' joins were 9 days old). YouTube: presence path proven platform-agnostic; `_enrich` gated by `twitch_enrichable`; `{platform}` template field; `golive_sessions.platform` column (schema 11→12, additive); a title-less stream rendered `{title}` as the platform name — fixed. Temp voice: guard `owned_channel_ids` allowance (only rows in `tempvoice_channels`), `allows_place` deliberately NOT widened, slash commands there still refused; bot grants itself view/connect/manage on spawned channels (hidden-channel lockout fixed). **Verified live after deploy:** `/health` ok, bot logged in 18:00:25Z, daily import ran, no log errors, Members page rendered signed in. **NOT verified live (owner sweep):** `/golive test platform:YouTube`; a real YouTube presence (only works when Discord itself shows "Streaming on YouTube"); a temp-voice panel appearing in a new channel's chat and a button press there — the Bots role needs Send Messages in that voice channel or the log shows `tempvoice.panel_failed`; a restart restoring old panels.

## 2026-08-27 — The dashboard is Direction A ("Discord-native"): new default theme, grouped sidebar, docked save bar

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~09:32, verbatim: "Lets go with A, keep this exact same design and implement it but make sure our existing theme selectors work"** → Direction A ("Discord-native") is the site look. Build: a new default theme `discord` (dark + light palettes from `info/dashboard-inspiration.md` §A) beside the five existing themes, the shell rebuilt to the mock (grouped sidebar, top bar with the cog, B-style tables, docked save bar, grouped settings), all token-driven so the five old themes still switch. Reference: the mock artboards are copied to `info/mock-direction-a/` (local only). Status ~10:20: **merged to main as `a60796c` (+ `666dd8e` copy fix for the daily birthday import), 1248 tests + ruff green, pushed; reviewed by Fable against the mock on the builder's mock server (Overview/Moderation/Settings match). DEPLOY PENDING — owner runs it (classifier refuses `flyctl deploy` in-session). After deploy: verify live in the Discord theme + one old theme, then move this item whole to DONE.** Polish noted, not blocking: the "On this page" sub-nav shows raw group keys (`core`, `birthday`) in lowercase; multi-select boxes (exempt roles/channels) look cramped in the 218px control slot.

**Landed:** merge `a60796c` (five builder commits `3412e40`→`e96b988`, Opus in a worktree, ~433k tokens) + `666dd8e` (Birthdays page copy no longer names the removed `/birthday import`). 1248 tests + ruff green with the venv interpreter (a first run used the system Python and failed on `discord` — run `.venv/Scripts/python -m pytest`). Reviewed by Fable against the mock on the builder's mock server: Overview/Moderation/Settings match. Deployed by the owner via `!` at 10:20 Phoenix (`deploys.log`); **verified live** signed in as the owner in the Discord theme. Mock reference kept at `info/mock-direction-a/` (local only); canvas https://claude.ai/code/artifact/ad76df70-49f4-4fcd-a66a-07c8969d0ddd (Direction A front page, Cookout parked on page 2). Deviations recorded in `info/code-notes.md` § "site restyle — Direction A": no `moderation_mode` key exists so that sidebar item has no dot; feature sub-lines use real counts or a plain sentence; stat strip counts the loaded page. **Follow-ups spun out as their own TODO items (10:18):** the old themes only repaint colours/faces under the new shell (tokenisation build), and the Members page. Polish noted, not done: "On this page" shows raw group keys in lowercase; multi-selects cramped in the 218px control slot.

## 2026-08-27 — `/birthday import` is gone; the Birthday Bot list is imported on a daily loop

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~09:39, verbatim: "lets hide the birthday import command and just put it on a daily cron. make sure you follow the A design as closely as possible"** → (1) the birthday import slash command comes off the tree and the import runs on a daily loop; (2) reinforcement for the in-flight Direction A build (brief already says pixel-exact; relayed to the builder as a narrowing note). Status ~09:52: **landed on main as `1b751b9` and pushed; 1248 tests green; DEPLOY PENDING — the deploy command was refused by the session's permission classifier twice, owner runs it (`! flyctl deploy --app black-bloc --ha=false --remote-only --yes`), then verify `/api/status` lists `_import_loop` and append `docs/deploys.log`.** Design: `/birthday import` removed, `import_rows` on a 24 h loop that also fires at startup, action logged only when something was imported, loop visible on the Health tab. Site builder was sent the "as close to A as possible" note.

**Landed:** `1b751b9` (Opus builder in a worktree, reviewed by Fable, fast-forwarded to `main`, pushed). 1248 tests green, ruff clean. Deployed by the owner via `!` at 10:00 Phoenix because the session's permission classifier refused `flyctl deploy` twice (`deploys.log`). **Verified live** in the Fly logs at 16:59:51Z: `_import_loop` ran 4 s after login — imported 0 / already 38 / ambiguous 0 / not_found 1 — so the seed is fully absorbed and only the one unmatched name remains. Loop health is on the Health tab by discovery (`tests/api/test_status.py`). Explanations: `info/code-notes.md` § "birthdays — daily import loop"; `info/phase5-design.md` Import section carries the superseded banner. **Residual:** `site/public/assets/page-birthdays.js:84` still says "The same import `/birthday import` runs" — one-line copy fix folded into the Direction A site restyle item (that builder owns `site/`).

## 2026-08-27 — Turning role menus off takes the panels down; turning it on posts them again

Moved whole from `TODO.md`:

- **Batch 6 item 3 (queued behind item 2), owner verbatim 2026-08-27 ~08:30:
  "Panels get turned off when off, I'll get the ux now, save role menu seed"**
  → OVERTURNS the "panels stay posted" default: on `rolemenu_mode` → `off`,
  delete every posted panel message (guarded delete; log `role_menu.unposted`
  per menu, keep `channel_id` so re-posting lands in the same channel, clear
  `message_id`); on → `on`, re-post every menu that had a channel (same
  persistent views), log `role_menu.reposted`. Menu rows, options and the
  seed data are NEVER touched by the switch. Driven by the same store change
  hook as item 2 (one trigger path), debounced with it.

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1243 tests pass (1221 before), ruff clean,
`site/mock/check.mjs` clean (13 pages, 48 routes).

- **`black_bloc/rolemenu_panels.py`** (new) — `reconcile(bot, reposting=…)`
  matches the posted panels to the stored mode, per guild. `off` → for every
  row with a `message_id`: guard check, delete the message, `message_id =
  NULL` (the `channel_id` stays), log `role_menu.unposted`. `on` → for every
  row with a `channel_id` and no `message_id`: guard check, `post_panel` (the
  same helper `/rolemenu post` and the web route use, so the same persistent
  view and the same `set_message`), log `role_menu.reposted`.
- **The guard is checked explicitly** because `guard.py` patches
  `send_message`/`edit_message`/`delete_channel` and **not** `delete_message`
  — a panel outside the test channel is refused and logged
  `role_menu.would_unpost` / `role_menu.would_repost` (checklist 1 and 2: a
  dry run and a failure never share a log kind).
- **One failure never aborts the sweep** — `discord.NotFound` means the panel
  was already deleted by hand and the row is simply forgotten; any other
  `HTTPException`, an unreachable channel, or an unexpected exception logs
  `role_menu.unpost_failed` / `role_menu.repost_failed` and the loop carries
  on to the next menu.
- **One coalesced run per flip** — the panel work is registered as a job on
  the **existing** `VisibilitySync` debounce (`controller(bot).also(job)`,
  run after the 5 s debounce and *before* the command sync, so panels are not
  held behind the 60 s sync rate limit). An `off → on → off` burst is one run
  and the last state wins, because `reconcile` reads the stored mode at run
  time rather than at flip time.
- **`on_ready` re-runs it one way only** (`panels_on_boot`): rows still
  holding a `message_id` while the mode is `off` come down, and nothing is
  ever posted at boot — a restart must not surprise the server with panels
  nobody asked for. It is also what arms the job (`PanelSync.ready`), so a
  cold channel cache in `setup_hook` cannot log failures for panels that are
  fine.
- **Menu rows, options and the seed are untouched** by the switch — asserted
  by a test that snapshots every menu and every option around an `off`/`on`
  round trip.
- **Wording** — the Role menus tab now says *"Turning this off removes the
  posted panels and hides the /rolemenu commands; turning it on re-posts every
  menu in its channel"*; `/rolemenu mode` and its `describe`, the
  `rolemenu_mode` registry help and the mock's copy of it all say the same.

**NOT verified:** any of it against a running bot — no panel message has ever
been deleted by this code, nothing has been re-posted, no guard has refused a
real delete, and the mode has never been flipped against live Discord.

## 2026-08-27 — The `/rolemenu` commands disappear while role menus are off

Owner ask, verbatim (~08:00): *"Can we suppress the / command for rolemenu too
toggle by ui"*.

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1221 tests pass (1206 before), ruff clean.

- **`black_bloc/command_visibility.py`** — a registry, `HIDDEN_WHEN_OFF =
  {"rolemenu_mode": ("rolemenu",)}`, mapping a mode key to the top-level
  command names to hide while that mode is `off`. `apply_visibility(bot)`
  removes them from the **dev-guild copy** of the tree
  (`tree.remove_command(name, guild=…)`, keeping the returned object so the
  put-back is the same `Group` with its cog binding) or re-adds them
  (`tree.add_command(command, guild=…, override=True)`), then sends **one**
  `tree.sync(guild=…)`, debounced 5 s and never more than once per 60 s
  (KI-2). Nothing changed → no sync at all.
- **`/settings` can never be hidden** (`NEVER_HIDDEN`) — it is the way back:
  `/settings set-value rolemenu_mode on`, since `/rolemenu mode` is hidden
  along with the rest of the group.
- **One trigger path** — `SettingsStore.on_change(key, callback)` (new) fires
  on every `set` **and** `clear`, so `/rolemenu mode`, `/settings set-value`
  and `PUT /api/settings/{key}` all reach the same code. `bot.py:61` registers
  it and applies once at startup, right after the initial sync.
- **`/help`** filters the tree through the registry, because hiding touches the
  guild copy and the global command would otherwise still be listed.
- **`commands.visibility`** action-log row per sync: resulting command count,
  what is hidden, and the actor who changed the setting.
- **Wording** — the dashboard's Role menus tab says the switch also hides the
  commands; `/rolemenu mode` says so as it flips; the "role menus are turned
  off" sentence now points at `/settings set-value rolemenu_mode on` rather
  than at a command that is no longer there.
- **Tests** — `tests/test_command_visibility.py` (11, all offline): a fake tree
  recording remove/add/sync; off at startup → removed + exactly one sync; on →
  untouched, no sync; three flips through the store hook → one sync; the same
  command object comes back; `/settings` never removed; the rate-limit window
  waited out; another guild ignored; no dev guild → nothing; a refused sync
  leaves the window open. One of them drives the **real** `CommandTree` with
  the real cogs loaded and only `sync` faked, which is where discord.py 2.7.1's
  `remove_command`/`add_command`/`copy_global_to` semantics are actually
  exercised. Plus two store-hook tests and two `/help` tests.

**NOT verified:** anything against a running bot or Discord — no command has
ever been removed from a live tree, no sync has been sent, nobody has clicked
the dashboard switch and watched `/rolemenu` vanish. The 5 s / 60 s figures are
asserted in tests, not measured against Discord's real rate limit.

**Moved whole from `TODO.md` § Open engineering items:**

- **Batch 6 item 2 (queued behind item 1), owner verbatim 2026-08-27 ~08:00:
  "Can we suppress the / command for rolemenu too toggle by ui"** → command
  VISIBILITY tied to the mode: when `rolemenu_mode` is `off`, remove the
  `rolemenu` group from the tree and re-sync the dev guild (rate-limit aware:
  one sync per change, debounced); when `on`, re-add + sync. Applied at startup
  from the stored mode and on every change (web toggle or `/settings
  set-value rolemenu_mode on`, which stays visible as the slash-side way back).
  Generic: a `hidden_when_off` registry so other features can opt in later.
  Log `commands.visibility` with the resulting count; `/help` reflects it.

## 2026-08-27 — Role selection turned off, with a switch to turn it back on

Owner ask, verbatim (~07:50): *"let's turn off all role selection stuff but do
it in a way we can turn it back on with ui."*

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1206 tests pass, ruff clean, `site/mock/check.mjs` reports
13 pages / 48 routes with every key present.

- **`rolemenu_mode`** — a new registry enum (`off`|`on`), **default `off`**,
  appended to `KEY_TYPES` so `mode_keys()` and the Overview chips pick it up
  with no change to either. Help: *"whether members can pick roles from the
  posted panels"*.
- **While off**, the self-serve select, the staff-assign select, `/rolemenu
  post`, `assign` and `unassign` all answer with one sentence and change no
  roles; `create`, `add`, `remove`, `show`, `showall`, `list`, `delete` and
  `seed-defaults` still work, so staff prepare menus while it is off.
- **`/rolemenu mode <off|on>`** (staff) flips it and logs `role_menu.mode`.
- **Web** — a first-section On/Off switch on the Role menus tab, reading
  `/api/settings` and writing `PUT /api/settings/rolemenu_mode`, repainting its
  chip from the stored value with no reload; the Overview chip for `rolemenu`
  now links to that tab. `POST /api/rolemenus/{name}/post` answers 409 with the
  same sentence while off, and the mock mirrors it.
- **Panels are LEFT POSTED** — the deliberate choice, so turning it back on is
  instant. Recorded in `info/code-notes.md` § "The off switch" and in the tab's
  own helper text.

**NOT verified:** anything against a running bot or the real API in a browser —
only pytest, ruff and the mock's contract check. Nobody has clicked the switch.

**Moved whole from `TODO.md` § Open engineering items:**

- **Batch 6 (dispatched 2026-08-27 ~07:55), owner verbatim: "let's turn off all
  role selection stuff but do it in a way we can turn it back on with ui"** →
  `rolemenu_mode` (`off|on`, default **off**): panels answer "turned off",
  `post/assign/unassign` refuse, CRUD still works, `/rolemenu mode`, an On/Off
  switch at the top of the dashboard's Role menus tab, Overview chip. Deliberate
  choice (overturnable): posted panels stay in place so turning back on is
  instant. Owner also asked "What's in batch 6" — it was empty until this item.

## 2026-08-27 — The Health tab finds every loop by itself (KI-7 closed)

**Supersedes the "finding worth keeping" in the presence entry below**, which
recorded the gap this closes.

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1195 tests pass, ruff clean.

- **`black_bloc/api/status.py`** — new `_loops(cog)` walks each cog's class MRO
  dicts and its instance dict for `discord.ext.tasks.Loop` instances and
  `getattr`s only those names, then asks `cog.loop_health(<attribute name>)` for
  the health beside each one. `dir(cog)` is still never called, so the
  property-that-raises hazard the old note named is still avoided.
- **`black_bloc/cogs/presence.py`** — `get_tasks` **deleted**. It was ours, not
  discord.py's, it was the only one in the tree, and a declaration only one of
  six cogs remembered to write is exactly the second home the discovery reader
  removes.
- **No mapping table was needed.** Every cog's `loop_health` already accepted
  its own attribute name: `Presence.status`, `GoLive.poller`,
  `Birthdays._sweep`, `Events._golive_loop` / `._reconcile_loop` (which strips
  the `_` prefix and `_loop` suffix itself), `TempVoice._reconcile_loop`,
  `Modmail._reconcile_loop`. **Seven loops, six cogs**, up from one.
- **`site/` untouched.** The per-loop shape is unchanged (`cog`, `name`,
  `running`, `failed`, `state`, `next_iteration`, `last_ok_at`, `last_error`),
  so `page-health.js`, the mock and `site/mock/contract.json` needed no edit —
  including the honest "this loop does not record its last success yet" text a
  blank `last_ok_at` still renders.
- **Tests.** `tests/api/test_status.py` now builds **real** `tasks.Loop` objects
  (a duck-typed double would no longer be found, so the old fakes would have
  passed while describing an empty page), and a parametrised test builds each
  real cog with the fake bot and asserts every loop it owns comes back from
  `/api/status` with the `last_ok_at` that cog records. A cog that grows a loop
  is one row in that table.

**NOT verified:** any of it against a running bot — no loop has ever been
discovered off a live gateway connection, and nobody has loaded the Health tab
against the real API. The residual, accepted in `KNOWN_ISSUES.md`: discovery is
by TYPE, so a loop held where `getattr` cannot reach it (in a list or a dict)
stays invisible. Nothing in the tree does that today.

## 2026-08-27 — The bot's own face: the site link in its About Me, and a "Cookout attendees" status

**The two asks, verbatim (owner, 2026-08-27 ~06:35):** (1) *"we should put the
url for the site in the bio of the bot"*; (2) *"The status of the bot should be
'Cookout attendees' then the number of server members"*. They arrived as items
(1) and (2) of a three-ask block in `TODO.md`; ask (3), the dashboard UX pass,
is still open there.

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1194 tests pass (1173 + 21), ruff clean.

- **`black_bloc/presence.py`** — the decisions, with almost no Discord in them:
  `status_text` (the `Cookout attendees: 412` sentence), `bio_text`,
  `human_count` (the guild's `member_count` minus the bots the cache can see),
  `status_guild` (the dev guild, else the first cached one), and the two
  appliers `update_status` and `ensure_bio`. Everything but the two appliers is
  pure and tested with no gateway.
- **`black_bloc/cogs/presence.py`** — the plumbing: the About Me written once
  per process on `on_ready`, the status re-applied on every `on_ready`, a
  10-minute `tasks.loop` with an `@loop.error` handler that restarts it, a
  5-second debounce on `on_member_join` / `on_member_remove`, and
  `/presence apply` (staff) to put both back by hand after a settings change.
- **Two registry keys**, both `text`: `bot_bio` (default renders the owner's
  sentence over `config.py`'s `site_origin`, so the hostname keeps one home)
  and `status_prefix` (default `Cookout attendees`). Both reachable from
  `/settings set-value` and from the dashboard's Settings page under **core**.
- **Health.** The cog reports `loop_health("status")` with `last_ok_at` /
  `last_error`, and defines `get_tasks()` so `api/status.py` can find the loop.

**The finding worth keeping.** `commands.Cog` in discord.py 2.7.1 has **no
`get_tasks` method** — verified at runtime (`hasattr(commands.Cog,
"get_tasks")` is `False`). `api/status.py:90` asks every cog for one, and none
of the five other loop-owning cogs defines it, so the dashboard's Health tab
currently lists **no loops at all**. The presence cog defines its own; the rest
are an open gap, not a fixed contract.

**Verified:** `AppInfo.edit(description=…)` exists in the installed library
(`.venv/Lib/site-packages/discord/appinfo.py:299`, `description` at `:304`,
added in 2.4), and `discord.CustomActivity` is there
(`discord/activity.py:760`). `change_presence` is a gateway op, so `guard.py`
neither sees nor needs to gate it — a status is not a channel, and it is
allowed to run in test mode.

**NOT verified:** any of it against a running bot. No About Me has ever been
edited by this code, no custom status ever set, `AppInfo.edit` has never been
called for real, and the 400-character description / 128-character status
limits are read off Discord's documentation rather than measured.

## 2026-08-27 — The Phase 8b security review's nine findings, fixed in two commits

**What:** two commits on `main` over `6b75c11`. **Not pushed, not deployed,
never run against a live bot.** 1178 tests pass (1134 + 44), ruff clean, and
`node site/mock/check.mjs` reports 13 pages / 49 routes with `MOCK_TEST_MODE`
at its **default** — which it could not do before.

**`5da62b3` — the three deploy blockers.**

- **CSRF (HIGH).** There was no Origin check at all: `SameSite=lax` does not
  stop a top-level form POST, so any other site could `<form method="post">` at
  `/api/mod/ban` and the browser would attach the session cookie. A middleware
  registered first (so it runs innermost, and its own refusal still picks up the
  security headers and the access log) now requires `Sec-Fetch-Site:
  same-origin` **or** an exact `Origin` match on every non-GET/HEAD/OPTIONS
  request under `/api`, **logout included, nothing exempt** — 403 `cross_site`
  with a sentence. It also requires `Content-Type: application/json` whenever
  there is a body (415 `not_json`), so a simple form POST cannot reach a handler
  even if the origin check were ever weakened; a bodyless request (logout, every
  `DELETE`) needs none, which is what `api.js` sends.
- **Caching.** Every `/api` answer carries `Cache-Control: no-store` and
  `Pragma: no-cache`, by assignment rather than `setdefault`. The page's assets
  are untouched.
- **Config.** `SESSION_COOKIE_SAMESITE` is `lax` or `strict` and nothing else
  (`none` would have left the new middleware as the only thing between another
  site and the cookie). `SESSION_SECRET` must be ≥ 32 characters or sign-in
  stays off with a plain warning — the cookie is an HMAC over a payload carrying
  the `staff` flag. `.env.example` says both.

**`3581eea` — the input guards, the read limit and the mock.**

- `purge_days` was `int(payload.get(...) or 0)` — a 500 on the word "seven".
  Guarded parse, bounded 0–7, refused **before** the guard check so junk cannot
  first record a `mod.would_ban` case and then fail.
- Role menu `PUT` wrote the heading, then walked the options, so a bad role in
  position two left a half-written menu. The whole body is validated first now;
  a non-dict option is a 400, not an AttributeError; `description` is coerced to
  `str` before it can reach sqlite, keeping absent / `""` / value distinct.
- Discord's 256 / 4096 / 100 / 25 live in the **cog** beside the SQL, reused by
  `create_menu`, `update_menu`, `add_option` and the API. They **refuse with the
  reason**, never truncate.
- A second `TokenBucket`, 300/min per session, on `/api/ref/*`, `/api/actions`
  and `/api/mod/cases`. And `TokenBucket`'s prune was O(n) per call and outrun by
  a spoofable header — it evicts the least-recently-used key in O(1) now.
- The mock refused a modmail reply and a warn that the **real API allows**;
  `check.mjs` now asserts the six genuinely-guarded routes 409 and those two do
  not, then flips the guard off through a new non-contract `/api/mock/guard` to
  read the shapes of the routes that refuse.

**Two existing tests changed, and why.** The bucket test asserted the dict
*shrinks* after a flood — true of the old sweep, false of an eviction cap; it
asserts the cap holds and the oldest key is gone. The `showall` paging test
built one menu with 100 options, which the 25-option limit refuses; it builds
four full menus instead and still spans several messages.

**Why:** `docs/info/code-notes.md`, "Phase 8b — the security review's fixes".

**NOT verified:** any of it against live Discord, or a real browser against the
real API. The same-site check is exercised through `TestClient` only, which
sends whatever the test says rather than what Chrome would send.

## 2026-08-27 — Batch 3 merged: the panel you can press in test mode, and `/voice`

**What:** one merge commit on `main`, `6b75c11`, two parents (`65dc85c` and
`af3dd55`). **Not pushed, not deployed, never run against a live bot.** The
branch `worktree-agent-aa87571126477eb8f` was cut from `9d948ca` and carried two
commits (`91c9c0b` the panel, `af3dd55` the `/voice` group). **1134 tests pass
(1105 + 29), ruff clean, `node site/mock/check.mjs` reports 13 pages / 49 routes
with every key present.**

Moved here whole from `TODO.md`. The ask, owner verbatim (2026-08-26 ~23:40):
*"in the join to create channel, i recall that bot we're mimicking having a way
to change the details of a channel in the chat associated with the voice
channel. can you do research then implement that."* The Phase 3 panel existed
but the guard suppressed it in test mode, so nobody could press a button until
test mode was lifted.

**What landed.** The panel is now posted **into the test channel** while guarded,
with a first line naming the voice channel it controls, and its buttons work
from there — which needed a new column, `tempvoice_channels.panel_channel_id`,
because `interaction.channel_id` stopped being the answer to "which channel is
this click about". Three outcomes, three log kinds: posted in the voice chat →
nothing extra, posted in the test channel → `tempvoice.panel_elsewhere`, no test
channel to post in → `tempvoice.panel_failed`. Unban and Unpermit joined the
panel (eleven buttons now), `tempvoice_prefs` grew a `bitrate` column, and a
`/voice` group of sixteen subcommands calls the same module-level `do_*` helpers
the buttons call — one implementation per action, not two.

**The merge conflict, and how it was resolved.** Both sides had restructured
`tempvoice.py` from the same base for different reasons. `main`'s batches 1–2
and the 8b reconcile had extracted the setup path to module level so the web
could call it (`make_creator_channel`, `repair_creator_channel`,
`adopt_creator_channel`, `creator_spot`, `where_sentence`, `may_act_in`,
`join_roles`, `same_lobby_name`, `lobbies_by_name`); the branch had extracted the
*panel* path to module level so the slash commands could call it (`Target`,
`temp_channel`, `panel_row`, `panel_home`, `get_row_by_panel`, `rate_limited`,
`already_message`, `move_out`, `pick_row`, `may_use_voice`,
`guild_bitrate_ceiling`, `clamp_bitrate`, `region_choices`, `member_lists`,
`mentions`, `info_lines`, eleven `do_*` helpers, and a `panel_context` that
returns a `Target`). Both were kept. ⚠️ **The branch's own `_repair` and
`_where_sentence` were DROPPED rather than merged** — `main` had already lifted
both to module level, and keeping the branch's copies would have been a second
home for each (checklist 15). Git auto-merged everything except two hunks;
`api/tools/tempvoice.py` still imports `connected_ids`, `make_creator_channel`
and `rows_for_guild` unchanged.

**Schema 8 → 10, and 9 is used rather than skipped.** Nothing on `main` had
claimed 9 (`main` was at 8; the other live worktrees are at 8 and 5), so the
branch's numbering stands: `panel_channel_id` is 9, `tempvoice_prefs.bitrate` is
10. Both are additive through `ADDED_COLUMNS` **and** present in `SCHEMA`, so a
fresh database and a migrated one agree.

**The docs gotcha, worth keeping.** The `### F8 follow-up` block in
`info/code-notes.md` carried a banner saying to re-key it after the merge and to
*trust the anchors, not the numbers* — which turned out to be the only usable
advice, because ⚠️ **its keys matched NEITHER branch commit.** Three of thirteen
(`:194`, `:200`, `:317`) were exact against `af3dd55`; most of the rest carried a
consistent **+170** offset against it, and none matched `91c9c0b`. A diff-based
re-key therefore produced confident, wrong numbers — `panel_context`'s note
landed on `return CANNOT_EDIT`. That block was re-keyed **by anchor**, function
by function, and every key verified one at a time against the merged file. The
main F8 block, keyed honestly against `65dc85c`, mapped cleanly (114 keys moved,
4 hand-repaired). Three notes described behaviour the merge removed and were
**rewritten rather than renumbered**: `_post_panel`'s "the panel is NOT posted in
test mode", the `would_post_panel` test note, and `db.py:11`'s "bumped to 8".

## 2026-08-27 — Phase 8b merged and reconciled: the API and the pages meet

**What:** three commits on `main`, **not pushed and not deployed**. `178fe69`
merges the API branch (`worktree-agent-aa75689d2dd1f44e7`, 53 routes, the name
resolver, the settings API, and plain-helper extractions in nine cogs);
`6bf4669` merges the pages branch (`worktree-agent-a1a9c6c08baf65618`,
`site/**` only, thirteen tabs and a Node mock); the third reconciles their
shapes. **1105 tests pass, ruff clean** (831 + 223 + 51 new contract cases).

**The one merge conflict, and how it was resolved.** Both halves had rewritten
`black_bloc/cogs/community/tempvoice.py`'s setup path from the same base and for
different reasons: Builder A extracted `make_creator_channel` so the web could
call it, while `main`'s test-sweep batches 1 and 2 had grown the remembered
lobby name, the join overwrites, repair, and adoption of a lobby the bot had
lost track of. **Both were kept, in one home**: the batch work now lives *inside*
`make_creator_channel`, with `repair_creator_channel` and `adopt_creator_channel`
beside it at module level; `setup_channel` defers and delegates; `_adopt` and
`_repair` are gone; `_may_act_in` and `_join_roles` delegate to module-level
`may_act_in` / `join_roles`. The behaviour change reaches the API too:
`POST /api/tempvoice/setup` now treats `repaired` and `adopted` as **successes**,
and the branch's `already_a_lobby` 409 went with the behaviour it described.

**The real work was the shapes.** The two builders coded blind against
`info/phase8b-design.md`, which fixes the JSON only for `/api/ref/*` and
`/api/settings`. Nine routes disagreed. ⚠️ **None of them would have thrown** —
they render as an em-dash, a blank tile or a badge that never appears, which is
exactly why they needed finding on purpose rather than by looking at a page:

| Route | What differed | Fixed where |
|---|---|---|
| `GET /api/mod/parity` | API nests the counts under `report` and has no `notes`; the page read `found.agree` and `found.notes` | **both** — page reads `report.*`; the API returns the command's own `parity_lines` as `notes`, so the "test mode is on" caveat has one wording |
| `GET /api/events` | API `decided_by_id`; page read `decided_by` | site |
| `GET /api/modmail/snippets`, `/blocks` | API `by_id`; page read `by` | site |
| `GET /api/modmail/tickets[/{id}]` | API `closed_by_id`; page resolved `closed_by` | site |
| modmail message `delivered` | API sends a bool; page tested `=== 0` | site |
| `GET /api/modmail/tickets` | page had a "Messages" count column the API never sends | site — column removed |
| `GET /api/settings/audit` | API `updated_by_id`; page read `updated_by` \| `by` | site |
| `GET /api/tempvoice/channels` | API `name`; page read `channel_name` | site |
| `POST /api/mod/{warn,…}` | API has no `id`; page printed "case ${found.id ?? 'written'}" | site — shows the API's own sentence |
| `PUT /api/rolemenus/{name}` | page's mode select offered only `multiple`/`single`, so saving a **staff** menu silently downgraded it | site — `staff` added |

**Two things the API gained, because the page needed them.**
`POST /api/birthdays/import` is the "import report" the design listed for the
birthdays tab and named no route for — Builder B correctly refused to invent an
endpoint, and it exists now because the cog already had the whole import trapped
inside the slash command, so `import_rows` and `members_of` were lifted to module
level the same way A lifted nine others. And parity's `notes`, above.

**Settings namespaces (owner decision at the merge):** `modlog_channel_id`,
`mod_dm_on_action` and `carl_modlog_channel_id` were served as three one-key
namespaces of their own, because the rule is "the prefix before the first `_`".
They are moderation keys, so they are folded into **`automod`** by an explicit
map, `settings_api.py:NAMESPACE_OVERRIDE`. Builder A's argument against a hand-kept
table — it goes stale when Phase 9 adds a key — is real and is written down beside
the map; the answer is that three lines in the one module that decides namespaces
beat handing somebody a settings page with groups called `mod`, `modlog` and `carl`.

⚠️ **The fix that outlives all of the above is `site/mock/contract.json`.** For
every route, the keys the pages actually read, derived by grepping the page
modules' property accesses rather than by restating the design doc. Both halves
read that one file: `tests/api/test_contract.py` runs it against the **real**
routers with fakes (51 cases, and a route that answers `[]` **fails** — a row
shape checked against nothing is a green test that never ran), and
`site/mock/check.mjs` runs it against the mock. So a shape can no longer be right
in one half and wrong in the other unless somebody edits one and not the file
both read. The mock was rewritten to be byte-compatible: bare arrays where the
API returns bare arrays, `*_id` name fields, flat ticket detail, `web.<area>.<verb>`
action kinds (it had been teaching `web.settings_set`), and `POST /api/mock/reset`
so each check starts from the same fixture.

**Verified:** `1105 passed`, `ruff: All checks passed!`, and
`check: ok - 13 pages, 49 routes, all keys present`. The mock's refusal paths
were smoke-tested by hand (409 under `MOCK_TEST_MODE`, 403 non-staff, 401
signed out). **NOT verified:** any page in a browser against the **real** API —
only against the mock; and nothing whatsoever against live Discord. The bot was
not run, nothing was pushed, nothing was deployed, and no worktree was removed.

## 2026-08-27 — Owner test sweep round 2: `/help`, and a lobby setup can adopt

**What:** two commits on `main`, not pushed and not deployed.

`/help` (`black_bloc/cogs/core.py`) answers the owner's ask verbatim — *"we also
need a / command that vomits out every /command that can be run"*. It walks
`bot.tree.get_commands()` **and** the guild-synced copies, merged by name, so a
guild-only command cannot be missing from "every command that can be run here";
recurses through groups and subgroups; renders `/group sub — description` one per
line under a bold heading per top-level command, sorted; chunks through the shared
`pages_under_limit`, first page as the ephemeral response and the rest as
ephemeral followups with `allowed_mentions=none`. An optional `filter:` narrows by
name or description and keeps a group's heading when the group itself matches; no
match gets a sentence, not an empty message. Staff-only commands are suffixed
`(staff)`, decided by `is_staff_command` in `settings_store.py` (one home, next to
`require_staff`): it reads the command body for the `require_staff` call and
follows **one** hop into a helper it calls — which is how `/warn` and the modmail
commands, gated in `_ready`, are marked — and leaves a gate further away
**unmarked rather than guessed at**, per the owner's instruction. That was chosen
over a decorator/`extras` marker on ~50 commands in nine files because a marker
goes stale silently the first time somebody forgets it, and reading the call
cannot.

Temp voice (`black_bloc/cogs/community/tempvoice.py`) now **adopts** a lobby it
lost track of instead of making a second one: when `tempvoice_creator_ids` names
no live channel, `/tempvoice setup` looks in the target category for a voice
channel whose name equals `tempvoice_creator_name` (stripped, case-insensitive),
stores its id **before** attempting the repair (the id is the durable half; a
rename Discord refuses must not undo the adoption), logs `tempvoice.adopt` as its
own kind, and repairs it in place with a sentence saying it took it over. Extra
matches are adopted too and named with `/tempvoice forget`, reusing the repair
path's existing sentence. `/tempvoice status` now lists every voice channel in the
target category carrying the lobby name whose id is **not** in the list, with the
sentence that fixes it.

**Root cause found for the duplicate lobby (finding 2a), and what could NOT be
established:** the write path has no gap. Both the Phase 3 original (`c3bf360`)
and the current command store the new channel's id immediately after a successful
create and before the reply, and the only two code paths that remove an id are
`/tempvoice forget` and the `on_guild_channel_delete` listener, which fires only
for a channel that really was deleted. So a lobby whose id is absent is one *this
store never saw created*: made by hand, made by a bot process reading a different
database (`DATABASE_PATH` defaults to a **relative** `data/black_bloc.sqlite3`, so
a local run and the Fly volume at `/data` are two different stores — measured
2026-08-27, the repo's own `data/black_bloc.sqlite3` has no `settings` table at
all), or one whose delete event removed it. ⚠️ **Which of those happened is NOT
established** — the live store is on the Fly volume and was not readable from this
tree, and the bot was not run (owner mid-sweep). What *is* established, and is the
real defect either way: the stored id was the **only** recogniser, so any lobby
the store did not know always produced a second one. It now has a second
recogniser.

**Tests:** 831 pass, ruff clean (817 before; 14 added). Changed tests: none
rewritten — the 14 are additions. New: the rendering of `/help` asserted as a
whole list (shape, sort order, `(staff)` suffix), the filter's three cases, the
chunking, the guild-only command appearing, and ⚠️ **the only test in the suite
that builds the real bot and loads every cog**, which is what proves the one-hop
staff detection on the real tree (`/warn` gates in `modcmds._ready`). Detection
tests in `tests/test_settings_store.py` pin the **limit** as well as the successes:
a gate two calls away reads `False` on purpose. Temp voice added the pure
name-matching function, adoption instead of a second channel, a channel with
another name being left alone, the id being stored even when Discord refuses the
rename, and status naming the strays.

**NOT verified:** anything against live Discord. `/help` has never been run in the
server, no lobby has ever been adopted, and the commands are not synced until the
next deploy.

**Commits:** `c47aa6f` (`/help`), `b430eb0` (temp voice). Docs: `info/code-notes.md`
re-keyed (98 keys moved across six files, one anchor repaired by hand).

## 2026-08-26 — Owner test sweep round 1: four findings fixed (not deployed)

**What:** `8fe0677` temp voice — `/tempvoice setup` now passes explicit
overwrites built from a copy of the category's own, adding `view_channel` +
`connect` for `tempvoice_allowed_role_id` (Member), for every **resolved** staff
role and for the bot (plus `manage_channels`/`move_members`), leaving `@everyone`
exactly as the category has it; spawned channels get the same allowed-role and
staff allows on top of the owner's. The lobby's name became a setting
(`tempvoice_creator_name`, default *join to create a channel*), and setup
**repairs** an existing lobby in place instead of refusing, gated on
`_may_act_in` because a rename is a side effect `guard.py` cannot see.
`_reconcile_loop` gained an `@loop.error` handler, `last_ok_at`/`last_error`,
`loop_health()` for `api/status.py`, and two lines in `/tempvoice status`.
`9d948ca` — `/rolemenu showall` (staff, every menu + every option, chunked
through the shared `pages_under_limit`, first page as the response and the rest
as ephemeral followups, `allowed_mentions=none` on all of them); `menu_heading`
and `option_line` extracted so `show` and `showall` cannot disagree, and `show`
gained the `allowed_mentions` it was missing while printing role mentions; and
`/twitch link` renamed its parameter to `channel` with no user-facing sentence
saying *login*, internal names (`twitch_login` column, `clean_login`, the log
detail key) deliberately unchanged.

**Why the `join` name was NOT a truncation bug:** measured, not guessed — the
cog has no string handling on the setup path, and the command's `name` parameter
introspects as optional with default `None`, so an unsupplied name renders the
full default. Discord must have sent `name: join`. The fix is a setting that can
be read back and re-applied, plus a repair path.

**Tests:** 817 pass (800 → 812 → 817), ruff clean. One test changed meaning:
*setup refuses a second lobby* became *setup repairs the lobby it already has*,
because refusing is what left the owner with a broken lobby and no way back.

**NOT verified:** nothing is deployed. No Discord API call was made and the bot
was never run — the owner was mid-sweep against the live instance. Deployment and
live re-verification are tracked in `TODO.md` under the round-1 sweep table.

## 2026-08-26 — Phase 8a live: the status site at blackbloc.heygabi.ai (Option A)

**What:** worktree build (`930248d` API auth + status routers, `6b1bdb0`
site — the builder rendered every refusal state in Chrome); Opus security
review → SHIP WITH FIXES (12 findings: cross-site cookie could never work on
Pages; `live_staff` failed OPEN for members who left; three 500 paths incl.
NaN latency; no rate limit; OAuth code in the access log; "could not check"
reported as "not staff"; no security headers); owner decision Q14 = Option A
(serve the site from the Fly app under one hostname); Opus fixer (`c211715`,
`50205dd`): StaticFiles mount, `__Host-` cookies, CSP/HSTS/nosniff, per-IP
rate limit via `Fly-Client-IP`, `staff_unknown` state, no CORS; merge agent
→ `618dcd1` (no conflicts; found and fixed the loop-health reader guessing
attribute names — Events' dict would have rendered as an error — via a
`cog.loop_health(name)` contract; `open_modmail` count added; dead
`api_origin` removed; `.env.example` corrected). 800 tests. Owner did DNS
(A/AAAA, proxy off — Claude drove the Cloudflare form via `form_input` after
a password-manager popup blocked keystrokes), both OAuth redirects; Fly cert
issued by Let's Encrypt; secrets staged via a self-cleaning script.
Deployed: `/health` 200, index 200 with CSP, Uvicorn on 0.0.0.0:8080,
bot logged in.
**Why Option A:** a `SameSite=Lax` cookie does not ride a cross-site fetch,
and `SameSite=None` is already blocked by Safari/Firefox partitioning; one
hostname removes the problem and every CORS line with it.
**Verified:** offline suite; HTTP checks against the live hostname. **Not
verified:** a real Discord sign-in round-trip — the owner's sweep.

## 2026-08-26 — Phase 6 live (shadow): moderation (F7) — the seventh and last core phase

**What:** worktree build (`6437d9f`, `fa6f6e8`, `71626c5`: pure rule
engine, shared `modcases.py`, automod cog, mod commands); Opus reviewer →
SHIP WITH FIXES (23 findings, top: a fired verdict re-fired on every later
message in the window — an apology would be deleted and timed out again;
Apply-now locked on the clicker not the case; parity could agree with
itself); owner decisions applied (raw mention counting, `/untimeout`+`/unban`
gated in test mode, `/settings show` chunked, arming refused while the staff
channel is the test channel); Opus fixer (`3c2beff`, `e85d9b5`); merge agent
→ `4677597` (6 conflicts incl. a genuine add/add on `tests/cogs/test_core.py`,
merged; duration parsers in events vs modcases documented as NOT
interchangeable — minutes vs seconds). 735 tests. Deployed: `synced 27 app
commands`. Architecture rule 5 gained the bounded-idempotent-rebuild
exception for the one non-additive schema step (`mod_cases.user_id` nullable).
**Why shadow beside Carl:** `/automod parity` is the cut-over number; Carl
stays armed until Bloc-only and Carl-only are both zero for a week.
**Verified:** offline suite; Fly log. **Not verified:** any real
delete/timeout/ban; Carl's modlog format is inferred from two shapes —
first parity run must be eyeballed.

## 2026-08-26 — Phase 7 live (disabled by default): modmail (F11)

**What:** worktree build (`b111a7f`, `0d7500c`, `c4e4777`); Opus reviewer →
SHIP WITH FIXES (16 findings: `/areply` leaked the staff role *colour*; the
bot DM'd strangers while modmail was off; transcript clamp counted chars
not bytes and a failed transcript still deleted the channel; nine commands
never deferred; no loop error handler); Opus fixer (`669440f`, `2cc9c02`);
merge agent → `088b107` (5 append-only conflicts, no one-home breaks;
Phase 7 already reused `events.clamp`/`slugify`, `golive.parse_ts`,
`timezones.stamp`). 628 tests. Deployed: `synced 17 app commands`.
**Why disabled by default:** the incumbent ModMail bot holds 5 live
tickets; Black Bloc says nothing until the owner flips `modmail_enabled`.
Channel mode (like today) is the default; thread mode is a setting.
**Verified:** offline suite; Fly log. **Not verified:** any DM relay,
ticket channel, or transcript against live Discord — owner's sweep.

## 2026-08-26 — Phase 5 live: birthdays (F6) — first parallel-worktree phase

**What:** built in an isolated git worktree while Phase 4 was on `main`
(`3978163`, `4c45f17`); Opus reviewer → SHIP WITH FIXES (12 findings — a
birthday *role* was granted even in shadow; removal used the current
setting's role, not the granted one; the import searched Discord by prefix
and could not match `[Tag] Name` nicknames); Opus fixer (`149c568`,
`6793c97`): mode-gated role add, `role_added_id` column, role taken back on
remove/optout, import scores against the cached member list (no network),
`/settings clear`, `#RRGGBB` colour validation, `importlib.resources` seed;
Opus merge agent → `08b114c` (4 conflicted files, all append-only; one
genuine break — a `sqlite_master` probe for Phase 4's table — removed as
a second home). 534 tests. Deployed: `synced 11 app commands`.
**Why worktrees:** owner asked for parallelism; a Docker deploy ships the
working tree, so builders must not share `main`. Shared files are touched
append-only and schema versions are pre-assigned per phase.
**Verified:** offline suite; Fly log. **Not verified:** the import against
the real 118 members (the report will say); any real embed.

## 2026-08-26 — Phase 4 live: events (F4/F5) + review fixes

**What:** Opus builder (`10ef099` timezones + `/timezone`, `039bb25`
events logic, `839cfff` cog: 5-field modal, `pending-user-event` review
channels, DynamicItem Approve/Deny, scheduled-event creation, go-live +
reconcile loops); Opus reviewer → SHIP WITH FIXES (14 findings: bare
`ValueError` from `ScheduledEvent.cancel()` would kill the reconcile loop
for the process's life; stale events announced late with a role ping;
retention deleted channels without the guard; the announcement promised an
Interested button that may not exist); Opus fixer (`63e1d15`, `8474f14`):
end-vs-cancel by event status, `@loop.error` + health on both loops,
missed/late handling with `events_max_late_minutes`, guard now gates
`delete_channel` via `allows_place`, `announce_text` truthful, requester
DM'd on every cancel, `AnswersErrors`/`SafeDynamicItem` mixins applied
across events/honeypot/tempvoice, two-miss reconcile, DST gap detection.
450 tests. Deployed: `synced 10 app commands`.
**Why the review card posts to the test channel in test mode:** the review
channel is not the test channel; the guarded send is the only way the owner
can click Approve/Deny during the sweep — it reverts to the review channel
when the guard is gone.
**Verified:** offline suite; Fly log. **Not verified:** a real modal, a
real scheduled event, a real rename against the 2/10-min limit — owner's sweep.

## 2026-08-26 — Phase 3 live: temp voice (F8), honeypot (F9, shadow), role-menu rider (F17)

**What:** Opus builder (`c3bf360` temp voice on schema v4, `6ed9f80`
honeypot, `9319560` role rider: Carl's real emoji, `staff` mode,
`runner-status`); Opus reviewer → SHIP WITH FIXES, 15 findings (HIGH: staff
exemption ignored category-inherited permissions — a Lead could be banned by
the trap; purge-days >7 would 400 every ban; threads bypassed the trap and
system messages could ban their author); Opus fixer (`85a7978`, `808686c`):
computed-permission staff derivation (one home, refuses to arm with an
empty set, status prints the resolved count), purge clamp 0–7 via
`delete_message_seconds`, message-type filter + thread denies, log-before-
answer in all eight panel handlers, defer-before-edit, claim/transfer lock
(on the bot object — module-level locks broke under per-test loops),
5-minute reconcile loop, claim requires being connected, `voice_states`
for occupancy, `forget` commands + channel-delete listeners, shadow-hit
dedupe, place-gated deletes. 288 tests. Deployed: `synced 8 app commands`.
**Why the panel is not posted in test mode:** a temp channel is not the
test channel; the guard would raise from the HTTP layer — logged as
`would_post_panel` instead. Checklist grew to 27 items.
**Verified:** offline suite; Fly log. **Not verified:** any real voice
event, channel creation, or trap post — owner's sweep.

## 2026-08-26 — Phase 2 live in shadow: go-live feed (F1/F2) + review fixes

**What:** Opus builder (3 commits `b635320` Twitch Helix client, `b2c0b39`
go-live logic + schema v3 + 8 settings keys, `ece5e3b` cog: presence
listener, 60 s Twitch poller, 120 s end-grace, `/golive`, `/twitch`);
Opus adversarial reviewer → **SHIP WITH FIXES** (13 findings, 5 blocking
before mode `on`); Opus fixer (`a680536` + `8579f3e`): reconcile open
sessions on start, unconditional role removal via `live_role_added`,
`golive.post_failed` distinct from `would_announce`, transport errors wrapped
as `TwitchError` + a tree error handler (`command_errors.py`),
`allowed_mentions` everywhere, per-user lock + partial unique index against
double-announce, poller health in `/golive status`, duplicate-login refusal,
guard now gates `edit_message`. 162 tests, ruff clean. Deployed; `synced 6
app commands`; Twitch enrichment confirmed on after the secrets import.
**Why shadow by default:** nothing reaches `#live-now` until the owner has
compared `would_announce` lines against YAG's real posts.
**Review learnings** → `info/review-checklist.md` (20 items), now in every
brief. **Verified:** offline suite; Fly log lines. **Not verified:** any
real presence event or Helix call — on the owner's test sweep.

## 2026-08-26 — Phase 1 live: settings store, action log, role menus (F16)

**What:** Opus builder, three commits (`7190855` settings store + schema v2
+ `/settings`, `81fe783` action log, `5c528c5` role menus + Carl seed);
Fable reviewed the select handler and staff derivation; 43 tests, ruff
clean; deployed to Fly — `synced 4 app commands`, logged in 01:30:00Z.
**Why these shapes:** one settings registry with typed keys and defaults
derived from TEST_MODE so nothing hard-codes a channel; `log_action` writes
the DB row first and never raises on the embed, so the log is the record
even when Discord refuses; role menus are select-menus (not reactions) with
persistent views re-registered on startup; the diff touches only the
menu's own roles, so posting our panels beside Carl's strips nobody.
**Builder deviations accepted:** `SettingsStore(db, settings)`;
`Database.is_connected`; `guard.refusal_message()`; `@everyone` excluded
from staff; seed does not pre-check assignability. **Verified:** offline
suite + the Fly log lines. **Not verified:** any click in Discord — on the
owner's test-sweep list in `TODO.md`.

## 2026-08-26 — Incumbent survey, feature list, seven phase designs

**What:** Two Opus research agents + Fable's own dashboard walk produced the
complete picture of what the server runs: `archive/current-bots/
discord-scan-2026-08-26.md` (128/128 channels, 12,488 messages, 60 roles),
`carl-bot-dashboard-…`, `yagpdb-dashboard-…`, `birthday-bot-export-…`, and
`info/reference-bots.md` (vendor docs for TempVoice, Honeypot, YAGPDB,
Carl, Birthday Bot, Modmail + Discord platform limits). Every owner decision
Q1–Q13 was asked one at a time and recorded in `TODO.md`. Output:
`info/feature-list.md` (F1–F16, build order approved) and
`info/phase1..7-design.md`.

**Why it took a rescan:** the first scan read 4/134 channels — the bot
lacked a role with View on the categories. Owner gave it `Bots`
(Administrator; accepted because moderation-role management is coming). The
first pass's *inference* that `#live-now` was human-posted was wrong;
measured: 199/200 posts are YAGPDB. Kept as the example of why inferences
get labelled.

**Findings that changed the design:** Birthday Bot fires at each member's
own midnight (15/16 land the evening before in Phoenix); Carl has exactly
one armed automod rule; YAGPDB has no role menus; three dormant bots incl.
two earlier attempts at this project; Discord exposes no user timezone;
EventSub needs a user token (websocket) or a public callback (webhook) — so
Twitch is Helix polling as a fallback, presence is primary.

**Verified:** all counts above are from the agents' reports and the saved
captures. **Not verified:** vendor-doc claims marked "(inferred)" or
"(from memory)" inside `reference-bots.md`; the Bash-tool Defender block
was diagnosed from `Get-MpThreatDetection`, not reproduced on purpose.

## 2026-08-26 — First Fly.io deploy; `/ping` confirmed by the owner

**What:** `flyctl` installed (winget `Fly-io.flyctl`), owner logged in from a
real PowerShell window (Claude's shells are non-interactive and `auth login`
refuses them), app `black-bloc` created in org *Sky*, 1 GB volume in `lax`
(there is no `phx` region), four secrets imported via stdin, `deploy
--ha=false`. Fly log shows `logged in as Black_Bloc#6132 … 1 guild(s)` at
2026-08-27T00:14:44Z on machine `85e744c4d959d8`. The owner confirmed `/ping`
worked against the local run just before ("ping worked").

**Why `--ha=false`:** Fly's default is two machines; for a gateway bot that
is two copies answering every command. One machine, one volume.

**Why `secrets import` over `secrets set`:** the token never appears on a
command line, in shell history, or in Claude's output.

**Verified:** login from Fly (log line above); `deploys.log` entry written.
**Not verified:** `/ping` against the *hosted* instance by a human (on TODO);
the machine surviving a Fly host restart with the volume intact (needs time).

## 2026-08-26 — First live login + test-mode gate + first commit/repo

**What:** Owner created the application, token, guild ID, invite and the three
privileged-intent toggles; the bot logged in as `Black_Bloc#6132` in *Black in
a Flash!* (1 guild) with `synced 2 app commands`. The owner's test-channel rule
became `black_bloc/guard.py` (`TEST_MODE`, `TEST_CHANNEL_ID`). First commit
made and pushed to a private GitHub repo under the owner's account.

**Why it took several runs — each run found a real defect that reading the
code had not:**
1. `DEV_GUILD_ID=` blank in `.env` → pydantic refused `""` as `int | None`.
   Fix: `before` validator maps blank → `None`; config errors now exit 2 with
   one plain line (`config.py:load_settings`).
2. Not-yet-invited server → bare `403 Forbidden` traceback from `tree.sync`.
   Fix: caught, logged with the invite URL (`bot.py:setup_hook`); the invite
   URL is built from `INVITE_PERMISSIONS` and logged before the gateway step.
3. Intents off → 40-line `PrivilegedIntentsRequired` traceback. Fix: mapped to
   exit 3 with the portal step named (`app.py:main`). Same for `LoginFailure`.
Lesson recorded in `info/gotchas.md`: run it, do not reason about it.

**Verified:** login, cog load, guild command sync, test-mode banner — from the
bot's own log, 16:57 Phoenix. 13/13 tests, ruff clean.
**Not verified:** the owner invoking `/ping` (left on TODO); the guard against
a *real* out-of-channel send (unit-tested only).

## 2026-08-26 — Project scaffold, venv, docs tree

**What:** Empty folder → runnable Python package `black_bloc/` (thin
`app.py` orchestrator, `bot.py` with cog loading + dev-guild command sync,
`config.py` on pydantic-settings, `storage/db.py` on aiosqlite, optional
`api/server.py` FastAPI health endpoint run inside the bot's loop), `tests/`
(config, offline bot+cog load, DB bootstrap, API health), `Dockerfile` +
`fly.toml`, `.venv`, and the seven-piece `docs/` tree with `DOCS_STANDARD.md`
copied from the estate.

**Why these choices (the part worth keeping):**
- **`discord.py` over hikari/nextcord/pycord** — largest ecosystem, first-party
  slash-command support (`app_commands`), cogs are the natural per-feature unit,
  and the estate has no existing Python Discord code to stay consistent with.
- **FastAPI over Flask** — the bot is `asyncio`; FastAPI runs in the same loop
  and can read bot state directly. Flask would need a thread and IPC. It is
  flag-gated (`API_ENABLED`) and OFF by default because no feature needs it yet.
- **SQLite (aiosqlite) over Postgres** — one process, one file, zero services
  to run; a hosted Postgres would be the first paid dependency for a bot with
  no data yet. Revisit when there is a second process or real write volume.
- **Not Cloudflare Workers** — owner's first thought for hosting, rejected
  because a moderation bot needs gateway events (messages, joins), which need a
  persistent websocket Workers cannot hold. Full reasoning: `info/hosting.md`.

**Verified:** `pytest` → 6 passed, `ruff check` → clean, both in the fresh
`.venv` (Python 3.12.10, discord.py installed 2026-08-26); `python -m black_bloc` with
no token exits 2 with a plain-English message instead of a traceback.
**Not verified:** anything against a live Discord gateway (no token yet); the
Fly.io deploy (not run).
