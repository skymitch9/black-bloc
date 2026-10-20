# Switch audit, 2026-10-19 — every mode, opt list and override, and where they contradict

> **Audience:** the owner (decisions, one at a time) and the builds that follow. **Status:** TRACKED · 🔎 READ-ONLY AUDIT, nothing changed. **Last verified: 2026-10-19 18:2x** — live values read through the operator token (`/api/settings`, `/api/posts`, `/api/sticky`); code read off `main` `1d27f595`. ⚠️ NOT verified: nothing met Discord or a browser; interactions I1–I10 are traced from code; build sizes are estimates. Measured by a 220k Opus agent at the owner's *"dry run audit first"*.

# Black Bloc switch audit (dry run, read-only)

**Code read:** `origin/main` `1d27f595` in a throwaway worktree. **Live values read:** `GET /api/settings`, `/api/posts` and `/api/sticky` through `scripts/read.ps1` (operator token), Mon 2026-10-19 ~18:27 Phoenix (`checked_at` 2026-10-20T01:27Z). No code, settings or docs were changed. File:line references are to `1d27f595`.

## 0. Headline

- The registry has **20 three-way `off/shadow/on` modes**, **12 two-way `off/on` enum modes**, **~110 on/off bools**, **14 rehearsal-home channel keys** (`shadow_channel_id` plus 13 `*_shadow_channel_id`) and **22 `*_log_level`** switches. That is 1,242 settings keys in total.
- "Shadow" means **three different things** depending on the feature:
  - (a) **Rehearsal copy.** A real message goes to a test channel. 12 features work this way.
  - (b) **Dry run.** The feature logs what it would do and posts nothing. 7 features.
  - (c) **Not a rehearsal at all.** For `tempvoice_mode`, shadow means the lobby is visible to staff only.
- The Posts page has **3 visible switches today**: posts (`on`), sticky (`shadow`) and weekly questions (`on`). It also has **at least 7 hidden ones**: each block's owning feature mode, plus `points_mode`, which actually decides the leaderboard sticky.
- **The biggest surprise:** `sticky_mode = shadow` does **not** keep the leaderboard sticky in rehearsal. `points_mode` does. Details in I1.

## 1. Inventory of every switch

### 1a. The 20 three-way modes (live value / default; ★ = live differs from the default)

