# Cutover plan — from test mode to running the server

> 🔨 **2026-09-25 — the shadow home is PER FEATURE now, branch `shadow-home-per-feature` (BUILT, NOT merged):** a feature's own `<feature>_shadow_channel_id` (frontdoor, posts, golive, marathon, poll, birthday) wins over `shadow_channel_id`; blank follows it. The owner's state after the deploy: `shadow_channel_id` → #blackbloc-logs, `frontdoor_shadow_channel_id` → #welcome-test (set by the conductor, not the build). [`shadow-home-per-feature-design.md`](shadow-home-per-feature-design.md).

> **Audience:** the owner (who flips the switches) + Claude sessions (who watch and
> verify). **Status:** TRACKED · ▶️ **STARTED — P5 TAKEN 2026-09-18 16:08; the §2 ladder is
> now the live to-do list, at the owner's pace.**
> **Last verified: 2026-09-19** — the docs staleness pass after the lift. ⚠️ **The Status line
> above said `NOT STARTED — PAUSED ON THE OWNER` while P5's own row already carried its
> ✅ banner**, so this file contradicted itself at the top. Re-stated below what is actually
> true: **events, requests and modmail are LIVE to members** (owner, 17:1x: *"its live and
> people can use it"*) — which is ladder rows **4**, **5** and **7** taken, out of order and
> in one step, because lifting P5 took them; **`frontdoor_mode` is `shadow`** aimed at
> `#welcome` (set 16:57, the copy verified in `#welcome-test` 17:00 and `#welcome` verified
> clean 17:03); go-live, polls, birthdays, temp voice, the honeypot and automod are still
> `shadow` or `off`. **Row 3c (YouTube UPLOADS) is DEAD** — the feature was removed whole at
> v139 and the row is struck. Every `KI-n` cited below was re-checked: **KI-5 is MOOT**
> (§4 already predicted it would be) and **KI-11 is CLOSED as moot** with the uploads half.
> ⚠️ **NOT checked:** the LIVE value of any key — the Settings page needs a Discord sign-in and
> this pass had none, so every mode named above is the conductor's 2026-09-18 reading, not a
> measurement taken today; `/health` was the only live thing read. Every `*_mode` /
> `*_channel_id` key name and every quoted button label was verified **2026-09-05** and has
> **not** been re-verified since. P2 (the channel rename) is still not done.
> Before that, **2026-09-11 09:10** — docs-wide staleness pass against **v108** `73e2e44`.
> ✅ **P5 TAKEN by the owner 2026-09-18 16:08** (`flyctl secrets set TEST_MODE=false --app black-bloc`, from his own terminal; the bot restarted 16:08:27 without the guard, the front door's rehearsal ids were cleared at boot, the self-test passed 116/116). What follows is the per-feature ladder at his pace. Was: ⚠️ **Six days and sixteen releases on, step P5 has still not been taken: `TEST_MODE` is ON
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
~~YouTube uploads~~ **YouTube LIVE streams** (⚠️ the uploads half was removed whole at **v139**,
2026-09-18 — [`youtube-uploads-removal-design.md`](youtube-uploads-removal-design.md); the
feature's on/off is `youtube_live_mode`) and ping roles for the real server; Carl-bot, YAGPDB,
Birthday Bot and Modmail are retired and (a few weeks later, owner's call 2026-09-01) kicked.
✅ **`TEST_MODE` is off — done 2026-09-18 16:08.** Every flip below is a settings-registry key reachable from the
feature's own panel, from `/settings` ▸ **A setting group…**, AND from the dashboard's
Settings page — nothing needs a deploy (checklist item 33).

## 1. Prerequisites — before ANY feature goes live

| # | Step | Who | How |
|---|---|---|---|
| P1 | The sweep rows for whatever you are about to flip are green, and the core ones (1–3, 6, 10, 12, 14–16, 21–24) at minimum | owner | [`../access/sweeps.md`](../access/sweeps.md) — **620** rows as of 2026-09-18 (counted 2026-09-19; this said 350, the 2026-09-11 reading; 294 at v92), grouped by feature; round 1 of the site sweep passed 2026-09-01, the self-test row (252) was run by the owner 2026-09-05. Rows 253–294 are still the owner's |
| P2 | Rename `#blackbloc-logs` → **`#black-block-logs`** (spelling confirmed 2026-08-26) | owner | Discord; the channel id survives a rename so `TEST_CHANNEL_ID`, `log_channel_id` and `selftest_channel_id` keep working. ⚠️ **STILL NOT DONE as of 2026-09-19, and P5 went ahead without it** — a prerequisite the ladder said came first was simply skipped, and nothing broke, which is worth knowing before treating the other P-rows as blocking. The channel WAS renamed once on 2026-09-16, from `#mute-me-bot-test-spam` to its current `#blackbloc-logs`; that is a different rename from the one this row asks for |
| P3 | Point `staff_channel_id` at the REAL staff channel | owner (+Claude verifies) | Settings page ▸ **Core**, or `/settings` ▸ **A setting group…** ▸ **core**. This drives who counts as staff everywhere (site access, approvers, exemptions). ⚠️ `/automod` ▸ **What automod does…** ▸ on refuses in words while it still points at the log channel (`automod.arming_refusal`) — that refusal is the guard working |
| P4 | Decide the approval channels | owner | `rolemenu_approval_channel_id`, `events_category_id`, `applications_channel_id`, `poll_channel_id`, `request_status_channel_id` / `request_notify_channel_id` — every one defaults to the staff channel or to the feature's own panel's Setup; leave defaults unless wanted elsewhere |
| P5 | **Lift `TEST_MODE`** — `flyctl secrets set TEST_MODE=false --app black-bloc` (restarts the bot) | ⚠️ **owner only** (standing rule: never Claude) | after P2–P4. From this moment the bot can post anywhere its features are pointed, so the per-feature modes below become the only brake — which is why everything acting on members is still `shadow` here. ⚠️ The restart kills every open ephemeral panel (**KI-20**) — do it at a quiet hour and tell staff |
| P4z | ⚠️ **WHAT ACTUALLY HAPPENED, 2026-09-18 16:08 — read this before the prediction below, because the prediction was half wrong.** The front door and the ticket button DID reconcile the instant the guard went — but three reconciles race at boot with no lock, so the door posted **TWICE** in `#welcome` and left an orphaned ticket button beside it. All three messages were deleted by hand at 16:1x, `frontdoor_channel_id` and `modmail_panel_channel_id` were cleared, and `log_channel_id` had to be **re-set** to `#blackbloc-logs` because its default went blank with the flag. The fix (`loops.Reconciler`, one lock per cog, the state read inside it) and `frontdoor_mode`'s new **shadow** value both shipped as **v141** the same afternoon; the door now rehearses in `#welcome-test` and posts nothing in `#welcome`. Review-checklist item **37** is the rule that came out of it. ⚠️ **"The rehearsal home stops mattering here" was the single wrong sentence** — it matters MORE after the lift, because it is now the only thing between a shadow feature and the real channel. The prediction as written: **The rehearsal home stops mattering here** — nothing to do, but know what each copy does when `TEST_MODE` goes off at P5. The **front door** and the **ticket button** reconcile within five minutes: the guard is gone, so each takes its rehearsal copy down (`frontdoor.taken_down_shadow`, `modmail.panel_taken_down_shadow`) and posts the real message in its own channel. The **welcome post** does NOT: `posts_mode` is still `shadow`, so its copy stays in the rehearsal home until row 11 flips posts to `on`, and the first real post removes it then (`post.shadow_taken_down`). **Polls** in shadow keep whatever copy they have; a new poll goes wherever `shadow_channel_id` points. ⚠️ Clearing `shadow_channel_id` afterwards is optional and safe: with `TEST_MODE` off the guard does not exist, so the key only decides where a feature still in `shadow` rehearses | owner | reading only, before P5 |
| P5a | **Flip `tempvoice_mode` shadow → on** — Settings page ▸ **tempvoice**, or `/voice` ▸ **Mode…** ▸ *on* — and the bot syncs the lobby with its category and gives the allowed role its view back. **Nothing to do in Discord** | owner | immediately after P5. While the mode is `shadow` the bot keeps **view = deny** on the lobby for `@everyone` and for the Member role, so only staff see it (v125; the mode is set to `shadow` by the conductor right after that deploy). The flip runs Discord's own **Sync now** on the lobby and then puts the Member role, the bot and the staff reach back on top — one `tempvoice.lobby_shown` row in the action log says it happened. ⚠️ **The rooms follow the LOBBY, not the category** — `tempvoice_room_overwrites` is `lobby` (v117), so the lobby is the whole job and no other setting has to change; `category` is the pre-v117 behaviour. ⚠️ **Never press Setup on `/voice` to do this** — `repair_creator_channel` rewrites the lobby's overwrites from its category and, in `shadow`, re-applies the mask; the mode flip is the only door |
| P6 | Verification pass right after the restart — ✅ **DONE 2026-09-18** (the lift boot was clean bar the doubled front door, P4z; the self-test read **116/116** at the v140 boot and `/health` has answered `ready: true` at every boot since) | Claude + owner | Claude: boot log shows `synced` **32** `app commands` (⚠️ **this said 29** — that was v108; `tests/test_bot.py:TOP_LEVEL_NOW` is 32 at v141), `selftest: N ok, 0 failed` (**116** checks at v140; it said 107 at v92) and NO `TEST MODE ON` line; `/health` answers `ready: true`. Owner: `/settings` ▸ **Self-test…** ▸ **Run the self-test** (the 107 checks, by a person), then `/golive` ▸ **Preview an announcement…** (ephemeral, posts nothing, leaves one `golive.test` row) |
| P7 | **Re-shoot every guide screenshot** (owner, 2026-09-16 15:5x, verbatim: "we need to update all screen shots once shadow mode is off to not have that message and to not have the old channel") — every one of the 16 captures taken at v111 shows the *in shadow* line and the old `#mute-me-bot-test-spam` channel name (⚠️ **that channel was RENAMED `#blackbloc-logs` on 2026-09-16** — the id survived, so nothing broke, but every screenshot still shows the old name and so does any doc written before then). ⚠️ **P5 has happened and this row has NOT** — the shots are now stale on two counts, the guard line AND the channel name | Claude, a capture session per `../access/guides-capture.md` | after P5–P6 AND after the per-feature modes below have flipped (a card re-shot while its feature is still `shadow` still says so). Trigger: **Mark every screenshot stale…**, the staff button under **Screenshots to re-shoot** on the hub (`POST /api/guides/stale/all`, built on branch `guides-stale`) — press it, confirm, write one line of why; then the runbook's stale list is the whole job. The `birthday-set` illustration is redrawn the same day for the same reason |

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
| 1 | **Temp voice** (`tempvoice_mode`, registry default `on`, **live value `shadow`** from v125; place-gated only by test mode) | **P5a** — flip `shadow` → `on`; check the lobby sits above "You Still Here?" | `tempvoice.panel_failed` (Bots role needs Send Messages in voice), `tempvoice.lobby_failed` | TempVoice bot behaviour (none installed — new capability) |
| 2 | **Role menus** | `/rolemenu` → **Turn role menus on**; then each menu's card → **Post it** into the real channel (`/rolemenu` ▸ the menu, or https://blackbloc.heygabi.ai/rolemenus.html); delete+re-seed `event-alerts` so Marathons wears `:JoyGAMING:` | duplicate panels (KI-8 sentence), approval cards landing in the right channel | Carl reaction roles (leave Carl's up until members have re-picked, then delete Carl's panels) |
| 3 | **Go-live** | `golive_channel_id` → `#live-now` (Settings page ▸ golive, or `/settings` ▸ **A setting group…** ▸ **golive** — the `/golive` panel does not set the channel); then `/golive` (as staff) → **Announcements: off / shadow / on** → on | double posts beside YAGPDB (expected while both run — pick a day to turn YAG's streaming module off), the `REGULATORS!` template rendering | YAGPDB streaming module (owner turns it off on yagpdb.xyz) |
| 3b | **Ping roles (F14)** | `/pings` → **Set up the Events role** (makes or reuses **Events**, points both feeds at it, puts it on the `notifications` menu) → `/rolemenu` ▸ **notifications** ▸ **Post it** → `/pings` ▸ **Mode…** → on. Streamer roles come after: **Start my own ping role**, or **Streamers…** → **Give somebody a ping role…**, then `/rolemenu` ▸ **streamers** ▸ **Post it** | the FIRST go-live after the flip — the line should read `<@&Events> <@&… pings> REGULATORS!` with both roles actually pinging; `pings.forbidden` in the log means the **Bots role is below a fan role** in Server Settings ▸ Roles and nothing was changed | nothing — this is new. ⚠️ It only makes sense once row 3 (go-live) is `on`; with `golive_mode` shadow the roles exist and nobody is ever pinged |
| ~~3c~~ | 🔴 **ROW DEAD — the YouTube UPLOADS half was REMOVED at v139** (2026-09-18 10:05, merge `72733e5`; owner: *"the youtube uploader we should just fully trash"*; [`youtube-uploads-removal-design.md`](youtube-uploads-removal-design.md)). There is nothing to flip: `youtube_mode`, `youtube_channel_id`, `youtube_template`, `youtube_poll_minutes` and four more keys are gone, the feed poll and the Setup sub-panel with them, and **KI-11 / KI-12 / KI-13 are CLOSED as moot**. The channel LINKS survive and are the input to row **3c-live**, which is the only YouTube row left. The text below is struck and kept so a reader meeting a `youtube_*` key in an old doc can see where it went | ~~members open `/youtube` → **Link my channel** (or staff **Link for somebody…**) — linking counts everything already on the channel as history, so nothing old fires. Then **Setup** → a channel if uploads should NOT share the go-live one, **Announcements are…** → `shadow` for a week, then `on` | the shadow week's `youtube.would_announce` lines: is the wording right, and is anything showing up that should not have? ⚠️ Specifically watch for a LIVE stream announced as an upload — that is **KI-11**, and the fix is setting `YOUTUBE_API_KEY`, not a code change. Shorts are already left out by default~~ | ~~nothing — this is new. Unlike row 3b it does NOT depend on go-live being `on`; it only borrows `golive_channel_id` when `youtube_channel_id` is blank~~ |
| 3c-live | **YouTube LIVE streams (v126)** — the same link, a second mode; `youtube_live_mode` ships **off**, ⚠️ **but the live value on this guild is `on`** (the owner flipped it 2026-09-17; read back on `/api/youtube/status` at the v139 boot, and **not** re-readable 2026-09-19 — that route now answers `not_signed_in` to an anonymous request). ⚠️ **Row 3c is dead, so this is the ONLY YouTube row** | nothing new to link: everybody with a linked channel is already opted in. `/youtube` (as staff) → **Live streams are…** → `shadow` for a stream or two, then `on`. ⚠️ Unlike row 3c this one DOES depend on row 3: a YouTube stream is announced through go-live, so with `golive_mode` shadow nothing is posted | the first `youtube.would_live_seen` / `golive.would_announce` pair — is it the right person, the right video, and does it arrive within `youtube_live_poll_minutes` of them going live? Then, on `on`, whether the announcement is EDITED when the stream ends (two quiet probes, `youtube_live_end_misses`). ⚠️ With no `YOUTUBE_API_KEY` the card's title reads **Live now** and the game reads **something** — that is the designed keyless shape, not a bug. KI-30 is the other thing to watch: a YouTube page change makes every linked channel read as offline | **the `on_presence_update` door**, which already catches a YouTube stream when the streamer's Discord status is Streaming with a youtube.com link. Both can fire; the session lock and the cooldown mean only one announcement is made, and whichever door got there first owns the session |
| 3d | **Raid trains (F19)** — live since `7b1c592` 2026-09-03, `raidtrain_mode` off; `/raidtrain` is ONE panel | `/raidtrain` → **Setup…** → a channel and an organizer role (blank channel borrows `events_announce_channel_id`) → **Save**, then **Mode…** → `shadow` for one train, then `on`. Streamers need `/golive` ▸ **Link my Twitch channel** first — that requirement is itself a key (`raidtrain_require_link`) | the shadow train's `raidtrain.would_remind` lines: is the DM's wording right, and does it name the RIGHT two neighbours? Then, on `on`, the FIRST reminder — it is a **DM**, so test mode never blocked it and it is the one thing that reaches a member before the feature is public. Watch `raidtrain.dm_failed` for anyone with DMs closed | nothing — this is new, and it replaces r3dlabs.com rather than an installed bot. Independent of rows 3/3b/3c except that D9's check-in reads the go-live signal, so "the train moves" line stays quiet until go-live is working (**KI-16**) |
| 2b | **Applications (F20)** — live since `7b1c592` 2026-09-03, `applications_mode` off | build the form first (`access/sweeps.md` rows 55–70 have the Twitch Team walk-through), then `/apply` ▸ **Mode…** → `shadow` for a day and `on` after. Point the cards somewhere with `applications_channel_id`, or leave it blank and they follow `rolemenu_approval_channel_id` | the first real application end to end: does the card land where staff read it, does the DM arrive, and does the approved card actually name the person who has to send the twitch.tv invite (**KI-17** — the bot cannot confirm it). `application.grant_failed` in the log means the **Bots role sits below the form's role** in Server Settings ▸ Roles — the application still says approved and the fix is `/rolemenu` ▸ the menu ▸ **Hand roles out…**, not a redeploy | nothing — this is new. It rides on row 2's plumbing (the approval channel, the approver role, the grant ledger) but does NOT need `rolemenu_mode` on |
| 4 | **Events** (`events_mode` off/shadow/on) | check it reads `on`; category/approvers per P4; scheduled-event toggle default ON | first real submission end-to-end: the `pending-<user>-<title>` channel, the Approve rename, the announcement | (new capability) |
| 5 | **Polls / Chat / Requests** (`poll_mode`, `chat_mode`, `request_mode`) | check each reads `on` | nothing special — no member is acted on. Chat spends money: `chat_monthly_cap_usd` is the brake there, not the mode | (new capability) |
| 6 | **Birthdays** | `birthday_channel_id` → `#general-chat` (was `#return-of-the-gen`, renamed; id `1411816390414962700`; set 2026-09-17) (Settings page ▸ birthday, or `/settings` ▸ **A setting group…** ▸ **birthday**); then `/birthday` (as staff) → **Wishes are…** → on; ⚠️ same day, owner disables Birthday Bot's announcements — two bots both wish at midnight otherwise | the per-member-midnight firing (the Phoenix gotcha from the incumbent measurement is FIXED by design — verify the first real one lands on the right day) | Birthday Bot |
| 7 | **Modmail** | `modmail_enabled` → true (and `modmail_mode` `channel` / `thread` is the second decision — `channel` matches the incumbent); owner disables the incumbent Modmail bot the same hour (two ticket systems = lost DMs) | first real ticket relayed both directions. ⚠️ ~~**KI-5**: a web reply reaches the member even in test mode, so this row is one you can rehearse before P5~~ **This row is TAKEN** — `modmail_enabled` is true and tickets are live to members (owner, 2026-09-18 17:1x). KI-5 is moot with the guard. What is still owed here is the RETIREMENT half: the incumbent Modmail bot must be turned off, because **two ticket systems = lost DMs** | Modmail bot — ⚠️ **whether the owner has turned it off was NOT checked 2026-09-19** (it needs a look at the guild), so treat the overlap this row warns about as possibly OPEN until he confirms |
| 8 | **Automod** | `/automod` → **What automod does…** → `shadow` for ~1 week against real traffic → read the would-lines together → `on` (the panel refuses `on` until P3 is done) | false `would_*` hits on innocent messages — tune exemptions BEFORE `on` | Carl automod (turn Carl's mention-spam off when ours goes `on`, not before) |
| 9 | **Moderation commands** (`/warn` `/timeout` `/untimeout` `/kick` `/ban` `/unban` `/purge`, `/mod` for cases) | ⚠️ **TAKEN, by omission — these went live at 16:08 on 2026-09-18 with nothing flipped**, exactly as this row predicted. There is no mode on them: staff just start using them, and a `/ban` typed today bans. ⚠️ Nobody has run one against a real member yet as far as this pass knows | case log correctness on `/mod` ▸ **Logs** (**KI-22**: `/purge` cannot say which door made a row) | Carl mod commands (habit change, not a switch) |
| 10 | **Honeypot** | `/honeypot` → **Setup…** in the real channel list, bottom; **What the trap does…** → `shadow` for 1 week (owner decision 2026-08-26) → `on` | any would-ban of a real member who isn't a bot — that's a tuning failure, stop | (new capability) |

| 11 | **Posts (F-P)** — the welcome and rules message. ⚠️ **Rewritten 2026-09-16: `posts_mode` is off/**shadow**/on and ships in SHADOW** (branch `posts-shadow`), so the rehearsal happens BEFORE P5 and the flip to `on` is the go-live | **(a) any time, no P5 needed:** press **Post it** on https://blackbloc.heygabi.ai/posts.html with the mode left at **shadow** — the real message goes into `#blackbloc-logs`, reads exactly as it will, and is kept edited there. **(b) at the cutover, P5 done:** point `welcome` at `#welcome`, set the switch to **on**, press **Post it**. Then delete Carl-bot's `1285806434050768927` by hand and turn Carl's welcome off | (a) the pill reads **posted (shadow)** and the copy in `#blackbloc-logs` is pinned and correct. (b) the message is in `#welcome`, pinned, reads exactly as Carl's did, the pill reads **posted** with no **changes not yet posted**, ⚠️ **the shadow copy is gone** and the log carries `post.shadow_taken_down`. Nothing here deletes Carl's message for you | Carl-bot's welcome post |

## 3. Retire the incumbents

Per-module turn-offs happen inside the ladder (rows 2, 3, 6, 7, 8). The **kick**
of Carl-bot, YAGPDB, Birthday Bot, Modmail + the dormant three (`Verification
Bot`, `baf`, `Black Block`) is a separate, later owner action — **owner set the
horizon 2026-09-01: "in a few weeks"**. Before kicking, Claude takes a final
scan of anything only those bots hold (Carl's dashboards are already archived
under `archive/current-bots/`).

## 4. Standing risks

- 🔴 **The one brake after P5 is per-feature modes — and this is now the CURRENT state, not a
  warning about a future one.** Since 2026-09-18 16:08 anything `on` acts on the real server
  immediately: **events, requests, modmail and chat** are live to members by the owner's word
  (*"its live and people can use it"*). Everything else is held by its own mode, and a mode is
  one click on https://blackbloc.heygabi.ai/settings.html — there is no second gate behind it.
  ⚠️ **A build that posts anything must now ship `shadow` unless the owner says otherwise**;
  "the guard will catch it" is not a thing a brief may say any more. That is by design; the
  sweep is what earns it. ⚠️ The list of what is `on` above is the conductor's 2026-09-18
  reading — **re-read the live values on the Settings page before acting on it**.
- ⚠️ **A reconcile that posts is a live-server risk, not a test-mode one.** The 16:08 boot is
  what proved it (P4z). Every such path now goes through `loops.Reconciler` — checklist item
  **37** — and `posted.duplicates_near` logs a `*.duplicate_seen` row rather than posting a
  third message. A new posted-and-kept-current surface that skips either is the next incident.
- **The dashboard carries automod's arming refusal too** (the gate pass filed as KI-21, **CLOSED at v89** `243dc0f` and gone from `KNOWN_ISSUES.md`; landed v84
  `675f233`: `api/settings_api.py:gated_writers` hands `automod_mode`, `honeypot_mode`
  and `honeypot_exempt_role_ids` to the cog's own move, so a `PUT` gets the panel's
  verdict). Either door is safe to flip from; the 2026-09-04 finding that said
  otherwise was closed before it was ever re-listed.
- ✅ **KI-5's DM behaviour IS moot** — P5 happened 2026-09-18 16:08, and the entry now
  carries that banner. This line predicted it correctly.
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
