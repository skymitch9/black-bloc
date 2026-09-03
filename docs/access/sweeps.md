# Owner sweeps — what is shipped but never exercised by a person

> **Audience:** the owner. **Status:** TRACKED (owner, 2026-08-31 — permanently, not temporarily). Last verified:
> **2026-09-03** — rows **80–86** added by the POLLS PANEL build (`/poll` becomes ONE command that
> opens a panel; the eleven subcommands go), and rows **6, 8, 9 and 27** were rewritten in place
> for it rather than added. Rows 80–86 are **live in v65** (`d13e1a4`, 14:14) and were not run against
> Discord by eye. Same day, before that — rows **73–79** added by the EVENTS PANEL build (`/event`
> becomes one command that opens a panel and the whole `/timezone` group is retired — the
> program's first real `commands synced` drop, 44 → 43); **live in v64** (`e670542`, 14:05),
> none run by eye yet; row 79's empty-select half is the one item the build could not check at
> all; rows 32 and 48 and the Phase 4 appendix script below were rewritten in place for it.
> Earlier — rows **87–93** added by the birthdays panel build (`/birthday` is ONE command that
> opens a panel; the twelve subcommands are retired; the Phase 5 prose block was replaced by
> those rows — it named six subcommands that no longer exist plus `/birthday import`, deleted
> 2026-08-27) — **live in v63**, none run by eye yet. Before that — rows **69–72** added by the
> applications no-role build (a form may keep a LIST instead of handing a role over; merged
> `main` at 12:40, LIVE in v62 12:48); rows **66–68** added by the requests SIXTH pass ("Ask them
> to check": the DM, the channel ping when their DMs are closed, and the auto-ask at ready) —
> LIVE in v61 (`44170f4`, 12:29). The file now holds **86** un-exercised rows, numbered to 93;
> none of 66–93 has been run against Discord or the live site.
> Same day — row **62** now says the done card does NOT post (owner: "suppress the
> request.done box in discord" — `request_channel_moves` default drops `done`). Same
> morning, row **65** added, and rows **14–15** corrected again, by the owner's
> "make the view request thing staff only" (viewing requests on the panel): a member no
> longer sees their own list unless `request_panel_own_list` is on. Before that, the same
> day — rows **58–64** added by the requests fourth pass (`/request` becomes one
> panel; rows 14–15 rewritten in place for the same build — the file now holds **69**
> un-exercised rows, numbered to 72). ⚠️ Rows 14–15 and 58–65 are **BUILT, not yet live** — merge and deploy
> land them; not run against Discord (this build cannot reach it). Before that, **2026-09-02**
> — rows **53–57** added by the Phase 19 (applications) build and rows
> **48–52** by the Phase 18 (F19, raid trains) build, both built in parallel. ✅ Rows 43–57 are LIVE: 43–47 shipped with Phase 16
> (`049881b`, 2026-09-02 22:18) and 48–57 with the 17 → 18 → 19 merge deployed `7b1c592`
> on 2026-09-03; every one of them may be attempted now (all three modes ship **off** — flip
> `chat_memory_mode` / `raidtrain_mode` / `applications_mode` first). Before that, rows
> **43–47** were added by the Phase 16 (F3, YouTube uploads) build. Before that, rows
> **38–42** were added by the Phase 15 (F14) build. Before that, 2026-08-31 — rows 18–20 and the phase-script appendix moved in
> whole from `TODO.md`; this file is the ONE home for un-exercised items. "Verified" below means a human did it in the real server;
> everything else is test-suite evidence only. Tick a row by moving it to the verified table with the date.

All of this happens in **`#mute-me-bot-test-spam`** (test mode) or on **https://blackbloc.heygabi.ai**.

## Verified by the owner
| Date | What | Result |
|---|---|---|
| 2026-08-27 | `@Black Bloc hi` (chat step 1) | replies |
| 2026-08-27 | `/golive test` (card with game art) | posts |
| 2026-08-27 | dashboard Direction A, themes, Members, Polls, Chat pages render | seen by Claude in the owner's browser |
| 2026-09-01 | **Site sweep round 1** — rows 25 (one-time sign-out + sign-in), 26 and 28 (R1 shell + Black Bloc look), plus general clicking | owner: "i did the sweep of the site and its good for now"; keeps sweeping the rest |

## Not yet verified — in the order that matters
| # | Feature | Do this | Expect |
|---|---|---|---|
| 1 | Role approval (Phase 9) | Dashboard → Role menus → Edit `runner-status` → Approval on, Expires after 7, Retry after 7, Channel → Save; post it; pick the role as a member | ephemeral "Sent to staff…"; a card with Approve/Deny in the staff (or set) channel; Approve → DM + role; Members chip shows "· 7 d"; Timed roles section lists it; `/role extend` moves it; End now removes it |
| 2 | Reconciliation | give someone a menu role by hand | Logs shows `role.changed_by_hand` (actor blank until the Bots role has **View Audit Log**) |
| 3 | Temp voice panel | join **join** | your channel's own text chat holds the control panel; buttons work; the log has no `panel_failed` (if it does: Bots role needs Send Messages in voice channels) |
| 4 | YouTube go-live | go live on YouTube with the Discord connection showing "Streaming on YouTube" (`golive_mode` shadow or on) | a card "… is now live on YouTube!" (or a `would_announce` line in shadow) |
| 5 | Stream end | end a stream | with `golive_end_mode` off the announcement is untouched; set it to `edit` and end another: suffix + "was live" card |
| 6 | Polls — native | `/poll` → **Create** → pick single/checkbox/yesno/rating in the modal → **Post it**; vote; `/poll` → pick it → **End** | a real Discord poll under a Black Bloc line; results embed on end; dashboard Polls row |
| 7 | Polls — the label question | look at test poll message `1542651824950218792` | does its first answer show as a DATE or as literal `<t:1788400000:d>`? Tell Claude — it decides `poll_date_labels` |
| 8 | Polls — panel | `/poll` → **Create**, tick **Nobody is told who voted**; then another with kind **date** → **Date slots…** 12 slots | Black Bloc's own button panel; anonymous never shows names |
| 9 | Polls — recurring, reminder | `/poll` → **Create** → **Repeat…** weekly; and a 1-hour poll | the next occurrence opens on schedule; a reminder 60 min before close |
| 10 | Chat 2 | `@Black Bloc how many of us` / `who's live` / `what's next` / `birthdays` / `my roles` / `I need a mod`; edit a greeting line on /chat.html then `hi` | live answers; the edited line is used; 👋🏿 tone visible |
| 11 | Birthday daily import | nothing to do — read the log after a restart | `birthdays: the daily import took nothing new — {… 'already': 38 …}` |
| 12 | Logs (Phase 12, live 18:38) | flip `golive_log_level` to `all`, `/golive test`, then back to `important`, `/golive test` again; `/golive logs` | Discord line only in `all`; dashboard shows both; a role request still posts its card with `rolemenu_log_level = off` |
| 13 | Emoji tone | `@Black Bloc hi` until a 👋 line comes up | dark tone by default; `emoji_skin_tone` setting changes it |
| 14 | Requests — the panel, staff (fourth pass, `/request` is now ONE command) | `/request` in the test channel as staff | an ephemeral panel: a counts line (open / being worked on / ready to check / on hold), your own requests (staff always see theirs), **File a request** / **Refresh** / **Open on the site**, a **Pick a request…** select (capped at 25, says "N of M — the rest are on the site" past that), and a **Logs** button that answers with a NEW ephemeral message (the panel stays put) |
| 15 | Requests — the panel, member | `/request` as a non-staff member | the same panel minus the staff controls: File a request / Refresh / Open on the site — and **NO list of your own requests**, because viewing requests on the panel is staff-only (`request_panel_own_list`, off by default). Once you have an open or held one, a **Take one back…** select still appears — picking one shows its card with **Yes, take it back** / **Keep it** |
| 16 | Via column | change one setting from Discord (`/settings set-value …`) and one from the website | Logs page → Settings audit shows **Discord** and **Website** in the Via column; `/settings logs` says the same |
| 17 | Cyberpunk look | cog → Cyberpunk | the estate's cyan/yellow palette again (no magenta) — say if it still reads wrong |
| 18 | `/help` (batch 2) | `/help`, then `/help filter:temp` | command list with `(staff)` marks on staff-only entries |
| 19 | Round-1 fixes | `/rolemenu showall`; open the `/twitch link` picker; `/tempvoice setup` | showall lists every menu (ephemeral); the picker says **channel**, never *login*; setup says **repaired / took it over** (never a second lobby), lobby named "join to create a channel", Member + staff can connect |
| 20 | Temp-voice memory (batch 4) | in your temp channel: `/voice permit @someone`, `/voice ban @someone-else`, `/voice region us-west` → leave (channel deletes) → re-join the lobby | the new channel has the same region and the same two people set; `/voice info` shows both halves; `/voice reset` clears it |
| 21 | Temp-voice room controls (B4, live 2026-08-31) | with a temp channel open: https://blackbloc.heygabi.ai/tempvoice.html → Open now | each row shows In it / Cap / Access + Rename, Cap, Lock, Hide buttons; press Rename — the channel renames and the reply says "remembered for next time" |
| 22 | Role-menu Un-post + Seed (B5+B6, live 2026-08-31) | /rolemenus.html → Un-post beside Post on a posted card; the Seed defaults button beside New menu; also `/rolemenu unpost` in Discord | un-post takes the panel down in the channel (in test mode: a `would_unpost` log line instead); seed says created/left-alone in words and never rewrites an existing menu |
| 23 | Staff assign from the site (B7, live 2026-08-31) | /rolemenus.html → Timed roles → "Hand roles out": pick a member, a menu, roles → Give these | the member's roles change (⚠️ REAL roles even in test mode, same as `/rolemenu assign`); the Logs page shows `web.role_menu.assign` with Via: Website |
| 24 | Event detail + edit (B8, live 2026-08-31) | /events.html → Queue → Open on a pending event → change the title or start in "Change it" | detail card shows every field; the review channel renames to match the new title; an already-posted announcement keeps its old text and the reply says so |
| 25 | One-time sign-out (sessions, live 2026-08-31 ~12:20) | open https://blackbloc.heygabi.ai | you are signed OUT once (old cookies have no session id) — sign in and everything is back; sign out and reload: signed out for real now (revoked server-side, not just cleared) |
| 26 | R1 shell (live 2026-08-31 ~12:20) | https://blackbloc.heygabi.ai/automod.html then /settings.html then any page | automod: two columns, no dead right half; type in a setting → a docked "N changes pending · Save Changes" bar (per-field Save/Clear gone); Settings: human labels with small mono keys, hover a row for ⌫ reset; rail has an icon per item; ⚙ walks all 6 themes × light/dark and the docked bar stays on-screen in every one |
| 27 | Keyed anonymous poll (live 2026-08-31) | `/poll` → **Create** with **Nobody is told who voted** ticked, vote | works exactly as before from your side; tell Claude when the first one exists and it verifies the vote row is HMAC-keyed |
| 28 | The Black Bloc look (R2, live 2026-08-31 ~13:14) | https://blackbloc.heygabi.ai — you'll land in the new default theme | warm charcoal + ember, the BLACK BLOC wordmark and page titles in Bangers, the Overview opens with a TODAY sentence ("Nothing's on fire. …") whose clauses link to their pages; ⚙ → flip Appearance to Light and back; your previously chosen theme (if you ever picked one) still wins over the default |
| 29 | Ctrl+K palette (R2) | press **Ctrl K** on any page, type `birthday_role`, Enter; then Ctrl K → type `theme: cyber` | lands on Settings with the row flashed ember; the theme switches instantly; the palette also finds pages and actions (sign out, show keys) |
| 30 | Show keys + Cases drawer (R2) | Settings → **Show keys** top-right, toggle + reload; Moderation → click a case row | keys hidden by default, toggle remembered per browser; the case opens in a right-hand drawer, Esc closes; note the table toolbars and "Showing 1–N of M" feet on Logs/Members/Cases/Polls/Requests |
| 31 | Live role survives a repoint (live 2026-09-01) | set `golive_live_role_id`, go live, CHANGE the setting to a different role mid-stream, stop | the **first** role comes off (not the new one); `/golive logs` shows `remove_role` with the original id |
| 32 | Requester in their review channel (live 2026-09-01) | `/event` → **Propose an event** (in the test channel while TEST_MODE; was `/event create` before 2026-09-03) | the reply says the pending channel is yours to post in; you can see + type in `pending-<you>-<title>`, and still can after Approve renames it |
| 33 | Chat LLM — before/after the switch (Phase 14, live 2026-09-01, OFF) | `/chat status` now (expect "off", tiers named as not ready); after you set both keys + flip `chat_llm_mode on`: `/chat status` again, then `@Black Bloc what do you make of all this then` | a real in-voice answer instead of "Not sure I follow"; `/chat status` shows answers today 1 and the month above $0.00 — **the first real cost figure anyone will have seen** |
| 34 | Knowledge grounding (Phase 14) | `/chat knowledge add title:Cookout hours body:The cookout runs Friday evenings.` → `@Black Bloc when is the cookout?`; `/chat knowledge list`; try `remove` on a server-written note | the answer quotes your note; the list shows yours + the server-written ones once the daily loop runs; removing a server note refuses in words |
| 36 | The chat-hardening wave (live 2026-09-01 19:01) | the 6-line list Claude posted in chat (role lookups, member-trust, hidden commands from a non-staff account, DBZ retest, Groq routing via `/chat status`, event-hosting answer) | each line names its expected answer; `/chat logs` shows `chat.reply_reference_fixed` when the guard catches an invention |
| 37 | Costs card (live 2026-09-01 19:01) | https://blackbloc.heygabi.ai/health.html#sect-costs then Settings → Costs → `cost_hosting_usd` = your Fly invoice figure | per-model spend matches `/chat status`; the hosting row stops saying "fill it in"; the Chat page's dollar figure links here |
| 38 | Ping roles — set-up (F14, `pings_mode` ships **off**) | `/pingroles setup` in the test channel, then Dashboard → Go-live → Pings → switch on; `/rolemenu post notifications` | the reply names the role it made or reused and says both feeds now point at it, plus "still off" until you flip it; a **Notifications** panel with one 🔔 option; `/pings events on` as a member puts the role on |
| 39 | Ping roles — a streamer's own role | as a linked streamer: `/pings fans on`; as staff for somebody else: `/pingroles streamer add @member`; then `/pings follow` from a second account | the role is made (named from `pings_fan_role_template`), a **Streamer pings** menu appears, `/pings follow` puts it on and `/pings list` names both halves. ⚠️ If Discord refuses, the reply says the Bots role has to sit ABOVE the new role and `/pingroles logs` has `pings.forbidden` |
| 40 | Ping roles — the announcement prefix | with `golive_mode` on (or shadow, and read the `would_announce` line) and a fan role on the streamer: go live | the line starts `<@&Events> <@&… pings>` — both roles, never twice, the shared one first; end the stream with `golive_end_mode edit` and the edit adds the suffix without adding a mention |
| 41 | Ping roles — 26 streamers (paging) | only if you ever have more than 25: `/pingroles streamer list` | there are TWO panels, `streamers` and `streamers-2`; post the second one too. ⚠️ Never exercised — the 25-per-select cap is Discord's documented limit, tested with 26 rows in the suite but not in the server |
| 42 | Ping roles — the dashboard | Dashboard → Go-live → Pings | the table shows every streamer, their role, a follower count (or a dash when the role was deleted by hand), who started it; Remove asks first; "Create for a streamer" makes one; the Logs section under it is `pings.*` only |
| 43 | YouTube uploads — link (F3, `youtube_mode` ships **off**) | `/youtube link` with your channel address (the `youtube.com/channel/UC…` one; an `@handle` works too), then `/youtube status` | the reply names the channel, says how many videos were counted as history, and says out loud that announcements are **off** until a Lead runs `/uploads mode on`. ⚠️ Nothing already published is ever announced — that is what the count is for |
| 44 | YouTube uploads — an actual upload | with `/uploads mode shadow`: publish something on the linked channel, then wait and run `/uploads logs` | within ~25 minutes a `youtube.would_announce` line carrying the rendered text (**KI-13** explains the two delays). Flip to `on` and repeat for a real post in the test channel |
| 45 | YouTube uploads — Shorts and live streams | publish a Short; separately, start a YouTube live stream | the Short is skipped with `youtube.skipped reason=short` (turn `youtube_announce_shorts` on and the next one posts); a live stream is skipped only while Discord shows you live on YouTube — see **KI-11**, that is the gap `YOUTUBE_API_KEY` would close |
| 46 | YouTube uploads — the dashboard | Dashboard → Go-live → **YouTube uploads** | the sweep card says running with a last-good time; the links table shows who is linked and whether their feed has answered yet; Recent uploads colours each row announced / would / skipped; Unlink asks first; **Upload settings** and **Upload logs** sit under it |
| 47 | YouTube uploads — the staff paths | `/uploads setup channel:#somewhere ping_role:@…`, `/uploads link-for @member <channel>`, `/uploads list` | setup names where posts will go; link-for counts their history the same way; list shows the mode, the channel, the sweep health and **api key — not set (feed only)** |
| 48 | Raid trains — build one (F19, `raidtrain_mode` ships **off**) | `/raidtrains mode on` (or Events page → Raid train settings), then `/raidtrain create` — title, what it is, `2026-09-14 19:30`, 60, 4 | the form is read in YOUR stored zone (set it with **My time zone** on `/event`; `/timezone` was retired 2026-09-03); the reply names where the lineup went; in the test channel a lineup post appears with four `open` rows and a thread under it. ⚠️ In TEST_MODE the post only lands if `raidtrain_channel_id` is the test channel — otherwise `/raidtrains logs` has one `raidtrain.post_skipped_test_mode` line and nothing is posted |
| 49 | Raid trains — claim, release, the cap | `/raidtrain list`, then `/raidtrain claim` with no slot; try `/raidtrain claim` a second time; `/raidtrain mine`; `/raidtrain release` | the first claim takes slot **#1** and the lineup post EDITS itself (no second message); the second refuses in words naming `raidtrain_max_slots_per_member`; `mine` shows the hour in your own clock; release opens it again. From an account with no `/twitch link`, claim refuses and names `/twitch link` |
| 50 | Raid trains — the reminder DM | claim a slot that starts **inside the next 30 minutes** (make a train starting ~35 min out), then wait one sweep (5 min) | ⚠️ **a DM, not a channel post** — it names your slot time, who raids INTO you and who you raid NEXT, with their twitch.tv links, plus a jump link to the lineup. Exactly once, ever. `/raidtrains logs` has one `raidtrain.remind`; in `shadow` it is `raidtrain.would_remind` and no DM |
| 51 | Raid trains — the train moves | with a train running (`live`) and `raidtrain_live_posts` on: have a slot holder actually go live on Twitch | within one sweep the slot gets a ✅ on the lineup and a line lands in the train's thread: "**login** is live — next up **login** at …". ⚠️ It sees only what go-live sees — a hidden presence with no Twitch link is never noticed (**KI-16**) |
| 52 | Raid trains — the organizer half and the dashboard | `/raidtrain assign`, `unassign`, `swap`, `lock`, `unlock`, `cancel`; then https://blackbloc.heygabi.ai/events.html#sect-raidtrains | assign ignores the per-member cap; swap moves the PEOPLE and never the times; lock refuses further claims and says who unlocks it; cancel DMs every holder with your reason. On the page: the trains table, Open → the slot grid with Put somebody in / Take off, "Change two slots round", Lock/Cancel, **Raid train settings** (13 keys) and **Raid train logs** below it |
| 35 | Personality + the cap drill (Phase 14) | `/chat personality set voice:noir` → @-mention again; then `/settings set-value key:chat_monthly_cap_usd value:0` → @-mention → set it back to 20; dashboard: /chat.html Knowledge/Personality/Spend sections | the noir answer is clipped but complete; at cap 0 you get an ordinary line with **no mention of money or limits** and one `chat.llm_capped` in `/chat logs`; the Spend meter names why each quiet tier is quiet |

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
- **Phase 4 (live; rewritten 2026-09-03 for the panel — every subcommand below is gone):**
  `/event` → **My time zone** → type `America/Phoenix` (expect the current local time
  back) → **Propose an event** (the same modal, 5 fields; start `YYYY-MM-DD HH:MM` about
  3 minutes ahead, duration `30m`) → expect a `pending-<you>-<title>` channel INSIDE
  the test category and the review card posted in the test channel with Approve/Deny
  → click Approve: channel renamed `approved-…`, announcement in the test channel,
  `event.would_create_scheduled` in the log (no real scheduled event in test mode),
  DM to you → wait for start: "starting now" post; after the end: `done-…`. Create
  a second one and Deny it with a reason from the panel's **Pick an event…** →
  **Deny**: `denied-…` + DM. The staff panel's list, **Settings** (shows loop health)
  and **Call it off** replace `/event list`, `/event settings` and `/event cancel`.
- **Phase 5 (live, mode `shadow`):** superseded by rows **87–93** below — `/birthday`
  is one panel now and every subcommand this block named is retired. The sweep the
  wishes themselves still get is: set your own birthday to today on the panel → within
  5 min expect a `birthday.would_announce` line in the test channel (`Wishes are… → on`
  to see the actual embed, colour `#4eefff`). The daily Birthday Bot import runs on its
  own loop; there has been no `/birthday import` since 2026-08-27.
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

### Phase 19 — applications (the Twitch Team form). ⚠️ On the branch; not merged, not deployed.

| # | Feature | Do this | Expect |
|---|---|---|---|
| 53 | Applications — the switch | /rolemenus.html → **Applications** → set it to **shadow**, then **on**; or `/settings set-value applications_mode on` | the segment saves in place and says so; with it **off** `/apply` disappears from Discord within about five seconds and the Apply buttons stop working |
| 54 | Applications — the form | follow the Twitch Team walk-through below (either the slash path or the dashboard editor) | `/applications question list twitch-team` shows five questions in order; the dashboard's form editor shows the same five, and Up/Down really reorders them |
| 55 | Applications — applying | in `#mute-me-bot-test-spam`: `/apply start twitch-team` (or press **Apply** on the posted panel) | a modal with your five questions; on submit an ephemeral "Sent to staff…", a DM "…is with staff now", and a card with **Approve** / **Deny** in the test channel (test mode redirects it there and the reply says so) |
| 56 | Applications — deciding | press **Approve** on that card | the applicant gets the role; the card is edited to say who has it and carries `@<owner> — next step: the Team owner sends your twitch.tv invite…`; the applicant is DMed the same thing; /rolemenus.html → Applications shows it under Decided and the Timed roles table has a clock on it if the form set one. Then apply again as somebody else and press **Deny** with a reason: the DM carries the reason AND the date they may apply again |
| 57 | Applications — the second application guard | apply twice on the same form without withdrawing | the second one refuses in words ("you already have an application waiting"); `/apply withdraw twitch-team` takes it back and lets you apply again; after a **deny**, applying again says *when* you may, not just no |
| 58 | Requests — panel move, Pick up (fourth pass) | `/request` as staff, pick an **open** request, press **Pick up** | the card re-renders **being worked on**; a card posts to the status channel if one is configured |
| 59 | Requests — panel move, Hold | on an open / in-progress / review card, press **Hold**, fill "Why is it on hold?" | the card re-renders **on hold**; the asker is DMed the reason (`request_dm_on_decision`) |
| 60 | Requests — panel move, Decline | press **Decline**, fill "Why?" | the card re-renders **declined**, final ("nothing moves it now"); the asker is DMed |
| 61 | Requests — panel move, Ready to check | on an in-progress card, press **Ready to check**, fill "What was built?" (+ optional "How does somebody test it?") | the card re-renders **ready to check**; nobody is DMed — it is staff-facing |
| 62 | Requests — panel move, Accept | on a review card, press **Accept** | the card re-renders **done**, final; the asker is DMed with what was built; ⚠️ **no done card appears in the request channel** (owner 2026-09-03: website logs only — `request_channel_moves` defaults to every move but `done`; tick it back on the Settings page to see one). Turn `request_review_by_other` on and reopen the same card as the staffer who marked it ready: Accept is gone, the footer says who may press it |
| 63 | Requests — panel move, Send back | on a review card, press **Send back**, fill "What's left?" | the card re-renders **being worked on**; whoever marked it ready is DMed the note |
| 64 | Requests — panel move, Resume | on a held card, press **Resume** | the card re-renders back where it was held from — usually being worked on, sometimes ready to check |
| 65 | Requests — giving members their list back | `/settings set-value key:request_panel_own_list value:true`, then `/request` as a non-staff member who has filed something | the member's own requests are summarised on the panel again (and "You have not asked for anything yet" when they have none) — exactly row 15's old behaviour. Set it back to `false` and the lines go away again; the Settings page has the same switch |
| 66 | Requests — Ask them to check (sixth pass) | `/request` as staff, open a request that is **ready to check**, press **Ask them to check** | the person who filed it gets a DM titled *"Request #N is ready for you to try 🙌"* with what was built, how to test it, who marked it ready and a line asking them to try it and say how it went; the card you are looking at re-renders with a new **Asked to check · @you · just now** field and stays **ready to check** (it does NOT move); the ephemeral reply says they were asked by DM; one `request.check_asked` line on the Requests log. The same button is on the review card at https://blackbloc.heygabi.ai/requests.html, between Accept and Send back, with an *asked by … · just now* chip beside the status |
| 67 | Requests — the ping when their DMs are closed | turn Discord DMs off for the account that filed the request (Privacy Settings → allow DMs from server members: off), then press **Ask them to check** again | the DM fails, so the card is posted in the request channel with a **real @mention** of the person who asked — the only place the requests bot ever pings anybody; the reply says their DMs are closed and they were pinged instead; the log carries a `request.dm_failed` line as well as `request.check_asked`. Then `/settings set-value key:request_check_fallback_channel value:false` and press it again: nothing is posted, and the reply names the key a Lead turns back on |
| 68 | Requests — asking automatically at ready | `/settings set-value key:request_check_on_ready value:true`, then take a request that is **being worked on** and press **Ready to check** | the DM from row 66 arrives with no second button press, and the log shows `request.review` followed by `request.check_asked`; set it back to `false` and the next Ready-to-check tells nobody. Both switches are on the Settings page too |

### Applications, no-role pass — a form that keeps a LIST. ⚠️ On the branch `feat/applications-no-role`; not merged, not deployed.

| # | What | Do this | Expect |
|---|---|---|---|
| 69 | A form with no role at all | on **https://blackbloc.heygabi.ai/rolemenus.html#applications** press **New form**, fill Name + Heading, leave **Role it hands over** on **No role — keep a list**, save. (`/applications create name:stream-team title:Stream Team` with no `role:` does the same thing) | the form saves; the **Role lasts, days** box disappears while the role is blank; the forms table shows a grey **list** badge in the Role column instead of a role chip. An existing form is switched over with `/applications edit form:<name> no_role:true`, or by picking the blank option in the editor |
| 70 | Applying and being approved with nothing to hand over | put the Apply button up, apply as a member, press **Approve** on the card | the card and the ephemeral reply say "Approved — **<name>** is on the **<heading>** list now." — no role is mentioned and none is given. The DM is the form's approved text with no "the role runs out" line. `/applications logs` shows `application.approved` with `granted: null` and NO `application.granted` line |
| 71 | The roster, and Copy as text | on the Role menus page open **Approved for <form>** under that form | one row per approved member: their name, **twitch.tv/<login>** as a link (or a quiet "not linked"), how long since staff said yes, and who decided. Somebody who has left the server is still listed with "left the server" beside them — `/settings set-value key:applications_roster_shows_left value:false` hides them instead. **Copy as text** puts one line per member on the clipboard, ready to paste into the official team page |
| 72 | Taking somebody off the list | on the roster press **Take off the list**, type a reason, confirm. (In Discord: `/applications show <id>` on an approved application — the same **Take off the list** button is on the panel) | they are DMed the reason and when they may apply again; the Decided table shows the row as **removed**; the roster is one shorter; `/applications list form:<name> status:approved` no longer names them. On a form that DOES hand a role over the button is not offered at all, and the route refuses in words pointing at `/role revoke` |
| 80 | Polls — the panel opens | `/poll` in #mute-me-bot-test-spam, first as a Lead and then as a plain member | ONE ephemeral panel, not a list of subcommands: **Create · Find #… · Refresh** on the top row for everybody, **Settings · Logs** added for a Lead only; a "Pick a poll…" select under it once something is running; a Lead also sees the counts line (**N** running · **N** waiting on a decision · **N** repeating) and, with a repeating poll saved, a second "Repeating polls…" select; **Open on the site** links to https://blackbloc.heygabi.ai/polls.html. A member sees no Settings and no Logs at all rather than buttons that refuse |
| 81 | Polls — Create through the two-step modal | on the panel press **Create**: type the question, `Pizza \| Tacos \| Neither`, leave hours blank, pick a kind on the radio, tick nothing; submit; on the preview pick a channel, a ping role, flip **Thread: off**; press **Post it** | the modal carries exactly five things (question, options, hours, the kind radio, the two switches) — Discord's cap; the preview is a card of what you typed with **Post it · Repeat… · Start over · Cancel**, and NOTHING is written until Post it (press **Cancel** on a preview and `/poll` shows no new poll). After Post it: the poll is up in the channel you picked, and `/poll` → **Logs** shows one `poll.created` and one `poll.opened` — never two of either |
| 82 | Polls — a date poll through the extra step | **Create** with kind **date**, no options; on the preview press **Date slots…**, start `2026-09-05`, 4 slots, step 1, unit **days**; **Post it** | before the slots are given there is no **Post it** button at all and the preview says the poll needs its slots; after them, four dated answers in the order you asked for. `poll_date_labels` still decides whether they read as `Sat 05 Sep` or as each reader's own clock |
| 83 | Polls — pick one and End it | with a poll running, `/poll` → pick it on the select → **End** | picking IS the results: the card is the same results embed `/poll results` used to print. **End** shows for the person who started it and for staff; the poll closes, the result posts in the channel, and the card re-renders with no moves left ("nothing moves a closed poll now"). As a bystander the card has only **Back** — the move is not drawn rather than refused. `/settings set-value key:poll_creator_may_end value:false` and the author loses End too; staff keep it |
| 84 | Polls — Cancel from the card | `/poll` → pick a running poll → **Cancel** (Lead only) | the vote is ended at Discord, no result is published, and the card re-renders **cancelled** with nothing left to press. **Find #…** takes any poll number (with or without the `#`) so a closed, cancelled or archived one is still reachable once it has dropped off the select |
| 85 | Polls — review on, Approve and Deny from the panel | `/poll` → **Settings** → press **Review: off** so it reads **Review: on**; as a member (with Create open to everyone) start a poll; then as a Lead `/poll` → pick the waiting poll → **Approve** on one, **Deny** + a reason on another | the panel decides it, not just the staff-channel card: Approve posts the poll and DMs the author; Deny DMs them the reason. ⚠️ A denied poll is NOT the end of the line — open it again and there is a **Post it anyway** button (owner's standing rule: staff can always leave a state), which posts it and tells the author it was approved after all |
| 86 | Polls — a recurrence paused, started and deleted | on a preview press **Repeat…** (weekly, `19:00`, `sat`, your zone) → **Post it**; then `/poll` → "Repeating polls…" → pick it → **Pause** → **Resume** → **Delete** → **Yes, stop it repeating** | the card names the cadence in words, when it next runs (or **paused**), the channel, the kind and the options. Pause/Resume/Delete are the SAME code the dashboard's Polls page runs, so https://blackbloc.heygabi.ai/polls.html and the Logs page agree — one `poll.recur_paused` / `_resumed` / `_deleted` line each, marked Via: Discord here and Via: Website there. Deleting leaves every poll it already opened alone |

| 73 | Events — the panel, member (`/timezone` is GONE) | `/event` as a non-staff member | ONE ephemeral panel: the intro, **your time zone line** (the old `/timezone show`, word for word), and the row **Propose an event · My time zone · Refresh · Open on the site**. **NO list of events** — `event_panel_own_list` ships off, exactly like requests. `/timezone` no longer exists in the command list at all |
| 74 | Events — setting your zone from the panel | **My time zone** → type `America/Phoenix`; open it again and type `Phoenix`; then type `nonsense` | the first saves and the panel re-renders with the local time; `Phoenix` on its own is refused in words and **suggests `America/Phoenix`** ("Did you mean…"), which is more help than the old autocomplete gave; `nonsense` is refused with no guess. Nothing is saved by either refusal. ⚠️ The box is a plain modal, not a picker — Discord caps a select at 25 options and this machine knows 598 zones |
| 75 | Events — proposing one | **Propose an event** | the same five-field modal `/event create` opened, unchanged. The reply now shows **both readings of the time you typed** — "7:00 PM your time (America/Phoenix) · `<t:…:F>`" — so you can see what the bot understood and what everybody else's client will render. A `pending-<you>-<title>` channel and its Approve/Deny card as before |
| 76 | Events — the panel, staff | `/event` as a Lead | the member panel **plus** a counts line (`N pending · N approved · N live`), the open events written out with who may approve, a **Pick an event…** select (capped at 25 — past that the placeholder says "25 of N — the rest are on the site"), **Settings** and **Logs**. Press **Logs**: it answers a **NEW** message and the panel stays where it is |
| 77 | Events — deciding from the panel | **Pick an event…** → a `pending` one → **Approve**; pick another → **Deny** and type a reason | the card re-renders approved/denied in place, the requester is DMed, the review channel renames — identical to pressing the buttons on the review card, because it is the same `apply_decision`. A `denied` card then offers **Approve after all** (staff always get the final say) while its review room still exists; once the room has been swept the card says so in words instead |
| 78 | Events — calling one off, both doors | on the staff card press **Call it off** and type a line; separately, as the member who proposed one, use **Call one off…** on your own panel | staff: the note is **optional** (dismiss the box and it still goes off) and whatever you type is appended to the requester's DM. Member: a plain **Yes, call it off / Keep it** confirm and no DM to yourself. Either way the event is cancelled, the channel renamed and an already-posted announcement edited |
| 79 | Events — settings without a subcommand | **Settings** on the staff panel | one sub-panel: a **mode** select, a category picker, an announce-channel picker, a ping-role picker, **Scheduled events: on/off**, **Numbers…** (retention days + how late is still announceable, refused in words when outside their bounds), **Forget…** and **Back**. The lines above update after every write and `/event logs` shows one `event.settings` row per press. ⚠️ **Try clearing a picker by submitting it EMPTY** — that is the one thing this build could not check without Discord; if your client will not send an empty select, **Forget…** does the same job and the write path is identical |

### Birthdays — `/birthday` is ONE panel (wave 1). Live in v63 (`616adb3`, 2026-09-03).

| # | What | Do this | Expect |
|---|---|---|---|
| 87 | The member panel with nothing stored | `/birthday` in `#mute-me-bot-test-spam` from an account with no birthday stored | one ephemeral panel: the intro, a line saying wishes are in **shadow** so nothing is posted yet, "Black Bloc has no birthday for you… **Set my birthday** button", the next five birthdays, and exactly two buttons — **Set my birthday** and **Refresh** — plus a **Look someone up…** picker. No Status, no Logs, no month list, no mode picker |
| 88 | Setting it, and the three refusals | press **Set my birthday**, type `09-15`, submit. Then **Change my birthday** and try `13-40`, then `09-15-2200`, then `next tuesday` | the panel re-renders with **September 15**, the zone by name and the next occurrence as a date + "in N months"; the ephemeral line says the same. `13-40` answers "There is no month **13**…", `09-15-2200` answers "**2200** is not a birth year Black Bloc can use…", `next tuesday` answers "Black Bloc could not read that as a date…" — and in all three cases nothing is stored. Reopening the modal offers the stored date back, `09-15` |
| 89 | Opting out and back in | press **Opt out**, then **Opt in** | after Opt out the panel says "You are **opted out**" and the row shows **Opt in** only (no Opt out); after Opt in it swaps back. The Birthdays log carries `birthday.optout` then `birthday.optin` |
| 90 | Removing it | press **Remove** → **Keep it**; then **Remove** → **Yes, forget it** | Keep it puts you back on the panel with the birthday still stored; Yes, forget it answers "Your birthday is forgotten", the panel goes back to the **Set my birthday** row, and the log carries one `birthday.remove` |
| 91 | Staff: looking somebody up and setting their birthday | as staff, `/birthday` → **Look someone up…** → pick a member with nothing stored → **Set their birthday** → `01-02` | their card names them and says Black Bloc has no birthday for them; the modal title reads *Set <name>'s birthday*; on submit the card re-renders with **January 2** and gains a **Forget their birthday** button. **Forget their birthday** → confirm: they are DMed one sentence saying staff removed it, and the log carries `birthday.remove` naming you as the actor. A member who is not staff sees only **Back** on that card |
| 92 | Staff: the month list and the mode picker | as staff: **List a month…** → **Every month**, then **August**, then a month nobody is in; then **Wishes are…** → **on** | the list arrives as one or more NEW ephemeral messages grouped by month (`· 10 — @PT (self)`), and the panel itself stays open behind them; an empty month answers "Nobody has a birthday stored in **March**." The mode picker re-renders the panel with the shadow warning gone, and the log carries `birthday.mode` |
| 93 | Staff: status, the role and the logs, then the quiet footer | as staff: **Status**; **Clear the birthday role** → confirm; **Logs**; then leave the panel alone for `birthday_panel_minutes` (10) minutes | Status is a new ephemeral message with mode, channel, template, colour, role, ages, the stored counts and both loops' last run/last error — the panel stays. Clear asks first, then answers "No birthday role will be given any more…" (or "There was no birthday role set" when none was). Logs opens the Birthdays log as its own ephemeral message. After ten minutes every button on the panel is greyed out and the embed footer reads *This panel has gone quiet — run /birthday again* |

## The owner's Twitch Team form — the walk-through

This is the form Phase 19 was built for (Pawpette's request, 2026-09-02). Nothing
about the Team is in the code: it is all data you create, and you can make a second
form the same way for anything else staff hand out.

⚠️ **The twitch.tv Team invite has no API.** Black Bloc owns the form, the review, the
role and the DMs; a human still clicks *invite* on twitch.tv. That click is what the
`owner` + `next_step` fields exist to name — see `KNOWN_ISSUES.md`.

**In Discord** (every step has a dashboard twin on /rolemenus.html → Applications):

1. `/applications mode value:on`
2. `/applications create name:twitch-team title:Twitch Team role:@Twitch Team`
   — add `channel:` if the cards should not go to the staff channel, and
   `approver_role:` if somebody other than staff decides them.
3. The five questions, in this order:
   - `/applications question add form:twitch-team label:Twitch handle placeholder:twitch.tv/…`
   - `/applications question add form:twitch-team label:How long have you been streaming`
   - `/applications question add form:twitch-team label:What is your usual schedule`
   - `/applications question add form:twitch-team label:What do you stream`
   - `/applications question add form:twitch-team label:Why the Team style:long required:False`
4. `/applications edit form:twitch-team owner:@<the Team owner> next_step:the Team owner sends your twitch.tv invite — accept it from your Twitch notifications`
   — and, if you want one, `approved_text:` (what the DM says) and `expires_days:`
   (0 or blank means the role never runs out).
5. `/applications panel form:twitch-team` — puts the **Apply** button up in that
   channel. Run it again anywhere to move it. Members can also use `/apply start`.
6. Check it: `/applications list`, `/applications show <id>`, `/applications logs`.

**To close it for a while** (applications in progress are untouched):
`/applications edit form:twitch-team open:False`.

## When something fails
Take a screenshot, note the time, and paste it to Claude with the row number — the Fly logs around that
minute plus the dashboard Logs page are enough to diagnose. Nothing here is destructive; the worst case is
a `would_*` line in the log where you expected a post (that is test mode doing its job).
