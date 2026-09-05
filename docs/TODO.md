# Black Bloc — TODO (active work only)

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-09-03 11:45** (v60 live, tree clean, nothing in flight) — the 🔁 resume
> block below was refreshed then; first written 07:50 at the owner's order during API outages ("make sure if we lose progress and memory our docs survive");
> everything in it was measured at that time (`git log`, `git worktree list`, the live
> page, the deploys log). Earlier: 2026-09-02 handoff pass before the switch to Fable 5.1
> (schema **20**, **2610** tests, 17 pages / **107** routes, 37 sweep rows — those counts
> are now stale: schema **26**, **3345** tests, 17 pages / **139** routes at `c4420cc`).
>
> Finished items MOVE whole to [`DONE.md`](DONE.md) in the session they land.
> Accepted defects go to [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md), not here.

## 🔁 IF THIS SESSION DIES — resume here (refreshed 2026-09-04 20:54, v77 live, PANELS PROGRAM COMPLETE — waves 1–3 all shipped)

**`main` = `43312b9`** (role-menus panel merge; v77 live 20:51, 4529 tests, **36 commands**; `youtube_mode` is
**shadow** since 2026-09-03 17:42). **The panels program is COMPLETE** — waves 1, 2 and 3 (17 features, one
command + panel each) are all live and the program item moved WHOLE to `DONE.md` 2026-09-04 ("Panels over
slash commands — the program"); sweeps 144–182 are the owner's to run.
**Next, in order:** (1) the **second slash-command audit** (🆕 below — Fable, main loop, the FULL list of every
`/` command and subcommand, then merge proposals ONE AT A TIME: `/case`+`/cases`, honeypot → one, ticket
commands maybe); (2) the **hide-when-off build** (🆕 below, Opus, 120–180k, then v78); (3) the builds the audit
decides; (4) the three sweeps the automod landing deferred (🔧 below: confirm-helper fold — now 7 copies —,
`LOG_LEVEL_COMMANDS` pass, settings-API gate pass — KI-21); (5) the small review findings folded into
whatever touches those files; (6) owner by-eye sweeps 14–15, 58–103, 144–182; (7) Pawpette's Twitch Team form still needs the owner's walk-through
(`access/sweeps.md` → "The owner's Twitch Team form") — no form exists on the live site as of 15:54. Merged
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
| F4 | **Event form → Discord Scheduled Event**, via review | **DECIDED 2026-08-26 (all blanks filled):** `/event create` **modal**. **Timezone:** Discord exposes no user timezone to bots (only language locale) → entered once via `/timezone set` with city autocomplete, default = server zone (America/Phoenix). **Review = a channel per submission** (like Modmail today) under an **Events** category, named `<status>-<user>-<event>` e.g. `pending-sky-block-party` → renamed `approved-…` / `denied-…` (Discord channel names are lowercase a-z0-9-_ only, so `!` and spaces are normalised). **Approvers = anyone who can see `#mute-me-bot-test-spam`** — i.e. Aunties/Uncles, Leads, Committee, etc.; implement as "roles with View on the configured staff channel/category", not a hard-coded list. **Create a real Discord Scheduled Event: toggle, default ON.** | BUILT (status corrected 2026-09-02; live modes per cutover-plan) |
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
4. **Global personality pool** — one trope store shared across estate bots
   (Black Bloc's `personality_tropes` + GABI's `personality.ts` unify). This is
   an ESTATE design spanning two repos: design doc first, likely a small shared
   store + sync convention; coordinate with catalog-platform docs.
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

- **Cutover, at your pace** — [`info/cutover-plan.md`](info/cutover-plan.md): prerequisites P1–P5 (channel rename, staff channel, TEST_MODE lift — the lift is yours alone), then the per-feature ladder.
- **Test sweep — the whole list lives in [`access/sweeps.md`](access/sweeps.md)** (37 rows in priority order + the detailed phase 1–8a scripts; it is the ONE home for what a person has not yet exercised).
- ~~Twitch developer app~~ **ALREADY DONE — stale line caught by the owner
  2026-08-31 ("didnt we already connect twitch dev").** Measured: `TWITCH_CLIENT_ID`
  + `TWITCH_CLIENT_SECRET` are Deployed on Fly and present in `.env`, and the boot
  log says `twitch: app token obtained` (20:13:48Z). Nothing to do.
- **Cleanup (later, owner):** kick the dormant bots `Verification Bot`, `baf`,
  `Black Block` once Black Bloc is stable.
- ✅ **DECIDED 2026-09-03 14:22 — SKIPPED (owner: "still would be YouTube? Let's skip it then.
  Back to the backlog dungeon with the music bot").** Request #3 stays on **hold**; nothing
  is built. Original: **Spotify for the music bot (owner, 2026-09-03 ~13:55: "Check if we can do
  Spotify for the music bot")** — request #3 (PT, on hold). Checked the same
  afternoon: **not as a source.** Spotify's Web API exposes no audio stream (it
  only controls a signed-in user's own Spotify client), its developer terms name
  Discord bots as not permitted, the 30-second `preview_url` was pulled for new
  apps 2024-11-27, and since 2025-05 an app needs 250k monthly users before it
  leaves development mode. What every surviving music bot does instead:
  **accept Spotify links** (track / album / playlist), resolve them to titles via
  the metadata endpoints (client-credentials, still open in dev mode), and play
  the matching audio from YouTube / SoundCloud (Lavalink + the LavaSrc plugin is
  the standard stack; needs a Java sidecar — a second Fly app — and YouTube
  increasingly blocks datacenter IPs, so that source needs its own care). Owner
  decision pending: "Spotify links in, audio from elsewhere" is buildable; native
  Spotify playback is not.

## 🔧 Open engineering items

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
- 🆕 **Second slash-command audit — list EVERY `/` command, then propose merges (owner, 2026-09-04
  clock read 20:50 after the asks: "Let's run another audit on all the slash commands and then propose what can be combined to
  minimize commands" · then: "Make sure you output all the / commands in this audit, I want a list
  of all of them").** Fable, main loop, no agent: build the real tree the way
  `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` does (`BlackBlocBot` +
  `COGS`), walk `tree.get_commands()` INCLUDING every Group's children, and the report carries the
  complete list — 36 top-level (pinned in `tests/test_bot.py`) and every subcommand — before any
  proposal. Then propose merges one decision at a time (owner rule), with a count of how many
  remain. Candidates already named by the owner, below; the audit adds the rest.
- 🆕 **`/case` + `/cases` → one panel (owner, 2026-09-04, clock read 20:50 after the ask: "Also we have case and cases for slash
  commands Let's combine those menus too").** Today `modcmds.py:696` `/case` shows one case and
  `modcmds.py:723` `/cases` lists a member's; the panel shape is `/cases [member]` → list with a
  select that opens the one-case card (moves on the card per the moderation panel design, staff
  final say). Folds into the second audit's proposals; one build, own design doc.
  **DECIDED (owner, 2026-09-04, audit proposal 2 of 6, "Yes"):** `/cases [member]` — no member = the
  server's newest cases, paged ‹ ›; a select opens the one-case card (kind, who, when, reason, note) with
  Edit reason, Add note, Void this case (reason required, DM'd); a Jump to case #… button (id modal)
  replaces `/case <id>`, which retires. 36 → 35 slots. Est. 200–260k Opus.
  **Proposal 3 of 6 DECIDED (owner, 2026-09-04, "Yes"):** the panel is spelled **`/mod [member]`** —
  the `/mod` group (only `logs`) folds in as a Logs button, so `/case`, `/cases` and the `/mod` group
  collapse into ONE `/mod`; 36 → 34 slots. The seven bare actions (`/warn`, `/timeout`, `/untimeout`,
  `/kick`, `/ban`, `/unban`, `/purge`) STAY bare — typed mid-incident with autocompleted arguments, a
  panel would be three clicks slower at the wrong moment.
- 🆕 **Honeypot → ONE slash command (owner, 2026-09-04, clock read 20:50 after the ask: "All of honeypot should be 1 slash
  commands Let's combine").** Today `honeypot.py:417` is a Group (`logs`, `setup`, `status`, `mode`,
  `forget`) with a nested `exempt` group (`add`, `remove`) — 7 subcommands. Becomes `/honeypot` →
  panel: status card, Setup…, mode select, Exempt roles (role select), Forget, Logs — the wave-3
  shape (`info/panels-program.md`). Folds into the second audit; one build, own design doc.
  **DECIDED (owner, 2026-09-04, audit proposal 1 of 6, "Yes"):** root card = today's `status`; buttons
  Setup… (name modal), mode select, Exempt roles (role multi-select replaces `exempt add`/`remove`),
  Forget (renders only when a trap is recorded), Logs. Est. 250–320k Opus. Design doc next, then build.
- 🆕 **Ticket / modmail commands → maybe one (owner, 2026-09-04, clock read 20:50 after the ask: "All ticket stuff maybe?").**
  Today: the `modmail` Group (`logs`, `block`, `unblock`, `blocked`, `mode`, `forget`) plus FOUR
  top-level ticket commands used INSIDE a ticket — `/reply`, `/areply`, `/note`, `/close`
  (`modmail.py:1131–1243`). The "maybe" is the owner's: the in-ticket four are typed mid-conversation
  with text arguments, which a panel handles with modals but costs a click. The audit proposes the
  split (a `/modmail` panel for the Group; the in-ticket four either stay, or become buttons on a
  pinned ticket card) and the owner decides.
  **Proposal 4 of 6 DECIDED (owner, 2026-09-04, "Yes"):** the `/modmail` group becomes ONE panel — root
  card = `status`; Setup… (channel selects + channels/threads mode select, replaces `settings`/`mode`),
  Blocked… (list, user select → Unblock, Block someone = user select + reason modal), Snippets… (list,
  Add modal, select → Remove — the whole `/snippet` group folds in), Forget (renders only when pointed),
  Logs. 11 subcommands over two slots → one; 36 → 33 with proposals 2–3. Est. 300–380k Opus.
  **Proposal 5 of 6 DECIDED (owner, 2026-09-05 06:25, "B"):** every ticket
  gets a PINNED staff card (member, opened-when, block state) with Reply (modal: text + snippet select),
  Reply as Staff, Private note, Close… (reason modal + silent toggle). **`/reply` stays bare** (the one
  typed constantly); `/areply`, `/note`, `/close` retire into the card. 36 → 30 with everything so far.
  **Proposal 6 of 6 DECIDED (owner, 2026-09-05 06:27, "Yes that's fine"):** `/presence apply`
  folds into the `/settings` panel as a Re-apply presence button (one slot freed); **`/settings` stays a
  group for now** (the escape hatch every panel points at; `<key>` autocompletes ~80 keys) — its own
  panel design comes AFTER the hide-when-off build, which adds a key. **Audit result: 36 → 29 slots;
  the only group left is `/settings`.** Build sequence: honeypot → `/mod` → modmail (+ snippets + ticket
  card) → presence-into-settings (folds into whichever build touches `cogs/core.py` first).
  **Owner, 2026-09-05 06:36: "Maybe /reply could be a menu. Walk me through that one again and through
  /settings. Start the rest in the meantime"** — proposal 5 reopened (`/reply` as a button/menu too) and a
  `/settings` panel walk-through requested; both answered one at a time, decisions land here.
  **`/reply` DECIDED (owner, 2026-09-05 06:41: "I think we do the both… We should have the buttons always
  appear to click reply at the bottom of a channel but also a /reply so they can just start typing a
  response"):** the staff card (Reply / Reply as Staff / Private note / Close…) is RE-POSTED at the bottom
  of the ticket after every member message so the buttons are always the last thing in the channel (the
  previous card's view is stopped, `ui/view.py` gotcha), AND `/reply` stays a bare command. `/areply`,
  `/note`, `/close` still retire into the card. Tickets are one channel each by default (`modmail_mode`
  `channel`; `thread` is the other choice) — the card works the same in a thread.
  **AMENDED + `/settings` DECIDED (owner, 2026-09-05 06:46: "Okay ship both with your suggestions"):**
  (1) the card is a STICKY message — on each member message the old card is deleted and a fresh one posted,
  so exactly one card exists, always last, one in the transcript; (2) the reply style is a SETTING
  `modmail_reply_style` (`buttons` / `typing relays` / `both`, default `both`) — in `both`/`typing`,
  a plain message typed by staff in the ticket relays to the member; (3) the staff panel carries **Try a
  fake ticket** — a practice ticket in the test channel with a fake member the owner "speaks as" from a
  button, so all three styles get tried under test mode, no throwaway mock; (4) `/settings` becomes the
  cross-cutting panel (option (a)): root shows every feature's mode read-only with "open `/x` to change",
  cards for the keys with no feature panel (staff/lead roles, log channel, `hide_commands_when_off`,
  panel-minutes, presence + Re-apply presence), Logs; `show`/`set`/`set-role`/`set-value`/`clear` retire —
  29 slots, ZERO groups. Sequence: hide-when-off (in flight) → honeypot → `/mod` → modmail → `/settings`.
  **DISPATCHED 06:36:** the hide-when-off build (Opus, own worktree off `cc18993`; usage at dispatch session 1% /
  weekly 5% / Fable 6%, read 06:25). Honeypot / `/mod` / modmail designs follow.
- **Wave-1 review findings, small, fold into the next build that touches each file (Fable
  review 2026-09-03 13:50–14:05):** `requests.py` re-renders lack `allowed_mentions`;
  `LOG_LEVEL_COMMANDS` help still says "`/birthday logs`" / "`/request logs`"; five form writes
  are logged twice (cog and API); `role_menus.py:392` re-implements `panels.answer()`;
  `chat.py:483–488` and `personas.py:75` still say `/request create` / `/request list`
  (`tests/test_chat.py:158` pins it) and `code-notes.md:3451` has the same stale name;
  `NO_ANNOUNCE_CHANNEL` is dead in `events.py`; events `confirm_cancel` Yes button does not
  re-run `may_cancel` (trusts the panel's opener pin); polls: `draft` status never written, no
  create-recurrence web route, (`OWNER_GUIDE.md` polls row added at the v65 landing). From the
  applications build (2026-09-03 14:55): `tests/test_bot.py::test_every_feature_group_has_a_logs_command`
  shrinks with every panel wave (each deletes a `LOGS_GROUPS` entry) — re-express the guarantee
  against the panels' **Logs** button before it covers nothing; `role_menus.py:answer()` is still a
  byte-for-byte copy of `panels.answer`; `architecture.md`'s "current" command counts are stale
  (a ⚠️ line names the real figures); `applications.py:NOT_YOUR_APPLICATION` / `NO_REVIEW_CHANNEL`
  look dead; `OWNER_GUIDE.md` restates the sweeps count (95) instead of linking — two homes for one
  number. From the golive build (2026-09-03 17:05, Fable review): the four earlier `*_panel_minutes`
  keys (event/poll/birthday/request) have no label in `site/public/assets/labels.js` or
  `site/mock/server.mjs` (memory and golive do); every panel's **Logs** button drops `count` /
  `important_only` (wave 1 shape — a modal if wanted back). From the pings build (2026-09-03 18:25,
  Fable review): `pings.panel_buttons` only offers **Take my ping role away** while `pings_mode` is on,
  so a streamer who already has a role cannot drop it from the panel with pings off (fork I1 said
  "always", the mode gate wins — decide whether the button should render regardless of mode); the
  youtube cog keeps its own `site_page_url` (returns `""` where `panels.site_page_url` returns `None`)
  — fold it at the next youtube touch; `code-notes.md` pings keys are anchored to the branch, not
  `a5ad521` — re-key at the next merge. **From the wave-3 design docs (2026-09-04 09:21–09:33,
  REPORT-not-fix until their builds):** the website can set `automod_mode=on` through the generic
  settings API, which validates against `KEY_CHOICES` only — neither arming refusal applies on the web
  path, so a guild with no resolved staff can be armed from the dashboard (`KNOWN_ISSUES` candidate;
  the fix is wiring `set_mode` into the settings route, a settings-API pass, not a panel change);
  `LOG_LEVEL_COMMANDS["pings"] = "pingroles"` (`settings_store.py`) names a wave-2-retired command and
  every other `LOG_LEVEL_COMMANDS` row goes stale as its panel lands — re-express against the Logs
  button; `/role revoke` is named in four places (`applications.py`, `OWNER_GUIDE.md:86`, `sweeps.md:254`,
  `applications-panel-design.md:130`) and has NEVER existed — the role-menus build's `End it now` makes
  it real; `site/mock/server.mjs:63`'s copy of `ROLE_MENUS_OFF` has already drifted from the real string;
  `panels-program.md` §3 undercounts role menus (17 → 18); `rolemenu_log_level`'s registration site was
  not read line-by-line (generated by the log-level family) — the build confirms it.

- 🔧 **Confirm-helper fold — FIVE copies now (deferred from the v74 merge, 2026-09-04 15:40):** the
  Keep it / Yes card is built separately in `cogs/community/chat_memory.py` `open_confirm`,
  `cogs/community/birthdays.py` `open_confirm`, `cogs/content/youtube.py` `open_confirm`,
  `cogs/content/pings.py` `open_confirm` and `black_bloc/automod.py` `build_confirm` + `confirm_buttons`
  (the automod one is pure-module-shaped, the other four are cog-shaped — that difference is why it was not
  folded at the merge). One `panels.confirm(...)` in `black_bloc/panels.py` with tests in `tests/test_panels.py`,
  the five callers delegating; checklist 15/17. Its own Opus sweep AFTER wave 3 (the chat, raidtrain and
  role-menus builds each add a confirm card of their own — fold once, after the last one lands, not three
  times). **Chat landed 2026-09-04 (v75) and made it SIX** (`RemoveYesButton` / `KeepItButton` in
  `cogs/content/chat.py`). **Same sweep, second helper:** the `still_staff` / `defer` / `db_ready` triplet is
  repeated **14×** in `cogs/content/chat.py` where automod carries a cog-local `opened()` — one
  `panels.opened(...)` beside `panels.confirm(...)`, both callers' copies delegating (chat review finding,
  non-blocking). **Raidtrain landed 2026-09-04 (v76): a SECOND cog-local `opened()` in
  `cogs/content/raidtrain.py`, and its `Outcome`/`refusal` fold into `panels.py` is DONE (chat imports
  them from there now). Role menus adds a SEVENTH confirm (`confirm()` in `cogs/community/role_menus.py`)
  and a `ready()` that is `opened()` under another name.** Est. 120–180k.
- 🔧 **`LOG_LEVEL_COMMANDS` is stale for eight features (report from the automod build, 2026-09-04):**
  `settings_store.py` still names `tempvoice` (now `voice`), `events` (now `event`), `poll`, `birthday`,
  `golive`, `request`, `applications` (now `/apply`) and `pings` (`pingroles`, retired) as the command that
  reads each log level — every one of those became a panel's **Logs** button. One pass: re-express the help
  text against the Logs button per feature and re-express
  `tests/test_bot.py::test_every_feature_group_has_a_logs_command` (already on the small-findings list) against
  the same thing before it covers nothing. Fold into whichever wave-3 build touches `settings_store.py` last,
  or its own Sonnet sweep. Est. 60–90k.
- 🔧 **Settings-API gate pass (KI-21, 2026-09-04):** the generic PUT in `api/settings_api.py` validates
  against `KEY_CHOICES` only, so the website can set `automod_mode=on` past both of the panel's arming
  refusals. Route the write through `cogs/moderation/automod.py:set_mode` with `via=website` (the youtube and
  pings routes already call their cog's shared moves), then audit every other key that has a cog-side gate
  for the same gap. Not a panel change — its own item, after wave 3. Est. 90–140k.
- **Via-labelling gap: `raidtrain.cancel_train` logs one row but calls a website cancel
  Via = Discord** (found by the double-logging build, 2026-09-03 — see `DONE.md` that
  date). Not a double post, so out of that fix's scope. Audit every shared function a
  route calls that does NOT yet take `via` (start from the `kind_via` call sites and the
  `tests/test_logkinds.py` AST walk's `SHARED` map), thread `via=` through, and add each
  to `tests/api/conftest.py:one_web_row`. Small; fold into the next requests/raid-train
  build rather than dispatching on its own.

- **Review the incoming member requests (owner, 2026-09-02 ~19:55: "we got some
  request in our /request features lets review them").** Read what has landed
  via `/request` (Requests page, `/api/requests`), present them to the owner one
  at a time, record each decision (accept → a TODO item; decline → the reason)
  and close them out on the Requests page. **Live read 2026-09-03 14:25 (`requests` table via
  `flyctl ssh`, owner-authorised): #1 done (Pawpette marked it), #2 review (→ done when `/apply`
  ships, v66), #3 hold (Spotify skipped 14:22), #4 "Do" done (a test).** Three in (all staff-filed →
  auto-approved, unassigned): #1 Pawpette — raid-train scheduler replacing
  r3dlabs.com (owner: "can we capture all the features of this tool" →
  [`info/raid-train-capture.md`](info/raid-train-capture.md), full inventory
  bucketed); #2 Pawpette — Twitch Team application form via the bot, staff
  approval; #3 PT — built-in music bot for the lounge/cowork voice channels.


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
