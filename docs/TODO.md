# Black Bloc — TODO (active work only)

> **Audience:** Claude sessions and the owner. **Status:** LOCAL ONLY (gitignored 2026-08-26).
> Last verified: **2026-08-27**.
>
> Finished items MOVE whole to [`DONE.md`](DONE.md) in the session they land.
> Accepted defects go to [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md), not here.

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

Status: **BUILDING IN PARALLEL (owner, 2026-08-26 20:38: "do what you can to start working in parallel").** **EVERYTHING BUILT SO FAR IS LIVE — `256f43d`, 2026-08-27 07:46 Phoenix, 1195 tests, 30 slash commands, schema 11:** seven core phases (shadow/test mode), the full dashboard (53-route write API, 13 tabs, UX pass, security-reviewed), `/voice` + panel + complete per-user memory, `/help`, bot About Me + "Cookout attendees: N" status, parity/Carl removed, Health tab lists all 7 loops. Owner's test sweep in progress; feedback → batches. `deploys.log` has every deploy. Phases 5, 6, 7 building in git worktrees under `.claude/worktrees/` (gitignored) on their own branches, schema versions pre-assigned 6/7/8, shared files touched append-only. **Merge order: Phase 4 fixes → deploy → merge 5 → review/fix → merge 6 → review/fix → merge 7 → review/fix; re-key `code-notes.md` after each merge; deploy from `main` only.** If a session inherits this mid-flight: `git worktree list` shows the branches; never deploy with a dirty main tree. Build order
approved (Q13): see `info/feature-list.md`. Design docs: `info/phase1-design.md`
(settings, action log, role menus), `info/phase2-design.md` (go-live feed);
later phases get theirs before dispatch.

**Autonomy (owner, 2026-08-26 18:15): "keep going and only stop building the
phases if im needed for a critical choice. I can do a big test sweep when i get
back."** So: each phase = design → Opus build → Fable review → deploy in
TEST_MODE/shadow → next phase; owner does one consolidated test sweep later.
Every phase landing gets a `DONE.md` entry and a "what to click" list under
**Test sweep** below.

**F12 website placement (owner asked 2026-08-26): Phase 8, immediately after
the seven core phases.** Phase 1's settings store + audit log and the existing
FastAPI module are built as its foundation.

**Rollout rule (owner, 2026-08-26):** Black Bloc eventually replaces ALL of
Birthday Bot, Carl-bot, Modmail and YAGPDB — "rome wasn't built in a day".
Every feature that acts on members ships **shadow/log → watch → on**, flipped
per feature, so the old bot keeps running until the new one is proven.

