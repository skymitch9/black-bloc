# Cutover plan — from test mode to running the server

> **Audience:** the owner (who flips the switches) + Claude sessions (who watch and
> verify). **Status:** TRACKED. **Last verified: 2026-09-01** — written against the
> live settings and `feature-list.md`; nothing below has been executed. The owner
> paces this; nothing here is a promise about dates.
>
> The standing rollout rule (owner, 2026-08-26): every feature that acts on members
> ships **shadow → watch → on**, flipped per feature, old bot running until the new
> one is proven. This doc is that rule turned into steps.

## 0. What "done" looks like

Black Bloc runs moderation, automod, go-live, events, birthdays, temp voice,
honeypot, modmail, role menus, polls, chat and requests for the real server;
Carl-bot, YAGPDB, Birthday Bot and Modmail are retired and (a few weeks later,
owner's call 2026-09-01) kicked. `TEST_MODE` is off. Every flip below is a
settings-registry key reachable from `/settings set-value` AND the dashboard —
nothing needs a deploy.

## 1. Prerequisites — before ANY feature goes live

| # | Step | Who | How |
|---|---|---|---|
| P1 | Sweep rows that matter are green (1–3, 6, 10, 12, 14–16, 21–24 at minimum) | owner | `access/sweeps.md`, ongoing — round 1 of the site sweep passed 2026-09-01 |
| P2 | Rename `#mute-me-bot-test-spam` → **`#black-block-logs`** (spelling confirmed 2026-08-26) | owner | Discord; channel id survives a rename so every stored setting keeps working |
| P3 | Point `staff_channel_id` at the REAL staff channel | owner (+Claude verifies) | this drives who counts as staff everywhere (site access, approvers, exemptions). ⚠️ `/automod mode on` refuses while it still points at the log channel — that refusal is the guard working |
| P4 | Decide the approval channels | owner | `rolemenu_approval_channel_id`, event review category, poll review — default to the staff channel; leave defaults unless wanted elsewhere |
| P5 | **Lift `TEST_MODE`** — `flyctl secrets set TEST_MODE=false --app black-bloc` (restarts the bot) | ⚠️ **owner only** (standing rule: never Claude) | after P2–P4. From this moment the bot can post anywhere its features are pointed, so the per-feature modes below become the only brake — which is why everything acting on members is still `shadow` here |
| P6 | Claude verification pass right after the restart | Claude | boot log clean, 35 commands, loops green, one `/golive test` into the log channel |

## 2. Per-feature ladder — suggested order, lowest risk first

Each feature: **flip → watch (the Logs page + `/<feature> logs`) → declare it live in
`DONE.md`**. Rollback for every row is the same: flip the mode back; the incumbent
bot never stopped running until its retirement step.

| Order | Feature | Flip | Watch for | Retires |
|---|---|---|---|---|
| 1 | **Temp voice** (already `on`, place-gated only by test mode) | nothing — P5 frees it; check the lobby sits above "You Still Here?" | `tempvoice.panel_failed` (Bots role needs Send Messages in voice) | TempVoice bot behaviour (none installed — new capability) |
| 2 | **Role menus** | `rolemenu_mode on`; post menus in the real channel; delete+re-seed `event-alerts` so Marathons wears `:JoyGAMING:` | duplicate panels (KI-8 sentence), approval cards landing in the right channel | Carl reaction roles (leave Carl's up until members have re-picked, then delete Carl's panels) |
| 3 | **Go-live** | `golive_channel_id` → `#live-now`; `golive_mode on` | double posts beside YAGPDB (expected while both run — pick a day to turn YAG's streaming module off), the `REGULATORS!` template rendering | YAGPDB streaming module (owner turns it off on yagpdb.xyz) |
| 3b | **Ping roles (F14)** | `/pings` → **Set up the Events role** (makes or reuses **Events**, points both feeds at it, puts it on the `notifications` menu) → `/rolemenu post notifications` → **Settings** → **Mode…** → on. Streamer roles come after: **Start my own ping role**, or **Streamers…** → **Give somebody a ping role…**, then `/rolemenu post streamers` | the FIRST go-live after the flip — the line should read `<@&Events> <@&… pings> REGULATORS!` with both roles actually pinging; `pings.forbidden` in the log means the **Bots role is below a fan role** in Server Settings ▸ Roles and nothing was changed | nothing — this is new. ⚠️ It only makes sense once row 3 (go-live) is `on`; with `golive_mode` shadow the roles exist and nobody is ever pinged |
| 3c | **YouTube uploads (F3)** — live since `049881b` 2026-09-02, `youtube_mode` off; `/youtube` became ONE panel on 2026-09-03 | members open `/youtube` → **Link my channel** (or staff **Link for somebody…**) — linking counts everything already on the channel as history, so nothing old fires. Then **Setup** → a channel if uploads should NOT share the go-live one, **Announcements are…** → `shadow` for a week, then `on` | the shadow week's `youtube.would_announce` lines: is the wording right, and is anything showing up that should not have? ⚠️ Specifically watch for a LIVE stream announced as an upload — that is **KI-11**, and the fix is setting `YOUTUBE_API_KEY`, not a code change. Shorts are already left out by default | nothing — this is new. Unlike row 3b it does NOT depend on go-live being `on`; it only borrows `golive_channel_id` when `youtube_channel_id` is blank |
| 3d | **Raid trains (F19)** — live since `7b1c592` 2026-09-03, `raidtrain_mode` off; `/raidtrain` became ONE panel on 2026-09-04 | `/raidtrain` → **Setup…** → a channel and an organizer role (blank channel borrows `events_announce_channel_id`) → **Save**, then **Mode…** → `shadow` for one train, then `on`. Streamers need `/golive` ▸ **Link my Twitch channel** first — that requirement is itself a key (`raidtrain_require_link`) | the shadow train's `raidtrain.would_remind` lines: is the DM's wording right, and does it name the RIGHT two neighbours? Then, on `on`, the FIRST reminder — it is a **DM**, so test mode never blocked it and it is the one thing that reaches a member before the feature is public. Watch `raidtrain.dm_failed` for anyone with DMs closed | nothing — this is new, and it replaces r3dlabs.com rather than an installed bot. Independent of rows 3/3b/3c except that D9's check-in reads the go-live signal, so "the train moves" line stays quiet until go-live is working (**KI-16**) |
| 2b | **Applications (F20)** — live since `7b1c592` 2026-09-03, `applications_mode` off | build the form first (`access/sweeps.md` has the Twitch Team walk-through), then `applications_mode shadow` for a day and `on` after. Point the cards somewhere with `applications_channel_id`, or leave it blank and they follow `rolemenu_approval_channel_id` | the first real application end to end: does the card land where staff read it, does the DM arrive, and does the approved card actually name the person who has to send the twitch.tv invite. `application.grant_failed` in the log means the **Bots role sits below the form's role** in Server Settings ▸ Roles — the application still says approved and the fix is `/role grant`, not a redeploy | nothing — this is new. It rides on row 2's plumbing (the approval channel, the approver role, the grant ledger) but does NOT need `rolemenu_mode` on |
| 4 | **Events** | already `on`; category/approvers per P4; scheduled-event toggle default ON | first real submission end-to-end | (new capability) |
| 5 | **Polls / Chat / Requests** | already `on` | nothing special — no member is acted on | (new capability) |
| 6 | **Birthdays** | `birthday_channel_id` → `#return-of-the-gen`; `birthday_mode on`; ⚠️ same day, owner disables Birthday Bot's announcements — two bots both wish at midnight otherwise | the per-member-midnight firing (Phoenix gotcha from the incumbent measurement is FIXED by design — verify the first real one lands on the right day) | Birthday Bot |
| 7 | **Modmail** | `modmail_enabled true`; owner disables the incumbent Modmail bot the same hour (two ticket systems = lost DMs) | first real ticket relayed both directions | Modmail bot |
| 8 | **Automod** | `automod_mode shadow` for ~1 week against real traffic → read the would-lines together → `on` | false `would_*` hits on innocent messages — tune exemptions BEFORE `on` | Carl automod (turn Carl's mention-spam off when ours goes `on`, not before) |
| 9 | **Moderation commands** | nothing to flip — live once TEST_MODE lifts; staff just start using `/warn` etc. | case log correctness | Carl mod commands (habit change, not a switch) |
| 10 | **Honeypot** | `/honeypot` → **Setup…** in the real channel list, bottom; `honeypot_mode shadow` for 1 week (owner decision 2026-08-26) → `on` from the panel's mode picker | any would-ban of a real member who isn't a bot — that's a tuning failure, stop | (new capability) |

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
- **KI-5's DM behaviour** becomes moot after P5 (its whole point was test mode).
- **Two announcers double-post** during any overlap window (go-live, birthdays).
  Overlap is deliberate (proving), but pick short windows for the noisy ones.
- **Session cookies / dashboard access** don't change at cutover — staff is
  derived from the staff channel (P3 widens/narrows it; check who gains access).
