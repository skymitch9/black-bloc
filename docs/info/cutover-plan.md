# Cutover plan — from test mode to running the server

> **Audience:** the owner (who flips the switches) + Claude sessions (who watch and
> verify). **Status:** TRACKED · ⏸️ **NOT STARTED — PAUSED ON THE OWNER.**
> **Last verified: 2026-09-11 09:10** — docs-wide staleness pass against **v108** `73e2e44`.
> ⚠️ **Six days and sixteen releases on, step P5 has still not been taken: `TEST_MODE` is ON
> and the bot still speaks only in `#blackbloc-logs` and DMs.** Not one row of §2 has
> been executed. That is not drift — the owner paces this and nothing here is a promise about
> dates — but a reader must not mistake this file for a record of what happened. **Re-measured
> today:** the command roster is still **29 top-level commands, zero `app_commands.Group`s**;
> the self-test is still **107 checks**; `../access/sweeps.md` now runs to **350** rows (294 at
> v92). **FIXED:** the sweep-row count in P1, and §4's KI-21 clause — **KI-21 is CLOSED** (v89
> `243dc0f`) and no longer appears in `KNOWN_ISSUES.md`. Every other `KI-n` cited below was
> re-checked and is still listed: KI-5, KI-8, KI-11, KI-16, KI-17, KI-20, KI-22.
> ⚠️ **NOT checked:** the LIVE value of
> any key (the Settings page needs a Discord sign-in) — "already `on`" rows say what the
> registry default is, and the owner reads the live value on
> https://blackbloc.heygabi.ai/settings.html before flipping anything; every `*_mode` /
> `*_channel_id` key name and every quoted button label was verified on 2026-09-05 and NOT
> re-verified today.
> Before that, **2026-09-05 20:55** — re-measured against
> **v92** `4b327cf`: the command roster, every `*_mode` / `*_channel_id` key named below in
> `black_bloc/settings_store.py`, every button label quoted against the string in the cog, and
> every `KI-n` cited then open in `KNOWN_ISSUES.md`.
>
> The 2026-09-01 version of this doc named slash sub-commands the panel waves have since
> retired (`/settings set-value`, `/golive test`, `/automod mode on`, `/rolemenu post`,
> `/role grant`, "35 commands"). Every step now names the panel move instead; where a panel
> sets its mode with a select rather than a button, the select's placeholder is quoted
> (**Announcements: off / shadow / on**, **Wishes are…**, **What automod does…**, **What the
> trap does…**, **Announcements are…**).
>
> The standing rollout rule (owner, 2026-08-26): every feature that acts on members
> ships **shadow → watch → on**, flipped per feature, old bot running until the new
> one is proven. This doc is that rule turned into steps.

## 0. What "done" looks like