| # | Feature | Open questions (answers land here) | Status |
|---|---|---|---|
| F1 | **Go-live → `#live-now`** | **DECIDED 2026-08-26: BOTH** — presence for discovery of anyone, Twitch EventSub (websocket) for rich posts on linked accounts; opt-out covers both. **PRIMARY = Discord presence/activity; Twitch EventSub is the FALLBACK/enrichment** (owner, 2026-08-26). **Measured incumbent (rescan):** YAGPDB posts ~8/day, 30 distinct streamers, template `REGULATORS! Mount up! **{login}** is currently streaming **{game}**! Check it out: https://www.twitch.tv/{login}` — keep the prefix; 4/199 posts render game as `****` (no category) → need a fallback; Twitch login ≠ Discord name (`thepresidentnoir`→`twitch.tv/prez`) → `/twitch link` is mandatory; YAG re-posts on restart/category change → **debounce**. Rich card = Discord's own link preview (free). Channel topic is stale ("post your links here") — fix when F1 ships. | design |
| F2 | **Twitch activity tracking** — **DECIDED 2026-08-26: YAGPDB "Streaming"-style.** Presence-based; when a member goes live post "X is live" (+title/link) to the channel; optional *Live* role while streaming; require-role / ignore-role filters; opt-out. No stats/leaderboard. Merges with F1 (one design doc). "Scan for inactive" still TBD. | design |
| F3 | **YouTube** — *maybe* | Go-live only, or uploads too. Parked until F1 lands. | parked |
| F4 | **Event form → Discord Scheduled Event**, via review | **DECIDED 2026-08-26 (all blanks filled):** `/event create` **modal**. **Timezone:** Discord exposes no user timezone to bots (only language locale) → entered once via `/timezone set` with city autocomplete, default = server zone (America/Phoenix). **Review = a channel per submission** (like Modmail today) under an **Events** category, named `<status>-<user>-<event>` e.g. `pending-sky-block-party` → renamed `approved-…` / `denied-…` (Discord channel names are lowercase a-z0-9-_ only, so `!` and spaces are normalised). **Approvers = anyone who can see `#mute-me-bot-test-spam`** — i.e. Aunties/Uncles, Leads, Committee, etc.; implement as "roles with View on the configured staff channel/category", not a hard-coded list. **Create a real Discord Scheduled Event: toggle, default ON.** | design |
| F5 | **Ping when an event goes live** | **DECIDED 2026-08-26:** announce in **`#live-now`** (channel set in an options menu); **role ping is a setting**, default *none* (YAG pings nobody today). See F14 for the roles. | design |
| F14 | **Ping roles** (owner, 2026-08-26): an opt-in **Events** role for go-live/event pings, and **favourite-streamer roles** — per-streamer opt-in pings ("people that want to see SuperNamu only … can get her pings"). Wire into F1/F5 announcements and the role menus. | future |
| F6 | **Birthday announcements**, opt-in, with a "cutover time" | **Seed data:** Birthday Bot export (39 rows) at `archive/current-bots/birthday-bot-export-2026-08-05.md`. **Measured incumbent (rescan, 16 posts):** channel **`#return-of-the-gen`** (`1411816390414962700`), an embed `Happy Birthday **{display_name}**!` colour `#4eefff`, no ping, no role; fires at **≈00:03 local midnight in a PER-MEMBER timezone** (UTC-4 ×8, -5 ×4, -6 ×2, -7 ×1, +1 ×1) — contradicts the bot's own "server time zone" blurb. 🔴 **Phoenix gotcha: 15 of 16 landed the evening BEFORE the birthday in Phoenix terms.** **DECIDED 2026-08-26 (Q12): per-member midnight** (uses the F4 `/timezone` store); **fallback = server midnight (America/Phoenix)** when a member has no timezone set. The `🎂` role's grantor is unknown (Birthday Bot lacks manage_roles). | design |
| F7 | **Moderation** — copy the *usual* settings from other bots; exceptions list fine-tuned later (mass pings, role-based exceptions) | **Carl's live config captured** (`archive/current-bots/carl-bot-dashboard-2026-08-26.md`): only mention-spam (5/30s → delete+warn+5-min timeout) is armed; whitelists empty; warn threshold 8 with no punishment. **YAGPDB automod measured OFF.** `#carlbot-logs`: 7 warn cases in ~2 years — quiet server, do not over-tune. **DECIDED 2026-08-26 (Q11): "follow what exists"** — reproduce Carl's live config as-is (mention-spam 5/30s → delete+warn+5-min timeout; everything else log-only), warn/timeout/kick/ban commands, modlog, exempt roles = staff set; **tune in shadow mode**, change later. | design |
| F8 | **Temporary voice channels** — replicate tempvoice.xyz | **DECIDED 2026-08-26:** one creator voice channel named **"join to create a channel"** in the existing voice-channel area, positioned **directly above "You Still Here?"** (the AFK channel — keep it above, never below); spawned channels named **`{user}'s bloc`**, placed next to the creator, deleted when empty; owner control panel (rename / limit / lock / hide / kick / ban / claim / transfer) per `info/reference-bots.md`; usable by **`Member`** to start. | design |
| F9 | **Honeypot** — replicate honeypotbot.com | **DECIDED 2026-08-26:** honeypot channel(s) at the bottom with a pinned "do not post here" notice; anything posted → **ban + purge messages**, shipped **shadow-first** (log would-ban for a week, act on nothing) then enforce. **Exempt:** all bots + anyone who can see the staff channel (same rule as F4 approvers). **Log channel:** `#mute-me-bot-test-spam` for now — the owner will **rename it to `#black-block-logs`** (spelling confirmed 2026-08-26) when the bot leaves test mode; the log channel is a setting, so the rename costs nothing. The scan found no existing honeypot channel; Carl's honeypot section is unconfigured. | design |
| F10 | **Conversation when @-mentioned** ("@'d", owner clarified 2026-08-26): when someone pings the bot it holds "some semblance of a conversation" — an LLM-backed reply. | **PARKED by owner until after core features.** Needs an LLM provider + key + a cost cap; personality/tone TBD then. | parked |
| F11 | **Modmail** (added by owner 2026-08-26 — replaces the Modmail bot) | **DECIDED 2026-08-26: do what the current bot does (channel-per-ticket in the ModMail category, topic `ModMail Channel <user-id> <channel-id>`), AND wire a second mode — private threads in one staff channel — as a setting** ("wire up the option to be in 2 channel"); the toggle is ported to the F12 website later. Reference: `info/reference-bots.md` (Modmail command table). | design |
| F13 | **Verification Bot** — **rescan result: dormant** (1 message in ~2 years, its own join notice); no use cases to port. Also found dormant: `baf#0659` (a Red-DiscordBot install, ~1 yr idle) and `Black Block#1423` — **two prior attempts at this project**. Recommend kicking all three once Black Bloc is stable (owner action; on the cleanup list). `Wordle` is a Discord built-in activity webhook (422-day streak) — leave it alone. | closed → cleanup |
| F17 | **Role-process takeover + audit** (owner, 2026-08-26: "grab all the roles and settings carl already has so we dont need to recreate them, same emojis too … audit each user and their roles so we can take over that process") | **Audit captured:** `archive/current-bots/role-audit-2026-08-26.md` — 118 humans, 7 bots, 59 roles, every member's roles, per-role counts, self-assign holders; **4 humans lack `Member`** (simonebwest, FFStreamWatcher, scrybaby, UraniumAnchor), 1 has no roles (scrybaby). Carl's panels/emojis already reproduced by `/rolemenu seed-defaults`; **fix:** Marathons must use Carl's custom emoji `<:JoyGAMING:1337948924844965931>` instead of 🎮 (do at Phase 2 review). **DECIDED 2026-08-26:** `Member` is granted by **Discord's own rules screen** (owner: "i think discord rules") — Black Bloc does not take over the gate; the 4 non-Members are for the owner to handle by hand. **YAG's 3 role-command groups become Bloc menus:** *Student/Teacher* folds into the existing `mentoring` panel (Mentor/Initiate); *Runner Status* (Runner / Live Runner / Commentator) becomes a **staff-assigned** set via a new `/rolemenu` mode `staff` (staff picks the member, not self-serve); *Rule Reader* is redundant with the Discord rules screen — dropped. "We can change later." → add to the next builder's scope (Phase 3 rider). | decided — build in Phase 3 |
| F12 | **Config website for mods/admins** — **DESIGNED 2026-08-26: `info/phase8-design.md`. Owner decisions 2026-08-26 18:30 (verbatim): "we can use blackbloc.heygabi.ai for now until the org decides on a name and then we port it to that domain … this site needs to be entirely disconnected from heygabi … discord login verification only except my google sso as the owner admin of the whole domain … we'll need to link my discord verification to my google sso in the future. only people/roles who can currently see the spam channel we're testing in should be able to get on the bot, aunties/uncles mainly and the roles above it."** Static site on Cloudflare Pages wearing the estate template (`estate-theme.css`, `theme.js` 5-theme dropdown, `permission-ux.js`, fonts from `catalog-platform/sites/heygabi-home`), Discord-OAuth login gated on the same staff-role rule as slash commands, FastAPI routers inside the bot process on Fly, 12 pages mapped from Carl/YAG dashboards onto F1–F16, one settings store + audit. **8a read-only status page can ship right after Phase 2; 8b full dashboard after Phase 7.** Owner decisions deferred to then: hostname, Discord-only vs +estate SSO, who may edit moderation rules. | designed — Phase 8 |

