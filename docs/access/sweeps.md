# Owner sweeps — what is shipped but never exercised by a person

> **Audience:** the owner. **Status:** TRACKED (owner, 2026-08-31 — permanently, not temporarily). Last verified:
> **2026-08-31** — rows 18–20 and the phase-script appendix moved in whole from `TODO.md`; this file
> is the ONE home for un-exercised items. "Verified" below means a human did it in the real server;
> everything else is test-suite evidence only. Tick a row by moving it to the verified table with the date.

All of this happens in **`#mute-me-bot-test-spam`** (test mode) or on **https://blackbloc.heygabi.ai**.

## Verified by the owner
| Date | What | Result |
|---|---|---|
| 2026-08-27 | `@Black Bloc hi` (chat step 1) | replies |
| 2026-08-27 | `/golive test` (card with game art) | posts |
| 2026-08-27 | dashboard Direction A, themes, Members, Polls, Chat pages render | seen by Claude in the owner's browser |

## Not yet verified — in the order that matters
| # | Feature | Do this | Expect |
|---|---|---|---|
| 1 | Role approval (Phase 9) | Dashboard → Role menus → Edit `runner-status` → Approval on, Expires after 7, Retry after 7, Channel → Save; post it; pick the role as a member | ephemeral "Sent to staff…"; a card with Approve/Deny in the staff (or set) channel; Approve → DM + role; Members chip shows "· 7 d"; Timed roles section lists it; `/role extend` moves it; End now removes it |
| 2 | Reconciliation | give someone a menu role by hand | Logs shows `role.changed_by_hand` (actor blank until the Bots role has **View Audit Log**) |
| 3 | Temp voice panel | join **join** | your channel's own text chat holds the control panel; buttons work; the log has no `panel_failed` (if it does: Bots role needs Send Messages in voice channels) |
| 4 | YouTube go-live | go live on YouTube with the Discord connection showing "Streaming on YouTube" (`golive_mode` shadow or on) | a card "… is now live on YouTube!" (or a `would_announce` line in shadow) |
| 5 | Stream end | end a stream | with `golive_end_mode` off the announcement is untouched; set it to `edit` and end another: suffix + "was live" card |
| 6 | Polls — native | `/poll create` kind single/checkbox/yesno/rating; vote; `/poll end` | a real Discord poll under a Black Bloc line; results embed on end; dashboard Polls row |
| 7 | Polls — the label question | look at test poll message `1542651824950218792` | does its first answer show as a DATE or as literal `<t:1788400000:d>`? Tell Claude — it decides `poll_date_labels` |
| 8 | Polls — panel | `/poll create … anonymous:true` and one `kind:date slots:12` | Black Bloc's own button panel; anonymous never shows names |
| 9 | Polls — recurring, reminder | `/poll recur create` weekly; a 1-hour poll | the next occurrence opens on schedule; a reminder 60 min before close |
| 10 | Chat 2 | `@Black Bloc how many of us` / `who's live` / `what's next` / `birthdays` / `my roles` / `I need a mod`; edit a greeting line on /chat.html then `hi` | live answers; the edited line is used; 👋🏿 tone visible |
| 11 | Birthday daily import | nothing to do — read the log after a restart | `birthdays: the daily import took nothing new — {… 'already': 38 …}` |
| 12 | Logs (Phase 12, live 18:38) | flip `golive_log_level` to `all`, `/golive test`, then back to `important`, `/golive test` again; `/golive logs` | Discord line only in `all`; dashboard shows both; a role request still posts its card with `rolemenu_log_level = off` |
| 13 | Emoji tone | `@Black Bloc hi` until a 👋 line comes up | dark tone by default; `emoji_skin_tone` setting changes it |
| 14 | Requests — staff (Phase 13, live 20:15) | `/request create` in the test channel as staff (What / Why / due date) | ephemeral "Filed as #N … approved straight away"; the row appears on https://blackbloc.heygabi.ai/requests.html under Planned & in progress; `/request list`, `/request logs` |
| 15 | Requests — member | have a non-staff member sign in at https://blackbloc.heygabi.ai and file one; or `/request create` as a member | they see ONLY the Requests page (file + their own); the row lands in Pending; Approve / Decline from the page → DM; `/request withdraw <id>` while pending |
| 16 | Via column | change one setting from Discord (`/settings set-value …`) and one from the website | Logs page → Settings audit shows **Discord** and **Website** in the Via column; `/settings logs` says the same |
| 17 | Cyberpunk look | cog → Cyberpunk | the estate's cyan/yellow palette again (no magenta) — say if it still reads wrong |
| 18 | `/help` (batch 2) | `/help`, then `/help filter:temp` | command list with `(staff)` marks on staff-only entries |
| 19 | Round-1 fixes | `/rolemenu showall`; open the `/twitch link` picker; `/tempvoice setup` | showall lists every menu (ephemeral); the picker says **channel**, never *login*; setup says **repaired / took it over** (never a second lobby), lobby named "join to create a channel", Member + staff can connect |
| 20 | Temp-voice memory (batch 4) | in your temp channel: `/voice permit @someone`, `/voice ban @someone-else`, `/voice region us-west` → leave (channel deletes) → re-join the lobby | the new channel has the same region and the same two people set; `/voice info` shows both halves; `/voice reset` clears it |
| 21 | Temp-voice room controls (B4, live 2026-08-31) | with a temp channel open: https://blackbloc.heygabi.ai/tempvoice.html → Open now | each row shows In it / Cap / Access + Rename, Cap, Lock, Hide buttons; press Rename — the channel renames and the reply says "remembered for next time" |
| 22 | Role-menu Un-post + Seed (B5+B6, live 2026-08-31) | /rolemenus.html → Un-post beside Post on a posted card; the Seed defaults button beside New menu; also `/rolemenu unpost` in Discord | un-post takes the panel down in the channel (in test mode: a `would_unpost` log line instead); seed says created/left-alone in words and never rewrites an existing menu |
| 23 | Staff assign from the site (B7, live 2026-08-31) | /rolemenus.html → Timed roles → "Hand roles out": pick a member, a menu, roles → Give these | the member's roles change (⚠️ REAL roles even in test mode, same as `/rolemenu assign`); the Logs page shows `web.role_menu.assign` with Via: Website |
| 24 | Event detail + edit (B8, live 2026-08-31) | /events.html → Queue → Open on a pending event → change the title or start in "Change it" | detail card shows every field; the review channel renames to match the new title; an already-posted announcement keeps its old text and the reply says so |

