# Black Bloc — TODO (active work only)

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-09-11 11:50** (docs-pass findings (a)–(h) ALL closed, the item moved whole to DONE; (e) landed 11:39 `f4b17e5` — 123 inline `code-notes.md` refs re-keyed, 367 left as they were on purpose, residue filed as its own line; v110 live 10:14 — Event rooms: the room is owned so the event's posts land in it, a staff Delete this room button, `room_forgotten`, keys 206, 5593 tests, 151 routes, merge `9c6201d`; v109 live 09:29 — `requests.py` refusals name the card buttons, docs pass landed; v108 live 00:37 — Where follow-up 4: a shorthand becomes a link and the link is tried first, keys 202, 5546 tests, merge `73e2e44`; v107 live 23:41 — Where follow-ups 2+3: links look like links, test rooms go in minutes, keys 199, 5502 tests; v106 17:41 — a channel AND a link, keys 198, 5473 tests; v105 17:09 — the Where picker, schema 34, 5453 tests; v104 16:44 raid-train calendar-name key; v103 16:24 selftest purge 1 min; no agent in flight, no worktree; earlier 2026-09-03 11:45: v60 live, tree clean) — the 🔁 resume
> block below was refreshed then; first written 07:50 at the owner's order during API outages ("make sure if we lose progress and memory our docs survive");
> everything in it was measured at that time (`git log`, `git worktree list`, the live
> page, the deploys log). Earlier: 2026-09-02 handoff pass before the switch to Fable 5.1
> (schema **20**, **2610** tests, 17 pages / **107** routes, 37 sweep rows — those counts
> are now stale: schema **26**, **3345** tests, 17 pages / **139** routes at `c4420cc`).
>
> Finished items MOVE whole to [`DONE.md`](DONE.md) in the session they land.
> Accepted defects go to [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md), not here.

## 🔁 IF THIS SESSION DIES — resume here (refreshed 2026-09-11 11:50 — **the docs-pass findings queue is CLOSED**: (a) pings body restored 10:45, (b) Google SSO dropped 10:50 → KI-25, (c) KI-26, (d) checklist 35, (e) inline `code-notes.md` refs re-keyed `f4b17e5` 11:39 (residue on its own 🔎 line), (f) BOMs, (g) theme.js, (h) v110; item moved WHOLE to DONE; no agent in flight; tree clean and pushed; NEXT: nothing queued for Claude — owner-side sweeps 323–359 (351–359 need TEST_MODE), the 21-name rotation, Settings/Events pages in a browser; `theme.js` comment + nothing else waits on a deploy. Before that: **v110 LIVE 10:14** (merge `9c6201d` of `event-rooms`, Event rooms: the review room is `guard.own_channel`ed at creation + re-owned on reconcile so announce / go-live / ended land in the event's OWN room (`events_posts_where` room), a staff-only **Delete this room** button that cancels an open event with a DM'd reason (`events_room_delete_who`, `events_approver_role_id`, `events_room_notice`), `event.room_forgotten` clears a dead `review_channel_id`; keys 206, tests 5593, routes 151; item moved WHOLE to DONE; worktree + branch removed; no agent in flight; NEXT: the docs-pass findings queue — owner questions (a) pings-panel body DONE 10:45 and (b) Google SSO DROPPED 10:50 — both answered; engineering (c)–(g) need nobody; owner-side sweeps 323–359 + the 21-name rotation). Before that: **v109 LIVE 09:29** (`c9c73d8`, the `requests.py` refusal fix from the docs pass + `deploy.ps1` wraps flyctl in `cmd /c 2>&1`; docs pass A–F merged, `code-notes.md` re-keyed whole by `scripts/scan/rekey_code_notes.py`). Before that: **v108 LIVE 00:37** (merge `73e2e44` of `where-smart`, Where follow-up 4: a bare host is a link at render time, `ttv/skyaiva` / `yt skyaiva` become hrefs at entry through `events_where_link_aliases`, `linkcheck.py` tries the link once — `events_where_link_check` warn by default, `events_where_link_check_seconds` 2; keys 202, tests 5546; the item moved to DONE with the review's live-probe measurements; worktree + branch removed; no agent in flight; NEXT: nothing in flight — owner-side sweeps 323–350 and the 21-name secret rotation, then design D4 or the code-notes re-key sweep). Before that: **v107 LIVE 23:41** (merge `ac43a20` of `where-links`, Where follow-ups 2+3: a typed link is a masked link on draft + card with an **Open link** button on the card only (the draft's button was dropped at review — it came and went with Submit), `events_test_retention_minutes` default 5 while the guard is installed, denied/cancelled rooms count from `decided_at`; keys 199, tests 5502; both items moved to DONE; worktree + branch removed; no agent in flight; NEXT: nothing in flight — owner-side sweeps 323–342 and the 22-name secret rotation, then design D4 or the code-notes re-key sweep). Before that: **v106 LIVE 17:41** (merge `6c10b9d`, the Where follow-up: a channel AND a link, `events_where_link_in_description` default true, keys 198, tests 5473; item moved to DONE; worktree + branch removed; no agent in flight; repo PUBLIC 20:06, CI green again, the 22-name rotation is the owner's; NEXT: nothing in flight — owner-side sweeps 323–337 and the repo flip/rotation, then design D4 or the code-notes re-key sweep). Before that: **v105 LIVE 17:09** (merge `3205c0f`, the Where picker rebased onto the rewritten main; schema 34; tests 5453; item moved to DONE; worktree + branch removed; repo PUBLIC 20:06, CI green again, the 22-name rotation is the owner's; NEXT: the channel-AND-link follow-up, design then Opus). Before that: **v104 LIVE 16:44** (merge `b320031`, `raidtrain_scheduled_name_template` default `{title}`, keys 197, tests 5403; item moved to DONE; worktree + branch removed). Before that: **v103 LIVE 16:24** (`f9f5339`, self-test purge 1 min, boot line `purge in 1 min`; item moved to DONE). Where-picker Opus build DISPATCHED 16:20 in `C:/lcw/bb-where-picker` branch `where-picker` off `a47e43a` — if this session dies, check `git -C C:/lcw/bb-where-picker log --oneline a47e43a..HEAD` + status; finished = merge `--no-ff`, gate, deploy, docs ritual, remove worktree + branch. Before that: **v102 LIVE 16:14** (`3609b3e`, When-picker labels: `Start time — hour` / `Start time — minute` (v101, `b5f2288`) and `Date` (v102), owner asks 16:07 / 16:11; both records on `deploys.log`, both verified booted + selftest 107/0). **v103 shipping**: selftest purge default 5 → **1 min** (owner 16:13: "the test stuff posted each deployment should last 60s instead since it's mainly for you and not me") — `SELFTEST_PURGE_MINUTES_DEFAULT`, both registries, 3 tests, `selftest-design.md`, owner guide; ⚠️ if the live guild has an EXPLICIT stored `selftest_purge_minutes` = 5 the default will not bite — check the v103 boot line says `purge in 1 min`, else set it on https://blackbloc.heygabi.ai/settings.html. **Next**: the Where picker — design `info/where-picker-design.md` written 16:13, Opus build (est. 200–300k) NOT yet dispatched; brief = the design doc + `review-checklist.md` + TEST_MODE + worktree `C:/lcw/bb-where-picker` branch `where-picker` + commit often + `## Deviations`. Before that: v100 LIVE 16:00** (`1f35f28`, THE "WHEN?" PICKER: `/event` Propose and `/raidtrain` Start are draft panels with Day/Hour/Minute(/How long) dropdowns, a text modal that never refuses, a `ZonePanel` zone dropdown, and `{title} Feat. BaF` as the scheduled event's name — five settings keys in the Events group, 191 → **196**; 386k Opus build against 250–350k; +109 tests to **5395** both orders; sweep rows **323–327** are the owner's (327 needs TEST_MODE lifted); item moved whole to DONE; `code-notes.md` re-keyed by line diff `ef54e60 → 1f35f28` (203 keys) — the two `# Events` sections were a few lines off their anchors BEFORE the merge, by-anchor sweep filed below; the 15:55 detached deploy run deadlocked at 82% of pytest with idle workers — killed, 15:58 retry shipped; worktree `C:/lcw/bb-when-picker` / branch `when-picker` to remove; no agent running. **Open for the owner:** (a) should a raid train's scheduled event ALSO get the ` Feat. BaF` suffix (one more key `raidtrain_scheduled_name_template`, not built — the agent's question); (b) rows 323–327 by eye; (c) design D4: the website's Events / Raid-train create forms still take a typed `YYYY-MM-DD HH:MM` (own small item, on TODO). Before that: v99 LIVE 2026-09-06 20:00 — **v99 LIVE 20:00** (`88e0242`, operator read bound: the right token is bounded by the shared 300/min read bucket on the operator identity; 158k Opus build; +7 tests to 5286; row 322 drilled twice by Claude — 400-read bursts 308/92 and 305/95 with the right sentence; `pytest -m live` still 58/1; the 19:52 deploy run deadlocked at 81% of pytest with 33 idle workers — killed, 19:59 retry shipped; worktree/branch removed; no agent running. Owner-side: rows 320, 321 (sign-in half), 322 and 103's Logs half by eye. Before that: v98 LIVE 14:22, live suite green 58/1. Before that: LOGS BUTTONS (Q3 "3. B") + RECURRENCE CREATE FROM THE WEBSITE (Q2 "2. A") ✅ MERGED `42d2e6e` / `c915ade` 11:36 (244k + 274k; rows 305–314; +41 tests to 5267; keys 189 → 191; routes 149 → 150; moved whole to DONE) — **v96 ✅ LIVE 11:39** (`c915ade`; gate 27.9 s; boot `database ready` 18:39:07Z, `synced 29`, selftest 107 ok 0 failed, `/health` ready; deploys.log line filled). Worktrees and branches removed; the folder `C:/lcw/bb-logs-buttons` is left behind, held open by six stray bash shells from the agent harness — delete it whenever it lets you, nothing in it matters. v94 ✅ LIVE — deployed by the OWNER 11:13 (Fly v94 + v95 = the same `b428236`; both boots clean; lines filled in `69c267a`); the session's own 10:42 run hung at 92% of pytest and PIDs 19840/67456 were still alive at 11:37 — owner kills them, harmless otherwise. Q4 KI-24 ✅ DECIDED 2026-09-06 11:48, owner verbatim *"Build it a"* — build the loop guard bundled with the `Core.purge_loop` `db.is_connected` guard and the `POST /api/polls` `poll_mode` gate; design `docs/info/loop-guard-design.md`; agent `loop-guard` dispatched ~11:55 in worktree `C:/lcw/bb-loop-guard` off `c71ed21` (lands as v97). Q5 `OPERATOR_READ_TOKEN` ✅ DECIDED 13:33, owner verbatim *"A"* — MINTED 13:34 via `scripts/mint-operator-token.ps1` under the owner's standing permission rule: `fly secrets list` shows it **Staged** (64 chars); local `BLACK_BLOC_OPERATOR_TOKEN` set. Goes live with **v97** (the loop-guard deploy) — after that boot: `scripts/read.ps1 -Path /api/requests` from a NEW terminal, `pytest -m live` once, record the count in `docs/access/testing.md`, run sweep row 103, refresh the NOT-verified headers in `access/operator-read.md` / `info/operator-read-design.md` / `access/RECOVERY.md`. All five owner questions are now answered. **v97 ✅ LIVE 13:52** (`aa44e3b`; the 13:45 detached deploy HUNG at 88% of pytest like the 10:42 one — its tree, PID 70000 + ~33 pythons started 13:45:41–49, could not be stopped (classifier), owner kills it; the foreground `powershell -NoProfile -File scripts/deploy.ps1` run took 1 m 44 s and shipped it; boot `database ready` 20:52:18Z, `synced 29`, selftest 107 ok 0 failed, `/health` ready; `OPERATOR_READ_TOKEN` now **Deployed**). **FIRST OPERATOR READ EVER 13:54** — `scripts/read.ps1 -Path /api/requests` answered the JSON. `pytest -m live`: 20 passed / 38 failed / 1 skipped — two findings, built as the OPERATOR BUCKET fix and ✅ LANDED as merge `deaae68` (moved whole to DONE). **v98 ✅ LIVE 14:22** (`deaae68`; the 14:09 foreground deploy HUNG at xdist spawn like 10:42 and 13:45 — 33 idle pythons from 14:09:28, PID 50392 tree, not stoppable by the session, owner kills all three sets; the 14:19 retry via the PowerShell tool with `*> file` shipped it; boot `database ready` 21:21:57Z, `synced 29`, `/health` ready). **`pytest -m live` against v98 = 58 passed / 1 skipped** after a test-side shape fix on main (third finding; in `access/testing.md`). Rows 320–321. Worktree/branch removed. The build's finding (staff_dependency-only routes had no per-identity read bound for the operator) became v99. Before that, v93 LIVE — **29 slots, zero Groups**; self-test live and run by the owner (sweep 252); the CONFIRM/OPENED FOLD ✅ LANDED as **v88** `794d3aa` 17:33 (309k, rows 262–275, moved to DONE); the ENGINEERING SWEEP ✅ LANDED as **v89** `243dc0f` 18:16 (481k, rows 276–279, KI-21 + `LOG_LEVEL_COMMANDS` + gate-pass items moved to DONE; B1–B4 and A1–A2 struck inside their parent items, B5–B9 / A3–A4 still open); the PERSONALITY-POOL BUILD, Black Bloc half ✅ LANDED as **v90** `7c59eb1` 19:00 (288k, rows 280–286, KI-23 added BLOCKED on the GABI half); the GABI HALF ✅ LIVE 19:33 (186k; catalog-platform `de4ef63` → main `cb4f779`, deployed by the owner `755cfd54`, health answers pool v1 + eleven) and Black Bloc **v91** `604226f` 19:38 (roster compare by name, byte-for-byte sync; selftest 107 ok with GABI answering) — item 4, KI-23 moved to DONE, rows 284/286 rewritten; the `C:/lcw/pool` worktree is still attached (remove with `git -C <catalog-platform> worktree remove C:/lcw/pool` once the other session has pulled `cb4f779`). ENGINEERING SWEEP 2 ✅ LANDED as **v92** (merge `f866e98`; 349k against 300–450k; rows 287–294; all nine items closed, +9 tests to 5186; wave-1 findings + via-labelling bullets moved whole to DONE, the still-open remainder re-listed under the same heading with 13 unlabelled settings keys and two fold candidates from the sweep). cutover plan REFRESHED 20:55 against v92; the automod web-path item was found ALREADY CLOSED at v84 (`gated_writers`) and struck 21:05. ENGINEERING SWEEP 3 ✅ LANDED as **v93** `09ff46b` 21:59 (277k against 100–150k — item 5 was 143 tracebacks not one; merge `9fddad1`; rows 295–299; five items closed, +2 tests to 5188, deploy-gate stderr 1716 → 0; KI-24 filed; the sweep-2 residual bullet moved whole to DONE, the remainder re-listed under the same heading). TEST-SUITE MEASUREMENT PASS ✅ LANDED 22:27 (181k against 60–90k; `docs/info/test-suite-profile.md` on main `e60d7a5`; verdict: keep all 5188, fix three fixtures — 84% of suite time is setup, one true duplicate worth 62 ms). **OWNER DECISIONS, all seven answered 22:30–22:50:** 1 seed `test_contract.py` once per module — YES; 2 module-scoped `db` fixture (46 files) — YES, as its own build after 1+3; 3 module-scoped api `client`/`create_app` — YES; 4 delete the one duplicate (`tests/cogs/community/test_applications.py::test_a_number_is_read_off_a_card_with_or_without_the_hash`) — YES; 5 real assertions for the three assertionless tests — YES; 6 parametrised tables — LEAVE; 7 mirror pairs — LEAVE. **FIXTURE-SCOPE BUILD, half A (decisions 1+3+4+5) ✅ LANDED Sun 2026-09-06 08:50** on main at `e24e6b7` (the `--no-ff` merge `099f02b` was flattened by `git pull --rebase` before the push — the branch's six commits sit linearly on main, content identical) (branch `fixture-scope-half-a`, hand-made worktree `C:/lcw/bb-fixtures-a` — `.claude/` is a junction, see `docs/access/runbook.md` § *Agent worktrees on this machine*; Opus, 302k / 174 calls / 81 min against a 120–180k estimate; **NOT deployed — test-only, v93 stays live**; 5188 → 5187 tests, suite 88.7 s → 54.4 s at the gate here, the agent's own before/after in `docs/info/test-suite-profile.md` § *Half A — measured*; moved whole to DONE). **HALF B (decision 2) ✅ LANDED Sun 2026-09-06 09:40** as merge `348b98e` (pushed before the docs commit this time; Opus, 203k / 127 calls / 50 min against a 250–400k estimate; **NOT deployed — test-only, v93 stays live**; 35 per-file `db` fixtures → one module-scoped `db` in `tests/conftest.py` rewound per test incl. schema; the presence reversed-serial failure was `discord.py load_extension` replacing cog modules in `sys.modules`, fixed test-side by an autouse restore; suite 28.2 s forward / 28.7 s reversed at the gate here, agent: 55.0 → 26.0 s `-n auto`, 462 → 110 s serial; moved whole to DONE — **all seven measurement-pass decisions are now settled**). Left for a later sweep, from half B's report: eleven test files still build a `Database` inline rather than through a fixture (`tests/storage/test_db.py` by design; `test_actionlog`, `test_chat_llm`, `test_chat_memory`, `test_knowledge`, `test_llm`, `test_personas`, `test_selftest`, `test_selftest_panels`, `test_settings_panel`, `test_settings_store`) — listed in `docs/info/test-suite-profile.md` § *Half B — measured*, not urgent. Landing ritual moves to `pytest -n auto` (87 s vs 336 s on `-n 4`, measured at the v93 gate). NEXT after that: owner by-eye sweeps 253–294; dormant bots; `OPERATOR_READ_TOKEN` mint (owner 16:33: "Keep running stuff, don't pause"))

**`main` = `43312b9`** (role-menus panel merge; v77 live 20:51, 4529 tests, **36 commands**; `youtube_mode` is
**shadow** since 2026-09-03 17:42). **The panels program is COMPLETE** — waves 1, 2 and 3 (17 features, one
command + panel each) are all live and the program item moved WHOLE to `DONE.md` 2026-09-04 ("Panels over
slash commands — the program"); sweeps 144–182 are the owner's to run.
**Next, in order:** (1) the **second slash-command audit** (🆕 below — Fable, main loop, the FULL list of every
`/` command and subcommand, then merge proposals ONE AT A TIME: `/case`+`/cases`, honeypot → one, ticket
commands maybe); (2) the **hide-when-off build** (🆕 below, Opus, 120–180k, then v78); (3) the builds the audit
decides; (4) the three sweeps the automod landing deferred (🔧 below: ~~confirm-helper fold~~ (v88),
`LOG_LEVEL_COMMANDS` pass, settings-API gate pass — KI-21); (5) the small review findings folded into
whatever touches those files; (6) owner by-eye sweeps 14–15, 58–103, 144–244; (7) ~~Pawpette's Twitch Team form~~ **exercised by Pawpette and approved
(owner, 2026-09-05 13:45: "she did a test and approved it") — noted on `access/sweeps.md` → "The owner's Twitch Team form".** Merged
worktrees/branches (`agent-a19bdce15408f8243` birthdays, `agent-a448c7ab780ed3c2b` events,
`agent-aa735ab092d13477d` polls, `agent-abf063b9177e02f17` applications, and the wave-2/3 ones —
`agent-aba5d44f8e27a8e28` raidtrain, `agent-ace2086f9f7cfa541` role menus) can be pruned.

**Landing ritual (unchanged):** branch → `git merge --no-ff` on `main` → `scripts/deploy.ps1`
DETACHED (refuses a dirty tree; ~3 min now: ruff → pytest `-n auto` → ES-module parse of every
site asset → check.mjs → push → `flyctl deploy --app
black-bloc --ha=false --remote-only --yes`; flyctl lives at
`C:\Users\nbasl\AppData\Local\Microsoft\WinGet\Packages\Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe\flyctl.exe`)
→ EDIT the skeleton line it appends to `docs/deploys.log` → verify the boot log
(`flyctl logs --app black-bloc --no-tail`) → move the 🔧 item WHOLE to `DONE.md`, flip the
design-doc header and the `info/README.md` row to SHIPPED, re-key `code-notes.md` → commit,
push → tell the owner what to click.

**Gotchas that cost time recently:** `node --check file.js` passes a broken ES module (parses
as CommonJS) — use `--input-type=module`; the site is a `StaticFiles(html=True)` mount so
page links carry `.html` (`logkinds.FEATURE_PAGES`); `flyctl ssh console -C` from
PowerShell splits on spaces — run one-offs from Bash with the script base64-encoded (see
`DONE.md` 2026-09-03 third pass); "The handle is invalid" after a flyctl ssh command is
noise, the command ran; a `discord.ui.View` replaced on a message is NOT stopped — call
`stop()` yourself or its timeout fires later against the wrong content
(`ui/view.py:940–968`); `commands synced` counts TOP-LEVEL commands — a `Group` is one slot,
so collapsing subcommands into a panel does not change it.

## 🎯 Feature asks — the first list (owner, 2026-08-26, verbatim then expanded)

Owner's words: *"Go live message for #live-now channel / Twitch activity
tracking on anyone in the discord (want an opt out, might need to scan for
people that dont have activity but tbd) / Youtube maybe / Event form
submission (someone fills out the information and the event is made in
discord) / Let form submission go to a mod review channel, make sure form uses
hammer time or normalizes timezone by user / Have bot ping when an event is
live / Birthday announcements / Opt in, cutover time / Moderation / Copy for
most moderation settings from other bots, exceptions list to be fined tuned
(pinging multiple people, role based exceptions) / Temporary voice channel —
https://tempvoice.xyz — Steal this / https://www.honeypotbot.com — Steal this /
Personality for the bot can be @d"*

Status: **BUILDING IN PARALLEL (owner, 2026-08-26 20:38: "do what you can to start working in parallel").** **EVERYTHING BUILT SO FAR IS LIVE — `8036918`, 2026-08-27 20:15 Phoenix, 2158 tests, 35 slash commands, schema 16, 17 dashboard pages / 89 routes** (all six figures re-measured 2026-08-31; this line previously read `256f43d` / 07:46 / 1195 tests / 30 commands / schema 11 / 13 tabs)**:** the seven core phases (shadow/test mode), the full dashboard, `/voice` + panel + per-user memory, `/help`, bot About Me + "Cookout attendees: N" status, parity/Carl removed, Health tab lists all 7 loops, plus Phase 9 role approvals, **Phase 10 polls, Phase 11 chat 2, Phase 12 logs and Phase 13 requests**. Owner's test sweep in progress; feedback → batches. `deploys.log` has every deploy (**37** to date, counted 2026-08-31). Phases 5, 6, 7 building in git worktrees under `.claude/worktrees/` (gitignored) on their own branches, schema versions pre-assigned 6/7/8, shared files touched append-only. **Merge order: Phase 4 fixes → deploy → merge 5 → review/fix → merge 6 → review/fix → merge 7 → review/fix; re-key `code-notes.md` after each merge; deploy from `main` only.** If a session inherits this mid-flight: `git worktree list` shows the branches; never deploy with a dirty main tree. Build order
approved (Q13): see `info/feature-list.md`. Design docs: `info/phase1-design.md`
(settings, action log, role menus), `info/phase2-design.md` (go-live feed);
later phases get theirs before dispatch.

**Autonomy (owner, 2026-08-26 18:15): "keep going and only stop building the
phases if im needed for a critical choice. I can do a big test sweep when i get
back."** So: each phase = design → Opus build → Fable review → deploy in
TEST_MODE/shadow → next phase; owner does one consolidated test sweep later.
Every phase landing gets a `DONE.md` entry and a "what to click" row in
[`access/sweeps.md`](access/sweeps.md).

**F12 website placement (owner asked 2026-08-26): Phase 8, immediately after
the seven core phases.** Phase 1's settings store + audit log and the existing
FastAPI module are built as its foundation.

**Rollout rule (owner, 2026-08-26):** Black Bloc eventually replaces ALL of
Birthday Bot, Carl-bot, Modmail and YAGPDB — "rome wasn't built in a day".
Every feature that acts on members ships **shadow/log → watch → on**, flipped
per feature, so the old bot keeps running until the new one is proven.

| # | Feature | Open questions (answers land here) | Status |
|---|---|---|---|
| F1 | **Go-live → `#live-now`** | **DECIDED 2026-08-26: BOTH** — presence for discovery of anyone, Twitch EventSub (websocket) for rich posts on linked accounts; opt-out covers both. **PRIMARY = Discord presence/activity; Twitch EventSub is the FALLBACK/enrichment** (owner, 2026-08-26). **Measured incumbent (rescan):** YAGPDB posts ~8/day, 30 distinct streamers, template `REGULATORS! Mount up! **{login}** is currently streaming **{game}**! Check it out: https://www.twitch.tv/{login}` — keep the prefix; 4/199 posts render game as `****` (no category) → need a fallback; Twitch login ≠ Discord name (`thepresidentnoir`→`twitch.tv/prez`) → `/twitch link` is mandatory; YAG re-posts on restart/category change → **debounce**. Rich card = Discord's own link preview (free). Channel topic is stale ("post your links here") — fix when F1 ships. | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
| F2 | **Twitch activity tracking** — **DECIDED 2026-08-26: YAGPDB "Streaming"-style.** Presence-based; when a member goes live post "X is live" (+title/link) to the channel; optional *Live* role while streaming; require-role / ignore-role filters; opt-out. No stats/leaderboard. Merges with F1 (one design doc). **"Scan" DECIDED + already built 2026-09-01** (owner: "as long as they opt in with the /link"): the Twitch poller polls every linked login via Helix and announces without Discord presence — that IS the scan; opt-in = `/twitch link`, opt-out honored. | built (shadow) |
| F3 | **YouTube** — *maybe* | Go-live via YouTube presence WORKS (sweeps row 4); uploads SHIPPED 2026-09-02 as Phase 16 (moved to `DONE.md`), `youtube_mode` off until the owner flips it. | BUILT (live mode per cutover-plan) |
| F4 | **Event form → Discord Scheduled Event**, via review | **DECIDED 2026-08-26 (all blanks filled):** `/event create` **modal** (⚠️ both commands named here are RETIRED since v64, 2026-09-03: `/event` is one command that opens a panel whose **Propose an event** button is the modal, and the `/timezone` group became the panel's **My time zone** modal — [`info/events-panel-design.md`](info/events-panel-design.md)). **Timezone:** Discord exposes no user timezone to bots (only language locale) → entered once via `/timezone set` with city autocomplete, default = server zone (America/Phoenix). **Review = a channel per submission** (like Modmail today) under an **Events** category, named `<status>-<user>-<event>` e.g. `pending-sky-block-party` → renamed `approved-…` / `denied-…` (Discord channel names are lowercase a-z0-9-_ only, so `!` and spaces are normalised). **Approvers = anyone who can see `#mute-me-bot-test-spam`** — i.e. Aunties/Uncles, Leads, Committee, etc.; implement as "roles with View on the configured staff channel/category", not a hard-coded list. **Create a real Discord Scheduled Event: toggle, default ON.** | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
| F5 | **Ping when an event goes live** | **DECIDED 2026-08-26:** announce in **`#live-now`** (channel set in an options menu); **role ping is a setting**, default *none* (YAG pings nobody today). See F14 for the roles. | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
| F14 | **Ping roles** (owner, 2026-08-26): an opt-in **Events** role for go-live/event pings, and **favourite-streamer roles** — per-streamer opt-in pings ("people that want to see SuperNamu only … can get her pings"). Wire into F1/F5 announcements and the role menus. | SHIPPED `d777f57` 2026-09-02 (Phase 15, `info/phase15-design.md`); `pings_mode` ON; live-Discord role sweep = owner's |
| F6 | **Birthday announcements**, opt-in, with a "cutover time" | **Seed data:** Birthday Bot export (39 rows) at `archive/current-bots/birthday-bot-export-2026-08-05.md`. **Measured incumbent (rescan, 16 posts):** channel **`#return-of-the-gen`** (`1411816390414962700`), an embed `Happy Birthday **{display_name}**!` colour `#4eefff`, no ping, no role; fires at **≈00:03 local midnight in a PER-MEMBER timezone** (UTC-4 ×8, -5 ×4, -6 ×2, -7 ×1, +1 ×1) — contradicts the bot's own "server time zone" blurb. 🔴 **Phoenix gotcha: 15 of 16 landed the evening BEFORE the birthday in Phoenix terms.** **DECIDED 2026-08-26 (Q12): per-member midnight** (uses the F4 `/timezone` store); **fallback = server midnight (America/Phoenix)** when a member has no timezone set. The `🎂` role's grantor is unknown (Birthday Bot lacks manage_roles). | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
| F7 | **Moderation** — copy the *usual* settings from other bots; exceptions list fine-tuned later (mass pings, role-based exceptions) | **Carl's live config captured** (`archive/current-bots/carl-bot-dashboard-2026-08-26.md`): only mention-spam (5/30s → delete+warn+5-min timeout) is armed; whitelists empty; warn threshold 8 with no punishment. **YAGPDB automod measured OFF.** `#carlbot-logs`: 7 warn cases in ~2 years — quiet server, do not over-tune. **DECIDED 2026-08-26 (Q11): "follow what exists"** — reproduce Carl's live config as-is (mention-spam 5/30s → delete+warn+5-min timeout; everything else log-only), warn/timeout/kick/ban commands, modlog, exempt roles = staff set; **tune in shadow mode**, change later. | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
| F8 | **Temporary voice channels** — replicate tempvoice.xyz | **DECIDED 2026-08-26:** one creator voice channel named **"join to create a channel"** in the existing voice-channel area, positioned **directly above "You Still Here?"** (the AFK channel — keep it above, never below); spawned channels named **`{user}'s bloc`**, placed next to the creator, deleted when empty; owner control panel (rename / limit / lock / hide / kick / ban / claim / transfer) per `info/reference-bots.md`; usable by **`Member`** to start. | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
| F9 | **Honeypot** — replicate honeypotbot.com | **DECIDED 2026-08-26:** honeypot channel(s) at the bottom with a pinned "do not post here" notice; anything posted → **ban + purge messages**, shipped **shadow-first** (log would-ban for a week, act on nothing) then enforce. **Exempt:** all bots + anyone who can see the staff channel (same rule as F4 approvers). **Log channel:** `#mute-me-bot-test-spam` for now — the owner will **rename it to `#black-block-logs`** (spelling confirmed 2026-08-26) when the bot leaves test mode; the log channel is a setting, so the rename costs nothing. The scan found no existing honeypot channel; Carl's honeypot section is unconfigured. | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
| F10 | **Conversation when @-mentioned** ("@'d", owner clarified 2026-08-26): when someone pings the bot it holds "some semblance of a conversation" — an LLM-backed reply. | BUILT + ARMED (Phase 14, 2026-09-01): three tiers live, Cookout voice + trope pool, $20/mo cap. Long-term memory = next-wave item 3. | BUILT |
| F11 | **Modmail** (added by owner 2026-08-26 — replaces the Modmail bot) | **DECIDED 2026-08-26: do what the current bot does (channel-per-ticket in the ModMail category, topic `ModMail Channel <user-id> <channel-id>`), AND wire a second mode — private threads in one staff channel — as a setting** ("wire up the option to be in 2 channel"); the toggle is ported to the F12 website later. Reference: `info/reference-bots.md` (Modmail command table). | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
| F13 | **Verification Bot** — **rescan result: dormant** (1 message in ~2 years, its own join notice); no use cases to port. Also found dormant: `baf#0659` (a Red-DiscordBot install, ~1 yr idle) and `Black Block#1423` — **two prior attempts at this project**. Recommend kicking all three once Black Bloc is stable (owner action; on the cleanup list). `Wordle` is a Discord built-in activity webhook (422-day streak) — leave it alone. | closed → cleanup |
| F17 | **Role-process takeover + audit** (owner, 2026-08-26: "grab all the roles and settings carl already has so we dont need to recreate them, same emojis too … audit each user and their roles so we can take over that process") | **Audit captured:** `archive/current-bots/role-audit-2026-08-26.md` — 118 humans, 7 bots, 59 roles, every member's roles, per-role counts, self-assign holders; **4 humans lack `Member`** (simonebwest, FFStreamWatcher, scrybaby, UraniumAnchor), 1 has no roles (scrybaby). Carl's panels/emojis already reproduced by `/rolemenu seed-defaults`; **fix:** Marathons must use Carl's custom emoji `<:JoyGAMING:1337948924844965931>` instead of 🎮 (do at Phase 2 review). **DECIDED 2026-08-26:** `Member` is granted by **Discord's own rules screen** (owner: "i think discord rules") — Black Bloc does not take over the gate; the 4 non-Members are for the owner to handle by hand. **YAG's 3 role-command groups become Bloc menus:** *Student/Teacher* folds into the existing `mentoring` panel (Mentor/Initiate); *Runner Status* (Runner / Live Runner / Commentator) becomes a **staff-assigned** set via a new `/rolemenu` mode `staff` (staff picks the member, not self-serve); *Rule Reader* is redundant with the Discord rules screen — dropped. "We can change later." → add to the next builder's scope (Phase 3 rider). | BUILT (Phase 3 + 9; status corrected 2026-09-02) |
| F12 | **Config website for mods/admins** — **DESIGNED 2026-08-26: `info/phase8-design.md`. Owner decisions 2026-08-26 18:30 (verbatim): "we can use blackbloc.heygabi.ai for now until the org decides on a name and then we port it to that domain … this site needs to be entirely disconnected from heygabi … discord login verification only except my google sso as the owner admin of the whole domain … we'll need to link my discord verification to my google sso in the future. only people/roles who can currently see the spam channel we're testing in should be able to get on the bot, aunties/uncles mainly and the roles above it."** Static site on Cloudflare Pages wearing the estate template (`estate-theme.css`, `theme.js` 5-theme dropdown, `permission-ux.js`, fonts from `catalog-platform/sites/heygabi-home`), Discord-OAuth login gated on the same staff-role rule as slash commands, FastAPI routers inside the bot process on Fly, 12 pages mapped from Carl/YAG dashboards onto F1–F16, one settings store + audit. **8a read-only status page can ship right after Phase 2; 8b full dashboard after Phase 7.** Owner decisions deferred to then: hostname, Discord-only vs +estate SSO, who may edit moderation rules. | BUILT + LIVE at blackbloc.heygabi.ai (status corrected 2026-09-02) |

## 📋 Session 2026-08-31 (owner back from the trip)

- **Owner 2026-08-31 ~10:13: "read all docs and global rules, lets get started with whats left on our todo list"** → B4–B8 built and **LIVE `3cae955`, deployed 11:32 (see `DONE.md` entry + `deploys.log`)**; owner sweep rows 21–24. Next in the queue: restyle R1/R2 + the KI-6/KI-9 security build (below).
- **Owner 2026-08-31 ~10:16, verbatim: "also read all docs and verify if theyer stale or need updating too"** → full docs staleness audit vs measured repo/deploy state. Status: **LANDED — 26 files reviewed + committed `d87ee84`; the same morning's bookkeeping sweep then moved the 30 landed items to `DONE.md` and consolidated owner checks into `access/sweeps.md` (rows 18–20 + phase scripts). Follow-ups queued below: code-notes re-key, KI-6/KI-9, DB backup drill.**
- **Hook finding fixed 10:15:** `scripts/docs/` (a tooling folder holding `move_done.py`, not a docs tree) tripped the session-start docs-shape check every session → renamed to `scripts/doctools/`, runbook reference updated, committed + pushed `7b7840b`.
- **DECIDED 2026-08-31 ~10:25 (owner): `docs/` stays TRACKED permanently** ("actually lets keep it tracked", after first picking purge). The 2026-08-26 local-only rule is retired; secret NAMES only still applies. `docs/` removed from `.gitignore`; the LOCAL ONLY / TEMPORARILY TRACKED headers across docs and the CLAUDE.md line get updated in the docs-audit review pass (audit agent is mid-flight in those files).

## 📋 Session 2026-09-01

- **Owner ~09:00, verbatim: "i did thee sweep of the site and its good for now, ill keep doing the sweep and playing with akk the buttons and menus. lets get started on everything in this list. (we will kick the bots in a few weeks so no worries about that). we can do the scan for no streaming activity too as long as they opt in with the /link. I did the dashboard sign in too"** →
  (a) site sweep round 1 PASSED (sweeps rows 25/26/28 + general site; owner keeps sweeping);
  (b) **F2 scan DECIDED: opt-in via `/twitch link` — and MEASURED ALREADY BUILT**: `golive.py:poll_once` polls every linked login via Helix each cycle and announces without Discord presence; opt-out honored on the shared `_go_live_once` path (`golive.py:396`). F2 fully closed;
  (c) bot kicks in a few weeks — cutover-plan §3 records the horizon;
  (d) "get started on everything in this list" → go-live hardening a/b/c + F4 requester-in-channel + F4(b)/F5 toggle verification: **Opus builder dispatched ~09:05 in a worktree**; KI-1 CLOSED (local `DATABASE_PATH` → `C:/Users/nbasl/black-bloc-data/`, old copy left inert in `data/`); **nightly DB backup built**: `black_bloc/dbsnapshot.py` + `scripts/backup_db.ps1` + Windows scheduled task "BlackBloc DB backup" daily 04:00 (StartWhenAvailable) — end-to-end test pending the next deploy shipping the module; **`info/cutover-plan.md` drafted** (the shadow→on ladder). Restyle overrides deliberately NOT flipped (owner named none).

- ✅ **Chat is LIVE AND ARMED (2026-09-01 ~14:50):** owner minted both keys and
  chose `.env` as the management place ("add the lines to the .env and we can
  push from there"); Claude pushed both to Fly from `.env` (values never
  displayed; format-checked) and — on the owner's "Yes, flip it now" — set
  `chat_llm_mode on` through the dashboard Settings page in the owner's
  browser (audited Via: Website; row read back ON after save). ⚠️ **No model
  call has happened yet** — the owner's first @-mention that no intent knows
  will be the first ever; sweeps rows 33–35 are the check-out and row 33's
  `/chat status` shows the first real cost figure. ✅ `.env.enc` refreshed by the owner
  2026-09-02 11:31 (via the full Git-bash path — `sh` is not on the owner's
  PATH; runbook command updated accordingly) and pushed in `8e81a03`.
  Future (estate-level): the "global personality pool" — one trope store
  shared across estate bots.




- **Owner 2026-09-02 ~11:30–11:50: secret custody moved to 1Password.** Owner asks, verbatim: "we use an estate vault for gabi in 1 password, can we do something like that here?" → "should we use the estate vault or make a new one? I assume a new one that way i can share the vault with another dev" → "we should do individual entries for the vault not 1 big one". Done live: vault **`Black Bloc`** created (separate from `Estate` for shareability), **nine bare-titled items** created from `.env` via the `op` CLI (values never in any transcript; owner clicked the authorization prompts), verified by title listing. Custody docs updated (RECOVERY header + runbook laptop flow): vault master → `.env` working copy → `.env.enc` offline fallback. Same window: `.env.enc` refreshed by the owner + pushed `8e81a03`; **CI stood up and GREEN on the first run** (ubuntu, 5m21s — the suite's first non-Windows execution) + the gated `scripts/deploy.ps1` is THE deploy path (runbook updated; incident-named). Gotcha recorded in RECOVERY: `op` needs an unsandboxed shell to reach the desktop app.

## 🚀 THE NEXT WAVE — decided 2026-09-02 (owner: "We're going to build those, update all docs, I'm gonna switch to fable 5.1 then we go")

**The session picking this up: read this block, design, dispatch — the owner has
already said go.** Order recommended by the 5.0 session, owner did not reorder:

1. ~~F14 — ping roles~~ **SHIPPED `d777f57` 2026-09-02 17:43** — moved whole to
   [`DONE.md`](DONE.md) ("Phase 15"). Owner's live-Discord sweep still open
   (role create/assign, the two-role prefix on a real announcement).
2. ~~F3 — YouTube upload announcements~~ **SHIPPED merge `7295f61`, deployed
   2026-09-02 22:18 (`049881b`)** — moved whole to [`DONE.md`](DONE.md) ("Phase 16").
   `youtube_mode` ships **off**; owner's optional `YOUTUBE_API_KEY` still open
   (Waiting on the owner). Never yet run against a live channel.
3. ~~Chat long-term memory~~ **SHIPPED merge `6d61994`, deployed `7b1c592`
   2026-09-03** — moved whole to [`DONE.md`](DONE.md) ("Phases 17/18/19").
   `chat_memory_mode` ships **off**; residual KI-14; never run against live Discord.
   Ride-along: the requests state machine (open → in_progress → done; hold/declined).
4. ~~Global personality pool~~ **SHIPPED — both halves LIVE 2026-09-05: Black Bloc v90 `7c59eb1` +
   v91 `604226f`, GABI catalog-platform `de4ef63` / `755cfd54`** — moved whole to [`DONE.md`](DONE.md)
   ("Personality pool, both halves"). KI-23 closed there too. Owner's sweep rows 280–286 open.
5. **Restyle overrides** — the three cheap look-and-feel flips below stay
   available; fold into any site-touching build.
6. ~~Raid trains (member request #1, Pawpette)~~ **SHIPPED merge `0bb3835`, deployed
   `7b1c592` 2026-09-03** — moved whole to [`DONE.md`](DONE.md) ("Phases 17/18/19").
   `raidtrain_mode` ships **off**; residuals KI-15/KI-16; request #1 flipped to `done`
   at landing. Owner's sweep rows 48–52 open.
7. ~~Twitch Team application form (member request #2, Pawpette)~~ **SHIPPED merge
   `7b1c592`, deployed `7b1c592` 2026-09-03** — moved whole to [`DONE.md`](DONE.md).
   `applications_mode` ships **off**; residuals KI-17/KI-18; request #2 flipped to `done`
   and #3 to `hold` at landing. Owner's sweep rows 53–57 open (the Twitch Team form
   walk-through is there).

8. ~~YouTube go-live by default / every-upload opt-in~~ **WITHDRAWN by the owner 2026-09-03 18:05 —
   no build.** Asked 17:59 ("grab going live for YouTube… every YouTube… off by default"); on hearing
   `/golive` already announces YouTube lives from Discord presence, the owner said: don't add live
   detection to `/youtube`; keep `youtube_mode` on **shadow** for now; turning uploads on stays a
   staff decision (Setup on the `/youtube` panel and the Go-live page, both already staff-gated).
   Recorded in `DONE.md` 2026-09-03 so nobody re-derives it.

**Standing context for the new session:** every build = Opus worktree builder
(Fable plans/reviews/never bulk-codes), brief points at `info/review-checklist.md`
(33 items) + the phase design doc; TEST_MODE confined; deploys ONLY via
`scripts/deploy.ps1`; CI must stay green; every decision configurable both ways;
docs bookkeeping lands with the work, not after.

## ⏳ Waiting on the owner

- ⏸️ **PAUSED again (owner, 2026-09-07 15:10: "The other 3 can be paused again").** **Cutover, at your pace** — [`info/cutover-plan.md`](info/cutover-plan.md) (**re-measured against v92 on 2026-09-05 20:55** — every step now names the panel move, not the retired sub-commands): prerequisites P1–P6 (channel rename, staff channel, approval channels, TEST_MODE lift — the lift is yours alone — then a verification pass), then the per-feature ladder. Either door flips automod safely — the dashboard has carried its arming refusal since v84 (plan §4).
- **Test sweep — the whole list lives in [`access/sweeps.md`](access/sweeps.md)** (37 rows in priority order + the detailed phase 1–8a scripts; it is the ONE home for what a person has not yet exercised).
- ~~Twitch developer app~~ **ALREADY DONE — stale line caught by the owner
  2026-08-31 ("didnt we already connect twitch dev").** Measured: `TWITCH_CLIENT_ID`
  + `TWITCH_CLIENT_SECRET` are Deployed on Fly and present in `.env`, and the boot
  log says `twitch: app token obtained` (20:13:48Z). Nothing to do.
- ⏸️ **PAUSED (owner, 2026-09-07).** **Cleanup (later, owner):** kick the dormant bots `Verification Bot`, `baf`,
  `Black Block` once Black Bloc is stable.
- 🔁 **RECURRING — monthly music-bot feasibility check (owner, 2026-09-07 15:10: "scrap this whole project, until we find a reliable way to do this let's be done with me. Maybe set up a monthly research task to look into if it's doable in a stable way").** The music bot / request #3 is SCRAPPED (moved whole to `DONE.md`, "Music bot scrapped"). What a session does when the date below has passed: one research pass, no build — is there now a STABLE, terms-compliant way for a Discord bot to play music (Spotify's developer terms and dev-mode 250k-user gate; whether YouTube/SoundCloud sources via Lavalink still survive datacenter-IP blocking; anything new from Discord itself, e.g. Activities/Watch Together-style playback); write the dated finding to `info/music-source-research.md` (create it), bump the next-check date here, and only if the answer is a clear YES put ONE question to the owner. **Next check: 2026-10-07.** This line is the reminder — session crons die with the session, and every session reads this file; a Windows scheduled task running Claude headless is the upgrade if the owner wants it unattended.

## 🔧 Open engineering items
- 🔴 **Make the repo public so Actions run again (owner, 2026-09-10 16:48, verbatim: "Make the repo public so we can run actions again"; 16:52: "Do b").** History scan before flipping: no `.env` ever committed, no token-shaped values in any commit, docs carry secret NAMES only — but `.env.enc` (the OpenSSL-encrypted copy of the whole `.env`, `scripts/env-lock.sh`) sat in the tree and in 2 commits. Owner chose **(b)**: purge `.env.enc` from history (fresh clone + `git filter-repo --invert-paths --path .env.enc`, force-push), stop tracking it (`.gitignore` un-negated; `env-lock.sh` + owner guide / runbook / RECOVERY say the `.enc` lives OUTSIDE the repo now), THEN `gh repo edit --visibility public`, THEN the owner rotates every secret named in `.env.example` (**21** names — measured 2026-09-11 08:50; the earlier "22" was a miscount — plus `OPERATOR_READ_TOKEN`, which `config.py` reads but `.env.example` omits, if it was ever set in `.env`) because the encrypted file must be treated as exposed. Local main is reset to the rewritten `origin/main` (tree clean, verified); the in-flight `where-picker` worktree branch is rebased onto the new main at landing (`git rebase --onto`), it never touched `.env.enc`. Status: purge DONE 16:55 (force-pushed, local reset, `.env.enc` ignored — commit `7d9120c`); the visibility flip itself was blocked for Claude by the permission classifier and handed to the owner: `! gh repo edit skymitch9/black-bloc --visibility public --accept-visibility-change-consequences` — the owner's `!` run at 18:00 did not take (still PRIVATE); at the owner's word ("Can you run it", 20:06) Claude ran the same command: **PUBLIC 20:06**, and the re-run of CI `34547769123` went GREEN in 3 m 1 s (the private-repo runs had died in 3 s on GitHub's billing block) — Actions run again. ⚠️ CI warns `actions/checkout@v4` / `setup-node@v4` / `setup-python@v5` are forced onto Node 24 — bump when convenient. REMAINING: rotate the 21 names in `.env.example` (+ `OPERATOR_READ_TOKEN` if set) (old commit `8e81a03` stays fetchable by SHA on GitHub until GC — GitHub Support can purge). Moves to DONE once public + rotated.

- 🔎 **`event.room_forgotten` is logged TWICE per row at boot (v110, 17:14:45Z, events 2 and 3).** Both `on_ready`'s reconcile and `_reconcile_loop`'s first tick read the swept rows before either wrote the cleared id. Harmless (two identical log rows once per restart, the id is cleared once) — fix is a single reconcile at boot or a `review_channel_id` re-read before the write; bundle into the next events build, not worth a deploy alone.
- 🔎 **`code-notes.md` still has un-re-keyed refs the inline pass could not reach (11:39):** 32 `` `path:N` `` refs in body prose OUTSIDE tables (some live, e.g. `storage/db.py:123`, `settings_store.py:649`), 43 second-and-later keys in the 34 multi-key column-1 cells (`` `site.css:709` and `:744` ``), all 11 `.css` refs (no construct index for CSS), and 367 in-row refs the tool refused to move because different base commits gave different verified answers (median 4 per ref) — a wrong-but-confident number is worse than a stale one. One move is doubted in the header: `server.mjs:2879 → :4164` should be the `DELETE /api/chat/lines/:id` route at ~4387, and that note's CLAIM (refuses the last line) is itself stale. Bundle into the next docs pass; the report is `scripts/scan/rekey_inline_report.json` (gitignored).
- 🔧 **When-picker follow-ups (from the v100 landing, 2026-09-10 16:01):** (0) ✅ label change (owner, 16:07, verbatim: "I don't love which hour, maybe make it start time") — `when_picker.py` `HOUR_PLACEHOLDER` / `MINUTE_PLACEHOLDER` now `Start time — hour` / `Start time — minute`, commit `b5f2288`, **v101 LIVE 16:11**; and (owner, 16:11: "Change which day to date") `DAY_PLACEHOLDER` → `Date`, shipping as v102. Both records on `deploys.log`. (1) design D4 — the website's Events / Raid-train create forms (`site/public/assets/page-events.js`, `page-raidtrain.js`) still take a typed `YYYY-MM-DD HH:MM`; a `datetime-local` input + a zone select fed by `timezone_choices` is its own small Opus item (est. 60–100k). (2) ~~owner question — raid trains' scheduled-event suffix~~ **shipped as `raidtrain_scheduled_name_template` at v104** (merge `b320031`, default `{title}`; in `DONE.md`). (3) ~~`code-notes.md` re-key debt (the two `# Events` sections + the five line-diff ranges `7d9120c → 3205c0f`, `ebe0ead → 6c10b9d`, `8b9976c → ac43a20`, `9fc3a33 → 73e2e44`, `d25f87c → b320031`)~~ **PAID 2026-09-11 09:10 by the docs pass, slice E** — the whole file re-keyed by anchor (`DONE.md` 2026-09-11 "Update all docs"); the tool that did it is `scripts/scan/rekey_code_notes.py` (gitignored, kept), one `--write` per merge from now on. (4) sweep rows 323–327 are the owner's; 327 (the calendar name) waits on TEST_MODE.
- 🔧 **Self-test leftovers after wave 5 (handed over at the v86 landing, 2026-09-05 — Fable review findings, none
  blocking):** (1) ~~`api/selftest_api.py:start` hands `selftest.finish(one)` to `asyncio.create_task` and nothing awaits
  it, so a check-runner that RAISES (not a check that fails — those are recorded) dies with only asyncio's GC warning;
  wrap it so the exception lands as a `selftest.finished` row with `failed` counted and the busy flag cleared (the
  `finally` already clears it — the row is what is missing)~~ **DONE `36e4ad7`** — `selftest.finish_quietly` records the
  crash as a `selftest.check` row in words, closes the run and logs the finished row; all three doors use it, not just
  the website's; (2) ~~`selftest.py:checks_of` scans every `selftest.check`
  row for the guild and filters by `run_id` in Python — grows one run's worth per run; index or `WHERE json_extract`
  on `details.run_id`, measure at ~50 runs~~ **DONE `36e4ad7`** — `json_extract(details, '$.run_id')` in the WHERE
  clause; measured at 50 runs × 106 checks, 5300 rows read → 106 and 14.9 ms → 3.4 ms, and with 50k unrelated rows
  beside them 19.6 → 8.5 ms. `EXPLAIN` showed `SCAN action_log` (no index existed at all), so schema **32** adds
  `action_log_by_kind` on `(guild_id, kind, id)`: 8.5 → 3.1 ms at that size. ⚠️ At 5.3k rows the index is SLOWER
  (3.4 → 4.2 ms, a temp B-tree for the ORDER BY) — the bigger measurement is the one that decided it;
  (3) ~~`OPERATOR_READ_TOKEN` is not set on Fly, so `tests/live/` has never
  hit the deployed host — mint one (Fly secret, NAME only in docs) and run `pytest -m live` once from a laptop, then
  record the measured count in `access/testing.md`~~ **DONE 2026-09-06 13:55** — minted (Q5 "A"), live at v97, first run 20/38/1 recorded in `access/testing.md`; the 38 are the v98 bucket fix, see the resume header; (4) the boot line and the purge line are the only live measurements of the self-test so far (v87: `106 ok, 0 failed, 24 posted`; v86 purge: 24 deleted 5 min 40 s later) — a person pressing **Run the self-test** is sweep row 252.
- 🔧 **`/settings` leftovers after Build 2 (handed over at the v84 landing, 2026-09-05):** (1) ~~the operator-read-log
  toggle on `Panels & commands…` is drawn only for `manage_guild` but `MoveButton.callback` → `run_toggle` does not
  re-ask it (the core-key picks do, through `core_keys_allowed`) — the panel is ephemeral to its opener so the exposure
  is a Lead losing the permission mid-panel; one `manages_guild` line + a test~~ **DONE `e6ecfba`** — `run_gated_set`
  is `run_core_set`'s body with the gate passed in, and both moves are one line on top of it; sweep row 276;
  (2) ~~`docs/info/panels-program.md` and
  `docs/info/feature-list.md` are STALE — panels-program still asks fork F3 as open, says "~120 keys", and its Core
  row/totals describe a `settings` Group; feature-list has no `/settings` panel row~~ **DONE `83920bc`** — F3 answered
  (the paged panel, v84), the Core row and totals re-measured at `aa03a01` (**29 commands, ZERO Groups, 185 keys**,
  not "~120"), the program's status flipped to COMPLETE, and feature-list gains row **C1**; its three
  `/settings set-value` instructions were corrected too — that subcommand no longer exists;
  (3) ~~**KI-21**: the `via` keyword
  exists now — route `PUT`/`DELETE /api/settings/{key}` through `set_key`/`clear_key` and delete the route's own
  `note()` (one commit)~~ **DONE `675f233` + `49370a6`** — and the gate pass with it: `gated_writers()` hands
  `automod_mode`, `honeypot_mode` and `honeypot_exempt_role_ids` to the cog's own move, which the audit found are
  **the only three writes in the app with a cog-side gate**; KI-21 moved WHOLE to `DONE.md`; sweep rows 277/278;
  (4) ~~the mock's `*_panel_minutes` rows claim `max: 1440` with no `KEY_MAX` in the registry
  (16 rows) and the mock's `CORE_KEYS` is a shorter second copy (3 vs 6) — one home~~ **DONE `c1263ca`** — measured
  against the running mock: **14** rows claimed the 1440 (the validator enforces no such bound, and KI-20 says it is
  deliberately unclamped, so the claim was removed rather than mirrored), `youtube_poll_minutes` was missing its
  `min: 5`, `CORE_KEYS` was 9 against 12, and **sixteen registry keys had no row in the mock at all**. All generated
  from the registry; `contract.json` gains a `settings` block that both `tests/api/test_contract.py` and
  `site/mock/check.mjs` read, in both directions; (5) the six singleton namespaces
  (`event`, `voice`, `memory`, `hide`, `emoji`, `cost`) now appear on a Discord control, one rename pass for both
  surfaces; (6) the number modal's bound is a compact label of its own because a `TextInput` label caps at 45 chars —
  fine, but the `bounds_line` prose and the label can drift; (7) `tests/cogs/test_presence.py` + `tests/test_bot.py`
  pollute each other in one process (the real bot starts the presence loop) — invisible under `-n auto`, pre-existing;
  (8) the `birthdays` → `cogs.core` import is the first `cogs/community/* → cogs/core` edge — rule on it before a second
  feature copies it (a module function, not a cog; acceptable, but `set_key`/`clear_key` may belong in a leaf module);
  (9) the three hand-rolled confirm copies are still three — Build 2 made the settings confirm a card STATE, so the
  "fold 7 copies" sweep is now a fold of the other panels, not of this one.
- **Wave-1 review findings — what is still open after ENGINEERING SWEEP 3 (v93, 2026-09-05; the
  sweep-2 residual bullet moved whole to `DONE.md`, "Engineering sweep 3 landed as v93"):** polls'
  `draft` status — **DECIDED 2026-09-06 09:45, owner verbatim "B but only save 1 draft per person max"**:
  saved drafts became real, one per person per guild enforced by the schema, design in
  [`info/poll-drafts-design.md`](info/poll-drafts-design.md), ✅ **LANDED 10:45 as merge `8405bea`**
  (358k against 250–400k, rows 300–304, v94 — moved whole to `DONE.md`; the mock's `POLL_STATUSES`
  still lists `'draft'`, `server.mjs:2986`/`:3303`, mock-only, one-line tidy when next in there);
  **Q2 (create-recurrence web route, "2. A") and Q3 (Logs button `count`/`important_only`, "3. B")
  ✅ LANDED 2026-09-06 11:36** as merges `c915ade` / `42d2e6e`, shipping as v96 (244k + 274k against
  120–180k + 150–220k; rows 305–314; +41 tests to 5267; keys 189 → 191; routes 149 → 150) — moved whole
  to `DONE.md` ("Logs buttons … and Create-a-recurring-poll from the website"). **Q4 (KI-24 loop guard, "Build it a")
  ✅ LANDED 2026-09-06 13:44** as merge `689eff5` (170k against 80–140k; rows 315–319; +10 tests to 5277; no schema or
  key change) shipping as v97 — moved whole to `DONE.md` ("Loop guard"); it also closed the `POST /api/polls`
  `poll_mode` gap and the `Core.purge_loop` unconditional start from the earlier reports. **Still open from those
  reports:** the `logs` namespace makes **23** settings groups against `/settings`' 25-option select — two more
  namespaces and the picker needs a `Find…` path like `chat` has; mock `state.pollRecurrences` seeds ids 4/5
  inside `state.polls`' id space (tidy with the `'draft'` one above); `rolemenu_log_level`'s registration site
  was not read line-by-line (generated by the log-level family); three `path:line` pointers into
  `architecture.md` inside past design docs' executed checklists are ~77 lines off (historical record, left on
  purpose). **The v98 build's operator read-bound finding (added 14:32) ✅ LANDED 2026-09-06 20:00 as merge `88e0242` (branch `operator-read-bound`, 158k against 60–100k; row 322; +7 tests to 5286; no schema, key, route or log-kind change) shipping as v99 — moved whole to `DONE.md` ("Operator read bound").**

- **Curated docs for peers — DECIDED + DONE 2026-09-01** (owner picked "Rewrite
  README now"): root `README.md` rewritten as the peer front door (what the bot
  does today, local run, the docs map, the six house rules); the tracked
  `docs/` tree stays as the deep reference. **Deploy-button idea: owner chose
  "Keep it parked" 2026-09-01** — revisit only if a session actually cannot
  deploy.

- **Restyle look-and-feel calls the owner may still override** (each cheap):
  nav grouping (Requests under Overview, Members under Moderation — one line in
  `shell.js:GROUPS`); the TODAY strip replaced the "Needs a human" card
  (one-fact-one-home); "RUNS THE COOKOUT" wraps to two rail lines in the
  Cyberpunk theme only (its own `--et-nav-head-size`; fix = shorter caption or a
  theme override). Say the word and any of these flips.

- **Owner 2026-08-27 ~11:49, verbatim: "Probably should make a deploy button api so you can deploy for me if you can't permission"** → idea logged. Today: the owner's standing authorisation works — the last four deploys ran from the session. A deploy endpoint on the bot would need a Fly API token on the machine and a self-redeploy path; higher risk than value while the session can deploy. Status: **parked unless the classifier blocks again.**



## ✅ (RESOLVED 2026-09-02) Groq model pin was DEAD — llama-3.3-70b deprecated

The catalog-platform session's entry above was independently confirmed here the
same day (owner: "0 api calls on groq" → measured 404 model_not_found on 4 live
attempts). Fixed: live setting repinned to `openai/gpt-oss-120b` via the
dashboard, code default + mock repinned in `5e15778`, ONE live call made and
verified 200 with real content at the bot's 400-token ceiling (note: gpt-oss
spends tokens on a `reasoning` field first — tiny max_tokens returns empty
content). KI-1 line above also removed — closed 2026-09-01 (DATABASE_PATH moved
out of OneDrive, recorded in KNOWN_ISSUES).
