# Owner sweeps — what is shipped but never exercised by a person

> **Audience:** the owner. **Status:** TRACKED (owner, 2026-08-31 — permanently, not temporarily). Last verified:
> **2026-09-03** — rows **135–143** added by the TEMP-VOICE PANEL build (`/voice` becomes ONE
> member-visible command that opens a panel; the `tempvoice` and `voice` groups and all
> twenty-two subcommands are retired, so the top-level count drops by one — **39 → 38, measured**
> through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, since this
> build has no token to boot with). Rows **19**, **20** and the Phase 3 appendix block below were
> rewritten IN PLACE for it rather than added. ⚠️ **Nothing in 135–143 has met live Discord** —
> no panel opened, no channel made, no DM sent. The in-channel control post is deliberately
> untouched and still works exactly as it did. Same day —
> rows **118–125** added by the YOUTUBE PANEL build (`/youtube` becomes ONE
> command that opens a panel; the `youtube` and `uploads` groups and their nine subcommands go,
> so `commands synced` drops by one — **41, measured** by loading every cog). Rows **43**, **44**
> and **47** were rewritten IN PLACE for it rather than added. ⚠️ Rows 118–125 have **not** been
> run against Discord and **nothing has been run against YouTube** — no channel resolved, no feed
> fetched, no panel opened. `youtube_mode` is still `off`. The block was written as 130–137 (the golive branch had reserved 109–129) and was
> renumbered to **118–125 at the merge**, since golive took 109–117. Before that, same day —
> **2026-09-03** — rows **109–117** added by the GO-LIVE PANEL build (`/golive` becomes ONE command that
> opens a panel; the `golive` and `twitch` groups and all eight subcommands are retired — a real
> `commands synced` drop, 42 → 41, measured through `tests/test_bot.py` rather than a boot). Rows **12,
> 19, 31, 49** and the Phase 2 appendix script below were rewritten in place for it rather than added;
> ⚠️ the **verified** row for `/golive test` (2026-08-27) is HISTORY and is left exactly as it is. Rows
> 104–108 are the memory panel's (below), which is why these start at 109 — the numbering held at the
> merge, nothing renumbered. ⚠️ **Nothing in 109–117 has met live Discord.** Same day — rows
> **104–108** added by the MEMORY PANEL build (`/memory` becomes ONE
> command that opens a panel; the five subcommands go, and `commands synced` does NOT move
> because a group already counted as one slot — **42, measured**). ⚠️ Rows 104–108 have **not**
> been run against Discord at all, and 104–107 need `chat_memory_mode` turned on first, which it
> is not. Same day — row **103** added by
> the OPERATOR READ TOKEN build (a Claude session can read
> `/api/*` with a bearer and change nothing). ⚠️ It is the first row here that cannot be run at
> all until the owner mints a secret, and nothing in it has met the live app. Same day —
> rows **80–86** added by the POLLS PANEL build (`/poll` becomes ONE command that
> opens a panel; the eleven subcommands go), and rows **6, 8, 9 and 27** were rewritten in place
> for it rather than added. Rows 80–86 are **live in v65** (`d13e1a4`, 14:14) and were not run against
> Discord by eye. Same day, before that — rows **73–79** added by the EVENTS PANEL build (`/event`
> becomes one command that opens a panel and the whole `/timezone` group is retired — the
> program's first real `commands synced` drop, 44 → 43); **live in v64** (`e670542`, 14:05),
> none run by eye yet; row 79's empty-select half is the one item the build could not check at
> all; rows 32 and 48 and the Phase 4 appendix script below were rewritten in place for it.
> Same day — rows **94–102** added by the APPLICATIONS PANEL build (`/apply` is ONE command that
> opens a panel; both the `apply` and `applications` groups and their seventeen subcommands go —
> the program's second `commands synced` drop, 43 → 42, measured). Rows **53–57**, **69–72** and
> the whole Twitch Team walk-through below were rewritten in place for it rather than added; row
> 53 now tests the OPPOSITE of what it used to (owner, 2026-09-03 13:47: "Visible" — the command
> no longer disappears when applications are off). Rows 94–102 are **live in v66**
> (`853776c`, 15:00) and none was run against Discord by eye.
> Earlier — rows **87–93** added by the birthdays panel build (`/birthday` is ONE command that
> opens a panel; the twelve subcommands are retired; the Phase 5 prose block was replaced by
> those rows — it named six subcommands that no longer exist plus `/birthday import`, deleted
> 2026-08-27) — **live in v63**, none run by eye yet. Before that — rows **69–72** added by the
> applications no-role build (a form may keep a LIST instead of handing a role over; merged
> `main` at 12:40, LIVE in v62 12:48); rows **66–68** added by the requests SIXTH pass ("Ask them
> to check": the DM, the channel ping when their DMs are closed, and the auto-ask at ready) —
> LIVE in v61 (`44170f4`, 12:29). The file now holds **96** un-exercised rows, numbered to 103;
> none of 66–103 has been run against Discord or the live site.
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
| 12 | Logs (Phase 12, live 18:38) | flip `golive_log_level` to `all`, `/golive` → **Preview an announcement…**, then back to `important` and preview again; `/golive` → **Logs** | Discord line only in `all`; dashboard shows both; a role request still posts its card with `rolemenu_log_level = off` |
| 13 | Emoji tone | `@Black Bloc hi` until a 👋 line comes up | dark tone by default; `emoji_skin_tone` setting changes it |
| 14 | Requests — the panel, staff (fourth pass, `/request` is now ONE command) | `/request` in the test channel as staff | an ephemeral panel: a counts line (open / being worked on / ready to check / on hold), your own requests (staff always see theirs), **File a request** / **Refresh** / **Open on the site**, a **Pick a request…** select (capped at 25, says "N of M — the rest are on the site" past that), and a **Logs** button that answers with a NEW ephemeral message (the panel stays put) |
| 15 | Requests — the panel, member | `/request` as a non-staff member | the same panel minus the staff controls: File a request / Refresh / Open on the site — and **NO list of your own requests**, because viewing requests on the panel is staff-only (`request_panel_own_list`, off by default). Once you have an open or held one, a **Take one back…** select still appears — picking one shows its card with **Yes, take it back** / **Keep it** |
| 16 | Via column | change one setting from Discord (`/settings set-value …`) and one from the website | Logs page → Settings audit shows **Discord** and **Website** in the Via column; `/settings logs` says the same |
| 17 | Cyberpunk look | cog → Cyberpunk | the estate's cyan/yellow palette again (no magenta) — say if it still reads wrong |
| 18 | `/help` (batch 2) | `/help`, then `/help filter:temp` | command list with `(staff)` marks on staff-only entries |
| 19 | Round-1 fixes | `/rolemenu showall`; `/golive` → **Link my Twitch channel**; `/voice` → **Setup** | showall lists every menu (ephemeral); the modal says **channel**, never *login*; Setup says **repaired / took it over** (never a second lobby), lobby named "join to create a channel", Member + staff can connect |
| 20 | Temp-voice memory (batch 4) | in your temp channel: `/voice` → **People…** → *Let someone in…*, *Keep someone out…*; **Region…** → `us-west`; leave (channel deletes) → re-join the lobby | the new channel has the same region and the same two people set; the panel's **remembered for next time** block shows both halves; **Forget my settings** clears it |
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
| 31 | Live role survives a repoint (live 2026-09-01) | set `golive_live_role_id`, go live, CHANGE the setting to a different role mid-stream, stop | the **first** role comes off (not the new one); `/golive` → **Logs** shows `remove_role` with the original id |
| 32 | Requester in their review channel (live 2026-09-01) | `/event` → **Propose an event** (in the test channel while TEST_MODE; was `/event create` before 2026-09-03) | the reply says the pending channel is yours to post in; you can see + type in `pending-<you>-<title>`, and still can after Approve renames it |
| 33 | Chat LLM — before/after the switch (Phase 14, live 2026-09-01, OFF) | `/chat` now (expect "off", tiers named as not ready); after you set both keys, press **Turn the conversation models on** on the same panel, then `@Black Bloc what do you make of all this then` | a real in-voice answer instead of "Not sure I follow"; re-open `/chat` and the status block shows answers today 1 and the month above $0.00 — **the first real cost figure anyone will have seen**. One `chat.mode` row for the flip |
| 34 | Knowledge grounding (Phase 14) | `/chat` → **Knowledge…** → **Write one down…** (title `Cookout hours`, body `The cookout runs Friday evenings.`) → `@Black Bloc when is the cookout?`; then **A note…** on a server-written row | the answer quotes your note; the list shows yours + the server-written ones once the daily loop runs; a `server` note's card has **neither** Remove nor Edit and says the daily read owns it |
| 36 | The chat-hardening wave (live 2026-09-01 19:01) | the 6-line list Claude posted in chat (role lookups, member-trust, hidden commands from a non-staff account, DBZ retest, Groq routing read off the `/chat` status block, event-hosting answer) | each line names its expected answer; `/chat` → **Logs** shows `chat.reply_reference_fixed` when the guard catches an invention |
| 37 | Costs card (live 2026-09-01 19:01) | https://blackbloc.heygabi.ai/health.html#sect-costs then Settings → Costs → `cost_hosting_usd` = your Fly invoice figure | per-model spend matches the `/chat` status block; the hosting row stops saying "fill it in"; the Chat page's dollar figure links here |
| 38 | Ping roles — set-up (F14, `pings_mode` ships **off**) | `/pings` as staff → **Set up the Events role** → leave the role picker empty → **Set it up**; then **Settings** → **Mode…** → on; `/rolemenu post notifications` | the reply names the role it made or reused and says both feeds now point at it, plus "still off" until you flip the mode; a **Notifications** panel with one 🔔 option; **Turn event pings on** as a member puts the role on. Rows **126–134** walk the whole panel |
| 39 | Ping roles — a streamer's own role | as a linked streamer: `/pings` → **Start my own ping role**; as staff for somebody else: `/pings` → **Streamers…** → **Give somebody a ping role…**; then **Follow a streamer…** from a second account | the role is made (named from `pings_fan_role_template`), a **Streamer pings** menu appears, following puts it on and the panel names both halves. ⚠️ If Discord refuses, the reply says the Bots role has to sit ABOVE the new role and **Logs** has `pings.forbidden` |
| 40 | Ping roles — the announcement prefix | with `golive_mode` on (or shadow, and read the `would_announce` line) and a fan role on the streamer: go live | the line starts `<@&Events> <@&… pings>` — both roles, never twice, the shared one first; end the stream with `golive_end_mode edit` and the edit adds the suffix without adding a mention |
| 41 | Ping roles — 26 streamers (paging) | only if you ever have more than 25: `/pings` → **Streamers…** | there are TWO panels, `streamers` and `streamers-2`; post the second one too. The member's **Follow a streamer…** select caps at 25 and says *"25 of N — the rest are on the *Streamer pings* panels"*, NOT "on the site" — a member cannot open the site. ⚠️ Never exercised in the server; the 25-per-select cap is Discord's documented limit, tested with 26 rows in the suite |
| 42 | Ping roles — the dashboard | Dashboard → Go-live → Pings | the table shows every streamer, their role, a follower count (or a dash when the role was deleted by hand), who started it; Remove asks first; "Create for a streamer" makes one; the Logs section under it is `pings.*` only |
| 43 | YouTube uploads — link (F3, `youtube_mode` ships **off**) | `/youtube` → **Link my channel**, paste your channel address (the `youtube.com/channel/UC…` one; an `@handle` works too) | the reply names the channel, says how many videos were counted as history, and says out loud that announcements are **off** until a Lead changes **Announcements are…** on the same panel. The panel then shows the five status lines. ⚠️ Nothing already published is ever announced — that is what the count is for |
| 44 | YouTube uploads — an actual upload | staff: `/youtube` → **Announcements are…** → **shadow**. Publish something on the linked channel, then wait and press **Logs** | within ~25 minutes a `youtube.would_announce` line carrying the rendered text (**KI-13** explains the two delays). Set the same picker to **on** and repeat for a real post in the test channel |
| 45 | YouTube uploads — Shorts and live streams | publish a Short; separately, start a YouTube live stream | the Short is skipped with `youtube.skipped reason=short` (turn `youtube_announce_shorts` on and the next one posts); a live stream is skipped only while Discord shows you live on YouTube — see **KI-11**, that is the gap `YOUTUBE_API_KEY` would close |
| 46 | YouTube uploads — the dashboard | Dashboard → Go-live → **YouTube uploads** | the sweep card says running with a last-good time; the links table shows who is linked and whether their feed has answered yet; Recent uploads colours each row announced / would / skipped; Unlink asks first; **Upload settings** and **Upload logs** sit under it |
| 47 | YouTube uploads — the staff paths | `/youtube` as staff → **Setup** (pick a channel and a ping role), **Back** → **Link for somebody…** → pick a member → paste their channel | the panel's own embed is the old `/uploads list` header — the mode, the channel, the sweep health, **api key — not set (feed only)** and who is linked; Setup names where posts will go; linking for somebody counts their history the same way. Rows **118–125** walk the whole panel |
| 48 | Raid trains — build one (F19, `raidtrain_mode` ships **off**) | `/raidtrains mode on` (or Events page → Raid train settings), then `/raidtrain create` — title, what it is, `2026-09-14 19:30`, 60, 4 | the form is read in YOUR stored zone (set it with **My time zone** on `/event`; `/timezone` was retired 2026-09-03); the reply names where the lineup went; in the test channel a lineup post appears with four `open` rows and a thread under it. ⚠️ In TEST_MODE the post only lands if `raidtrain_channel_id` is the test channel — otherwise `/raidtrains logs` has one `raidtrain.post_skipped_test_mode` line and nothing is posted |
| 49 | Raid trains — claim, release, the cap | `/raidtrain list`, then `/raidtrain claim` with no slot; try `/raidtrain claim` a second time; `/raidtrain mine`; `/raidtrain release` | the first claim takes slot **#1** and the lineup post EDITS itself (no second message); the second refuses in words naming `raidtrain_max_slots_per_member`; `mine` shows the hour in your own clock; release opens it again. From an account with no linked Twitch channel, claim refuses and points at `/golive` → **Link my Twitch channel** |
| 50 | Raid trains — the reminder DM | claim a slot that starts **inside the next 30 minutes** (make a train starting ~35 min out), then wait one sweep (5 min) | ⚠️ **a DM, not a channel post** — it names your slot time, who raids INTO you and who you raid NEXT, with their twitch.tv links, plus a jump link to the lineup. Exactly once, ever. `/raidtrains logs` has one `raidtrain.remind`; in `shadow` it is `raidtrain.would_remind` and no DM |
| 51 | Raid trains — the train moves | with a train running (`live`) and `raidtrain_live_posts` on: have a slot holder actually go live on Twitch | within one sweep the slot gets a ✅ on the lineup and a line lands in the train's thread: "**login** is live — next up **login** at …". ⚠️ It sees only what go-live sees — a hidden presence with no Twitch link is never noticed (**KI-16**) |
| 52 | Raid trains — the organizer half and the dashboard | `/raidtrain assign`, `unassign`, `swap`, `lock`, `unlock`, `cancel`; then https://blackbloc.heygabi.ai/events.html#sect-raidtrains | assign ignores the per-member cap; swap moves the PEOPLE and never the times; lock refuses further claims and says who unlocks it; cancel DMs every holder with your reason. On the page: the trains table, Open → the slot grid with Put somebody in / Take off, "Change two slots round", Lock/Cancel, **Raid train settings** (13 keys) and **Raid train logs** below it |
| 35 | Personality + the cap drill (Phase 14) | `/chat` → **Personality…** → **The voice…** → `noir` → @-mention again; then **Back** → **Settings** → **Limits…** and set the monthly cap to 0 → @-mention → set it back to 20; dashboard: /chat.html Knowledge/Personality/Spend sections | the noir answer is clipped but complete; at cap 0 you get an ordinary line with **no mention of money or limits** and one `chat.llm_capped` in `/chat` ▸ **Logs**; the Spend meter names why each quiet tier is quiet. One `chat.settings` row per **Limits…** save, never five |

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
- **Phase 2 (live, mode `shadow`; ONE command since 2026-09-03):** `/golive` as staff —
  the embed carries the status lines (expect mode shadow, channel = test channel, Twitch
  polling running with a last-ok time) → **Preview an announcement…** → *Twitch*
  (ephemeral preview, no ping, nothing posted) → **Link my Twitch channel** and type your
  channel (expect "Linked" or "could not be reached to check") → go live on Twitch once
  with Discord showing the Streaming status: expect a `golive.would_announce` embed in
  the test channel within seconds (presence) — and nothing in `#live-now`. Stop
  streaming: expect `golive.end` ~2 min later. Try **Stop announcing my streams** then
  **Announce my streams again**. `/settings show` now lists the golive keys.
- **Phase 3 (live; honeypot `shadow`; rewritten 2026-09-03 for the panel — every
  subcommand below is gone):** `/voice` as a Lead → **Setup** (expect a "join to
  create a channel" voice channel created INSIDE the test channel's category while
  TEST_MODE, and the reply saying so) → join it: expect `<you>'s bloc` to appear next
  to it and you moved in; the control panel goes into `#mute-me-bot-test-spam` with a
  first line naming the voice channel it controls, logged as
  `tempvoice.panel_elsewhere`, and its buttons work from there (that post is
  unchanged and is a second door onto the same functions); press Rename and
  Lock → leave: channel deleted within ~60 s. `/voice` again for the staff block that
  replaced `/tempvoice status`, and the panel itself for what `/voice info`,
  `/voice bitrate` and `/voice region` used to say — **Bitrate** and **Region…**.
  Then `/honeypot setup`
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

### Phase 19 — applications (the Twitch Team form). Live since v56; rows 53–57 rewritten for the `/apply` panel (v66).

| # | Feature | Do this | Expect |
|---|---|---|---|
| 53 | Applications — the switch, and the command that does NOT vanish | /rolemenus.html → **Applications** → set it to **shadow**, then **on**, then back to **off**; or `/settings set-value applications_mode off` | the segment saves in place and says so. ⚠️ **With it off `/apply` is STILL in Discord** (owner, 2026-09-03: "Visible") — open it and the panel says *"Applications are turned off right now…"* in words and offers **no** form to apply for, while staff still get **A form…**, **New form**, **Settings** and **Logs**. The posted Apply buttons stop working. This is the opposite of what row 53 tested before the panel, when the whole member command disappeared within five seconds |
| 54 | Applications — the form | follow the Twitch Team walk-through below (either the Discord panel or the dashboard editor) | `/apply` → **A form…** → **Questions…** shows five questions in order; the dashboard's form editor shows the same five, and Up/Down really reorders them (reorder is site-only — the sub-panel says so and links there) |
| 55 | Applications — applying | in `#mute-me-bot-test-spam`: `/apply` → **Apply for…** → **Twitch Team** (or press **Apply** on the posted panel) | a modal with your five questions; on submit an ephemeral "Sent to staff…", a DM "…is with staff now", and a card with **Approve** / **Deny** in the test channel (test mode redirects it there and the reply says so) |
| 56 | Applications — deciding | press **Approve** on that card | the applicant gets the role; the card is edited to say who has it and carries `@<owner> — next step: the Team owner sends your twitch.tv invite…`; the applicant is DMed the same thing; /rolemenus.html → Applications shows it under Decided and the Timed roles table has a clock on it if the form set one. Then apply again as somebody else and press **Deny** with a reason: the DM carries the reason AND the date they may apply again |
| 57 | Applications — the second application guard | apply twice on the same form without withdrawing | the second one refuses in words ("you already have an application waiting"); `/apply` → **Take one back…** → **Yes, take it back** withdraws it and lets you apply again; after a **deny**, applying again says *when* you may, not just no |
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

### Applications, no-role pass — a form that keeps a LIST. Live in v62; rows 69–72 rewritten for the `/apply` panel (v66).

| # | What | Do this | Expect |
|---|---|---|---|
| 69 | A form with no role at all | on **https://blackbloc.heygabi.ai/rolemenus.html#applications** press **New form**, fill Name + Heading, leave **Role it hands over** on **No role — keep a list**, save. (In Discord: `/apply` → **New form**, then on its card **Edit…** and leave the role picker alone) | the form saves; the **Role lasts, days** box disappears while the role is blank; the forms table shows a grey **list** badge in the Role column instead of a role chip. An existing form is switched over by submitting **Edit…**'s role picker EMPTY, or by picking the blank option in the editor |
| 70 | Applying and being approved with nothing to hand over | put the Apply button up, apply as a member, press **Approve** on the card | the card and the ephemeral reply say "Approved — **<name>** is on the **<heading>** list now." — no role is mentioned and none is given. The DM is the form's approved text with no "the role runs out" line. `/apply` → **Logs** shows `application.approved` with `granted: null` and NO `application.granted` line |
| 71 | The roster, and Copy as text | on the Role menus page open **Approved for <form>** under that form; in Discord, `/apply` → **A form…** → **Roster** | one row per approved member: their name, **twitch.tv/<login>** as a link (or a quiet "not linked"), how long since staff said yes, and who decided. Somebody who has left the server is still listed with "left the server" beside them — `/settings set-value key:applications_roster_shows_left value:false` hides them instead, on both surfaces. **Copy as text** (site only) puts one line per member on the clipboard |
| 72 | Taking somebody off the list | on the roster press **Take off the list**, type a reason, confirm. (In Discord: `/apply` → **A form…** → **Roster** → **Take somebody off…**, or **Find #…** the application and press **Take off the list** on its card) | they are DMed the reason and when they may apply again; the Decided table shows the row as **removed**; the roster is one shorter. On a form that DOES hand a role over the button is not offered at all and the card says so in words, pointing at `/role revoke` |
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

### Applications — `/apply` is ONE panel (wave 1). Live in v66 (`853776c`, 2026-09-03).

Two commands became one: `/apply` (three subcommands) and `/applications` (fourteen) are both
gone, and every one of the seventeen is a button, a picker or a modal on the panel `/apply`
opens. `commands synced` drops 43 → 42. Nothing about a form, a question, an approval or a log
row changed — only the door.

| # | What | Do this | Expect |
|---|---|---|---|
| 94 | The member panel | `/apply` in `#mute-me-bot-test-spam` as a plain member, with a form open | ONE ephemeral panel: the intro, **your own applications written out** (or "You have not applied for anything here yet."), a line saying form-making is for staff, an **Apply for…** picker, **Refresh** and **Open on the site**. **No** queue, **no** A form…, **no** New form, **no** Settings, **no** Logs — they are not drawn rather than drawn and refused |
| 95 | Applying from the picker | **Apply for…** → **Twitch Team** | the same modal `/apply start` used to open, unchanged; on submit the same "Sent to staff" reply, the same DM, and the same Approve/Deny card in the test channel. Then `/settings set-value key:applications_panel_own_list value:false` and open `/apply` again: your own applications are no longer written out, and the **Take one back…** picker is still there |
| 96 | Taking one back, and changing your mind | **Take one back…** → your waiting application → **Yes, take it back**; apply again, then **Take one back…** → **Keep it** | the first withdraws it — the channel card is edited, the row reads `withdrawn`, and the Logs page carries one `application.withdrawn`. **Keep it** changes nothing and puts you back on the panel. Applying again straight afterwards is allowed: no cooling-off follows a withdrawal |
| 97 | The staff panel | `/apply` as a Lead | the same embed **plus** a counts line (**N** form(s) · **N** waiting · **N** on a list), a **Pick an application…** picker (capped at 25 — past that its placeholder reads "25 of N — the rest are on the site"), an **A form…** picker, and the five-button row **New form · Find #… · Settings · Logs · Refresh** with **Open on the site** under it. Press **Logs**: it answers a **NEW** message and the panel stays where it is. ⚠️ Staff get no **Apply for…** picker — staff apply through **A form…** → **Fill it in** |
| 98 | Deciding from the panel | **Pick an application…** → a waiting one → **Approve**; pick another → **Deny** and type a reason | identical to pressing the buttons on the review card, because it is the same `apply_decision`: the role (or the "on the list" wording), the DM, the channel card edited, and **exactly one** log row each. The card re-renders in place with the moves that are still valid |
| 99 | Staff's exit from a no | on a **denied** card press **Approve after all**; take somebody off a list, then **Find #…** their number and press **Put them back on the list** | both go back to `approved`, the person is DMed the approval, a role form hands the role over, and the log shows `application.approved` (not a new kind). ⚠️ A **withdrawn** card offers nothing and says so — the member owns that one and the way back is applying again |
| 100 | The form card, its questions and clearing a picker | **A form…** → a form → **Questions…** → **Add…**, then pick one → **Edit**, then **Remove** → confirm; **Back** → **Edit…** → submit the **Role it hands over…** picker with nothing chosen | the questions change one at a time, each leaving one `application.question_changed` row; the questions sub-panel says reordering is on the Role menus page and links there. Clearing the role picker leaves the form keeping a list — exactly what `no_role:true` did — and the card's role line reads **nothing — it keeps a list**. ⚠️ **The empty-select submit is the one thing this build could not check without Discord**; if your client will not send one, the site's editor does the same write |
| 101 | Roster, opening and closing, and the Apply button | **A form…** → a no-role form → **Roster** → **Take somebody off…** → a reason; **Back** → **Close it**, then **Open it**; then **Post the Apply button** → pick a channel | the roster is one shorter and they are DMed the reason; the card's "Taking applications" line flips no → yes; the Apply button appears in the channel you picked (test mode refuses any channel but `#mute-me-bot-test-spam`, in words). ⚠️ **Delete** is only drawn when nobody is waiting on the form — with somebody waiting it is absent and the card says how many |
| 102 | Settings, and the quiet footer | **Settings** → the **Mode…** picker → **shadow**; a channel picker; submit the **Who decides…** picker EMPTY; **Numbers…**; then leave the panel alone for `applications_panel_minutes` (10) minutes | the lines above update after every write, the mode write leaves one `application.mode` row, and an empty picker CLEARS its key rather than doing nothing. **Numbers…** takes the retry days and the panel minutes and refuses a value outside their bounds in words. After ten minutes every control is greyed out and the embed footer reads *This panel has gone quiet — run /apply again* |

## Operator read token — what YOU see when a session reads

Built 2026-09-03 (`info/operator-read-design.md`). ⚠️ **Inert until you mint the
secret** — `access/operator-read.md` has the one command, and until you run it
nothing below can happen at all.

| # | What | Do this | Expect |
|---|---|---|---|
| 103 | A session's read shows up in your log | mint `OPERATOR_READ_TOKEN` (one command, `access/operator-read.md`) and deploy; ask the session to run `.\scripts\read.ps1 -Path /api/requests`; then open the **Logs** page (or `/settings logs`) | one new line, `web.operator.read`, whose **Via** column reads **Operator token** rather than Discord or Website, with `path=/api/requests` in its details. One line per read, not one per route. Nothing is posted to Discord (it is a routine Core kind, so `core_log_level` at its default stays quiet). If you would rather see nothing at all, turn **Whether an operator-token read leaves a log line** (`operator_read_log`) off on the Settings page and read again — same data, no line. Ask the session to try a CHANGE and it is refused in words: *the operator token can only look, never change* |

## Chat memory — `/memory` is ONE command that opens a panel

Built 2026-09-03 (`info/memory-panel-design.md`, wave 2). ⚠️ **`chat_memory_mode` ships
`off` and nothing is written down until a Lead turns it on**, so rows 104–107 need
`/settings set-value key:chat_memory_mode value:on` first AND a conversation or two with
Black Bloc, because the profile is only written on the hourly sweep. Everything here is
ephemeral and visible to nobody but you — there is no staff row on this panel by design
(`chat_memory_staff_view` and the Chat page are the staff surface).

| # | What | Do this | Expect |
|---|---|---|---|
| 104 | The panel | `/memory` in `#mute-me-bot-test-spam` after a conversation or two | ONE ephemeral panel titled *What Black Bloc remembers about you*, the line "Nobody else can read this.", your lines NUMBERED `#1 #2 #3` (one learned in a DM marked *(learned in a DM — never used in a channel)*), a **Forget one of these…** picker whose options carry the same numbers, and the row **Forget everything · Stop remembering me · Refresh**. **No** Logs, **no** Open on the site, nothing staff-shaped — a member following a site link would meet a 403, so there is no link |
| 105 | Dropping one line | **Forget one of these…** → pick `#2` | the panel re-renders in place with that line gone and the rest renumbered; the reply says *Dropped **1** line(s)*. Open the **Chat** log (dashboard Logs page, or `/chat logs`): ONE `chat.memory_forgot` row, details `who_asked: self · lines: 1 · via: discord`, and **no trace of what the line said** — the text of a note never reaches the action log |
| 106 | Forgetting the lot, and changing your mind | **Forget everything** → **Keep it**; then **Forget everything** → **Yes, forget it all** | Keep it changes nothing and puts you back on the panel with every line still there and no new log row. Yes clears it: the panel re-renders saying Black Bloc has not written anything down about you yet, the picker is gone, and only **Stop remembering me · Refresh** are left. One `chat.memory_forgot` row |
| 107 | Stopping it, and starting again | **Stop remembering me** → **Yes, stop**; then **Remember me again** | the first wipes AND opts you out in that order — one `chat.memory_optout` row — and the panel then offers **Remember me again · Refresh** only. The second brings the writing back with one `chat.memory_optin` row. ⚠️ Neither one asks staff for anything: this is your own data and the panel never refuses you |
| 108 | Memory switched off, and the quiet footer | leave the panel alone for `memory_panel_minutes` (10) minutes; then `/settings set-value key:chat_memory_mode value:off` and run `/memory` again | after ten minutes every control on the old panel is greyed out and the embed footer reads *This panel has gone quiet — run /memory again*. With the mode off `/memory` **still opens** (owner, 2026-09-03 16:12 — fork I-M1): the panel says Black Bloc is not remembering anybody here as a LINE, whatever it already stored is still listed, and **Forget everything** and the picker still work. Turning memory off does not delete profiles, so this is the only door left to them |

## Go-live — `/golive` is ONE command that opens a panel (wave 2)

Built 2026-09-03 (`info/golive-panel-design.md`), branch
`worktree-agent-a87a00d41b8dc47d1`. ⚠️ **The `golive` and `twitch` groups and all
eight subcommands are gone** — `/golive logs`, `/golive optout`, `/golive optin`,
`/golive status`, `/golive mode`, `/golive test`, `/twitch link` and
`/twitch unlink` are each a button or a select on one panel now, and
`commands synced` drops 42 → 41. ⚠️ **Nothing here has met live Discord**: no
panel has been opened, no button pressed and no Helix call made. Rows **104–108
are claimed by a sibling wave-2 build**, so these take **109 onward** and the
memory panel took 104–108, so these are **109 onward**; the numbering held at the merge.

| # | What | Do this | Expect |
|---|---|---|---|
| 109 | The member panel | `/golive` from an account with no Twitch linked | ONE ephemeral panel titled **Go-live**: an intro line, "**Your Twitch channel** — none linked yet", "**Your streams** — announced here whenever Black Bloc sees you go live", a line saying announcements are in **shadow** right now, and the buttons **Link my Twitch channel · Stop announcing my streams · Refresh · Open on the site**. ⚠️ **No status lines, no Logs, no preview, no mode select** — and the panel says in words that the feed's settings are for staff rather than hiding anything |
| 110 | Linking, and changing your mind | **Link my Twitch channel** → type your channel name; then **Change my channel** → type nonsense; then try a name another member already holds | the first links and the panel says `twitch.tv/<you>` (or "not verified with Twitch" if Twitch could not be reached, which is honest, not a failure); the modal opens **already filled in** the second time; nonsense refuses in words and changes nothing; the taken name refuses **without ever naming who holds it** |
| 111 | Opting out and back in | **Stop announcing my streams**, then **Announce my streams again** | exactly one of the two buttons is ever on the panel; the "Your streams" line flips each way; **Logs** shows one `golive.optout` and one `golive.optin` — one row each, never two |
| 112 | Unlinking is not opting out | **Unlink**, then go live on Twitch with Discord showing Streaming | the link is gone (and the fan role does whatever `pings_fan_role_on_unlink` says); presence still announces you, because unlinking and opting out are different things |
| 113 | The staff panel | `/golive` as a Lead | the same embed **plus** the eleven status lines — mode, stream end, channel, cooldown, twitch polling, last good poll, last poll error, links/opt-outs/live-now, and one line per open session — and **Logs · Streamers… · Preview an announcement… · Announcements: off / shadow / on**. ⚠️ **There is no Status button: the status IS the embed.** Press **Logs**: it answers a **NEW** message and the panel stays put |
| 114 | Previewing an announcement | **Preview an announcement…** → *Twitch*, then *YouTube*, then *As you are now* | three ephemeral previews with the sentence and the card, **no ping**, **nothing posted in any channel**, and one `golive.test` log row each. ⚠️ With `golive_channel_id` pointing anywhere but `#mute-me-bot-test-spam`, the **channel** line SAYS test mode is why nothing real would post — the answer to "why was my stream not announced", in words |
| 115 | The mode select | **Announcements: off / shadow / on** → **on**, then **shadow** | the panel re-renders with the new mode and the select shows it as the chosen option; one `golive.mode` row each; the next go-live behaves accordingly (a real post on `on`, `golive.would_announce` on `shadow`) |
| 116 | Staff acting for somebody else (the gap the website used to be the only door for) | **Streamers…** → pick somebody → **Unlink them** → **Yes, unlink them**; pick another → **Opt them out**, then **Opt them back in** | the same result the Go-live page gives, because it is the same function: one log row each, the card re-renders, and **Unlink them** asks first. Past 25 linked members the select says "25 of N — the rest are on the site" |
| 117 | The panel goes quiet | leave `/golive` alone for `golive_panel_minutes` (10) minutes | every control greys out and the embed footer reads *This panel has gone quiet — run /golive again*. ⚠️ Setting it to 15 or more loses the footer (KI-20) and the help text on the Settings page says so |

## The YouTube panel — `/youtube` is one window (wave 2, 2026-09-03)

Rows **118–125**. `/youtube` is now ONE command that opens a panel; the `youtube` and
`uploads` groups and their nine subcommands are gone, so `commands synced` drops by one
(**41**, measured by loading every cog). ⚠️ **`youtube_mode` still ships `off`**, and rows
119–124 read differently with it on — row 118 is deliberately the off-state reading, which
is the wording least likely to have been exercised. Nothing here has been run against
Discord or against YouTube at all.

| # | What | Do this | Expect |
|---|---|---|---|
| 118 | The member panel with the mode off | `/youtube` in `#mute-me-bot-test-spam` as a plain member with nothing linked | ONE ephemeral panel titled *Your YouTube channel*: an intro line, a line saying announcements are **off** **and that a Lead changes it with Announcements are… on this panel**, then **Link my channel · Refresh · Open on the site**. **No** picker, **no** Setup, **no** Logs. Nothing anywhere says `/uploads` or `/youtube link` |
| 119 | Linking, and the five status lines | **Link my channel** → paste `youtube.com/channel/UC…`; then **Refresh** | the same words `/youtube link` used to give — the channel, how many videos were counted as history, and the off note — and the panel now shows **channel · linked · last video seen · announced here · Shorts**. ONE `youtube.link` row in the Uploads log |
| 120 | The two ways a link can fail, told apart | **Relink…** → paste nonsense; then, if YouTube's feed is having one of its bad days (**KI-12**), try a real `@handle` | TWO DIFFERENT refusals: *I could not turn … into a YouTube channel id* for the paste, and the flaky-feed sentence (*usually the feed being flaky rather than the channel being wrong*) when YouTube would not answer. **Nothing is changed either way**, and the panel stays open. ⚠️ The second half depends on YouTube misbehaving, so it may not be reproducible on demand |
| 121 | Unlinking, and changing your mind | **Unlink** → **Keep it**; then **Unlink** → **Yes, forget it** | Keep it changes nothing and leaves the channel linked with no new log row. Yes forgets it, the panel goes back to **Link my channel**, and there is ONE `youtube.unlink` row. You are never DMed about your own unlink |
| 122 | The staff half | `/youtube` as a Lead | the same card PLUS the health block the old `/uploads list` printed (mode · channel · every N minutes · **api key — not set (feed only)** · last good sweep · last error · links/videos/announced) and who is linked; then **Somebody's channel…**, **Announcements are…**, **Link for somebody… · Setup · Logs**. **Logs** answers a NEW message and the panel stays where it was. Past 25 linked channels the picker says *25 of N — the rest are on the site* |
| 123 | Linking and unlinking for somebody else | **Link for somebody…** → pick a member → paste their channel; then **Somebody's channel…** → pick them → **Unlink for** → type a reason | linking counts their history exactly as `/uploads link-for` did. Unlinking forgets it, **DMs them the reason** (new behaviour — staff-final-say; turn it off with `youtube_unlink_dms_them`), and leaves ONE `youtube.unlink` row. Dismissing the reason box keeps the link |
| 124 | The mode, Setup, and clearing a picker | **Announcements are…** → **shadow**; then **Setup** → pick a channel, then submit the channel picker EMPTY, then **Forget…** → the ping role; **Numbers…** → `2` | the mode line updates and leaves ONE `youtube.mode` row. The empty picker CLEARS the upload channel and the panel says uploads fall back to the go-live channel — **Forget…** does exactly the same thing for a client that will not submit an empty picker. `2` is refused in words naming the five-minute floor and nothing is written. ⚠️ **The empty-picker submit is the one thing this build could not check without Discord** |
| 125 | The quiet footer | leave the panel alone for `youtube_panel_minutes` (10) minutes | every control is greyed out and the embed footer reads *This panel has gone quiet — run /youtube again* |

## The pings panel — `/pings` is one window (wave 2, 2026-09-03)

Rows **126–134**. `/pings` is now ONE command that opens a panel; `/pingroles`, its
`streamer` group and the `events`/`fans` groups are gone — twelve leaf subcommands become
buttons, selects and one modal — so `commands synced` drops by one (**39**, measured by
loading every cog). ⚠️ **`pings_mode` still ships `off`**; row 130 is deliberately the
off-state reading. Nothing here has been run against Discord.

| # | What | Do this | Expect |
|---|---|---|---|
| 126 | The member panel with the mode ON | `/pings` in `#mute-me-bot-test-spam` as a plain member | ONE ephemeral panel titled *Your pings*: your pings written out, **Follow a streamer…**, **Stop following…** if you follow one, the Events toggle, the fan button and **Refresh** — and **no** Streamers…, **no** Settings, **no** Logs, **no** site link (every `/api/pings/*` route is staff-only, so a link would be a sign-in wall). Nothing anywhere says `/pingroles` or `/pings follow` |
| 127 | Follow and unfollow | **Follow a streamer…** → a name; then **Stop following…** → the same name | the role goes on and comes off; the panel re-renders each time; **Logs** shows `pings.follow` then `pings.unfollow`, ONE row each |
| 128 | The Events toggle | press it twice | the role goes on and off, one `pings.events_on` then one `pings.events_off`. With the Events role NOT set up there is no toggle at all and the panel says staff have not made it yet |
| 129 | Your own ping role | as a linked streamer press **Start my own ping role**, then **Take my ping role away** → **Keep it**, then again → **Yes, take it away** | the role is made and appears on the **Streamer pings** panel; Keep it changes nothing and writes no log row; Yes removes it and the panel loses it. ⚠️ It renders even when `pings_fan_role_creation` is `staff` (owner fork I1 = keep today's behaviour): taking a role off yourself is never gated on who was allowed to put it on |
| 130 | With `pings_mode` **off** | `/pings` as a member who follows somebody | the panel still opens and says ping roles are **off**, offers **no** Follow control and **no** toggles — but **Stop following…** is still there and still takes the role off. That asymmetry is deliberate: an access-REDUCING move fails safe and needs no feature switch |
| 131 | The staff half | `/pings` as a Lead | adds a counts line (**N** streamer(s) · **N** with a role Discord still has) and **Streamers… · Set up the Events role · Settings · Logs · Open on the site** — exactly Discord's five per row. **Logs** answers a NEW message and the panel stays. The staff half renders with the mode off as well as on |
| 132 | Set up, and giving somebody a role | **Set up the Events role** → leave the role picker empty → **Set it up**; then again picking an existing role. Then **Streamers…** → **Give somebody a ping role…** → pick a member → **Make the role**; pick them on **A streamer…** → **Remove their ping role** → **Yes, take it away** | the first makes or reuses **Events** and points both feeds at it, and says "still off" while the mode is off; the second reuses the one you picked. Giving is identical to the old `/pingroles streamer add`, removal deletes the Discord role when `pings_fan_role_delete` is on. ⚠️ **Whether the client will submit an EMPTY role picker is the one thing this build could not check without Discord** — the confirm button does the same write either way, which is the fallback |
| 133 | A role somebody deleted by hand | delete a streamer's role in Server Settings, then **Streamers…** → pick them | the card says *the role is gone from the server* and shows **Make the role again**; pressing it makes a fresh one and the Streamer pings panel picks it up. Staff-final-say: without it a tidied-away role is a row staff can only delete |
| 134 | Settings, split feeds, and the quiet footer | **Settings** → flip **Mode…**, flip **Who may start one…** to *staff*, open **Names…** and type `{game} pings`; then point `events_ping_role_id` at a DIFFERENT role from `golive_ping_role_id`; then leave the panel `pings_panel_minutes` (10) minutes | the lines update and each flip leaves ONE `pings.settings` row; **Names…** echoes what the template will ACTUALLY produce and says out loud that a broken one fell back (it never pretends it saved `{game}`); with *staff* set, a member's **Start my own ping role** is gone and the panel says why. Split feeds turn the one toggle into TWO labelled ones (**Turn go-live pings on** / **Turn event pings on**) — owner fork I2. Then every control greys out and the footer reads *This panel has gone quiet — run /pings again* |

## Temp voice — `/voice` is one command that opens a panel (rows 135–143)

Written 2026-09-03 by the temp-voice panel build. ⚠️ **None of it has been run against
Discord** — no panel opened, no channel made, no DM sent; everything below is what the code
and its tests say should happen. Twenty-two subcommands over two top-level slots became ONE
member-visible `/voice`, so the top-level count dropped **39 → 38** (measured through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, not a boot). The
per-channel control post is deliberately UNCHANGED and is still a second door onto the same
functions.

| # | What | Do this | Expect |
|---|---|---|---|
| 135 | The panel with no channel of your own | `/voice` in `#mute-me-bot-test-spam` with no temp channel | ONE ephemeral panel titled *Your voice channel* saying you don't own one and naming the lobby to join — and **no** Rename, **no** Lock, **no** Claim anywhere. Nothing says `/voice rename` or `/tempvoice setup` |
| 136 | Your own channel's card | join the lobby, then `/voice` | the owner card: **Rename · Limit · Lock · Hide · Bitrate** on the first row, then **People… · Region… · Hand it over… · Refresh** — plus **Forget my settings** once anything has been remembered. The lines above are exactly what `/voice info` used to print, including *remembered for next time* |
| 137 | The toggles say what they will do | press **Lock**, then **Refresh**; press **Hide**, then **Refresh** | the button now reads **Unlock** / **Show** — never both at once — and the **locked** / **hidden** lines above it agree, because both read the channel's own `@everyone` overwrite |
| 138 | People, and undoing it | **People…** → *Let someone in…* one member, *Keep someone out…* another; then **Undo for…** | the two names appear on ONE undo select with the right word each (*take their way in back* / *let them back in*); undoing puts the channel's own rules back and it is remembered for next time. *Move someone out…* is only there while somebody else is actually connected |
| 139 | Region and bitrate | **Region…** → pick one → **Automatic**; **Back**; **Bitrate** → `96` | the select holds **25** regions and no `auto` (that is the button), the region changes and is remembered, **Automatic** says Discord picks; a bitrate above this server's boost level says so out loud rather than silently clamping |
| 140 | Somebody else's channel | leave your channel, have somebody else join it and run `/voice` | with you gone they see **Claim** and it works; with you still in it there is no Claim at all and the panel tells them to ask you for **Hand it over…** |
| 141 | The staff half | `/voice` as a Lead | adds the whole status block that `/tempvoice status` used to print, then **Setup · Forget a lobby… · Turn join-to-create off · Logs**, a **A channel…** picker of every open temp channel, and **Open on the site**. **Logs** answers a NEW message and the panel stays. A Lead WITHOUT the Member role still gets all of that, and is told why there is no card of their own |
| 142 | Setup, forgetting a lobby, and the mode | **Setup** → a name; then **Forget a lobby…** → the lobby; then **Turn join-to-create off** and re-join the lobby; then leave the panel `voice_panel_minutes` (10) minutes | Setup says **repaired / took it over** (never a second lobby); forgetting removes it from the list and joining it makes nothing; with the mode off joining makes no channel and existing ones still work; then every control greys out and the footer reads *This panel has gone quiet — run /voice again*. A lobby Black Bloc is NOT keeping track of is named in the status block with what to do about it — it is not offered on **Forget a lobby…**, because forgetting an id it never stored would do nothing |
| 143 | Staff reassigning somebody's channel | as a Lead: **A channel…** → somebody else's channel → **Hand it over…** → pick a third member | the row's owner moves, the new owner gets the channel's controls, and the displaced owner is DM'd one line naming who has it now. Staff always get the final say on a stored decision; the member's own **Hand it over…** sends no DM, because they are the person affected |

## Chat — `/chat` is one command that opens a panel (rows C1–C8)

Written 2026-09-04 by the chat panel build (wave 3). ⚠️ **The numbers are placeholders.**
Two wave-3 builds were writing rows at the same time and the merge order was not fixed, so
the conductor assigns the real numbers at landing; `C1`–`C8` are deliberately not digits so
a half-renumbered table cannot look finished. Rows **33, 34, 35, 36** and **37** above were
rewritten IN PLACE for this build rather than added — every one of them told you to run a
subcommand that no longer exists. ⚠️ **None of this has been run against Discord** — no
panel opened, no note written, no model called; everything below is what the code and its
tests say should happen. `/chat` is staff-only and, while `TEST_MODE` stands, must be run
in `#mute-me-bot-test-spam`.

| Row | What | Do this | Expect |
|---|---|---|---|
| C1 | The panel itself | `/chat` in `#mute-me-bot-test-spam` as a Lead | ONE ephemeral panel: the mode and tier lines, the turns and money, the notes count, then **Personality… · Knowledge… · Settings**, the two mode toggles, and **Logs · Refresh · Open on the site**. A line points at `/memory` for what the bot remembers about a person — a line, never a button. Nothing anywhere says `/chat status`, `/chat knowledge`, `/chat personality` or `/chat settings` |
| C2 | The spend block is the only thing the admin key hides | the same as a staffer who is NOT an administrator, `chat_status_admin_only` on (the default) | the whole panel opens — **Knowledge…** and **Personality…** included — and the turns-and-money lines are replaced by one sentence saying what they are and who may read them. Set the key off (Settings page or `/settings set-value`) and re-open: the two lines appear |
| C3 | The voice and the pool | **Personality…** → **The voice…** → `noir`; then **Turn a mood off…** → `peppy`; then **Turn a mood on…** → `peppy` | the voice line changes and says it applies from the next answer on; the mood moves from one select to the other; ONE `chat.personality_mode` row and one `chat.trope_disabled` / `chat.trope_enabled` row each, all `via: discord`. With `chat_llm_mode` off the card also says nothing is using the voice yet |
| C4 | The pool cannot be emptied, and the panel says so | with the voice set to `noir`: **Personality…** → **Turn a mood off…** | `noir` is **not on the select at all**, and the card carries a line saying which moods are held back and how to free them (move the voice first). The website already refused this; both doors now refuse it identically, from one function |
| C5 | Writing a note down, and editing it | **Knowledge…** → **Write one down…** → title/body/tag; then **A note…** → pick it → **Edit…** and change the body | the note is saved and named by number, one `chat.knowledge_added` row; the card shows it whole with **Remove** and **Edit…**; the edit modal arrives **prefilled**, saves in place keeping the same number, and leaves one `chat.knowledge_edited` row |
| C6 | A note the bot wrote itself | **A note…** → pick a `server` row (there are none until the daily read has run once) | the card shows it, has **neither** Remove nor Edit, and says the daily read owns it — change the channel, role or event it describes instead |
| C7 | Removing, and finding | **Remove** → **Yes, remove it**; then **Find…** with a word from a note | the confirm is asked first and **Keep it** puts the card back untouched; a yes removes it and the list re-renders without it, one `chat.knowledge_removed` row. **Find…** filters the list and says so, and leaves NO log row — it is a read. Past 25 notes the picker's placeholder says how many of how many and points at the Chat page |
| C8 | The numbers, the modes, and the panel timing out | **Settings** → read the list → **Limits…** → change the cap and the minutes; then **Back**, the two mode toggles, `@Black Bloc hello`, then leave the panel `chat_panel_minutes` minutes | Settings lists every `chat_*` key with its value and names `/memory` as the home of the memory ones; **Limits…** arrives prefilled with all five numbers and one bad field refuses the whole modal by name and saves NOTHING; each mode flip is ONE click and leaves ONE `chat.mode` row — with answering off the bot says nothing at all; then every control greys out and the footer reads *This panel has gone quiet — run /chat again* |

## The owner's Twitch Team form — the walk-through

This is the form Phase 19 was built for (Pawpette's request, 2026-09-02). Nothing
about the Team is in the code: it is all data you create, and you can make a second
form the same way for anything else staff hand out.

⚠️ **The twitch.tv Team invite has no API.** Black Bloc owns the form, the review, the
role and the DMs; a human still clicks *invite* on twitch.tv. That click is what the
`owner` + `next_step` fields exist to name — see `KNOWN_ISSUES.md`.

**In Discord** — one command, `/apply`, and every step has a dashboard twin on
/rolemenus.html → Applications:

1. `/apply` → **Settings** → the **Mode…** picker → **on**.
2. **Back** → **New form**: name `twitch-team`, heading `Twitch Team`, and a line
   under it. You land on the new form's card.
3. On that card, **Edit…** → the **Role it hands over…** picker → `@Twitch Team`;
   the **Where its cards wait…** picker if they should not go to the staff channel;
   the **Who decides it…** picker if somebody other than staff decides them; the
   **Who is nudged next…** picker for the Team owner. ⚠️ **Submitting a picker with
   nothing chosen CLEARS it** — that is how a form goes back to keeping a list.
4. **Words…** on the same sub-panel: the heading, the line under it, **what happens
   after a yes** (`the Team owner sends your twitch.tv invite — accept it from your
   Twitch notifications`) and what an approved applicant is DM'd. **Numbers…** takes
   the days the role lasts (0 = forever) and the wait before somebody may apply again.
5. **Back** → **Questions…** → **Add…**, five times, in this order — Twitch handle
   (hint `twitch.tv/…`), How long have you been streaming, What is your usual
   schedule, What do you stream, Why the Team (`long`, required `no`). Picking one on
   the select gives you **Edit** and **Remove**. ⚠️ **Reordering is site-only** and the
   sub-panel says so — Discord has nothing to drag with.
6. **Back** → **Post the Apply button** → pick the channel. Press it again to move it.
7. Check it: **A form…** for the forms, **Pick an application…** for the queue,
   **Find #…** for a settled one by number, and **Logs**.

**To close it for a while** (applications in progress are untouched): `/apply` →
**A form…** → **Close it**. **Open it** puts it back.

## When something fails
Take a screenshot, note the time, and paste it to Claude with the row number — the Fly logs around that
minute plus the dashboard Logs page are enough to diagnose. Nothing here is destructive; the worst case is
a `would_*` line in the log where you expected a post (that is test mode doing its job).
