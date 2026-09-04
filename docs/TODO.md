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

## 🔁 IF THIS SESSION DIES — resume here (refreshed 2026-09-04 09:35, v73 live, wave-3 DESIGNS LANDED, forks to the owner next)

**`main` = `4d64b36`** (voice panel merge; v73 live 22:08, 4265 tests, **38 commands**; `youtube_mode` is
**shadow** since 17:42). Panels wave 1 AND wave 2 are COMPLETE (memory v68, golive v70, youtube v71,
pings v72, voice v73); all five landing entries are in `DONE.md` 2026-09-03. The operator read token is
LIVE (v72; moved whole to `DONE.md`). **Wave 3 is next** (`info/panels-program.md` §5: raidtrain · role
menus · chat · automod) and follows the program ritual — Opus design doc per feature (~200k each), Fable
review against §2, owner forks ONE AT A TIME, then Opus builds in their own worktrees off `main`, sweeps
144+; usage read before every dispatch; weekly cut-off 90%. **Next:** (1) wave-3 design docs; (2) their
forks to the owner one at a time, builds in cost order, merge/deploy each as it lands; (3) the
small review findings (🔧 below) folded into whatever touches those files; (4) owner by-eye sweeps
14–15, 58–103; (5) Pawpette's Twitch Team form still needs the owner's walk-through
(`access/sweeps.md` → "The owner's Twitch Team form") — no form exists on the live site as of 15:54. Merged
worktrees/branches (`agent-a19bdce15408f8243` birthdays, `agent-a448c7ab780ed3c2b` events,
`agent-aa735ab092d13477d` polls, `agent-abf063b9177e02f17` applications) can be pruned.

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
  recorded here as they come. Then builds in cost order (automod ~300–360k, chat ~300–360k, raidtrain
  380–450k, role menus 420–500k), each Opus in its own worktree off `main`, layer-boundary commits, sweeps
  numbered from 144 at build time; usage read before each dispatch; weekly cut-off 90%.
  Events I2 DECIDED 12:40 (`/timezone` retired).
  **Wave-1 builds all landed 13:40–13:50** (birthdays merged `58974e1`; events on
  `worktree-agent-a448c7ab780ed3c2b`, polls on `worktree-agent-aa735ab092d13477d`, both under Fable
  review); the applications build follows once I-A3 is answered. Merge in wave order, re-key
  `code-notes.md` per merge, deploy per landing. ⚠️ The v63 deploy REFUSED at the gate 13:52 on the
  rate-limit flake — fixed by freezing the clock in the test (`code-notes.md` →
  `tests/api/test_settings_api.py:221`), three `-n auto` runs green; **v63 live 13:58, v64
  (events, `e670542`) live 14:05** — both landings recorded in `DONE.md` 2026-09-03. Polls merged
  `27452ac` (3644 tests), **live in v65** (`d13e1a4`, 14:14) — landing entry in `DONE.md`.

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