| Key | Live | Default | Read by (file:line) | What shadow does for this feature | Site page | Shadow kind |
|---|---|---|---|---|---|---|
| `posts_mode` | **on** ★ | shadow | `posts.py:26,386`, `publish_post :1406-1440`, `rehearse_post :1537` | Post it sends the message to the rehearsal home, not the post's channel. In shadow, Post to test = Post it (`:1544`), so that button is hidden | Posts (chip) | a |
| `sticky_mode` | **shadow** | shadow | `sticky.py:472`, `sticky_posts.py:113-126` (`owner_rule`) | Every sticky copy goes to the rehearsal home with a "where it would go" line. ⚠️ A sticky of a post that a feature owns follows **that feature's** mode instead (see I1) | Posts ▸ Sticky messages | a |
| `question_mode` | **on** ★ | shadow | `questions.py:217`, `questions_moves.py:51-70` | Each week's question is posted in the rehearsal home with the note | Posts ▸ Weekly questions (settings fold only) | a |
| `points_mode` | **shadow** | shadow | `points_moves.py`, `cogs/content/points.py:16`, `sticky_posts.py:121` (via the leaderboard block `owner=`, `post_blocks.py:~476`) | Runs are taken and approved for real. The top-places post and the **leaderboard sticky** go to the rehearsal home | Leaderboard | a |
| `frontdoor_mode` | on | on | `frontdoor.py:155` `door_is_on` (≠ off), `cogs/community/frontdoor.py:528` | A standalone door goes to the rehearsal home with the note. **A door carried by a post ignores shadow** (I2) | Modmail | a |
| `poll_mode` | on | on | `polls.py:276`, `cogs/community/polls.py:3324` | Polls are posted for real into the rehearsal home or log channel, with a "why here" line | Polls | a |
| `birthday_mode` | **on** ★ | shadow | `birthdays.py:506`, `cogs/community/birthdays.py:1147-1158,1266` | A rehearsal copy goes to the rehearsal home. The key's help text says "log only", which is **stale**: the code posts a copy | Settings and the block editor | a |
| `marathon_mode` | **on** ★ | shadow | `settings_store.py:7080`, `marathons-section.js` | Board, reminders and shoutouts go to the rehearsal home with the note | Events ▸ Marathons | a |
| `spotlight_mode` | **on** ★ | shadow | `cogs/content/spotlight.py:1840,2505`, `golive.py:1911` | The rehearsal copy goes to the rehearsal home | Go-live | a |
| `brackets_mode` | **shadow** | shadow | `command_visibility.py:21`, brackets modules | Tournaments run for real, but the thread is made in the rehearsal home (today that is the **log channel**, because `brackets_shadow_channel_id` is blank) | Brackets | a |
| `pb_feed_mode` | **off** ★ | shadow | `settings_panel.py:82`, `pb_feed.py` | Looks for new PBs and sends them to the rehearsal home | PBs | a |
| `structure_backup_mode` | **shadow** | shadow | `settings_store.py:3638` | The snapshot is taken for real and the notice goes to `structure_backup_shadow_channel_id`. That key is blank live, so **no notice goes anywhere**. Shadow is effectively "on, silent" | Structure (leads only) | a/b |
| `golive_mode` | **on** ★ | shadow | `cogs/content/golive.py:1706,1911,2018`, `youtube.py:399,991` | Watches and logs. (`golive_shadow_channel_id` is the home for spotlight rehearsals.) Help says "Off by default", but the default is shadow: **stale** | Go-live | b |
| `youtube_live_mode` | **on** ★ | off | `cogs/content/youtube.py:321,899,978` | Probes and logs. It also passes through `golive_mode` | Go-live | b |
| `events_mode` | on | on | `cogs/community/events.py:468,1040,2566,2575` | No public announcement. The Upcoming block draws but stays empty (I3) | Events | b |
| `applications_mode` | **on** ★ | off | `applications.py:30` | Log only: nothing is posted or DMed | Role menus | b |
| `raidtrain_mode` | **shadow** ★ | off | `cogs/content/raidtrain.py:428,819` | Log only | Settings | b |
| `honeypot_mode` | **shadow** | shadow | `cogs/moderation/honeypot.py:404,489,793` | Log only; nobody is banned | Settings | b (safety) |
| `automod_mode` | **shadow** | shadow | `cogs/moderation/automod.py:575,834,1082` | Logs what it would delete, warn or time out | Automod | b (safety) |
| `tempvoice_mode` | on | on | `cogs/community/tempvoice.py:739,1622,2587`, `tempvoice.py:211-218` | **Not a rehearsal:** rooms are really made, but only staff can see the lobby | Settings | c |

**Live `shadow` right now:** sticky, points, brackets, structure_backup, raidtrain, honeypot, automod.
**Live `off`:** pb_feed, rolemenu, minutes, poll_review.

### 1b. Two-way `off/on` enum modes

| Key | Live | Default | Note |
|---|---|---|---|
| `pings_mode` | on ★ | off | Hides `/pings`. A member can take themselves off the list even while it is off (`cogs/content/pings.py:728`) |
| `request_mode` | on | on | |
| `rolemenu_mode` | **off** | off | Panels down, `/rolemenu` hidden |
| `chat_mode` / `chat_llm_mode` / `chat_memory_mode` | on / on ★ / on ★ | on / off / off | |
| `chat_tone_feedback_mode` / `chat_review_mode` | on / on | on / on | |
| `chat_greeting_via_model` | on | on | An enum where a bool would do |
| `guides_mode` | on | on | |
| `handoff_mode` | on | on | |
| `minutes_mode` | **off** | off | Prototype |
| `poll_review_mode` | off | off | |
| `golive_costream_mode` | on | on | A behaviour choice, not a feature gate |
| `boot_status_mode` | on | on | Internal ops |
| `modmail_enabled` (bool) | true ★ | false | "Old ModMail bot vs Black Bloc" cut-over switch |