Black Bloc runs moderation, automod, go-live, events, birthdays, temp voice,
honeypot, modmail, role menus, polls, chat, requests, applications, raid trains,
YouTube uploads and ping roles for the real server; Carl-bot, YAGPDB, Birthday Bot
and Modmail are retired and (a few weeks later, owner's call 2026-09-01) kicked.
`TEST_MODE` is off. Every flip below is a settings-registry key reachable from the
feature's own panel, from `/settings` ▸ **A setting group…**, AND from the dashboard's
Settings page — nothing needs a deploy (checklist item 33).

## 1. Prerequisites — before ANY feature goes live

| # | Step | Who | How |
|---|---|---|---|
| P1 | The sweep rows for whatever you are about to flip are green, and the core ones (1–3, 6, 10, 12, 14–16, 21–24) at minimum | owner | [`../access/sweeps.md`](../access/sweeps.md) — **350** rows as of 2026-09-11 (294 at v92), grouped by feature; round 1 of the site sweep passed 2026-09-01, the self-test row (252) was run by the owner 2026-09-05. Rows 253–294 are still the owner's |
| P2 | Rename `#blackbloc-logs` → **`#black-block-logs`** (spelling confirmed 2026-08-26) | owner | Discord; the channel id survives a rename so `TEST_CHANNEL_ID`, `log_channel_id` and `selftest_channel_id` keep working. Not done as of 2026-09-05 (every sweep row still names the old name) |
| P3 | Point `staff_channel_id` at the REAL staff channel | owner (+Claude verifies) | Settings page ▸ **Core**, or `/settings` ▸ **A setting group…** ▸ **core**. This drives who counts as staff everywhere (site access, approvers, exemptions). ⚠️ `/automod` ▸ **What automod does…** ▸ on refuses in words while it still points at the log channel (`automod.arming_refusal`) — that refusal is the guard working |
| P4 | Decide the approval channels | owner | `rolemenu_approval_channel_id`, `events_category_id`, `applications_channel_id`, `poll_channel_id`, `request_status_channel_id` / `request_notify_channel_id` — every one defaults to the staff channel or to the feature's own panel's Setup; leave defaults unless wanted elsewhere |
| P5 | **Lift `TEST_MODE`** — `flyctl secrets set TEST_MODE=false --app black-bloc` (restarts the bot) | ⚠️ **owner only** (standing rule: never Claude) | after P2–P4. From this moment the bot can post anywhere its features are pointed, so the per-feature modes below become the only brake — which is why everything acting on members is still `shadow` here. ⚠️ The restart kills every open ephemeral panel (**KI-20**) — do it at a quiet hour and tell staff |
| P6 | Verification pass right after the restart | Claude + owner | Claude: boot log shows `synced 29 app commands`, `selftest: N ok, 0 failed` (107 checks at v92) and NO `TEST MODE ON` line; `/health` answers `ready: true`. Owner: `/settings` ▸ **Self-test…** ▸ **Run the self-test** (the 107 checks, by a person), then `/golive` ▸ **Preview an announcement…** (ephemeral, posts nothing, leaves one `golive.test` row) |
| P7 | **Re-shoot every guide screenshot** (owner, 2026-09-16 15:5x, verbatim: "we need to update all screen shots once shadow mode is off to not have that message and to not have the old channel") — every one of the 16 captures taken at v111 shows the *in shadow* line and the old `#mute-me-bot-test-spam` channel name | Claude, a capture session per `../access/guides-capture.md` | after P5–P6 AND after the per-feature modes below have flipped (a card re-shot while its feature is still `shadow` still says so). Trigger: a staff **Mark every screenshot stale** move (TODO follow-up) or, until it exists, `UPDATE guide_media SET stale = 1` by hand; then the runbook's stale list is the whole job. The `birthday-set` illustration is redrawn the same day for the same reason |

## 2. Per-feature ladder — suggested order, lowest risk first

Each feature: **flip → watch → declare it live in `DONE.md`**. "Watch" is the panel's
**Logs** button (every one of the 18 features has one — `tests/test_bot.py` fails if a
panel loses it) and the dashboard's Logs page https://blackbloc.heygabi.ai/audit.html#logs
filtered to that feature. Rollback for every row is the same: flip the mode back; the
incumbent bot never stopped running until its retirement step.

Every mode below is ALSO a row on https://blackbloc.heygabi.ai/settings.html, and the
three gated keys (automod's mode, honeypot's mode and exemptions) get the same refusal
there as on the panel (§4). The panel move is named because it is where staff will be.

| Order | Feature | Flip | Watch for | Retires |
|---|---|---|---|---|
| 1 | **Temp voice** (`tempvoice_mode`, default `on`; place-gated only by test mode) | nothing — P5 frees it; check the lobby sits above "You Still Here?" | `tempvoice.panel_failed` (Bots role needs Send Messages in voice) | TempVoice bot behaviour (none installed — new capability) |
| 2 | **Role menus** | `/rolemenu` → **Turn role menus on**; then each menu's card → **Post it** into the real channel (`/rolemenu` ▸ the menu, or https://blackbloc.heygabi.ai/rolemenus.html); delete+re-seed `event-alerts` so Marathons wears `:JoyGAMING:` | duplicate panels (KI-8 sentence), approval cards landing in the right channel | Carl reaction roles (leave Carl's up until members have re-picked, then delete Carl's panels) |
| 3 | **Go-live** | `golive_channel_id` → `#live-now` (Settings page ▸ golive, or `/settings` ▸ **A setting group…** ▸ **golive** — the `/golive` panel does not set the channel); then `/golive` (as staff) → **Announcements: off / shadow / on** → on | double posts beside YAGPDB (expected while both run — pick a day to turn YAG's streaming module off), the `REGULATORS!` template rendering | YAGPDB streaming module (owner turns it off on yagpdb.xyz) |
| 3b | **Ping roles (F14)** | `/pings` → **Set up the Events role** (makes or reuses **Events**, points both feeds at it, puts it on the `notifications` menu) → `/rolemenu` ▸ **notifications** ▸ **Post it** → `/pings` ▸ **Mode…** → on. Streamer roles come after: **Start my own ping role**, or **Streamers…** → **Give somebody a ping role…**, then `/rolemenu` ▸ **streamers** ▸ **Post it** | the FIRST go-live after the flip — the line should read `<@&Events> <@&… pings> REGULATORS!` with both roles actually pinging; `pings.forbidden` in the log means the **Bots role is below a fan role** in Server Settings ▸ Roles and nothing was changed | nothing — this is new. ⚠️ It only makes sense once row 3 (go-live) is `on`; with `golive_mode` shadow the roles exist and nobody is ever pinged |
| 3c | **YouTube uploads (F3)** — live since `049881b` 2026-09-02, `youtube_mode` off; `/youtube` is ONE panel | members open `/youtube` → **Link my channel** (or staff **Link for somebody…**) — linking counts everything already on the channel as history, so nothing old fires. Then **Setup** → a channel if uploads should NOT share the go-live one, **Announcements are…** → `shadow` for a week, then `on` | the shadow week's `youtube.would_announce` lines: is the wording right, and is anything showing up that should not have? ⚠️ Specifically watch for a LIVE stream announced as an upload — that is **KI-11**, and the fix is setting `YOUTUBE_API_KEY`, not a code change. Shorts are already left out by default | nothing — this is new. Unlike row 3b it does NOT depend on go-live being `on`; it only borrows `golive_channel_id` when `youtube_channel_id` is blank |
| 3d | **Raid trains (F19)** — live since `7b1c592` 2026-09-03, `raidtrain_mode` off; `/raidtrain` is ONE panel | `/raidtrain` → **Setup…** → a channel and an organizer role (blank channel borrows `events_announce_channel_id`) → **Save**, then **Mode…** → `shadow` for one train, then `on`. Streamers need `/golive` ▸ **Link my Twitch channel** first — that requirement is itself a key (`raidtrain_require_link`) | the shadow train's `raidtrain.would_remind` lines: is the DM's wording right, and does it name the RIGHT two neighbours? Then, on `on`, the FIRST reminder — it is a **DM**, so test mode never blocked it and it is the one thing that reaches a member before the feature is public. Watch `raidtrain.dm_failed` for anyone with DMs closed | nothing — this is new, and it replaces r3dlabs.com rather than an installed bot. Independent of rows 3/3b/3c except that D9's check-in reads the go-live signal, so "the train moves" line stays quiet until go-live is working (**KI-16**) |
| 2b | **Applications (F20)** — live since `7b1c592` 2026-09-03, `applications_mode` off | build the form first (`access/sweeps.md` rows 55–70 have the Twitch Team walk-through), then `/apply` ▸ **Mode…** → `shadow` for a day and `on` after. Point the cards somewhere with `applications_channel_id`, or leave it blank and they follow `rolemenu_approval_channel_id` | the first real application end to end: does the card land where staff read it, does the DM arrive, and does the approved card actually name the person who has to send the twitch.tv invite (**KI-17** — the bot cannot confirm it). `application.grant_failed` in the log means the **Bots role sits below the form's role** in Server Settings ▸ Roles — the application still says approved and the fix is `/rolemenu` ▸ the menu ▸ **Hand roles out…**, not a redeploy | nothing — this is new. It rides on row 2's plumbing (the approval channel, the approver role, the grant ledger) but does NOT need `rolemenu_mode` on |
| 4 | **Events** (`events_mode` off/shadow/on) | check it reads `on`; category/approvers per P4; scheduled-event toggle default ON | first real submission end-to-end: the `pending-<user>-<title>` channel, the Approve rename, the announcement | (new capability) |
| 5 | **Polls / Chat / Requests** (`poll_mode`, `chat_mode`, `request_mode`) | check each reads `on` | nothing special — no member is acted on. Chat spends money: `chat_monthly_cap_usd` is the brake there, not the mode | (new capability) |
| 6 | **Birthdays** | `birthday_channel_id` → `#return-of-the-gen` (Settings page ▸ birthday, or `/settings` ▸ **A setting group…** ▸ **birthday**); then `/birthday` (as staff) → **Wishes are…** → on; ⚠️ same day, owner disables Birthday Bot's announcements — two bots both wish at midnight otherwise | the per-member-midnight firing (the Phoenix gotcha from the incumbent measurement is FIXED by design — verify the first real one lands on the right day) | Birthday Bot |
| 7 | **Modmail** | `modmail_enabled` → true (and `modmail_mode` `channel` / `thread` is the second decision — `channel` matches the incumbent); owner disables the incumbent Modmail bot the same hour (two ticket systems = lost DMs) | first real ticket relayed both directions. ⚠️ **KI-5**: a web reply reaches the member even in test mode, so this row is one you can rehearse before P5 | Modmail bot |
| 8 | **Automod** | `/automod` → **What automod does…** → `shadow` for ~1 week against real traffic → read the would-lines together → `on` (the panel refuses `on` until P3 is done) | false `would_*` hits on innocent messages — tune exemptions BEFORE `on` | Carl automod (turn Carl's mention-spam off when ours goes `on`, not before) |
| 9 | **Moderation commands** (`/warn` `/timeout` `/untimeout` `/kick` `/ban` `/unban` `/purge`, `/mod` for cases) | nothing to flip — live once TEST_MODE lifts; staff just start using them | case log correctness on `/mod` ▸ **Logs** (**KI-22**: `/purge` cannot say which door made a row) | Carl mod commands (habit change, not a switch) |
| 10 | **Honeypot** | `/honeypot` → **Setup…** in the real channel list, bottom; **What the trap does…** → `shadow` for 1 week (owner decision 2026-08-26) → `on` | any would-ban of a real member who isn't a bot — that's a tuning failure, stop | (new capability) |

## 3. Retire the incumbents

Per-module turn-offs happen inside the ladder (rows 2, 3, 6, 7, 8). The **kick**
of Carl-bot, YAGPDB, Birthday Bot, Modmail + the dormant three (`Verification
Bot`, `baf`, `Black Block`) is a separate, later owner action — **owner set the
horizon 2026-09-01: "in a few weeks"**. Before kicking, Claude takes a final
scan of anything only those bots hold (Carl's dashboards are already archived
under `archive/current-bots/`).

## 4. Standing risks

- **The one brake after P5 is per-feature modes.** Anything already `on`
  (tempvoice, polls, chat, events, requests, golive-once-flipped) acts on the
  real server immediately. That is by design; the sweep is what earns it.
- **The dashboard carries automod's arming refusal too** (the gate pass filed as KI-21, **CLOSED at v89** `243dc0f` and gone from `KNOWN_ISSUES.md`; landed v84
  `675f233`: `api/settings_api.py:gated_writers` hands `automod_mode`, `honeypot_mode`
  and `honeypot_exempt_role_ids` to the cog's own move, so a `PUT` gets the panel's
  verdict). Either door is safe to flip from; the 2026-09-04 finding that said
  otherwise was closed before it was ever re-listed.
- **KI-5's DM behaviour** becomes moot after P5 (its whole point was test mode).
- **KI-20 — a restart kills every open ephemeral panel.** P5 is a restart; so is
  every deploy. Neither is dangerous, but a staffer mid-move gets "This
  interaction failed" and has to reopen the panel.
- **Two announcers double-post** during any overlap window (go-live, birthdays).
  Overlap is deliberate (proving), but pick short windows for the noisy ones.
- **Session cookies / dashboard access** don't change at cutover — staff is
  derived from the staff channel (P3 widens/narrows it; check who gains access).
- **GABI shares the personality pool** (`info/personality-pool-design.md`): nothing
  here touches it, but a cutover-day roster edit on either bot turns the
  self-test's `pool.in_step_with_gabi` red — that is the check working.
