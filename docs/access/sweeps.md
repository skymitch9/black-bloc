# Owner sweeps — what is shipped but never exercised by a person

> **Audience:** the owner. **Status:** TRACKED (owner, 2026-08-31 — permanently, not temporarily). Last verified:
> **2026-09-05** — rows **252–261** at the FOOT added by the SELF-TEST build (wave 5; written as
> `ST1`–`ST10`, numbered at the merge, shipped as **v86**; schema 30 → 31); before them rows
> **245–251** added by the MODMAIL follow-up (the ticket card ON the
> panel; written as `ML1`–`ML7`, numbered at the merge, shipped as **v85**); before them rows
> **231–244** added by the SETTINGS PANEL build (231–242 written as
> `S1`–`S12` by **Build 2** on `worktree-agent-a56c7b5137d9a609d`, 243–244 as `SB1`–`SB2` by Build 1;
> numbered at the merge, after 230; shipped as **v83** (Build 1) and **v84** (Build 2)).
> `/settings` becomes ONE command that opens a panel; `show` / `set` / `set-role` / `set-value` /
> `clear` and the whole `/presence` group retire, and the top-level count is **30 → 29 with ZERO
> `app_commands.Group`s left** — measured through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, not predicted.
> ⚠️ **Eighteen numbered rows above were rewritten IN PLACE** — 16, 53, 65, 67, 68, 71, 83, 95,
> 103, 108, 130, 156, 174, 184, 185, 186, 197, 199 — plus the Phase 1, Phase 2, Phase 5 and chat
> memory prose, because every one of them told the owner to run a subcommand that no longer
> exists. Row **16** also named a **`/settings logs` that had never existed** (design §J defect
> 2); after this build the button it names is real. ⚠️ **Nothing in 231–244 has met live
> Discord by a person** — the verification is `pytest` (5002), `ruff check`, `node site/mock/check.mjs`
> (17 pages, 146 routes, unchanged) and the v84 boot (`synced 29`).
> Before it, same day — rows **219–230** added by the MODMAIL PANEL build
> **Build B** (written as `MB1`–`MB12` on `worktree-agent-a4bebd98196e3ca14`, numbered at the merge; shipped as **v82**).
> Build B adds the sticky ticket card, `modmail_reply_style`, the practice ticket, and retires
> `/areply` `/note` `/close` — top-level **33 → 30 on `main`, measured** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`. Schema **29 → 30**
> (`modmail_tickets` gains `card_message_id` and `practice`), and the migration was RUN against
> a database built by `main`'s own `db.py` at `6e5a550`, not reasoned about. The block is
> lettered on purpose and numbered at the merge. ⚠️ **Nothing in 219–230 has
> met live Discord** — no boot, no card posted, no practice thread made; the whole verification
> is `pytest` (4738), `ruff check` and `node site/mock/check.mjs` (17 pages, 146 routes,
> unchanged). The **Phase 7** block below was rewritten IN PLACE again, because it still told the
> owner to run `/areply`, `/note` and `/close`. Before that, same day —
> rows **208–218** added by the MOD CASES PANEL build (`/mod [member]` becomes
> ONE staff-only command that opens a panel; `/case`, `/cases` and the `mod` group with its `logs`
> child are all retired, and a case can now be edited, noted, voided and restored from either
> Discord or the dashboard). ⚠️ **This supersedes the "UNCHANGED at 36" line below**: the
> top-level count really does move — **36 → 34 on the branch, 35 → 33 on `main`** (modmail A had already taken one), **measured** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`. Schema **28 → 29**
> (`mod_cases` gains six nullable columns), and the migration was RUN against a database built by
> the code at `97531cc`, not reasoned about. The build wrote its block as `C1`–`C11`, letters
> on purpose, and the conductor numbered them **208–218** at the merge, after modmail A's 200–207. ⚠️ **Nothing in 208–218 has met live
> Discord** — no boot, no panel opened, no DM seen; the whole verification is `pytest` (4600),
> `ruff check` and `node site/mock/check.mjs` (17 pages, 146 routes). The **Phase 6 appendix**
> block was rewritten IN PLACE, because it told the owner to run `/cases` and `/case`.
> Before that, same day —
> rows **200–207** added by the MODMAIL PANEL build (Build A: `/modmail`
> becomes ONE staff-only command that opens a panel; the whole `modmail` group and the whole
> `snippet` group are retired, so the top-level count moves — **36 → 35, measured** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`). The build wrote its block
> as `MA1`–`MA8`, letters on purpose, and the conductor numbered them **200–207** at the merge, after
> the honeypot's 188–199. The **Phase 7** block above was rewritten IN PLACE for it rather than added to. ⚠️ **`/reply`
> `/areply` `/note` `/close` are untouched** by Build A. ⚠️ **Nothing in 200–207 has met live
> Discord** — no panel opened, no snippet saved, no member blocked; the whole verification is
> `pytest` (4571) and `ruff check`. Before that, same day —
> rows **188–199** added by the HONEYPOT PANEL build (`/honeypot` becomes ONE
> staff-only command that opens a panel; the `honeypot` and `exempt` groups and all seven leaf
> subcommands are retired, and the top-level count is **UNCHANGED at 36, measured** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` — a group was already
> one slot). The build wrote its block as `H1`–`H12`, letters on purpose, and the conductor
> numbered them **188–199** at the merge, after hide-when-off's 183–187. The **Phase 3 appendix** honeypot lines were rewritten IN PLACE
> rather than added to. ⚠️ **Nothing in 188–199 has met live Discord** — no boot, no sync, no
> panel opened, no trap created; the whole verification is `pytest` (4593) and `ruff check`.
> Same day —
> rows **183–187** added by the HIDE COMMANDS WHEN OFF build (a feature whose
> mode reads `off` has its one top-level command removed from the guild's tree; fourteen features
> — every mode key with an `off` except `chat_memory_mode`, whose `/memory` stays (fork I-M1) —
> one new bool key `hide_commands_when_off` defaulting **true**). ⚠️ The top-level count in
> `tests/test_bot.py` is UNCHANGED at **36** — hiding happens at guild-sync time, not in the tree
> that test counts, so `commands synced` in the live log is what moves. ⚠️ **Nothing in 183–187
> has met live Discord** — no boot, no sync, no command seen to disappear from a client; the
> whole verification is `pytest` (4539) and `ruff check`. Rows **53, 108, 130** and **174** were
> rewritten IN PLACE for it rather than added to — each of them said in words that a particular
> command does NOT vanish when its mode is off, which is now true only for the ≤60 s sync lag.
> Before that, same week —
> rows **173–182** added by the ROLE MENUS PANEL build (`/rolemenu` becomes ONE
> staff-only command that opens a panel; BOTH the `rolemenu` and `role` groups and all eighteen
> leaf subcommands are retired, so the top-level count really does move — **38 → 37, measured**
> through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`). ⚠️ The build
> wrote its block as `M1`–`M10`, letters on purpose — a half-renumbered table cannot look
> finished — and the conductor numbered them **173–182** at the merge, after raidtrain's
> 163–172. Rows **1, 19, 22, 23, 38, 53, 72** and the **Phase 1 and Phase 3 appendix scripts**
> were rewritten IN PLACE for it rather than added to. ⚠️ **Nothing in 173–182 has met live
> Discord** — no panel opened, no menu posted, no role handed over, no request decided. Same day —
> rows **163–172** added by the RAID-TRAIN PANEL build (`/raidtrain` becomes ONE
> member-visible command that opens a panel; **both** groups go — `/raidtrain`'s twelve
> subcommands and the whole `/raidtrains` staff group — so the top-level count drops by one,
> **38 → 37, measured** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, since this build has
> no token to boot with). Rows **48–52** were rewritten IN PLACE for it rather than added.
> ⚠️ **Nothing in 163–172 has met live Discord** — no panel opened, no hour claimed, no DM sent
> — and **no raid train has ever run at all**: `raidtrain_mode` is still `off`, so row 163 is
> where a sweep of this feature starts. Same day —
> rows **155–162** added by the CHAT PANEL build (`/chat` becomes ONE
> staff-only command that opens a panel; the `chat` group's eight subcommands are retired and
> the top-level count does **NOT** move — **38 → 38, measured** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`). Rows **33–37**
> were rewritten IN PLACE for it. The branch wrote the block as `C1`–`C8` and the conductor
> numbered it at the merge, after automod's 144–154. ⚠️ **Nothing in 155–162 has met live
> Discord** — no panel opened, no note written, no model called. Same day —
> rows **144–154** added by the AUTOMOD PANEL build (`/automod` becomes ONE
> staff-only command that opens a panel; the `automod`, `rule` and `exempt` groups and all
> eight leaf subcommands are retired, and the top-level count does **NOT** move — **38 → 38,
> measured** through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`,
> since a group already counted as one slot). The **Phase 6 appendix block** below was
> rewritten IN PLACE for it rather than added to. ⚠️ **Nothing in 144–154 has met live
> Discord** — no panel opened, no rule changed, no mode flipped; and while the test guard is
> installed `on` behaves like `shadow`, so row 152 proves the control and row 154 proves the
> enforcement path is unchanged. Before that,
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
| 1 | Role approval (Phase 9) | Dashboard → Role menus → Edit `runner-status` → Approval on, Expires after 7, Retry after 7, Channel → Save; post it; pick the role as a member | ephemeral "Sent to staff…"; a card with Approve/Deny in the staff (or set) channel; Approve → DM + role; Members chip shows "· 7 d"; Timed roles section lists it; `/rolemenu` ▸ **Grants…** ▸ the grant ▸ **Push it back…** moves it and **End it now** removes it |
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
| 16 | Via column | change one setting from Discord (`/settings` ▸ **A setting group…** ▸ any key) and one from the website | Logs page → Settings audit shows **Discord** and **Website** in the Via column; `/settings` ▸ **Logs** says the same. ⚠️ **This row used to name `/settings logs`, which never existed** — the button is real from 2026-09-05 |
| 17 | Cyberpunk look | cog → Cyberpunk | the estate's cyan/yellow palette again (no magenta) — say if it still reads wrong |
| 18 | `/help` (batch 2) | `/help`, then `/help filter:temp` | command list with `(staff)` marks on staff-only entries |
| 19 | Round-1 fixes | `/rolemenu` (the root panel lists every menu — `showall` was retired 2026-09-04); `/golive` → **Link my Twitch channel**; `/voice` → **Setup** | the panel lists every menu with its option count, mode and posted state (ephemeral); the modal says **channel**, never *login*; Setup says **repaired / took it over** (never a second lobby), lobby named "join to create a channel", Member + staff can connect |
| 20 | Temp-voice memory (batch 4) | in your temp channel: `/voice` → **People…** → *Let someone in…*, *Keep someone out…*; **Region…** → `us-west`; leave (channel deletes) → re-join the lobby | the new channel has the same region and the same two people set; the panel's **remembered for next time** block shows both halves; **Forget my settings** clears it |
| 21 | Temp-voice room controls (B4, live 2026-08-31) | with a temp channel open: https://blackbloc.heygabi.ai/tempvoice.html → Open now | each row shows In it / Cap / Access + Rename, Cap, Lock, Hide buttons; press Rename — the channel renames and the reply says "remembered for next time" |
| 22 | Role-menu Un-post + Seed (B5+B6, live 2026-08-31) | /rolemenus.html → Un-post beside Post on a posted card; the Seed defaults button beside New menu; also `/rolemenu` ▸ the menu ▸ **Take it down** in Discord | un-post takes the panel down in the channel (in test mode: a `would_unpost` log line instead); seed says created/left-alone in words and never rewrites an existing menu |
| 23 | Staff assign from the site (B7, live 2026-08-31) | /rolemenus.html → Timed roles → "Hand roles out": pick a member, a menu, roles → Give these | the member's roles change (⚠️ REAL roles even in test mode, same as `/rolemenu` ▸ the menu ▸ **Hand roles out…**); the Logs page shows `web.role_menu.assign` with Via: Website |
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
| 38 | Ping roles — set-up (F14, `pings_mode` ships **off**) | `/pings` as staff → **Set up the Events role** → leave the role picker empty → **Set it up**; then **Settings** → **Mode…** → on; `/rolemenu` ▸ *notifications* ▸ **Post it** | the reply names the role it made or reused and says both feeds now point at it, plus "still off" until you flip the mode; a **Notifications** panel with one 🔔 option; **Turn event pings on** as a member puts the role on. Rows **126–134** walk the whole panel |
| 39 | Ping roles — a streamer's own role | as a linked streamer: `/pings` → **Start my own ping role**; as staff for somebody else: `/pings` → **Streamers…** → **Give somebody a ping role…**; then **Follow a streamer…** from a second account | the role is made (named from `pings_fan_role_template`), a **Streamer pings** menu appears, following puts it on and the panel names both halves. ⚠️ If Discord refuses, the reply says the Bots role has to sit ABOVE the new role and **Logs** has `pings.forbidden` |
| 40 | Ping roles — the announcement prefix | with `golive_mode` on (or shadow, and read the `would_announce` line) and a fan role on the streamer: go live | the line starts `<@&Events> <@&… pings>` — both roles, never twice, the shared one first; end the stream with `golive_end_mode edit` and the edit adds the suffix without adding a mention |
| 41 | Ping roles — 26 streamers (paging) | only if you ever have more than 25: `/pings` → **Streamers…** | there are TWO panels, `streamers` and `streamers-2`; post the second one too. The member's **Follow a streamer…** select caps at 25 and says *"25 of N — the rest are on the *Streamer pings* panels"*, NOT "on the site" — a member cannot open the site. ⚠️ Never exercised in the server; the 25-per-select cap is Discord's documented limit, tested with 26 rows in the suite |
| 42 | Ping roles — the dashboard | Dashboard → Go-live → Pings | the table shows every streamer, their role, a follower count (or a dash when the role was deleted by hand), who started it; Remove asks first; "Create for a streamer" makes one; the Logs section under it is `pings.*` only |
| 43 | YouTube uploads — link (F3, `youtube_mode` ships **off**) | `/youtube` → **Link my channel**, paste your channel address (the `youtube.com/channel/UC…` one; an `@handle` works too) | the reply names the channel, says how many videos were counted as history, and says out loud that announcements are **off** until a Lead changes **Announcements are…** on the same panel. The panel then shows the five status lines. ⚠️ Nothing already published is ever announced — that is what the count is for |
| 44 | YouTube uploads — an actual upload | staff: `/youtube` → **Announcements are…** → **shadow**. Publish something on the linked channel, then wait and press **Logs** | within ~25 minutes a `youtube.would_announce` line carrying the rendered text (**KI-13** explains the two delays). Set the same picker to **on** and repeat for a real post in the test channel |
| 45 | YouTube uploads — Shorts and live streams | publish a Short; separately, start a YouTube live stream | the Short is skipped with `youtube.skipped reason=short` (turn `youtube_announce_shorts` on and the next one posts); a live stream is skipped only while Discord shows you live on YouTube — see **KI-11**, that is the gap `YOUTUBE_API_KEY` would close |
| 46 | YouTube uploads — the dashboard | Dashboard → Go-live → **YouTube uploads** | the sweep card says running with a last-good time; the links table shows who is linked and whether their feed has answered yet; Recent uploads colours each row announced / would / skipped; Unlink asks first; **Upload settings** and **Upload logs** sit under it |
| 47 | YouTube uploads — the staff paths | `/youtube` as staff → **Setup** (pick a channel and a ping role), **Back** → **Link for somebody…** → pick a member → paste their channel | the panel's own embed is the old `/uploads list` header — the mode, the channel, the sweep health, **api key — not set (feed only)** and who is linked; Setup names where posts will go; linking for somebody counts their history the same way. Rows **118–125** walk the whole panel |
| 48 | Raid trains — build one (F19, `raidtrain_mode` ships **off**) | `/raidtrain` → **Mode…** → **on** (or Events page → Raid train settings), then **Start a raid train** — title, what it is, `2026-09-14 19:30`, 60, 4 | the form is read in YOUR stored zone (set it with **My time zone** on `/event`; `/timezone` was retired 2026-09-03); the reply names where the lineup went and the panel lands back on the root with the new train on **A train…**; in the test channel a lineup post appears with four `open` rows and a thread under it. ⚠️ In TEST_MODE the post only lands if `raidtrain_channel_id` is the test channel — otherwise **Logs** has one `raidtrain.post_skipped_test_mode` line and nothing is posted |
| 49 | Raid trains — claim, release, the cap | `/raidtrain` → **A train…**, then **Take an hour…** → `#1`; re-open the card and try a second hour; **Back** → **My slots…**; back on the card, **Give back slot #1** | the first claim takes slot **#1** and the lineup post EDITS itself (no second message); after it, *Take an hour…* is **gone** because the cap is reached, and the refusal on the website names `raidtrain_max_slots_per_member`; **My slots…** shows the hour in your own clock; giving it back opens it again. From an account with no linked Twitch channel there is **no** *Take an hour…* at all and the card carries a line pointing at `/golive` → **Link my Twitch channel** |
| 50 | Raid trains — the reminder DM | claim a slot that starts **inside the next 30 minutes** (make a train starting ~35 min out), then wait one sweep (5 min) | ⚠️ **a DM, not a channel post** — it names your slot time, who raids INTO you and who you raid NEXT, with their twitch.tv links, plus a jump link to the lineup. Exactly once, ever. `/raidtrain` ▸ **Logs** has one `raidtrain.remind`; in `shadow` it is `raidtrain.would_remind` and no DM |
| 51 | Raid trains — the train moves | with a train running (`live`) and `raidtrain_live_posts` on: have a slot holder actually go live on Twitch | within one sweep the slot gets a ✅ on the lineup and a line lands in the train's thread: "**login** is live — next up **login** at …". ⚠️ It sees only what go-live sees — a hidden presence with no Twitch link is never noticed (**KI-16**). On the card neither **Lock the lineup** nor **Open it for sign-ups** is there at all while a train is `live` |
| 52 | Raid trains — the organizer half and the dashboard | on the card: **Put somebody in…**, **Take somebody off…**, **Change two slots round…**, **Lock the lineup**, **Call it off…**; then https://blackbloc.heygabi.ai/events.html#sect-raidtrains | assign ignores the per-member cap; swap moves the PEOPLE and never the times; locking refuses further claims and the button then reads **Open it for sign-ups**; **Call it off…** takes the reason in a modal — typing it IS the confirmation — and DMs every holder. On the page: the trains table, Open → the slot grid with Put somebody in / Take off, "Change two slots round", Lock/Cancel, **Raid train settings** (14 keys) and **Raid train logs** below it |
| 35 | Personality + the cap drill (Phase 14) | `/chat` → **Personality…** → **The voice…** → `noir` → @-mention again; then **Back** → **Settings** → **Limits…** and set the monthly cap to 0 → @-mention → set it back to 20; dashboard: /chat.html Knowledge/Personality/Spend sections | the noir answer is clipped but complete; at cap 0 you get an ordinary line with **no mention of money or limits** and one `chat.llm_capped` in `/chat` ▸ **Logs**; the Spend meter names why each quiet tier is quiet. One `chat.settings` row per **Limits…** save, never five |

## Detailed phase scripts (1–8a) — moved whole from `TODO.md` 2026-08-31

The step-by-step click scripts for the seven core phases + 8a, as accumulated
while each landed. Rows 1–20 above are the priority order; these are the long
form for a full pass.

- **Phase 1 (live; rewritten 2026-09-04 for the panel — every subcommand below is
  gone):** in `#mute-me-bot-test-spam` run `/settings` (expect the root panel, and the three core keys
  with the test channel as their default under **Roles & channels…**) → `/rolemenu` → **Seed the defaults** → **Yes, make
  them** (the root list is what `/rolemenu list` printed) → **A menu…** → `pronouns`
  → **Post it** → the test channel; pick roles on the posted panel (expect an
  ephemeral "Added: …/Removed: …" and your roles change) → **Back** → **A menu…**
  → `interests` (the card is what `/rolemenu show` printed). Try `/rolemenu` from a
  non-staff account: expect the staff sentence and NO panel. Check the action-log embeds
  landed in the same channel.
- **Phase 2 (live, mode `shadow`; ONE command since 2026-09-03):** `/golive` as staff —
  the embed carries the status lines (expect mode shadow, channel = test channel, Twitch
  polling running with a last-ok time) → **Preview an announcement…** → *Twitch*
  (ephemeral preview, no ping, nothing posted) → **Link my Twitch channel** and type your
  channel (expect "Linked" or "could not be reached to check") → go live on Twitch once
  with Discord showing the Streaming status: expect a `golive.would_announce` embed in
  the test channel within seconds (presence) — and nothing in `#live-now`. Stop
  streaming: expect `golive.end` ~2 min later. Try **Stop announcing my streams** then
  **Announce my streams again**. `/settings` ▸ **A setting group…** ▸ golive now lists the golive keys.
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
  Then `/honeypot` → **Setup…**
  (trap created in the test category; notice skipped in test mode) → post in it from
  a throwaway account: message deleted, a `honeypot.would_ban` embed with a **Ban
  now** button in the test channel; nobody banned. `/honeypot` again for what
  `/honeypot status` used to print (expect the resolved staff-role count > 0), and
  the mode picker for what `/honeypot mode` used to set. Role rider: `/rolemenu` → **Seed the defaults** again
  (expect "already there" for the five, created `runner-status`) → **A menu…** →
  `runner-status` → **Hand roles out…** → pick a member → **Give them roles…** → the
  staff picker → **A menu…** → `event-alerts` → **Post it** shows the real
  `:JoyGAMING:` emoji only if you delete and re-seed that menu (the seed never
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
- **Phase 7 (live, `modmail_enabled` false; rewritten 2026-09-05 AGAIN for Build B — every
  `/modmail …`, `/snippet …`, `/areply`, `/note` and `/close` this block used to name is
  gone):** `/modmail` is ONE command that opens a panel carrying the whole status block
  (resolved staff, loop health, the open tickets) → **Setup…** → **Answer DMs on** → from a
  second account DM the bot: expect a ticket channel `<username>` INSIDE the test category,
  the header card + your DM relayed into the test channel (guarded send), ✅ on the DM →
  ⚠️ **the ticket's sticky card appears in the test channel, not in the ticket** — that is
  `speak`'s redirect under test mode and it is expected → press **Reply**, **Reply as
  Staff**, **Private note** and **Close…** on that card; `/reply ticket:<n> hello` still
  works typed. Try **Snippets…** → **Add one…** and **Blocked…** → **Block someone…**.
  Then **Setup…** → **Answer DMs off** again so the incumbent keeps the real tickets.
  ⚠️ `/reply` is the only typed modmail command left.
- **Phase 6 (live, automod `shadow`):** `/automod` — ONE panel carrying everything
  `/automod status` used to print (mode shadow, resolved staff, rules: mention_spam armed,
  others log-only) → from a second account post 5 @mentions within 30 s in the test
  channel: expect ONE `automod.would_*` case card with an **Apply now** button (nothing
  deleted/timed out), and a following "sorry" message does NOT re-fire → `/warn @second
  reason` (allowed) → `/timeout @second 5m x` (expect the test-mode refusal +
  `mod.would_timeout`) → `/mod @second` (ONE panel, narrowed to them), then **A case…** → the
  card, then **Back** → `/settings` (one panel, not six messages).
  Arming is not offered-and-refused any more: **on** is simply NOT on the *What automod
  does…* picker while the staff channel is still the test channel, and the panel says so
  in words.
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
| 53 | Applications — the switch, and the command that does NOT vanish | /rolemenus.html → **Applications** → set it to **shadow**, then **on**, then back to **off**; or `/settings` ▸ **A setting group…** ▸ applications ▸ `applications_mode` | the segment saves in place and says so. ⚠️ **With it off `/apply` is STILL in Discord** (owner, 2026-09-03: "Visible") — open it and the panel says *"Applications are turned off right now…"* in words and offers **no** form to apply for, while staff still get **A form…**, **New form**, **Settings** and **Logs**. The posted Apply buttons stop working. ⚠️ **Rewritten 2026-09-04, and the "STILL in Discord" half is now only true for about a minute**: the hide-commands-when-off build (rows 183–187) puts `applications_mode` back in the table, so once the tree syncs `/apply` is gone from the list and the words-in-the-panel behaviour above is what you see during the lag. `/rolemenu` is the same. To get either back: `/settings` ▸ **Turn a feature back on…** — `/settings` can never be hidden. To stop the hiding for every feature at once, `hide_commands_when_off` → `false`, and then this row reads exactly as it did on 2026-09-03 |
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
| 65 | Requests — giving members their list back | `/settings` ▸ **A setting group…** ▸ request ▸ `request_panel_own_list` → **Turn it on**, then `/request` as a non-staff member who has filed something | the member's own requests are summarised on the panel again (and "You have not asked for anything yet" when they have none) — exactly row 15's old behaviour. Set it back to `false` and the lines go away again; the Settings page has the same switch |
| 66 | Requests — Ask them to check (sixth pass) | `/request` as staff, open a request that is **ready to check**, press **Ask them to check** | the person who filed it gets a DM titled *"Request #N is ready for you to try 🙌"* with what was built, how to test it, who marked it ready and a line asking them to try it and say how it went; the card you are looking at re-renders with a new **Asked to check · @you · just now** field and stays **ready to check** (it does NOT move); the ephemeral reply says they were asked by DM; one `request.check_asked` line on the Requests log. The same button is on the review card at https://blackbloc.heygabi.ai/requests.html, between Accept and Send back, with an *asked by … · just now* chip beside the status |
| 67 | Requests — the ping when their DMs are closed | turn Discord DMs off for the account that filed the request (Privacy Settings → allow DMs from server members: off), then press **Ask them to check** again | the DM fails, so the card is posted in the request channel with a **real @mention** of the person who asked — the only place the requests bot ever pings anybody; the reply says their DMs are closed and they were pinged instead; the log carries a `request.dm_failed` line as well as `request.check_asked`. Then `/settings` ▸ **A setting group…** ▸ request ▸ `request_check_fallback_channel` → off and press it again: nothing is posted, and the reply names the key a Lead turns back on |
| 68 | Requests — asking automatically at ready | `/settings` ▸ **A setting group…** ▸ request ▸ `request_check_on_ready` → on, then take a request that is **being worked on** and press **Ready to check** | the DM from row 66 arrives with no second button press, and the log shows `request.review` followed by `request.check_asked`; set it back to `false` and the next Ready-to-check tells nobody. Both switches are on the Settings page too |

### Applications, no-role pass — a form that keeps a LIST. Live in v62; rows 69–72 rewritten for the `/apply` panel (v66).

| # | What | Do this | Expect |
|---|---|---|---|
| 69 | A form with no role at all | on **https://blackbloc.heygabi.ai/rolemenus.html#applications** press **New form**, fill Name + Heading, leave **Role it hands over** on **No role — keep a list**, save. (In Discord: `/apply` → **New form**, then on its card **Edit…** and leave the role picker alone) | the form saves; the **Role lasts, days** box disappears while the role is blank; the forms table shows a grey **list** badge in the Role column instead of a role chip. An existing form is switched over by submitting **Edit…**'s role picker EMPTY, or by picking the blank option in the editor |
| 70 | Applying and being approved with nothing to hand over | put the Apply button up, apply as a member, press **Approve** on the card | the card and the ephemeral reply say "Approved — **<name>** is on the **<heading>** list now." — no role is mentioned and none is given. The DM is the form's approved text with no "the role runs out" line. `/apply` → **Logs** shows `application.approved` with `granted: null` and NO `application.granted` line |
| 71 | The roster, and Copy as text | on the Role menus page open **Approved for <form>** under that form; in Discord, `/apply` → **A form…** → **Roster** | one row per approved member: their name, **twitch.tv/<login>** as a link (or a quiet "not linked"), how long since staff said yes, and who decided. Somebody who has left the server is still listed with "left the server" beside them — `/settings` ▸ **A setting group…** ▸ applications ▸ `applications_roster_shows_left` → off hides them instead, on both surfaces. **Copy as text** (site only) puts one line per member on the clipboard |
| 72 | Taking somebody off the list | on the roster press **Take off the list**, type a reason, confirm. (In Discord: `/apply` → **A form…** → **Roster** → **Take somebody off…**, or **Find #…** the application and press **Take off the list** on its card) | they are DMed the reason and when they may apply again; the Decided table shows the row as **removed**; the roster is one shorter. On a form that DOES hand a role over the button is not offered at all and the card says so in words, pointing at `/rolemenu` ▸ **Grants…** ▸ the grant ▸ **End it now** |
| 80 | Polls — the panel opens | `/poll` in #mute-me-bot-test-spam, first as a Lead and then as a plain member | ONE ephemeral panel, not a list of subcommands: **Create · Find #… · Refresh** on the top row for everybody, **Settings · Logs** added for a Lead only; a "Pick a poll…" select under it once something is running; a Lead also sees the counts line (**N** running · **N** waiting on a decision · **N** repeating) and, with a repeating poll saved, a second "Repeating polls…" select; **Open on the site** links to https://blackbloc.heygabi.ai/polls.html. A member sees no Settings and no Logs at all rather than buttons that refuse |
| 81 | Polls — Create through the two-step modal | on the panel press **Create**: type the question, `Pizza \| Tacos \| Neither`, leave hours blank, pick a kind on the radio, tick nothing; submit; on the preview pick a channel, a ping role, flip **Thread: off**; press **Post it** | the modal carries exactly five things (question, options, hours, the kind radio, the two switches) — Discord's cap; the preview is a card of what you typed with **Post it · Repeat… · Start over · Cancel**, and NOTHING is written until Post it (press **Cancel** on a preview and `/poll` shows no new poll). After Post it: the poll is up in the channel you picked, and `/poll` → **Logs** shows one `poll.created` and one `poll.opened` — never two of either |
| 82 | Polls — a date poll through the extra step | **Create** with kind **date**, no options; on the preview press **Date slots…**, start `2026-09-05`, 4 slots, step 1, unit **days**; **Post it** | before the slots are given there is no **Post it** button at all and the preview says the poll needs its slots; after them, four dated answers in the order you asked for. `poll_date_labels` still decides whether they read as `Sat 05 Sep` or as each reader's own clock |
| 83 | Polls — pick one and End it | with a poll running, `/poll` → pick it on the select → **End** | picking IS the results: the card is the same results embed `/poll results` used to print. **End** shows for the person who started it and for staff; the poll closes, the result posts in the channel, and the card re-renders with no moves left ("nothing moves a closed poll now"). As a bystander the card has only **Back** — the move is not drawn rather than refused. `/settings` ▸ **A setting group…** ▸ poll ▸ `poll_creator_may_end` → off and the author loses End too; staff keep it |
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
| 95 | Applying from the picker | **Apply for…** → **Twitch Team** | the same modal `/apply start` used to open, unchanged; on submit the same "Sent to staff" reply, the same DM, and the same Approve/Deny card in the test channel. Then `/settings` ▸ **A setting group…** ▸ applications ▸ `applications_panel_own_list` → off and open `/apply` again: your own applications are no longer written out, and the **Take one back…** picker is still there |
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
| 103 | A session's read shows up in your log | mint `OPERATOR_READ_TOKEN` (one command, `access/operator-read.md`) and deploy; ask the session to run `.\scripts\read.ps1 -Path /api/requests`; then open the **Logs** page (or `/settings` ▸ **Logs**) | one new line, `web.operator.read`, whose **Via** column reads **Operator token** rather than Discord or Website, with `path=/api/requests` in its details. One line per read, not one per route. Nothing is posted to Discord (it is a routine Core kind, so `core_log_level` at its default stays quiet). If you would rather see nothing at all, turn **Whether an operator-token read leaves a log line** (`operator_read_log`) off on the Settings page and read again — same data, no line. Ask the session to try a CHANGE and it is refused in words: *the operator token can only look, never change* |

## Chat memory — `/memory` is ONE command that opens a panel

Built 2026-09-03 (`info/memory-panel-design.md`, wave 2). ⚠️ **`chat_memory_mode` ships
`off` and nothing is written down until a Lead turns it on**, so rows 104–107 need
`/settings` ▸ **A setting group…** ▸ chat ▸ `chat_memory_mode` → on first AND a conversation or two with
Black Bloc, because the profile is only written on the hourly sweep. Everything here is
ephemeral and visible to nobody but you — there is no staff row on this panel by design
(`chat_memory_staff_view` and the Chat page are the staff surface).

| # | What | Do this | Expect |
|---|---|---|---|
| 104 | The panel | `/memory` in `#mute-me-bot-test-spam` after a conversation or two | ONE ephemeral panel titled *What Black Bloc remembers about you*, the line "Nobody else can read this.", your lines NUMBERED `#1 #2 #3` (one learned in a DM marked *(learned in a DM — never used in a channel)*), a **Forget one of these…** picker whose options carry the same numbers, and the row **Forget everything · Stop remembering me · Refresh**. **No** Logs, **no** Open on the site, nothing staff-shaped — a member following a site link would meet a 403, so there is no link |
| 105 | Dropping one line | **Forget one of these…** → pick `#2` | the panel re-renders in place with that line gone and the rest renumbered; the reply says *Dropped **1** line(s)*. Open the **Chat** log (dashboard Logs page, or `/chat logs`): ONE `chat.memory_forgot` row, details `who_asked: self · lines: 1 · via: discord`, and **no trace of what the line said** — the text of a note never reaches the action log |
| 106 | Forgetting the lot, and changing your mind | **Forget everything** → **Keep it**; then **Forget everything** → **Yes, forget it all** | Keep it changes nothing and puts you back on the panel with every line still there and no new log row. Yes clears it: the panel re-renders saying Black Bloc has not written anything down about you yet, the picker is gone, and only **Stop remembering me · Refresh** are left. One `chat.memory_forgot` row |
| 107 | Stopping it, and starting again | **Stop remembering me** → **Yes, stop**; then **Remember me again** | the first wipes AND opts you out in that order — one `chat.memory_optout` row — and the panel then offers **Remember me again · Refresh** only. The second brings the writing back with one `chat.memory_optin` row. ⚠️ Neither one asks staff for anything: this is your own data and the panel never refuses you |
| 108 | Memory switched off, and the quiet footer | leave the panel alone for `memory_panel_minutes` (10) minutes; then `/settings` ▸ **A setting group…** ▸ chat ▸ `chat_memory_mode` → off and run `/memory` again | after ten minutes every control on the old panel is greyed out and the embed footer reads *This panel has gone quiet — run /memory again*. With the mode off `/memory` ⚠️ **STAYS in the command list** — the one feature the hide-commands-when-off build (rows 183–187) leaves out, because fork I-M1 (owner, 2026-09-03 16:12, "open it") stands: turning memory off does not delete profiles and the site is staff-only and counts-only, so the panel is a MEMBER's only door to their own notes (KI-14). It opens, says Black Bloc is not remembering anybody here as a LINE, whatever it already stored is still listed, and **Forget everything** and the picker still work |

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
| 129 | Your own ping role | as a linked streamer press **Start my own ping role**, then **Take my ping role away** → **Keep it**, then again → **Yes, take it away** | the role is made and appears on the **Streamer pings** panel; Keep it changes nothing and writes no log row; Yes removes it and the panel loses it. ⚠️ It renders even when `pings_fan_role_creation` is `staff` (owner fork I1 = keep today's behaviour): taking a role off yourself is never gated on who was allowed to put it on  ⚠️ **Since v86 it also renders with `pings_mode` OFF** (owner 2026-09-05 14:35: "a for pings") — switch pings off and the button is still there for anyone who holds a role; **Start my own ping role** is not|
| 130 | With `pings_mode` **off** | `/pings` as a member who follows somebody, within the first few seconds of the flip | the panel still opens and says ping roles are **off**, offers **no** Follow control and **no** toggles — but **Stop following…** is still there and still takes the role off. That asymmetry is deliberate: an access-REDUCING move fails safe and needs no feature switch. ⚠️ **Rewritten 2026-09-04: wait a minute and `/pings` is GONE from the command list** (rows 183–187), so that panel is only reachable during the sync lag. `/settings` ▸ **Turn a feature back on…** brings it back |
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

## The automod panel — rows 144–154

Written 2026-09-04 by the automod panel build. ⚠️ **None of it has been run against
Discord** — no panel opened, no rule changed, no mode flipped; everything below is what the
code and its tests say should happen. Eight leaf subcommands over ONE top-level slot became
ONE `/automod`, so the top-level count does **NOT** move — **38 → 38, measured** through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, not a boot. The
Phase 6 appendix block above was rewritten IN PLACE for this build rather than added to.
⚠️ **Run every row in `#mute-me-bot-test-spam`.** While the guard is installed the engine
only ever sees that channel, and **`on` behaves like `shadow`** — nothing is punished,
everything is logged. So row 152 proves the CONTROL works and proves nothing about
enforcement; row 154 is the row that proves enforcement did not change.

| # | What | Do this | Expect |
|---|---|---|---|
| 144 | The panel is the whole status block | `/automod` as a Lead in `#mute-me-bot-test-spam` | ONE ephemeral panel titled *What automod is watching*: mode, resolved staff, what the member is told, warn threshold, modlog, both exemption lists, the acted-on/logged-only counts, then every rule on its own line — over **A rule… · What automod does… · Exemptions… · Settings… · Refresh · Logs · Open on the site**. Nothing anywhere says `/automod status` or `/automod rule` |
| 145 | Arming is not offered while it would be refused | look at **What automod does…** while `staff_channel_id` is still the test channel | it offers **off** and **shadow** and **NOT on**, and the panel says in words that the staff channel is still the test channel and what to set instead. Arming is not offered-and-refused; it is not offered |
| 146 | A rule card | **A rule…** → `mention_spam` | its card: **Turn it off · Change the numbers… · Log only · Back**, a *What it does…* picker with delete, warn and timeout already ticked, and a line saying it counts everything one member does in 30 seconds. **No Words…** — that button is `bad_words`' alone |
| 147 | A refused number saves nothing at all | **Change the numbers…** → type `abc` in the seconds box, leave the other two | one sentence saying `window_s` takes a whole number — and **nothing is saved**: re-open the card and all three numbers are what they were, including the two that parsed. Then try `4000` in the same box: one sentence naming the 0–3600 range, again nothing saved |
| 148 | The toggle says what it will do | **Turn it off**, then **Back** → **A rule…** → `mention_spam` | the button now reads **Turn it on** — never both — and the line above it agrees, because both read the same rule object. **Log only** is gone once the rule has no actions left |
| 149 | The word list, one per line | **A rule…** → `bad_words` → **Words…** | the box arrives prefilled with the words there are; typing a list ONE PER LINE saves them all (not one long word), and so does a comma list. More than 200 is refused in words, and a list too long for the box says to use the dashboard instead of quietly truncating |
| 150 | Caps asks for a percent | **A rule…** → `caps` → **Change the numbers…** | the threshold box is labelled **Percent capitals, 1–100**, not a count — and `200` is refused naming the 1–100 range |
| 151 | Exemptions, both kinds on one removal select | **Exemptions…** → *Stop watching a role…*, then *Stop watching a channel…*, then *Watch it again…* | each add says what happened and the lists above update; the removal select carries the role AND the channel with the right word each; a second add of the same thing says it was already exempt and changes nothing. The honeypot channels are named as also-never-read and are **not** on the removal select — the honeypot owns them |
| 152 | Arming asks a second time, going quieter does not | **What automod does…** → **on** (with a real staff channel set), then **Keep it in shadow**; then → **shadow**, then → **off** | **on** re-renders the panel with *Are you sure?* and **Yes, arm it / Keep it in shadow**; keeping it changes nothing and leaves no log row. Every other move is ONE press and leaves ONE `automod.mode` row. ⚠️ Arming here proves the CONTROL only: while the guard is installed `on` still punishes nobody |
| 153 | Settings, and the quiet footer | **Settings…** → **Stop asking before arming** (it flips to *Ask before arming*), → **Numbers…** → `0` then `25`; then leave the panel `automod_panel_minutes` minutes | the toggle flips and leaves ONE `automod.settings` row; `0` is refused in words and `25` saves. The warn threshold and what a punished member is told are LINES here with a sentence saying they live on the dashboard's Moderation page — no control, because they belong to `/warn` too. Then every control greys out and the footer reads *This panel has gone quiet — run /automod again* |
| 154 | Nothing about enforcement changed | post five @mentions from a second account in the test channel | ⚠️ unchanged from before this build: ONE `automod.would_*` case card with **Apply now**, nothing deleted, and a following "sorry" does not re-fire. **This is the most important row in the set** — it is the proof the panel changed only how automod is configured |
## Chat — `/chat` is one command that opens a panel (rows 155–162)

Written 2026-09-04 by the chat panel build (wave 3) as `C1`–`C8` — two wave-3 builds were
writing rows at the same time and the merge order was not fixed, so the branch used letters
and the conductor numbered them **155–162** at the merge (automod landed first and took
144–154). Rows **33, 34, 35, 36** and **37** above were
rewritten IN PLACE for this build rather than added — every one of them told you to run a
subcommand that no longer exists. ⚠️ **None of this has been run against Discord** — no
panel opened, no note written, no model called; everything below is what the code and its
tests say should happen. `/chat` is staff-only and, while `TEST_MODE` stands, must be run
in `#mute-me-bot-test-spam`.

| Row | What | Do this | Expect |
|---|---|---|---|
| 155 | The panel itself | `/chat` in `#mute-me-bot-test-spam` as a Lead | ONE ephemeral panel: the mode and tier lines, the turns and money, the notes count, then **Personality… · Knowledge… · Settings**, the two mode toggles, and **Logs · Refresh · Open on the site**. A line points at `/memory` for what the bot remembers about a person — a line, never a button. Nothing anywhere says `/chat status`, `/chat knowledge`, `/chat personality` or `/chat settings` |
| 156 | The spend block is the only thing the admin key hides | the same as a staffer who is NOT an administrator, `chat_status_admin_only` on (the default) | the whole panel opens — **Knowledge…** and **Personality…** included — and the turns-and-money lines are replaced by one sentence saying what they are and who may read them. Set the key off (Settings page, or `/settings` ▸ **A setting group…** ▸ chat) and re-open: the two lines appear |
| 157 | The voice and the pool | **Personality…** → **The voice…** → `noir`; then **Turn a mood off…** → `peppy`; then **Turn a mood on…** → `peppy` | the voice line changes and says it applies from the next answer on; the mood moves from one select to the other; ONE `chat.personality_mode` row and one `chat.trope_disabled` / `chat.trope_enabled` row each, all `via: discord`. With `chat_llm_mode` off the card also says nothing is using the voice yet |
| 158 | The pool cannot be emptied, and the panel says so | with the voice set to `noir`: **Personality…** → **Turn a mood off…** | `noir` is **not on the select at all**, and the card carries a line saying which moods are held back and how to free them (move the voice first). The website already refused this; both doors now refuse it identically, from one function |
| 159 | Writing a note down, and editing it | **Knowledge…** → **Write one down…** → title/body/tag; then **A note…** → pick it → **Edit…** and change the body | the note is saved and named by number, one `chat.knowledge_added` row; the card shows it whole with **Remove** and **Edit…**; the edit modal arrives **prefilled**, saves in place keeping the same number, and leaves one `chat.knowledge_edited` row |
| 160 | A note the bot wrote itself | **A note…** → pick a `server` row (there are none until the daily read has run once) | the card shows it, has **neither** Remove nor Edit, and says the daily read owns it — change the channel, role or event it describes instead |
| 161 | Removing, and finding | **Remove** → **Yes, remove it**; then **Find…** with a word from a note | the confirm is asked first and **Keep it** puts the card back untouched; a yes removes it and the list re-renders without it, one `chat.knowledge_removed` row. **Find…** filters the list and says so, and leaves NO log row — it is a read. Past 25 notes the picker's placeholder says how many of how many and points at the Chat page |
| 162 | The numbers, the modes, and the panel timing out | **Settings** → read the list → **Limits…** → change the cap and the minutes; then **Back**, the two mode toggles, `@Black Bloc hello`, then leave the panel `chat_panel_minutes` minutes | Settings lists every `chat_*` key with its value and names `/memory` as the home of the memory ones; **Limits…** arrives prefilled with all five numbers and one bad field refuses the whole modal by name and saves NOTHING; each mode flip is ONE click and leaves ONE `chat.mode` row — with answering off the bot says nothing at all; then every control greys out and the footer reads *This panel has gone quiet — run /chat again* |

## Raid trains — `/raidtrain` is one command that opens a panel (rows 163–172)

Written 2026-09-04 by the raid-train panel build (wave 3). **Both** groups go: `/raidtrain`'s
twelve subcommands and the whole `/raidtrains` staff group, so the top-level count drops by
one — **38 → 37, measured** through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, since this build has
no token to boot with. Rows **48–52** above were rewritten IN PLACE for it rather than added
— every one of them told you to run a subcommand that no longer exists. ⚠️ **None of this has
been run against Discord** — no panel opened, no hour claimed, no DM sent; and **no raid train
has ever run at all** (`raidtrain_mode` is still `off`). Everything below is what the code and
its tests say should happen. `/raidtrain` is **member-visible** and, while `TEST_MODE` stands,
must be run in `#mute-me-bot-test-spam`.

| Row | What | Do this | Expect |
|---|---|---|---|
| 163 | The panel with raid trains **off** | `/raidtrain` as an ordinary member, then as a Lead | the member gets ONE ephemeral panel saying raid trains are **off** and nothing new can be started, with **Refresh** and nothing else; the Lead gets the same line PLUS the sweep block, **Mode…**, **Setup…**, **Logs** and **Open on the site**. **Mode… → on** turns the feature on from the panel — the only door left now that `/raidtrains mode` is gone. Nothing anywhere says `/raidtrains` |
| 164 | Setting it up, and clearing one key again | **Setup…** → a channel, an organizer role, a ping role → **Save**; then **Clear…** → **The ping role** | ONE `raidtrain.setup` line for the save (not three), the three lines above it update, and clearing empties exactly one key and leaves the other two alone. ⚠️ **Clear… only lists the keys that are actually set**, so it disappears entirely once all three are empty. Nothing says `/raidtrains setup` |
| 165 | Starting a train | **Start a raid train** → title, blank description, `2026-09-20 19:30`, `60`, `4` | the five-field form is read in YOUR stored zone; the lineup post appears in the test channel with four `open` rows and a thread under it; the panel lands back on the root with the new train on **A train…**. A bad number refuses the whole form by name and writes nothing. ⚠️ In TEST_MODE the post only lands if `raidtrain_channel_id` IS the test channel — otherwise **Logs** has one `raidtrain.post_skipped_test_mode` line |
| 166 | The card, with no Twitch link | **A train…** → the train, from an account with no linked Twitch channel | the lineup exactly as the post shows it, **no** *Take an hour…* select at all, and a field pointing at `/golive` ▸ **Link my Twitch channel** — never a greyed button |
| 167 | Taking an hour, and the cap | link Twitch, re-open the card, **Take an hour…** → `#1`; then look for a second hour | the claim edits the lineup post **in place** (no second message) and answers with the slot time; on the next render *Take an hour…* is **gone**, because `raidtrain_max_slots_per_member` is reached, and **Give back slot #1** is there instead. Two people picking the same hour: the second is refused in words and nothing is overwritten |
| 168 | Giving an hour back, one and many | **Give back slot #1**; then set `raidtrain_max_slots_per_member` to 0, take two hours, and look at the card | with one hour held the button reads its number; with two it becomes **Give an hour back…** and opens a select of both. ⚠️ The two **never appear together**, and picking one goes straight back to the card |
| 169 | The organizer half | as an organizer: **Put somebody in…** → an hour + a member → **Put them in**; then **Take somebody off…** | assign ignores the per-member cap; **Put them in** with only half the picks says which half is missing and writes nothing; somebody with no Twitch link is refused in words naming `/golive`; the off-select lists only the hours that are **taken**, so "already empty" is unreachable. Both edit the lineup post |
| 170 | Swapping, and locking | **Change two slots round…** → `#1` then `#3`; then **Lock the lineup**, then re-open the card | the second select never offers the first pick; the swap moves the PEOPLE and never the times; after locking the button reads **Open it for sign-ups** — never both — and every claim control is gone. On a `live` train neither button is there at all |
| 171 | Calling it off | **Call it off…** → type a reason | typing the reason IS the confirmation — there is no second Yes/No — and a blank one is refused by Discord itself. Every slot holder is DMed the reason, the post says cancelled, and the card afterwards offers **Back** and **Refresh** and nothing else |
| 172 | **My slots…**, **Logs**, and the panel timing out | hold hours on two trains → **My slots…** → pick one; then **Logs** as a Lead; then leave the panel `raidtrain_panel_minutes` (10) minutes | **My slots…** lists the hours in your own clock across every train and picking one opens that train's card; **Logs** answers a NEW message and the panel stays; then every control greys out and the footer reads *This panel has gone quiet — run /raidtrain again*. ⚠️ On the website, cancelling a train from the Events page now writes **`web.raidtrain.cancel`, Via = Website** — before this build it said `raidtrain.cancel`, Via = Discord |

## The owner's Twitch Team form — the walk-through

✅ **Exercised by a person 2026-09-05 13:42** — the owner: "she did a test and approved it": Pawpette ran the
form and approved it. Rows 53–57 are the first rows of the applications feature a person has run; this walk-through
is kept as the reference for the next form.

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

### Role menus panel (wave 3) — rows 173–182

Written as `M1`–`M10` on the build's branch (letters on purpose, so a half-renumbered table could
not look finished) and numbered **173–182** by the conductor at the merge, after raidtrain's 163–172.

| # | Do this | Expect |
|---|---|---|
| 173 | `/rolemenu` on a server that has menus | one ephemeral panel: the menu list as lines (name, option count, mode, posted or not), **A menu…**, **New menu**, **Seed the defaults**, **Grants…**, the mode button, **Logs**, **Refresh** — and nothing that asks you to type a menu name anywhere |
| 174 | press the mode button (**Turn role menus off**), then run `/rolemenu` again straight away — within the first few seconds | the posted panels come down, and while the tree is still catching up the panel opens and says picking is off in a line, with **Post it** / **Hand roles out…** gone from every menu card while **Words…**, **Rules…**, **Delete it** and the rest stay. ⚠️ **Rewritten 2026-09-04: wait a minute and `/rolemenu` is GONE from the command list** — the 2026-09-03 "the command is still there" answer is reversed by the hide-commands-when-off build (rows 183–187). To get it back: `/settings` ▸ **Turn a feature back on…**, which works because `/settings` can never be hidden |
| 175 | mode back on → **A menu…** → `pronouns` | the card: **Add a role…** · a **Take a role off this menu…** select · **Words…** · **Rules…** · **Ask staff first** · **Post it** · **Hand roles out…** · **Delete it** · **Back** · **Refresh** — and the lines above are exactly what `/rolemenu show` used to print |
| 176 | **Back** → **A menu…** → `runner-status` (a `staff`-mode menu) | **no Post it at all** — the card says in words that nobody gives themselves these roles, and **Hand roles out…** is how they are handed over |
| 177 | **Add a role…** → pick a role that sits ABOVE Black Bloc in Server Settings → Roles → **Use the role's own name** | refused **in words** naming the fix, and nothing is added. Then pick a real one and press **Give it a label…** for a label and an emoji; the **Take a role off this menu…** select takes it back off and says nobody loses the role they have |
| 178 | on `pronouns`: **Post it** → the test channel; then **Move it…** → the same channel; then **Take it down** | one panel, moved not duplicated (it edits the message it already has); taking it down leaves the menu and everybody's roles alone and **Post it** comes back on the card. ⚠️ Any channel but `#mute-me-bot-test-spam` is refused in words while test mode is on |
| 179 | **Rules…** → 7 days, retry 7; then **Ask staff first**; then pick the role as a member on the posted panel | the posted panel refreshes ITSELF (fork F-R3) so its "Before you pick" block says both things without you posting again; picking sends a request and DMs you; a card with Approve / Deny appears in the approval channel (⚠️ in the test channel while test mode is on, and the reply says so) |
| 180 | `/rolemenu` → **Waiting on staff (1)…** → the request → **Approve for a while…** → 3 | the same card the channel shows; approving DMs the member, adds the role and edits the channel card — and pressing **Approve** on the channel card afterwards says it was already decided rather than acting twice |
| 181 | `/rolemenu` → **Grants…** | ⚠️ **an AUDIT, not an empty box** — every timed role running in the server, soonest to end first, one line each: member · role · time left · the end date (or `no end date`), capped at 25 with a line pointing at the site's Timed roles table. Then **Whose roles?** → that member: the same list narrowed to them, and **A timed role…** picks from what is shown |
| 182 | on that grant: **Push it back…** 3, then **End it now** → **Yes, take it back**; then **Back** → **Give somebody a role…** → a member, a role, **How long for…** 0; then leave the panel `rolemenu_panel_minutes` minutes | the end date moves; ending takes the role back, DMs nobody (it is a staff move) and the Timed roles table on the site agrees — ⚠️ **this is the `/role revoke` four docs promised**; a 0-day grant lands with **no end date** at all (fork F-R2) and still writes its `role_grants` row; the panel goes quiet with its footer. ⚠️ Handing roles out and ending grants change REAL roles, test mode or not |

### Hide commands when off — rows 183–187

The 2026-09-04 ask: *"if we turn a feature off on the web portal … make the `/youtube` command not
appear until it turns back on"*. Fourteen features do this now, not just YouTube; `/memory` is
the one deliberate exception (it is a member's only door to their own notes, KI-14). ⚠️ **Discord takes
up to a minute** — the bot waits 5 s for you to stop clicking and syncs at most once a minute — and
your own client may need a `Ctrl+R` to redraw the list. ⚠️ **`shadow` is not `off`**: only the word
`off` takes a command away. ⚠️ **`/settings` can never be hidden**, so there is always a way back.

| # | Do this | Expect |
|---|---|---|
| 183 | dashboard → **Settings** → `youtube_mode` → **off**. Wait a minute, then `Ctrl+R` in Discord and type `/` | **`/youtube` is gone from the list.** Nothing else moved — `/golive`, `/poll` and the rest are where they were |
| 184 | `/help` with nothing in the filter | the last line reads *"N command(s) are not listed because their feature is turned off"* and names both ways back — the dashboard's Settings page, or `/settings` ▸ **Turn a feature back on…**. ⚠️ Run `/help filter:ping` and that line is **not** there (a filtered list is short on purpose) |
| 185 | `/settings` ▸ **A setting group…** → youtube → `youtube_mode` → **shadow**. Wait a minute, `Ctrl+R` | **`/youtube` is back**, because shadow is not off. Set it to `on` and it stays. This is the trap worth checking by eye — your posture for YouTube is `shadow` today, so nothing was hidden until you chose `off` |
| 186 | turn two or three features off (`poll_mode`, `birthday_mode`, `tempvoice_mode`), wait a minute, then `/settings` ▸ **Panels & commands…** → **Leave every command showing**. Wait a minute, `Ctrl+R` | **every command is back at once** — `/poll`, `/birthday`, `/voice` — while the three features stay off, and opening one says in words that it is off. `/help` stops saying anything about missing commands. Set it back to `true` and they vanish again |
| 187 | dashboard → **Logs** → filter `commands.visibility`, after doing 183 and 186 | **one row per sync, not one per command** — each naming how many commands are in the guild, which are `hidden` and which were `shown` again, and whether Discord or the website set it off. ⚠️ A burst of changes inside a minute leaves ONE row, which is correct |

### The honeypot panel — rows 188–199

Written as `H1`–`H12` on the build's branch (letters on purpose, so a half-renumbered table could
not look finished) and numbered **188–199** by the conductor at the merge. `/honeypot` is now ONE
staff-only command that opens a panel; `/honeypot status`, `/honeypot setup`, `/honeypot mode`,
`/honeypot forget`, `/honeypot exempt add|remove` and `/honeypot logs` are all **gone**
(2026-09-05). ⚠️ **Nothing below has met live Discord** — no boot, no sync, no panel opened.
⚠️ Every row runs in `#mute-me-bot-test-spam`; while test mode is on the trap is created inside
that channel's category, its pinned notice is not posted, and **nobody is ever banned**, so a row
that flips the mode to `on` proves the CONTROL works and proves nothing about enforcement.

| # | Do this | Expect |
|---|---|---|
| 188 | `/honeypot` as a Lead in `#mute-me-bot-test-spam` | ONE ephemeral panel: the whole block `/honeypot status` used to print — mode, resolved staff roles by name, trap channels, purge days, exempt roles, and the banned/shadow/failed/ignored tally — over **What the trap does… · Roles the trap ignores… · Setup… · Settings… · Refresh · Logs · Open on the site**. Nothing says `/honeypot status`, `/honeypot setup` or `/honeypot exempt` anywhere. ⚠️ One line says test mode contains the trap and nobody will be banned |
| 189 | look at the mode picker while at least one staff role resolves | it offers **off · shadow · on**, with the current one already ticked. Then point `staff_channel_id` at a channel no role can see and re-open: it offers **off** and **shadow** and **NOT on**, and the panel says in words that no staff role resolves and what to set. Arming is not offered-and-refused; it is not offered |
| 190 | **Setup…** → leave the name box as it arrives → submit | the trap is created **inside the test channel's category**, the reply names it and says the notice was not posted because of test mode, and the panel's **trap channels** line now names it. Re-open `/honeypot`: **Setup… is gone** — a second trap is not offered rather than offered-and-refused |
| 191 | **Setup…** again after typing a name of 101 characters | ⚠️ it cannot be typed: the box stops at 100. This is the bound the `name` parameter used to carry |
| 192 | post in the trap from a throwaway account, in `shadow` | ⚠️ unchanged from today: the message is deleted, a `honeypot.would_ban` card with a **Ban now** button appears in the test channel, nobody is banned, and a second post from the same account inside 10 minutes gets no second button. **This row is the proof the panel changed nothing about catching** and it is the most important row in the set |
| 193 | **Roles the trap ignores…** → pick two roles | the reply names what changed, the **exempt roles** line above lists both, and the log holds exactly ONE `honeypot.exempt_set` row naming both. Open the picker again: **both are already ticked** |
| 194 | **Roles the trap ignores…** → untick one and submit | the reply says which was removed and ONE more row is logged. Submitting again with no change says nothing changed and writes **no** row at all |
| 195 | press **Exempt nobody** | the list empties, ONE row is logged, and the button disappears because there is nothing left to clear. ⚠️ If your client refuses to submit an EMPTY picker, this button is the reversal path — that is why it exists (fork F-H1) |
| 196 | delete the trap channel in Server Settings, then `/honeypot` | the id is already forgotten (the channel-delete listener, unchanged) and **Setup…** is back. Then add a stale id by hand from the site's Settings page and re-open: the panel names it as *a channel Discord no longer has* and **Forget…** → the picker removes it with no id typed anywhere |
| 197 | **Settings…** → **Numbers…** → purge days `9`, then `3` | `9` is refused in one sentence naming the 7-day ceiling and **nothing is saved** — not even the panel-minutes box that parsed; `3` saves both and leaves ONE `honeypot.settings` row. The card also names `/settings` ▸ **A setting group…** ▸ honeypot as the way back when the mode is off |
| 198 | **Logs**; then leave the panel `honeypot_panel_minutes` (10) minutes | Logs answers a **NEW** ephemeral message and the panel stays where it is; after the wait the panel greys out with the *this panel has gone quiet* footer |
| 199 | turn `honeypot_mode` to `off` on the dashboard, wait ~60 s, then look for `/honeypot` | ⚠️ **the command is gone** — that is the hide-commands-when-off behaviour doing its job, and honeypot keeps it deliberately because the mode ships `shadow`, so `off` is a real "I do not want this" choice. `/settings` ▸ **A setting group…** ▸ honeypot ▸ `honeypot_mode` → **shadow**, or the portal, brings it back within ~60 s |

### Modmail — `/modmail` is one command that opens a panel (rows 200–207)

Written as `MA1`–`MA8` on the build's branch (letters on purpose — two wave-4 builds were written
side by side, and a half-renumbered table cannot look finished) and numbered **200–207** by the
conductor at the merge.

`/modmail` is now ONE staff-only command that opens a panel. The whole `modmail` group (logs,
block, unblock, blocked, mode, forget, status, settings) and the whole `snippet` group (add,
remove, list) are **gone**, so the top-level command count really moves — **36 → 35, measured**
through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`. ⚠️ **`/reply`,
`/areply`, `/note` and `/close` were UNTOUCHED** by this build; **Build B retires three of them
into the ticket card — see rows 219–230 below.** ⚠️ **`/modmail` can never be hidden** by `hide_commands_when_off`
— `modmail_mode` is `channel`/`thread` with no `off`, and the switch is the bool
`modmail_enabled` — so it is in the list whatever the posture, which is right, because the panel
is the Discord door to turning modmail on. `modmail_panel_minutes` (10) decides how long the
panel stays live.

| # | Do this | Expect |
|---|---|---|
| 200 | `/modmail` with `modmail_enabled` **false** | ONE ephemeral panel: everything `/modmail status` used to print (answering DMs, mode, the three places, resolved staff, how many are blocked, the reconciler's last ok/last error, the open tickets or "No ticket is open"), then a line saying the old ModMail bot still holds the inbox. Buttons: **Setup… · Blocked… · Snippets… · Forget… · Logs · Refresh · Open on the site** |
| 201 | **Setup…** → **Transcripts…** → pick the test channel; then **Mode…** → `thread`; then **Answer DMs on** | each re-renders the same card in place with the new value on it. The mode reply says the tickets already open keep the mode they were opened in. Dashboard → **Logs**: **one `modmail.settings` row per change**, and — this is the point — **no second `web.modmail.*` row** beside it |
| 202 | **Setup…** again | the button now reads **Answer DMs off**, never both spellings at once. Press it and modmail is back where it was |
| 203 | **Snippets…** → **Add one…** (name `ban-appeal`, some text) → **Add one…** again with the SAME name → then pick it and **Change it…** | the first saves; the second is refused **in words naming Change it…** (there is no `overwrite:true` any more); **Change it…** opens the modal already filled in and replaces the text. ⚠️ `/reply snippet:ban-appeal` still sends it — that is the one typed command this build keeps |
| 204 | **Snippets…** → pick one → **Remove it** → **Keep it**; then **Remove it** → **Yes, remove it** | **Keep it** changes nothing and leaves no log row; **Yes, remove it** removes it and leaves ONE `modmail.snippet_removed` row |
| 205 | **Blocked…** → **Block someone…** → pick yourself → **Block them…** → a reason; then **Refresh**, pick yourself from **Somebody…** → **Unblock them** | both land. Dashboard → **Logs**: **ONE line each**, not two — `modmail.blocked` then `modmail.unblocked`, and both read as **important**. ⚠️ Block yourself twice and the second says *"was already blocked, so nothing changed"* and writes **no** second row |
| 206 | Block somebody from the **dashboard's Modmail page**, then unblock them there | the Logs page shows `web.modmail.blocked` and `web.modmail.unblocked` — **one row each**, where before this build the website wrote a `web.modmail.block` line on top of nothing at all from Discord. Same for a website snippet save (`web.modmail.snippet_saved`) and a website reply (`web.modmail.reply`) |
| 207 | **Forget…** → clear the ticket category → **Forget…** again | the select only ever lists the places that are actually pointed, and once nothing is pointed the **Forget…** button is not drawn at all. Leave the panel `modmail_panel_minutes` minutes and it goes quiet with its footer, every button disabled |

### `/mod` — one panel over the case record, and the four corrections (rows 208–218)

`/mod [member]` is now ONE staff-only command that opens a panel. ⚠️ **`/case`, `/cases` and
`/mod logs` are gone** — the list, the card and the logs are all controls on it. The seven bare
actions (`/warn`, `/timeout`, `/untimeout`, `/kick`, `/ban`, `/unban`, `/purge`) are unchanged and
the panel's footer says so. ⚠️ **Voiding a case does not undo the punishment** — a voided ban is
still a ban — and the card says that in a sentence. ⚠️ Under test mode the void DM goes (a DM is
allowed) but the modlog card is NOT rewritten while the modlog is not the test channel; that is
`edit_case_card`'s existing behaviour, not a fault of this build. Written as `C1`–`C11` on the build's branch
(letters on purpose) and numbered **208–218** by the conductor at the merge.

| # | Do this | Expect |
|---|---|---|
| 208 | `/mod` as a Lead in `#mute-me-bot-test-spam` | ONE ephemeral panel titled *What Black Bloc has done*: the newest ten cases as the lines `/cases` used to print, newest first, *page 1 of N*, over **A case… · Whose cases? · Jump to case #… · Refresh · Logs · Open on the site**. The footer names the seven bare actions. Nothing anywhere says `/case` or `/cases` |
| 209 | `Older ›`, then `‹ Newer` | the page changes in place and the header's page number agrees. `‹ Newer` is simply **not there** on page 1 and `Older ›` is not there on the last — not there and refusing |
| 210 | `Whose cases?` → a member with cases, then **Everyone's cases** | the list narrows and the first line reads *"**N** case(s) for @them — page 1 of M"*; **Everyone's cases** appears only while the filter is on and takes it back off |
| 211 | `/mod @somebody-with-no-cases` | *"Black Bloc has no cases for @them yet"* over **Everyone's cases** and nothing else — no empty select, no dead page buttons |
| 212 | `A case…` → a warn | the card `/case` used to show — kind, member, moderator, when, reason — over **Edit reason… · Add a note… · Void this case… · Back · Refresh**, and a line saying voiding does not undo anything |
| 213 | `Edit reason…` — the box arrives holding the current reason. Clear it and submit; then reopen it and type a real one | the empty one is refused in one sentence and **nothing is saved** (reopen the card: the old reason is still there, and the Logs have no new row); the real one saves, leaves ONE `case.reason_edited` line, and the card in the modlog is rewritten to match |
| 214 | `Add a note…`, then look at the card again | the button now reads **Edit the note…** — never both — the note is a *Note* field on the card, and the Logs carry one `case.noted`. Reopening it shows the note you wrote |
| 215 | `Void this case…` → a reason → submit | the member is DM'd (or not, per `mod_dm_on_action`) that a case was cancelled and that it undoes nothing; the card shows **Voided** with who, when and why; the Logs carry ONE `case.voided`; **the timeout or ban is still in force**. Press **Back**: the line is struck through and the select says `voided`. Now open a SECOND `/mod` panel from before the void and press **Void this case…** there: it says somebody just voided it and does nothing twice |
| 216 | On the voided case: **Restore this case** | the strike-through goes, the card is back to C5's five buttons — no state is terminal — the member is DM'd that it was put back, and the Logs carry `case.restored`. ⚠️ Also check `/warn` on that member: a voided warn no longer counts toward `automod_warn_threshold` |
| 217 | `Jump to case #…` → `99999`; then a case number from another server; then `abc`; then leave the panel `mod_panel_minutes` (10) minutes | each answers in a NEW message — *"Black Bloc has no case **#99999**"*, the same for the other server's, and *"**abc** is not a case number"* — with the panel untouched behind it. After ten minutes every control greys out and the footer reads *this panel has gone quiet — run /mod again* |
| 218 | dashboard → **Moderation** → a case row → the drawer | the four moves are there beside **Apply now**: a **Reason** box with **Save the reason**, a **Note** box with **Add the note**, and **Void this case** behind a confirm that spells out what voiding does not do. Void one: the row's reason is struck through with a red **voided** pill, and the Logs page shows `web.case.voided` — ONE row, not two. **Restore this case** takes it back off |

### Modmail Build B — the sticky card, the reply style and the practice ticket (rows 219–230)

Written as `MB1`–`MB12` on `worktree-agent-a4bebd98196e3ca14` (letters on purpose) and numbered
**219–230** by the conductor at the merge, after `/mod`'s 208–218. Merged and deployed as **v82** on 2026-09-05.

Every open ticket now carries **one card at the bottom** with **Reply · Reply as Staff · Private
note · Close…**, and it jumps back under the newest message on every write. ⚠️ **`/areply`,
`/note` and `/close` are GONE** — they are those buttons — so the top-level count moves
**33 → 30, measured**. `/reply` stays, and keeps its optional `ticket:`. Schema **29 → 30**:
⚠️ **migrate before deploy.** New setting **`modmail_reply_style`** (`buttons` / `typing` /
`both`, default `both`) decides whether a plain message typed in a ticket still reaches the
member — and **223 is the reason the practice ticket exists: it is how that choice is made
without a real member and a real DM.**

⚠️ **Read this before 229 or it will look like a bug:** in a REAL ticket under test mode the
card appears in **`#mute-me-bot-test-spam`**, not in the ticket channel, because `speak`
redirects every guarded send there. In the **practice** thread it appears where you would expect,
because that one thread is claimed with `own_channel`. That difference is the whole point of the
practice ticket.

| # | Do this | Expect |
|---|---|---|
| 219 | `/modmail` | the panel from rows 200–207 **plus** a new **Try a fake ticket** button on the first row. With no staff role resolving it is absent, and the embed says why |
| 220 | **Try a fake ticket** | it asks first: *"Black Bloc makes a private thread for you… nobody is DMed"* over **Yes, open one · No**. **No** opens nothing at all |
| 221 | **Yes, open one** | a **private thread on the test channel** appears with the header card, a line saying it is practice, and under it the staff card: **Reply · Reply as Staff · Private note · Close… · Speak as the member · End the practice** |
| 222 | **Speak as the member** → "hello?" three times quickly | the message appears each time and the card **moves to the bottom once**, not three times (2-second debounce, 8-second floor). ⚠️ The old card is deleted, so the thread has exactly one. ⚠️ **This row is the only measurement of the debounce there has ever been** — `CARD_DEBOUNCE_SECONDS` (2.0) and `CARD_MIN_GAP_SECONDS` (8.0) were reasoned from Discord's documented per-channel buckets and have never met a real channel: time on a stopwatch **how many seconds pass between your last "hello?" and the card reappearing at the bottom**, write that number here, and say whether the card ever double-posted or the bot visibly stalled; a gap much over 2 s (or any second card) is the signal to change the constants |
| 223 | **Reply** → type text; **Reply** again → pick the snippet AND add a line; then **Reply as Staff** | all three land in the thread as *Sent to the member* embeds; the anonymous one says **Staff** and carries no role colour; the snippet one reads *snippet, blank line, your words* — byte-identical to `/reply text: snippet:`. ⚠️ **No DM reaches anybody and there is NO `modmail.dm_failed`** — it is practice, and a suppressed DM is not a failed one |
| 224 | **Private note** → some text | a *Private note* embed in the thread, **one** `modmail.note` row in the Logs (`/note` never wrote one at all), and no DM |
| 225 | `/modmail` → **Setup…** | a new **Reply style…** button and a **reply style — both** line. Pick **typing**; the reply says *"anything staff type in a ticket goes to the member"*. In the practice thread type `hello` as yourself, then `=this is private`: the plain line relays as a *Sent to the member* embed with a ✅, the `=` line does not and gets 📝 |
| 226 | now set **Reply style… → buttons** and type in the thread again | ⚠️ **nothing at all happens** — no relay, no ✅, no row. `=note` still becomes a note, and the card's **Reply** and `/reply` still work. This is the choice the setting is for; `both` puts it back |
| 227 | `/reply text:hi` typed in the test channel | unchanged: it finds the only open ticket, or `ticket:<n>` names one. It is the **only typed modmail command left** |
| 228 | **End the practice** | the transcript `.txt` **and** the summary land in the transcripts channel marked **PRACTICE** — title *Practice ticket #N closed*, file `modmail-practice-ticket-N.txt`, first line of the file says PRACTICE — the thread is archived and locked, the card is gone, and you are **not** DM'd |
| 229 | Turn `modmail_enabled` on, DM the bot from a second account, then press **Close…** on the card with a reason | a real ticket channel in the test category; ⚠️ **its card is in the test channel, not in the ticket** (see the warning above); **Close…** DMs the member for real, files the transcript, deletes the channel, and the card goes with it — the transcript carries one card, not two |
| 230 | Restart the bot (or wait five minutes) with an open ticket whose card you deleted by hand | the reconciler posts a new one within five minutes. Then check the dashboard's Modmail page: the practice ticket is **not** in the list, and a ticket read by number carries a `practice` field |

## Settings — `/settings` is ONE command that opens the panel (wave 4)

Built 2026-09-05 (`info/settings-panel-design.md`, Build 2, on top of Build 1's pure half). Rows
231–242 were written as `S1`–`S12` and numbered at the merge; 243–244 are Build 1's two website rows.
This is the LAST panel of the program: `/settings show|set|set-role|set-value|clear` and the
whole `/presence` group are gone, and the top-level count drops **30 → 29 with ZERO
`app_commands.Group`s left in the tree** — measured through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, not predicted.
✅ **Row 231 exercised by the owner 2026-09-05 14:35** (verbatim: "settings Slash menu looks good") — the root panel
opens and reads right. ✅ **Rows 232–244 exercised by the owner 2026-09-05 15:19** (verbatim: "1 and 2 are good",
item 2 being "sweeps 232–251 by eye") — the group cards, editors, roles & channels, look, panels, log levels and
the two website rows, shipped as v84 on 2026-09-05. Nothing was reported wrong.

| # | Do this | Expect |
|---|---|---|
| 231 | `/settings` as a Lead in `#mute-me-bot-test-spam` | ONE ephemeral panel. The top reads every feature's mode — sixteen lines, each naming the command that changes it (`**YouTube uploads** — shadow · /youtube to change`) — and **not one of them is a control here**. Below: **Turn a feature back on… · A setting group… · Roles & channels… · How Black Bloc looks… · Panels & commands… · Logs · Open on the site · Log levels… · Refresh**. Nothing anywhere says `/settings show` or `/settings set-value` |
| 232 | **A setting group…** → **chat** | the group card lists the chat settings and the picker says **25 of 28 — the rest are on the site**. Press **Find a setting…**, type `memory`, and the ones that were off the end are on the picker. `chat` is the only namespace over 25 — the other 21 groups never draw **Find a setting…** at all |
| 233 | **A setting group…** → **birthday** → `birthday_color` → **The colour…** → type `blue` | one sentence naming the shape `#4eefff` and **nothing is saved** — re-open the card and the colour is what it was. Type `#4EEFFF` and it saves as `#4eefff`, one `settings.set` row, **Via: Discord** on the Logs page |
| 234 | the same key card → **Put the default back**, then look for it again | the first press says the default is back and leaves one `settings.clear` row; **the second press is not there** — the button does not render on a key with nothing stored. No state is terminal and no button answers "nothing changed" |
| 235 | **A setting group…** → **automod** → `automod_rules` | the card has **no editor at all** and says the rule book is edited on `/automod` ▸ **A rule…**. It is the only key in the registry like that — every other one of the 181 has exactly one control |
| 236 | **A setting group…** → **honeypot** → `honeypot_exempt_role_ids`, with more than 25 roles stored | the role picker is **not drawn**, the card says the list is longer than one Discord picker can edit and names the Settings page, and **Clear the list** is still there. ⚠️ Under 25 the picker IS drawn with the stored roles already ticked, and its minimum is 0 so an empty submit clears the list |
| 237 | dashboard → Settings → `youtube_mode` → **off**. Wait a minute, `Ctrl+R`, then `/settings` | `/youtube` is gone from the command list, and the panel now carries **Turn a feature back on…** with **YouTube uploads — turn it on** on it. Pick it: within about a minute `/youtube` is back **on**, not shadow. ⚠️ **This row is the whole reason `set-value` could be retired** — it is the most important row in the set |
| 238 | `/settings set-value` | ⚠️ **there is no such command**, and neither is `/presence`. `/help` says so too: its missing-commands line now names **`/settings` ▸ Turn a feature back on…**. Type `/` and count: **29 commands, no groups** |
| 239 | **Panels & commands…** → **Leave every command showing**, with two features still off, then **Refresh** | the reply says the change lands within about a minute; every command is back at once; **Turn a feature back on… is absent**, and the embed says hiding is switched off altogether rather than "every command is showing" — the two sentences mean different things and the second would read as a bug |
| 240 | **How Black Bloc looks…** → **Re-apply presence** | the same sentence `/presence apply` used to print — whether the About Me changed and what the status now reads — and a `presence.bio_set` row when it did change. The card also shows when the status loop last succeeded and its last error. ⚠️ `/presence` itself is **gone from the command list** |
| 241 | **Roles & channels…** as a staff member who does **not** have Manage Server | the button is **not drawn** and the panel says in one line that re-pointing the staff, log, moderation-log and role-menu channels is for somebody with Manage Server. It is not offered-and-refused; it is not offered. As a Lead it is there, each picker labelled in words (*Where staff talk — and who counts as staff*) and never with the raw key name. ⚠️ Set `settings_core_keys_admin_only` to `false` and plain staff get it. Then open `staff_channel_id`'s own card as a Lead and press **Put the default back**: it asks first — *Are you sure?* naming **#mute-me-bot-test-spam** and saying that automod and the honeypot both stop arming, quietly. **Leave it as it is** changes nothing. It is the ONLY key that asks; every other reset is one press |
| 242 | **Log levels…** → **Chat** → the two buttons; then **Logs**; then leave the panel `settings_panel_minutes` (10) minutes | the level card offers only the two levels it is **not** on (never three with one greyed out), and the key's help text now says *and in `/chat` ▸ **Logs*** rather than naming a retired `logs` subcommand; **Logs** answers a **NEW** ephemeral message and the panel stays where it is; after ten minutes every control greys out and the footer reads *This panel has gone quiet — run /settings again* |
| 243 | dashboard → **Settings** → the **core** group | two rows at the bottom of it: **How long the /settings panel stays live** (10) and **Whether only a Lead may re-point the staff and log channels** (true). ⚠️ They must be under **core**, not under a group called `settings` — that is what `CORE_KEYS` is for (Build 1, v83) |
| 244 | set **How long the /settings panel stays live** to `0`, then to `10` again | `0` is refused in words by the same validator every other panel-minutes key uses, and nothing is saved. The Discord door onto the same key is `/settings` ▸ **Panels & commands…** ▸ **How long a panel stays open…** (Build 2, v84) |

## Modmail leftovers — the ticket card ON the panel (wave 4 follow-up)

Rows 245–251, written as `ML1`–`ML7` on `worktree-agent-ad2fc0f5aad473c19` and numbered at the
merge 2026-09-05; shipped as **v85**. ✅ **Exercised by the owner 2026-09-05 15:19** ("1 and 2 are good" — item 2
was "sweeps 232–251 by eye"); nothing reported wrong. The design is
[`../info/modmail-panel-design.md`](../info/modmail-panel-design.md) §B row S5 and §C *"The ticket
card ON THE PANEL"*. Everything here is a second door onto moves rows 219–230 already cover from
the card in the channel — the point of walking it is that the SAME move, pressed here, leaves the
same one row and the same one DM.

| # | Do this | Expect |
|---|---|---|
| 245 | `/modmail` with **no** ticket open, then DM the bot from a second account and run `/modmail` again | the first panel has no picker at all; the second carries **A ticket…** on its own row above **Setup…**, reading `#N · channel · <their name>` with the date it opened underneath |
| 246 | pick the ticket on **A ticket…** | the panel becomes that ticket's card — the **same** embed the sticky card in the test channel carries (number, who, when, mode, the in/out/note counts, and the blocked line if they are blocked) — over **Reply · Reply as Staff · Private note · Close… · Back** |
| 247 | **Reply** → type something; then **Reply as Staff** | both DM the member for real (test mode does not stop a DM), both leave **one** `modmail.reply` row on the Logs page, the anonymous one says **Staff** and carries no role colour, and the panel redraws the card with the counts one higher each time |
| 248 | **Private note** → some text | one *Private note* embed in the ticket, **one** `modmail.note` row, **no** DM, and the card's note count goes up |
| 249 | **Back** | the inbox again, with **A ticket…** still on it |
| 250 | **Close…** with a reason | the member is DM'd, the transcript is filed, the channel goes — and the panel is left showing the card with **only Back** on it and a footer saying the ticket is closed. Press **Back**: the ticket is gone from **A ticket…** |
| 251 | with **26** tickets open (or just read the picker with more than 25), and separately: pick a ticket, have somebody else close it, then press **Close…** | the picker shows 25 options and its placeholder reads **25 of 26 — the rest are on the site**; the raced close answers *"was closed by somebody else while you were typing"* in words and never a bare error. ⚠️ A `modmail.card_failed` row on the Logs page is now also written when the sticky card's own background move **raises** — before this it was a log line nobody could see |

## The self-test (wave 5) — rows 252–261

Rows 252–261, written as `ST1`–`ST10` on `worktree-agent-a4aa5efd43f249ba6` and numbered at the
merge 2026-09-05; shipped as **v86**, read checks corrected in **v87**. ✅ **Row 252 exercised by the owner 2026-09-05 16:21** (verbatim: "The test ran and worked") — a person pressed **Run the self-test** and it completed; the boot line at v87 read `106 ok, 0 failed, 24 messages posted` and the v86 purge deleted all 24. Rows 253–261 not yet walked one by one. Built 2026-09-05 (`info/selftest-design.md`). The bot
exercises itself against the real guild — every settings channel and role, every read the pages
make, all 18 panel cards posted as real messages, and six announcements rendered through their own
templates — then deletes every message it posted five minutes later. The log lines stay on the
dashboard's Logs page under **Test**. ⚠️ **Nothing below has met live Discord by a person**, and
nothing under `tests/live/` has been run against the deployed host.

| # | Do this | Expect |
|---|---|---|
| 252 | `/settings` as a Lead in `#mute-me-bot-test-spam` → **Self-test…** | a card titled **The self-test** saying what it will do, that it runs at every boot, where the cards go (`#mute-me-bot-test-spam`) and that they are deleted again after 5 minute(s). Buttons: **Run the self-test · Logs · Back**. ⚠️ **Purge now is NOT there** — nothing has been posted yet, so there is nothing to purge, and a button that answers "nothing to do" is not drawn |
| 253 | press **Run the self-test** and watch `#mute-me-bot-test-spam` | ~24 messages arrive: one root card per panel (`/settings`, `/automod`, `/honeypot`, `/mod`, `/modmail`, `/event`, `/poll`, `/birthday`, `/rolemenu`, `/voice`, `/request`, `/apply`, `/chat`, `/memory`, `/golive`, `/youtube`, `/pings`, `/raidtrain`) and six announcements (go-live, upload, birthday, event, ping prefix, raid-train lineup). The ephemeral answer says **N ok, M failed** and names every failure. ⚠️ **The buttons on those cards are REAL** — press one and it works, for as long as the card lives (fork F-ST3) |
| 254 | look at the card again, then press **Purge now** | **Purge now** is there now, and the embed says how many messages are still waiting. Pressing it answers *N self-test message(s) deleted.* and the channel is clean. Press it a second time: it is gone, because there is nothing left to purge |
| 255 | run it again and leave it alone for five minutes | every message the run posted disappears on its own, within about a minute of the fifth minute. The `/settings` ▸ **Self-test…** card then says its messages were deleted |
| 256 | dashboard → **Logs** | ⚠️ **not one `selftest.*` line is in the default view** — that is the point. The chip bar has a **Test** chip at the end; press it and only the test rows show: `selftest.started`, one `selftest.check` per check, `selftest.finished`, `selftest.purged`, each **via Discord** or **By the bot at boot**. Press **Everything** again and they vanish. The CSV export follows the same rule |
| 257 | `/settings` ▸ **Self-test…** ▸ **Logs** | a NEW ephemeral message titled **Test log** with the same rows. This is the ONLY door in Discord onto them, because the dashboard's default view leaves them out |
| 258 | dashboard → **Health** → the **Self-test** card | the last run: when, `ok`/`failed`/`posted`, whether its cards are still in Discord, and every failure by name with its sentence. **Run the self-test** starts one; while it is going the card refreshes itself every 15 seconds and the button is disabled. Older runs are in a **Runs before this one** foldout |
| 259 | press **Run the self-test** on the website twice, quickly | the second press is refused **in words** — *"A self-test is already running (started 14:03, 12 of 106 checks done)…"* — never a bare 409. The same sentence comes back from the `/settings` card if you press its button while a website run is going |
| 260 | dashboard → **Settings** → the **core** group | four new rows: **Whether the bot tests itself at every boot** (true), **Where the self-test posts the cards it is proving** (`#mute-me-bot-test-spam`), **How long the self-test's cards stay before the bot deletes them** (5), and **How much of the self-test is repeated into Discord** (**off** — the only feature that ships at off, on purpose). Set the minutes to `0`: refused in words. The Discord door onto all four is `/settings` ▸ **A setting group…** ▸ **core** |
| 261 | after the next deploy, `flyctl logs` | one line — `selftest: 106 ok, 0 failed, 24 messages posted (purge in 5 min)` — and one `selftest: FAILED <check> — <sentence>` line per failure. ⚠️ **This is the line that verifies a deploy**, without opening Discord at all. Turn `selftest_on_boot` off and the line stops; the boot purge of any leftovers still happens |

## When something fails
Take a screenshot, note the time, and paste it to Claude with the row number — the Fly logs around that
minute plus the dashboard Logs page are enough to diagnose. Nothing here is destructive; the worst case is
a `would_*` line in the log where you expected a post (that is test mode doing its job).

## Engineering sweep (settings + self-test leftovers)

Rows written as `ES1`–`ES4` on `worktree-agent-accb69989b295c889`, 2026-09-05, off `main` at
`aa03a01` (v87) — **the conductor numbers them at the merge**. These are the engineering
leftovers from the `/settings` (v84) and self-test (v86/v87) landings: three of them are a
refusal a person can now read instead of a thing quietly happening, and one is a help line that
had been naming retired commands. ⚠️ **None of it has met live Discord or the live dashboard.**
The verification is `pytest` (5127), `ruff check` and `node site/mock/check.mjs`
(17 pages / 149 routes / 12 core settings).

| # | Do this | Expect |
|---|---|---|
| ES1 | As a **Lead**: `/settings` in `#mute-me-bot-test-spam` → **Panels & commands…**. Have somebody take Manage Server off you (or take it off a second Lead who has the card open) — do NOT close the card — then press **Leave operator-token reads unlogged** | a plain ephemeral sentence: *"Nothing was changed: whether an operator-token read leaves a log line is changed by somebody with Manage Server, and this panel no longer has it. Ask a Lead if it needs to change; press **Refresh** and the card will say the same."* The setting is unchanged, no line lands on the Logs page, and nothing shows a bare status. Give the permission back, press the button again: it toggles, the card redraws, and one `settings.set` row appears under **Core** |
| ES2 | Dashboard → https://blackbloc.heygabi.ai/automod.html → set **Mode** to **on** while the staff channel is still `#mute-me-bot-test-spam` | the page refuses **in words** — the same sentence `/automod`'s own mode picker gives, naming the test channel — and `automod_mode` does not move. ⚠️ **Before this it silently succeeded**, arming automod from the website past a refusal the Discord panel was making. **shadow** and **off** still save normally. The same on https://blackbloc.heygabi.ai/honeypot.html: **on** is refused while no role can see the staff channel |
| ES3 | Dashboard → https://blackbloc.heygabi.ai/honeypot.html → change the **exempt roles** list, then https://blackbloc.heygabi.ai/audit.html#logs | ONE `honeypot.exempt_set` row, marked **via Website**, naming what was added and removed — the same row the `/honeypot` panel leaves. Before this a website edit of that list left **no row at all**, so nobody could tell it had happened |
| ES4 | Dashboard → https://blackbloc.heygabi.ai/settings.html → any `*_log_level` row's help text (e.g. **How much of the go-live log is repeated into Discord**) | the sentence ends *"…and in `/golive` ▸ **Logs**"* — a command that exists and a button that is really on that panel. Every one of the 18 features says its own. ⚠️ **Eight of them used to name a retired command** (`tempvoice`, `events`, `poll`, `birthday`, `golive`, `request`, `applications`, `pings`); that was fixed at the v84 landing and is now held there by a test that loads the whole tree and fails by name if any of them drifts again |