Choice enums that are not on/off (`modmail_mode`, `events_review_mode`, `events_where_link_check`, …) are left out.

### 1c. Rehearsal homes (where shadow and Post to test send things)

`shadow.py:home_id/channel_id` resolves in this order: the feature's own key, then `shadow_channel_id`, then the guard channel, then `log_channel_id`.

| Key | Live |
|---|---|
| `shadow_channel_id` (global) | `1542316174472380517`, the **same channel as `log_channel_id`** |
| `posts_shadow_channel_id`, `sticky_shadow_channel_id`, `question_shadow_channel_id`, `points_shadow_channel_id`, `frontdoor_shadow_channel_id` | all **#post-test** `1550284332365783091` |
| `golive_`, `marathon_`, `marathon_public_`, `poll_`, `birthday_`, `brackets_`, `pb_feed_shadow_channel_id` | blank, so they fall back to the log channel |
| `structure_backup_shadow_channel_id` | blank. **Never falls back, on purpose** (it names private channels) |

Related state keys:
- `rehearsal_note`: blank live, so rehearsal copies carry no note line.
- `poll_shadow_note` and `pb_feed_posting_shadow`: shadow-only wording.
- `frontdoor_shadow_message_id` is **set** (`1560105628234420427`) even though the door is `on` and carried by the welcome post. It may be a stale id; not verified.
- `frontdoor_shadow_hash`, `modmail_panel_shadow_message_id` and `modmail_panel_shadow_hash` are blank.

### 1d. Per-feature on/off bools

About 110 of them, spread over golive (12), marathon (28), request (7), chat (6), poll (6), frontdoor/modmail (8), raidtrain (5), guides (3), and a few in core and posts.

**Every one is at its default live except `modmail_enabled`** (true). These are behaviour options inside a feature, not on/off gates for the feature, so this audit leaves them alone apart from §4 P4.

### 1e. Hide-when-off and the `/settings` mode list

- `HIDDEN_WHEN_OFF` (`command_visibility.py:17-38`) maps 20 mode keys to the commands hidden when `hide_commands_when_off` is true (live: true).
- **Only `off` hides a command; shadow never does.**
- `/settings` root shows `FEATURE_MODES` (`settings_panel.py:108-137`): those 20 plus 5 `EXTRA_MODES` (chat memory, modmail, marathon, structure backup, pb feed) = **exactly 25**. A test pins it at 25 (`tests/test_settings_panel.py:156`).
- `SELECT_LIMIT = 25` (`settings_panel.py:34`) is the Discord select cap. Any new mode breaks the pinned count, and the list is already at the cap. Removing switches buys headroom.
- `question_mode` and `spotlight_mode` are **not** in that list at all. They can only be changed through the site and `/settings set-value`.

## 2. Permission gates (brief)

"Permissions" in the code mostly means **who may do something**, and that side is already simple. The on/off/shadow switches are the real sprawl.

**Site API tiers:**
- `member_dependency` / `member_read_dependency` (`api/writes.py:106-131`): signed in and in the server.
- `staff_dependency` (`api/auth.py:393`): can see `staff_channel_id`.
- `writer_dependency` / `reader_dependency` (`api/writes.py:134-158`): staff plus a rate bucket.
- `leads_dependency` (`api/tools/structure.py:102`): staff and the structure rule (`structure_backup_role_id`, the owner or Administrator); never the operator token.