## 🧪 Owner test sweep — round 1 findings (2026-08-26 ~22:55)

Four findings, all four **fixed on `main`, committed, NOT pushed and NOT
deployed**: `8fe0677` (temp voice) and `9d948ca` (role menus + `/twitch link`).
817 tests pass, ruff clean. What is still open is deployment and live
re-verification.

| # | Owner's words | Fixed by | Still to do |
|---|---|---|---|
| 1 | *"we need a /rolemenu showall to display all role menus"* | `9d948ca` — `/rolemenu showall`, chunked at 1900 chars, ephemeral, no pings | deploy + sync commands, then run it |
| 2 | *"for /twitch link it should say channel name not login, login sounds more concerning"* | `9d948ca` — parameter renamed to `channel`, no user-facing sentence says *login* | deploy + sync (a renamed option needs a command sync), then re-read the picker |
| 3 | *"it made a locked channel i cant get into. its just a lock icon."* | `8fe0677` — explicit overwrites (allowed role + resolved staff + the bot), and `/tempvoice setup` now REPAIRS the lobby it already has | deploy, then run `/tempvoice setup` again — it should say **repaired**, rename `join` (id `1542410969815453767`) back to *join to create a channel*, and let Member + staff connect. Then join it. |
| 4 | 8a merge left `TempVoice._reconcile_loop` with no `@loop.error` and no health | `8fe0677` — handler + `last_ok_at`/`last_error` + `loop_health()` | deploy, then check the status page's Loops row for `_reconcile_loop` |

