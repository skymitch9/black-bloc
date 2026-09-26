# Guides audit — 2026-09-25: what is stale, what drifted, what is missing, and the re-shoot plan

> ✅ **2026-09-25 20:00 Phoenix — EXECUTED** by the re-shoot session (drill log at the top of
> [`../access/guides-capture.md`](../access/guides-capture.md)). **DONE:** §2 — every ⚠️/🔴 step and fault fixed live
> and in the seed (`7a3cdff1`), and the live text of every seeded guide brought to the seed (it was mostly the v111
> original); the pings audience → member; the six test-mode fault answers (the "seven" of §3 counts `minutes-take`
> f1, also fixed) rewritten as rehearsal answers. §3 — all 8 guides made and published on the site and in the seed.
> §4 — self-test run #69, 9 cards shot, 14 pictures uploaded (11 captures + 3 mocks), stale **12 → 0**.
> **REMAINS:** `/rolemenu` hidden while role menus are off (a CODE change, on TODO); the rolemenu guide itself was
> left as it is (archive or a "this is off" line is the owner's call); pictures for the 6 new staff guides and
> `minutes-take`; re-shooting the 6 non-stale older pictures (v121/v127) if their cards drifted.
> **Audience:** the end-of-day re-shoot session (a Claude session with Claude in Chrome), the
> conductor, and the owner. **Status:** TRACKED — secret NAMES only. A dated one-off: the
> re-shoot follows it once, then it is history (move it to `archive/` when the re-shoot lands).
> **Last verified: 2026-09-25 17:3x Phoenix**, read-only, against `main` at `0fecffa9` (v165 live
> + the merged-not-deployed `shadow-home-per-feature`, which is v166's content so far).
> **Measured:** `black_bloc/guides_seed.json` (19 guides, 80 steps) read whole; every **bold**
> control in every step and fault grepped against `black_bloc/**.py` and the panel builders read
> for each command; the stale list read through the operator token at 2026-09-26T00:28:23Z
> (`/api/guides/stale`, **12 shots**); the live settings read through the operator token at
> 17:34 Phoenix (`/api/settings` — the modes quoted below). `docs/deploys.log` v121–v165.
> **NOT verified:** nothing met Discord or a browser; nothing was pressed or uploaded. ⚠️ **The
> LIVE guide text was not read** — `/api/guides` is member-gated and refuses the operator token —
> so the wording table audits the SEED. Staff may already have edited a guide on its page; where
> they have, the live words win and this table is only a lead (see §2's first note). Which guide
> steps carry the 10 pictures that are NOT stale could not be listed for the same reason.

## Live state this audit leans on (operator read, 17:34 Phoenix)

| Key | Live | Why it matters to a guide |
|---|---|---|
| `events_review_mode` | **forum** | a proposal is a POST in the events forum, not a `pending-…` room |
| `marathon_mode` | **shadow** | `/event` shows **Marathons…** to members too (`cogs/community/events.py:502`) |
| `frontdoor_mode` | **shadow** | the door's posted copy is only in the rehearsal home, not a member channel |
| `rolemenu_mode` | **off** | since 2026-09-16 (retiring to Community onboarding); `/rolemenu` never hides (`command_visibility.py:35`) |
| `minutes_mode` | **off** | `/minutes` is hidden (`hide_commands_when_off` = true) |
| `raidtrain_mode` · `automod_mode` · `honeypot_mode` | shadow · shadow · shadow | |
| `pings_mode` · `golive_mode` · `spotlight_mode` · `youtube_live_mode` | on · on · on · on | |
| `modmail_mode` | **forum** | |
| `selftest_channel_id` / `selftest_purge_minutes` | `#blackbloc-logs` / **1** | the cards are gone a minute after they post |
| `TEST_MODE` | **false** since 2026-09-18 16:08 | every "Test mode is on" fault answer is now a rehearsal-only answer |

---

## 1. The stale table — the 12 shots `/api/guides/stale` lists

`stale_since` is the FIRST release that named the feature after the shot; later releases changed
the same card again. UTC → Phoenix is −7 h, and each `stale_since` matches a `deploys.log` line.

| # | Slug | Feature | Shot at | Stale since | What changed since (deploys.log / DONE) | Re-shoot how |
|---|---|---|---|---|---|---|
| 21 | `event-propose` | events | v121 (09-17 12:01) | **v128** 16:09 | v128 Send to… (request → pre-filled draft); v131 Try again; v136 events forum + Settings ▸ Rooms ▸ Forum; v137 Move to the forum; v138 Where hint; v148 Spotlight this stream on the card; **v164 `Marathons…` on the root** (`cogs/community/events.py:1523`, shown at `:502`); v165 marathon event modes | self-test root card `panel.event` in `#blackbloc-logs` — ⚠️ read its body first (staff view lists open events and who asked) |
| 22 | `event-review` | events | v121 | v128 | same card as #21 | the SAME capture file as #21, uploaded twice |
| 36 | `front-door` | modmail | v125 (09-17 15:03) | v128 | v129 rehearsal home + `rehearsal_note`; v141 `frontdoor_mode` shadow; v166 per-feature rehearsal home. The `/ask` card's words are settings keys — likely unchanged | self-test `panel.ask` — unchanged, just re-shoot |
| 37 | `request-file` | request | v127 (09-17 15:12) | v128 | v128 Send to events… on the card; v131 Try again; v143 `request_filed_line`; v150 the real Requests page (site only) | self-test `panel.request` — ⚠️ staff view lists requests with names; read the body |
| 40 | `modmail-ticket` | modmail | v127, **mock** | v128 | v128 **Make this a request… / Make this an event…** on the ticket card; v166 the ticket's rehearsal copy follows the door's home | **mock** (redraw) — the real inbox lists members' tickets; invent the names |
| 39 | `feature-modes` | core | v127 (09-17 15:13) | **v131** 18:12 | v131 four core keys (errors); v146 `Self-test…` ▸ Run the self-test; registry 284 → **488** keys (the root's count line) | self-test `panel.settings` — just re-shoot |
| 41 | `golive-announce` | golive | v127, **mock** | **v133** 18:44 | v133–v135 YouTube live; v139 uploads removed; v143 co-streaming; v148 Spotlight; **v151 `Channels…` + `Link from history`** on the staff half (`golive.py:766-767`); v154–v156 | **mock** (redraw) — the real card's staff half lists who is live; invent the names; member half = Link / Stop announcing / Refresh |
| 20 | `pings-follow` | pings | v121 | **v150** 23:32 | v150 spotlight ping roles (channel rows are followable, `pings.py:1219`); v164 ping windows on channel rows | self-test `panel.pings` — just re-shoot |
| 24 | `poll-vote-make` | poll | v121 | v150 | v150 the Discord mock on the shadow note; v166 poll rehearsal home | self-test `panel.poll` — just re-shoot |
| 27 | `raidtrain-slot` | raidtrain | v121 | v150 | v150 Raid trains page 21 + Also make an event; mode is shadow | self-test `panel.raidtrain` — just re-shoot (read the body: a lineup names people) |
| 34 | `birthday-set` | birthday | v121, **mock** | v150 | v150 Discord mock; v158 site Change; v159 **Post today's wishes** (staff only, `cogs/community/birthdays.py:516`) | **mock** (redraw) — the member view is unchanged: Set my birthday · Refresh; never a capture (§2 isolation rule) |
| 26 | `chat-memory` | chat | v121 | **v159** 14:07 | v159 tones + channel notes; v162 review queue; v163 greetings — none of it is on `/memory` | self-test `panel.memory` — unchanged, just re-shoot |

**Tally:** 12 stale shots on 12 guides; **9 captures from 8 cards** (event is one card for two
guides) + **3 mocks**. v166 will re-mark events / modmail / poll / golive (already stale — their
`stale_since` does not move).

⚠️ **Every self-test card is built for whoever runs it** (`selftest_panels.py:60`,
`api/writes.py:188`). From the Health page or `/test` that is the owner — a STAFF view — so every
member guide's picture shows the staff buttons (Settings, Logs, Marathons…, Pick an event…) and
any staff list. That was already true of the v121 pictures; it is a choice to keep, not a new
defect. What IS a stop sign: a staff list with member names in the card body — the §2 isolation
rule of `access/guides-capture.md` applies, and the answer is a mock.

---

## 2. The wording table — every guide, step by step (seed text)

⚠️ **How a wording fix actually lands.** A guide is DB rows seeded ONCE per guild; editing
`guides_seed.json` changes only what **Put the original back** restores (`guides.py:850-883`,
`refresh_seeds` never touches staff text). So each fix is TWO edits: the live text on the guide's
own page (staff edit in place) AND the seed (a commit, for the next deploy). 🔴 **Do not press
Put the original back to pick up a seed fix** — `reset_to_seed` deletes the steps and detaches
every picture from its step (`guides.py:896`, `UPDATE guide_media SET step_id = NULL`).

Legend: ✅ still true · ⚠️ drifted (the words to change, and what the code says now) · 🔴 names a
control that no longer exists. Steps are `s1…`, faults `f1…` (faults are listed only where they
drifted).

### `front-door` — `/ask` (member)

| Step | Verdict | Detail |
|---|---|---|
| s1 | ⚠️ live state | "find the message a Lead has posted in a channel" — `frontdoor_mode` is **shadow**: the posted copy exists only in the rehearsal home, so a member finds no message. The three labels are right (`settings_store.py:2384-2385`, `cogs/community/events.py:263`). Add "(once the front door is on)" or drop the clause until it is |
| s2 · s3 | ✅ | |

### `golive-announce` — `/golive` (member)

| Step | Verdict | Detail |
|---|---|---|
| s1 · s2 · s3 | ✅ | `golive.py:758` Link my Twitch channel; `:703` the twitch.tv/name line |
| s4 | ⚠️ | "set under **Announcement wording** on the site" → the Go-live page's section is **The announcement** (`site/public/assets/page-golive.js:1492`) and its card **The wording** (`:114`) with a Starting / Ending switch (`:117-120`) |
| s5 · s6 | ✅ | `golive.py:761-762`; `/youtube` **Link my channel** `youtube.py:360` |
| f1 | ⚠️ | "the one Once the stream is over box … right under the live wording, and the Wording card below both" → ONE card, **The wording**, with **Starting / Ending**; the ending box is still labelled *Once the stream is over* (`page-golive.js:132`) |
| f2 | ⚠️ | "The panel's **Announcements line** says so" → the panel's mode line reads *Go-live announcements are in **shadow** right now* (`golive.py:718`) |

### `pings-follow` — `/pings` (⚠️ audience **staff**)

| Step | Verdict | Detail |
|---|---|---|
| guide | ⚠️ decision | `audience: staff` (seed line 74) was the owner's 2026-09-16 call while pings was being remade ("make the guide staff only"). `pings_mode` is **on** now and members use `/pings`, but F-G3 hides staff guides from members — so no member can read it. Owner's call: flip to `member` |
| s1 | ✅ | `pings.py:821` Your pings |
| s2 | ⚠️ | "Press **Turn event pings on** … now says **Turn them off**" holds only while the go-live and event roles are one role (`pings.py:1172-1178`). Split, the panel shows **Turn go-live pings on** and **Turn event pings on**, and each turns into **Turn … off** (`pings.py:980-983`, `:1232-1237`) |
| s3 | ✅ | built from `pings.py:840` + `:982` |
| s4 | ✅ | still true; channels Black Bloc watches by name are followable too now (`pings.py:1219`) — worth one clause |
| s5 · s6 | ✅ | `pings.py:1020`, `:1032`, `:1037` |

### `event-propose` — `/event` (member)

| Step | Verdict | Detail |
|---|---|---|
| s1 | ✅ | **My time zone** `events.py:126`; the zone panel is a pick list plus *Other — type it…* (`events.py:614`) |
| s2 | ✅ | **Title & details** `events.py:577` |
| s3 | ⚠️ | "Pick a **Day**, an **Hour** and a **Minute**" → the dropdowns read **Date**, **Start time — hour**, **Start time — minute**, and a fourth, **How long?** (`when_picker.py:28-32`) |
| s4 | ✅ | **Where** `events.py:215` opens *Where is it?* with a channel pick and *Other — type a place or link…* (`events.py:581`, `:588`) |
| s5 | ⚠️ live state | "A review room named pending-you-title appears" → `events_review_mode` is **forum**: the proposal is a post in the events forum under BlackMail, tagged pending. The `pending-<name>-<title>` room (`events.py:160`) is room mode only |
| (picture) | — | the root card now carries **Marathons…** for everyone while `marathon_mode` ≠ off (`cogs/community/events.py:502`) |

### `birthday-set` — `/birthday` (member) — ✅ s1–s3 all true (`birthdays.py:289-292`; "next five" is `NEXT_LIMIT` 5 when `birthday_panel_next_for_members` is on, `birthdays.py:33`, `:36`)

### `voice-room` — `/voice` (member) — ✅ s1–s4 all true (`tempvoice.py:149-158`; creator name `settings_store.py:126`)

### `poll-vote-make` — `/poll` (member)

| Step | Verdict | Detail |
|---|---|---|
| s1 | ✅ | |
| s2 | ⚠️ | "the options one per line or split by \|" → the box's label is *The answers, separated by \|* (`cogs/community/polls.py:3174`), and it also carries Anonymous / Hidden switches (`:3159-3170`) |
| s3 | ⚠️ | "The **Where** dropdown" → the dropdown reads **Post it in…** (`cogs/community/polls.py:319`); *Where* is the preview's field above it (`:2254`) |
| s4 | ✅ | **Pick a poll…** `polls.py:304`, **End** `polls.py:887` |
| f3 | 🔴 | **Save the draft** → **Save for later** (or *Save (replaces your draft)*) (`cogs/community/polls.py:326-327`); **Resume the draft** → **Resume draft** (`:328`) |

### `request-file` — `/request` (member) — ✅ s1–s4 all true

Labels at `requests.py:512-531` and `cogs/community/requests.py:1332`. Two optional clauses:
s1's box also asks *Needed by* (`cogs/community/requests.py:1511`); s4's check DM also goes out
unasked when `request_check_on_ready` is on (`settings_store.py:1428`, live value not read).

### `chat-memory` — `/memory` (member) — ✅ s1–s4 all true (`cogs/content/chat_memory.py:111`, `:150`, `:153`)

### `raidtrain-slot` — `/raidtrain` (member) — ✅ s1–s4 all true (`cogs/content/raidtrain.py:914`, `:917`; `raidtrain.py:134`, `:195`). Mode is shadow live.

### `apply-form` — `/apply` (member) — ✅ s1–s3 all true (`applications.py:234-235`)

### `event-review` — `/event` (staff)

| Step | Verdict | Detail |
|---|---|---|
| s1 | ✅ | both homes are named; lead with the forum post, since that is live. **Pick an event…** `events.py:965` |
| s2 | ⚠️ live state | "The room renames to approved- or denied-" → in forum mode the post's TAG changes (six status tags, v136); the rename is room mode only |
| s3 | ⚠️ | "open the event on the website's Events page and press **Change it**" → press **Open** on its row (`page-events.js:204`), change the **Change it** card, press **Save** (`page-events.js:192`, `:173`). *Change it* is a card, not a button |
| s4 | ⚠️ live state | "press **Delete this room**" → in forum mode it reads **Delete this post** (`events.py:843`; room `:736`). f5 already says so; put it in the step |
| f2 · f3 | ⚠️ | "Test mode is on …" — TEST_MODE is off since 2026-09-18; true only for a rehearsal |

### `modmail-ticket` — `/modmail` (staff) — ✅ s1–s4 all true (`modmail.py:578-579`, `:842-844`; forum is live). f1 ⚠️ "Test mode redirects real tickets' cards there" — TEST_MODE off.

### `mod-case` — `/mod` (staff) — ✅ s1–s4 all true (`modcases.py:28`, `:532`, `:598-602`). f2 ⚠️ test-mode answer.

### `automod-arm` — `/automod` (staff) — ✅ s1–s5 all true (`cogs/moderation/automod.py:185-186`; `automod.py:510-511`, `:516`, `:526`). f3 ⚠️ test-mode answer.

### `honeypot-set` — `/honeypot` (staff) — ✅ s1–s4 all true (`honeypot.py:22-23`, `:49`; `cogs/moderation/honeypot.py:444`)

### `rolemenu-post` — `/rolemenu` (staff)

| Step | Verdict | Detail |
|---|---|---|
| guide | ⚠️ decision | every label is right (`rolemenus.py:85-87`, `:151-164`), but `rolemenu_mode` is **off** since the owner's 2026-09-16 22:4x retirement ("Our role menus will probably retire to use discords…"), and `/rolemenu` stays in the picker regardless (`command_visibility.py:35`). Owner's call: archive the guide, or add a first line that the feature is off |
| s1–s4 | ✅ | |
| f2 | ⚠️ | test-mode answer |

### `feature-modes` — `/settings` (staff)

| Step | Verdict | Detail |
|---|---|---|
| s1 · s2 · s4 | ✅ | `settings_panel.py:468-480`, `:150`, `:152` |
| s3 | ⚠️ | "A feature set to off loses its slash command" → only while `hide_commands_when_off` is on (it is), and never `/rolemenu`, `/help`, `/about`, `/ping` or `/settings` (`command_visibility.py:35`) |

### `minutes-take` — `/minutes` (staff) — ✅ s1–s5 all true (`minutes.py:84-90`, `:71`; `page-minutes.js:77`, `:96`)

f1 ⚠️: "Start says meeting minutes are turned off" — with `minutes_mode` off AND
`hide_commands_when_off` on (both live), `/minutes` is not in the picker at all, so nobody
reaches Start. The self-test posts no `/minutes` card (`selftest_panels.py:37-58`) — its picture
can only ever be a mock.

**Tally:** 80 steps — **69 ✅, 11 ⚠️, 0 🔴**. Faults: **10 drifted** (1 🔴 — poll f3; 7 are the
retired test-mode answer). Guide-level decisions for the owner: **3** (pings audience,
rolemenu retired, and whether the test-mode fault answers go or become rehearsal answers).

---

## 3. Missing guides — a command or member-facing panel with no guide

Written in the seed's voice (one **bold** control per step). None is in `guides_seed.json`; a
guide added to the seed is inserted on the next guides tick after a deploy (the v127 fix).

| Proposed slug | Title | Command · audience | Steps |
|---|---|---|---|
| `marathons-follow` | See when BaF runs at a marathon | `/event` ▸ **Marathons…** · member | 1. Type **/event** and press **Marathons…** → *A panel headed BaF next: every BaF run on a schedule Black Bloc follows, soonest first.* 2. Press **My runs** → *Your own runs, if a schedule lists you. A runner is matched by their Twitch link.* 3. Wait for the reminders → *One two hours before a run and one fifteen minutes before; the fifteen-minute one pings.* 4. Press **Back** → *The /event panel again.* (`marathon.py:67-70`, `:253-254`, `:279-284`; members see the button only while `marathon_mode` ≠ off) |
| `marathons-manage` | Follow a marathon's schedule | `/event` ▸ **Marathons…** · staff | 1. Type **/event**, press **Marathons…**, then **Add a marathon…** and paste the schedule link → *The marathon is listed with its dates, its runs and how many are BaF.* 2. Pick it from **Pick a marathon to manage…** → *Its card: schedule, last read, runs, event, board.* 3. Press **Pair a runner…** for a name the schedule has that Black Bloc could not match → *That runner is BaF from now on.* 4. Press **Post the board** → *One board post, edited in place as the schedule moves.* 5. **Feeds…** watches GDQ and RPG Limit Break for new marathons → *A new one arrives as a notice with Add it / Not this one.* (`marathon.py:95-97`, `:252-276`) |
| `golive-channels` | Watch a channel nobody here streams from | `/golive` ▸ **Channels…** · staff | 1. Type **/golive** and press **Channels…** → *Every channel watched by name, and whether it is spotlit.* 2. Press **Add a channel…**, type the name after twitch.tv/ → *It is announced like any other stream.* 3. Pick it from **A spotlighted channel…** and press **Spotlight on** → *Its announcement is pinned while it streams, with a reminder every few hours.* 4. Press **Set dates…** for a start and an end → *Nothing is announced before the start; the spotlight ends at the end.* 5. **Opt out of announcements**, **Give it a ping role**, **Marathons on/off** and **Link a YouTube channel** are on the same card. (`golive.py:766`; `spotlight.py:166`, `:176`, `:195`, `:199-200`, `:248`, `:293`; `settings_store.py:1848`; `marathon_channels.py:10-11`) |
| `ping-windows` | Ping only during an event | `/golive` ▸ **Channels…** · staff | 1. On **/golive** ▸ **Channels…** pick the channel → *Its Pings line: always, never or during events.* 2. Press **Pings: during events** → *Its announcements still post; they ping nobody outside a window.* 3. Press **Add a ping window…**, type **Pings start**, **Pings stop** and what it is for → *The window is listed under the channel.* 4. A window opening while the channel is live → *One pinged reminder.* 5. **Remove a ping window…** takes one off; a marathon's own window is changed on the marathon. (`spotlight.py:763-765`, `:776-783`, `:827`) |
| `chat-panel` | Teach Black Bloc what to say | `/chat` · staff | 1. Type **/chat** → *How Black Bloc answers: whether it answers, whether the models are on, what it knows.* 2. Press **Knowledge…** ▸ **Write one down…** → *A note it reads before answering.* 3. Press **Channel notes…** → *What each channel is for, read before the Discord topic.* 4. Press **Review queue…** → *Replies it was unsure of, one at a time, with **Approve**, **Write a fact…** and **Dismiss**.* 5. **Personality…** sets the voice. (`chat_panel.py:99`, `:226-233`, `:264-269`, `:293-303`; `settings_store.py:3686`, `:4198`) |
| `request-check` | Ask the requester to check the work | `/request` or the request's post · staff | 1. Press **Ready to check** on the request and say what was built → *It moves to review.* 2. Press **Ask them to check** → *They are DMed what to try, or pinged in the channel if DMs are shut.* 3. When they are happy press **Accept** → *Done, and the requester is told (`requests.py:229` names who may not accept their own).* 4. Not right yet: **Send back** with why → *In progress again.* (`requests.py:512-531`, `:202-213`, `:229`) |
| `apply-review` | Decide an application | `/apply` · staff | 1. Type **/apply** and use **Pick an application…** → *The answers and who sent them.* 2. Press **Approve** → *They get the role, or go on the list, and are DMed.* 3. Or **Deny** with a reason → *They are DMed it, with when they may apply again.* 4. Changed your mind: **Approve after all**. (`applications.py:232-235`, `:262-266`) |
| `posts-welcome` | Post and edit the welcome and rules | `/posts` · staff | 1. Type **/posts** and pick one from **A post…** → *Its card, with where it is posted.* 2. Edit the words on the site's Posts page, then **Post it** → *Posted, or updated in place where it already is.* 3. **Versions…** brings an older wording back. 4. **Take it down** removes it; every word is kept. (`cogs/community/posts.py:99-100`; `posts.py:193-196`) |

Not proposed: `/minutes` already has `minutes-take`; `/youtube` is `golive-announce` s6; `/test`,
`/help`, `/about`, `/ping`, `/purge`, `/reply` are one-shot commands with no panel to walk.
⚠️ `marathon-people` (dispatched 17:2x) may change the Marathons card — re-read
`cogs/content/marathon.py:2766` before seeding the two marathon guides.

---

## 4. The re-shoot plan — end of day, in runbook order

Runbook: [`../access/guides-capture.md`](../access/guides-capture.md). The session presses nothing
in Discord.

1. **v166 live first.** `docs/deploys.log` has a v166 line and `release.json` says v166. Then
   `.\scripts\read.ps1 -Path /api/guides/stale` — expect **12** (the same rows; v166 re-marks
   already-stale features). A number other than 12 is a finding; take the list it returns.
2. **Fix the words BEFORE shooting** (§2): the 11 ⚠️ steps and the poll f3 🔴 edited in place on
   each guide page by staff, and the same edits committed to the seed by a build agent. Never
   **Put the original back** (§2's first note). The 3 owner decisions go to him one at a time.
3. **Dashboard signed in** — `fetch('/api/auth/me')` answers 200, or the owner signs in.
4. **Keep the cards up.** Either the owner types `/test keep:30` in `#blackbloc-logs` (no borrowed
   setting), or the session borrows `selftest_purge_minutes` → 30 on the Settings page and presses
   **Run the self-test** on the Health page — and puts it back to **1** at the end.
5. **Shoot, in the order the self-test posts** (`selftest_panels.py:37-58`), 8 cards:
   `panel.settings` (feature-modes) → `panel.event` (event-propose + event-review, one file) →
   `panel.poll` → `panel.request` → `panel.ask` (front-door) → `panel.memory` (chat-memory) →
   `panel.pings` → `panel.raidtrain`. Read each card's BODY before uploading: `/event`, `/request`
   and `/raidtrain` are staff views that can list members — a list with names is a mock.
6. **Upload 9** (the event file twice), `a screenshot`.
7. **Draw 3 mocks** (§5 of the runbook, invented names, sampled colours): `modmail-ticket` (the
   forum-mode inbox), `golive-announce` (member half + the staff row Logs · Streamers… · Channels… ·
   Link from history), `birthday-set` (member view: Set my birthday · Refresh). Upload as
   `a drawn illustration`.
8. **Read the stale list again** — expect **0** — and report before/after, per §6.
9. **Optional, same session:** the `/event` ▸ Marathons… root card (`panel.marathon`) for a future
   `marathons-follow`, only once that guide exists.

**Estimate:** the owner: 0–2 clicks (sign in if signed out; `/test keep:30` if he runs it).
The session: about **160 tool calls** — setup ~15, 8 captures × ~5, 9 uploads × ~7, 3 mocks ×
~12, teardown ~5 — of which about **40 are page clicks** in the dashboard (uploads, the settings
borrow and return, Run the self-test). Plus the wording edits in step 2: ~20 fields across 9
guides.

---

## 5. What this audit did NOT verify

- Nothing in Discord or a browser. No card was looked at; "just re-shoot" means the code for that
  root card did not change its buttons, not that the pixels were compared.
- The **live** guide text (member-gated `/api/guides`); the table audits the seed.
- Which steps hold the **10 non-stale pictures**, and whether their cards drifted in releases
  whose `release.json` did not name the feature.
- `request_check_on_ready`, the pings role split (`golive_ping_role_id` vs `events_ping_role_id`, `pings.py:42-43`), and
  `birthday_panel_next_for_members` — the conditional clauses above hang on them.
- v166's final content: only `shadow-home-per-feature` is merged at `0fecffa9`; `marathon-people`
  is in flight.
- The Go-live page's section names were read from `page-golive.js`, not seen rendered.