**Who may change a mode:** any staff writer. The exceptions:
- `settings_core_keys_admin_only` (true) locks the four core keys (staff, log and modlog channels…) to admins.
- `SITE_ONLY_KEYS` is a single key, `marathon_optout_role_ids`.
- Discord slash commands default to `STAFF_ONLY = manage_messages` (`command_visibility.py:15`).

**Per-feature role and "who" gates** (each one adds a group beside staff or narrows one):

| Key | Live |
|---|---|
| `brackets_to_role_id` | blank |
| `points_verifier_role_id` | blank |
| `raidtrain_organizer_role_id` | blank |
| `applications_approver_role_id` | blank (falls back to `rolemenu_approver_role_id`, then staff) |
| `events_room_delete_who` | staff (`events_approver_role_id` blank) |
| `guides_who_edits` | staff |
| `poll_who_can_create` | staff |
| `poll_creator_may_end` | true |
| `request_who_can_file` | everyone |
| `request_review_by_other` | false |
| `modmail_member_command` | true |
| `birthday_panel_lookup` | true (any member may look others up; see I6) |
| `birthday_panel_next_for_members` | true |
| `chat_status_admin_only` | true |
| `chat_staff_can_ping_roles` | true |
| `chat_memory_staff_view` | counts |
| `tempvoice_allowed_role_id` | set |
| `chat_visibility_role_id` | set |

**Verdict:** there is little to merge here. The two places that *are* tangled are the opt-in/opt-out lists (section 5) and the hidden coupling between modes (I1, I2).

## 3. The Posts-page umbrella today

`page-posts.js:1276-1280` renders five sections: **The posts**, **Blocks**, **Sticky messages**, **Weekly questions**, and **Settings and logs**.