⚠️ **Root cause of the `join` name, measured not guessed:** nothing in the cog
truncates a channel name. `channel_name` is the only string handling in the file
and is not on the setup path; the command's `name` parameter introspects as
optional with default `None` (`Command._params["name"].required is False`), so an
unsupplied name renders the full default. The only way to get `join` is Discord
having sent `name: join` — a value typed into the optional field. The fix is
therefore a real setting (`tempvoice_creator_name`) plus a repair path, not a
truncation bug fix: there was no truncation to fix.

## ⏳ Waiting on the owner

- **Answers to the F-table questions above** — being asked one at a time.
- **Test sweep** (when the owner is back) — accumulating list of what to click,
  filled per phase as each lands:
  - **Phase 1 (live):** in `#mute-me-bot-test-spam` run `/settings show` (expect the
    three keys with the test channel as default) → `/rolemenu seed-defaults` →
    `/rolemenu list` → `/rolemenu post pronouns` → pick roles on the panel (expect an
    ephemeral "Added: …/Removed: …" and your roles change) → `/rolemenu show
    interests`. Try `/rolemenu list` from a non-staff account: expect the staff
    sentence. Check the action-log embeds landed in the same channel.
  - **Phase 2 (live, mode `shadow`):** `/golive status` (expect mode shadow, channel =
    test channel, Twitch polling running with a last-ok time) → `/golive test` (ephemeral
    preview, no ping) → `/twitch link <your login>` (expect "linked" or "could not be
    checked") → go live on Twitch once with Discord showing the Streaming status: expect
    a `golive.would_announce` embed in the test channel within seconds (presence) — and
    nothing in `#live-now`. Stop streaming: expect `golive.end` ~2 min later. Try
    `/golive optout` then `/golive optin`. `/settings show` now lists the 8 golive keys.
  - **Phase 3 (live; honeypot `shadow`):** `/tempvoice setup` (expect a "join to
    create a channel" voice channel created INSIDE the test channel's category while
    TEST_MODE, and the reply saying so) → join it: expect `<you>'s bloc` to appear next
    to it and you moved in; ⚠️ **the control panel IS posted now** (batch-3 merge
    2026-08-27) — it goes into `#mute-me-bot-test-spam` with a first line naming the
    voice channel it controls, logged as `tempvoice.panel_elsewhere`, and **its
    buttons work from there**; press Rename and Lock → leave: channel deleted within
    ~60 s. `/tempvoice status`. Also try the new group: `/voice info`, `/voice
    bitrate`, `/voice region`. Then `/honeypot setup` (trap created in the test category; notice skipped
    in test mode) → post in it from a throwaway account: message deleted, a
    `honeypot.would_ban` embed with a **Ban now** button in the test channel; nobody
    banned. `/honeypot status` (expect the resolved staff-role count > 0). Role rider:
    `/rolemenu seed-defaults` again (expect "already there" for the five, created
    `runner-status`) → `/rolemenu assign runner-status @someone` (staff picker) →
    `/rolemenu post event-alerts` shows the real `:JoyGAMING:` emoji only if you
    delete and re-seed that menu (the seed never rewrites existing options).
  - **Phase 4 (live):** `/timezone set America/Phoenix` (autocomplete; expect the current
    local time back) → `/event create` (modal, 5 fields; start `YYYY-MM-DD HH:MM` about
    3 minutes ahead, duration `30m`) → expect a `pending-<you>-<title>` channel INSIDE
    the test category and the review card posted in the test channel with Approve/Deny
    → click Approve: channel renamed `approved-…`, announcement in the test channel,
    `event.would_create_scheduled` in the log (no real scheduled event in test mode),
    DM to you → wait for start: "starting now" post; after the end: `done-…`. Create
    a second one and Deny it with a reason: `denied-…` + DM. `/event list`, `/event
    settings` (shows loop health), `/event cancel <id>`.
  - **Phase 5 (live, mode `shadow`):** `/birthday import` (staff; expect a report:
    N imported / ambiguous / not found, searched 118 members) → `/birthday next` →
    `/birthday list` → `/birthday set <today's month> <day>` for yourself → within 5 min
    expect a `birthday.would_announce` line in the test channel (flip `/birthday mode on`
    to see the actual embed, colour `#4eefff`) → `/birthday status` (loop health,
    resolved staff) → `/birthday remove`. `/settings clear birthday_role_id` exists now.
  - **Phase 7 (live, `modmail_enabled` false):** `/modmail status` (resolved staff,
    loop health) → `/modmail settings enabled:true` → from a second account DM the bot:
    expect a ticket channel `<username>` INSIDE the test category, the header card +
    your DM relayed into the test channel (guarded send), ✅ on the DM → in the test
    channel `/reply ticket:<n> hello` (relayed to the DM, shows your name) → `/areply`
    (shows "Staff", default colour) → `/note` or a message starting `=` (never
    relayed) → `/close reason:done` → transcript `.txt` + summary in the test channel,
    DM to the member. Try `/snippet add`, `/modmail block`. Then `/modmail settings
    enabled:false` again so the incumbent keeps the real tickets.
  - **Phase 6 (live, automod `shadow`):** `/automod status` (mode shadow, resolved staff,
    rules: mention_spam armed, others log-only) → from a second account post 5 @mentions
    within 30 s in the test channel: expect ONE `automod.would_*` case card with an
    **Apply now** button (nothing deleted/timed out), and a following "sorry" message
    does NOT re-fire → `/warn @second reason` (allowed) → `/timeout @second 5m x`
    (expect the test-mode refusal + `mod.would_timeout`) → `/cases @second`, `/case 1`
    → `/settings show` (chunked, no 400). `/automod mode on` must REFUSE while the
    staff channel is still the test channel.
  - **Phase 8a (live):** open https://blackbloc.heygabi.ai → expect the signed-out
    state with a "Sign in with Discord" button (no bare errors) → sign in (Discord
    authorise; you are staff via Manage Server) → expect the dashboard: health, uptime,
    7 feature mode chips (all shadow/off/on as set), loop health per cog, the last 50
    action-log rows (your sweep's `would_*` lines should be there), open counts. Theme
    dropdown: 5 themes. Try a second, non-staff account: expect the amber "not staff"
    sentence. Sign out → signed-out state again.
- **Twitch developer app** — owner is creating it (2026-08-26); `TWITCH_CLIENT_ID` /
  `TWITCH_CLIENT_SECRET` go in `.env`. Fallback path only; F1 ships on presence first.
- **Cleanup (later, owner):** kick the dormant bots `Verification Bot`, `baf`,
  `Black Block` once Black Bloc is stable.

## 🔧 Open engineering items

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
  A's shell + B's tables, mock A and C). ⏸ **Four owner questions at the end
  of that doc are unanswered and block step (3):** dark-only vs both · keep
  the 5-theme dropdown? · nav icons or text-only · which direction;
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
  pages read present. NOT pushed, NOT deployed — that is the next step, and
  batch 3 (below) merges first or after, but the two touch `tempvoice.py`.
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
- **Test-sweep batch 4 LANDED on `main` 2026-08-27, NOT pushed and NOT deployed**
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
  `node site/mock/check.mjs` clean. NOT pushed, NOT deployed, NOT run against a
  live bot.** Still to do: review the merged `tempvoice.py`, deploy, then the
  owner tests the panel in `#mute-me-bot-test-spam` (press Rename and Lock from
  there — the click has to find its way back to the voice channel) and
  `/voice info` / `/voice bitrate` / `/voice region`. Owner also had the stale
  `🍯-do-not-post-here` trap deleted (2026-08-26 23:33) — `/honeypot setup`
  recreates it.
- **Test-sweep batch 2 FIXED on `main`, NOT pushed and NOT deployed** (see
  `DONE.md`, 2026-08-27): `/help` and temp-voice lobby adoption. Still to do:
  deploy, sync commands, then (a) run `/help` and `/help filter:temp` and check
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
- **Fly secrets gotcha (2026-08-26):** piping python output into `flyctl secrets
  import` from PowerShell prepends a UTF-8 BOM to the first key name ("\ufeffTWITCH_…
  is not a valid secret name"). Write an ASCII temp file and redirect it with
  `cmd /c "flyctl … < file"`. → move to `access/deploy.md` (done below) and gotchas.

- **Curated docs for peers** (owner, 2026-08-26: "give them the curated docs
  they need"). `docs/` is now local-only; the repo's `README.md` is the only
  peer-facing doc. Open: what the curated set should contain (setup? command
  list? contribution rules?) and whether it lives in `README.md` or a tracked
  `docs-public/`-style folder. Ask the owner when the first peer needs it.
- **Back up `docs/` off this machine** — it is local-only now (RECOVERY gap).

- **Bot access RESOLVED 2026-08-26 ~18:00:** owner gave `Black_Bloc` the `Bots`
  role (carries Administrator — owner accepted: "it'll need to do moderation
  roles eventually"). Rescan then read 128/128 channels.
- **Role menus (new feature row needed at design time):** Carl's 5 reaction-role
  panels with measured emoji→role maps are in `archive/current-bots/discord-scan-2026-08-26.md`
  §D (gotchas: skin-tone emoji in text vs plain in reactions; 🧑‍🍳 is a ZWJ
  sequence). YAGPDB has NO role menus despite "7 role commands" on its dashboard.
- **Move the SQLite file out of the OneDrive-synced tree** — KI-1.
- **Twitch developer app** (`TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`) will be
  needed for F1/F2 if EventSub or Helix lookups are in the design.

- **Owner 2026-08-27 ~11:49, verbatim: "Probably should make a deploy button api so you can deploy for me if you can't permission"** → idea logged. Today: the owner's standing authorisation works — the last four deploys ran from the session. A deploy endpoint on the bot would need a Fly API token on the machine and a self-redeploy path; higher risk than value while the session can deploy. Status: **parked unless the classifier blocks again.**

- **Owner 2026-08-27 ~12:09, verbatim: "Stop at 90 weekly so we can save some headroom"** → project rule: no new agent dispatch at ≥ 90% weekly (global rule says 93); builds in flight land, nothing new starts; saved to memory. Status: **in force (weekly 83% at 12:02).**



- **Owner 2026-08-27 ~17:14, verbatim: "i think we need to pipe a lot of the logs to the website and a logs command per function and keep the discord spam to a minimum"** → Phase 12 "Logs": (1) every action still lands in the DB (the action log already does) but the Discord log channel only gets **important** kinds — a per-feature `<feature>_log_level` (`off` / `important` / `all`, default **important**) with "important" = acted on a member (warn/timeout/kick/ban/role grant/approve/deny/expire) or FAILED; shadow `would_*`, housekeeping (imports with 0, panel reposts, reminders, sweeps, `chat.*`, `poll.created`) stay off Discord; (2) website: a per-feature **Logs** section on every feature page (recent actions by kind prefix, search, kind chips, pager) + a global Logs page (all kinds, actor/target filters, CSV export) — the Audit tab becomes that page; (3) slash `/<feature> logs [count]` (ephemeral, last N from the DB) on every feature group. **Decision (owner ~17:17): "a is fine, also any approvals need to make notifications still"** → default "important" = acted on a member OR failed; and every approval REQUEST (role requests, poll reviews, event proposals) still posts its card/ping to its approval channel regardless of log level — those are notifications, not log lines, and are never filtered. Status: **owner "send it now" (17:23, weekly 88 — overriding the reset hold) → 12a dispatched 17:24 off `0090fd8`; 12b when 12a lands if weekly < 90, else after the Sunday 16:00 reset.**

- **Owner 2026-08-27 ~17:27, verbatim: "im getting on a plane tomorrow morning (friday and im not back until sunday night after reset) so we have wiffle"** → the 90% weekly stop is lifted for THIS window only (owner away Fri 08-28 → Sun 08-30 night; weekly resets Sun 16:00): spend the remainder on 12b now (parallel with 12a); at the Sunday reset, a one-shot wake-up resumes with the audit leftovers B4–B8 (temp-voice per-room actions, role-menu un-post/seed/staff-assign, event detail/edit) unless the owner has said otherwise. The 90 rule returns after the reset. Status: **12b dispatched 17:28 in parallel; Sunday 16:05 wake-up scheduled.**

- **Owner 2026-08-27 ~17:33, verbatim: "yes start keeping the docs up to date every task and creating our normal set of access docs. temporarily committ the docs folder so i can use it while away, and any scripts i'll need"** → `docs/` force-added and pushed as a TEMPORARY exception to the local-only rule (secret scan clean: names only); `access/runbook.md` + `access/sweeps.md` added; `scripts/docs/move_done.py` committed. ⚠️ **When the owner is back: purge `docs/` from history again (filter-repo) or decide to keep it tracked — owner decision, one question.** Status: **committed + pushed 17:35; purge decision pending the owner's return.**

- **Owner 2026-08-27 ~17:37, verbatim: "committ anything i'll need. also i probably need a copy of the .env on my laptop… can we store the .env in a firebase or something safely and then write it to a local file with a script?"** → decided: no Firebase (a service-account key is a second secret to protect); `scripts/env-lock.sh` / `scripts/env-unlock.sh` (OpenSSL AES-256-CBC + PBKDF2, passphrase-only) committed; `.env.enc` allowed by `.gitignore`; the owner runs `lock` in their own terminal and commits `.env.enc` — Claude never handles the values. Laptop checklist in `access/runbook.md`. Status: **scripts + docs committed 17:40; the owner runs `sh scripts/env-lock.sh` and commits `.env.enc` before leaving.**

- **Owner 2026-08-27 ~17:42, verbatim: "we should also make a /request command so we can stop using the google doc, also put it on the website"** → F18 Requests: a `/request` slash (modal) that replaces the Google doc members currently fill, stored in the DB, listed/triaged on a dashboard **Requests** page (status open / accepted / done / declined, assignee, notes, reply to the member), with the same review pattern as events/role requests. **Owner ~17:46: "its just the initial doc that I gave you, its an idea on paper, we should make our request form more robust for sure. no need for name just collect who ask, get the what, the why, and a due date if needed. review can be on the site but its its a mod or higher auto approve it. have it go to a pending features list"** → F18 = feature-request intake: `/request` modal (What, Why, Due date optional; requester recorded automatically), status pending → approved → planned → in progress → done / declined; a mod-or-higher requester is auto-approved; dashboard **Requests** page = the pending-features list (filters, assignee, notes, decide, DM the requester). Design `info/phase13-design.md`. Status: **design written 17:48; build after the Sunday reset.**