## Detailed phase scripts (1–8a) — moved whole from `TODO.md` 2026-08-31

The step-by-step click scripts for the seven core phases + 8a, as accumulated
while each landed. Rows 1–20 above are the priority order; these are the long
form for a full pass.

- **Phase 1 (live):** in `#mute-me-bot-test-spam` run `/settings show` (expect the
  three keys with the test channel as default) → `/rolemenu seed-defaults` →
  `/rolemenu list` → `/rolemenu post pronouns` → pick roles on the panel (expect an
  ephemeral "Added: …/Removed: …" and your roles change) → `/rolemenu show
  interests`. Try `/rolemenu list` from a non-staff account: expect the staff
  sentence. Check the action-log embeds landed in the same channel.
- **Phase 2 (live, mode `shadow`):** `/golive status` (expect mode shadow, channel =
  test channel, Twitch polling running with a last-ok time) → `/golive test` (ephemeral
  preview, no ping) → `/twitch link <your channel>` (expect "linked" or "could not be
  checked") → go live on Twitch once with Discord showing the Streaming status: expect
  a `golive.would_announce` embed in the test channel within seconds (presence) — and
  nothing in `#live-now`. Stop streaming: expect `golive.end` ~2 min later. Try
  `/golive optout` then `/golive optin`. `/settings show` now lists the 8 golive keys.
- **Phase 3 (live; honeypot `shadow`):** `/tempvoice setup` (expect a "join to
  create a channel" voice channel created INSIDE the test channel's category while
  TEST_MODE, and the reply saying so) → join it: expect `<you>'s bloc` to appear next
  to it and you moved in; the control panel goes into `#mute-me-bot-test-spam` with a
  first line naming the voice channel it controls, logged as
  `tempvoice.panel_elsewhere`, and its buttons work from there; press Rename and
  Lock → leave: channel deleted within ~60 s. `/tempvoice status`. Also try the new
  group: `/voice info`, `/voice bitrate`, `/voice region`. Then `/honeypot setup`
  (trap created in the test category; notice skipped in test mode) → post in it from
  a throwaway account: message deleted, a `honeypot.would_ban` embed with a **Ban
  now** button in the test channel; nobody banned. `/honeypot status` (expect the
  resolved staff-role count > 0). Role rider: `/rolemenu seed-defaults` again
  (expect "already there" for the five, created `runner-status`) → `/rolemenu assign
  runner-status @someone` (staff picker) → `/rolemenu post event-alerts` shows the
  real `:JoyGAMING:` emoji only if you delete and re-seed that menu (the seed never
  rewrites existing options).
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

## When something fails
Take a screenshot, note the time, and paste it to Claude with the row number — the Fly logs around that
minute plus the dashboard Logs page are enough to diagnose. Nothing here is destructive; the worst case is
a `would_*` line in the log where you expected a post (that is test mode doing its job).