| Item on the page | Its switch(es) today | Live |
|---|---|---|
| Posts (2: *Welcome and rules* → #welcome-ish `1285369365071527997`, posted live and carrying the door; *Leaderboard* → #speed-and-pbs, never posted for real) | `posts_mode` (chip, `page-posts.js:1130`) + `posts_shadow_channel_id` | on, #post-test |
| Blocks: frontdoor, tempvoice, marathonrole, pingsfollow, birthday, proposeevent, livenow, upcoming, links, leaderboard (`post_blocks.py:92-101`) | Each block draws or blanks on its **owner feature's mode** (`blockwords.js:246-265` offKey: pings, birthday, events; `tempvoice.shows_block`; `golive.py:1905` BLOCK_SHOWN_MODE; `door_is_on`; leaderboard → `points_mode`) | mixed |
| Sticky messages (1 row: the Leaderboard post in #speed-and-pbs, **state `rehearsing`**, copy in #post-test since 2026-10-10) | `sticky_mode` (`sticky-section.js:31`, `modeSwitch`) **AND** `points_mode` through `owner_rule` | shadow / shadow |
| Weekly questions | `question_mode` + `question_shadow_channel_id`, in the section's settings fold | on, #post-test |

**Existing Post to test** (`docs/info/post-to-test-design.md`, live since v223):
- `posts.rehearse_post` (`posts.py:1537`), `POST /api/posts/{slug}/rehearse`, and the `/posts` card button on row 1.
- It sends a copy, with the rehearsal note, to `posts_shadow_channel_id` (#post-test) and tracks it on `posts.shadow_message_id`.
- It uses `set_test_copy` so the real post's `posted_*` fields are untouched.
- The next real Post it takes the copy down (`_drop_shadow`), and `Desk._drop_test_copy` does the same for stickies.
- The button is **hidden while the mode is shadow**, because there Post it already goes to #post-test.
- Live: both posts carry `test_copy: true`.
- Sticky words (not a post) and weekly questions have **no** Post to test today. Questions is the queued item (a).

## 4. Proposals, ranked

### P1. One off/on switch for the Posts umbrella, shadow replaced by Post to test (recommended, do first)

**What merges:** `posts_mode`, `sticky_mode` and `question_mode` become **one `posts_mode` with values `off`/`on`**. The shadow value is retired for these three.

Each item gets a **Post to test** button:
- **Posts:** exists already.
- **Questions:** queued item (a). It sends this week's question, with the note, to the test channel and never touches the slot state.
- **Sticky:** new. "Post to test" on a sticky row sends one plain, unpinned copy to the test channel, as `rehearse_post` already does for a sticky's post (`posts.py:1550-1556`). Extend it to words-stickies.

**Keys affected:**
- Retire `sticky_mode` and `question_mode`.
- Narrow `posts_mode` choices to `off`/`on`.
- Fold `sticky_shadow_channel_id` and `question_shadow_channel_id` into `posts_shadow_channel_id`. All three are #post-test today, so nothing moves.
- `HIDDEN_WHEN_OFF` loses `sticky_mode`. `/sticky` hides under `posts_mode` instead.
- `FEATURE_MODES` drops from 25 to 24.
- **Decouple placement from `points_mode`:** the leaderboard sticky should follow the Posts switch, not `points_mode` (fixes I1). `points_mode` then governs only whether runs are taken. Also the top-places post if staff want; that is the one owner decision.
- The carried front door already follows `posts_mode` (I2). Say so and drop `frontdoor_mode`'s shadow value (see P3).

**Who would see what differently the moment it ships:**
- **Welcome post:** nothing changes (already `on`).
- **Weekly questions:** nothing changes (already `on`).
- ⚠️ **Leaderboard sticky:** it is `rehearsing` in #post-test because `sticky_mode = shadow` and `points_mode = shadow`. If the merged switch reads `on` and the sticky follows it, **members in #speed-and-pbs get a new leaderboard message that keeps re-sticking to the bottom of the channel**, and the copy in #post-test is taken down. To avoid that, the migration should **pause** any sticky row whose state is `rehearsing` (sticky rows already have a `paused` state). Staff then press Post to test and Resume when ready. Nobody sees a change until a person acts.
- **Staff:** the Sticky "shadow / on / off" control disappears. Posts shows one switch.

**Migration (settings rows, no schema change):**
1. Read `sticky_mode`. If it is not `on`, pause each sticky that is not paused; that is today's single row.
2. Delete the stored `sticky_mode`, `question_mode`, `sticky_shadow_channel_id` and `question_shadow_channel_id`.
3. Map `posts_mode = shadow` to `on` (it is already on).

Sticky reading `paused` needs one extra word in the posted-state pill. A dry-run migration report should list each row it would pause.

**Risk:**
- Losing "let it run unattended in the test channel for a few days" for stickies. Post to test is a one-shot.
- The weekly question's automatic post loses its rehearsal; Post to test covers it.
- The `owner_rule` rewrite touches the Desk's one-at-a-time lock; it is checklist territory.

**Build size:** posts/sticky/questions code, site (3 sections), mock, contract, tests, migration. That is a **multi-layer build**: by the CLAUDE.md calibration table, between 279k (one subsystem) and 474k (core + db + worker + web). Split it: (1) Post to test for questions and stickies; (2) the switch merge and migration.

### P2. One test channel instead of 14 rehearsal homes

**What merges:**
- `shadow_channel_id` plus 12 per-feature `*_shadow_channel_id` become **one `test_channel_id`**. A label rename is enough: keep the key `shadow_channel_id`, call it "Test channel".
- Keep `structure_backup_shadow_channel_id`, which is deliberately non-falling-back for privacy.

**Behaviour change if it is set to #post-test:**
- Every feature whose override is blank today rehearses in the **log channel** and would move to #post-test.
- **Live, only `brackets_mode` is shadow among those**, so new tournament threads would start being made in #post-test instead of the log channel.
- Polls, birthdays, spotlight and marathon are `on`, so nothing changes for them until someone uses shadow or Post to test.
- pb_feed is off.

**Migration:** copy #post-test into `shadow_channel_id`, delete the 12 overrides (5 are set, all to #post-test; 7 are blank).

**Risk:** low. The only loss is "send just X's rehearsals elsewhere", and nobody uses it: every set override has the same value.

**Size:** small to medium. Mostly `shadow.py`, `SHADOW_HOME_WORDS` (`settings_store.py:3436`), labels, and the site settings panels.

### P3. App-wide: give "shadow" one meaning

Today shadow means three things (§1a "Shadow kind"). Proposal:

**(a) Staff-triggered content:** posts, sticky, questions, polls, front door, event announcements. Use **off/on + Post to test**, as in P1.
- `poll_mode` and `frontdoor_mode` lose `shadow`. Both are `on` live, so nobody sees a change.
- The `frontdoor_shadow_*` and `poll_shadow_*` keys can go: `frontdoor_shadow_channel_id`, `frontdoor_shadow_message_id`, `frontdoor_shadow_hash`, `poll_shadow_channel_id`, `poll_shadow_note`.
- `modmail_panel_shadow_*` too, if the ticket button's shadow path goes with the door's. Verify first.

**(b) Automated posters and safety features keep three states, renamed "test":** marathon, spotlight, golive, youtube, birthday, points top-places, brackets, pb_feed, raidtrain, applications, events, honeypot, automod, structure.
- These post on a timer or act on members, so "watch it run before trusting it" is real value. **Shadow must survive for honeypot and automod** (bans and timeouts).
- Rename the value in words only ("test"). Keep the stored value `shadow` to avoid a migration.

**(c) `tempvoice_mode` shadow** becomes a word change: "staff only". Keep the stored value or migrate it. No behaviour change.

**Also fold:**
- `youtube_live_mode` into `golive_mode`. YouTube becomes a plain bool, "also watch YouTube". Today both must agree (`youtube.py:399`), and its shadow only logs.
- `spotlight_mode`'s off/on into golive's. Keep its own on/off if staff want spotlight separately; that is an owner decision.

**Size:** medium per feature, mostly words and tests. It can be rolled out one feature at a time.

### P4. Switches that are dead, unused or never moved (candidates to simply remove or turn into constants)

All of these are still at their default live. "Never changed" was **not** proven from the action log.

**Mode keys:**
- `boot_status_mode` (on): ops-only, make it a constant.
- `chat_greeting_via_model` (on): an enum that should be a bool, or a constant.
- `golive_costream_mode` (on): keep only if staff ever want "second platform not announced".
- `handoff_mode` (on): keep or make constant.
- `modmail_enabled` (true ★): a cut-over switch. If the old ModMail bot is gone, retire it. Not verified.
- `rolemenu_mode` (off) and `minutes_mode` (off, prototype): parked features. Keep; they hide their commands.
- `poll_review_mode` (off): keep (a real choice).

**Shadow-only leftovers:** these go with P1 and P3.
- `poll_shadow_note`, `pb_feed_posting_shadow`, `rehearsal_note` (blank live).
- `frontdoor_shadow_message_id` / `_hash` and `modmail_panel_shadow_message_id` / `_hash`.
- `marathon_public_shadow_channel_id` (blank; P2).

**Twenty-two `*_log_level` keys plus `logs_important_only`:** out of scope here, but it is the next largest family of switches.

## 5. How switches, opt-in/opt-out lists, roles and overrides interact (owner's "permissions loops")

Each item lists: what is involved, which wins today, a surprising scenario, and a simpler rule.

**I1. Sticky mode vs the owning feature's mode.**
- **Involved:** `sticky_mode`, `points_mode` (leaderboard block `owner=`), `sticky_posts.owner_rule` (`sticky_posts.py:113-126`).
- **Wins today:** `sticky_mode = off` stops everything. Any other value hands control to the owner's mode. So `sticky_mode = shadow` + `points_mode = on` makes the sticky **live**.
- **Scenario:** staff flip Points to `on` to start taking runs. The leaderboard sticky starts posting in #speed-and-pbs, even though the Sticky messages switch on the Posts page still reads *shadow*.
- **Rule:** placement is decided by the Posts switch alone (P1). A feature's mode decides whether its data exists, never where a post goes.

**I2. Front door carried by a post.**
- **Involved:** `frontdoor_mode`, `posts.carries_door`, `frontdoor.door_is_on` (`frontdoor.py:155`), `carried_parts` (`cogs/community/frontdoor.py:528`).
- **Wins today:** for a carried door, `frontdoor_mode` only matters as off versus not-off. `posts_mode` decides where it goes.
- **Scenario:** staff set the front door to *shadow* to rehearse a wording change. The welcome post, which is `on`, keeps showing the door live in the real channel. The shadow setting does nothing.
- **Rule:** the carried door follows the post. Front door becomes off/on, and wording is checked with Post to test.

**I3. Events shadow vs the Upcoming block.**
- **Involved:** `events_mode` (`events.py:2566` loads events only when `on`; `:2575` blanks the block only when `off`).
- **Scenario:** with events in shadow, every post carrying Upcoming shows an empty "no upcoming events" card to members.
- **Rule:** a block shows when its feature is `on` and is hidden otherwise, the same as livenow (`golive.py:1905`) and tempvoice (`tempvoice.py:216`).

**I4. Go-live opt-out does not reach spotlight or marathons.**
- **Involved:** the `golive_optout` table (one row per user, **no guild column**, `storage/db.py:130`), checked only by the member go-live path (`cogs/content/golive.py:1356`) and the history sweep (`:645`). Spotlight `add` (`cogs/content/spotlight.py:1936-1966`) never consults it.
- The marathon People card offers **Spotlight…** for any runner whose Twitch login has no spotlight row (`marathon_people.py:471-472`).
- Marathon runner and public posts use their own lists (I5).
- **Scenario:** a member opts out of go-live announcements. Staff, or a marathon, spotlights their Twitch login. The stream is then announced and pinned anyway, and marathon posts can still @-mention them (`marathon_mention_people` = true).
- **Rule:** one per-person "don't announce me" that every announcer reads (go-live, spotlight, YouTube, marathon public and runner posts, PB feed). Staff override it only with a logged reason, per the staff-final-say rule.
- **Not exercised:** this is inferred from the code paths.

**I5. Marathon BaF: role opt-out, then override, then per-marathon opt-out, then announce defaults.**
- **Involved:**
  - `marathon_optout_role_ids` (SITE_ONLY; live: one role)
  - `marathon_baf_overrides` table (`db.py:1201`)
  - per-marathon `opted` column (`marathon_announce.py:180`)
  - `marathon_announcements_default` (true) / `marathon_host_announcements_default` (false)
  - per-run answers
  - `marathon_mention_people`
- **Wins today:** the override beats the role. `not_ours` = role holders minus overrides (`marathon_announce.py:201`). The per-marathon opt-out then only removes public posts.
- **Scenario:**
  1. Staff press "Count as BaF anyway" on someone.
  2. Later that person puts on the opt-out role themselves, meaning "leave me out".
  3. The old override silently keeps them in.
  4. Members ▸ Opted out lists them under a `marathon_override` chip, which is an *opt-in*, inside the opted-out roll-up (`api/tools/optouts.py:36-42`).
- The role can only be edited on the site, but the override is pressed in Discord.
- **Rule:**
  - "Latest act wins": taking the role after an override clears the override, with a log line and a staff notice.
  - Show overrides as their own "counted in" list, not as an opt-out.
  - The four layers collapse to: the person's choice, then a staff override with a reason, then per-marathon "not this one".

**I6. Birthday opt-out vs member lookup.**
- **Involved:** `birthdays.opted_in` (stops the post: `cogs/community/birthdays.py:1158`) and `birthday_panel_lookup` (true).
- **Wins today:** `build_card` (`cogs/community/birthdays.py:541-553`) shows the date to **any member** whatever `opted_in` says. The key's help text calls opt-out "the member's own privacy control".
- **Scenario:** a member opts out for privacy, and another member looks them up on `/birthday` and sees the date.
- **Rule:** opted out means hidden from other members. Staff still see it.

**I7. Hide-when-off removes the undo door.**
- **Involved:** `hide_commands_when_off` (true) and `HIDDEN_WHEN_OFF`.
- `pings_mode = off` hides `/pings` (`command_visibility.py:29-31`). The member's own "take me off" works while off (`cogs/content/pings.py:728`), but the command that carries it is gone, and "nobody loses a role they already wear".
- **Scenario:** pings are switched off. A member wants to drop the Events role and has no button left, unless a post still carries the pings-follow block (not checked).
- The same shape applies to `/golive` (member opt-out) and `/birthday` (opt-out), but there nothing posts while off, so the harm is low.
- **Rule:** a command whose panel holds a member's own opt-out or role removal is never hidden. Alternatively, turning the feature off removes the roles it handed out.
- **Escape that already exists:** `/settings` "back on" (`settings_panel.py:550`). Staff are never locked out.

**I8. The two announcement gates plus the role filters.**
- **Order today** (`cogs/content/golive.py:1350-1362`): `golive_mode` off, then `golive_optout`, then `golive_require_role_id` / `golive_ignore_role_id`, then the cooldown.
- Separately: `youtube_live_mode` must also be non-off (`youtube.py:321`); `spotlight_mode` gates non-members; the per-spotlight-channel `announce` field gates each channel (`spotlight.py:908-911`); `golive_member_optout_post` / `golive_channel_optout_post` decide what happens to an already-posted message.
- **Scenario:** staff can't tell from one place why someone was not announced. There are 5 gates on 3 pages.
- **Rule:** one go-live switch, one "also watch YouTube" bool, and one per-person opt-out (I4). The ignore role becomes a filter on that same person list, so it shows in the roll-up.

**I9. The Members ▸ Opted out roll-up is partial, and one source flips meaning.**
- **Sources** (`api/tools/optouts.py:24`): marathon role, marathon override (an opt-*in*), per-marathon posts, go-live, chat memory, birthdays, PBs.
- **Missing:** `golive_ignore_role_id` holders, pings streamer-list hides, spotlight channel opt-outs, opted-out marathon channels (ESA seed), honeypot and automod exempt roles.
- **Flipping source:** chat memory's entry depends on `chat_memory_consent` (live `optout`). Flipping it to `optin` turns **everyone** without a row into "opted out" overnight (`chat_memory.off_default`, `chat_memory.py:1103`).
- **Rule:** the roll-up reads one canonical per-person table (I4/I5), and consent-model changes are confirmed with a count first.

**I10. Staff override of a member's own opt-out.**
- `/golive` ▸ Streamers lets staff opt a member back **in** (`cogs/content/golive.py:2217-2220`). That follows the staff-final-say rule, but it silently reverses a privacy choice.
- **Rule:** keep it, but require a reason and DM the person. The house rule already says "with a DM'd reason where a person is affected"; whether this path DMs was **not checked**.

## 6. What I did NOT verify

- Nothing met Discord or a browser. All behaviour is read from code at `1d27f595` plus live settings JSON. The working-tree branch `questions-this-week` (uncommitted questions changes) was **not** read.
- I1, I2, I4 and I6 are traced from code paths, not exercised. I3 is from code only.
- Whether any key was ever changed and then set back. Equal-to-default was read; the action log was not.
- Whether `frontdoor_shadow_message_id = 1560105628234420427` is a stale id or a live message.
- Whether the old ModMail bot still exists (`modmail_enabled` retirement).
- Whether the pings-follow block's button works while `pings_mode` is off (I7).
- Whether the birthday month list exposes opted-out people to members. `MonthSelect` was not traced.
- Phone-width and site rendering of any section.
- Build-size figures are estimates from the CLAUDE.md calibration table, not measurements.
