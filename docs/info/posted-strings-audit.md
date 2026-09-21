# Posted strings — the audit list (every feature, no fixes)

> **Audience:** the owner, and the build that keys these strings next. **Status:** TRACKED
> — `docs/` is in git, so **secret NAMES only** (this file holds none).
> **Last verified: 2026-09-18** against `main` `b2ab14f` (v138 live), measured by an AST walk
> of every `.py` under `black_bloc/` (135 files, 86,360 lines) plus `black_bloc/settings_store.py`
> read through the running interpreter (`len(KEY_TYPES)` = **284** keys, **49** of them `text`/`json`,
> `namespace_of` over all 284 = **25** namespaces, exactly Discord's select cap).
>
> ⏸️ **This is a LIST, not a build.** Owner, 2026-09-18 09:2x, verbatim: *"for the audit make a
> list but don't execute fixes yet"*. Nothing in this file has been keyed; no code was changed.
> The design this list feeds is [`posted-strings-events-design.md`](posted-strings-events-design.md),
> whose **§A** supplies the pass-1 / pass-2 split used here verbatim. The pattern of what "keyed"
> looks like is the front door — [`front-door-design.md`](front-door-design.md),
> `frontdoor_title` / `frontdoor_text` / the three labels / `rehearsal_note`.
>
> ⚠️ **What was NOT checked.** Nothing was run against Discord and no browser rendered anything —
> no string below was seen on a card, a button or a post by eye. The site (`site/public/*.js`,
> `site/mock/`) was NOT swept: this audit is the words the **bot** posts, not the words the
> dashboard draws. Tests (`tests/`), `scripts/` and `docs/` were not swept. The `pass` column is
> RULE-BASED (see *How it was measured*) and was hand-checked on a sample of ~60 rows, not on all
> 3,456 — treat an individual `pass` cell as a proposal, not a measurement. The `proposed key`
> column is GENERATED from the constant name; it has not been checked for collisions against the
> 284 keys already in the registry, and the build must do that.
>
> ⚠️ **The YouTube UPLOADS half is excluded on purpose.** A build was deleting it in a separate
> worktree while this was measured ([`youtube-uploads-removal-design.md`](youtube-uploads-removal-design.md)),
> so its rows here are the file as it stood at `b2ab14f` and some of them will not exist by the
> time anyone reads this. The upload-only strings are marked in the YouTube table.

---

## 1. The counts

| Feature | literals found | already keyed | unkeyed | pass 1 | pass 2 | — |
|---|---:|---:|---:|---:|---:|---:|
| core | 380 | 1 | 213 | 60 | 153 | 167 |
| events | 283 | 3 | 231 | 96 | 135 | 52 |
| requests | 140 | 0 | 120 | 45 | 75 | 20 |
| modmail + front door | 229 | 7 | 210 | 65 | 145 | 19 |
| go-live | 82 | 4 | 77 | 23 | 54 | 5 |
| youtube | 103 | 1 | 80 | 21 | 59 | 23 |
| polls | 267 | 1 | 254 | 102 | 152 | 13 |
| birthdays | 59 | 1 | 57 | 26 | 31 | 2 |
| temp voice | 112 | 2 | 94 | 35 | 59 | 18 |
| role menus | 178 | 0 | 168 | 47 | 121 | 10 |
| pings | 189 | 3 | 176 | 48 | 128 | 13 |
| raid trains | 122 | 1 | 113 | 43 | 70 | 9 |
| applications | 183 | 0 | 164 | 35 | 129 | 19 |
| honeypot | 52 | 0 | 47 | 21 | 26 | 5 |
| automod | 73 | 0 | 70 | 22 | 48 | 3 |
| mod commands | 82 | 0 | 68 | 23 | 45 | 14 |
| chat | 568 | 0 | 237 | 39 | 198 | 331 |
| guides | 160 | 0 | 56 | 2 | 54 | 104 |
| posts | 97 | 0 | 76 | 10 | 66 | 21 |
| minutes | 82 | 3 | 63 | 20 | 43 | 19 |
| boot status / presence | 11 | 4 | 10 | 0 | 10 | 1 |
| errors | 4 | 3 | 4 | 0 | 4 | 0 |
| **TOTAL** | **3456** | **34** | **2588** | **783** | **1805** | **868** |

*"already keyed" counts only the `text` keys whose value is a WORD the bot posts. Fifteen more
`text`/`json` keys are state or configuration wearing a text type — `frontdoor_message_id`,
`frontdoor_shadow_hash`, `modmail_panel_shadow_message_id`, `chat_memory_model`,
`personality_pool_peer_url`, `automod_rules`, `timezone_choices`, `default_timezone`,
`events_where_link_aliases` and their siblings — and are excluded from the keyed column.*

*Every one of the 49 `text`/`json` keys was checked against a read site outside `settings_store.py`
(directly and through its `UPPER_CASE` alias constant). **All 49 are read somewhere** — there is no
key registered but never read. The read site is the `file:line` in each feature's "already keyed" row.*

### The five features with the most unkeyed pass-1 strings

| # | Feature | unkeyed pass 1 | unkeyed pass 2 | already keyed |
|---|---|---:|---:|---:|
| 1 | **polls** | **102** | 152 | 1 |
| 2 | **events** | **96** | 135 | 3 |
| 3 | **modmail + front door** | **65** | 145 | 7 |
| 4 | **core** | **60** | 153 | 1 |
| 5 | **pings** | **48** | 128 | 3 |

---

## 2. How it was measured

One AST walk (`ast.parse` per file, not a text grep) over every `.py` under `black_bloc/`,
collecting four shapes:

| Shape collected | Example | Rows |
|---|---|---:|
| module-level `NAME = "…"`, and every string inside a module-level tuple / list / dict | `DM_APPROVED = "Your event **{title}** was approved…"` | 3,199 |
| keyword arguments `label=` `placeholder=` `title=` `name=` `description=` `content=` `text=` `note=` `topic=` `reason=` on any call (`discord.ui.Button`, `discord.ui.TextInput`, `embed.add_field`, `create_text_channel`, …) | `discord.ui.Button(label="Apply now")` | 253 |
| positional string literals to anything named `send*` / `reply` / `respond` / `edit_message` | `await channel.send("…")` | 0 |
| f-strings in the same position, reduced to their literal parts | `f"**{title}** has ended."` | 4 |

A second AST pass recorded, for every `UPPER_CASE` constant, the **enclosing function and class**
of every place it is LOADED (4,601 use sites), including the class's base list — that is what tells a
modal's label from a card's heading.

Filters applied before anything reached a table: strings shorter than 3 characters; strings that are
all-lowercase-with-underscores (custom ids, log kinds, enum values); `ALL_CAPS` single tokens; URLs;
anything containing a regex group (`(?P<…>`), which is how every `DynamicItem` custom-id template is
written; and the files that are not member-facing by construction (`logkinds.py`, `logging_setup.py`,
`config.py`, `command_sync.py`, `command_visibility.py`, `intents.py`, `dbsnapshot.py`, `loops.py`,
`storage/`, and `api/` outside `api/tools/`).

**The `pass` column is decided by the constant's NAME, then corrected by its use sites**, in this order:

| Test | Result |
|---|---|
| name is a noise family (`__all__`, `INTENTS`, `FEATURE_PATHS`, `LOG_*`, `*_KIND`, `VIA_*`, `SEED`, `TOKENS`, …) | `—` |
| `app_commands.command(description=…)` or `app_commands.describe(…)` | `—` (Discord metadata, not a post) |
| `reason=` on a Discord API call | `—` (audit-log reason) |
| name starts `DM_` or ends `_ANNOUNCEMENT` `_TEMPLATE` `_NOTICE` `_TOPIC` `_OPENED` `_ENDED` `_REMINDER` `_LINE` `_HEAD` `_TEXT` `_BODY` `_SUFFIX` `_NAME` `_MARK` `_OPENER` | **1** |
| name contains `_MODAL`, or ends `_LABEL`/`_TITLE` and is used inside a `Modal` subclass | **2** (§A: modal labels are pass 2) |
| name ends `_BUTTON` `_LABEL(S)` `_PLACEHOLDER` `_TITLE` `_INTRO` `_FIELD*` `_FOOTER` `_HINT` `_NOTE` `_NAMES` `_WORDS` `_CARD*` `_EMBED*` | **1** (card and button furniture — §A keeps the draft card's headings and the picker placeholders in pass 1 even though the panel is ephemeral) |
| name is a refusal / answer family (`*_SAID`, `*_REFUSED`, `NO_*`, `NOT_*`, `ALREADY_*`, `UNKNOWN_*`, `CANNOT_*`, `*_FAILED`, `*_GONE`, `*_SAVED`, `*_DONE`, …) | **2** |
| anything else | **2** (a bare sentence constant is an answer until shown otherwise) |

**What this sweep MISSES.** Everything assembled at call time rather than declared:

- **f-strings built inside functions** — `f"#{n} · {title}"`, `f"{who} opened a ticket"`. Measured by
  the same AST walk: **1,204** `JoinedStr` nodes in `black_bloc/`, of which **355** carry at least two
  consecutive words of literal English. Only **4** of those sat in a `send()` position and reached a
  table above. Most of the other 351 are joins of constants already listed here, but this is the one
  bucket where a real posted sentence can hide, and it is the biggest single gap in this audit:
  **call it 150–250 genuinely new member-facing words.**
- **`.format()` and `"".join(...)` assemblies** — **1,069** `.format()` calls and **237** joins on a
  literal separator. Most `.format()` calls FILL a constant this audit already lists (that is how the
  templates work), so they add few new words; the joins are line-by-line card bodies in
  `events.py`, `polls.py`, `modmail.py` and `applications.py` and are where a stray `" · "` or
  `"and"` lives — **60–90** of them carry a word of their own.
- **Strings passed through a helper** (`say(...)`, `answer(...)`, `panels.retire(...)`) where the
  literal is a default argument on the helper rather than at the call — a handful, under **20**.
- **Words in data files, not code**: `black_bloc/personality_pool.json`, `black_bloc/posts_seed.json`,
  `black_bloc/guides_seed.json`. These are already editable — posts and guides are DB rows the site
  edits — so they are correctly absent, but they are words the bot posts and are named here so the
  count is not read as complete.
- **The site's own words** (`site/public/*.js`, `site/mock/server.mjs` labels) — out of scope by
  the rule's wording (*"every word the bot POSTS"*), but they are the other half of the surface.

So: **3,456 strings classified, ~230–360 more that this shape of sweep cannot see.**

---

## 3. The tables

One table per feature. Rows are **pass 1 first, then pass 2**; the `—` rows (log lines, command
descriptions, audit-log reasons, custom-id regexes) are COUNTED in §1 but not listed — they are not
keying work, and listing 867 of them would bury the 2,589 that are. Each feature's already-keyed
strings lead its table.

`proposed key` is `<namespace>_<constant name, lower-cased>`; ⚠️ the namespace head must be one of the
**25 that already exist** (§4), which is why the requests prefix is `request_` not `requests_`, polls
is `poll_`, birthdays is `birthday_`, minutes is `minutes_` (overridden onto `events`), and
`mod_*` / `error_*` / `boot_status_*` need an explicit `NAMESPACE_OVERRIDE` or `CORE_KEYS` entry.

### core

*380 strings — 1 keyed · 60 unkeyed pass 1 · 153 unkeyed pass 2 · 167 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/shadow.py:14` | *(the key's value)* | read from the store at render | **yes → `rehearsal_note`** (ns `core`, 1 read site(s)) | — | 1 |
| `black_bloc/actionlog.py:73` | Actor | card field name | no | `core_card_actor` | 1 |
| `black_bloc/actionlog.py:75` | Target | card field name | no | `core_card_target` | 1 |
| `black_bloc/actionlog.py:77` | Reason | card field name | no | `core_card_reason` | 1 |
| `black_bloc/actionlog.py:80` | Details | card field name | no | `core_card_details` | 1 |
| `black_bloc/api/tools/rolemenus.py:63` | A role menu needs a short name and a heading, so nothing was created. Fill both … | channel / role name | no | `core_needs_a_name` | 1 |
| `black_bloc/cogs/core.py:49` | (staff) | channel post | no | `core_staff_suffix` | 1 |
| `black_bloc/cogs/core.py:60` | ⏎ *{count} command(s) are not listed because their feature is turned off. A Lead… | card description | no | `core_hidden_note` | 1 |
| `black_bloc/cogs/core.py:292` | Pong — gateway latency ms | channel post / DM | no | `core_line_pong_gateway_latency_ms` | 1 |
| `black_bloc/cogs/core.py:298` | **Black Bloc** v — moderation and content bot. | channel post / DM | no | `core_line_black_bloc_v_moderation_and_content_bot` | 1 |
| `black_bloc/cogs/core.py:385` | Who counts as staff, and where Black Bloc talks | card title | no | `core_roles_channels_title` | 1 |
| `black_bloc/cogs/core.py:386` | How Black Bloc looks | card title | no | `core_looks_title` | 1 |
| `black_bloc/cogs/core.py:387` | Panels and commands | card title | no | `core_panels_title` | 1 |
| `black_bloc/cogs/core.py:389` | The {group} settings | card title | no | `core_group_title` | 1 |
| `black_bloc/cogs/core.py:409` | **How long a panel stays open** — {count} panels have their own number, and the … | card description | no | `core_panel_minutes_intro` | 1 |
| `black_bloc/cogs/core.py:413` | Every feature keeps every line on the dashboard's Logs page. This decides how mu… | card description | no | `core_levels_intro` | 1 |
| `black_bloc/cogs/core.py:417` | {count} setting(s) in **{group}**. Pick one to see what it is and change it. | card description | no | `core_group_intro` | 1 |
| `black_bloc/cogs/core.py:423` | A whole number | card field | no | `core_number_label` | 1 |
| `black_bloc/cogs/core.py:428` | A hex colour like #4eefff | card field | no | `core_colour_label` | 1 |
| `black_bloc/handoff.py:44` | Your request **#{request_id}** on **{guild}** is now event **#{event_id}** — sta… | DM | no | `core_request_to_event_dm` | 1 |
| `black_bloc/handoff.py:48` | Your event **#{event_id}** on **{guild}** is now request **#{request_id}** inste… | DM | no | `core_event_to_request_dm` | 1 |
| `black_bloc/handoff.py:53` | → event **#{event_id}** | channel post | no | `core_request_moved_line` | 1 |
| `black_bloc/handoff.py:54` | → request **#{request_id}** | channel post | no | `core_event_moved_line` | 1 |
| `black_bloc/handoff.py:55` | → {what} **#{ident}** — {who} said yes to filing it. | channel post | no | `core_ticket_moved_line` | 1 |
| `black_bloc/handoff.py:56` | {who} said no — nothing was filed and the ticket stays private. | channel post | no | `core_ticket_said_no_line` | 1 |
| `black_bloc/handoff.py:57` | {who} has been asked by DM whether this ticket may be filed as a {what}. No answ… | channel post | no | `core_ticket_asked_line` | 1 |
| `black_bloc/handoff.py:67` | What staff would file | card field | no | `core_ask_title_field` | 1 |
| `black_bloc/handoff.py:68` | In your words | card field | no | `core_ask_body_field` | 1 |
| `black_bloc/handoff.py:69` | Black Bloc · nothing is filed unless you say yes | card description | no | `core_ask_footer` | 1 |
| `black_bloc/handoff.py:73` | What should it be called? | card field | no | `core_ask_title_label` | 1 |
| `black_bloc/handoff.py:74` | What should it say? (the member sees this before they answer) | card field | no | `core_ask_body_label` | 1 |
| `black_bloc/handoff.py:89` | Staff would like to file your ticket | card title | no | `core_confirm_title` | 1 |
| `black_bloc/handoff.py:90` | Staff on **{guild}** would like to file your ticket **#{ticket_id}** as a {what}… | channel post | no | `core_confirm_body` | 1 |
| `black_bloc/logs_panel.py:20` | This log has gone quiet — press Logs again | card description | no | `core_panel_timeout_footer` | 1 |
| `black_bloc/panels.py:16` | {shown} of {total} — the rest are on the site | select placeholder | no | `core_capped_placeholder` | 1 |
| `black_bloc/panels.py:17` | Are you sure? | card title | no | `core_confirm_title_2` | 1 |
| `black_bloc/selftest.py:45` | selftest: {ok} ok, {failed} failed, {posted} messages posted (purge in {minutes}… | channel post | no | `core_boot_line` | 1 |
| `black_bloc/selftest.py:75` | pool v{version} here; GABI does not say its pool version yet | card field | no | `core_pool_no_field` | 1 |
| `black_bloc/selftest_panels.py:19` | {name} did not build an embed and a view | channel post | no | `core_not_a_card` | 1 |
| `black_bloc/selftest_panels.py:23` | Black Bloc self-test | channel post | no | `core_selftest_mark` | 1 |
| `black_bloc/selftest_panels.py:24` | A self-test card. It is deleted again in a few minutes. | card description | no | `core_selftest_note` | 1 |
| `black_bloc/settings_panel.py:28` | Black Bloc's settings for this server | card title | no | `core_panel_title` | 1 |
| `black_bloc/settings_panel.py:29` | This panel has gone quiet — run /settings again | card description | no | `core_panel_timeout_footer_2` | 1 |
| `black_bloc/settings_panel.py:114` | The front door | card field | no | `core_mode_labels` | 1 |
| `black_bloc/settings_panel.py:128` | The settings no feature panel owns. All {total} of them are on the site, and eve… | card description | no | `core_root_intro` | 1 |
| `black_bloc/settings_panel.py:133` | **{label}** — {state} · `/{command}` to change | channel post | no | `core_mode_line` | 1 |
| `black_bloc/settings_panel.py:147` | Turn a feature back on… | select placeholder | no | `core_back_on_placeholder` | 1 |
| `black_bloc/settings_panel.py:152` | How long a panel stays open… | select placeholder | no | `core_panel_minutes_placeholder` | 1 |
| `black_bloc/settings_panel.py:154` | Skin tone… | select placeholder | no | `core_skin_tone_placeholder` | 1 |
| `black_bloc/settings_panel.py:156` | **{key}** — {value} | channel post | no | `core_key_line` | 1 |
| `black_bloc/settings_panel.py:157` | Black Bloc's own default is {value}. | channel post | no | `core_key_default_line` | 1 |
| `black_bloc/settings_panel.py:171` | Are you sure? | card title | no | `core_confirm_title_3` | 1 |
| `black_bloc/settings_panel.py:188` | Find a setting | card title | no | `core_find_title` | 1 |
| `black_bloc/settings_panel.py:189` | Part of the setting's name | card field | no | `core_find_label` | 1 |
| `black_bloc/settings_panel.py:202` | The self-test | card title | no | `core_selftest_title` | 1 |
| `black_bloc/settings_panel.py:203` | Black Bloc exercises itself against this server: every setting's channel and rol… | card description | no | `core_selftest_intro` | 1 |
| `black_bloc/settings_panel.py:230` | Hide a feature's command while it is off | card field | no | `core_hide_on_label` | 1 |
| `black_bloc/settings_panel.py:231` | Leave every command showing | card field | no | `core_hide_off_label` | 1 |
| `black_bloc/settings_panel.py:232` | Write a line for every operator-token read | card field | no | `core_operator_log_on_label` | 1 |
| `black_bloc/settings_panel.py:233` | Leave operator-token reads unlogged | card field | no | `core_operator_log_off_label` | 1 |
| `black_bloc/settings_panel.py:311` | Back to the group | card field | no | `core_key_back_label` | 1 |
| `black_bloc/actionlog.py:36` | Nothing has been logged for this yet. | ephemeral answer | no | `core_nothing_yet` | 2 |
| `black_bloc/actionlog.py:37` | Nothing important has been logged for this yet. | ephemeral answer | no | `core_nothing_important` | 2 |
| `black_bloc/actionlog.py:38` | The whole log, searchable, is on the dashboard: {origin}/{page} | ephemeral answer | no | `core_footer` | 2 |
| `black_bloc/actionlog.py:39` | Black Bloc cannot reach its own database right now, so it cannot read the log. W… | ephemeral answer | no | `core_logs_db_down` | 2 |
| `black_bloc/api/tools/chat_memory.py:34` | Black Bloc is not remembering anybody on this server, so there is nothing here y… | ephemeral answer | no | `core_memory_is_off` | 2 |
| `black_bloc/api/tools/chat_memory.py:38` | This server keeps what Black Bloc remembers about a member private to that membe… | ephemeral answer | no | `core_contents_are_private` | 2 |
| `black_bloc/api/tools/chat_memory.py:45` | Black Bloc remembers nothing about that member on this server, so there was noth… | ephemeral answer | no | `core_no_such_profile` | 2 |
| `black_bloc/api/tools/chat_memory.py:49` | Cleared. Black Bloc remembers nothing about {who} here. | ephemeral answer | no | `core_forgot_said` | 2 |
| `black_bloc/api/tools/rolemenus.py:55` | This server has no role menu called **{name}**, so nothing was changed. The role… | ephemeral answer | no | `core_no_such_menu` | 2 |
| `black_bloc/api/tools/rolemenus.py:59` | This server already has a role menu called **{name}**, so nothing was created. P… | ephemeral answer | no | `core_name_taken` | 2 |
| `black_bloc/api/tools/rolemenus.py:67` | **{given}** is not a way a role menu can work, so nothing was changed. It is one… | ephemeral answer | no | `core_bad_mode` | 2 |
| `black_bloc/api/tools/rolemenus.py:71` | **{role_id}** is not a role in this server any more, so the menu was left as it … | ephemeral answer | no | `core_no_such_role` | 2 |
| `black_bloc/api/tools/rolemenus.py:75` | Black Bloc cannot hand out **{name}**, so it was not added. That role is either … | ephemeral answer | no | `core_unassignable` | 2 |
| `black_bloc/api/tools/rolemenus.py:80` | **{name}** is a staff-assigned menu, so there is no panel to post — nobody gives… | ephemeral answer | no | `core_staff_menu_not_posted` | 2 |
| `black_bloc/api/tools/rolemenus.py:84` | **{name}** has no roles on it yet, so there is nothing to post. Add one first. | ephemeral answer | no | `core_nothing_to_post` | 2 |
| `black_bloc/api/tools/rolemenus.py:87` | **{channel_id}** is not a channel Black Bloc can see, so nothing was posted. Pic… | ephemeral answer | no | `core_no_such_channel` | 2 |
| `black_bloc/api/tools/rolemenus.py:91` | One of the roles on that menu arrived in a shape Black Bloc could not read, so n… | ephemeral answer | no | `core_bad_option` | 2 |
| `black_bloc/api/tools/rolemenus.py:96` | **{given}** is not a state a role request can be in, so nothing was listed. They… | ephemeral answer | no | `core_unknown_status` | 2 |
| `black_bloc/api/tools/rolemenus.py:99` | **{given}** is not on or off, so nothing was changed. It is a fault in the page … | ephemeral answer | no | `core_bad_approval` | 2 |
| `black_bloc/api/tools/rolemenus.py:107` | **{name}** is not posted anywhere yet, so there is no panel to move. Post it fro… | ephemeral answer | no | `core_not_posted_yet` | 2 |
| `black_bloc/api/tools/rolemenus.py:111` | Black Bloc could not take **{name}**'s old panel down, so it is still where it w… | ephemeral answer | no | `core_panel_not_moved` | 2 |
| `black_bloc/api/tools/rolemenus.py:116` | A denied request needs one line the member is sent, so nothing was done. Say why… | ephemeral answer | no | `core_deny_needs_a_reason` | 2 |
| `black_bloc/api/tools/rolemenus.py:120` | **{name}** has no panel up right now, so there was nothing to take down. Post it… | ephemeral answer | no | `core_nothing_to_unpost` | 2 |
| `black_bloc/api/tools/rolemenus.py:124` | Black Bloc could not take **{name}**'s panel down, so it is still where it was. … | ephemeral answer | no | `core_panel_stuck` | 2 |
| `black_bloc/api/tools/rolemenus.py:129` | **{name}**'s panel is down. The menu and its roles are untouched and nobody lose… | ephemeral answer | no | `core_panel_taken_down` | 2 |
| `black_bloc/cogs/core.py:47` | **{key}** is no longer set, so Black Bloc is back to its own default for it. | ephemeral answer | no | `core_cleared` | 2 |
| `black_bloc/cogs/core.py:48` | **{key}** was not set for this server, so nothing changed. | ephemeral answer | no | `core_not_set` | 2 |
| `black_bloc/cogs/core.py:50` | Every command Black Bloc can run here. The ones marked (staff) need the Manage S… | ephemeral answer | no | `core_help_header` | 2 |
| `black_bloc/cogs/core.py:54` | No command matches **{filter}**, so there is nothing to list. Run `/help` with n… | ephemeral answer | no | `core_no_match` | 2 |
| `black_bloc/cogs/core.py:58` | · [guide]({url}) | ephemeral answer | no | `core_guide_clause` | 2 |
| `black_bloc/cogs/core.py:59` | All the guides | ephemeral answer | no | `core_all_the_guides` | 2 |
| `black_bloc/cogs/core.py:67` | **{key}** is now {value}. | ephemeral answer | no | `core_saved` | 2 |
| `black_bloc/cogs/core.py:390` | {key} | modal title or field | no | `core_key_title` | 2 |
| `black_bloc/cogs/core.py:392` | **About Me** — {value} | ephemeral answer | no | `core_bio_now` | 2 |
| `black_bloc/cogs/core.py:393` | **status** — {value} | ephemeral answer | no | `core_status_now` | 2 |
| `black_bloc/cogs/core.py:394` | **skin tone** — {value} | ephemeral answer | no | `core_skin_tone_now` | 2 |
| `black_bloc/cogs/core.py:395` | **the status loop last succeeded** — {when} | ephemeral answer | no | `core_status_loop_ok` | 2 |
| `black_bloc/cogs/core.py:396` | **the status loop** — it has not succeeded yet in this process | ephemeral answer | no | `core_status_loop_never` | 2 |
| `black_bloc/cogs/core.py:397` | **its last error** — {error} | ephemeral answer | no | `core_status_loop_error` | 2 |
| `black_bloc/cogs/core.py:398` | **the hosting bill** — {value} US dollars a month | ephemeral answer | no | `core_hosting_now` | 2 |
| `black_bloc/cogs/core.py:399` | **an operator-token read leaves a log line** — {value} | ephemeral answer | no | `core_operator_log_now` | 2 |
| `black_bloc/cogs/core.py:400` | Whether an operator-token read leaves a log line is changed by somebody with Man… | ephemeral answer | no | `core_operator_log_is_for_a_lead` | 2 |
| `black_bloc/cogs/core.py:404` | Nothing was changed: whether an operator-token read leaves a log line is changed… | ephemeral answer | no | `core_operator_log_refused` | 2 |
| `black_bloc/cogs/core.py:418` | **{label}** takes a whole number and you typed `{given}`, so nothing was changed… | ephemeral answer | no | `core_not_a_number` | 2 |
| `black_bloc/cogs/core.py:424` | A whole number from {low} to {high} | ephemeral answer | no | `core_number_both` | 2 |
| `black_bloc/cogs/core.py:425` | A whole number, no more than {high} | ephemeral answer | no | `core_number_max` | 2 |
| `black_bloc/cogs/core.py:426` | A whole number, at least {low} | ephemeral answer | no | `core_number_min` | 2 |
| `black_bloc/cogs/core.py:427` | The words | modal title or field | no | `core_text_label` | 2 |
| `black_bloc/directory.py:17` | ## The channels of this server ⏎ This is the whole list, and it is the only list… | ephemeral answer | no | `core_directory_heading` | 2 |
| `black_bloc/directory.py:22` | ## The channels of this server ⏎ You have not been given the channel list, so na… | ephemeral answer | no | `core_directory_none` | 2 |
| `black_bloc/emoji.py:19` | 261D 26F9 270A 270B 270C 270D 1F385 1F3C2 1F3C3 1F3C4 1F3C7 1F3CA 1F3CB 1F3CC 1F… | ephemeral answer | no | `core_modifier_base` | 2 |
| `black_bloc/handoff.py:28` | Send to events… | ephemeral answer | no | `core_send_to_events` | 2 |
| `black_bloc/handoff.py:29` | Not an event — make it a request | ephemeral answer | no | `core_not_an_event` | 2 |
| `black_bloc/handoff.py:30` | Make this a request… | ephemeral answer | no | `core_make_a_request` | 2 |
| `black_bloc/handoff.py:31` | Make this an event… | ephemeral answer | no | `core_make_an_event` | 2 |
| `black_bloc/handoff.py:32` | Open a ticket with them… | ephemeral answer | no | `core_open_a_ticket` | 2 |
| `black_bloc/handoff.py:33` | Make the event… | ephemeral answer | no | `core_make_the_event` | 2 |
| `black_bloc/handoff.py:34` | Yes, file it | ephemeral answer | no | `core_confirm_yes` | 2 |
| `black_bloc/handoff.py:35` | No, keep it private | ephemeral answer | no | `core_confirm_no` | 2 |
| `black_bloc/handoff.py:40` | Filed as request #{request_id} by <@{user_id}> | ephemeral answer | no | `core_filed_as` | 2 |
| `black_bloc/handoff.py:41` | Filed from ticket #{ticket_id} by <@{user_id}> | ephemeral answer | no | `core_from_ticket` | 2 |
| `black_bloc/handoff.py:42` | (filed from event #{event_id}) | ephemeral answer | no | `core_from_event` | 2 |
| `black_bloc/handoff.py:52` | filed as request #{request_id} instead | ephemeral answer | no | `core_event_to_request_why` | 2 |
| `black_bloc/handoff.py:61` | {who} said yes. **{title}** still needs a date — press **Make the event…** to pi… | ephemeral answer | no | `core_ticket_said_yes_event` | 2 |
| `black_bloc/handoff.py:71` | {who} has been asked by DM whether this may be filed as a {what}. | ephemeral answer | no | `core_asked_said` | 2 |
| `black_bloc/handoff.py:75` | File this ticket as a request | modal title | no | `core_ask_modal_title` | 2 |
| `black_bloc/handoff.py:75` | File this ticket as an event | modal title | no | `core_ask_modal_title_2` | 2 |
| `black_bloc/handoff.py:79` | <@{user_id}> is not somebody Black Bloc can see on this server any more, so no t… | ephemeral answer | no | `core_no_such_member` | 2 |
| `black_bloc/handoff.py:83` | Request #{request_id} | ephemeral answer | no | `core_ticket_subject` | 2 |
| `black_bloc/handoff.py:84` | This is about your request **#{request_id}** — *{what}* ⏎ ⏎ > {why} ⏎ ⏎ Tell us … | ephemeral answer | no | `core_ticket_quote` | 2 |
| `black_bloc/handoff.py:95` | Thank you — it has been filed and staff can see it now. | ephemeral answer | no | `core_confirm_yes_said` | 2 |
| `black_bloc/handoff.py:96` | Nothing was filed. Your ticket stays private. | ephemeral answer | no | `core_confirm_no_said` | 2 |
| `black_bloc/handoff.py:97` | Black Bloc could not DM {who}, so nothing was asked and nothing was filed. Their… | DM | no | `core_confirm_dm_failed` | 2 |
| `black_bloc/handoff.py:102` | **Send to…** is switched off on this server, so nothing was moved. It needs `han… | ephemeral answer | no | `core_handoff_off` | 2 |
| `black_bloc/handoff.py:107` | Request **#{request_id}** is already **{status}**, so there is nothing left to s… | ephemeral answer | no | `core_already_final` | 2 |
| `black_bloc/handoff.py:111` | Event **#{event_id}** is already **{status}**, so there is nothing left to send … | ephemeral answer | no | `core_event_already_decided` | 2 |
| `black_bloc/handoff.py:114` | Black Bloc already asked {who} — it is waiting on their answer until {when}. Not… | ephemeral answer | no | `core_already_asked` | 2 |
| `black_bloc/handoff.py:118` | {who} already said yes to an event. Press **Make the event…** in the ticket to p… | ephemeral answer | no | `core_already_said_yes` | 2 |
| `black_bloc/handoff.py:122` | Ticket **#{ticket_id}** has already been filed as {what} **#{ident}**, so nothin… | ephemeral answer | no | `core_already_moved` | 2 |
| `black_bloc/handoff.py:126` | This question is no longer waiting on an answer — either it has run out of time … | ephemeral answer | no | `core_confirm_gone` | 2 |
| `black_bloc/handoff.py:130` | That ticket is no longer there, so nothing was filed. | ephemeral answer | no | `core_no_such_ticket` | 2 |
| `black_bloc/handoff.py:131` | This is a **practice** ticket, so there is no member to ask and nothing was file… | ephemeral answer | no | `core_practice_ticket` | 2 |
| `black_bloc/logs_panel.py:17` | Show more | ephemeral answer | no | `core_more` | 2 |
| `black_bloc/logs_panel.py:18` | Important only | ephemeral answer | no | `core_only_important` | 2 |
| `black_bloc/logs_panel.py:19` | Show everything | ephemeral answer | no | `core_everything` | 2 |
| `black_bloc/panels.py:18` | Keep it | ephemeral answer | no | `core_keep_it` | 2 |
| `black_bloc/selftest.py:38` | /api | ephemeral answer | no | `core_api_prefix` | 2 |
| `black_bloc/selftest.py:39` | /api/auth/login | ephemeral answer | no | `core_skip_paths` | 2 |
| `black_bloc/selftest.py:39` | /api/auth/callback | ephemeral answer | no | `core_skip_paths_2` | 2 |
| `black_bloc/selftest.py:39` | /api/auth/logout | ephemeral answer | no | `core_skip_paths_3` | 2 |
| `black_bloc/selftest.py:44` | not set | ephemeral answer | no | `core_not_set_2` | 2 |
| `black_bloc/selftest.py:46` | selftest: FAILED {name} — {detail} | ephemeral answer | no | `core_boot_failure` | 2 |
| `black_bloc/selftest.py:47` | A self-test is already running (started {started}, {done} of {total} checks done… | ephemeral answer | no | `core_busy` | 2 |
| `black_bloc/selftest.py:52` | The self-test has nowhere to post: selftest_channel_id is not set and Black Bloc… | ephemeral answer | no | `core_no_channel` | 2 |
| `black_bloc/selftest.py:57` | Black Bloc has no self-test run numbered {run_id} for this server, so there was … | ephemeral answer | no | `core_no_run` | 2 |
| `black_bloc/selftest.py:61` | the self-test itself | ephemeral answer | no | `core_runner_check` | 2 |
| `black_bloc/selftest.py:62` | The self-test stopped part way through — {detail}. That is a fault in the test r… | ephemeral answer | no | `core_runner_failed` | 2 |
| `black_bloc/selftest.py:73` | python scripts/sync_personality_pool.py | ephemeral answer | no | `core_pool_fix` | 2 |
| `black_bloc/selftest.py:74` | pool v{version} here; no peer address is set, so nothing was asked | ephemeral answer | no | `core_pool_no_peer` | 2 |
| `black_bloc/selftest.py:76` | could not reach GABI's health route ({reason}) — the pool itself is fine | ephemeral answer | no | `core_pool_unreachable` | 2 |
| `black_bloc/selftest.py:77` | GABI is on personality pool v{theirs}, this bot on v{mine}, so {ahead} is ahead … | ephemeral answer | no | `core_pool_behind` | 2 |
| `black_bloc/selftest.py:81` | GABI and this bot say the same pool version, and she lists {theirs} moods where … | ephemeral answer | no | `core_pool_count` | 2 |
| `black_bloc/selftest.py:85` | GABI and this bot say the same pool version, but her roster reads {theirs} where… | ephemeral answer | no | `core_pool_roster` | 2 |
| `black_bloc/selftest_panels.py:18` | the {name} cog is not loaded, so its panel cannot be built | ephemeral answer | no | `core_no_cog` | 2 |
| `black_bloc/selftest_panels.py:20` | posted; {buttons} button(s), {selects} select(s) | ephemeral answer | no | `core_posted` | 2 |
| `black_bloc/selftest_panels.py:21` | posted; {what} | ephemeral answer | no | `core_sent` | 2 |
| `black_bloc/settings_panel.py:87` | Where staff talk — and who counts as staff | ephemeral answer | no | `core_key_purpose` | 2 |
| `black_bloc/settings_panel.py:87` | Where Black Bloc repeats what it did | ephemeral answer | no | `core_key_purpose_2` | 2 |
| `black_bloc/settings_panel.py:87` | Where moderation actions are written down | ephemeral answer | no | `core_key_purpose_3` | 2 |
| `black_bloc/settings_panel.py:87` | Where the role menus are posted | ephemeral answer | no | `core_key_purpose_4` | 2 |
| `black_bloc/settings_panel.py:94` | answering DMs | ephemeral answer | no | `core_modmail_answering` | 2 |
| `black_bloc/settings_panel.py:95` | not answering DMs | ephemeral answer | no | `core_modmail_not_answering` | 2 |
| `black_bloc/settings_panel.py:132` | **What each feature is doing** — a mode is changed on its own panel: | ephemeral answer | no | `core_modes_header` | 2 |
| `black_bloc/settings_panel.py:134` | ⚠️ **{count} command(s) are hidden right now** because their feature is off: {na… | ephemeral answer | no | `core_hidden_some` | 2 |
| `black_bloc/settings_panel.py:138` | Every command is showing. | ephemeral answer | no | `core_hidden_none` | 2 |
| `black_bloc/settings_panel.py:139` | Hiding a command while its feature is off is switched off altogether, so every c… | ephemeral answer | no | `core_hiding_off` | 2 |
| `black_bloc/settings_panel.py:143` | **{stored}** of {total} settings are set away from Black Bloc's own default here… | ephemeral answer | no | `core_stored_count` | 2 |
| `black_bloc/settings_panel.py:145` | A setting group… | ephemeral answer | no | `core_pick_a_group` | 2 |
| `black_bloc/settings_panel.py:146` | A setting… | ephemeral answer | no | `core_pick_a_setting` | 2 |
| `black_bloc/settings_panel.py:148` | {label} — turn it on | ephemeral answer | no | `core_back_on_option` | 2 |
| `black_bloc/settings_panel.py:153` | {key} — {minutes} minute(s) | ephemeral answer | no | `core_panel_minutes_option` | 2 |
| `black_bloc/settings_panel.py:158` | It takes a whole number from {low} to {high}. | ephemeral answer | no | `core_key_bounds_both` | 2 |
| `black_bloc/settings_panel.py:159` | It takes a whole number no larger than {high}. | ephemeral answer | no | `core_key_bounds_max` | 2 |
| `black_bloc/settings_panel.py:160` | It takes a whole number of at least {low}. | ephemeral answer | no | `core_key_bounds_min` | 2 |
| `black_bloc/settings_panel.py:161` | The rule book is edited on `/automod` ▸ **A rule…**, so there is nothing to chan… | ephemeral answer | no | `core_rules_elsewhere` | 2 |
| `black_bloc/settings_panel.py:164` | ⚠️ **{count} are stored**, which is more than one Discord picker can edit at onc… | ephemeral answer | no | `core_list_too_long` | 2 |
| `black_bloc/settings_panel.py:169` | **Put the default back** makes **{key}** {value}. | ephemeral answer | no | `core_put_back_makes` | 2 |
| `black_bloc/settings_panel.py:173` | Putting the default back points the staff channel at {channel}. That changes who… | ephemeral answer | no | `core_confirm_staff_channel` | 2 |
| `black_bloc/settings_panel.py:179` | Re-pointing the staff channel, the log channel, the moderation log or the role-m… | ephemeral answer | no | `core_core_keys_are_for_a_lead` | 2 |
| `black_bloc/settings_panel.py:184` | Black Bloc's presence is not running in this process, so there is nothing to re-… | ephemeral answer | no | `core_presence_not_running` | 2 |
| `black_bloc/settings_panel.py:190` | Nothing in **{group}** has **{needle}** in its name, so the list is unchanged. P… | ephemeral answer | no | `core_nothing_matches` | 2 |
| `black_bloc/settings_panel.py:194` | **{state}** from now on. Discord's own command list catches up within about a mi… | ephemeral answer | no | `core_hide_changed` | 2 |
| `black_bloc/settings_panel.py:198` | A feature's command is hidden while it is off | ephemeral answer | no | `core_hide_on_state` | 2 |
| `black_bloc/settings_panel.py:199` | Every command shows all the time | ephemeral answer | no | `core_hide_off_state` | 2 |
| `black_bloc/settings_panel.py:200` | That applies the next time `/settings` is run, not to this panel. | ephemeral answer | no | `core_panel_minutes_next_time` | 2 |
| `black_bloc/settings_panel.py:208` | **At every boot** — yes, so a deploy proves itself without anybody looking. | ephemeral answer | no | `core_selftest_boot_on` | 2 |
| `black_bloc/settings_panel.py:209` | **At every boot** — no, so it only runs when somebody asks. | ephemeral answer | no | `core_selftest_boot_off` | 2 |
| `black_bloc/settings_panel.py:210` | **Where the cards go** — {value} | ephemeral answer | no | `core_selftest_where` | 2 |
| `black_bloc/settings_panel.py:211` | It has not run yet in this server. | ephemeral answer | no | `core_selftest_never` | 2 |
| `black_bloc/settings_panel.py:212` | **The last run** — started {started} · {ok} ok · {failed} failed · {posted} mess… | ephemeral answer | no | `core_selftest_last` | 2 |
| `black_bloc/settings_panel.py:215` | Its messages were deleted {at}. | ephemeral answer | no | `core_selftest_purged` | 2 |
| `black_bloc/settings_panel.py:216` | {count} message(s) are still waiting to be deleted. | ephemeral answer | no | `core_selftest_waiting` | 2 |
| `black_bloc/settings_panel.py:217` | ⚠️ **{name}** — {detail} | ephemeral answer | no | `core_selftest_failure` | 2 |
| `black_bloc/settings_panel.py:218` | A run is going right now, so **Run the self-test** is not drawn. | ephemeral answer | no | `core_selftest_is_running` | 2 |
| `black_bloc/settings_panel.py:219` | The self-test ran: **{ok} ok, {failed} failed**, {posted} message(s) posted. The… | ephemeral answer | no | `core_selftest_done` | 2 |
| `black_bloc/settings_panel.py:223` | Nothing failed. | ephemeral answer | no | `core_selftest_all_well` | 2 |
| `black_bloc/settings_panel.py:224` | The self-test has nothing waiting to be deleted, so nothing was done. Its last r… | ephemeral answer | no | `core_selftest_nothing_to_purge` | 2 |
| `black_bloc/settings_panel.py:228` | {count} self-test message(s) deleted. | ephemeral answer | no | `core_selftest_purge_done` | 2 |
| `black_bloc/settings_panel.py:234` | Turn {key} on | ephemeral answer | no | `core_turn_it_on` | 2 |
| `black_bloc/settings_panel.py:235` | Turn {key} off | ephemeral answer | no | `core_turn_it_off` | 2 |
| `black_bloc/shadow.py:15` | Rehearsal — this is where it would go: {channel} | ephemeral answer | no | `core_note_default` | 2 |
| `black_bloc/timezones.py:10` | America/Phoenix | ephemeral answer | no | `core_default_tz` | 2 |
| `black_bloc/timezones.py:11` | %Y-%m-%d %H:%M | ephemeral answer | no | `core_start_format` | 2 |

### events

*283 strings — 3 keyed · 96 unkeyed pass 1 · 135 unkeyed pass 2 · 52 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/events.py:1750` | *(the key's value)* | read from the store at render | **yes → `events_moved_line`** (ns `events`, 6 read site(s)) | — | 1 |
| `black_bloc/events.py:1484` | *(the key's value)* | read from the store at render | **yes → `events_scheduled_name_template`** (ns `events`, 2 read site(s)) | — | 1 |
| `black_bloc/events.py:58` | *(the key's value)* | read from the store at render | **yes → `events_where_hint`** (ns `events`, 2 read site(s)) | — | 1 |
| `black_bloc/api/tools/events.py:67` | The public announcement still says what it said before; Black Bloc does not rewr… | channel post | no | `events_announcement_stale` | 1 |
| `black_bloc/cogs/community/events.py:239` | Approve | card field | no | `events_decision_labels` | 1 |
| `black_bloc/cogs/community/events.py:239` | Deny | card field | no | `events_decision_labels_2` | 1 |
| `black_bloc/cogs/community/events.py:252` | Events — settings | card title | no | `events_settings_title` | 1 |
| `black_bloc/cogs/community/events.py:253` | Propose an event | button label | no | `events_propose_button` | 1 |
| `black_bloc/cogs/community/events.py:254` | Settings | button label | no | `events_settings_button` | 1 |
| `black_bloc/cogs/community/events.py:255` | Numbers… | button label | no | `events_numbers_button` | 1 |
| `black_bloc/cogs/community/events.py:256` | Forget… | button label | no | `events_forget_button` | 1 |
| `black_bloc/cogs/community/events.py:258` | Forget which one? | select placeholder | no | `events_forget_placeholder` | 1 |
| `black_bloc/cogs/community/events.py:259` | Scheduled events: {state} | button label | no | `events_scheduled_button` | 1 |
| `black_bloc/cogs/community/events.py:260` | How events behave… | select placeholder | no | `events_mode_placeholder` | 1 |
| `black_bloc/cogs/community/events.py:261` | Where review channels go (pick nothing to forget it) | select placeholder | no | `events_category_placeholder` | 1 |
| `black_bloc/cogs/community/events.py:262` | Where approved events are announced | select placeholder | no | `events_announce_placeholder` | 1 |
| `black_bloc/cogs/community/events.py:263` | Role mentioned when one is announced | select placeholder | no | `events_ping_placeholder` | 1 |
| `black_bloc/cogs/community/events.py:287` | One line the requester will be sent | card field | no | `events_note_labels` | 1 |
| `black_bloc/cogs/community/events.py:287` | One line the requester will be sent | card field | no | `events_note_labels_2` | 1 |
| `black_bloc/cogs/community/events.py:1148` | Back | button label | no | `events_button_back` | 1 |
| `black_bloc/cogs/community/events.py:1335` | Refresh | button label | no | `events_button_refresh` | 1 |
| `black_bloc/cogs/community/events.py:1343` | Back | button label | no | `events_button_back_2` | 1 |
| `black_bloc/cogs/community/events.py:1359` | Logs | button label | no | `events_button_logs` | 1 |
| `black_bloc/events.py:126` | My time zone | button label | no | `events_zone_button` | 1 |
| `black_bloc/events.py:141` | A new event is on the calendar. | channel post | no | `events_announce_head` | 1 |
| `black_bloc/events.py:215` | Where | button label | no | `events_where_button` | 1 |
| `black_bloc/events.py:225` | Open link | button label | no | `events_where_open_link_button` | 1 |
| `black_bloc/events.py:344` | — ⚠️ {note} | channel post | no | `events_where_note_mark` | 1 |
| `black_bloc/events.py:345` | *{hint}* | channel post | no | `events_where_hint_mark` | 1 |
| `black_bloc/events.py:456` | Who | card field name | no | `events_card_who` | 1 |
| `black_bloc/events.py:457` | Status | card field name | no | `events_card_status` | 1 |
| `black_bloc/events.py:458` | How long | card field name | no | `events_card_how_long` | 1 |
| `black_bloc/events.py:459` | When | card field name | no | `events_card_when` | 1 |
| `black_bloc/events.py:462` | Where | card field name | no | `events_card_where` | 1 |
| `black_bloc/events.py:464` | Why not | card field name | no | `events_card_why_not` | 1 |
| `black_bloc/events.py:467` | Now | card field name | no | `events_card_now` | 1 |
| `black_bloc/events.py:552` | An event needs a name, so nothing was submitted. Put something in the Title box … | card title | no | `events_no_title` | 1 |
| `black_bloc/events.py:566` | Propose an event — draft | card title | no | `events_draft_title` | 1 |
| `black_bloc/events.py:572` | Times are read in **{tz}** — the server's default. Press **Time zone** if that i… | card description | no | `events_draft_zone_hint` | 1 |
| `black_bloc/events.py:577` | Title & details | button label | no | `events_text_button` | 1 |
| `black_bloc/events.py:578` | Time zone | button label | no | `events_zone_panel_button` | 1 |
| `black_bloc/events.py:579` | Submit | button label | no | `events_submit_button` | 1 |
| `black_bloc/events.py:581` | Where is it? | card title | no | `events_where_panel_title` | 1 |
| `black_bloc/events.py:582` | Pick the voice or text channel it happens in, or **Other** for a place or a link… | card description | no | `events_where_panel_intro` | 1 |
| `black_bloc/events.py:587` | A voice or text channel… | select placeholder | no | `events_where_placeholder` | 1 |
| `black_bloc/events.py:588` | Other — type a place or link… | button label | no | `events_where_other_button` | 1 |
| `black_bloc/events.py:589` | Link or place (optional)… | button label | no | `events_where_link_button` | 1 |
| `black_bloc/events.py:590` | Clear | button label | no | `events_where_clear_button` | 1 |
| `black_bloc/events.py:594` | A voice or stage channel gives everybody a **Join** button on the Discord event;… | card description | no | `events_where_join_note` | 1 |
| `black_bloc/events.py:613` | Your time zone | card title | no | `events_zone_panel_title` | 1 |
| `black_bloc/events.py:614` | Times you pick are read in this zone. Pick one, or **Other — type it…** for anyw… | card description | no | `events_zone_panel_intro` | 1 |
| `black_bloc/events.py:617` | **{title}** is cancelled and is no longer happening. | channel post | no | `events_cancelled_announcement` | 1 |
| `black_bloc/events.py:646` | Black Bloc could not post the review card in {channel} — the log says why, and a… | channel post | no | `events_submitted_no_card` | 1 |
| `black_bloc/events.py:661` | Your event **{title}** was approved on **{guild}**. It starts {stamp}. | DM | no | `events_dm_approved` | 1 |
| `black_bloc/events.py:662` | Your event **{title}** was not approved on **{guild}**. The reason given was: {r… | DM | no | `events_dm_denied` | 1 |
| `black_bloc/events.py:666` | Your event **{title}** on **{guild}** has been cancelled — {why} | DM | no | `events_dm_cancelled` | 1 |
| `black_bloc/events.py:667` | The reason given was: {note} | card description | no | `events_cancel_note` | 1 |
| `black_bloc/events.py:696` | Your event **{title}** on **{guild}** finished before Black Bloc ever announced … | DM | no | `events_dm_missed` | 1 |
| `black_bloc/events.py:710` | **{title}** has ended. Thanks for coming. | channel post | no | `events_ended_text` | 1 |
| `black_bloc/events.py:722` | This room is Black Bloc's — it goes away on its own **{when}**. Staff can remove… | channel post | no | `events_room_notice` | 1 |
| `black_bloc/events.py:727` | Delete this room | button label | no | `events_room_delete_button` | 1 |
| `black_bloc/events.py:728` | Remove this room? | card title | no | `events_room_delete_title` | 1 |
| `black_bloc/events.py:729` | A line the host is sent (if the event is still open) | card field | no | `events_room_delete_label` | 1 |
| `black_bloc/events.py:753` | It is announced in the event's own room rather than a public channel — **events_… | channel post | no | `events_announced_in_room` | 1 |
| `black_bloc/events.py:763` | One post per proposed event: the review card and its buttons are the first messa… | channel topic | no | `events_forum_topic` | 1 |
| `black_bloc/events.py:822` | This post is Black Bloc's — it is tagged as the event moves and archives itself … | channel post | no | `events_post_notice` | 1 |
| `black_bloc/events.py:830` | Event **#{event_id}** — proposed by <@{who}>. Approve or deny it below. | channel post | no | `events_post_opened` | 1 |
| `black_bloc/events.py:831` | Delete this post | button label | no | `events_post_delete_button` | 1 |
| `black_bloc/events.py:832` | Remove this post? | card title | no | `events_post_delete_title` | 1 |
| `black_bloc/events.py:858` | Move to the forum | button label | no | `events_move_to_forum_button` | 1 |
| `black_bloc/events.py:895` | It is announced in the event's own post rather than a public channel — **events_… | channel post | no | `events_announced_in_post` | 1 |
| `black_bloc/events.py:949` | Events | card title | no | `events_panel_title` | 1 |
| `black_bloc/events.py:950` | Propose something for the server to do, and see where the open ones have got to. | card description | no | `events_panel_intro` | 1 |
| `black_bloc/events.py:952` | This panel has gone quiet — run /event again | card description | no | `events_panel_timeout_footer` | 1 |
| `black_bloc/events.py:962` | The review channel | button label | no | `events_review_room_button` | 1 |
| `black_bloc/events.py:963` | The review post | button label | no | `events_review_post_button` | 1 |
| `black_bloc/events.py:2750` | Events — rooms | card title | no | `events_rooms_title` | 1 |
| `black_bloc/events.py:2751` | Rooms… | button label | no | `events_rooms_button` | 1 |
| `black_bloc/events.py:2752` | Where an event's posts go… | select placeholder | no | `events_posts_where_placeholder` | 1 |
| `black_bloc/events.py:2753` | Who may remove a room… | select placeholder | no | `events_room_delete_placeholder` | 1 |
| `black_bloc/events.py:2754` | The role that may remove a room (pick nothing for staff) | select placeholder | no | `events_room_approver_placeholder` | 1 |
| `black_bloc/events.py:2755` | Delete message: {state} | button label | no | `events_room_notice_button` | 1 |
| `black_bloc/events.py:2756` | Events — the forum | card title | no | `events_forum_title` | 1 |
| `black_bloc/events.py:2757` | Forum… | button label | no | `events_forum_button` | 1 |
| `black_bloc/events.py:2758` | Where a proposal is reviewed… | select placeholder | no | `events_review_mode_placeholder` | 1 |
| `black_bloc/events.py:2759` | The events forum (pick nothing to forget it) | select placeholder | no | `events_forum_channel_placeholder` | 1 |
| `black_bloc/events.py:2760` | a text channel of its own, under events_category_id | card field | no | `events_review_mode_words` | 1 |
| `black_bloc/events.py:2760` | one post in the events forum, under BlackMail | card field | no | `events_review_mode_words_2` | 1 |
| `black_bloc/events.py:2764` | the event's own room | card field | no | `events_posts_where_words` | 1 |
| `black_bloc/events.py:2764` | the announce channel | card field | no | `events_posts_where_words_2` | 1 |
| `black_bloc/events.py:2764` | both the room and the announce channel | card field | no | `events_posts_where_words_3` | 1 |
| `black_bloc/when_picker.py:25` | Later — pick a date… | card field | no | `events_later_label` | 1 |
| `black_bloc/when_picker.py:26` | Other — type it… | card field | no | `events_other_label` | 1 |
| `black_bloc/when_picker.py:28` | Date | select placeholder | no | `events_day_placeholder` | 1 |
| `black_bloc/when_picker.py:29` | Start time — hour | select placeholder | no | `events_hour_placeholder` | 1 |
| `black_bloc/when_picker.py:30` | Start time — minute | select placeholder | no | `events_minute_placeholder` | 1 |
| `black_bloc/when_picker.py:31` | Which time zone? | select placeholder | no | `events_zone_placeholder` | 1 |
| `black_bloc/when_picker.py:32` | How long? | select placeholder | no | `events_duration_placeholder` | 1 |
| `black_bloc/when_picker.py:35` | Date — YYYY-MM-DD | card field | no | `events_later_label_field` | 1 |
| `black_bloc/api/tools/events.py:47` | Black Bloc has no event **#{event_id}** any more, so nothing was done. The event… | ephemeral answer | no | `events_no_such_event` | 2 |
| `black_bloc/api/tools/events.py:51` | **{given}** is not a state an event can be in, so nothing was listed. They are {… | ephemeral answer | no | `events_unknown_status` | 2 |
| `black_bloc/api/tools/events.py:54` | A denied event needs one line the requester is sent, so nothing was done. Say wh… | ephemeral answer | no | `events_deny_needs_a_reason` | 2 |
| `black_bloc/api/tools/events.py:58` | Event **#{event_id}** is **{status}** already, so there was nothing to cancel. | ephemeral answer | no | `events_not_cancellable` | 2 |
| `black_bloc/api/tools/events.py:61` | Event **#{event_id}** is **{status}**, so its details cannot be changed — only a… | ephemeral answer | no | `events_not_editable` | 2 |
| `black_bloc/api/tools/events.py:71` | The Discord scheduled event still has the old details — nothing here edits one t… | ephemeral answer | no | `events_scheduled_stale` | 2 |
| `black_bloc/api/tools/events.py:75` | Saved, and the review channel's name follows the title. | ephemeral answer | no | `events_edited` | 2 |
| `black_bloc/api/tools/events.py:76` | Event **#{event_id}** has no room of its own any more, so there was nothing to r… | ephemeral answer | no | `events_no_room` | 2 |
| `black_bloc/api/tools/events.py:79` | Event **#{event_id}** has no post of its own any more, so there was nothing to r… | ephemeral answer | no | `events_no_post` | 2 |
| `black_bloc/cogs/community/events.py:257` | Yes, call it off | ephemeral answer | no | `events_cancel_yes` | 2 |
| `black_bloc/cogs/community/events.py:264` | Your time zone | modal title | no | `events_zone_modal_title` | 2 |
| `black_bloc/cogs/community/events.py:265` | Region/City — Phoenix is America/Phoenix | modal title or field | no | `events_zone_modal_label` | 2 |
| `black_bloc/cogs/community/events.py:270` | Events — numbers | modal title | no | `events_numbers_modal_title` | 2 |
| `black_bloc/cogs/community/events.py:271` | Nothing was picked, so nothing was forgotten. | ephemeral answer | no | `events_forgot_nothing` | 2 |
| `black_bloc/cogs/community/events.py:286` | Why not? | ephemeral answer | no | `events_note_titles` | 2 |
| `black_bloc/cogs/community/events.py:286` | Why is it off? | ephemeral answer | no | `events_note_titles_2` | 2 |
| `black_bloc/cogs/community/events.py:293` | the category review channels go in | ephemeral answer | no | `events_forgettable` | 2 |
| `black_bloc/cogs/community/events.py:293` | where approved events are announced | ephemeral answer | no | `events_forgettable_2` | 2 |
| `black_bloc/cogs/community/events.py:293` | the role that gets mentioned | ephemeral answer | no | `events_forgettable_3` | 2 |
| `black_bloc/cogs/community/events.py:293` | the events forum | ephemeral answer | no | `events_forgettable_4` | 2 |
| `black_bloc/cogs/community/events.py:1769` | One line the requester will be sent | modal field label | no | `events_modal_one_line_the_requester_will_be_sent` | 2 |
| `black_bloc/cogs/community/events.py:1926` | Title | modal field label | no | `events_modal_title` | 2 |
| `black_bloc/cogs/community/events.py:1928` | What is it? | modal field label | no | `events_modal_what_is_it` | 2 |
| `black_bloc/events.py:102` | Black Bloc event {event_id}: kept {kept} day(s) | ephemeral answer | no | `events_sweep_kept_days` | 2 |
| `black_bloc/events.py:103` | Black Bloc event {event_id}: kept {kept} minute(s) while in test mode | ephemeral answer | no | `events_sweep_kept_minutes` | 2 |
| `black_bloc/events.py:136` | **{given}** is not a length Black Bloc can read, so nothing was submitted. Write… | ephemeral answer | no | `events_bad_duration` | 2 |
| `black_bloc/events.py:142` | Hit **Interested** on it to be reminded: {url} | ephemeral answer | no | `events_interested_link` | 2 |
| `black_bloc/events.py:143` | Hit **Interested** on it in the server's Events list to be reminded. | ephemeral answer | no | `events_interested_here` | 2 |
| `black_bloc/events.py:144` | There is no Discord event to click this time, so watch this channel — Black Bloc… | ephemeral answer | no | `events_no_scheduled_event` | 2 |
| `black_bloc/events.py:218` | a channel that has gone | ephemeral answer | no | `events_where_gone_word` | 2 |
| `black_bloc/events.py:346` | that page answered 404 — check the name | ephemeral answer | no | `events_where_note_missing` | 2 |
| `black_bloc/events.py:347` | {host} did not answer within {seconds} s — the link is kept as typed | ephemeral answer | no | `events_where_note_unreachable` | 2 |
| `black_bloc/events.py:348` | **{url}** answered 404, so nowhere was saved and the old place was kept. That us… | ephemeral answer | no | `events_where_refused_missing` | 2 |
| `black_bloc/events.py:353` | **{url}** did not answer within {seconds} seconds, so nowhere was saved and the … | ephemeral answer | no | `events_where_refused_unreachable` | 2 |
| `black_bloc/events.py:386` | A voice or text channel has to be picked before it can be saved, so nothing was … | ephemeral answer | no | `events_where_needs_a_channel` | 2 |
| `black_bloc/events.py:390` | Black Bloc cannot find channel **{given}** on this server, so nothing was saved.… | ephemeral answer | no | `events_where_no_such_channel` | 2 |
| `black_bloc/events.py:394` | **{name}** is not somewhere an event can happen, so nothing was saved. Discord t… | ephemeral answer | no | `events_where_not_a_place` | 2 |
| `black_bloc/events.py:514` | Ask in the server | ephemeral answer | no | `events_location_fallback` | 2 |
| `black_bloc/events.py:524` | **{given}** is not a time zone Black Bloc knows, so nothing was saved. Write the… | ephemeral answer | no | `events_unknown_tz` | 2 |
| `black_bloc/events.py:529` | Did you mean {names}? | ephemeral answer | no | `events_did_you_mean` | 2 |
| `black_bloc/events.py:542` | Event proposals are turned off on this server, so nothing was submitted. A Lead … | ephemeral answer | no | `events_events_off` | 2 |
| `black_bloc/events.py:546` | Black Bloc is in test mode and cannot work out where a review channel would be a… | ephemeral answer | no | `events_no_test_channel` | 2 |
| `black_bloc/events.py:561` | **{given}** happens twice in **{tz}** — the clocks go back and that hour runs ag… | ephemeral answer | no | `events_dst_ambiguous` | 2 |
| `black_bloc/events.py:567` | (needed) | ephemeral answer | no | `events_draft_needed` | 2 |
| `black_bloc/events.py:568` | (not set) | ephemeral answer | no | `events_draft_not_set` | 2 |
| `black_bloc/events.py:569` | (nothing yet) | ephemeral answer | no | `events_draft_nothing_yet` | 2 |
| `black_bloc/events.py:571` | {when}, read in **{tz}** | ephemeral answer | no | `events_draft_when` | 2 |
| `black_bloc/events.py:575` | Times are read in **{tz}**, which **Time zone** changes. | ephemeral answer | no | `events_draft_zone` | 2 |
| `black_bloc/events.py:576` | **Still needed:** {why} | ephemeral answer | no | `events_still_needed` | 2 |
| `black_bloc/events.py:580` | Title & details | modal title | no | `events_text_modal_title` | 2 |
| `black_bloc/events.py:591` | Somewhere else | modal title | no | `events_where_modal_title` | 2 |
| `black_bloc/events.py:592` | A link or a note | modal title | no | `events_where_link_modal_title` | 2 |
| `black_bloc/events.py:593` | Where, or a link | modal title or field | no | `events_where_modal_label` | 2 |
| `black_bloc/events.py:618` | Black Bloc has nowhere to put the review channel, so nothing was submitted. A Le… | ephemeral answer | no | `events_no_category` | 2 |
| `black_bloc/events.py:622` | **events_category_id** points at something that is not a category, so nothing wa… | ephemeral answer | no | `events_not_a_category` | 2 |
| `black_bloc/events.py:626` | Discord refused to make the review channel, so nothing was submitted. Black Bloc… | ephemeral answer | no | `events_cannot_create` | 2 |
| `black_bloc/events.py:635` | **{title}** is in — the mods will review it and Black Bloc will DM you either wa… | ephemeral answer | no | `events_submitted` | 2 |
| `black_bloc/events.py:638` | Their review card is in {channel} — you can see and post in there too, so answer… | ephemeral answer | no | `events_submitted_here` | 2 |
| `black_bloc/events.py:642` | Test mode is on, so the review card is in this channel rather than in {channel},… | ephemeral answer | no | `events_submitted_test` | 2 |
| `black_bloc/events.py:650` | It starts {local} your time ({tz}) · {stamp} | ephemeral answer | no | `events_starts_at` | 2 |
| `black_bloc/events.py:651` | Black Bloc has no record of that event any more, so nothing was changed. `/event… | ephemeral answer | no | `events_no_such_event_2` | 2 |
| `black_bloc/events.py:655` | Somebody got there first — event #{event_id} is already **{status}**, so nothing… | ephemeral answer | no | `events_already_decided` | 2 |
| `black_bloc/events.py:659` | Approved. {extra} | ephemeral answer | no | `events_approved_said` | 2 |
| `black_bloc/events.py:660` | Denied, and the requester has been told why. | ephemeral answer | no | `events_denied_said` | 2 |
| `black_bloc/events.py:668` | Black Bloc could not finish setting it up, so nobody was ever able to review it.… | ephemeral answer | no | `events_cancel_why` | 2 |
| `black_bloc/events.py:668` | the channel the mods were reviewing it in is no longer there. Propose it again w… | ephemeral answer | no | `events_cancel_why_2` | 2 |
| `black_bloc/events.py:668` | the channel the mods were reviewing it in was deleted. Propose it again with `/e… | ephemeral answer | no | `events_cancel_why_3` | 2 |
| `black_bloc/events.py:668` | Black Bloc could not read the start time stored for it. Propose it again with `/… | ephemeral answer | no | `events_cancel_why_4` | 2 |
| `black_bloc/events.py:668` | staff removed its room. | ephemeral answer | no | `events_cancel_why_5` | 2 |
| `black_bloc/events.py:668` | staff removed its post. | ephemeral answer | no | `events_cancel_why_6` | 2 |
| `black_bloc/events.py:668` | staff have filed it as a request instead, so it is not on the calendar any more.… | ephemeral answer | no | `events_cancel_why_7` | 2 |
| `black_bloc/events.py:693` | either you or a member of staff called it off. Ask a Lead there if that is a sur… | ephemeral answer | no | `events_cancel_why_default` | 2 |
| `black_bloc/events.py:701` | Event #{event_id} is cancelled. | ephemeral answer | no | `events_cancelled_said` | 2 |
| `black_bloc/events.py:702` | Event #{event_id} is already **{status}**, so there was nothing to cancel. | ephemeral answer | no | `events_not_open` | 2 |
| `black_bloc/events.py:703` | **{given}** is not an event number, so nothing was cancelled. `/event` has them. | ephemeral answer | no | `events_not_an_id` | 2 |
| `black_bloc/events.py:704` | ⚠️ **No staff roles resolve**, so nobody but server admins can see a review chan… | ephemeral answer | no | `events_no_staff_warning` | 2 |
| `black_bloc/events.py:711` | **{title}** was not approved. The reason given was: {reason}. Ask a Lead if you … | ephemeral answer | no | `events_room_denied` | 2 |
| `black_bloc/events.py:725` | {n} minutes after it ends | ephemeral answer | no | `events_room_goes_minutes` | 2 |
| `black_bloc/events.py:726` | {n} days after it ends | ephemeral answer | no | `events_room_goes_days` | 2 |
| `black_bloc/events.py:730` | Only staff can remove this room. If you want your event called off, use **Call i… | ephemeral answer | no | `events_room_delete_not_staff` | 2 |
| `black_bloc/events.py:734` | That button belongs to event #{event_id}, which is not the event this room is fo… | ephemeral answer | no | `events_room_not_this_event` | 2 |
| `black_bloc/events.py:738` | Event #{event_id} has no room any more, so there was nothing to remove. | ephemeral answer | no | `events_room_already_gone` | 2 |
| `black_bloc/events.py:741` | The room is gone. | ephemeral answer | no | `events_room_deleted_said` | 2 |
| `black_bloc/events.py:742` | Event #{event_id} is cancelled, and the person who proposed it has been told why… | ephemeral answer | no | `events_room_also_cancelled` | 2 |
| `black_bloc/events.py:745` | Discord would not remove this room just now, so it is still here — the log says … | ephemeral answer | no | `events_room_delete_failed` | 2 |
| `black_bloc/events.py:748` | Black Bloc is in test mode and may only delete channels inside its test channel'… | ephemeral answer | no | `events_room_delete_refused_test` | 2 |
| `black_bloc/events.py:752` | Black Bloc event {event_id}: room removed by {who} | ephemeral answer | no | `events_room_deleted_by` | 2 |
| `black_bloc/events.py:776` | Make the forum | ephemeral answer | no | `events_make_the_forum` | 2 |
| `black_bloc/events.py:777` | <#{where}> is already the events forum, so nothing was made. Clear **events_foru… | ephemeral answer | no | `events_forum_exists` | 2 |
| `black_bloc/events.py:781` | **modmail_category_id** is not pointed at a category Black Bloc can see, so ther… | ephemeral answer | no | `events_forum_no_category` | 2 |
| `black_bloc/events.py:786` | This server cannot be given a forum channel by Black Bloc — the library it runs … | ephemeral answer | no | `events_forum_unsupported` | 2 |
| `black_bloc/events.py:791` | Black Bloc could not make the forum — {reason}. Check it has **Manage Channels**… | ephemeral answer | no | `events_forum_failed_said` | 2 |
| `black_bloc/events.py:795` | <#{where}> is up: a forum under the BlackMail category, with its overwrites, and… | ephemeral answer | no | `events_forum_made` | 2 |
| `black_bloc/events.py:800` | ⚠️ Black Bloc is in **test mode** and this forum is OUTSIDE the test channel — m… | ephemeral answer | no | `events_forum_made_guarded` | 2 |
| `black_bloc/events.py:813` | Staff have not set up the events forum yet, so nothing was submitted. Tell a Lea… | ephemeral answer | no | `events_forum_not_set_member` | 2 |
| `black_bloc/events.py:818` | Discord refused to open the post for it, so nothing was submitted. Black Bloc ne… | ephemeral answer | no | `events_cannot_create_post` | 2 |
| `black_bloc/events.py:826` | This post is Black Bloc's — it goes away on its own **{when}**. Staff can remove… | ephemeral answer | no | `events_post_notice_test` | 2 |
| `black_bloc/events.py:833` | Only staff can remove this post. If you want your event called off, use **Call i… | ephemeral answer | no | `events_post_delete_not_staff` | 2 |
| `black_bloc/events.py:837` | That button belongs to event #{event_id}, which is not the event this post is fo… | ephemeral answer | no | `events_post_not_this_event` | 2 |
| `black_bloc/events.py:841` | Event #{event_id} has no post any more, so there was nothing to remove. | ephemeral answer | no | `events_post_already_gone` | 2 |
| `black_bloc/events.py:844` | The post is gone. | ephemeral answer | no | `events_post_deleted_said` | 2 |
| `black_bloc/events.py:845` | Discord would not remove this post just now, so it is still here — the log says … | ephemeral answer | no | `events_post_delete_failed` | 2 |
| `black_bloc/events.py:848` | Black Bloc is in test mode and may only delete a post it made itself, so this on… | ephemeral answer | no | `events_post_delete_refused_test` | 2 |
| `black_bloc/events.py:852` | Black Bloc is in **test mode** and the guard refused the events forum, so nothin… | ephemeral answer | no | `events_post_refused_test` | 2 |
| `black_bloc/events.py:856` | Black Bloc event {event_id}: post removed by {who} | ephemeral answer | no | `events_post_deleted_by` | 2 |
| `black_bloc/events.py:859` | Event #{event_id} now lives in <#{post}>. | ephemeral answer | no | `events_moved_said` | 2 |
| `black_bloc/events.py:860` | Event #{event_id} is already reviewed in a post, so there is nothing to move. It… | ephemeral answer | no | `events_move_already_a_post` | 2 |
| `black_bloc/events.py:864` | Event #{event_id} is **{status}**, so it is not moving anywhere — only an event … | ephemeral answer | no | `events_move_settled` | 2 |
| `black_bloc/events.py:868` | Event #{event_id} has no room of its own any more, so there is nothing to move i… | ephemeral answer | no | `events_move_no_room` | 2 |
| `black_bloc/events.py:878` | Black Bloc is in **test mode** and the guard refused the events forum, so nothin… | ephemeral answer | no | `events_move_refused_test` | 2 |
| `black_bloc/events.py:882` | Discord would not open a post for it, so nothing was moved and the room is untou… | ephemeral answer | no | `events_move_failed` | 2 |
| `black_bloc/events.py:886` | Only staff can move this event into the forum. If you want your event called off… | ephemeral answer | no | `events_move_not_staff` | 2 |
| `black_bloc/events.py:951` | You have not proposed an event yet. | ephemeral answer | no | `events_panel_empty` | 2 |
| `black_bloc/events.py:953` | Pick an event… | ephemeral answer | no | `events_pick_an_event` | 2 |
| `black_bloc/events.py:954` | Call one off… | ephemeral answer | no | `events_call_one_off` | 2 |
| `black_bloc/events.py:956` | Nothing is open — nothing is waiting on a decision and nothing is running. | ephemeral answer | no | `events_nothing_open` | 2 |
| `black_bloc/events.py:957` | **{status}** is where an event finishes — nothing moves it now. | ephemeral answer | no | `events_no_moves_left` | 2 |
| `black_bloc/events.py:958` | It was denied and the room it was reviewed in was cleaned up — propose it again … | ephemeral answer | no | `events_denied_room_gone` | 2 |
| `black_bloc/events.py:2831` | **{given}** is not a whole number, so nothing was changed. {label} takes a numbe… | ephemeral answer | no | `events_not_a_number` | 2 |
| `black_bloc/events.py:2835` | **{given}** is outside what Discord and Black Bloc allow, so nothing was changed… | ephemeral answer | no | `events_out_of_bounds` | 2 |
| `black_bloc/events.py:2839` | Days a finished channel is kept | ephemeral answer | no | `events_number_bounds` | 2 |
| `black_bloc/events.py:2839` | Minutes late it may still be announced | ephemeral answer | no | `events_number_bounds_2` | 2 |
| `black_bloc/when_picker.py:19` | %Y-%m-%d | ephemeral answer | no | `events_day_format` | 2 |
| `black_bloc/when_picker.py:21` | %Y-%m-%d %H:%M | ephemeral answer | no | `events_start_format` | 2 |
| `black_bloc/when_picker.py:34` | Pick a date | modal title or field | no | `events_later_title` | 2 |
| `black_bloc/when_picker.py:36` | Your time zone | modal title | no | `events_zone_modal_title_2` | 2 |
| `black_bloc/when_picker.py:37` | Region/City — Phoenix is America/Phoenix | modal title or field | no | `events_zone_modal_label_2` | 2 |
| `black_bloc/when_picker.py:39` | Back | ephemeral answer | no | `events_zone_back` | 2 |
| `black_bloc/when_picker.py:41` | a day | ephemeral answer | no | `events_needs_day` | 2 |
| `black_bloc/when_picker.py:42` | an hour | ephemeral answer | no | `events_needs_hour` | 2 |
| `black_bloc/when_picker.py:43` | a minute | ephemeral answer | no | `events_needs_minute` | 2 |
| `black_bloc/when_picker.py:44` | Pick {parts} from the dropdowns above, and the time is set. | ephemeral answer | no | `events_needs_when` | 2 |
| `black_bloc/when_picker.py:51` | 1h 30m | ephemeral answer | no | `events_durations` | 2 |
| `black_bloc/when_picker.py:51` | 2h 30m | ephemeral answer | no | `events_durations_2` | 2 |
| `black_bloc/when_picker.py:51` | All day | ephemeral answer | no | `events_durations_3` | 2 |

### requests

*140 strings — 0 keyed · 45 unkeyed pass 1 · 75 unkeyed pass 2 · 20 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/cogs/community/requests.py:172` | Why is it on hold? (sent to the asker) | card field | no | `request_note_labels` | 1 |
| `black_bloc/cogs/community/requests.py:172` | Why? (sent to the asker) | card field | no | `request_note_labels_2` | 1 |
| `black_bloc/cogs/community/requests.py:172` | What's left? (sent to who marked it ready) | card field | no | `request_note_labels_3` | 1 |
| `black_bloc/cogs/community/requests.py:1332` | File a request | button label | no | `request_button_file_a_request` | 1 |
| `black_bloc/cogs/community/requests.py:1351` | Refresh | button label | no | `request_button_refresh` | 1 |
| `black_bloc/cogs/community/requests.py:1393` | Logs | button label | no | `request_button_logs` | 1 |
| `black_bloc/cogs/community/requests.py:1419` | Back | button label | no | `request_button_back` | 1 |
| `black_bloc/requests.py:94` | being worked on | card field | no | `request_status_words` | 1 |
| `black_bloc/requests.py:94` | ready to check | card field | no | `request_status_words_2` | 1 |
| `black_bloc/requests.py:94` | on hold | card field | no | `request_status_words_3` | 1 |
| `black_bloc/requests.py:164` | Sending a request back needs one line saying what is still to do, so nothing was… | card description | no | `request_sending_back_needs_a_note` | 1 |
| `black_bloc/requests.py:196` | There is nothing to add, so no comment was left. Type what you want on the reque… | channel post | no | `request_comment_needs_text` | 1 |
| `black_bloc/requests.py:201` | Request **#{request_id}** — {who} has been asked by DM to try it. | DM | no | `request_check_asked_dm` | 1 |
| `black_bloc/requests.py:210` | Try it and tell {asked_by} how it went — say what works and what does not. Staff… | card description | no | `request_check_asked_description` | 1 |
| `black_bloc/requests.py:221` | Requests | card title | no | `request_panel_title` | 1 |
| `black_bloc/requests.py:222` | Ask the server for something, or see where what you already asked for has got to… | card description | no | `request_panel_intro` | 1 |
| `black_bloc/requests.py:224` | This panel has gone quiet — run /request again | card description | no | `request_panel_timeout_footer` | 1 |
| `black_bloc/requests.py:230` | New request **#{request_id}** from {who}: {what} | channel post | no | `request_move_line` | 1 |
| `black_bloc/requests.py:230` | Request **#{request_id}** from {who} is being worked on: {what} | channel post | no | `request_move_line_2` | 1 |
| `black_bloc/requests.py:230` | Request **#{request_id}** from {who} is ready to check: {what} | channel post | no | `request_move_line_3` | 1 |
| `black_bloc/requests.py:230` | Request **#{request_id}** from {who} was sent back — {note} | channel post | no | `request_move_line_4` | 1 |
| `black_bloc/requests.py:230` | Request **#{request_id}** from {who} is done: {what} | channel post | no | `request_move_line_5` | 1 |
| `black_bloc/requests.py:230` | Request **#{request_id}** from {who} is on hold — {reason} | channel post | no | `request_move_line_6` | 1 |
| `black_bloc/requests.py:230` | Request **#{request_id}** from {who} was declined — {reason} | channel post | no | `request_move_line_7` | 1 |
| `black_bloc/requests.py:230` | Request **#{request_id}** from {who} moved on: {what} | channel post | no | `request_move_line_8` | 1 |
| `black_bloc/requests.py:230` | Request **#{request_id}** from {who} — they have been asked to check it: {what} | channel post | no | `request_move_line_9` | 1 |
| `black_bloc/requests.py:249` | Black Bloc requests — one post per request. The card in each post is where staff… | channel topic | no | `request_forum_topic` | 1 |
| `black_bloc/requests.py:338` | Asked for | card field | no | `request_field_labels` | 1 |
| `black_bloc/requests.py:338` | Why | card field | no | `request_field_labels_2` | 1 |
| `black_bloc/requests.py:338` | What was built | card field | no | `request_field_labels_3` | 1 |
| `black_bloc/requests.py:338` | How to test | card field | no | `request_field_labels_4` | 1 |
| `black_bloc/requests.py:338` | What needs doing | card field | no | `request_field_labels_5` | 1 |
| `black_bloc/requests.py:338` | Why it is waiting | card field | no | `request_field_labels_6` | 1 |
| `black_bloc/requests.py:338` | Why | card field | no | `request_field_labels_7` | 1 |
| `black_bloc/requests.py:338` | Now | card field | no | `request_field_labels_8` | 1 |
| `black_bloc/requests.py:338` | Requested by | card field | no | `request_field_labels_9` | 1 |
| `black_bloc/requests.py:338` | Assignee | card field | no | `request_field_labels_10` | 1 |
| `black_bloc/requests.py:338` | Marked ready by | card field | no | `request_field_labels_11` | 1 |
| `black_bloc/requests.py:338` | Accepted by | card field | no | `request_field_labels_12` | 1 |
| `black_bloc/requests.py:338` | Sent back by | card field | no | `request_field_labels_13` | 1 |
| `black_bloc/requests.py:338` | Due | card field | no | `request_field_labels_14` | 1 |
| `black_bloc/requests.py:338` | Was | card field | no | `request_field_labels_15` | 1 |
| `black_bloc/requests.py:338` | Asked to check | card field | no | `request_field_labels_16` | 1 |
| `black_bloc/requests.py:338` | Asked by | card field | no | `request_field_labels_17` | 1 |
| `black_bloc/requests.py:370` | Black Bloc · requests | card description | no | `request_embed_footer` | 1 |
| `black_bloc/api/tools/requests.py:84` | text/csv | ephemeral answer | no | `request_csv_media_type` | 2 |
| `black_bloc/api/tools/requests.py:110` | Filed as **#{request_id}** — staff will see it on this page. | ephemeral answer | no | `request_filed_said` | 2 |
| `black_bloc/api/tools/requests.py:111` | Request **#{request_id}** is now **{status}**. | ephemeral answer | no | `request_set_said` | 2 |
| `black_bloc/api/tools/requests.py:112` | Request **#{request_id}** is saved. | ephemeral answer | no | `request_saved_said` | 2 |
| `black_bloc/api/tools/requests.py:113` | Your comment is on request **#{request_id}**. | ephemeral answer | no | `request_comment_said` | 2 |
| `black_bloc/api/tools/requests.py:114` | That change arrived with nothing in it, so nothing was saved. It is a fault in t… | ephemeral answer | no | `request_nothing_to_save` | 2 |
| `black_bloc/api/tools/requests.py:118` | **{given}** is not somebody Black Bloc can see in this server, so nothing was ch… | ephemeral answer | no | `request_bad_assignee` | 2 |
| `black_bloc/cogs/community/requests.py:150` | Request **#{request_id}** is now **{status}**. | ephemeral answer | no | `request_set_said_2` | 2 |
| `black_bloc/cogs/community/requests.py:151` | Request **#{request_id}** is off hold and back to **{status}**. | ephemeral answer | no | `request_resumed_said` | 2 |
| `black_bloc/cogs/community/requests.py:153` | Request **#{request_id}** is ready to check — staff will look at it. | ephemeral answer | no | `request_ready_said` | 2 |
| `black_bloc/cogs/community/requests.py:154` | Request **#{request_id}** is done. The person who asked has been told. | ephemeral answer | no | `request_accepted_said` | 2 |
| `black_bloc/cogs/community/requests.py:155` | Request **#{request_id}** is back with whoever is working on it. | ephemeral answer | no | `request_sent_back_said` | 2 |
| `black_bloc/cogs/community/requests.py:164` | Ready to check | modal title | no | `request_ready_modal_title` | 2 |
| `black_bloc/cogs/community/requests.py:165` | Yes, take it back | ephemeral answer | no | `request_withdraw_yes` | 2 |
| `black_bloc/cogs/community/requests.py:167` | Put this on hold | ephemeral answer | no | `request_note_titles` | 2 |
| `black_bloc/cogs/community/requests.py:167` | Decline this request | ephemeral answer | no | `request_note_titles_2` | 2 |
| `black_bloc/cogs/community/requests.py:167` | Send this back | ephemeral answer | no | `request_note_titles_3` | 2 |
| `black_bloc/cogs/community/requests.py:205` | Make the forum | ephemeral answer | no | `request_make_the_forum` | 2 |
| `black_bloc/cogs/community/requests.py:206` | <#{where}> is already the request forum, so nothing was made. Clear **request_fo… | ephemeral answer | no | `request_forum_exists` | 2 |
| `black_bloc/cogs/community/requests.py:210` | **modmail_category_id** is not pointed at a category Black Bloc can see, so ther… | ephemeral answer | no | `request_forum_no_category` | 2 |
| `black_bloc/cogs/community/requests.py:215` | This server cannot be given a forum channel by Black Bloc — the library it runs … | ephemeral answer | no | `request_forum_unsupported` | 2 |
| `black_bloc/cogs/community/requests.py:220` | Black Bloc could not make the forum — {reason}. Check it has **Manage Channels**… | ephemeral answer | no | `request_forum_failed_said` | 2 |
| `black_bloc/cogs/community/requests.py:224` | <#{where}> is up: a forum under the Blackmail category, with its overwrites, and… | ephemeral answer | no | `request_forum_made` | 2 |
| `black_bloc/cogs/community/requests.py:228` | ⚠️ Black Bloc is in **test mode** and this forum is OUTSIDE the test channel — m… | ephemeral answer | no | `request_forum_made_guarded` | 2 |
| `black_bloc/cogs/community/requests.py:1501` | What are you asking for? | modal field label | no | `request_modal_what_are_you_asking_for` | 2 |
| `black_bloc/cogs/community/requests.py:1506` | Why is it worth doing? | modal field label | no | `request_modal_why_is_it_worth_doing` | 2 |
| `black_bloc/cogs/community/requests.py:1511` | Needed by — YYYY-MM-DD | modal field label | no | `request_modal_needed_by_yyyy_mm_dd` | 2 |
| `black_bloc/cogs/community/requests.py:1532` | What was built? | modal field label | no | `request_modal_what_was_built` | 2 |
| `black_bloc/cogs/community/requests.py:1537` | How does somebody test it? | modal field label | no | `request_modal_how_does_somebody_test_it` | 2 |
| `black_bloc/requests.py:86` | YYYY-MM-DD | ephemeral answer | no | `request_due_shape` | 2 |
| `black_bloc/requests.py:105` | Requests are turned off on this server, so nothing was filed. A Lead turns them … | ephemeral answer | no | `request_requests_off` | 2 |
| `black_bloc/requests.py:109` | Only staff may file a request on this server at the moment, so nothing was filed… | ephemeral answer | no | `request_staff_only_files` | 2 |
| `black_bloc/requests.py:113` | A request needs a line saying what you are asking for, so nothing was filed. Fil… | ephemeral answer | no | `request_needs_what` | 2 |
| `black_bloc/requests.py:117` | A request needs a line saying why it is worth doing, so nothing was filed. That … | ephemeral answer | no | `request_needs_why` | 2 |
| `black_bloc/requests.py:125` | Black Bloc has no request **#{request_id}**, so nothing was done. `/request` sho… | ephemeral answer | no | `request_no_such_request` | 2 |
| `black_bloc/requests.py:129` | Request **#{request_id}** is not yours, so nothing was withdrawn. Only the perso… | ephemeral answer | no | `request_not_yours` | 2 |
| `black_bloc/requests.py:133` | Request **#{request_id}** is **{status}**, so there was nothing to withdraw. You… | ephemeral answer | no | `request_too_late_to_withdraw` | 2 |
| `black_bloc/requests.py:137` | Request **#{request_id}** is already **{status}**, so nothing was changed. | ephemeral answer | no | `request_already_that` | 2 |
| `black_bloc/requests.py:138` | **{given}** is not a state a request can be in, so nothing was changed. They are… | ephemeral answer | no | `request_unknown_status` | 2 |
| `black_bloc/requests.py:141` | Request **#{request_id}** is **{status}**, and staff cannot move it to **{wanted… | ephemeral answer | no | `request_no_such_move` | 2 |
| `black_bloc/requests.py:145` | From **{status}** it can go to {moves}. | ephemeral answer | no | `request_moves_are` | 2 |
| `black_bloc/requests.py:146` | **{status}** is where a request finishes — nothing moves it now. | ephemeral answer | no | `request_no_moves_left` | 2 |
| `black_bloc/requests.py:147` | A declined request needs one line the person who asked is sent, so nothing was c… | ephemeral answer | no | `request_decline_needs_a_reason` | 2 |
| `black_bloc/requests.py:151` | A request put on hold needs one line the person who asked is sent, so nothing wa… | ephemeral answer | no | `request_hold_needs_a_reason` | 2 |
| `black_bloc/requests.py:159` | Marking a request ready to check needs a line saying what was actually built, so… | ephemeral answer | no | `request_ready_needs_what_was_built` | 2 |
| `black_bloc/requests.py:173` | Request **#{request_id}** is **{status}**, and a request only finishes once some… | ephemeral answer | no | `request_done_needs_a_check` | 2 |
| `black_bloc/requests.py:179` | You are the one who marked request **#{request_id}** ready to check, and this se… | ephemeral answer | no | `request_review_by_somebody_else` | 2 |
| `black_bloc/requests.py:184` | Request **#{request_id}** is **{status}**, not ready to check, so there was noth… | ephemeral answer | no | `request_not_ready_to_check` | 2 |
| `black_bloc/requests.py:188` | Request **#{request_id}** is **{status}**, not on hold, so there was nothing to … | ephemeral answer | no | `request_not_on_hold` | 2 |
| `black_bloc/requests.py:200` | Request **#{request_id}** is withdrawn. Nobody will pick it up now. | ephemeral answer | no | `request_withdrawn_said` | 2 |
| `black_bloc/requests.py:202` | Request **#{request_id}** — {who}'s DMs are closed, so they were pinged in the r… | ephemeral answer | no | `request_check_asked_channel` | 2 |
| `black_bloc/requests.py:206` | Request **#{request_id}** — {who}'s DMs are closed and the channel fallback is o… | ephemeral answer | no | `request_check_asked_nobody` | 2 |
| `black_bloc/requests.py:214` | Filed as **#{request_id}** — staff will see it on the site. You will get a DM ev… | ephemeral answer | no | `request_filed` | 2 |
| `black_bloc/requests.py:218` | Nothing has been filed yet — `/request` puts the first one in. | ephemeral answer | no | `request_nothing_filed_yet` | 2 |
| `black_bloc/requests.py:219` | Nothing is open — every request has been finished, declined or withdrawn. | ephemeral answer | no | `request_nothing_open` | 2 |
| `black_bloc/requests.py:220` | You have not filed a request yet — `/request` puts one in. | ephemeral answer | no | `request_nothing_of_yours` | 2 |
| `black_bloc/requests.py:223` | You have not asked for anything yet. | ephemeral answer | no | `request_panel_empty` | 2 |
| `black_bloc/requests.py:225` | Only somebody other than {who} may accept this one. | ephemeral answer | no | `request_accept_needs_somebody_else` | 2 |
| `black_bloc/requests.py:226` | Pick a request… | ephemeral answer | no | `request_pick_a_request` | 2 |
| `black_bloc/requests.py:228` | Take one back… | ephemeral answer | no | `request_take_one_back` | 2 |
| `black_bloc/requests.py:253` | picked up | ephemeral answer | no | `request_forum_picked_up_tag` | 2 |
| `black_bloc/requests.py:254` | ready to check | ephemeral answer | no | `request_forum_ready_tag` | 2 |
| `black_bloc/requests.py:255` | on hold | ephemeral answer | no | `request_forum_hold_tag` | 2 |
| `black_bloc/requests.py:293` | (filed from a forum post) | ephemeral answer | no | `request_adopted_why` | 2 |
| `black_bloc/requests.py:294` | {who} — this post was not turned into a request, because only staff may file one… | ephemeral answer | no | `request_adopted_not_yours_to_file` | 2 |
| `black_bloc/requests.py:299` | {who} — this post was not turned into a request, because requests are turned off… | ephemeral answer | no | `request_adopted_requests_off` | 2 |
| `black_bloc/requests.py:316` | New request #{request_id} | ephemeral answer | no | `request_embed_titles` | 2 |
| `black_bloc/requests.py:316` | Request #{request_id} is being worked on | ephemeral answer | no | `request_embed_titles_2` | 2 |
| `black_bloc/requests.py:316` | Request #{request_id} is ready to check 🔎 | ephemeral answer | no | `request_embed_titles_3` | 2 |
| `black_bloc/requests.py:316` | Request #{request_id} was sent back | ephemeral answer | no | `request_embed_titles_4` | 2 |
| `black_bloc/requests.py:316` | Request #{request_id} is done ✅ | ephemeral answer | no | `request_embed_titles_5` | 2 |
| `black_bloc/requests.py:316` | Request #{request_id} is on hold | ephemeral answer | no | `request_embed_titles_6` | 2 |
| `black_bloc/requests.py:316` | Request #{request_id} was declined | ephemeral answer | no | `request_embed_titles_7` | 2 |
| `black_bloc/requests.py:316` | Request #{request_id} moved on | ephemeral answer | no | `request_embed_titles_8` | 2 |
| `black_bloc/requests.py:316` | Request #{request_id} is ready for you to try 🙌 | ephemeral answer | no | `request_embed_titles_9` | 2 |

### modmail + front door

*229 strings — 7 keyed · 65 unkeyed pass 1 · 145 unkeyed pass 2 · 19 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/frontdoor.py:11` | *(the key's value)* | read from the store at render | **yes → `frontdoor_event_label`** (ns `modmail`, 2 read site(s)) | — | 1 |
| `black_bloc/frontdoor.py:18` | *(the key's value)* | read from the store at render | **yes → `frontdoor_request_label`** (ns `modmail`, 2 read site(s)) | — | 1 |
| `black_bloc/frontdoor.py:130` | *(the key's value)* | read from the store at render | **yes → `frontdoor_text`** (ns `modmail`, 2 read site(s)) | — | 1 |
| `black_bloc/frontdoor.py:24` | *(the key's value)* | read from the store at render | **yes → `frontdoor_ticket_label`** (ns `modmail`, 2 read site(s)) | — | 1 |
| `black_bloc/frontdoor.py:126` | *(the key's value)* | read from the store at render | **yes → `frontdoor_title`** (ns `modmail`, 2 read site(s)) | — | 1 |
| `black_bloc/modmail.py:553` | *(the key's value)* | read from the store at render | **yes → `modmail_panel_text`** (ns `modmail`, 1 read site(s)) | — | 1 |
| `black_bloc/modmail.py:552` | *(the key's value)* | read from the store at render | **yes → `modmail_panel_title`** (ns `modmail`, 1 read site(s)) | — | 1 |
| `black_bloc/api/tools/modmail.py:92` | The member could not be sent that reply — their DMs are closed or they have left… | DM | no | `modmail_dm_failed` | 1 |
| `black_bloc/cogs/moderation/modmail.py:277` | Black Bloc is not handling modmail on **{guild}** yet, so staff have not seen th… | DM | no | `modmail_disabled_dm` | 1 |
| `black_bloc/cogs/moderation/modmail.py:282` | Staff on **{guild}** have stopped Black Bloc from opening modmail tickets for yo… | DM | no | `modmail_blocked_dm` | 1 |
| `black_bloc/cogs/moderation/modmail.py:287` | Black Bloc only takes modmail from members of the servers it looks after, and it… | DM | no | `modmail_no_guild_dm` | 1 |
| `black_bloc/cogs/moderation/modmail.py:291` | Black Bloc could not open a ticket for that message, so staff have not seen it. … | DM | no | `modmail_cannot_open_dm` | 1 |
| `black_bloc/cogs/moderation/modmail.py:355` | A note with nothing in it says nothing, so none was saved. | card description | no | `modmail_nothing_to_note` | 1 |
| `black_bloc/cogs/moderation/modmail.py:362` | Black Bloc could not DM the member — they have DMs off or have blocked it. The t… | DM | no | `modmail_dm_failed_said` | 1 |
| `black_bloc/cogs/moderation/modmail.py:382` | **{who}** left the server. The ticket is still open, and a reply still reaches t… | card description | no | `modmail_left_note` | 1 |
| `black_bloc/cogs/moderation/modmail.py:415` | Practice ticket #{ticket_id} is open in <#{where}>. **Speak as the member** puts… | channel post | no | `modmail_practice_opened` | 1 |
| `black_bloc/cogs/moderation/modmail.py:426` | Practice ticket #{ticket_id} is over. The transcript is marked PRACTICE. | channel post | no | `modmail_practice_ended` | 1 |
| `black_bloc/cogs/moderation/modmail.py:487` | Ticket **#{ticket_id}** with **{who}** is open in <#{where}>, and what you wrote… | channel post | no | `modmail_staff_opened` | 1 |
| `black_bloc/cogs/moderation/modmail.py:3043` | The ticket category | card field | no | `modmail_forget_labels` | 1 |
| `black_bloc/cogs/moderation/modmail.py:3043` | The staff channel | card field | no | `modmail_forget_labels_2` | 1 |
| `black_bloc/cogs/moderation/modmail.py:3043` | The ticket forum | card field | no | `modmail_forget_labels_3` | 1 |
| `black_bloc/cogs/moderation/modmail.py:3043` | The transcripts channel | card field | no | `modmail_forget_labels_4` | 1 |
| `black_bloc/cogs/moderation/modmail.py:3049` | Black Bloc is **not** answering DMs here, so the old ModMail bot still holds the… | channel post | no | `modmail_incumbent_line` | 1 |
| `black_bloc/frontdoor.py:95` | This panel has gone quiet — run /ask again | card description | no | `modmail_panel_timeout_footer` | 1 |
| `black_bloc/frontdoor.py:96` | Propose an event | card title | no | `modmail_event_handoff_title` | 1 |
| `black_bloc/frontdoor.py:97` | An event is a card you fill in — the day, the time, where it is — rather than on… | channel post | no | `modmail_event_handoff_text` | 1 |
| `black_bloc/modmail.py:36` | Staff | channel / role name | no | `modmail_anonymous_name` | 1 |
| `black_bloc/modmail.py:45` | ⏎ ⏎ … truncated — this ticket is longer than one transcript file can hold. ⏎ | channel post | no | `modmail_truncated_mark` | 1 |
| `black_bloc/modmail.py:46` | (not delivered) | channel post | no | `modmail_undelivered_mark` | 1 |
| `black_bloc/modmail.py:57` | Black Bloc modmail \| user {user_id} \| ticket {ticket_id} | channel post | no | `modmail_topic_template` | 1 |
| `black_bloc/modmail.py:59` | {name} · #{ticket_id} | channel post | no | `modmail_thread_name_template` | 1 |
| `black_bloc/modmail.py:62` | PRACTICE — a fake ticket. Nothing in it reached a member and no DM was sent. | channel post | no | `modmail_practice_mark` | 1 |
| `black_bloc/modmail.py:63` | (no text) | channel post | no | `modmail_no_text` | 1 |
| `black_bloc/modmail.py:206` | Attachments | card field name | no | `modmail_card_attachments` | 1 |
| `black_bloc/modmail.py:230` | Account made | card field name | no | `modmail_card_account_made` | 1 |
| `black_bloc/modmail.py:235` | Joined the server | card field name | no | `modmail_card_joined_the_server` | 1 |
| `black_bloc/modmail.py:239` | Roles | card field name | no | `modmail_card_roles` | 1 |
| `black_bloc/modmail.py:240` | Earlier tickets | card field name | no | `modmail_card_earlier_tickets` | 1 |
| `black_bloc/modmail.py:241` | Mode | card field name | no | `modmail_card_mode` | 1 |
| `black_bloc/modmail.py:337` | Opened | card field name | no | `modmail_card_opened` | 1 |
| `black_bloc/modmail.py:338` | Closed | card field name | no | `modmail_card_closed` | 1 |
| `black_bloc/modmail.py:340` | Closed by | card field name | no | `modmail_card_closed_by` | 1 |
| `black_bloc/modmail.py:344` | Mode | card field name | no | `modmail_card_mode_2` | 1 |
| `black_bloc/modmail.py:346` | Messages | card field name | no | `modmail_card_messages` | 1 |
| `black_bloc/modmail.py:351` | Practice | card field name | no | `modmail_card_practice` | 1 |
| `black_bloc/modmail.py:353` | Reason | card field name | no | `modmail_card_reason` | 1 |
| `black_bloc/modmail.py:400` | Black Bloc modmail — one post per ticket. Only staff can see this; the member ne… | channel topic | no | `modmail_forum_topic` | 1 |
| `black_bloc/modmail.py:430` | The modmail inbox | card title | no | `modmail_panel_title` | 1 |
| `black_bloc/modmail.py:431` | This panel has gone quiet — run /modmail again | card description | no | `modmail_panel_timeout_footer_2` | 1 |
| `black_bloc/modmail.py:432` | Where modmail is set up | card title | no | `modmail_setup_title` | 1 |
| `black_bloc/modmail.py:433` | Who cannot open modmail tickets | card title | no | `modmail_blocked_title` | 1 |
| `black_bloc/modmail.py:434` | Saved replies | card title | no | `modmail_snippets_title` | 1 |
| `black_bloc/modmail.py:435` | Forget where modmail has been pointed | card title | no | `modmail_forget_title` | 1 |
| `black_bloc/modmail.py:462` | a DM to Black Bloc | card field | no | `modmail_source_words` | 1 |
| `black_bloc/modmail.py:462` | /modmail | card field | no | `modmail_source_words_2` | 1 |
| `black_bloc/modmail.py:462` | the Open a ticket button | card field | no | `modmail_source_words_3` | 1 |
| `black_bloc/modmail.py:500` | Opened | card field name | no | `modmail_card_opened_2` | 1 |
| `black_bloc/modmail.py:501` | Came in by | card field name | no | `modmail_card_came_in_by` | 1 |
| `black_bloc/modmail.py:503` | Opened by | card field name | no | `modmail_card_opened_by` | 1 |
| `black_bloc/modmail.py:506` | About | card field name | no | `modmail_card_about` | 1 |
| `black_bloc/modmail.py:555` | Modmail | card title | no | `modmail_member_title` | 1 |
| `black_bloc/modmail.py:556` | Modmail is how you reach staff privately. Nobody else sees what you write. | card description | no | `modmail_member_intro` | 1 |
| `black_bloc/modmail.py:562` | The Open a ticket button | card title | no | `modmail_ticket_button_title` | 1 |
| `black_bloc/modmail.py:816` | Ticket #{ticket_id} | card title | no | `modmail_card_title` | 1 |
| `black_bloc/modmail.py:817` | Practice ticket #{ticket_id} | card title | no | `modmail_card_practice_title` | 1 |
| `black_bloc/modmail.py:818` | ⚠️ **They are blocked** — a new ticket cannot be opened after this one. | channel post | no | `modmail_card_blocked_line` | 1 |
| `black_bloc/modmail.py:819` | This ticket is **practice**. Nothing here reaches a member: no DM is sent and no… | channel post | no | `modmail_card_practice_line` | 1 |
| `black_bloc/modmail.py:825` | **filed as** — {what} | channel post | no | `modmail_card_moved_line` | 1 |
| `black_bloc/modmail.py:877` | This ticket is closed — Back goes to the inbox. | card description | no | `modmail_card_closed_footer` | 1 |
| `black_bloc/modmail.py:911` | A message typed in a ticket now stays in the ticket — only the card's **Reply** … | card field | no | `modmail_reply_style_words` | 1 |
| `black_bloc/modmail.py:911` | ⚠️ From now on, anything staff type in a ticket goes to the member. The card's b… | card field | no | `modmail_reply_style_words_2` | 1 |
| `black_bloc/modmail.py:911` | ⚠️ From now on, anything staff type in a ticket goes to the member, and the card… | card field | no | `modmail_reply_style_words_3` | 1 |
| `black_bloc/api/tools/modmail.py:56` | Black Bloc has no ticket **#{ticket_id}**, so nothing was done. The modmail page… | ephemeral answer | no | `modmail_no_such_ticket` | 2 |
| `black_bloc/api/tools/modmail.py:60` | Ticket **#{ticket_id}** is closed already, so nothing was sent. Open tickets are… | ephemeral answer | no | `modmail_ticket_closed` | 2 |
| `black_bloc/api/tools/modmail.py:64` | That reply was empty, so nothing was sent. Write something for the member to rea… | ephemeral answer | no | `modmail_nothing_to_send` | 2 |
| `black_bloc/api/tools/modmail.py:67` | **{given}** is not a state a ticket can be in, so nothing was listed. They are {… | ephemeral answer | no | `modmail_unknown_status` | 2 |
| `black_bloc/api/tools/modmail.py:70` | Ticket **#{ticket_id}** was closed by somebody else a moment ago, so nothing was… | ephemeral answer | no | `modmail_close_raced` | 2 |
| `black_bloc/api/tools/modmail.py:73` | Closing that ticket would delete its channel, and Black Bloc is in **test mode**… | ephemeral answer | no | `modmail_close_would_delete` | 2 |
| `black_bloc/api/tools/modmail.py:78` | A snippet needs a short name and the text it stands for, so nothing was saved. | ephemeral answer | no | `modmail_snippet_needs_both` | 2 |
| `black_bloc/api/tools/modmail.py:81` | Black Bloc has no snippet called **{name}**, so there was nothing to remove. | ephemeral answer | no | `modmail_no_such_snippet` | 2 |
| `black_bloc/api/tools/modmail.py:84` | **{channel_id}** is not a channel Black Bloc can see, so the ticket button was n… | ephemeral answer | no | `modmail_no_such_channel` | 2 |
| `black_bloc/api/tools/modmail.py:88` | Black Bloc is in **test mode**, so the only channel it may put the ticket button… | ephemeral answer | no | `modmail_panel_would_post` | 2 |
| `black_bloc/cogs/moderation/modmail.py:295` | Black Bloc is in test mode and cannot see its test channel, so no ticket was mad… | ephemeral answer | no | `modmail_no_test_channel` | 2 |
| `black_bloc/cogs/moderation/modmail.py:299` | Black Bloc has nowhere to put ticket threads, so nothing was opened. A Lead poin… | ephemeral answer | no | `modmail_no_staff_channel` | 2 |
| `black_bloc/cogs/moderation/modmail.py:304` | Black Bloc has no forum to put ticket posts in, so nothing was opened. A Lead pr… | ephemeral answer | no | `modmail_no_forum_channel` | 2 |
| `black_bloc/cogs/moderation/modmail.py:309` | Black Bloc is in **test mode** and has not claimed <#{where}> yet, so no ticket … | ephemeral answer | no | `modmail_forum_not_claimed` | 2 |
| `black_bloc/cogs/moderation/modmail.py:314` | **modmail_category_id** is not pointed at a category Black Bloc can see, so ther… | ephemeral answer | no | `modmail_no_forum_category` | 2 |
| `black_bloc/cogs/moderation/modmail.py:318` | <#{where}> is already the ticket forum, so nothing was made. **Forget…** → **The… | ephemeral answer | no | `modmail_forum_exists` | 2 |
| `black_bloc/cogs/moderation/modmail.py:322` | This server cannot be given a forum channel by Black Bloc — the library it runs … | ephemeral answer | no | `modmail_forum_unsupported` | 2 |
| `black_bloc/cogs/moderation/modmail.py:326` | Black Bloc could not make the forum — {reason}. Check it has **Manage Channels**… | ephemeral answer | no | `modmail_forum_failed` | 2 |
| `black_bloc/cogs/moderation/modmail.py:330` | <#{where}> is up: a forum under the ticket category, with its overwrites, and wi… | ephemeral answer | no | `modmail_forum_made` | 2 |
| `black_bloc/cogs/moderation/modmail.py:334` | ⚠️ Black Bloc is in **test mode** and this forum is OUTSIDE the test channel — m… | ephemeral answer | no | `modmail_forum_made_guarded` | 2 |
| `black_bloc/cogs/moderation/modmail.py:340` | This channel is not a modmail ticket, so nothing was sent. Run the command insid… | ephemeral answer | no | `modmail_no_ticket_here` | 2 |
| `black_bloc/cogs/moderation/modmail.py:344` | Black Bloc cannot tell which ticket you mean — {count} are open, so nothing was … | ephemeral answer | no | `modmail_many_open` | 2 |
| `black_bloc/cogs/moderation/modmail.py:348` | **{given}** is not a ticket number, so nothing was sent. | ephemeral answer | no | `modmail_not_a_ticket_id` | 2 |
| `black_bloc/cogs/moderation/modmail.py:349` | Black Bloc has no record of ticket #{ticket_id} on this server, so nothing was s… | ephemeral answer | no | `modmail_no_such_ticket_2` | 2 |
| `black_bloc/cogs/moderation/modmail.py:353` | Ticket #{ticket_id} is already closed, so nothing was sent. | ephemeral answer | no | `modmail_ticket_closed_2` | 2 |
| `black_bloc/cogs/moderation/modmail.py:354` | Type some text or name a snippet — nothing was sent. | ephemeral answer | no | `modmail_nothing_to_send_2` | 2 |
| `black_bloc/cogs/moderation/modmail.py:356` | There is no snippet called **{name}**, so nothing was sent. `/modmail` → **Snipp… | ephemeral answer | no | `modmail_no_snippet` | 2 |
| `black_bloc/cogs/moderation/modmail.py:360` | Sent to the member as **{who}**. | ephemeral answer | no | `modmail_sent` | 2 |
| `black_bloc/cogs/moderation/modmail.py:361` | Noted on ticket #{ticket_id} — the member never sees it. | ephemeral answer | no | `modmail_note_saved` | 2 |
| `black_bloc/cogs/moderation/modmail.py:366` | The ticket itself could not be written to; the log says why. | ephemeral answer | no | `modmail_relay_failed_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:367` | Ticket #{ticket_id} is closed.{extra} | ephemeral answer | no | `modmail_closed_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:368` | Ticket #{ticket_id} was closed by somebody else while you were typing. | ephemeral answer | no | `modmail_close_raced_2` | 2 |
| `black_bloc/cogs/moderation/modmail.py:369` | The transcript could not be posted, so the ticket channel was left where it is r… | ephemeral answer | no | `modmail_no_transcript_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:373` | The member was not told, because you asked for a silent close. | ephemeral answer | no | `modmail_silent_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:374` | **{who}** can no longer open modmail tickets. **Unblock them** on `/modmail` → *… | ephemeral answer | no | `modmail_blocked_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:378` | **{who}** was already blocked, so nothing changed. | ephemeral answer | no | `modmail_already_blocked` | 2 |
| `black_bloc/cogs/moderation/modmail.py:379` | **{who}** can open modmail tickets again. | ephemeral answer | no | `modmail_unblocked_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:380` | **{who}** was not blocked, so nothing changed. | ephemeral answer | no | `modmail_not_blocked` | 2 |
| `black_bloc/cogs/moderation/modmail.py:381` | Nobody is blocked from modmail. | ephemeral answer | no | `modmail_no_blocks` | 2 |
| `black_bloc/cogs/moderation/modmail.py:386` | **{key}** is forgotten, so modmail falls back to its default. **Setup…** on `/mo… | ephemeral answer | no | `modmail_forgotten` | 2 |
| `black_bloc/cogs/moderation/modmail.py:390` | **{key}** is now {place}. | ephemeral answer | no | `modmail_pointed` | 2 |
| `black_bloc/cogs/moderation/modmail.py:391` | Black Bloc answers modmail DMs on this server from now on. A member who DMs it g… | ephemeral answer | no | `modmail_answering` | 2 |
| `black_bloc/cogs/moderation/modmail.py:395` | Black Bloc has stopped answering modmail DMs here, so the old ModMail bot keeps … | ephemeral answer | no | `modmail_not_answering` | 2 |
| `black_bloc/cogs/moderation/modmail.py:399` | New tickets from now on: {what}. The {count} ticket(s) already open keep the mod… | ephemeral answer | no | `modmail_mode_set` | 2 |
| `black_bloc/cogs/moderation/modmail.py:407` | Snippet **{name}** saved. `/reply snippet:{name}` sends it. | ephemeral answer | no | `modmail_snippet_saved` | 2 |
| `black_bloc/cogs/moderation/modmail.py:408` | There is already a snippet called **{name}**, so nothing was changed. Pick it on… | ephemeral answer | no | `modmail_snippet_exists` | 2 |
| `black_bloc/cogs/moderation/modmail.py:412` | Snippet **{name}** is gone. | ephemeral answer | no | `modmail_snippet_gone` | 2 |
| `black_bloc/cogs/moderation/modmail.py:413` | There is no snippet called **{name}**, so nothing was removed. | ephemeral answer | no | `modmail_no_such_snippet_2` | 2 |
| `black_bloc/cogs/moderation/modmail.py:414` | There are no snippets yet — **Add one…** makes the first. | ephemeral answer | no | `modmail_no_snippets` | 2 |
| `black_bloc/cogs/moderation/modmail.py:420` | **This is a practice ticket.** It behaves like a real one except that no DM is e… | ephemeral answer | no | `modmail_practice_header` | 2 |
| `black_bloc/cogs/moderation/modmail.py:425` | Said it — the card should now be under it. | ephemeral answer | no | `modmail_practice_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:428` | Black Bloc could not make the practice thread, so nothing was opened. The log sa… | ephemeral answer | no | `modmail_practice_failed` | 2 |
| `black_bloc/cogs/moderation/modmail.py:432` | You already have a modmail ticket open, and Black Bloc allows one per person — s… | ephemeral answer | no | `modmail_already_practising` | 2 |
| `black_bloc/cogs/moderation/modmail.py:436` | No staff role resolves, so a practice ticket would have nobody in it and none wa… | ephemeral answer | no | `modmail_no_staff_to_practise` | 2 |
| `black_bloc/cogs/moderation/modmail.py:442` | That is a real ticket with a real member, so nobody can be spoken for. | ephemeral answer | no | `modmail_not_practice` | 2 |
| `black_bloc/cogs/moderation/modmail.py:443` | Type something for the pretend member to say — nothing was added. | ephemeral answer | no | `modmail_nothing_to_say` | 2 |
| `black_bloc/cogs/moderation/modmail.py:444` | ⚠️ **No staff roles resolve**, so a ticket channel would be visible to server ad… | ephemeral answer | no | `modmail_no_staff_warning` | 2 |
| `black_bloc/cogs/moderation/modmail.py:450` | Open a ticket | modal title | no | `modmail_ticket_modal_title` | 2 |
| `black_bloc/cogs/moderation/modmail.py:451` | What is this about — a few words, if you like | modal title or field | no | `modmail_ticket_subject_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:452` | Tell us what is happening | modal title or field | no | `modmail_ticket_body_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:453` | Open a ticket with somebody | modal title | no | `modmail_staff_modal_title` | 2 |
| `black_bloc/cogs/moderation/modmail.py:454` | What they are sent — it opens the ticket as your first reply | modal title or field | no | `modmail_staff_body_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:455` | Your ticket is open — ticket **#{ticket_id}**. Staff can see it now, and their r… | ephemeral answer | no | `modmail_ticket_opened_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:459` | ⚠️ Black Bloc could not DM you, so open DMs from this server or staff's replies … | ephemeral answer | no | `modmail_dms_are_shut` | 2 |
| `black_bloc/cogs/moderation/modmail.py:463` | You already have an open ticket, so nothing new was made. Anything you DM Black … | ephemeral answer | no | `modmail_already_open_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:467` | Black Bloc could not open a ticket just now, so staff have not seen this. Try ag… | ephemeral answer | no | `modmail_cannot_open_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:471` | **{who}** is a bot, and a bot has no DMs to answer, so no ticket was opened. | ephemeral answer | no | `modmail_a_bot_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:472` | Black Bloc is not answering modmail here, so no ticket was opened. **Setup…** → … | ephemeral answer | no | `modmail_staff_disabled_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:476` | **{who}** is blocked from modmail, so no ticket was opened. **Unblock them** und… | ephemeral answer | no | `modmail_staff_blocked_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:480` | **{who}** already has an open ticket: <#{where}>. Reply there instead. | ephemeral answer | no | `modmail_staff_already_open` | 2 |
| `black_bloc/cogs/moderation/modmail.py:481` | **Open a ticket with…** is switched off on this server, so no ticket was opened.… | ephemeral answer | no | `modmail_open_with_off` | 2 |
| `black_bloc/cogs/moderation/modmail.py:491` | ⚠️ The DM did not reach them — their DMs are shut or Black Bloc is blocked. The … | ephemeral answer | no | `modmail_staff_not_reached` | 2 |
| `black_bloc/cogs/moderation/modmail.py:495` | Black Bloc is not answering modmail on **{guild}** yet, so there is no ticket to… | ephemeral answer | no | `modmail_member_door_off` | 2 |
| `black_bloc/cogs/moderation/modmail.py:499` | Staff here have stopped Black Bloc from opening modmail tickets for you, so ther… | ephemeral answer | no | `modmail_member_blocked` | 2 |
| `black_bloc/cogs/moderation/modmail.py:503` | No **Open a ticket** button is up. **Post it…** puts one in a channel of your ch… | ephemeral answer | no | `modmail_panel_nowhere` | 2 |
| `black_bloc/cogs/moderation/modmail.py:506` | The **Open a ticket** button is in <#{where}> — message `{message_id}`. | ephemeral answer | no | `modmail_panel_is_at` | 2 |
| `black_bloc/cogs/moderation/modmail.py:507` | The **Open a ticket** button is up in <#{where}>. | ephemeral answer | no | `modmail_panel_posted_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:508` | The **Open a ticket** button is in <#{where}> now; the old message is gone. | ephemeral answer | no | `modmail_panel_moved_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:509` | The **Open a ticket** button is down. Nothing else changed. | ephemeral answer | no | `modmail_panel_down_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:510` | There is no **Open a ticket** button up, so nothing was taken down. | ephemeral answer | no | `modmail_panel_not_up` | 2 |
| `black_bloc/cogs/moderation/modmail.py:511` | Black Bloc could not post the **Open a ticket** button there — the log says why.… | ephemeral answer | no | `modmail_panel_stuck` | 2 |
| `black_bloc/cogs/moderation/modmail.py:515` | Black Bloc is in **test mode**, so the only channels it may post the **Open a ti… | ephemeral answer | no | `modmail_panel_guarded` | 2 |
| `black_bloc/cogs/moderation/modmail.py:522` | Black Bloc is in test mode, so the **Open a ticket** button is rehearsing in <#{… | ephemeral answer | no | `modmail_panel_rehearsing_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:527` | The **Open a ticket** button is down, and so is the rehearsal copy. Nothing else… | ephemeral answer | no | `modmail_panel_rehearsal_down_said` | 2 |
| `black_bloc/cogs/moderation/modmail.py:533` | **heading** — {title} ⏎ **says** — {text} ⏎ Staff change both on the dashboard's… | ephemeral answer | no | `modmail_panel_lines` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3053` | Nobody is blocked, so there is nobody to let back in. | ephemeral answer | no | `modmail_nothing_blocked_here` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3054` | **Try a fake ticket?** Black Bloc makes a private thread for you, with the ticke… | ephemeral answer | no | `modmail_really_practise` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3058` | Picked: <@{user_id}>. | ephemeral answer | no | `modmail_picked_block` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3059` | About to block <@{user_id}> — **Block them…** asks for the reason. | ephemeral answer | no | `modmail_picked_to_block` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3060` | Picked: **{name}**. | ephemeral answer | no | `modmail_picked_snippet` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3061` | Remove the snippet **{name}**? Nothing that already went out changes. | ephemeral answer | no | `modmail_really_remove` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3062` | Why they are blocked | modal title or field | no | `modmail_block_reason_title` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3063` | Why — the log records this, the member is not told | modal title or field | no | `modmail_block_reason_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3064` | A new saved reply | ephemeral answer | no | `modmail_snippet_title_new` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3065` | Change a saved reply | ephemeral answer | no | `modmail_snippet_title_edit` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3066` | What to call it — lowercase, dashes, no spaces | modal title or field | no | `modmail_snippet_name_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:3067` | What it says | modal title or field | no | `modmail_snippet_content_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4170` | Reply to the member | modal title or field | no | `modmail_reply_title` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4171` | Reply as Staff | modal title or field | no | `modmail_anon_reply_title` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4172` | What the member is sent | modal title or field | no | `modmail_reply_text_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4173` | Or a saved reply — with both, the snippet goes first | modal title or field | no | `modmail_reply_snippet_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4174` | A private note | modal title or field | no | `modmail_card_note_title` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4175` | Why — the member never sees this | modal title or field | no | `modmail_card_note_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4176` | Close this ticket | modal title or field | no | `modmail_close_title` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4177` | Why — the member is told this | modal title or field | no | `modmail_close_reason_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4178` | Or close it quietly | modal title or field | no | `modmail_close_silent_label` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4179` | Close without telling them | ephemeral answer | no | `modmail_close_silent_option` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4180` | Say it as the member | modal title or field | no | `modmail_speak_title` | 2 |
| `black_bloc/cogs/moderation/modmail.py:4181` | What the pretend member says — nobody is DMed | modal title or field | no | `modmail_speak_label` | 2 |
| `black_bloc/frontdoor.py:58` | The front door is switched off, so there is nothing to open here. A Lead turns `… | ephemeral answer | no | `modmail_door_off` | 2 |
| `black_bloc/frontdoor.py:64` | There is no front door posted anywhere, so nothing was taken down. **Post the fr… | ephemeral answer | no | `modmail_door_not_up` | 2 |
| `black_bloc/frontdoor.py:68` | Black Bloc is in test mode, so it only posts in its own test channel and in the … | ephemeral answer | no | `modmail_door_guarded` | 2 |
| `black_bloc/frontdoor.py:74` | That is not a channel Black Bloc can see, so the front door was not posted. Pick… | ephemeral answer | no | `modmail_door_no_channel` | 2 |
| `black_bloc/frontdoor.py:78` | Black Bloc could not post the front door in that channel. It needs **View Channe… | ephemeral answer | no | `modmail_door_stuck` | 2 |
| `black_bloc/frontdoor.py:82` | The front door is up in <#{where}>. | ephemeral answer | no | `modmail_door_posted_said` | 2 |
| `black_bloc/frontdoor.py:83` | Black Bloc is in test mode, so the front door is rehearsing in <#{where}> instea… | ephemeral answer | no | `modmail_door_rehearsing_said` | 2 |
| `black_bloc/frontdoor.py:88` | The front door is down, and so is the rehearsal copy. Nothing else changed, and … | ephemeral answer | no | `modmail_door_rehearsal_down_said` | 2 |
| `black_bloc/frontdoor.py:92` | The front door has moved to <#{where}>. | ephemeral answer | no | `modmail_door_moved_said` | 2 |
| `black_bloc/frontdoor.py:93` | The front door is down. Nothing else changed, and `/ask` still works. | ephemeral answer | no | `modmail_door_down_said` | 2 |
| `black_bloc/modmail.py:47` | Attachment links stop working about 24 hours after they were posted. | ephemeral answer | no | `modmail_attachments_expire` | 2 |
| `black_bloc/modmail.py:50` | From the member | ephemeral answer | no | `modmail_titles` | 2 |
| `black_bloc/modmail.py:50` | Sent to the member | ephemeral answer | no | `modmail_titles_2` | 2 |
| `black_bloc/modmail.py:50` | Private note | ephemeral answer | no | `modmail_titles_3` | 2 |
| `black_bloc/modmail.py:438` | …and {rest} more — the Modmail page on the site lists every one. | ephemeral answer | no | `modmail_more_blocked` | 2 |
| `black_bloc/modmail.py:439` | …and {rest} more — the Modmail page on the site lists every one. | ephemeral answer | no | `modmail_more_snippets` | 2 |
| `black_bloc/modmail.py:440` | Somebody… | ephemeral answer | no | `modmail_pick_a_block` | 2 |
| `black_bloc/modmail.py:441` | A snippet… | ephemeral answer | no | `modmail_pick_a_snippet` | 2 |
| `black_bloc/modmail.py:442` | A ticket… | ephemeral answer | no | `modmail_pick_a_ticket` | 2 |
| `black_bloc/modmail.py:443` | Which place to forget… | ephemeral answer | no | `modmail_pick_a_place` | 2 |
| `black_bloc/modmail.py:444` | How new tickets are made… | ephemeral answer | no | `modmail_pick_a_mode` | 2 |
| `black_bloc/modmail.py:445` | How staff answer a ticket… | ephemeral answer | no | `modmail_pick_a_reply_style` | 2 |
| `black_bloc/modmail.py:446` | Pick a channel… | ephemeral answer | no | `modmail_pick_a_channel` | 2 |
| `black_bloc/modmail.py:447` | Pick a category… | ephemeral answer | no | `modmail_pick_a_category` | 2 |
| `black_bloc/modmail.py:448` | Pick a forum… | ephemeral answer | no | `modmail_pick_a_forum` | 2 |
| `black_bloc/modmail.py:449` | Who to block… | ephemeral answer | no | `modmail_pick_somebody` | 2 |
| `black_bloc/modmail.py:557` | **Your ticket is open.** Staff can see it, and their replies come back as a DM f… | ephemeral answer | no | `modmail_member_ticket_open` | 2 |
| `black_bloc/modmail.py:561` | **Your ticket is open:** <#{where}>. Staff answer there, and by DM. | ephemeral answer | no | `modmail_member_ticket_seen` | 2 |
| `black_bloc/modmail.py:563` | Who to open a ticket with… | ephemeral answer | no | `modmail_pick_a_member` | 2 |
| `black_bloc/modmail.py:823` | **messages** — {inbound} from them · {outbound} sent · {notes} note(s) | ephemeral answer | no | `modmail_card_counts` | 2 |
| `black_bloc/modmail.py:824` | **opened by staff** — <@{who}> | ephemeral answer | no | `modmail_card_opened_by_staff` | 2 |
| `black_bloc/modmail.py:826` | ⚠️ **The last reply did not reach them** — their DMs are shut or Black Bloc is b… | ephemeral answer | no | `modmail_card_not_reached` | 2 |
| `black_bloc/modmail.py:905` | only the card's Reply and /reply reach the member | ephemeral answer | no | `modmail_reply_style_options` | 2 |
| `black_bloc/modmail.py:905` | a plain message in a ticket is relayed, as it always has been | ephemeral answer | no | `modmail_reply_style_options_2` | 2 |
| `black_bloc/modmail.py:905` | both — today's behaviour, with the card added | ephemeral answer | no | `modmail_reply_style_options_3` | 2 |
| `black_bloc/modmail.py:910` | Staff answer tickets by **{style}** from now on. {what} | ephemeral answer | no | `modmail_reply_style_set` | 2 |

### go-live

*82 strings — 4 keyed · 23 unkeyed pass 1 · 54 unkeyed pass 2 · 5 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/api/tools/golive.py:132` | *(the key's value)* | read from the store at render | **yes → `golive_end_author`** (ns `golive`, 2 read site(s)) | — | 1 |
| `black_bloc/api/tools/golive.py:112` | *(the key's value)* | read from the store at render | **yes → `golive_end_suffix`** (ns `golive`, 3 read site(s)) | — | 1 |
| `black_bloc/api/tools/golive.py:123` | *(the key's value)* | read from the store at render | **yes → `golive_end_template`** (ns `golive`, 3 read site(s)) | — | 1 |
| `black_bloc/api/tools/golive.py:114` | *(the key's value)* | read from the store at render | **yes → `golive_template`** (ns `golive`, 4 read site(s)) | — | 1 |
| `black_bloc/api/tools/golive.py:50` | Any% attempts | card title | no | `golive_title_any_attempts` | 1 |
| `black_bloc/cogs/content/golive.py:116` | test mode means nothing is posted outside <#{test_channel_id}> | card description | no | `golive_test_mode_note` | 1 |
| `black_bloc/cogs/content/golive.py:117` | Right now {note}, so nothing of yours reaches the announcement channel. | channel post | no | `golive_test_mode_line` | 1 |
| `black_bloc/cogs/content/golive.py:118` | Your Twitch channel, and whether your streams get announced | card description | no | `golive_command_description` | 1 |
| `black_bloc/cogs/content/golive.py:128` | Streamers | card title | no | `golive_streamers_title` | 1 |
| `black_bloc/cogs/content/golive.py:129` | Everyone who has linked a Twitch channel. Picking one shows what Black Bloc know… | card description | no | `golive_streamers_intro` | 1 |
| `black_bloc/cogs/content/golive.py:134` | **{name}** — twitch.tv/{login} | channel post | no | `golive_streamer_card` | 1 |
| `black_bloc/cogs/content/golive.py:149` | The go-live feed's own settings are for staff. | channel post | no | `golive_staff_only_line` | 1 |
| `black_bloc/cogs/content/golive.py:154` | a test stream | card title | no | `golive_title_a_test_stream` | 1 |
| `black_bloc/cogs/content/golive.py:162` | a test stream | card title | no | `golive_title_a_test_stream_2` | 1 |
| `black_bloc/cogs/content/golive.py:1562` | Yes, unlink them | button label | no | `golive_button_yes_unlink_them` | 1 |
| `black_bloc/cogs/content/golive.py:1579` | Back | button label | no | `golive_button_back` | 1 |
| `black_bloc/cogs/content/golive.py:1592` | Back | button label | no | `golive_button_back_2` | 1 |
| `black_bloc/golive.py:26` | Live now | card title | no | `golive_embed_no_title` | 1 |
| `black_bloc/golive.py:27` | Game | card field | no | `golive_embed_game_field` | 1 |
| `black_bloc/golive.py:28` | Black Bloc · via {source} | card description | no | `golive_embed_footer` | 1 |
| `black_bloc/golive.py:491` | Go-live | card title | no | `golive_panel_title` | 1 |
| `black_bloc/golive.py:492` | This panel has gone quiet — run /golive again | card description | no | `golive_panel_timeout_footer` | 1 |
| `black_bloc/golive.py:494` | Your Twitch channel, and whether your streams get announced. | card description | no | `golive_panel_intro` | 1 |
| `black_bloc/golive.py:495` | **Your Twitch channel** — none linked yet. Linking one lets Black Bloc fill in y… | channel post | no | `golive_no_link_line` | 1 |
| `black_bloc/golive.py:499` | **Your Twitch channel** — twitch.tv/{login} | channel post | no | `golive_link_line` | 1 |
| `black_bloc/golive.py:504` | **Your streams** — not announced, because you opted out. **Announce my streams a… | channel post | no | `golive_opted_out_line` | 1 |
| `black_bloc/golive.py:508` | **Your streams** — announced here whenever Black Bloc sees you go live. | channel post | no | `golive_announced_line` | 1 |
| `black_bloc/api/tools/golive.py:53` | 2 h 10 min | ephemeral answer | no | `golive_preview_duration` | 2 |
| `black_bloc/api/tools/golive.py:56` | **{user_id}** has no Twitch account linked, so there was nothing to unlink. The … | ephemeral answer | no | `golive_not_linked` | 2 |
| `black_bloc/api/tools/golive.py:60` | **{user_id}** was not opted out, so there was nothing to undo. The opt-outs tabl… | ephemeral answer | no | `golive_not_opted_out` | 2 |
| `black_bloc/api/tools/golive.py:64` | **{given}** is not a Twitch channel name Black Bloc can use, so nothing was link… | ephemeral answer | no | `golive_bad_login` | 2 |
| `black_bloc/api/tools/golive.py:68` | **{name}** is linked to twitch.tv/{login}. Black Bloc did not check that channel… | ephemeral answer | no | `golive_linked` | 2 |
| `black_bloc/api/tools/golive.py:72` | **{name}** is opted out, so no stream of theirs is announced from now on. | ephemeral answer | no | `golive_opted_out` | 2 |
| `black_bloc/api/tools/golive.py:73` | **{name}** is no longer opted out, so their streams can be announced again. | ephemeral answer | no | `golive_opted_in` | 2 |
| `black_bloc/cogs/content/golive.py:67` | go-live: Twitch enrichment is off (TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET are not… | ephemeral answer | no | `golive_twitch_off` | 2 |
| `black_bloc/cogs/content/golive.py:71` | off — no Twitch credentials; the sweep still runs and still ages sessions out | ephemeral answer | no | `golive_polling_no_creds` | 2 |
| `black_bloc/cogs/content/golive.py:74` | not known — the go-live cog is not loaded, so nothing is polling or announcing | ephemeral answer | no | `golive_polling_no_cog` | 2 |
| `black_bloc/cogs/content/golive.py:80` | Done — Black Bloc will not announce your streams. **Announce my streams again** … | ephemeral answer | no | `golive_opted_out_2` | 2 |
| `black_bloc/cogs/content/golive.py:84` | Done — Black Bloc will announce your streams again when it sees you go live. **S… | ephemeral answer | no | `golive_opted_in_2` | 2 |
| `black_bloc/cogs/content/golive.py:88` | That does not look like a Twitch channel name, so nothing was linked. Use the ch… | ephemeral answer | no | `golive_bad_login_2` | 2 |
| `black_bloc/cogs/content/golive.py:92` | Twitch has no channel called **{channel}**, so nothing was linked. Check the spe… | ephemeral answer | no | `golive_no_such_channel` | 2 |
| `black_bloc/cogs/content/golive.py:96` | Linked **{channel}** to you. Black Bloc will use it to fill in the game and titl… | ephemeral answer | no | `golive_linked_2` | 2 |
| `black_bloc/cogs/content/golive.py:100` | Linked **{channel}** to you, but Twitch could not be reached to check that the c… | ephemeral answer | no | `golive_link_not_checked` | 2 |
| `black_bloc/cogs/content/golive.py:105` | **{channel}** is already linked to another member here, so nothing was changed. … | ephemeral answer | no | `golive_link_taken` | 2 |
| `black_bloc/cogs/content/golive.py:110` | Done — Black Bloc has forgotten your Twitch channel. Discord presence still anno… | ephemeral answer | no | `golive_unlinked` | 2 |
| `black_bloc/cogs/content/golive.py:114` | Go-live announcements are now **{mode}**. | ephemeral answer | no | `golive_mode_set` | 2 |
| `black_bloc/cogs/content/golive.py:115` | an unknown platform | ephemeral answer | no | `golive_platform_unknown` | 2 |
| `black_bloc/cogs/content/golive.py:119` | Your Twitch channel | modal title | no | `golive_link_modal_title` | 2 |
| `black_bloc/cogs/content/golive.py:120` | The name after twitch.tv/ | modal title or field | no | `golive_link_modal_label` | 2 |
| `black_bloc/cogs/content/golive.py:123` | Preview an announcement… | ephemeral answer | no | `golive_preview_pick` | 2 |
| `black_bloc/cogs/content/golive.py:124` | As you are now | ephemeral answer | no | `golive_preview_as_you_are` | 2 |
| `black_bloc/cogs/content/golive.py:125` | Announcements: off / shadow / on | ephemeral answer | no | `golive_mode_pick` | 2 |
| `black_bloc/cogs/content/golive.py:126` | Announcements: {mode} | ephemeral answer | no | `golive_mode_option` | 2 |
| `black_bloc/cogs/content/golive.py:127` | Somebody who has linked a channel… | ephemeral answer | no | `golive_pick_a_streamer` | 2 |
| `black_bloc/cogs/content/golive.py:133` | Nobody has linked a Twitch channel yet. | ephemeral answer | no | `golive_streamers_empty` | 2 |
| `black_bloc/cogs/content/golive.py:135` | {name} — twitch.tv/{login} | ephemeral answer | no | `golive_streamer_option` | 2 |
| `black_bloc/cogs/content/golive.py:136` | — not verified with Twitch | ephemeral answer | no | `golive_streamer_unverified` | 2 |
| `black_bloc/cogs/content/golive.py:137` | Opted out, so none of their streams are announced. | ephemeral answer | no | `golive_streamer_opted_out` | 2 |
| `black_bloc/cogs/content/golive.py:138` | Announced whenever Black Bloc sees them go live. | ephemeral answer | no | `golive_streamer_announced` | 2 |
| `black_bloc/cogs/content/golive.py:139` | Unlink **{name}** from twitch.tv/{login}? They keep every role they already have… | ephemeral answer | no | `golive_streamer_unlink_confirm` | 2 |
| `black_bloc/cogs/content/golive.py:143` | Done — **{name}** is no longer linked to a Twitch channel. | ephemeral answer | no | `golive_they_unlinked` | 2 |
| `black_bloc/cogs/content/golive.py:144` | Done — no stream of **{name}**'s is announced from now on. | ephemeral answer | no | `golive_they_opted_out` | 2 |
| `black_bloc/cogs/content/golive.py:145` | Done — **{name}**'s streams can be announced again. | ephemeral answer | no | `golive_they_opted_in` | 2 |
| `black_bloc/cogs/content/golive.py:146` | Unlink them | ephemeral answer | no | `golive_unlink_them` | 2 |
| `black_bloc/cogs/content/golive.py:147` | Opt them out | ephemeral answer | no | `golive_opt_them_out` | 2 |
| `black_bloc/cogs/content/golive.py:148` | Opt them back in | ephemeral answer | no | `golive_opt_them_in` | 2 |
| `black_bloc/golive.py:18` | Twitch | ephemeral answer | no | `golive_twitch` | 2 |
| `black_bloc/golive.py:19` | YouTube | ephemeral answer | no | `golive_youtube` | 2 |
| `black_bloc/golive.py:23` | Someone | ephemeral answer | no | `golive_nobody` | 2 |
| `black_bloc/golive.py:29` | Twitch | ephemeral answer | no | `golive_embed_source_twitch` | 2 |
| `black_bloc/golive.py:30` | Discord activity | ephemeral answer | no | `golive_embed_source_presence` | 2 |
| `black_bloc/golive.py:31` | YouTube | ephemeral answer | no | `golive_embed_source_youtube` | 2 |
| `black_bloc/golive.py:36` | is now live | ephemeral answer | no | `golive_live_verb` | 2 |
| `black_bloc/golive.py:37` | was live | ephemeral answer | no | `golive_ended_verb` | 2 |
| `black_bloc/golive.py:38` | under a minute | ephemeral answer | no | `golive_duration_short` | 2 |
| `black_bloc/golive.py:39` | {minutes} min | ephemeral answer | no | `golive_duration_minutes` | 2 |
| `black_bloc/golive.py:40` | {hours} h | ephemeral answer | no | `golive_duration_hours` | 2 |
| `black_bloc/golive.py:41` | {hours} h {minutes} min | ephemeral answer | no | `golive_duration_both` | 2 |
| `black_bloc/golive.py:500` | — not verified with Twitch, so the game and title may not fill in. **Change my c… | ephemeral answer | no | `golive_link_unverified` | 2 |
| `black_bloc/golive.py:509` | Go-live announcements are **off** right now, so nobody's streams are announced. … | ephemeral answer | no | `golive_mode_lines` | 2 |
| `black_bloc/golive.py:509` | Go-live announcements are in **shadow** right now — the log says what would have… | ephemeral answer | no | `golive_mode_lines_2` | 2 |

### youtube

*103 strings — 1 keyed · 21 unkeyed pass 1 · 59 unkeyed pass 2 · 23 not member-facing (not listed).*

⚠️ `black_bloc/youtube.py` and the upload lines of `black_bloc/cogs/content/youtube.py` are the
half being DELETED — treat every row naming uploads, videos, the feed, shorts or seeding as gone.

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/cogs/content/youtube.py:1143` | *(the key's value)* | read from the store at render | **yes → `youtube_template`** (ns `youtube`, 6 read site(s)) | — | 1 |
| `black_bloc/cogs/content/youtube.py:132` | A Lead has removed the YouTube channel Black Bloc had linked to you in **{guild}… | DM | no | `youtube_unlinked_dm` | 1 |
| `black_bloc/cogs/content/youtube.py:136` | ⏎ ⏎ What they said: {why} | DM | no | `youtube_unlinked_dm_why` | 1 |
| `black_bloc/cogs/content/youtube.py:137` | Announcements are **off** at the moment, so nothing is posted until a Lead sets … | card description | no | `youtube_mode_off_note` | 1 |
| `black_bloc/cogs/content/youtube.py:141` | Announcements are **off** for this server at the moment, so nothing is posted. L… | channel post | no | `youtube_mode_off_line` | 1 |
| `black_bloc/cogs/content/youtube.py:148` | Live streams are… | select placeholder | no | `youtube_live_mode_placeholder` | 1 |
| `black_bloc/cogs/content/youtube.py:149` | off — linked channels are not checked for live streams | card field | no | `youtube_live_mode_labels` | 1 |
| `black_bloc/cogs/content/youtube.py:149` | shadow — the probe runs and logs, nothing else changes | card field | no | `youtube_live_mode_labels_2` | 1 |
| `black_bloc/cogs/content/youtube.py:149` | on — a linked channel going live is announced | card field | no | `youtube_live_mode_labels_3` | 1 |
| `black_bloc/cogs/content/youtube.py:180` | Tell Black Bloc where your YouTube channel is and it posts here when you put a n… | card description | no | `youtube_panel_intro` | 1 |
| `black_bloc/cogs/content/youtube.py:187` | Announcements are… | select placeholder | no | `youtube_mode_placeholder` | 1 |
| `black_bloc/cogs/content/youtube.py:188` | off — nothing is checked and nothing is posted | card field | no | `youtube_mode_labels` | 1 |
| `black_bloc/cogs/content/youtube.py:188` | shadow — the sweep runs and logs, nothing is posted | card field | no | `youtube_mode_labels_2` | 1 |
| `black_bloc/cogs/content/youtube.py:188` | on — a new upload is announced | card field | no | `youtube_mode_labels_3` | 1 |
| `black_bloc/cogs/content/youtube.py:194` | **{who}**'s YouTube channel | channel post | no | `youtube_their_card` | 1 |
| `black_bloc/cogs/content/youtube.py:204` | Where uploads are posted | card title | no | `youtube_setup_title` | 1 |
| `black_bloc/cogs/content/youtube.py:211` | Words… | button label | no | `youtube_words_button` | 1 |
| `black_bloc/cogs/content/youtube.py:212` | Numbers… | button label | no | `youtube_numbers_button` | 1 |
| `black_bloc/cogs/content/youtube.py:213` | Forget… | button label | no | `youtube_forget_button` | 1 |
| `black_bloc/cogs/content/youtube.py:214` | Clear one of these… | select placeholder | no | `youtube_forget_placeholder` | 1 |
| `black_bloc/youtube.py:403` | Your YouTube channel | card title | no | `youtube_panel_title` | 1 |
| `black_bloc/youtube.py:404` | This panel has gone quiet — run /youtube again | card description | no | `youtube_panel_timeout_footer` | 1 |
| `black_bloc/api/tools/youtube.py:38` | **{user_id}** has no YouTube channel linked, so there was nothing to unlink. The… | ephemeral answer | no | `youtube_not_linked` | 2 |
| `black_bloc/api/tools/youtube.py:42` | No channel was given, so nothing was linked. Paste the channel address — the one… | ephemeral answer | no | `youtube_no_channel_given` | 2 |
| `black_bloc/api/tools/youtube.py:46` | **{name}** is linked to {title}. The {count} video(s) already on the channel are… | ephemeral answer | no | `youtube_linked` | 2 |
| `black_bloc/api/tools/youtube.py:50` | **{name}** is linked to {title}, but YouTube's feed would not answer just now, s… | ephemeral answer | no | `youtube_linked_not_seeded` | 2 |
| `black_bloc/cogs/content/youtube.py:87` | GoLive | ephemeral answer | no | `youtube_golive_cog` | 2 |
| `black_bloc/cogs/content/youtube.py:92` | youtube: no YOUTUBE_API_KEY, so uploads run on the public feed alone — Shorts ar… | ephemeral answer | no | `youtube_no_key` | 2 |
| `black_bloc/cogs/content/youtube.py:96` | **{channel}** is already linked to another member here, so nothing was changed. … | ephemeral answer | no | `youtube_already_linked` | 2 |
| `black_bloc/cogs/content/youtube.py:101` | You have no YouTube channel linked, so there was nothing to change. **Link my ch… | ephemeral answer | no | `youtube_not_linked_2` | 2 |
| `black_bloc/cogs/content/youtube.py:105` | **{who}** has no YouTube channel linked, so there was nothing to unlink. The pan… | ephemeral answer | no | `youtube_not_linked_for` | 2 |
| `black_bloc/cogs/content/youtube.py:109` | Linked **{title}** to you. Black Bloc will post here when you put a new video ou… | ephemeral answer | no | `youtube_linked_2` | 2 |
| `black_bloc/cogs/content/youtube.py:114` | Linked **{title}** to {who}. The {count} video(s) already on the channel are cou… | ephemeral answer | no | `youtube_linked_for` | 2 |
| `black_bloc/cogs/content/youtube.py:118` | Linked **{title}** to you, but YouTube's feed would not answer just now, so noth… | ephemeral answer | no | `youtube_linked_not_seeded_2` | 2 |
| `black_bloc/cogs/content/youtube.py:122` | Linked **{title}** to {who}, but YouTube's feed would not answer just now, so no… | ephemeral answer | no | `youtube_linked_for_not_seeded` | 2 |
| `black_bloc/cogs/content/youtube.py:126` | Done — Black Bloc has forgotten your YouTube channel and will not announce your … | ephemeral answer | no | `youtube_unlinked` | 2 |
| `black_bloc/cogs/content/youtube.py:129` | Done — **{who}**'s YouTube channel is forgotten and their uploads are not announ… | ephemeral answer | no | `youtube_unlinked_for` | 2 |
| `black_bloc/cogs/content/youtube.py:146` | Upload announcements are now **{mode}**. | ephemeral answer | no | `youtube_mode_set` | 2 |
| `black_bloc/cogs/content/youtube.py:147` | Live-stream announcements are now **{mode}**. | ephemeral answer | no | `youtube_live_mode_set` | 2 |
| `black_bloc/cogs/content/youtube.py:154` | A live stream is announced through the go-live feature, and `golive_channel_id` … | ephemeral answer | no | `youtube_live_no_golive_channel` | 2 |
| `black_bloc/cogs/content/youtube.py:158` | Go-live announcements are **{mode}** at the moment, and a YouTube stream is anno… | ephemeral answer | no | `youtube_live_golive_not_on` | 2 |
| `black_bloc/cogs/content/youtube.py:162` | The go-live feature is not loaded right now, so a linked channel going live cann… | ephemeral answer | no | `youtube_live_cog_missing` | 2 |
| `black_bloc/cogs/content/youtube.py:166` | Upload announcements now go to {where}{ping}. | ephemeral answer | no | `youtube_setup_done` | 2 |
| `black_bloc/cogs/content/youtube.py:167` | Nothing was given, so nothing changed. | ephemeral answer | no | `youtube_setup_nothing` | 2 |
| `black_bloc/cogs/content/youtube.py:168` | Uploads have nowhere to go: neither `youtube_channel_id` nor `golive_channel_id`… | ephemeral answer | no | `youtube_no_channel` | 2 |
| `black_bloc/cogs/content/youtube.py:172` | the go-live channel <#{channel}> | ephemeral answer | no | `youtube_falls_back` | 2 |
| `black_bloc/cogs/content/youtube.py:173` | nowhere — neither an upload channel nor a go-live channel is set | ephemeral answer | no | `youtube_nowhere` | 2 |
| `black_bloc/cogs/content/youtube.py:174` | The uploads feature is not loaded right now, so nothing was changed. Tell a Lead… | ephemeral answer | no | `youtube_feature_missing` | 2 |
| `black_bloc/cogs/content/youtube.py:186` | Somebody's channel… | ephemeral answer | no | `youtube_pick_a_channel` | 2 |
| `black_bloc/cogs/content/youtube.py:193` | Whose channel is it? | ephemeral answer | no | `youtube_whose_channel` | 2 |
| `black_bloc/cogs/content/youtube.py:195` | Link your YouTube channel | modal title or field | no | `youtube_link_title` | 2 |
| `black_bloc/cogs/content/youtube.py:196` | Link a channel for {who} | modal title or field | no | `youtube_link_for_title` | 2 |
| `black_bloc/cogs/content/youtube.py:197` | Your channel address, @handle, or UC… id | modal title or field | no | `youtube_link_label` | 2 |
| `black_bloc/cogs/content/youtube.py:198` | Their channel address, @handle, or UC… id | modal title or field | no | `youtube_link_for_label` | 2 |
| `black_bloc/cogs/content/youtube.py:200` | Why? | modal title or field | no | `youtube_unlink_for_title` | 2 |
| `black_bloc/cogs/content/youtube.py:201` | One line they will be sent | modal title or field | no | `youtube_unlink_for_label` | 2 |
| `black_bloc/cogs/content/youtube.py:205` | Where uploads are posted… | ephemeral answer | no | `youtube_where_uploads` | 2 |
| `black_bloc/cogs/content/youtube.py:206` | Who is pinged… | ephemeral answer | no | `youtube_who_is_pinged` | 2 |
| `black_bloc/cogs/content/youtube.py:207` | Shorts: announced | ephemeral answer | no | `youtube_shorts_on` | 2 |
| `black_bloc/cogs/content/youtube.py:208` | Shorts: not announced | ephemeral answer | no | `youtube_shorts_off` | 2 |
| `black_bloc/cogs/content/youtube.py:209` | Fans pinged: on | ephemeral answer | no | `youtube_fans_on` | 2 |
| `black_bloc/cogs/content/youtube.py:210` | Fans pinged: off | ephemeral answer | no | `youtube_fans_off` | 2 |
| `black_bloc/cogs/content/youtube.py:215` | the upload channel — uploads fall back to the go-live one | ephemeral answer | no | `youtube_forget_channel` | 2 |
| `black_bloc/cogs/content/youtube.py:216` | the ping role — nobody is pinged | ephemeral answer | no | `youtube_forget_ping_role` | 2 |
| `black_bloc/cogs/content/youtube.py:217` | What an upload announcement says | modal title or field | no | `youtube_words_title` | 2 |
| `black_bloc/cogs/content/youtube.py:218` | {name} {title} {url} {channel} {kind} | modal title or field | no | `youtube_words_label` | 2 |
| `black_bloc/cogs/content/youtube.py:220` | Numbers | modal title or field | no | `youtube_numbers_title` | 2 |
| `black_bloc/cogs/content/youtube.py:221` | Minutes between checks | modal title or field | no | `youtube_every_label` | 2 |
| `black_bloc/cogs/content/youtube.py:222` | Minutes this panel stays live | modal title or field | no | `youtube_panel_minutes_label` | 2 |
| `black_bloc/cogs/content/youtube.py:223` | **{given}** is not a whole number, so nothing was changed. {label} takes a numbe… | ephemeral answer | no | `youtube_not_a_number` | 2 |
| `black_bloc/cogs/content/youtube.py:227` | Saved. An upload announcement now reads like this: | ephemeral answer | no | `youtube_words_saved` | 2 |
| `black_bloc/youtube.py:55` | I could not turn **{given}** into a YouTube channel id, so nothing was linked. P… | ephemeral answer | no | `youtube_cannot_resolve` | 2 |
| `black_bloc/youtube.py:60` | YouTube's feed server would not answer for that channel after {attempts} tries. … | ephemeral answer | no | `youtube_feed_refused` | 2 |
| `black_bloc/youtube.py:407` | not checked yet | ephemeral answer | no | `youtube_not_seeded_yet` | 2 |
| `black_bloc/youtube.py:408` | Nobody has linked a YouTube channel yet. | ephemeral answer | no | `youtube_nobody_linked` | 2 |
| `black_bloc/youtube.py:409` | **quota used today** — none; with no YOUTUBE_API_KEY a live stream is announced … | ephemeral answer | no | `youtube_live_no_key` | 2 |
| `black_bloc/youtube.py:413` | yes — YouTube served the last probe its *Sign in to confirm you're not a bot* pa… | ephemeral answer | no | `youtube_bot_checked` | 2 |
| `black_bloc/youtube.py:429` | Forget your YouTube channel? Black Bloc stops watching it for new uploads. You c… | ephemeral answer | no | `youtube_unlink_question` | 2 |
| `black_bloc/youtube.py:433` | Yes, forget it | ephemeral answer | no | `youtube_unlink_yes` | 2 |
| `black_bloc/youtube_live.py:26` | YouTube answered {status} for {channel}'s live page. | ephemeral answer | no | `youtube_probe_refused` | 2 |
| `black_bloc/youtube_live.py:27` | YouTube's API said nothing about {video_id}. | ephemeral answer | no | `youtube_confirm_refused` | 2 |

### polls

*267 strings — 1 keyed · 102 unkeyed pass 1 · 152 unkeyed pass 2 · 13 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/polls.py:279` | *(the key's value)* | read from the store at render | **yes → `poll_shadow_note`** (ns `poll`, 1 read site(s)) | — | 1 |
| `black_bloc/api/tools/polls.py:123` | **{question}** is in, but Black Bloc could not post the review card — the log sa… | channel post | no | `poll_created_no_card` | 1 |
| `black_bloc/cogs/community/polls.py:222` | Black Bloc could not post the review card in {channel} — the log says why, and a… | channel post | no | `poll_review_no_card` | 1 |
| `black_bloc/cogs/community/polls.py:263` | Your poll **{question}** was approved on **{guild}** and is up now. | DM | no | `poll_dm_approved` | 1 |
| `black_bloc/cogs/community/polls.py:264` | Your poll **{question}** was not approved on **{guild}**. The reason given was: … | DM | no | `poll_dm_denied` | 1 |
| `black_bloc/cogs/community/polls.py:268` | Your poll **{question}** was approved on **{guild}**, but Black Bloc could not p… | DM | no | `poll_dm_approved_not_posted` | 1 |
| `black_bloc/cogs/community/polls.py:285` | Create | button label | no | `poll_create_button` | 1 |
| `black_bloc/cogs/community/polls.py:286` | Refresh | button label | no | `poll_refresh_button` | 1 |
| `black_bloc/cogs/community/polls.py:287` | Settings | button label | no | `poll_settings_button` | 1 |
| `black_bloc/cogs/community/polls.py:288` | Logs | button label | no | `poll_logs_button` | 1 |
| `black_bloc/cogs/community/polls.py:289` | Back | button label | no | `poll_back_button` | 1 |
| `black_bloc/cogs/community/polls.py:290` | Numbers… | button label | no | `poll_numbers_button` | 1 |
| `black_bloc/cogs/community/polls.py:291` | Clear ping role | button label | no | `poll_clear_ping_button` | 1 |
| `black_bloc/cogs/community/polls.py:292` | Clear channel | button label | no | `poll_clear_channel_button` | 1 |
| `black_bloc/cogs/community/polls.py:293` | Post it | button label | no | `poll_post_button` | 1 |
| `black_bloc/cogs/community/polls.py:294` | Date slots… | button label | no | `poll_slots_button` | 1 |
| `black_bloc/cogs/community/polls.py:295` | Repeat… | button label | no | `poll_repeat_button` | 1 |
| `black_bloc/cogs/community/polls.py:296` | Start over | button label | no | `poll_start_over_button` | 1 |
| `black_bloc/cogs/community/polls.py:297` | Cancel | button label | no | `poll_give_up_button` | 1 |
| `black_bloc/cogs/community/polls.py:298` | Delete | button label | no | `poll_delete_button` | 1 |
| `black_bloc/cogs/community/polls.py:299` | Pause | button label | no | `poll_pause_button` | 1 |
| `black_bloc/cogs/community/polls.py:300` | Resume | button label | no | `poll_resume_button` | 1 |
| `black_bloc/cogs/community/polls.py:301` | Yes, stop it repeating | button label | no | `poll_delete_yes_button` | 1 |
| `black_bloc/cogs/community/polls.py:315` | Poll settings | card title | no | `poll_settings_title` | 1 |
| `black_bloc/cogs/community/polls.py:321` | Nothing is saved until you press **Post it**. | card description | no | `poll_draft_intro` | 1 |
| `black_bloc/cogs/community/polls.py:326` | Save for later | button label | no | `poll_save_button` | 1 |
| `black_bloc/cogs/community/polls.py:327` | Save (replaces your draft) | button label | no | `poll_save_replaces_button` | 1 |
| `black_bloc/cogs/community/polls.py:328` | Resume draft | button label | no | `poll_resume_draft_button` | 1 |
| `black_bloc/cogs/community/polls.py:329` | Discard draft | button label | no | `poll_discard_button` | 1 |
| `black_bloc/cogs/community/polls.py:330` | Discard | button label | no | `poll_discard_staff_button` | 1 |
| `black_bloc/cogs/community/polls.py:331` | Yes, discard it | button label | no | `poll_discard_yes_button` | 1 |
| `black_bloc/cogs/community/polls.py:362` | Staff removed your saved poll draft **{question}** on **{guild}**: {reason}. Not… | DM | no | `poll_dm_draft_discarded` | 1 |
| `black_bloc/cogs/community/polls.py:366` | This is your saved draft. **Post it** puts it up and clears the draft. | card description | no | `poll_resumed_intro` | 1 |
| `black_bloc/cogs/community/polls.py:2252` | Where | card field name | no | `poll_card_where` | 1 |
| `black_bloc/cogs/community/polls.py:2257` | Ping | card field name | no | `poll_card_ping` | 1 |
| `black_bloc/cogs/community/polls.py:2260` | Thread | card field name | no | `poll_card_thread` | 1 |
| `black_bloc/cogs/community/polls.py:2263` | Repeats | card field name | no | `poll_card_repeats` | 1 |
| `black_bloc/cogs/community/polls.py:2270` | Slots | card field name | no | `poll_card_slots` | 1 |
| `black_bloc/cogs/community/polls.py:3149` | Pizza \| Tacos \| Neither | select placeholder | no | `poll_placeholder_pizza_tacos_neither` | 1 |
| `black_bloc/cogs/community/polls.py:3170` | What are you asking? | message content | no | `poll_line_what_are_you_asking` | 1 |
| `black_bloc/cogs/community/polls.py:3172` | The answers, separated by \| | message content | no | `poll_line_the_answers_separated_by` | 1 |
| `black_bloc/cogs/community/polls.py:3176` | How many hours? (blank for the server default) | message content | no | `poll_line_how_many_hours_blank_for_the_server_defa` | 1 |
| `black_bloc/cogs/community/polls.py:3211` | First slot — 2026-09-05 or 2026-09-05 19:00 | message content | no | `poll_line_first_slot_2026_09_05_or_2026_09_05_19_0` | 1 |
| `black_bloc/cogs/community/polls.py:3247` | Time of day, 24-hour clock | message content | no | `poll_line_time_of_day_24_hour_clock` | 1 |
| `black_bloc/cogs/community/polls.py:3254` | Timezone | message content | no | `poll_line_timezone` | 1 |
| `black_bloc/cogs/community/polls.py:3326` | How long a poll stays open, in hours | card field | no | `poll_number_fields` | 1 |
| `black_bloc/cogs/community/polls.py:3326` | Last call, minutes before close (0 for none) | card field | no | `poll_number_fields_2` | 1 |
| `black_bloc/cogs/community/polls.py:3326` | Days a closed poll stays on the list | card field | no | `poll_number_fields_3` | 1 |
| `black_bloc/cogs/community/polls.py:3326` | Minutes this panel stays live | card field | no | `poll_number_fields_4` | 1 |
| `black_bloc/cogs/community/polls.py:3326` | Days a saved draft is kept (0 for ever) | card field | no | `poll_number_fields_5` | 1 |
| `black_bloc/polls.py:66` | %a %d %b | card field | no | `poll_day_label` | 1 |
| `black_bloc/polls.py:73` | Monday | card field | no | `poll_weekday_names` | 1 |
| `black_bloc/polls.py:73` | Tuesday | card field | no | `poll_weekday_names_2` | 1 |
| `black_bloc/polls.py:73` | Wednesday | card field | no | `poll_weekday_names_3` | 1 |
| `black_bloc/polls.py:73` | Thursday | card field | no | `poll_weekday_names_4` | 1 |
| `black_bloc/polls.py:73` | Friday | card field | no | `poll_weekday_names_5` | 1 |
| `black_bloc/polls.py:73` | Saturday | card field | no | `poll_weekday_names_6` | 1 |
| `black_bloc/polls.py:73` | Sunday | card field | no | `poll_weekday_names_7` | 1 |
| `black_bloc/polls.py:124` | A **free text** poll | card field | no | `poll_later_kind_names` | 1 |
| `black_bloc/polls.py:124` | A **number** poll | card field | no | `poll_later_kind_names_2` | 1 |
| `black_bloc/polls.py:124` | A **ranked choice** poll | card field | no | `poll_later_kind_names_3` | 1 |
| `black_bloc/polls.py:284` | Posted here because polls are in **shadow** — it would have gone to {channel}. | card description | no | `poll_shadow_note` | 1 |
| `black_bloc/polls.py:292` | · **{shadow}** posted in shadow | channel post | no | `poll_panel_shadow_line` | 1 |
| `black_bloc/polls.py:297` | Polls | card title | no | `poll_panel_title` | 1 |
| `black_bloc/polls.py:298` | Put something to the room, or look at what is already running. | card description | no | `poll_panel_intro` | 1 |
| `black_bloc/polls.py:299` | This panel has gone quiet — run /poll again | card description | no | `poll_panel_timeout_footer` | 1 |
| `black_bloc/polls.py:305` | Find #… | button label | no | `poll_find_button` | 1 |
| `black_bloc/polls.py:308` | Repeats: {question} | card title | no | `poll_recurrence_title` | 1 |
| `black_bloc/polls.py:311` | {question} | card title | no | `poll_results_title` | 1 |
| `black_bloc/polls.py:313` | <- winner | channel post | no | `poll_winner_mark` | 1 |
| `black_bloc/polls.py:674` | Status | card field name | no | `poll_card_status` | 1 |
| `black_bloc/polls.py:676` | Votes | card field name | no | `poll_card_votes` | 1 |
| `black_bloc/polls.py:682` | Average | card field name | no | `poll_card_average` | 1 |
| `black_bloc/polls.py:687` | Winner | card field name | no | `poll_card_winner` | 1 |
| `black_bloc/polls.py:689` | Closed | card field name | no | `poll_card_closed` | 1 |
| `black_bloc/polls.py:727` | Status | card field name | no | `poll_card_status_2` | 1 |
| `black_bloc/polls.py:728` | Voters | card field name | no | `poll_card_voters` | 1 |
| `black_bloc/polls.py:729` | How | card field name | no | `poll_card_how` | 1 |
| `black_bloc/polls.py:731` | Results | card field name | no | `poll_card_results` | 1 |
| `black_bloc/polls.py:733` | Anonymous | card field name | no | `poll_card_anonymous` | 1 |
| `black_bloc/polls.py:738` | Average | card field name | no | `poll_card_average_2` | 1 |
| `black_bloc/polls.py:741` | Closes | card field name | no | `poll_card_closes` | 1 |
| `black_bloc/polls.py:771` | Who | card field name | no | `poll_card_who` | 1 |
| `black_bloc/polls.py:772` | Status | card field name | no | `poll_card_status_3` | 1 |
| `black_bloc/polls.py:773` | Kind | card field name | no | `poll_card_kind` | 1 |
| `black_bloc/polls.py:774` | Open for | card field name | no | `poll_card_open_for` | 1 |
| `black_bloc/polls.py:778` | Options | card field name | no | `poll_card_options` | 1 |
| `black_bloc/polls.py:780` | Why not | card field name | no | `poll_card_why_not` | 1 |
| `black_bloc/polls.py:956` | Repeats | card field name | no | `poll_card_repeats_2` | 1 |
| `black_bloc/polls.py:958` | Next | card field name | no | `poll_card_next` | 1 |
| `black_bloc/polls.py:963` | Where | card field name | no | `poll_card_where_2` | 1 |
| `black_bloc/polls.py:965` | Kind | card field name | no | `poll_card_kind_2` | 1 |
| `black_bloc/polls.py:966` | Open for | card field name | no | `poll_card_open_for_2` | 1 |
| `black_bloc/polls.py:970` | Options | card field name | no | `poll_card_options_2` | 1 |
| `black_bloc/polls.py:975` | Saved draft | card title | no | `poll_draft_title` | 1 |
| `black_bloc/polls.py:976` | You have a saved draft: **{question}** — saved {when} | channel post | no | `poll_draft_line` | 1 |
| `black_bloc/polls.py:977` | · **{drafts}** saved draft(s) | channel post | no | `poll_draft_staff_line` | 1 |
| `black_bloc/polls.py:1086` | Who | card field name | no | `poll_card_who_2` | 1 |
| `black_bloc/polls.py:1087` | Kind | card field name | no | `poll_card_kind_3` | 1 |
| `black_bloc/polls.py:1088` | Open for | card field name | no | `poll_card_open_for_3` | 1 |
| `black_bloc/polls.py:1090` | Where | card field name | no | `poll_card_where_3` | 1 |
| `black_bloc/polls.py:1093` | Saved | card field name | no | `poll_card_saved` | 1 |
| `black_bloc/polls.py:1100` | Options | card field name | no | `poll_card_options_3` | 1 |
| `black_bloc/api/tools/polls.py:77` | text/csv | ephemeral answer | no | `poll_csv_media_type` | 2 |
| `black_bloc/api/tools/polls.py:79` | Black Bloc has no poll **#{poll_id}** any more, so nothing was done. The polls p… | ephemeral answer | no | `poll_no_such_poll` | 2 |
| `black_bloc/api/tools/polls.py:83` | **{given}** is not a state a poll can be in, so nothing was listed. They are {kn… | ephemeral answer | no | `poll_unknown_status` | 2 |
| `black_bloc/api/tools/polls.py:86` | Poll **#{poll_id}** is **{status}** already, so there was nothing to close. | ephemeral answer | no | `poll_not_closeable` | 2 |
| `black_bloc/api/tools/polls.py:87` | Poll **#{poll_id}** is **{status}** already, so there was nothing to cancel. | ephemeral answer | no | `poll_not_cancellable` | 2 |
| `black_bloc/api/tools/polls.py:88` | Poll **#{poll_id}** is **{status}**, so it is not waiting on a decision any more… | ephemeral answer | no | `poll_not_waiting` | 2 |
| `black_bloc/api/tools/polls.py:92` | A denied poll needs one line the person who asked is sent, so nothing was done. … | ephemeral answer | no | `poll_deny_needs_a_reason` | 2 |
| `black_bloc/api/tools/polls.py:96` | Poll #{poll_id} is marked closed, but Black Bloc could not read the final count … | ephemeral answer | no | `poll_closed_no_result` | 2 |
| `black_bloc/api/tools/polls.py:100` | Poll #{poll_id} is closed and the result is posted. | ephemeral answer | no | `poll_closed_said` | 2 |
| `black_bloc/api/tools/polls.py:101` | Poll #{poll_id} is cancelled. No result was published. | ephemeral answer | no | `poll_cancelled_said` | 2 |
| `black_bloc/api/tools/polls.py:102` | This poll was run without a voter list, so there is nothing per-person to export… | ephemeral answer | no | `poll_votes_are_anonymous` | 2 |
| `black_bloc/api/tools/polls.py:106` | This poll has been archived and its per-voter rows were dropped, which is what `… | ephemeral answer | no | `poll_votes_were_dropped` | 2 |
| `black_bloc/api/tools/polls.py:110` | Black Bloc has nowhere to put this poll, so nothing was posted. Pick a channel o… | ephemeral answer | no | `poll_no_channel_picked` | 2 |
| `black_bloc/api/tools/polls.py:114` | Discord would not take the poll, so nothing went up and the draft is marked canc… | ephemeral answer | no | `poll_could_not_post` | 2 |
| `black_bloc/api/tools/polls.py:118` | **{question}** is up in <#{channel_id}>. | ephemeral answer | no | `poll_created_posted` | 2 |
| `black_bloc/api/tools/polls.py:119` | **{question}** is in — a Lead has to approve it before it posts, and the person … | ephemeral answer | no | `poll_created_held` | 2 |
| `black_bloc/api/tools/polls.py:127` | Staff review is on but Black Bloc has nowhere to send a poll for it, so nothing … | ephemeral answer | no | `poll_no_review_channel` | 2 |
| `black_bloc/api/tools/polls.py:131` | Black Bloc has no repeating poll **#{poll_id}**, so nothing was done. It may hav… | ephemeral answer | no | `poll_recur_not_a_recurrence` | 2 |
| `black_bloc/api/tools/polls.py:135` | **{question}** is paused. Nothing opens until it is started again. | ephemeral answer | no | `poll_recur_paused_said` | 2 |
| `black_bloc/api/tools/polls.py:136` | **{question}** is running again. | ephemeral answer | no | `poll_recur_resumed_said` | 2 |
| `black_bloc/api/tools/polls.py:137` | **{question}** will not run again. Polls it already opened are untouched. | ephemeral answer | no | `poll_recur_deleted_said` | 2 |
| `black_bloc/api/tools/polls.py:138` | Black Bloc cannot work out when **{question}** would next run, so it was left pa… | ephemeral answer | no | `poll_recur_unreadable` | 2 |
| `black_bloc/api/tools/polls.py:142` | Black Bloc could not work out when that would next come round, so nothing was sa… | ephemeral answer | no | `poll_recur_not_worked_out` | 2 |
| `black_bloc/api/tools/polls.py:146` | **{question}** will run {cadence}. Nothing is posted yet — the Repeating section… | ephemeral answer | no | `poll_recur_created_said` | 2 |
| `black_bloc/cogs/community/polls.py:198` | Polls are turned off on this server, so nothing was posted. A Lead turns them ba… | ephemeral answer | no | `poll_polls_off` | 2 |
| `black_bloc/cogs/community/polls.py:202` | Polls are staff-only on this server right now, so nothing was posted. Ask a Lead… | ephemeral answer | no | `poll_not_a_creator` | 2 |
| `black_bloc/cogs/community/polls.py:206` | Black Bloc could not work out which channel this poll would go in, so nothing wa… | ephemeral answer | no | `poll_no_channel` | 2 |
| `black_bloc/cogs/community/polls.py:210` | Discord refused to post the poll, so nothing went up. Black Bloc needs Send Mess… | ephemeral answer | no | `poll_cannot_post` | 2 |
| `black_bloc/cogs/community/polls.py:214` | Your poll is up: {url} | ephemeral answer | no | `poll_posted` | 2 |
| `black_bloc/cogs/community/polls.py:215` | Your poll is up in this channel. | ephemeral answer | no | `poll_posted_no_link` | 2 |
| `black_bloc/cogs/community/polls.py:216` | Black Bloc could not open the discussion thread; the log says why. | ephemeral answer | no | `poll_thread_failed` | 2 |
| `black_bloc/cogs/community/polls.py:217` | **{question}** is in — a Lead will approve or deny it and Black Bloc will DM you… | ephemeral answer | no | `poll_sent_for_review` | 2 |
| `black_bloc/cogs/community/polls.py:221` | Their card is in {channel}. | ephemeral answer | no | `poll_review_here` | 2 |
| `black_bloc/cogs/community/polls.py:226` | Black Bloc has nowhere to send a poll for review, so nothing was posted. A Lead … | ephemeral answer | no | `poll_no_review_channel_2` | 2 |
| `black_bloc/cogs/community/polls.py:231` | **{given}** is not a poll number, so nothing was done. This panel lists them. | ephemeral answer | no | `poll_not_an_id` | 2 |
| `black_bloc/cogs/community/polls.py:232` | Black Bloc has no record of that poll any more, so nothing was done. This panel … | ephemeral answer | no | `poll_no_such_poll_2` | 2 |
| `black_bloc/cogs/community/polls.py:236` | Poll #{poll_id} is already **{status}**, so nothing was changed. | ephemeral answer | no | `poll_not_open` | 2 |
| `black_bloc/cogs/community/polls.py:237` | Poll #{poll_id} is not yours, so nothing was closed. Only the person who started… | ephemeral answer | no | `poll_not_yours` | 2 |
| `black_bloc/cogs/community/polls.py:241` | Denied, and the person who asked has been told why. | ephemeral answer | no | `poll_denied_said` | 2 |
| `black_bloc/cogs/community/polls.py:242` | Approved and posted: {where} | ephemeral answer | no | `poll_approved_posted` | 2 |
| `black_bloc/cogs/community/polls.py:243` | Approved, but nothing was posted, so the poll is marked cancelled — the log says… | ephemeral answer | no | `poll_approved_not_posted` | 2 |
| `black_bloc/cogs/community/polls.py:247` | Poll #{poll_id} is closed and the result is posted. | ephemeral answer | no | `poll_ended` | 2 |
| `black_bloc/cogs/community/polls.py:248` | Poll #{poll_id} is marked closed, but Black Bloc could not read the final count … | ephemeral answer | no | `poll_ended_no_result` | 2 |
| `black_bloc/cogs/community/polls.py:252` | Poll #{poll_id} is cancelled. The vote is closed at Discord and no result was po… | ephemeral answer | no | `poll_cancelled_said_2` | 2 |
| `black_bloc/cogs/community/polls.py:255` | Somebody got there first — poll #{poll_id} is already **{status}**, so nothing w… | ephemeral answer | no | `poll_already_decided` | 2 |
| `black_bloc/cogs/community/polls.py:258` | Nothing is running — **Create** starts one. | ephemeral answer | no | `poll_no_open_polls` | 2 |
| `black_bloc/cogs/community/polls.py:259` | Black Bloc is in **test mode**, so it will not touch a poll outside <#{channel_i… | ephemeral answer | no | `poll_guarded` | 2 |
| `black_bloc/cogs/community/polls.py:272` | ⚠️ **No staff roles resolve**, so nobody but server admins can press Approve. Po… | ephemeral answer | no | `poll_no_staff_warning` | 2 |
| `black_bloc/cogs/community/polls.py:303` | Thread: on | ephemeral answer | no | `poll_thread_on` | 2 |
| `black_bloc/cogs/community/polls.py:304` | Thread: off | ephemeral answer | no | `poll_thread_off` | 2 |
| `black_bloc/cogs/community/polls.py:305` | Find a poll | modal title or field | no | `poll_find_title` | 2 |
| `black_bloc/cogs/community/polls.py:306` | The poll number, like 12 | modal title or field | no | `poll_find_label` | 2 |
| `black_bloc/cogs/community/polls.py:308` | New poll | modal title or field | no | `poll_create_title` | 2 |
| `black_bloc/cogs/community/polls.py:309` | Date slots | modal title or field | no | `poll_slots_title` | 2 |
| `black_bloc/cogs/community/polls.py:310` | Repeat this poll | modal title or field | no | `poll_cadence_title` | 2 |
| `black_bloc/cogs/community/polls.py:311` | Poll numbers | modal title or field | no | `poll_numbers_title` | 2 |
| `black_bloc/cogs/community/polls.py:312` | Why not? | modal title or field | no | `poll_deny_title` | 2 |
| `black_bloc/cogs/community/polls.py:313` | One line the person who asked will be sent | modal title or field | no | `poll_deny_label` | 2 |
| `black_bloc/cogs/community/polls.py:316` | Date slot labels… | ephemeral answer | no | `poll_date_labels_pick` | 2 |
| `black_bloc/cogs/community/polls.py:317` | Where dashboard polls go… | ephemeral answer | no | `poll_settings_channel_pick` | 2 |
| `black_bloc/cogs/community/polls.py:318` | Ping role… | ephemeral answer | no | `poll_settings_role_pick` | 2 |
| `black_bloc/cogs/community/polls.py:319` | Post it in… | ephemeral answer | no | `poll_draft_channel_pick` | 2 |
| `black_bloc/cogs/community/polls.py:320` | Ping… | ephemeral answer | no | `poll_draft_role_pick` | 2 |
| `black_bloc/cogs/community/polls.py:322` | A date poll needs its slots before it can go up — press **Date slots…**. | ephemeral answer | no | `poll_draft_needs_slots` | 2 |
| `black_bloc/cogs/community/polls.py:323` | Only staff can close this poll early on this server, so nothing was changed. Ask… | ephemeral answer | no | `poll_not_yours_to_end` | 2 |
| `black_bloc/cogs/community/polls.py:332` | Saved. Resume it from this panel any time. | ephemeral answer | no | `poll_draft_saved` | 2 |
| `black_bloc/cogs/community/polls.py:333` | Saved, and it replaced the draft you had — one per person. Resume it from this p… | ephemeral answer | no | `poll_draft_replaced` | 2 |
| `black_bloc/cogs/community/polls.py:337` | That draft is gone and nothing was posted. **Create** starts a fresh one. | ephemeral answer | no | `poll_draft_discarded` | 2 |
| `black_bloc/cogs/community/polls.py:338` | Black Bloc has no saved draft of yours any more, so there was nothing to open. I… | ephemeral answer | no | `poll_draft_gone` | 2 |
| `black_bloc/cogs/community/polls.py:342` | Saved drafts are turned off on this server, so nothing was saved. A Lead turns t… | ephemeral answer | no | `poll_drafts_off` | 2 |
| `black_bloc/cogs/community/polls.py:346` | Black Bloc has no saved draft for that person any more, so nothing was discarded… | ephemeral answer | no | `poll_draft_not_theirs` | 2 |
| `black_bloc/cogs/community/polls.py:350` | Discard this saved draft? They are DM'd the reason you give on the next screen, … | ephemeral answer | no | `poll_draft_discard_ask` | 2 |
| `black_bloc/cogs/community/polls.py:354` | Throw this draft away? Nothing is posted either way and nobody else is told. | ephemeral answer | no | `poll_draft_discard_mine_ask` | 2 |
| `black_bloc/cogs/community/polls.py:357` | Why is it going? | modal title or field | no | `poll_draft_discard_title` | 2 |
| `black_bloc/cogs/community/polls.py:358` | One line the person who saved it will be sent | modal title or field | no | `poll_draft_discard_label` | 2 |
| `black_bloc/cogs/community/polls.py:360` | That draft is discarded and they have been told why. | ephemeral answer | no | `poll_draft_discard_said` | 2 |
| `black_bloc/cogs/community/polls.py:361` | Black Bloc could not DM them, so tell them yourself — the log says why. | DM | no | `poll_draft_dm_failed` | 2 |
| `black_bloc/cogs/community/polls.py:367` | Nobody is told who voted | ephemeral answer | no | `poll_switch_anonymous` | 2 |
| `black_bloc/cogs/community/polls.py:368` | Hide the bars until it closes | ephemeral answer | no | `poll_switch_hidden` | 2 |
| `black_bloc/cogs/community/polls.py:370` | Anything else? | modal title or field | no | `poll_switches_label` | 2 |
| `black_bloc/cogs/community/polls.py:371` | How often? | modal title or field | no | `poll_cadence_label` | 2 |
| `black_bloc/cogs/community/polls.py:372` | Counted in | modal title or field | no | `poll_step_unit_label` | 2 |
| `black_bloc/cogs/community/polls.py:1986` | One line the person who asked will be sent | modal field label | no | `poll_modal_one_line_the_person_who_asked_will_be_se` | 2 |
| `black_bloc/cogs/community/polls.py:3318` | Polls | ephemeral answer | no | `poll_settings_toggles` | 2 |
| `black_bloc/cogs/community/polls.py:3318` | Create | ephemeral answer | no | `poll_settings_toggles_2` | 2 |
| `black_bloc/cogs/community/polls.py:3318` | Review | ephemeral answer | no | `poll_settings_toggles_3` | 2 |
| `black_bloc/cogs/community/polls.py:3318` | Threads | ephemeral answer | no | `poll_settings_toggles_4` | 2 |
| `black_bloc/cogs/community/polls.py:3318` | Drop votes | ephemeral answer | no | `poll_settings_toggles_5` | 2 |
| `black_bloc/cogs/community/polls.py:3318` | Drafts | ephemeral answer | no | `poll_settings_toggles_6` | 2 |
| `black_bloc/cogs/community/polls.py:3343` | **{given}** is not a whole number between {low} and {high}, so nothing was saved… | ephemeral answer | no | `poll_not_a_number` | 2 |
| `black_bloc/polls.py:64` | %Y-%m-%d | ephemeral answer | no | `poll_day_format` | 2 |
| `black_bloc/polls.py:65` | %Y-%m-%d %H:%M | ephemeral answer | no | `poll_day_time_format` | 2 |
| `black_bloc/polls.py:77` | %H:%M | ephemeral answer | no | `poll_clock_format` | 2 |
| `black_bloc/polls.py:130` | that kind of poll arrives with the next update | ephemeral answer | no | `poll_next_update` | 2 |
| `black_bloc/polls.py:137` | **{count}** options is more than the {limit} Black Bloc can put on one poll, so … | ephemeral answer | no | `poll_too_many` | 2 |
| `black_bloc/polls.py:142` | Discord's own polls list everybody who voted, so an **anonymous** one cannot be … | ephemeral answer | no | `poll_panel_because_anonymous` | 2 |
| `black_bloc/polls.py:145` | Discord's own polls show the bars as the votes come in and there is no way to hi… | ephemeral answer | no | `poll_panel_because_hidden` | 2 |
| `black_bloc/polls.py:148` | **{count}** options is more than the {limit} a Discord poll carries | ephemeral answer | no | `poll_panel_because_long` | 2 |
| `black_bloc/polls.py:149` | This one is a Black Bloc panel rather than a Discord poll, because {why}. People… | ephemeral answer | no | `poll_panel_said` | 2 |
| `black_bloc/polls.py:154` | A poll needs a question, so nothing was posted. Put the thing you are asking in … | ephemeral answer | no | `poll_no_question` | 2 |
| `black_bloc/polls.py:158` | That question is **{given}** characters and Discord allows {limit}, so nothing w… | ephemeral answer | no | `poll_question_too_long` | 2 |
| `black_bloc/polls.py:162` | A poll needs at least {limit} options and this one has **{given}**, so nothing w… | ephemeral answer | no | `poll_too_few_options` | 2 |
| `black_bloc/polls.py:166` | The option **{given}** is longer than the {limit} characters Discord allows on a… | ephemeral answer | no | `poll_label_too_long` | 2 |
| `black_bloc/polls.py:170` | **{given}** is in the options twice, so nothing was posted — two identical answe… | ephemeral answer | no | `poll_duplicate_option` | 2 |
| `black_bloc/polls.py:174` | **{given}** is not a length Black Bloc can give a poll, so nothing was posted. D… | ephemeral answer | no | `poll_bad_hours` | 2 |
| `black_bloc/polls.py:179` | **{given}** is not a date Black Bloc can read, so nothing was posted. Write it a… | ephemeral answer | no | `poll_bad_start` | 2 |
| `black_bloc/polls.py:183` | A date poll needs between {low} and {high} slots and this one asked for **{given… | ephemeral answer | no | `poll_bad_slots` | 2 |
| `black_bloc/polls.py:187` | **{given}** is not a gap Black Bloc can leave between two slots, so nothing was … | ephemeral answer | no | `poll_bad_step` | 2 |
| `black_bloc/polls.py:191` | **{given}** is not a unit a date poll can step by, so nothing was posted. It is … | ephemeral answer | no | `poll_bad_step_unit` | 2 |
| `black_bloc/polls.py:195` | A date poll needs a start date, so nothing was posted. Give it one with `start:2… | ephemeral answer | no | `poll_date_needs_a_start` | 2 |
| `black_bloc/polls.py:200` | Press an option to vote. Pressing a different one moves your vote. | ephemeral answer | no | `poll_panel_how_one` | 2 |
| `black_bloc/polls.py:201` | Press everything that works for you. Pressing one again takes it back. | ephemeral answer | no | `poll_panel_how_many` | 2 |
| `black_bloc/polls.py:202` | Hidden until this closes, so nobody's vote is swayed by the bars. | ephemeral answer | no | `poll_panel_hidden` | 2 |
| `black_bloc/polls.py:203` | Nobody is told who pressed what — Black Bloc does not keep your name against a v… | ephemeral answer | no | `poll_panel_anonymous` | 2 |
| `black_bloc/polls.py:206` | Vote | ephemeral answer | no | `poll_panel_vote` | 2 |
| `black_bloc/polls.py:207` | Clear my vote | ephemeral answer | no | `poll_panel_clear` | 2 |
| `black_bloc/polls.py:209` | Your vote is on **{label}**. | ephemeral answer | no | `poll_voted_one` | 2 |
| `black_bloc/polls.py:210` | You have {labels}. | ephemeral answer | no | `poll_voted_many` | 2 |
| `black_bloc/polls.py:211` | Your vote is cleared, so nothing of yours counts towards this poll now. | ephemeral answer | no | `poll_vote_cleared` | 2 |
| `black_bloc/polls.py:212` | That poll is **{status}**, so nothing was counted. The result on the message is … | ephemeral answer | no | `poll_vote_not_open` | 2 |
| `black_bloc/polls.py:215` | Black Bloc has no record of that poll any more, so nothing was counted. It may h… | ephemeral answer | no | `poll_vote_gone` | 2 |
| `black_bloc/polls.py:221` | Black Bloc cannot count a vote on this anonymous poll just now, so nothing was c… | ephemeral answer | no | `poll_vote_key_missing` | 2 |
| `black_bloc/polls.py:226` | polls: POLL_VOTE_SECRET is not set, so a new anonymous poll keeps the old per-po… | ephemeral answer | no | `poll_poll_secret_unset` | 2 |
| `black_bloc/polls.py:236` | **{given}** is not a time of day Black Bloc can read, so nothing was saved. Writ… | ephemeral answer | no | `poll_bad_clock` | 2 |
| `black_bloc/polls.py:240` | **{given}** is not a day of the week, so nothing was saved. A weekly poll runs o… | ephemeral answer | no | `poll_bad_weekday` | 2 |
| `black_bloc/polls.py:244` | **{given}** is not a day of the month Black Bloc will use, so nothing was saved.… | ephemeral answer | no | `poll_bad_month_day` | 2 |
| `black_bloc/polls.py:248` | **{given}** is not a timezone this machine knows, so nothing was saved. Write it… | ephemeral answer | no | `poll_bad_zone` | 2 |
| `black_bloc/polls.py:252` | A **date** poll cannot recur, so nothing was saved — its slots are fixed days, a… | ephemeral answer | no | `poll_recur_not_a_date` | 2 |
| `black_bloc/polls.py:257` | No poll is set to repeat. **Repeat…** while you are writing one starts it off. | ephemeral answer | no | `poll_recur_none` | 2 |
| `black_bloc/polls.py:258` | **{question}** will run {cadence}. The first one opens <t:{when}:R>. | ephemeral answer | no | `poll_recur_saved` | 2 |
| `black_bloc/polls.py:259` | **{question}** is paused. Nothing opens until it is started again. | ephemeral answer | no | `poll_recur_paused` | 2 |
| `black_bloc/polls.py:260` | **{question}** is running again. The next one opens <t:{when}:R>. | ephemeral answer | no | `poll_recur_resumed` | 2 |
| `black_bloc/polls.py:261` | **{question}** will not run again. Polls it already opened are untouched. | ephemeral answer | no | `poll_recur_deleted` | 2 |
| `black_bloc/polls.py:262` | Black Bloc has no repeating poll **#{poll_id}**, so nothing was done. The `/poll… | ephemeral answer | no | `poll_not_a_recurrence` | 2 |
| `black_bloc/polls.py:266` | every day at {clock} {zone} | ephemeral answer | no | `poll_cadence_daily` | 2 |
| `black_bloc/polls.py:267` | every {day} at {clock} {zone} | ephemeral answer | no | `poll_cadence_weekly` | 2 |
| `black_bloc/polls.py:268` | on the {day}{ordinal} of each month at {clock} {zone} | ephemeral answer | no | `poll_cadence_monthly` | 2 |
| `black_bloc/polls.py:285` | no channel | ephemeral answer | no | `poll_no_channel_word` | 2 |
| `black_bloc/polls.py:286` | a channel Black Bloc cannot see | ephemeral answer | no | `poll_channel_unseen` | 2 |
| `black_bloc/polls.py:293` | Black Bloc keeps a poll pinned while it is open | ephemeral answer | no | `poll_pin_reason` | 2 |
| `black_bloc/polls.py:294` | the poll is closed | ephemeral answer | no | `poll_unpin_reason` | 2 |
| `black_bloc/polls.py:300` | **{running}** running · **{waiting}** waiting on a decision · **{repeating}** re… | ephemeral answer | no | `poll_panel_counts` | 2 |
| `black_bloc/polls.py:303` | Pick a poll… | ephemeral answer | no | `poll_pick_a_poll` | 2 |
| `black_bloc/polls.py:304` | Repeating polls… | ephemeral answer | no | `poll_pick_a_recurrence` | 2 |
| `black_bloc/polls.py:307` | nothing moves a {status} poll now | ephemeral answer | no | `poll_no_moves_left` | 2 |
| `black_bloc/polls.py:309` | paused — nothing opens until it is started again | ephemeral answer | no | `poll_recurrence_paused` | 2 |
| `black_bloc/polls.py:312` | Nobody voted. | ephemeral answer | no | `poll_no_votes` | 2 |
| `black_bloc/polls.py:314` | It is a tie between {names}. | ephemeral answer | no | `poll_tied` | 2 |
| `black_bloc/polls.py:315` | Average rating: **{mean}** out of {top}. | ephemeral answer | no | `poll_average` | 2 |
| `black_bloc/polls.py:978` | Saved drafts… | ephemeral answer | no | `poll_draft_pick` | 2 |
| `black_bloc/polls.py:979` | somebody who has left | ephemeral answer | no | `poll_draft_nobody` | 2 |
| `black_bloc/polls.py:980` | no question yet | ephemeral answer | no | `poll_draft_no_question` | 2 |

### birthdays

*59 strings — 1 keyed · 26 unkeyed pass 1 · 31 unkeyed pass 2 · 2 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/cogs/community/birthdays.py:1096` | *(the key's value)* | read from the store at render | **yes → `birthday_template`** (ns `birthday`, 3 read site(s)) | — | 1 |
| `black_bloc/birthdays.py:30` | Birthdays | card title | no | `birthday_panel_title` | 1 |
| `black_bloc/birthdays.py:31` | Tell Black Bloc when your birthday is, and see whose is coming up. | card description | no | `birthday_panel_intro` | 1 |
| `black_bloc/birthdays.py:32` | This panel has gone quiet — run /birthday again | card description | no | `birthday_panel_timeout_footer` | 1 |
| `black_bloc/birthdays.py:50` | Your birthday — MM-DD, or MM-DD-YYYY | card field | no | `birthday_date_label` | 1 |
| `black_bloc/birthdays.py:51` | 09-15 or 09-15-1994 | select placeholder | no | `birthday_date_placeholder` | 1 |
| `black_bloc/birthdays.py:58` | Look someone up… | select placeholder | no | `birthday_lookup_placeholder` | 1 |
| `black_bloc/birthdays.py:59` | List a month… | select placeholder | no | `birthday_month_placeholder` | 1 |
| `black_bloc/birthdays.py:61` | Wishes are… | select placeholder | no | `birthday_mode_placeholder` | 1 |
| `black_bloc/birthdays.py:77` | January | card field | no | `birthday_month_names` | 1 |
| `black_bloc/birthdays.py:77` | February | card field | no | `birthday_month_names_2` | 1 |
| `black_bloc/birthdays.py:77` | March | card field | no | `birthday_month_names_3` | 1 |
| `black_bloc/birthdays.py:77` | April | card field | no | `birthday_month_names_4` | 1 |
| `black_bloc/birthdays.py:77` | May | card field | no | `birthday_month_names_5` | 1 |
| `black_bloc/birthdays.py:77` | June | card field | no | `birthday_month_names_6` | 1 |
| `black_bloc/birthdays.py:77` | July | card field | no | `birthday_month_names_7` | 1 |
| `black_bloc/birthdays.py:77` | August | card field | no | `birthday_month_names_8` | 1 |
| `black_bloc/birthdays.py:77` | September | card field | no | `birthday_month_names_9` | 1 |
| `black_bloc/birthdays.py:77` | October | card field | no | `birthday_month_names_10` | 1 |
| `black_bloc/birthdays.py:77` | November | card field | no | `birthday_month_names_11` | 1 |
| `black_bloc/birthdays.py:77` | December | card field | no | `birthday_month_names_12` | 1 |
| `black_bloc/cogs/community/birthdays.py:837` | Status | button label | no | `birthday_button_status` | 1 |
| `black_bloc/cogs/community/birthdays.py:846` | Clear the birthday role | button label | no | `birthday_button_clear_the_birthday_role` | 1 |
| `black_bloc/cogs/community/birthdays.py:855` | Logs | button label | no | `birthday_button_logs` | 1 |
| `black_bloc/cogs/community/birthdays.py:863` | Back | button label | no | `birthday_button_back` | 1 |
| `black_bloc/cogs/community/birthdays.py:871` | Set their birthday | button label | no | `birthday_button_set_their_birthday` | 1 |
| `black_bloc/cogs/community/birthdays.py:883` | Forget their birthday | button label | no | `birthday_button_forget_their_birthday` | 1 |
| `black_bloc/api/tools/birthdays.py:41` | Black Bloc has no birthday stored for **{user_id}**, so there was nothing to rem… | ephemeral answer | no | `birthday_no_birthday` | 2 |
| `black_bloc/api/tools/birthdays.py:45` | A birthday needs a month and a day, so nothing was stored. Pick both and send it… | ephemeral answer | no | `birthday_needs_a_date` | 2 |
| `black_bloc/api/tools/birthdays.py:48` | **{name}** gets a birthday wish again. | ephemeral answer | no | `birthday_wished` | 2 |
| `black_bloc/api/tools/birthdays.py:49` | **{name}** is opted out, so Black Bloc says nothing on their birthday. | ephemeral answer | no | `birthday_not_wished` | 2 |
| `black_bloc/api/tools/birthdays.py:50` | There is no Birthday Bot export to read, so nothing was imported. The seed file … | ephemeral answer | no | `birthday_import_empty` | 2 |
| `black_bloc/birthdays.py:33` | **Next birthdays** | ephemeral answer | no | `birthday_panel_next_heading` | 2 |
| `black_bloc/birthdays.py:34` | The list of birthdays coming up is for staff in this server, so it is not shown … | ephemeral answer | no | `birthday_panel_next_is_staff_only` | 2 |
| `black_bloc/birthdays.py:37` | ⚠️ Birthday wishes are **off**, so nothing is posted on the day yet. Your birthd… | ephemeral answer | no | `birthday_mode_warnings` | 2 |
| `black_bloc/birthdays.py:37` | ⚠️ Birthday wishes are in **shadow** — the day is written to the log but nothing… | ephemeral answer | no | `birthday_mode_warnings_2` | 2 |
| `black_bloc/birthdays.py:48` | Your birthday | modal title or field | no | `birthday_date_mine_title` | 2 |
| `black_bloc/birthdays.py:49` | Set {who}'s birthday | modal title or field | no | `birthday_date_theirs_title` | 2 |
| `black_bloc/birthdays.py:53` | Black Bloc could not read that as a date. Write it as **MM-DD** — `09-15` — or a… | ephemeral answer | no | `birthday_date_unreadable` | 2 |
| `black_bloc/birthdays.py:60` | Every month | ephemeral answer | no | `birthday_every_month` | 2 |
| `black_bloc/cogs/community/birthdays.py:86` | Black Bloc birthday | ephemeral answer | no | `birthday_role_reason` | 2 |
| `black_bloc/cogs/community/birthdays.py:89` | Black Bloc has no birthday for you, so there is nothing to change. Add one with … | ephemeral answer | no | `birthday_not_stored` | 2 |
| `black_bloc/cogs/community/birthdays.py:94` | Black Bloc has no birthday for {who}. They can add one themselves with **Set my … | ephemeral answer | no | `birthday_not_stored_for` | 2 |
| `black_bloc/cogs/community/birthdays.py:98` | Your birthday is forgotten. Nothing will be posted for you. | ephemeral answer | no | `birthday_removed` | 2 |
| `black_bloc/cogs/community/birthdays.py:99` | **{who}**'s birthday is forgotten. Nothing will be posted for them. | ephemeral answer | no | `birthday_removed_for` | 2 |
| `black_bloc/cogs/community/birthdays.py:100` | Staff have removed the birthday Black Bloc had stored for you in **{guild}**, so… | ephemeral answer | no | `birthday_forgotten_by_staff` | 2 |
| `black_bloc/cogs/community/birthdays.py:104` | You are opted out — your birthday is still stored, but nothing will be posted. *… | ephemeral answer | no | `birthday_opted_out` | 2 |
| `black_bloc/cogs/community/birthdays.py:108` | You are opted back in. Black Bloc will post on the day again. | ephemeral answer | no | `birthday_opted_in` | 2 |
| `black_bloc/cogs/community/birthdays.py:109` | You were already opted {state}, so nothing changed. | ephemeral answer | no | `birthday_already_opted` | 2 |
| `black_bloc/cogs/community/birthdays.py:110` | Nobody has a birthday stored yet. People add their own with **Set my birthday** … | ephemeral answer | no | `birthday_nobody_yet` | 2 |
| `black_bloc/cogs/community/birthdays.py:114` | Nobody has a birthday stored in **{month}**. | ephemeral answer | no | `birthday_none_this_month` | 2 |
| `black_bloc/cogs/community/birthdays.py:115` | There are no birthdays to show — everyone stored is opted out, or nobody has set… | ephemeral answer | no | `birthday_nothing_upcoming` | 2 |
| `black_bloc/cogs/community/birthdays.py:118` | Birthday wishes are now **{mode}**. | ephemeral answer | no | `birthday_mode_set` | 2 |
| `black_bloc/cogs/community/birthdays.py:119` | Forget your birthday? Black Bloc will stop posting for you and will not remember… | ephemeral answer | no | `birthday_remove_confirm` | 2 |
| `black_bloc/cogs/community/birthdays.py:123` | Forget **{who}**'s birthday? Black Bloc will stop posting for them, and they are… | ephemeral answer | no | `birthday_forget_confirm` | 2 |
| `black_bloc/cogs/community/birthdays.py:127` | Stop giving a birthday role at all? A role somebody already has for today still … | ephemeral answer | no | `birthday_role_clear_confirm` | 2 |
| `black_bloc/cogs/community/birthdays.py:131` | No birthday role will be given any more. A role somebody already has for today s… | ephemeral answer | no | `birthday_role_cleared` | 2 |
| `black_bloc/cogs/community/birthdays.py:135` | There was no birthday role set, so nothing changed. `/settings` ▸ **A setting gr… | ephemeral answer | no | `birthday_role_not_set` | 2 |

### temp voice

*112 strings — 2 keyed · 35 unkeyed pass 1 · 59 unkeyed pass 2 · 18 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/cogs/community/tempvoice.py:1495` | *(the key's value)* | read from the store at render | **yes → `tempvoice_creator_name`** (ns `tempvoice`, 6 read site(s)) | — | 1 |
| `black_bloc/cogs/community/tempvoice.py:1526` | *(the key's value)* | read from the store at render | **yes → `tempvoice_name_template`** (ns `tempvoice`, 2 read site(s)) | — | 1 |
| `black_bloc/api/tools/tempvoice.py:51` | A channel needs a name, so nothing was changed. Type what it should be called an… | channel / role name | no | `tempvoice_no_name` | 1 |
| `black_bloc/cogs/community/tempvoice.py:43` | You Still Here? | channel / role name | no | `tempvoice_afk_fallback_name` | 1 |
| `black_bloc/cogs/community/tempvoice.py:168` | An Auntie/Uncle handed the temporary voice channel **{channel}** to **{who}**, s… | DM | no | `tempvoice_handed_over_dm` | 1 |
| `black_bloc/cogs/community/tempvoice.py:188` | Who may be in your channel. Letting somebody in or shutting them out is remember… | card description | no | `tempvoice_people_intro` | 1 |
| `black_bloc/cogs/community/tempvoice.py:192` | Which of Discord's servers carries the audio. **Automatic** lets Discord pick th… | card description | no | `tempvoice_region_intro` | 1 |
| `black_bloc/cogs/community/tempvoice.py:196` | Pick who should own **{channel}**. They get the controls and you do not — you ke… | card description | no | `tempvoice_hand_over_intro` | 1 |
| `black_bloc/cogs/community/tempvoice.py:200` | The channels Black Bloc treats as join-to-create. Forgetting one leaves the Disc… | card description | no | `tempvoice_lobby_intro` | 1 |
| `black_bloc/cogs/community/tempvoice.py:212` | {name} — take their way in back | card field | no | `tempvoice_undo_labels` | 1 |
| `black_bloc/cogs/community/tempvoice.py:212` | {name} — let them back in | card field | no | `tempvoice_undo_labels_2` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2452` | Rename | button label | no | `tempvoice_button_rename` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2459` | Limit | button label | no | `tempvoice_button_limit` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2466` | Lock / Unlock | button label | no | `tempvoice_button_lock_unlock` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2470` | Hide / Show | button label | no | `tempvoice_button_hide_show` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2474` | Kick | button label | no | `tempvoice_button_kick` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2478` | Ban | button label | no | `tempvoice_button_ban` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2482` | Unban | button label | no | `tempvoice_button_unban` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2486` | Permit | button label | no | `tempvoice_button_permit` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2490` | Unpermit | button label | no | `tempvoice_button_unpermit` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2494` | Transfer | button label | no | `tempvoice_button_transfer` | 1 |
| `black_bloc/cogs/community/tempvoice.py:2498` | Claim | button label | no | `tempvoice_button_claim` | 1 |
| `black_bloc/tempvoice.py:43` | Your voice channel | card title | no | `tempvoice_panel_title` | 1 |
| `black_bloc/tempvoice.py:44` | This panel has gone quiet — run /voice again | card description | no | `tempvoice_panel_timeout_footer` | 1 |
| `black_bloc/tempvoice.py:46` | Your own temporary voice channel, and everything you can change about it. Nothin… | card description | no | `tempvoice_panel_intro` | 1 |
| `black_bloc/tempvoice.py:50` | Join-to-create is **off** for this server at the moment, so joining the lobby ma… | channel post | no | `tempvoice_mode_off_line` | 1 |
| `black_bloc/tempvoice.py:54` | The lobby is hidden from members while temp voice is in **shadow** — staff can s… | channel post | no | `tempvoice_shadow_line` | 1 |
| `black_bloc/tempvoice.py:58` | You are in <@{owner_id}>'s channel and they have left it, so **Claim** makes it … | channel post | no | `tempvoice_orphan_line` | 1 |
| `black_bloc/tempvoice.py:61` | You are in <@{owner_id}>'s channel and they are still in it, so it cannot be cla… | channel post | no | `tempvoice_guest_line` | 1 |
| `black_bloc/tempvoice.py:91` | What joining the lobby does, and who can see it. | card description | no | `tempvoice_mode_intro` | 1 |
| `black_bloc/tempvoice.py:93` | Who may be in your channel | card title | no | `tempvoice_people_title` | 1 |
| `black_bloc/tempvoice.py:94` | Where the audio goes | card title | no | `tempvoice_region_title` | 1 |
| `black_bloc/tempvoice.py:95` | What join-to-create does | card title | no | `tempvoice_mode_title` | 1 |
| `black_bloc/tempvoice.py:96` | Hand your channel over | card title | no | `tempvoice_hand_over_title` | 1 |
| `black_bloc/tempvoice.py:97` | Join-to-create lobbies | card title | no | `tempvoice_lobby_title` | 1 |
| `black_bloc/tempvoice.py:98` | A temporary voice channel | card title | no | `tempvoice_staff_card_title` | 1 |
| `black_bloc/tempvoice.py:99` | Are you sure? | card title | no | `tempvoice_forget_title` | 1 |
| `black_bloc/api/tools/tempvoice.py:47` | Black Bloc is not keeping track of a temporary voice channel with that id, so no… | ephemeral answer | no | `tempvoice_no_such_room` | 2 |
| `black_bloc/api/tools/tempvoice.py:55` | **{given}** is not a number of people Black Bloc can use, so nothing was changed… | ephemeral answer | no | `tempvoice_bad_limit` | 2 |
| `black_bloc/cogs/community/tempvoice.py:58` | This panel is not attached to a temporary voice channel any more, so nothing was… | ephemeral answer | no | `tempvoice_not_a_temp_channel` | 2 |
| `black_bloc/cogs/community/tempvoice.py:62` | Black Bloc did not make you a voice channel because join-to-create is for member… | ephemeral answer | no | `tempvoice_not_allowed` | 2 |
| `black_bloc/cogs/community/tempvoice.py:66` | Discord refused that change, so nothing happened. Black Bloc needs the Manage Ch… | ephemeral answer | no | `tempvoice_cannot_edit` | 2 |
| `black_bloc/cogs/community/tempvoice.py:70` | **{name}** is not in this channel, so nothing was changed. They have to be conne… | ephemeral answer | no | `tempvoice_not_in_channel` | 2 |
| `black_bloc/cogs/community/tempvoice.py:74` | This channel still belongs to <@{owner_id}>, and they are still in it, so it can… | ephemeral answer | no | `tempvoice_owner_still_here` | 2 |
| `black_bloc/cogs/community/tempvoice.py:78` | Black Bloc is in test mode and cannot see its test channel, so no channel was cr… | ephemeral answer | no | `tempvoice_no_test_channel` | 2 |
| `black_bloc/cogs/community/tempvoice.py:82` | Discord refused to create the channel, so nothing was made. Black Bloc needs the… | ephemeral answer | no | `tempvoice_cannot_create` | 2 |
| `black_bloc/cogs/community/tempvoice.py:86` | Someone else just claimed this channel, so nothing was changed. Ask them to hand… | ephemeral answer | no | `tempvoice_claim_lost` | 2 |
| `black_bloc/cogs/community/tempvoice.py:90` | You have to be connected to this channel before you can claim it, so nothing was… | ephemeral answer | no | `tempvoice_claim_needs_connection` | 2 |
| `black_bloc/cogs/community/tempvoice.py:94` | That temporary voice channel is gone, so nothing was changed. Join the join-to-c… | ephemeral answer | no | `tempvoice_channel_gone` | 2 |
| `black_bloc/cogs/community/tempvoice.py:98` | Discord only lets a channel be renamed **twice every 10 minutes**, and this one … | ephemeral answer | no | `tempvoice_renamed_too_often` | 2 |
| `black_bloc/cogs/community/tempvoice.py:102` | Voice controls are for members with the <@&{role_id}> role, so nothing was chang… | ephemeral answer | no | `tempvoice_voice_needs_role` | 2 |
| `black_bloc/cogs/community/tempvoice.py:106` | You don't own a temp channel right now — join **{lobby}** to make one. | ephemeral answer | no | `tempvoice_no_owned_channel` | 2 |
| `black_bloc/cogs/community/tempvoice.py:109` | You are not in one of Black Bloc's temporary voice channels, so there is nothing… | ephemeral answer | no | `tempvoice_claim_needs_a_channel` | 2 |
| `black_bloc/cogs/community/tempvoice.py:113` | Discord would not use **{region}** as this channel's voice region, so nothing ch… | ephemeral answer | no | `tempvoice_cannot_set_region` | 2 |
| `black_bloc/cogs/community/tempvoice.py:117` | Forgotten. Your next temporary channel starts from the server's defaults — name,… | ephemeral answer | no | `tempvoice_prefs_cleared` | 2 |
| `black_bloc/cogs/community/tempvoice.py:122` | Black Bloc repaired the join-to-create channel it already had — {where} — instea… | ephemeral answer | no | `tempvoice_repaired` | 2 |
| `black_bloc/cogs/community/tempvoice.py:126` | Black Bloc found a join-to-create channel it was not keeping track of — {where} … | ephemeral answer | no | `tempvoice_adopted` | 2 |
| `black_bloc/cogs/community/tempvoice.py:131` | There are other join-to-create channels too — {extras} — so drop the ones you do… | ephemeral answer | no | `tempvoice_extra_lobbies` | 2 |
| `black_bloc/cogs/community/tempvoice.py:135` | **not kept track of** — {extras}. Each of those is called **{name}** and sits wh… | ephemeral answer | no | `tempvoice_stray_lobbies` | 2 |
| `black_bloc/cogs/community/tempvoice.py:140` | Discord refused to change {where}, so nothing was repaired. Black Bloc needs the… | ephemeral answer | no | `tempvoice_cannot_repair` | 2 |
| `black_bloc/cogs/community/tempvoice.py:145` | {where} is Black Bloc's join-to-create channel, but it sits outside the test cha… | ephemeral answer | no | `tempvoice_outside_test_category` | 2 |
| `black_bloc/cogs/community/tempvoice.py:150` | **{channel_id}** is not one of Black Bloc's join-to-create channels, so nothing … | ephemeral answer | no | `tempvoice_not_a_lobby` | 2 |
| `black_bloc/cogs/community/tempvoice.py:154` | **{name}** sits outside the test channel's category and Black Bloc did not make … | ephemeral answer | no | `tempvoice_outside_test_room` | 2 |
| `black_bloc/cogs/community/tempvoice.py:159` | Black Bloc has forgotten **{channel_id}** — joining it no longer makes anybody a… | ephemeral answer | no | `tempvoice_lobby_forgotten` | 2 |
| `black_bloc/cogs/community/tempvoice.py:163` | Join-to-create is now **{mode}**. | ephemeral answer | no | `tempvoice_mode_set` | 2 |
| `black_bloc/cogs/community/tempvoice.py:164` | **{given}** is not a setting Black Bloc knows for join-to-create, so nothing was… | ephemeral answer | no | `tempvoice_not_a_mode` | 2 |
| `black_bloc/cogs/community/tempvoice.py:172` | That temporary voice channel is not yours any more, so nothing was changed. The … | ephemeral answer | no | `tempvoice_lost_the_channel` | 2 |
| `black_bloc/cogs/community/tempvoice.py:176` | **{member_id}** is not somebody Black Bloc can see in this server any more, so n… | ephemeral answer | no | `tempvoice_no_such_member` | 2 |
| `black_bloc/cogs/community/tempvoice.py:180` | That is not a number between 0 and 99, so nothing was changed. Type a whole numb… | ephemeral answer | no | `tempvoice_not_a_limit` | 2 |
| `black_bloc/cogs/community/tempvoice.py:184` | **{given}** is not a whole number of kbps, so nothing was changed. Type a number… | ephemeral answer | no | `tempvoice_not_a_bitrate` | 2 |
| `black_bloc/cogs/community/tempvoice.py:204` | Black Bloc temp voice: shadow — the lobby is staff-only | ephemeral answer | no | `tempvoice_hide_reason` | 2 |
| `black_bloc/cogs/community/tempvoice.py:205` | Black Bloc temp voice: shadow is off — syncing the lobby with its category | ephemeral answer | no | `tempvoice_show_reason` | 2 |
| `black_bloc/cogs/community/tempvoice.py:206` | Black Bloc temp voice: shadow is off — giving the allowed role its view back | ephemeral answer | no | `tempvoice_allow_reason` | 2 |
| `black_bloc/cogs/community/tempvoice.py:207` | not on the server any more | ephemeral answer | no | `tempvoice_lobby_gone` | 2 |
| `black_bloc/cogs/community/tempvoice.py:208` | gone from the server | ephemeral answer | no | `tempvoice_channel_left` | 2 |
| `black_bloc/cogs/community/tempvoice.py:210` | {shown} of {total} in the channel | ephemeral answer | no | `tempvoice_capped_here` | 2 |
| `black_bloc/cogs/community/tempvoice.py:211` | {shown} of {total} — the rest are on the site | ephemeral answer | no | `tempvoice_capped_undo` | 2 |
| `black_bloc/cogs/community/tempvoice.py:2313` | New name | modal field label | no | `tempvoice_modal_new_name` | 2 |
| `black_bloc/cogs/community/tempvoice.py:2334` | 0 to 99 (0 means no limit) | modal field label | no | `tempvoice_modal_0_to_99_0_means_no_limit` | 2 |
| `black_bloc/cogs/community/tempvoice.py:2378` | What it should be called | modal field label | no | `tempvoice_modal_what_it_should_be_called` | 2 |
| `black_bloc/tempvoice.py:65` | You do not have the <@&{role_id}> role, so Black Bloc keeps no channel of your o… | ephemeral answer | no | `tempvoice_staff_without_role` | 2 |
| `black_bloc/tempvoice.py:69` | Nobody has a temporary voice channel open right now, so there is nothing to hand… | ephemeral answer | no | `tempvoice_nothing_to_see` | 2 |
| `black_bloc/tempvoice.py:73` | A channel… | ephemeral answer | no | `tempvoice_pick_channel` | 2 |
| `black_bloc/tempvoice.py:74` | A lobby to forget… | ephemeral answer | no | `tempvoice_pick_lobby` | 2 |
| `black_bloc/tempvoice.py:75` | A region… | ephemeral answer | no | `tempvoice_pick_region` | 2 |
| `black_bloc/tempvoice.py:76` | Let someone in… | ephemeral answer | no | `tempvoice_pick_permit` | 2 |
| `black_bloc/tempvoice.py:77` | Keep someone out… | ephemeral answer | no | `tempvoice_pick_ban` | 2 |
| `black_bloc/tempvoice.py:78` | Move someone out… | ephemeral answer | no | `tempvoice_pick_kick` | 2 |
| `black_bloc/tempvoice.py:79` | Undo for… | ephemeral answer | no | `tempvoice_pick_undo` | 2 |
| `black_bloc/tempvoice.py:80` | Who should own it? | ephemeral answer | no | `tempvoice_pick_new_owner` | 2 |
| `black_bloc/tempvoice.py:81` | What join-to-create should do… | ephemeral answer | no | `tempvoice_pick_mode` | 2 |
| `black_bloc/tempvoice.py:86` | Joining the lobby makes nothing. Rooms that exist keep working. | ephemeral answer | no | `tempvoice_mode_means` | 2 |
| `black_bloc/tempvoice.py:86` | It works, but only staff see the lobby — and a room it makes follows it. | ephemeral answer | no | `tempvoice_mode_means_2` | 2 |
| `black_bloc/tempvoice.py:86` | The lobby is visible to whoever its category shows. | ephemeral answer | no | `tempvoice_mode_means_3` | 2 |
| `black_bloc/tempvoice.py:101` | Forget everything Black Bloc remembers about your voice channels? The channel yo… | ephemeral answer | no | `tempvoice_forget_question` | 2 |
| `black_bloc/tempvoice.py:105` | Yes, forget it | ephemeral answer | no | `tempvoice_forget_yes` | 2 |

### role menus

*178 strings — 0 keyed · 47 unkeyed pass 1 · 121 unkeyed pass 2 · 10 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/api/tools/roles.py:23` | That timed role ended on {when}, so there was nothing to change. Give it again w… | channel post | no | `rolemenu_already_ended` | 1 |
| `black_bloc/cogs/community/role_menus.py:163` | A menu that already exists is left exactly as it is, options and all — to pick u… | card description | no | `rolemenu_seed_emoji_note` | 1 |
| `black_bloc/cogs/community/role_menus.py:208` | Picking a role here asks staff first — you get a DM either way, and nothing chan… | card description | no | `rolemenu_needs_approval_note` | 1 |
| `black_bloc/cogs/community/role_menus.py:212` | A role from this menu lasts {days} day(s), then Black Bloc takes it back. | card description | no | `rolemenu_expires_note` | 1 |
| `black_bloc/cogs/community/role_menus.py:244` | **{label}** is off **{name}** and the clock is closed. They were not sent a DM —… | channel post | no | `rolemenu_grant_ended` | 1 |
| `black_bloc/cogs/community/role_menus.py:400` | Roles | card field name | no | `rolemenu_card_roles` | 1 |
| `black_bloc/cogs/community/role_menus.py:403` | Before you pick | card field name | no | `rolemenu_card_before_you_pick` | 1 |
| `black_bloc/cogs/community/role_menus.py:781` | Role | card field name | no | `rolemenu_card_role` | 1 |
| `black_bloc/cogs/community/role_menus.py:782` | Menu | card field name | no | `rolemenu_card_menu` | 1 |
| `black_bloc/cogs/community/role_menus.py:783` | Asked | card field name | no | `rolemenu_card_asked` | 1 |
| `black_bloc/cogs/community/role_menus.py:784` | Lasts | card field name | no | `rolemenu_card_lasts` | 1 |
| `black_bloc/cogs/community/role_menus.py:785` | Status | card field name | no | `rolemenu_card_status` | 1 |
| `black_bloc/cogs/community/role_menus.py:787` | Decided by | card field name | no | `rolemenu_card_decided_by` | 1 |
| `black_bloc/cogs/community/role_menus.py:789` | Reason | card field name | no | `rolemenu_card_reason` | 1 |
| `black_bloc/cogs/community/role_menus.py:1198` | Pick the roles you want | select placeholder | no | `rolemenu_placeholder_pick_the_roles_you_want` | 1 |
| `black_bloc/cogs/community/role_menus.py:1695` | Where should {name} go? | card title | no | `rolemenu_where_title` | 1 |
| `black_bloc/cogs/community/role_menus.py:1702` | Picked: <@&{role_id}>. Name it after the role itself, or give it your own words. | channel post | no | `rolemenu_role_add_line` | 1 |
| `black_bloc/cogs/community/role_menus.py:1704` | Picking here changes **{name}**'s roles at once, test mode or not. | channel post | no | `rolemenu_hand_line` | 1 |
| `black_bloc/cogs/community/role_menus.py:1707` | Giving <@&{role_id}> to <@{user_id}>. **How long for…** finishes it. | channel post | no | `rolemenu_new_grant_line` | 1 |
| `black_bloc/cogs/community/role_menus.py:2467` | Picking roles from the panels is now ****. | channel post / DM | no | `rolemenu_line_picking_roles_from_the_panels_is_now` | 1 |
| `black_bloc/rolegrants.py:68` | Staff approved **{label}** on **{guild}**, and you have it now.{extra} | DM | no | `rolemenu_dm_approved` | 1 |
| `black_bloc/rolegrants.py:71` | Staff did not approve **{label}** on **{guild}**. The reason given was: {reason}… | DM | no | `rolemenu_dm_denied` | 1 |
| `black_bloc/rolegrants.py:75` | Your **{label}** on **{guild}** ran out today, so it has been taken off. Ask sta… | DM | no | `rolemenu_dm_expired` | 1 |
| `black_bloc/rolemenus.py:18` | Role menus | card title | no | `rolemenu_panel_title` | 1 |
| `black_bloc/rolemenus.py:19` | The menu {name} | card title | no | `rolemenu_menu_title` | 1 |
| `black_bloc/rolemenus.py:20` | Add a role to {name} | card title | no | `rolemenu_add_role_title` | 1 |
| `black_bloc/rolemenus.py:21` | Hand out roles from {name} | card title | no | `rolemenu_hand_out_title` | 1 |
| `black_bloc/rolemenus.py:22` | Timed roles running right now | card title | no | `rolemenu_grants_title` | 1 |
| `black_bloc/rolemenus.py:23` | Give somebody a role | card title | no | `rolemenu_new_grant_title` | 1 |
| `black_bloc/rolemenus.py:24` | Timed role #{grant_id} | card title | no | `rolemenu_grant_title` | 1 |
| `black_bloc/rolemenus.py:25` | Requests waiting on staff | card title | no | `rolemenu_requests_title` | 1 |
| `black_bloc/rolemenus.py:26` | Are you sure? | card title | no | `rolemenu_confirm_title` | 1 |
| `black_bloc/rolemenus.py:27` | This panel has gone quiet — run /rolemenu again | card description | no | `rolemenu_panel_timeout_footer` | 1 |
| `black_bloc/rolemenus.py:29` | This server has no role menus yet. **New menu** starts one, and **Seed the defau… | channel post | no | `rolemenu_no_menus_line` | 1 |
| `black_bloc/rolemenus.py:38` | **{name}** — {count} role(s), {mode}, {posted} | channel post | no | `rolemenu_menu_list_line` | 1 |
| `black_bloc/rolemenus.py:64` | <@{user_id}> · <@&{role_id}> · {left} · {ends} | channel post | no | `rolemenu_grant_line` | 1 |
| `black_bloc/rolemenus.py:83` | Turn role menus on | card field | no | `rolemenu_mode_on_label` | 1 |
| `black_bloc/rolemenus.py:84` | Turn role menus off | card field | no | `rolemenu_mode_off_label` | 1 |
| `black_bloc/rolemenus.py:85` | Ask staff first | card field | no | `rolemenu_approval_on_label` | 1 |
| `black_bloc/rolemenus.py:86` | Hand it over straight away | card field | no | `rolemenu_approval_off_label` | 1 |
| `black_bloc/rolemenus.py:87` | Post it | card field | no | `rolemenu_post_label` | 1 |
| `black_bloc/rolemenus.py:88` | Move it… | card field | no | `rolemenu_move_label` | 1 |
| `black_bloc/rolemenus.py:94` | Yes, delete it | card field | no | `rolemenu_delete_yes_label` | 1 |
| `black_bloc/rolemenus.py:100` | Yes, take it back | card field | no | `rolemenu_end_yes_label` | 1 |
| `black_bloc/rolemenus.py:101` | Leave it | card field | no | `rolemenu_leave_it_label` | 1 |
| `black_bloc/rolemenus.py:106` | Yes, make them | card field | no | `rolemenu_seed_yes_label` | 1 |
| `black_bloc/rolemenus.py:107` | Leave it | card field | no | `rolemenu_leave_them_label` | 1 |
| `black_bloc/api/tools/roles.py:19` | Black Bloc has no timed role **#{grant_id}** any more, so nothing was changed. T… | ephemeral answer | no | `rolemenu_no_such_grant` | 2 |
| `black_bloc/api/tools/roles.py:27` | That role has no end date, so there is nothing to push back. End it now instead,… | ephemeral answer | no | `rolemenu_no_end_date` | 2 |
| `black_bloc/api/tools/roles.py:31` | **{user_id}** is not somebody Black Bloc can see in this server, so nothing was … | ephemeral answer | no | `rolemenu_no_such_member` | 2 |
| `black_bloc/api/tools/roles.py:35` | **{role_id}** is not a role in this server any more, so nothing was granted. Ref… | ephemeral answer | no | `rolemenu_no_such_role` | 2 |
| `black_bloc/api/tools/roles.py:39` | **{given}** is not a number of days, so nothing was changed. Send a whole number… | ephemeral answer | no | `rolemenu_bad_days` | 2 |
| `black_bloc/api/tools/roles.py:43` | Extending a role needs a number of days, so nothing was changed. Send how many t… | ephemeral answer | no | `rolemenu_days_needed` | 2 |
| `black_bloc/cogs/community/role_menus.py:41` | <:JoyGAMING:1337948924844965931> | ephemeral answer | no | `rolemenu_joy_gaming` | 2 |
| `black_bloc/cogs/community/role_menus.py:124` | Role menus are turned off right now, so nothing was changed. A Lead can turn the… | ephemeral answer | no | `rolemenu_role_menus_off` | 2 |
| `black_bloc/cogs/community/role_menus.py:128` | Every menu that has a channel is posted there again in a few seconds. `/rolemenu… | ephemeral answer | no | `rolemenu_mode_on` | 2 |
| `black_bloc/cogs/community/role_menus.py:132` | The posted panels are taken down in a few seconds. Nobody loses a role, no menu … | ephemeral answer | no | `rolemenu_mode_off` | 2 |
| `black_bloc/cogs/community/role_menus.py:136` | Role menus only work inside the server, and this click did not come from one, so… | ephemeral answer | no | `rolemenu_not_in_guild` | 2 |
| `black_bloc/cogs/community/role_menus.py:140` | Black Bloc could not change your roles because Discord refused the edit. It need… | ephemeral answer | no | `rolemenu_cannot_edit_roles` | 2 |
| `black_bloc/cogs/community/role_menus.py:145` | Discord refused the change, so **{name}** still has exactly the roles they had. … | ephemeral answer | no | `rolemenu_cannot_edit_theirs` | 2 |
| `black_bloc/cogs/community/role_menus.py:150` | **{name}** is a staff-assigned menu, so there is no panel to post — nobody gives… | ephemeral answer | no | `rolemenu_staff_menu_not_posted` | 2 |
| `black_bloc/cogs/community/role_menus.py:155` | **{name}** has none of the roles on **{menu}**, so there is nothing to take off.… | ephemeral answer | no | `rolemenu_nothing_to_unassign` | 2 |
| `black_bloc/cogs/community/role_menus.py:159` | This server has no role menus yet. Open `/rolemenu`: **New menu** starts one, an… | ephemeral answer | no | `rolemenu_no_menus_yet` | 2 |
| `black_bloc/cogs/community/role_menus.py:170` | **{name}** already has exactly those roles, so nothing changed. | ephemeral answer | no | `rolemenu_already_exactly` | 2 |
| `black_bloc/cogs/community/role_menus.py:173` | **{user_id}** is not somebody Black Bloc can see in this server, so nothing was … | ephemeral answer | no | `rolemenu_no_such_member_2` | 2 |
| `black_bloc/cogs/community/role_menus.py:177` | **{name}** has no roles on it yet, so there is nothing to hand out. Add one to t… | ephemeral answer | no | `rolemenu_nothing_on_this_menu` | 2 |
| `black_bloc/cogs/community/role_menus.py:181` | **{name}** has no panel up right now, so there was nothing to take down. **Post … | ephemeral answer | no | `rolemenu_nothing_to_unpost` | 2 |
| `black_bloc/cogs/community/role_menus.py:185` | Black Bloc could not take **{name}**'s panel down, so it is still where it was. … | ephemeral answer | no | `rolemenu_panel_stuck` | 2 |
| `black_bloc/cogs/community/role_menus.py:190` | **{name}**'s panel is down. The menu and its roles are untouched and nobody lose… | ephemeral answer | no | `rolemenu_panel_taken_down` | 2 |
| `black_bloc/cogs/community/role_menus.py:196` | That {what} is {given} characters and Discord will not show more than {limit}, s… | ephemeral answer | no | `rolemenu_too_long` | 2 |
| `black_bloc/cogs/community/role_menus.py:200` | A role menu shows at most {limit} roles and that one would have {given}, so noth… | ephemeral answer | no | `rolemenu_too_many_options` | 2 |
| `black_bloc/cogs/community/role_menus.py:204` | The menu this panel belongs to has been deleted, so nothing was changed. Ask a L… | ephemeral answer | no | `rolemenu_menu_is_gone` | 2 |
| `black_bloc/cogs/community/role_menus.py:213` | Test mode is on, so the card for staff is in the test channel rather than in the… | ephemeral answer | no | `rolemenu_card_in_test_channel` | 2 |
| `black_bloc/cogs/community/role_menus.py:217` | That request belongs to somebody else's server, so nothing was changed. | ephemeral answer | no | `rolemenu_not_staffs_request` | 2 |
| `black_bloc/cogs/community/role_menus.py:220` | **{name}** is not in this server any more, so the role could not be handed over … | ephemeral answer | no | `rolemenu_member_has_gone` | 2 |
| `black_bloc/cogs/community/role_menus.py:224` | The request is marked approved, but Discord refused to add **{label}** — Black B… | ephemeral answer | no | `rolemenu_role_refused_after_decision` | 2 |
| `black_bloc/cogs/community/role_menus.py:229` | **{given}** is not a number of days, so nothing was decided. Type a whole number… | ephemeral answer | no | `rolemenu_bad_days_2` | 2 |
| `black_bloc/cogs/community/role_menus.py:233` | They already had it, so nothing was added — Black Bloc is only keeping time on i… | ephemeral answer | no | `rolemenu_grant_started_on_a_role_they_had` | 2 |
| `black_bloc/cogs/community/role_menus.py:236` | Discord refused to add **{label}**, so **{name}** was left exactly as they were.… | ephemeral answer | no | `rolemenu_cannot_add` | 2 |
| `black_bloc/cogs/community/role_menus.py:240` | Discord refused to take **{label}** off **{name}**, so nothing was changed and t… | ephemeral answer | no | `rolemenu_cannot_remove` | 2 |
| `black_bloc/cogs/community/role_menus.py:1111` | One line the member will be sent | modal field label | no | `rolemenu_modal_one_line_the_member_will_be_sent` | 2 |
| `black_bloc/cogs/community/role_menus.py:1129` | Days, or 0 for a role that never runs out | modal field label | no | `rolemenu_modal_days_or_0_for_a_role_that_never_runs_out` | 2 |
| `black_bloc/cogs/community/role_menus.py:1696` | A channel… | ephemeral answer | no | `rolemenu_where_pick` | 2 |
| `black_bloc/cogs/community/role_menus.py:1697` | The role menu channel is {where}, so leave it there or pick another. | ephemeral answer | no | `rolemenu_where_default` | 2 |
| `black_bloc/cogs/community/role_menus.py:1698` | No role menu channel is set, so pick one here. `/settings` ▸ **Roles & channels…… | ephemeral answer | no | `rolemenu_where_nowhere` | 2 |
| `black_bloc/cogs/community/role_menus.py:1703` | Pick the role first — Black Bloc only offers roles it can hand out. | ephemeral answer | no | `rolemenu_role_add_nothing` | 2 |
| `black_bloc/cogs/community/role_menus.py:1705` | Pick who this is about first. | ephemeral answer | no | `rolemenu_hand_nobody` | 2 |
| `black_bloc/cogs/community/role_menus.py:1706` | **{name}** has none of this menu's roles, so there is nothing to take back. | ephemeral answer | no | `rolemenu_hand_has_none` | 2 |
| `black_bloc/cogs/community/role_menus.py:1708` | Pick who gets it and which role, and Black Bloc will ask how long for. | ephemeral answer | no | `rolemenu_new_grant_nobody` | 2 |
| `black_bloc/cogs/community/role_menus.py:1709` | Black Bloc has no record of that timed role any more, so nothing was changed. Pr… | ephemeral answer | no | `rolemenu_grant_gone` | 2 |
| `black_bloc/cogs/community/role_menus.py:1713` | This server has no role menu called **{name}** any more, so nothing was changed.… | ephemeral answer | no | `rolemenu_menu_gone` | 2 |
| `black_bloc/cogs/community/role_menus.py:1717` | Black Bloc has no record of that request any more, so nothing was changed. Press… | ephemeral answer | no | `rolemenu_request_gone` | 2 |
| `black_bloc/cogs/community/role_menus.py:1721` | This server already has a role menu called **{name}**, so nothing was created. P… | ephemeral answer | no | `rolemenu_name_taken` | 2 |
| `black_bloc/cogs/community/role_menus.py:1725` | Created **{name}** ({mode}). **Add a role…** puts the first role on it. | ephemeral answer | no | `rolemenu_menu_made` | 2 |
| `black_bloc/cogs/community/role_menus.py:1726` | **{name}** is saved. | ephemeral answer | no | `rolemenu_menu_saved` | 2 |
| `black_bloc/cogs/community/role_menus.py:1727` | **{label}** is on **{name}**. | ephemeral answer | no | `rolemenu_option_added` | 2 |
| `black_bloc/cogs/community/role_menus.py:1728` | **{label}** is off **{name}**. Nobody loses the role they already have. | ephemeral answer | no | `rolemenu_option_gone` | 2 |
| `black_bloc/cogs/community/role_menus.py:1729` | That role was not on **{name}**, so nothing changed. Press **Refresh** and look … | ephemeral answer | no | `rolemenu_option_was_not_on` | 2 |
| `black_bloc/cogs/community/role_menus.py:1732` | Deleted **{name}**. Nobody loses a role they already have, and any panel already… | ephemeral answer | no | `rolemenu_menu_deleted` | 2 |
| `black_bloc/cogs/community/role_menus.py:1736` | **{name}** is live in {where}. {link} | ephemeral answer | no | `rolemenu_posted_said` | 2 |
| `black_bloc/cogs/community/role_menus.py:1737` | **{given}** is not a way a role menu can work, so nothing was changed. Type one … | ephemeral answer | no | `rolemenu_bad_mode` | 2 |
| `black_bloc/cogs/community/role_menus.py:1741` | **{given}** is not a whole number of days, so nothing was changed. Type a number… | ephemeral answer | no | `rolemenu_bad_number` | 2 |
| `black_bloc/cogs/community/role_menus.py:1744` | Black Bloc cannot hand out **{name}**, so it was not added. That role is either … | ephemeral answer | no | `rolemenu_cannot_hand_out` | 2 |
| `black_bloc/cogs/community/role_menus.py:1750` | The posted panel could not be refreshed, so press **Move it…** when you want it … | ephemeral answer | no | `rolemenu_repost_trouble` | 2 |
| `black_bloc/cogs/community/role_menus.py:1754` | A new role menu | modal title or field | no | `rolemenu_new_menu_title` | 2 |
| `black_bloc/cogs/community/role_menus.py:1755` | What this menu says | modal title or field | no | `rolemenu_words_title` | 2 |
| `black_bloc/cogs/community/role_menus.py:1756` | How this menu behaves | modal title or field | no | `rolemenu_rules_title` | 2 |
| `black_bloc/cogs/community/role_menus.py:1757` | How this role reads | modal title or field | no | `rolemenu_option_title` | 2 |
| `black_bloc/cogs/community/role_menus.py:1758` | How long for? | modal title or field | no | `rolemenu_days_title` | 2 |
| `black_bloc/cogs/community/role_menus.py:1759` | Push the end date back | modal title or field | no | `rolemenu_push_title` | 2 |
| `black_bloc/cogs/community/role_menus.py:1761` | Short name, the one you will pick it by | modal title or field | no | `rolemenu_name_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1762` | Heading shown on the panel | modal title or field | no | `rolemenu_heading_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1763` | Optional line under the heading | modal title or field | no | `rolemenu_description_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1764` | multiple, single or staff | modal title or field | no | `rolemenu_mode_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1765` | What the option says | modal title or field | no | `rolemenu_label_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1766` | Optional emoji beside it | modal title or field | no | `rolemenu_emoji_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1767` | Days a role from this menu lasts, 0 for never | modal title or field | no | `rolemenu_expires_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1768` | Days a member waits after a no | modal title or field | no | `rolemenu_retry_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1769` | Days, or 0 for a role that never runs out | modal title or field | no | `rolemenu_days_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:1770` | Days to add | modal title or field | no | `rolemenu_push_label` | 2 |
| `black_bloc/cogs/community/role_menus.py:2995` | One line the member will be sent | modal field label | no | `rolemenu_modal_one_line_the_member_will_be_sent_2` | 2 |
| `black_bloc/rolegrants.py:41` | Sent to staff for approval — you'll get a DM when it's decided. Pick **{label}**… | ephemeral answer | no | `rolemenu_request_sent` | 2 |
| `black_bloc/rolegrants.py:45` | You have already asked for **{label}** and staff have not decided yet, so nothin… | ephemeral answer | no | `rolemenu_already_asked` | 2 |
| `black_bloc/rolegrants.py:49` | Staff said no to **{label}** on {when}; you can ask again {stamp}. Nothing was s… | ephemeral answer | no | `rolemenu_too_soon` | 2 |
| `black_bloc/rolegrants.py:53` | Your request for **{label}** has been taken back, so staff will not be deciding … | ephemeral answer | no | `rolemenu_withdrawn_said` | 2 |
| `black_bloc/rolegrants.py:57` | Black Bloc has no record of that request any more, so nothing was changed. The r… | ephemeral answer | no | `rolemenu_nothing_to_approve` | 2 |
| `black_bloc/rolegrants.py:61` | Somebody got there first — that request is already **{status}**, so nothing was … | ephemeral answer | no | `rolemenu_already_decided` | 2 |
| `black_bloc/rolegrants.py:65` | Role request #{request_id} | ephemeral answer | no | `rolemenu_card_heading` | 2 |
| `black_bloc/rolegrants.py:66` | Approved — {name} has **{label}** now.{extra} | ephemeral answer | no | `rolemenu_approved_said` | 2 |
| `black_bloc/rolegrants.py:67` | Denied, and they have been told why. | ephemeral answer | no | `rolemenu_denied_said` | 2 |
| `black_bloc/rolegrants.py:79` | It runs out {stamp}. | ephemeral answer | no | `rolemenu_expires_extra` | 2 |
| `black_bloc/rolegrants.py:81` | **{name}** has **{label}**{until}. | ephemeral answer | no | `rolemenu_granted_said` | 2 |
| `black_bloc/rolegrants.py:82` | Black Bloc is not keeping time on **{label}** for **{name}**, so there was nothi… | ephemeral answer | no | `rolemenu_no_such_grant_2` | 2 |
| `black_bloc/rolegrants.py:86` | **{name}**'s **{label}** has no end date, so there is nothing to push back. **En… | ephemeral answer | no | `rolemenu_grant_never_ends` | 2 |
| `black_bloc/rolegrants.py:90` | **{name}**'s **{label}** now runs out {stamp}. | ephemeral answer | no | `rolemenu_extended_said` | 2 |
| `black_bloc/rolegrants.py:91` | Discord refused the change, so **{name}** still has exactly the roles they had. … | ephemeral answer | no | `rolemenu_cannot_edit_theirs_2` | 2 |
| `black_bloc/rolegrants.py:96` | Black Bloc has nowhere to send the request, so nothing was submitted. A Lead poi… | ephemeral answer | no | `rolemenu_no_approval_channel` | 2 |
| `black_bloc/rolegrants.py:100` | Your request for **{label}** is saved, but Black Bloc could not post the card fo… | ephemeral answer | no | `rolemenu_card_not_posted` | 2 |
| `black_bloc/rolemenu_panels.py:30` | the channel is not one Black Bloc can see any more | ephemeral answer | no | `rolemenu_no_channel` | 2 |
| `black_bloc/rolemenus.py:33` | Members cannot pick roles from the posted panels right now, so the panels are do… | ephemeral answer | no | `rolemenu_picking_is_off` | 2 |
| `black_bloc/rolemenus.py:39` | No roles on it yet — **Add a role…** puts the first one on. | ephemeral answer | no | `rolemenu_no_roles_yet` | 2 |
| `black_bloc/rolemenus.py:40` | Nobody gives themselves these roles, so there is no panel to post — **Hand roles… | ephemeral answer | no | `rolemenu_nobody_picks_these` | 2 |
| `black_bloc/rolemenus.py:44` | This menu is holding all {limit} roles Discord will show, so nothing else fits. … | ephemeral answer | no | `rolemenu_options_are_full` | 2 |
| `black_bloc/rolemenus.py:48` | The order the options sit in is set on the Role menus page; Discord has nothing … | ephemeral answer | no | `rolemenu_no_ordering` | 2 |
| `black_bloc/rolemenus.py:53` | **{count}** timed role(s) running, soonest to end first. | ephemeral answer | no | `rolemenu_grants_header` | 2 |
| `black_bloc/rolemenus.py:54` | **{count}** timed role(s) running for that member, soonest to end first. | ephemeral answer | no | `rolemenu_grants_for_one` | 2 |
| `black_bloc/rolemenus.py:55` | Nothing in this server is on a clock right now. **Give somebody a role…** starts… | ephemeral answer | no | `rolemenu_no_grants` | 2 |
| `black_bloc/rolemenus.py:58` | That member has no timed role running, so there is nothing to push back or end. … | ephemeral answer | no | `rolemenu_no_grants_for_one` | 2 |
| `black_bloc/rolemenus.py:62` | {shown} of {total} — the Timed roles table on the site has the rest | ephemeral answer | no | `rolemenu_grants_capped` | 2 |
| `black_bloc/rolemenus.py:63` | A timed role… | ephemeral answer | no | `rolemenu_grant_pick` | 2 |
| `black_bloc/rolemenus.py:65` | no end date | ephemeral answer | no | `rolemenu_no_end_date_2` | 2 |
| `black_bloc/rolemenus.py:66` | no end date | ephemeral answer | no | `rolemenu_ends_never` | 2 |
| `black_bloc/rolemenus.py:67` | due now | ephemeral answer | no | `rolemenu_due_now` | 2 |
| `black_bloc/rolemenus.py:68` | under a day left | ephemeral answer | no | `rolemenu_under_a_day` | 2 |
| `black_bloc/rolemenus.py:69` | {days} day(s) left | ephemeral answer | no | `rolemenu_days_left` | 2 |
| `black_bloc/rolemenus.py:71` | Nothing is waiting on staff right now. | ephemeral answer | no | `rolemenu_no_requests` | 2 |
| `black_bloc/rolemenus.py:72` | A request… | ephemeral answer | no | `rolemenu_request_pick` | 2 |
| `black_bloc/rolemenus.py:73` | {shown} of {total} — the Role menus page has the rest | ephemeral answer | no | `rolemenu_requests_capped` | 2 |
| `black_bloc/rolemenus.py:75` | A menu… | ephemeral answer | no | `rolemenu_menu_pick` | 2 |
| `black_bloc/rolemenus.py:76` | {shown} of {total} — the Role menus page has the rest | ephemeral answer | no | `rolemenu_menus_capped` | 2 |
| `black_bloc/rolemenus.py:77` | Whose roles? | ephemeral answer | no | `rolemenu_whose_roles` | 2 |
| `black_bloc/rolemenus.py:78` | Who gets it? | ephemeral answer | no | `rolemenu_who_gets_it` | 2 |
| `black_bloc/rolemenus.py:79` | Which role? | ephemeral answer | no | `rolemenu_which_role` | 2 |
| `black_bloc/rolemenus.py:80` | Take a role off this menu… | ephemeral answer | no | `rolemenu_remove_pick` | 2 |
| `black_bloc/rolemenus.py:81` | A role to put on the menu… | ephemeral answer | no | `rolemenu_role_pick` | 2 |
| `black_bloc/rolemenus.py:90` | Delete **{name}**? Nobody loses a role they already have, and any panel already … | ephemeral answer | no | `rolemenu_delete_question` | 2 |
| `black_bloc/rolemenus.py:96` | Take <@&{role_id}> back off <@{user_id}> now? They are not sent a DM — this is a… | ephemeral answer | no | `rolemenu_end_question` | 2 |
| `black_bloc/rolemenus.py:102` | Make the six default menus? A menu that already exists is left exactly as it is,… | ephemeral answer | no | `rolemenu_seed_question` | 2 |

### pings

*189 strings — 3 keyed · 48 unkeyed pass 1 · 128 unkeyed pass 2 · 13 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/pings.py:41` | *(the key's value)* | read from the store at render | **yes → `pings_events_role_name`** (ns `pings`, 2 read site(s)) | — | 1 |
| `black_bloc/pings.py:38` | *(the key's value)* | read from the store at render | **yes → `pings_fan_role_template`** (ns `pings`, 1 read site(s)) | — | 1 |
| `black_bloc/pings.py:34` | *(the key's value)* | read from the store at render | **yes → `pings_onboarding_prompt_title`** (ns `pings`, 1 read site(s)) | — | 1 |
| `black_bloc/cogs/content/pings.py:60` | What Black Bloc pings you about, and how to change it. Nothing here is on until … | card description | no | `pings_panel_intro` | 1 |
| `black_bloc/cogs/content/pings.py:65` | Follow a streamer… | select placeholder | no | `pings_follow_placeholder` | 1 |
| `black_bloc/cogs/content/pings.py:66` | Stop following… | select placeholder | no | `pings_unfollow_placeholder` | 1 |
| `black_bloc/cogs/content/pings.py:67` | A streamer… | select placeholder | no | `pings_streamer_placeholder` | 1 |
| `black_bloc/cogs/content/pings.py:68` | Give somebody a ping role… | select placeholder | no | `pings_give_placeholder` | 1 |
| `black_bloc/cogs/content/pings.py:69` | Use this role instead — leave it empty and one is made | select placeholder | no | `pings_role_placeholder` | 1 |
| `black_bloc/cogs/content/pings.py:70` | Mode… | select placeholder | no | `pings_mode_placeholder` | 1 |
| `black_bloc/cogs/content/pings.py:71` | When a streamer's role is made… | select placeholder | no | `pings_creation_placeholder` | 1 |
| `black_bloc/cogs/content/pings.py:72` | On unlink… | select placeholder | no | `pings_unlink_placeholder` | 1 |
| `black_bloc/cogs/content/pings.py:74` | off — nobody can opt in and nobody is pinged | card field | no | `pings_mode_labels` | 1 |
| `black_bloc/cogs/content/pings.py:74` | on — members choose their pings | card field | no | `pings_mode_labels_2` | 1 |
| `black_bloc/cogs/content/pings.py:78` | self — a streamer starts their own | card field | no | `pings_creation_labels` | 1 |
| `black_bloc/cogs/content/pings.py:78` | staff — only an Auntie/Uncle starts one | card field | no | `pings_creation_labels_2` | 1 |
| `black_bloc/cogs/content/pings.py:78` | auto — one is made the moment Twitch is linked | card field | no | `pings_creation_labels_3` | 1 |
| `black_bloc/cogs/content/pings.py:78` | follow — the first person to follow them makes it | card field | no | `pings_creation_labels_4` | 1 |
| `black_bloc/cogs/content/pings.py:84` | keep — the role is left alone | card field | no | `pings_unlink_labels` | 1 |
| `black_bloc/cogs/content/pings.py:84` | delete — the role is taken off the server | card field | no | `pings_unlink_labels_2` | 1 |
| `black_bloc/cogs/content/pings.py:89` | The streamer list | card title | no | `pings_streamers_title` | 1 |
| `black_bloc/cogs/content/pings.py:90` | Ping-role settings | card title | no | `pings_settings_title` | 1 |
| `black_bloc/cogs/content/pings.py:91` | Set up the Events role | card title | no | `pings_setup_title` | 1 |
| `black_bloc/cogs/content/pings.py:92` | Set up the raid-train role | card title | no | `pings_raid_title` | 1 |
| `black_bloc/cogs/content/pings.py:93` | Discord onboarding | card title | no | `pings_onboarding_title` | 1 |
| `black_bloc/cogs/content/pings.py:94` | A ping role for {who} | card title | no | `pings_give_title` | 1 |
| `black_bloc/cogs/content/pings.py:95` | Names… | button label | no | `pings_names_button` | 1 |
| `black_bloc/cogs/content/pings.py:96` | Numbers… | button label | no | `pings_numbers_button` | 1 |
| `black_bloc/cogs/content/pings.py:111` | Pick a role Black Bloc should use, or leave the picker empty and one is made fro… | card description | no | `pings_role_pick_intro` | 1 |
| `black_bloc/cogs/content/pings.py:118` | **{name}** | card title | no | `pings_card_head` | 1 |
| `black_bloc/pings.py:37` | Raid trains | channel / role name | no | `pings_raidtrain_role_name` | 1 |
| `black_bloc/pings.py:54` | Streamer pings | card title | no | `pings_streamers_title_2` | 1 |
| `black_bloc/pings.py:56` | Notifications | card title | no | `pings_notifications_title` | 1 |
| `black_bloc/pings.py:57` | Events — go-live and event pings | card field | no | `pings_events_option_label` | 1 |
| `black_bloc/pings.py:545` | Your pings | card title | no | `pings_panel_title` | 1 |
| `black_bloc/pings.py:546` | This panel has gone quiet — run /pings again | card description | no | `pings_panel_timeout_footer` | 1 |
| `black_bloc/pings.py:554` | Go-live and event pings | card field | no | `pings_feed_words` | 1 |
| `black_bloc/pings.py:554` | Go-live pings | card field | no | `pings_feed_words_2` | 1 |
| `black_bloc/pings.py:554` | Event pings | card field | no | `pings_feed_words_3` | 1 |
| `black_bloc/pings.py:554` | Raid-train pings | card field | no | `pings_feed_words_4` | 1 |
| `black_bloc/pings.py:576` | Ping roles are **off** for this server at the moment, so nobody can opt in and n… | channel post | no | `pings_panel_off_line` | 1 |
| `black_bloc/pings.py:636` | • **{name}** — {listed} · {role} · last live {when} | channel post | no | `pings_streamer_line` | 1 |
| `black_bloc/pings.py:642` | **{streamers}** streamer(s) seen · **{listed}** on the list · **{with_role}** wi… | channel post | no | `pings_counts_line` | 1 |
| `black_bloc/pings.py:704` | Turn event pings on | card field | no | `pings_events_on_label` | 1 |
| `black_bloc/pings.py:705` | Turn them off | card field | no | `pings_events_off_label` | 1 |
| `black_bloc/pings_onboarding.py:17` | Which streamers? | card title | no | `pings_streamer_prompt_title` | 1 |
| `black_bloc/pings_onboarding.py:69` | Get pinged when something is happening here | card description | no | `pings_events_description` | 1 |
| `black_bloc/pings_onboarding.py:70` | Get pinged when somebody goes live | card description | no | `pings_golive_description` | 1 |
| `black_bloc/pings_onboarding.py:71` | Get pinged for events and when somebody goes live | card description | no | `pings_both_description` | 1 |
| `black_bloc/pings_onboarding.py:72` | Get pinged when a raid train moves | card description | no | `pings_raid_description` | 1 |
| `black_bloc/pings_onboarding.py:73` | Get pinged when they go live | card description | no | `pings_streamer_description` | 1 |
| `black_bloc/api/tools/pings.py:22` | **{member_id}** is not somebody Black Bloc can see in this server, so nothing wa… | ephemeral answer | no | `pings_no_such_member` | 2 |
| `black_bloc/api/tools/pings.py:26` | **{role_id}** is not a role in this server any more, so nothing was changed. Rel… | ephemeral answer | no | `pings_no_such_role` | 2 |
| `black_bloc/cogs/content/pings.py:97` | Delete the role too: on | ephemeral answer | no | `pings_delete_on` | 2 |
| `black_bloc/cogs/content/pings.py:98` | Delete the role too: off | ephemeral answer | no | `pings_delete_off` | 2 |
| `black_bloc/cogs/content/pings.py:99` | Set it up | ephemeral answer | no | `pings_set_it_up` | 2 |
| `black_bloc/cogs/content/pings.py:100` | Make the role | ephemeral answer | no | `pings_make_the_role` | 2 |
| `black_bloc/cogs/content/pings.py:102` | Done — Black Bloc will not write to this server's onboarding again. The prompts … | ephemeral answer | no | `pings_onboarding_stopped` | 2 |
| `black_bloc/cogs/content/pings.py:106` | Done — Black Bloc will keep its onboarding prompts in step again. Press **Sync n… | ephemeral answer | no | `pings_onboarding_started` | 2 |
| `black_bloc/cogs/content/pings.py:115` | Using **{role}**. | ephemeral answer | no | `pings_role_picked` | 2 |
| `black_bloc/cogs/content/pings.py:116` | Nothing picked, so a fresh role is made. | ephemeral answer | no | `pings_role_not_picked` | 2 |
| `black_bloc/cogs/content/pings.py:119` | on the list — {state} · last live {when} · seen live {count} time(s) | ephemeral answer | no | `pings_card_listed` | 2 |
| `black_bloc/cogs/content/pings.py:120` | role — {role} | ephemeral answer | no | `pings_card_role` | 2 |
| `black_bloc/cogs/content/pings.py:121` | role — none yet; the first person to follow them makes it | ephemeral answer | no | `pings_card_no_role` | 2 |
| `black_bloc/cogs/content/pings.py:122` | followers — {count} | ephemeral answer | no | `pings_card_followers` | 2 |
| `black_bloc/cogs/content/pings.py:123` | started — {when} by {who} | ephemeral answer | no | `pings_card_started` | 2 |
| `black_bloc/cogs/content/pings.py:124` | the role is gone from the server | ephemeral answer | no | `pings_card_role_gone` | 2 |
| `black_bloc/cogs/content/pings.py:126` | never — Black Bloc has not seen them stream | ephemeral answer | no | `pings_card_never_live` | 2 |
| `black_bloc/cogs/content/pings.py:128` | **{member_id}** is not somebody Black Bloc can see in this server any more, so n… | ephemeral answer | no | `pings_no_such_member_2` | 2 |
| `black_bloc/cogs/content/pings.py:133` | Names and numbers | modal title | no | `pings_names_modal_title` | 2 |
| `black_bloc/cogs/content/pings.py:134` | What the shared Events role is called | modal title or field | no | `pings_events_name_label` | 2 |
| `black_bloc/cogs/content/pings.py:135` | A streamer's role name — {name} is them | modal title or field | no | `pings_template_label` | 2 |
| `black_bloc/cogs/content/pings.py:136` | Minutes this panel stays live | modal title or field | no | `pings_panel_minutes_label` | 2 |
| `black_bloc/cogs/content/pings.py:137` | **{given}** is not a whole number, so nothing was changed. {label} takes a numbe… | ephemeral answer | no | `pings_not_a_number` | 2 |
| `black_bloc/cogs/content/pings.py:147` | Days and ceilings | modal title | no | `pings_numbers_modal_title` | 2 |
| `black_bloc/cogs/content/pings.py:148` | Days on the list without a go-live | modal title or field | no | `pings_stale_days_label` | 2 |
| `black_bloc/cogs/content/pings.py:149` | Days an unworn ping role survives | modal title or field | no | `pings_empty_role_days_label` | 2 |
| `black_bloc/cogs/content/pings.py:150` | Streamers on the onboarding prompt | modal title or field | no | `pings_cap_label` | 2 |
| `black_bloc/pings.py:59` | Black Bloc pings | ephemeral answer | no | `pings_role_reason` | 2 |
| `black_bloc/pings.py:61` | Ping roles are turned off right now, so nothing was changed and nobody was pinge… | ephemeral answer | no | `pings_off` | 2 |
| `black_bloc/pings.py:65` | Staff have not set up the Events role yet, so there is nothing to opt in to. Ask… | ephemeral answer | no | `pings_no_events_role` | 2 |
| `black_bloc/pings.py:70` | The Events role is set to **{role_id}**, and that is not a role in this server a… | ephemeral answer | no | `pings_events_role_gone` | 2 |
| `black_bloc/pings.py:75` | Discord refused the role change, so nothing was changed. Black Bloc needs the Ma… | ephemeral answer | no | `pings_forbidden` | 2 |
| `black_bloc/pings.py:80` | Discord refused to make the role **{name}**, so nothing was set up. Black Bloc n… | ephemeral answer | no | `pings_cannot_make_role` | 2 |
| `black_bloc/pings.py:85` | Black Bloc cannot hand out **{name}**, so it was not used. That role is either a… | ephemeral answer | no | `pings_role_unassignable` | 2 |
| `black_bloc/pings.py:90` | Black Bloc does not know you stream yet, so there is nothing to make a role for.… | ephemeral answer | no | `pings_not_a_streamer` | 2 |
| `black_bloc/pings.py:95` | Only staff start a streamer's ping role on this server, so nothing was made. Ask… | ephemeral answer | no | `pings_staff_only_creation` | 2 |
| `black_bloc/pings.py:100` | **{name}** already has a ping role — <@&{role_id}>. Nothing was changed; people … | ephemeral answer | no | `pings_already_has_one` | 2 |
| `black_bloc/pings.py:104` | **{name}** has no ping role, so there was nothing to take away. `/pings` ▸ **Str… | ephemeral answer | no | `pings_no_fan_role` | 2 |
| `black_bloc/pings.py:108` | Made **{role}** and put it on the *{menu}* panel. People pick it there, or with … | ephemeral answer | no | `pings_created` | 2 |
| `black_bloc/pings.py:113` | Used the role **{role}** for **{name}** and put it on the *{menu}* panel. People… | ephemeral answer | no | `pings_reused` | 2 |
| `black_bloc/pings.py:117` | **{name}** no longer has a ping role here, and the Discord role **{role}** was l… | ephemeral answer | no | `pings_removed_kept` | 2 |
| `black_bloc/pings.py:121` | **{name}** no longer has a ping role, and the Discord role **{role}** is gone fr… | ephemeral answer | no | `pings_removed_deleted` | 2 |
| `black_bloc/pings.py:125` | **{name}** no longer has a ping role here. The Discord role had already been del… | ephemeral answer | no | `pings_removed_already_gone` | 2 |
| `black_bloc/pings.py:129` | Made the role **{role}** and pointed go-live and event pings at it. | ephemeral answer | no | `pings_setup_created` | 2 |
| `black_bloc/pings.py:130` | Used the role **{role}** that was already here and pointed both feeds at it. | ephemeral answer | no | `pings_setup_reused` | 2 |
| `black_bloc/pings.py:131` | Both feeds already pointed at **{role}**, so nothing was changed. | ephemeral answer | no | `pings_setup_unchanged` | 2 |
| `black_bloc/pings.py:132` | Put it on the *{menu}* panel — `/rolemenu` ▸ *{menu}* ▸ **Post it**. | ephemeral answer | no | `pings_setup_menu_added` | 2 |
| `black_bloc/pings.py:133` | It is already on the *{menu}* panel. | ephemeral answer | no | `pings_setup_menu_there` | 2 |
| `black_bloc/pings.py:134` | Ping roles are still off, so nobody can opt in yet — turn them on with `/setting… | ephemeral answer | no | `pings_setup_still_off` | 2 |
| `black_bloc/pings.py:560` | go-live and event pings | ephemeral answer | no | `pings_feed_said` | 2 |
| `black_bloc/pings.py:560` | go-live pings | ephemeral answer | no | `pings_feed_said_2` | 2 |
| `black_bloc/pings.py:560` | event pings | ephemeral answer | no | `pings_feed_said_3` | 2 |
| `black_bloc/pings.py:560` | raid-train pings | ephemeral answer | no | `pings_feed_said_4` | 2 |
| `black_bloc/pings.py:566` | Staff have not set up the raid-train role yet, so there is nothing to opt in to.… | ephemeral answer | no | `pings_no_raid_role` | 2 |
| `black_bloc/pings.py:581` | Nobody has gone live here yet, so there is nobody to follow. Black Bloc puts som… | ephemeral answer | no | `pings_no_streamers` | 2 |
| `black_bloc/pings.py:585` | **{given}** is not somebody with a ping role here any more, so nothing was chang… | ephemeral answer | no | `pings_no_such_streamer` | 2 |
| `black_bloc/pings.py:589` | **{name}** has no ping role yet, and on this server only staff start one, so not… | ephemeral answer | no | `pings_staff_only_follow` | 2 |
| `black_bloc/pings.py:594` | **{given}** is not on this server's streamer list any more, so nothing was chang… | ephemeral answer | no | `pings_not_on_the_list_any_more` | 2 |
| `black_bloc/pings.py:598` | You already follow **{name}**, so nothing was changed. **Stop following…** stops… | ephemeral answer | no | `pings_already_following` | 2 |
| `black_bloc/pings.py:601` | You do not follow **{name}**, so there was nothing to stop. | ephemeral answer | no | `pings_not_following` | 2 |
| `black_bloc/pings.py:602` | Done — you now wear **{role}**, so Black Bloc mentions you when **{name}** goes … | ephemeral answer | no | `pings_following` | 2 |
| `black_bloc/pings.py:606` | Done — you no longer get **{name}**'s go-live pings. | ephemeral answer | no | `pings_unfollowed` | 2 |
| `black_bloc/pings.py:607` | Done — you now wear **{role}**, so you get {what}. The same button turns them ba… | ephemeral answer | no | `pings_events_on` | 2 |
| `black_bloc/pings.py:610` | Done — you no longer get {what}. The same button puts them back on. | ephemeral answer | no | `pings_events_off` | 2 |
| `black_bloc/pings.py:611` | You already wear **{role}**, so nothing was changed. | ephemeral answer | no | `pings_events_already_on` | 2 |
| `black_bloc/pings.py:612` | You do not wear **{role}**, so there was nothing to take off. | ephemeral answer | no | `pings_events_already_off` | 2 |
| `black_bloc/pings.py:613` | • {what} — **on** (<@&{role_id}>) | ephemeral answer | no | `pings_list_events_on` | 2 |
| `black_bloc/pings.py:614` | • {what} — **off**; the button below turns them on | ephemeral answer | no | `pings_list_events_off` | 2 |
| `black_bloc/pings.py:615` | • {what} — staff have not set up the Events role yet | ephemeral answer | no | `pings_list_events_unset` | 2 |
| `black_bloc/pings.py:616` | • {what} — the role staff picked (**{role_id}**) is not in this server any more | ephemeral answer | no | `pings_list_events_gone` | 2 |
| `black_bloc/pings.py:619` | • You follow no streamers. **Follow a streamer…** picks one. | ephemeral answer | no | `pings_list_none` | 2 |
| `black_bloc/pings.py:620` | • **{name}** — <@&{role_id}> | ephemeral answer | no | `pings_list_one` | 2 |
| `black_bloc/pings.py:621` | • You are **on** the streamer list, so people can follow you from here. **Take m… | ephemeral answer | no | `pings_list_yours_on` | 2 |
| `black_bloc/pings.py:625` | • You are **off** the streamer list, so nobody new can follow you and going live… | ephemeral answer | no | `pings_list_yours_off` | 2 |
| `black_bloc/pings.py:629` | {shown} of {total} — the rest are on the dashboard's Go-live tab | ephemeral answer | no | `pings_streamers_capped` | 2 |
| `black_bloc/pings.py:630` | {shown} of {total} — the rest are on Discord's onboarding screen | ephemeral answer | no | `pings_streamers_capped_member` | 2 |
| `black_bloc/pings.py:631` | You have no ping role, so there was nothing to take away. | ephemeral answer | no | `pings_fans_off_none` | 2 |
| `black_bloc/pings.py:632` | Black Bloc has not seen anybody streaming here yet, so the streamer list is empt… | ephemeral answer | no | `pings_streamer_list_empty` | 2 |
| `black_bloc/pings.py:638` | **hidden** | ephemeral answer | no | `pings_hidden_word` | 2 |
| `black_bloc/pings.py:639` | no ping role yet | ephemeral answer | no | `pings_no_role_word` | 2 |
| `black_bloc/pings.py:640` | {count} follower(s) | ephemeral answer | no | `pings_followers_known` | 2 |
| `black_bloc/pings.py:641` | the role is gone from the server | ephemeral answer | no | `pings_followers_unknown` | 2 |
| `black_bloc/pings.py:646` | {shown} of {total} — the rest are on Discord's onboarding screen | ephemeral answer | no | `pings_capped_follow` | 2 |
| `black_bloc/pings.py:647` | Saved. A streamer's ping role will be called **{example}**. | ephemeral answer | no | `pings_template_ok` | 2 |
| `black_bloc/pings.py:648` | Saved, but **{given}** is not something Black Bloc can fill in, so a ping role w… | ephemeral answer | no | `pings_template_broken` | 2 |
| `black_bloc/pings.py:652` | Nothing was given, so nothing changed. | ephemeral answer | no | `pings_settings_nothing` | 2 |
| `black_bloc/pings.py:653` | Saved — | ephemeral answer | no | `pings_settings_saved` | 2 |
| `black_bloc/pings.py:654` | **{key}** is now `{value}` | ephemeral answer | no | `pings_settings_one` | 2 |
| `black_bloc/pings.py:695` | Take your own ping role away? The people who follow you stop being pinged when y… | ephemeral answer | no | `pings_own_drop_question` | 2 |
| `black_bloc/pings.py:698` | Yes, take it away | ephemeral answer | no | `pings_own_drop_yes` | 2 |
| `black_bloc/pings.py:699` | Take **{name}**'s ping role away? Everybody who followed them simply stops being… | ephemeral answer | no | `pings_card_remove_question` | 2 |
| `black_bloc/pings.py:702` | Yes, take it away | ephemeral answer | no | `pings_card_remove_yes` | 2 |
| `black_bloc/pings.py:706` | Turn {what} on | ephemeral answer | no | `pings_events_on_label_feed` | 2 |
| `black_bloc/pings.py:707` | Turn {what} off | ephemeral answer | no | `pings_events_off_label_feed` | 2 |
| `black_bloc/pings.py:740` | Take yourself off the streamer list? Nobody new can follow you, going live does … | ephemeral answer | no | `pings_list_out_question` | 2 |
| `black_bloc/pings.py:744` | Yes, take me off | ephemeral answer | no | `pings_list_out_yes` | 2 |
| `black_bloc/pings.py:1248` | Black Bloc has never seen you streaming, so you are not on the streamer list and… | ephemeral answer | no | `pings_not_on_the_list` | 2 |
| `black_bloc/pings.py:1252` | **{name}** is already off the streamer list, so nothing was changed. **Put me ba… | ephemeral answer | no | `pings_already_hidden` | 2 |
| `black_bloc/pings.py:1256` | **{name}** is already on the streamer list, so nothing was changed. | ephemeral answer | no | `pings_already_listed` | 2 |
| `black_bloc/pings.py:1257` | Done — you are off the streamer list, so nobody new can follow you and going liv… | ephemeral answer | no | `pings_hidden_self` | 2 |
| `black_bloc/pings.py:1261` | Nobody was following you, so your ping role **{role}** is gone too. | ephemeral answer | no | `pings_hidden_self_role_gone` | 2 |
| `black_bloc/pings.py:1262` | Done — **{name}** is off the streamer list, so nobody new can follow them and go… | ephemeral answer | no | `pings_hidden_staff` | 2 |
| `black_bloc/pings.py:1266` | Done — you are back on the streamer list, so people can follow you from `/pings`… | ephemeral answer | no | `pings_restored_self` | 2 |
| `black_bloc/pings.py:1269` | Done — **{name}** is back on the streamer list. | ephemeral answer | no | `pings_restored_staff` | 2 |
| `black_bloc/pings.py:1270` | **{given}** is not somebody on this server's streamer list, so nothing was chang… | ephemeral answer | no | `pings_no_such_listing` | 2 |
| `black_bloc/pings.py:1592` | Made the role **{role}** and pointed raid-train pings at it. Members opt in with… | ephemeral answer | no | `pings_raidtrain_created` | 2 |
| `black_bloc/pings.py:1596` | Used the role **{role}** that was already here and pointed raid-train pings at i… | ephemeral answer | no | `pings_raidtrain_reused` | 2 |
| `black_bloc/pings.py:1600` | Raid-train pings already pointed at **{role}**, so nothing was changed. | ephemeral answer | no | `pings_raidtrain_unchanged` | 2 |
| `black_bloc/pings_onboarding.py:18` | Black Bloc pings onboarding | ephemeral answer | no | `pings_reason` | 2 |
| `black_bloc/pings_onboarding.py:24` | This server is not a Community server yet, so Discord has no onboarding screen t… | ephemeral answer | no | `pings_no_community` | 2 |
| `black_bloc/pings_onboarding.py:29` | Black Bloc is not managing this server's onboarding, so nothing was changed. **M… | ephemeral answer | no | `pings_not_managed` | 2 |
| `black_bloc/pings_onboarding.py:33` | There is nothing to put on the onboarding screen yet — staff have not set up the… | ephemeral answer | no | `pings_nothing_to_say` | 2 |
| `black_bloc/pings_onboarding.py:37` | Discord's onboarding screen already says exactly this, so nothing was written. | ephemeral answer | no | `pings_unchanged` | 2 |
| `black_bloc/pings_onboarding.py:38` | Done — Discord's onboarding screen now carries {prompts}. {what} | ephemeral answer | no | `pings_wrote` | 2 |
| `black_bloc/pings_onboarding.py:39` | **{more}** more streamer(s) are on `/pings` rather than the screen. | ephemeral answer | no | `pings_wrote_capped` | 2 |
| `black_bloc/pings_onboarding.py:40` | Discord refused the onboarding write, so nothing was changed: {why}. Black Bloc … | ephemeral answer | no | `pings_refused` | 2 |
| `black_bloc/pings_onboarding.py:45` | Black Bloc keeps **{count}** onboarding prompt(s) in step with the ping roles. I… | ephemeral answer | no | `pings_card_managed` | 2 |
| `black_bloc/pings_onboarding.py:49` | Black Bloc is **not** managing this server's onboarding. The prompts are exactly… | ephemeral answer | no | `pings_card_not_managed` | 2 |
| `black_bloc/pings_onboarding.py:53` | This server is not a Community server, so there is no onboarding screen. The *No… | ephemeral answer | no | `pings_card_no_community` | 2 |
| `black_bloc/pings_onboarding.py:57` | **{title}** — {options} | ephemeral answer | no | `pings_card_prompt` | 2 |
| `black_bloc/pings_onboarding.py:58` | nothing to offer yet | ephemeral answer | no | `pings_card_no_options` | 2 |
| `black_bloc/pings_onboarding.py:59` | Last written: {when} | ephemeral answer | no | `pings_card_last_sync` | 2 |
| `black_bloc/pings_onboarding.py:60` | Black Bloc has not written to onboarding yet. | ephemeral answer | no | `pings_card_never_synced` | 2 |
| `black_bloc/pings_onboarding.py:61` | **{count}** prompt(s) here belong to somebody else and are left exactly as they … | ephemeral answer | no | `pings_card_foreign` | 2 |
| `black_bloc/pings_onboarding.py:65` | Events | ephemeral answer | no | `pings_events_option` | 2 |
| `black_bloc/pings_onboarding.py:66` | Go-lives | ephemeral answer | no | `pings_golive_option` | 2 |
| `black_bloc/pings_onboarding.py:67` | Events and go-lives | ephemeral answer | no | `pings_both_option` | 2 |
| `black_bloc/pings_onboarding.py:68` | Raid trains | ephemeral answer | no | `pings_raid_option` | 2 |

### raid trains

*122 strings — 1 keyed · 43 unkeyed pass 1 · 70 unkeyed pass 2 · 9 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/cogs/content/raidtrain.py:2356` | *(the key's value)* | read from the store at render | **yes → `raidtrain_scheduled_name_template`** (ns `raidtrain`, 2 read site(s)) | — | 1 |
| `black_bloc/api/tools/raidtrain.py:63` | A raid train needs a title, so nothing was made. Give it one and try again. | card title | no | `raidtrain_no_title` | 1 |
| `black_bloc/cogs/content/raidtrain.py:162` | lineups go to {} | card field | no | `raidtrain_setup_words` | 1 |
| `black_bloc/cogs/content/raidtrain.py:162` | organizers are {} | card field | no | `raidtrain_setup_words_2` | 1 |
| `black_bloc/cogs/content/raidtrain.py:162` | {} is pinged | card field | no | `raidtrain_setup_words_3` | 1 |
| `black_bloc/cogs/content/raidtrain.py:781` | Raid train #{train_id} | card title | no | `raidtrain_card_title` | 1 |
| `black_bloc/cogs/content/raidtrain.py:782` | The hours you hold | card title | no | `raidtrain_mine_title` | 1 |
| `black_bloc/cogs/content/raidtrain.py:783` | Where lineups go, and who may run them | card title | no | `raidtrain_setup_title` | 1 |
| `black_bloc/cogs/content/raidtrain.py:784` | Put somebody in | card title | no | `raidtrain_put_in_title` | 1 |
| `black_bloc/cogs/content/raidtrain.py:785` | Change two slots round | card title | no | `raidtrain_swap_title` | 1 |
| `black_bloc/cogs/content/raidtrain.py:786` | Give an hour back | card title | no | `raidtrain_give_back_title` | 1 |
| `black_bloc/cogs/content/raidtrain.py:791` | A train… | select placeholder | no | `raidtrain_train_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:793` | Mode… | select placeholder | no | `raidtrain_mode_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:794` | Take an hour… | select placeholder | no | `raidtrain_claim_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:795` | Take somebody off… | select placeholder | no | `raidtrain_take_off_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:796` | Which slot… | select placeholder | no | `raidtrain_slot_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:797` | First… | select placeholder | no | `raidtrain_first_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:798` | Second… | select placeholder | no | `raidtrain_second_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:799` | Which hour… | select placeholder | no | `raidtrain_hour_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:800` | Who takes it? | select placeholder | no | `raidtrain_who_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:801` | Where the lineup post lives | select placeholder | no | `raidtrain_channel_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:802` | Who may build a lineup, besides staff | select placeholder | no | `raidtrain_organizer_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:803` | Who is pinged in front of a lineup | select placeholder | no | `raidtrain_ping_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:804` | Clear… | select placeholder | no | `raidtrain_clear_placeholder` | 1 |
| `black_bloc/cogs/content/raidtrain.py:806` | Raid trains are **{mode}**. | channel post | no | `raidtrain_mode_line` | 1 |
| `black_bloc/cogs/content/raidtrain.py:807` | In **shadow** every move is recorded and the lineup post and the DMs are held ba… | channel post | no | `raidtrain_shadow_line` | 1 |
| `black_bloc/cogs/content/raidtrain.py:810` | Raid trains are **off**, so nothing new can be started. | channel post | no | `raidtrain_off_line` | 1 |
| `black_bloc/cogs/content/raidtrain.py:812` | **#{train_id} {title}** — {when} · {taken}/{total} filled · {status} · open: {fr… | channel post | no | `raidtrain_train_line` | 1 |
| `black_bloc/cogs/content/raidtrain.py:816` | The sweep runs every {every} minute(s): {running}, last clean pass {ok}, {failur… | channel post | no | `raidtrain_sweep_line` | 1 |
| `black_bloc/cogs/content/raidtrain.py:824` | {trains} train(s), {upcoming} still to come · {claimed} of {slots} hour(s) claim… | channel post | no | `raidtrain_totals_line` | 1 |
| `black_bloc/cogs/content/raidtrain.py:827` | **#{train_id} {title}** — slot #{position}, {when} | channel post | no | `raidtrain_mine_line` | 1 |
| `black_bloc/cogs/content/raidtrain.py:835` | The lineup channel | card field | no | `raidtrain_setup_labels` | 1 |
| `black_bloc/cogs/content/raidtrain.py:835` | The organizer role | card field | no | `raidtrain_setup_labels_2` | 1 |
| `black_bloc/cogs/content/raidtrain.py:835` | The ping role | card field | no | `raidtrain_setup_labels_3` | 1 |
| `black_bloc/cogs/content/raidtrain.py:1584` | Back | button label | no | `raidtrain_button_back` | 1 |
| `black_bloc/raidtrain.py:56` | open for sign-ups | card field | no | `raidtrain_status_words` | 1 |
| `black_bloc/raidtrain.py:56` | locked — the lineup is set | card field | no | `raidtrain_status_words_2` | 1 |
| `black_bloc/raidtrain.py:56` | running now | card field | no | `raidtrain_status_words_3` | 1 |
| `black_bloc/raidtrain.py:102` | Raid trains | card title | no | `raidtrain_panel_title` | 1 |
| `black_bloc/raidtrain.py:103` | This panel has gone quiet — run /raidtrain again | card description | no | `raidtrain_panel_timeout_footer` | 1 |
| `black_bloc/raidtrain.py:132` | Give back slot #{position} | card field | no | `raidtrain_give_back_label` | 1 |
| `black_bloc/raidtrain.py:134` | Start a raid train — draft | card title | no | `raidtrain_draft_title` | 1 |
| `black_bloc/raidtrain.py:135` | Start | button label | no | `raidtrain_start_button` | 1 |
| `black_bloc/raidtrain.py:136` | A raid train needs a name, so nothing was made. Put something in the Title box —… | card title | no | `raidtrain_no_train_title` | 1 |
| `black_bloc/api/tools/raidtrain.py:59` | Black Bloc has no raid train **{train_id}** in this server, so nothing was done.… | ephemeral answer | no | `raidtrain_no_such_train` | 2 |
| `black_bloc/api/tools/raidtrain.py:64` | A raid train runs {count_min} to {count_max} slots of {min} to {max} minutes eac… | ephemeral answer | no | `raidtrain_bad_size` | 2 |
| `black_bloc/api/tools/raidtrain.py:68` | **{status}** is not a state a raid train can be in. It is one of open, locked, l… | ephemeral answer | no | `raidtrain_bad_status` | 2 |
| `black_bloc/api/tools/raidtrain.py:72` | **{title}** is up with {count} slot(s) of {minutes} minutes each. | ephemeral answer | no | `raidtrain_created` | 2 |
| `black_bloc/api/tools/raidtrain.py:73` | **{title}** is now **{status}**. | ephemeral answer | no | `raidtrain_status_set` | 2 |
| `black_bloc/api/tools/raidtrain.py:74` | Cancelling tells everybody who signed up, so it needs a reason to tell them. Typ… | ephemeral answer | no | `raidtrain_cancel_needs_reason` | 2 |
| `black_bloc/cogs/content/raidtrain.py:111` | Building a raid train's lineup is for {who}, so nothing was changed. Ask one of … | ephemeral answer | no | `raidtrain_not_an_organizer` | 2 |
| `black_bloc/cogs/content/raidtrain.py:115` | Black Bloc has no raid train **{train}** here any more, so nothing was done. Pre… | ephemeral answer | no | `raidtrain_no_such_train_2` | 2 |
| `black_bloc/cogs/content/raidtrain.py:119` | There is no raid train on the calendar right now. An organizer starts one with *… | ephemeral answer | no | `raidtrain_nothing_upcoming` | 2 |
| `black_bloc/cogs/content/raidtrain.py:123` | You do not hold a slot on any raid train. **Back** shows the ones that are comin… | ephemeral answer | no | `raidtrain_nothing_held` | 2 |
| `black_bloc/cogs/content/raidtrain.py:126` | **{title}** is up with {count} slot(s) of {minutes} minutes, starting <t:{when}:… | ephemeral answer | no | `raidtrain_created_2` | 2 |
| `black_bloc/cogs/content/raidtrain.py:130` | The lineup is in <#{channel_id}>. | ephemeral answer | no | `raidtrain_lineup_here` | 2 |
| `black_bloc/cogs/content/raidtrain.py:131` | There is nowhere to put the lineup yet — a Lead picks a channel under **Setup…**… | ephemeral answer | no | `raidtrain_lineup_nowhere` | 2 |
| `black_bloc/cogs/content/raidtrain.py:135` | Slot **#{position}** on **{title}** is yours — <t:{when}:F> (<t:{when}:R>). You … | ephemeral answer | no | `raidtrain_claimed` | 2 |
| `black_bloc/cogs/content/raidtrain.py:139` | Raid trains are in **shadow** at the moment, so no DM is actually sent. | ephemeral answer | no | `raidtrain_claimed_shadow` | 2 |
| `black_bloc/cogs/content/raidtrain.py:140` | Slot **#{position}** on **{title}** is open again, so somebody else can take tha… | ephemeral answer | no | `raidtrain_released` | 2 |
| `black_bloc/cogs/content/raidtrain.py:143` | Slot **#{position}** on **{title}** now belongs to {who}. | ephemeral answer | no | `raidtrain_assigned` | 2 |
| `black_bloc/cogs/content/raidtrain.py:144` | Slot **#{position}** on **{title}** is open again. | ephemeral answer | no | `raidtrain_unassigned` | 2 |
| `black_bloc/cogs/content/raidtrain.py:145` | Slot **#{position}** is already empty, so there was nothing to take off it. | ephemeral answer | no | `raidtrain_nobody_there` | 2 |
| `black_bloc/cogs/content/raidtrain.py:146` | Slots **#{a}** and **#{b}** on **{title}** have changed places. | ephemeral answer | no | `raidtrain_swapped` | 2 |
| `black_bloc/cogs/content/raidtrain.py:147` | Those are the same slot, so nothing was changed. | ephemeral answer | no | `raidtrain_same_slot` | 2 |
| `black_bloc/cogs/content/raidtrain.py:148` | **{title}** is locked — its lineup cannot be changed until it is unlocked. | ephemeral answer | no | `raidtrain_locked_now` | 2 |
| `black_bloc/cogs/content/raidtrain.py:149` | **{title}** is open for sign-ups again. | ephemeral answer | no | `raidtrain_unlocked_now` | 2 |
| `black_bloc/cogs/content/raidtrain.py:150` | **{title}** is cancelled, and the {count} person/people who held a slot were tol… | ephemeral answer | no | `raidtrain_cancelled_now` | 2 |
| `black_bloc/cogs/content/raidtrain.py:151` | **{who}** has no Twitch channel linked, so the lineup cannot say who to raid. Th… | ephemeral answer | no | `raidtrain_member_not_linked` | 2 |
| `black_bloc/cogs/content/raidtrain.py:155` | Raid trains are now **{mode}**.{extra} | ephemeral answer | no | `raidtrain_mode_set` | 2 |
| `black_bloc/cogs/content/raidtrain.py:156` | Nothing has anywhere to be posted yet: neither `raidtrain_channel_id` nor `event… | ephemeral answer | no | `raidtrain_no_channel_yet` | 2 |
| `black_bloc/cogs/content/raidtrain.py:160` | Nothing was picked, so nothing changed. | ephemeral answer | no | `raidtrain_setup_nothing` | 2 |
| `black_bloc/cogs/content/raidtrain.py:161` | Raid trains: {parts}. | ephemeral answer | no | `raidtrain_setup_done` | 2 |
| `black_bloc/cogs/content/raidtrain.py:167` | lineups have nowhere of their own again | ephemeral answer | no | `raidtrain_setup_cleared` | 2 |
| `black_bloc/cogs/content/raidtrain.py:167` | only staff may build a lineup again | ephemeral answer | no | `raidtrain_setup_cleared_2` | 2 |
| `black_bloc/cogs/content/raidtrain.py:167` | nobody is pinged in front of a lineup | ephemeral answer | no | `raidtrain_setup_cleared_3` | 2 |
| `black_bloc/cogs/content/raidtrain.py:178` | **{title}** is now **{status}**. | ephemeral answer | no | `raidtrain_moved_now` | 2 |
| `black_bloc/cogs/content/raidtrain.py:787` | Call off {title} | modal title or field | no | `raidtrain_cancel_title` | 2 |
| `black_bloc/cogs/content/raidtrain.py:788` | What the people who signed up are told | modal title or field | no | `raidtrain_cancel_label` | 2 |
| `black_bloc/cogs/content/raidtrain.py:789` | Before you can take an hour | ephemeral answer | no | `raidtrain_link_first` | 2 |
| `black_bloc/cogs/content/raidtrain.py:792` | {shown} of {total} — the rest are on the Events page | ephemeral answer | no | `raidtrain_train_capped` | 2 |
| `black_bloc/cogs/content/raidtrain.py:811` | **Mode…** below is how a Lead turns them on. | ephemeral answer | no | `raidtrain_off_line_staff` | 2 |
| `black_bloc/cogs/content/raidtrain.py:815` | Lineups go to <#{channel_id}>. | ephemeral answer | no | `raidtrain_lineup_channel` | 2 |
| `black_bloc/cogs/content/raidtrain.py:821` | **not running** | ephemeral answer | no | `raidtrain_sweep_stopped` | 2 |
| `black_bloc/cogs/content/raidtrain.py:823` | The last sweep did not finish: {why}. | ephemeral answer | no | `raidtrain_sweep_trouble` | 2 |
| `black_bloc/cogs/content/raidtrain.py:828` | The lineup post goes to {where}. | ephemeral answer | no | `raidtrain_setup_channel_now` | 2 |
| `black_bloc/cogs/content/raidtrain.py:829` | Organizers are {who}. | ephemeral answer | no | `raidtrain_setup_organizer_now` | 2 |
| `black_bloc/cogs/content/raidtrain.py:830` | The lineup pings {who}. | ephemeral answer | no | `raidtrain_setup_ping_now` | 2 |
| `black_bloc/cogs/content/raidtrain.py:831` | nobody yet | ephemeral answer | no | `raidtrain_setup_unset` | 2 |
| `black_bloc/cogs/content/raidtrain.py:832` | Pick what you want to change and press **Save**. **Clear…** empties one of them … | ephemeral answer | no | `raidtrain_setup_how` | 2 |
| `black_bloc/cogs/content/raidtrain.py:840` | Pick the hour and the person, then press **Put them in**. | ephemeral answer | no | `raidtrain_put_in_how` | 2 |
| `black_bloc/cogs/content/raidtrain.py:841` | Hour **#{slot}**, {who}. | ephemeral answer | no | `raidtrain_put_in_picked` | 2 |
| `black_bloc/cogs/content/raidtrain.py:842` | Pick an hour and a person first, then press **Put them in**. | ephemeral answer | no | `raidtrain_put_in_needs_both` | 2 |
| `black_bloc/cogs/content/raidtrain.py:843` | Pick two hours, then press **Swap them**. The people move; the times do not. | ephemeral answer | no | `raidtrain_swap_how` | 2 |
| `black_bloc/cogs/content/raidtrain.py:844` | First **#{first}**, second **{second}**. | ephemeral answer | no | `raidtrain_swap_picked` | 2 |
| `black_bloc/cogs/content/raidtrain.py:845` | Pick two hours first, then press **Swap them**. | ephemeral answer | no | `raidtrain_swap_needs_both` | 2 |
| `black_bloc/cogs/content/raidtrain.py:846` | Pick the hour you would rather not keep. It opens again for somebody else. | ephemeral answer | no | `raidtrain_give_back_how` | 2 |
| `black_bloc/cogs/content/raidtrain.py:847` | You do not hold an hour on this train any more, so nothing was given back. | ephemeral answer | no | `raidtrain_not_on_this_train` | 2 |
| `black_bloc/cogs/content/raidtrain.py:1515` | Title | modal field label | no | `raidtrain_modal_title` | 2 |
| `black_bloc/cogs/content/raidtrain.py:1517` | What is it? | modal field label | no | `raidtrain_modal_what_is_it` | 2 |
| `black_bloc/cogs/content/raidtrain.py:1523` | Minutes per slot | modal field label | no | `raidtrain_modal_minutes_per_slot` | 2 |
| `black_bloc/cogs/content/raidtrain.py:1526` | How many slots | modal field label | no | `raidtrain_modal_how_many_slots` | 2 |
| `black_bloc/raidtrain.py:64` | **{status}** is the end of the line for a raid train, so nothing was changed. | ephemeral answer | no | `raidtrain_nowhere_to_move` | 2 |
| `black_bloc/raidtrain.py:65` | A raid train that is **{status}** cannot be marked **{to}**, so nothing was chan… | ephemeral answer | no | `raidtrain_cannot_move` | 2 |
| `black_bloc/raidtrain.py:69` | Black Bloc needs to know your Twitch channel before you can take a slot, because… | ephemeral answer | no | `raidtrain_needs_link` | 2 |
| `black_bloc/raidtrain.py:74` | Slot **#{position}** already belongs to someone else, so nothing was changed. Th… | ephemeral answer | no | `raidtrain_slot_taken` | 2 |
| `black_bloc/raidtrain.py:78` | This train has no slot **#{position}**, so nothing was changed. It runs from #1 … | ephemeral answer | no | `raidtrain_slot_unknown` | 2 |
| `black_bloc/raidtrain.py:82` | Every slot on **{title}** is taken, so there was nothing to claim. | ephemeral answer | no | `raidtrain_train_full` | 2 |
| `black_bloc/raidtrain.py:83` | You already hold {held} slot(s) on **{title}**, which is as many as this server … | ephemeral answer | no | `raidtrain_cap_reached` | 2 |
| `black_bloc/raidtrain.py:88` | **{title}** is locked, so its lineup cannot be changed. An organizer opens it ag… | ephemeral answer | no | `raidtrain_train_locked` | 2 |
| `black_bloc/raidtrain.py:92` | Slot **#{position}** is not yours, so nothing was released. **My slots…** on `/r… | ephemeral answer | no | `raidtrain_not_yours` | 2 |
| `black_bloc/raidtrain.py:96` | Take an hour with `/raidtrain` — pick this train, then **Take an hour…**. Link y… | ephemeral answer | no | `raidtrain_claim_here` | 2 |
| `black_bloc/raidtrain.py:140` | **{given}** is not a whole number, so no train was made. Slots are {min}-{max} m… | ephemeral answer | no | `raidtrain_bad_number` | 2 |
| `black_bloc/raidtrain.py:144` | A raid train runs {count_min} to {count_max} slots of {min} to {max} minutes eac… | ephemeral answer | no | `raidtrain_out_of_range` | 2 |

### applications

*183 strings — 0 keyed · 35 unkeyed pass 1 · 129 unkeyed pass 2 · 19 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/api/tools/applications.py:36` | An application form needs a short name and a heading, so nothing was created. Fi… | channel / role name | no | `applications_needs_a_name` | 1 |
| `black_bloc/applications.py:73` | You're in — staff said yes. | channel post | no | `applications_default_approved_text` | 1 |
| `black_bloc/applications.py:201` | **{title}** on **{guild}** — approved. {said} | DM | no | `applications_dm_approved` | 1 |
| `black_bloc/applications.py:202` | **{title}** on **{guild}** — staff said no. The reason given was: {reason}. You … | DM | no | `applications_dm_denied` | 1 |
| `black_bloc/applications.py:206` | **{title}** on **{guild}** — staff took you off the list. The reason given was: … | DM | no | `applications_dm_removed` | 1 |
| `black_bloc/applications.py:210` | Your **{title}** application on **{guild}** is with staff now. You'll get a DM e… | DM | no | `applications_dm_received` | 1 |
| `black_bloc/applications.py:214` | Discord refused to add the role, so it is still off them — hand it over from `/r… | channel post | no | `applications_grant_failed_on_card` | 1 |
| `black_bloc/applications.py:219` | Applications | card title | no | `applications_panel_title` | 1 |
| `black_bloc/applications.py:220` | This panel has gone quiet — run /apply again | card description | no | `applications_panel_timeout_footer` | 1 |
| `black_bloc/applications.py:221` | Apply for what this server hands out, and see where what you already sent has go… | card description | no | `applications_panel_intro` | 1 |
| `black_bloc/applications.py:231` | **{forms}** form(s) · **{waiting}** waiting · **{approved}** on a list | channel post | no | `applications_counts_line` | 1 |
| `black_bloc/applications.py:519` | Applicant | card field name | no | `applications_card_applicant` | 1 |
| `black_bloc/applications.py:520` | Sent | card field name | no | `applications_card_sent` | 1 |
| `black_bloc/applications.py:521` | Status | card field name | no | `applications_card_status` | 1 |
| `black_bloc/applications.py:530` | Decided by | card field name | no | `applications_card_decided_by` | 1 |
| `black_bloc/applications.py:534` | Reason | card field name | no | `applications_card_reason` | 1 |
| `black_bloc/cogs/community/applications.py:49` | Take off the list | card field | no | `applications_take_off_label` | 1 |
| `black_bloc/cogs/community/applications.py:65` | **{title}** ⏎ {description} ⏎ Press **Apply** to fill the form in. Staff look at… | channel post | no | `applications_panel_body` | 1 |
| `black_bloc/cogs/community/applications.py:114` | Making and changing forms is for staff. | channel post | no | `applications_panel_staff_only_line` | 1 |
| `black_bloc/cogs/community/applications.py:136` | <@{user_id}>{gone}{twitch} · on since {stamp} | channel post | no | `applications_roster_line` | 1 |
| `black_bloc/cogs/community/applications.py:138` | No questions on it yet, so nobody can apply for it. | channel post | no | `applications_no_questions_line` | 1 |
| `black_bloc/cogs/community/applications.py:139` | **{questions}** question(s) · **{waiting}** waiting · **{approved}** approved | channel post | no | `applications_form_counts_line` | 1 |
| `black_bloc/cogs/community/applications.py:144` | Applications — settings | card title | no | `applications_settings_title` | 1 |
| `black_bloc/cogs/community/applications.py:155` | short or long | card description | no | `applications_style_hint` | 1 |
| `black_bloc/cogs/community/applications.py:156` | yes or no | card description | no | `applications_required_hint` | 1 |
| `black_bloc/cogs/community/applications.py:266` | If you are approved | card field name | no | `applications_card_if_you_are_approved` | 1 |
| `black_bloc/cogs/community/applications.py:1012` | Apply | button label | no | `applications_button_apply` | 1 |
| `black_bloc/cogs/community/applications.py:1227` | Where it can go | card field name | no | `applications_card_where_it_can_go` | 1 |
| `black_bloc/cogs/community/applications.py:1494` | Refresh | button label | no | `applications_button_refresh` | 1 |
| `black_bloc/cogs/community/applications.py:1502` | Back | button label | no | `applications_button_back` | 1 |
| `black_bloc/cogs/community/applications.py:1510` | Logs | button label | no | `applications_button_logs` | 1 |
| `black_bloc/cogs/community/applications.py:1518` | Find #… | button label | no | `applications_button_find` | 1 |
| `black_bloc/cogs/community/applications.py:1543` | New form | button label | no | `applications_button_new_form` | 1 |
| `black_bloc/cogs/community/applications.py:2527` | Settings | button label | no | `applications_button_settings` | 1 |
| `black_bloc/cogs/community/applications.py:2609` | Numbers… | button label | no | `applications_button_numbers` | 1 |
| `black_bloc/api/tools/applications.py:40` | Black Bloc has no application form with that number, so there is no list to show… | ephemeral answer | no | `applications_no_roster_form` | 2 |
| `black_bloc/api/tools/applications.py:44` | Black Bloc has no application form with that number any more, so nothing was cha… | ephemeral answer | no | `applications_no_such_form_id` | 2 |
| `black_bloc/api/tools/applications.py:48` | Black Bloc has no application with that number any more, so nothing was changed.… | ephemeral answer | no | `applications_no_such_application` | 2 |
| `black_bloc/api/tools/applications.py:52` | **{role_id}** is not a role in this server any more, so the form was left as it … | ephemeral answer | no | `applications_no_such_role` | 2 |
| `black_bloc/api/tools/applications.py:56` | Black Bloc cannot hand out **{name}**, so the form was not saved. That role is e… | ephemeral answer | no | `applications_unassignable` | 2 |
| `black_bloc/api/tools/applications.py:61` | **{channel_id}** is not a channel Black Bloc can see, so nothing was posted. Pic… | ephemeral answer | no | `applications_no_such_channel` | 2 |
| `black_bloc/api/tools/applications.py:65` | **{given}** is not a state an application can be in, so nothing was listed. They… | ephemeral answer | no | `applications_unknown_status` | 2 |
| `black_bloc/api/tools/applications.py:69` | **{given}** is not a decision, so nothing was changed. It is `approved` or `deni… | ephemeral answer | no | `applications_bad_decision` | 2 |
| `black_bloc/api/tools/applications.py:72` | The questions arrived in a shape Black Bloc could not read, so nothing was chang… | ephemeral answer | no | `applications_bad_questions` | 2 |
| `black_bloc/applications.py:71` | Application #{application_id} — {title} | ephemeral answer | no | `applications_card_heading` | 2 |
| `black_bloc/applications.py:72` | (left blank) | ephemeral answer | no | `applications_no_answer` | 2 |
| `black_bloc/applications.py:75` | **{given}** is not a name Black Bloc can use, so nothing was changed. Use lower-… | ephemeral answer | no | `applications_form_name_shape` | 2 |
| `black_bloc/applications.py:80` | That {what} is {given} characters and Discord will not show more than {limit}, s… | ephemeral answer | no | `applications_too_long` | 2 |
| `black_bloc/applications.py:84` | **{given}** is not a kind of answer box, so nothing was changed. It is `short` (… | ephemeral answer | no | `applications_bad_style` | 2 |
| `black_bloc/applications.py:88` | Discord shows at most {limit} boxes on one form and this would be number {given}… | ephemeral answer | no | `applications_too_many_questions` | 2 |
| `black_bloc/applications.py:92` | **{given}** is not a slot on this form, so nothing was changed. The slots are 1 … | ephemeral answer | no | `applications_bad_position` | 2 |
| `black_bloc/applications.py:96` | **{given}** is not a number of days, so nothing was changed. Type a whole number… | ephemeral answer | no | `applications_bad_days` | 2 |
| `black_bloc/applications.py:101` | This server has no application form called **{name}**, so nothing was changed. `… | ephemeral answer | no | `applications_no_such_form` | 2 |
| `black_bloc/applications.py:105` | This server already has an application form called **{name}**, so nothing was cr… | ephemeral answer | no | `applications_name_taken` | 2 |
| `black_bloc/applications.py:109` | **{name}** has no questions on it yet, so there is nothing to fill in. Staff add… | ephemeral answer | no | `applications_no_questions_yet` | 2 |
| `black_bloc/applications.py:113` | **{title}** is not taking applications right now, so nothing was sent. Staff reo… | ephemeral answer | no | `applications_form_closed` | 2 |
| `black_bloc/applications.py:117` | Applications are turned off right now, so nothing was sent. A Lead turns them on… | ephemeral answer | no | `applications_applications_off` | 2 |
| `black_bloc/applications.py:121` | You already have an application waiting on **{title}**, so nothing was sent twic… | ephemeral answer | no | `applications_already_applied` | 2 |
| `black_bloc/applications.py:125` | Staff decided your last **{title}** application on {when}, so you can apply agai… | ephemeral answer | no | `applications_too_soon` | 2 |
| `black_bloc/applications.py:129` | Sent to staff — you'll get a DM either way. `/apply` says where it is, and its *… | ephemeral answer | no | `applications_sent` | 2 |
| `black_bloc/applications.py:133` | Your application for **{title}** is saved, but Black Bloc could not put the card… | ephemeral answer | no | `applications_card_not_posted` | 2 |
| `black_bloc/applications.py:137` | Test mode is on, so the card for staff is in the test channel rather than in the… | ephemeral answer | no | `applications_card_in_test_channel` | 2 |
| `black_bloc/applications.py:141` | You have nothing waiting on **{title}**, so there was nothing to take back. `/ap… | ephemeral answer | no | `applications_nothing_to_withdraw` | 2 |
| `black_bloc/applications.py:145` | Black Bloc has no record of that application any more, so nothing was changed. T… | ephemeral answer | no | `applications_nothing_to_decide` | 2 |
| `black_bloc/applications.py:149` | Somebody got there first — that application is already **{status}**, so nothing … | ephemeral answer | no | `applications_already_decided` | 2 |
| `black_bloc/applications.py:153` | That application belongs to somebody else's server, so nothing was changed. | ephemeral answer | no | `applications_not_this_server` | 2 |
| `black_bloc/applications.py:156` | **{name}** is not in this server any more, so the role could not be handed over … | ephemeral answer | no | `applications_member_has_gone` | 2 |
| `black_bloc/applications.py:160` | A denied application needs one line the person is sent, so nothing was done. Say… | ephemeral answer | no | `applications_deny_needs_a_reason` | 2 |
| `black_bloc/applications.py:164` | Taking somebody off the list needs one line they are sent, so nothing was done. … | ephemeral answer | no | `applications_remove_needs_a_reason` | 2 |
| `black_bloc/applications.py:168` | That application is **{status}**, not approved, so there was nobody to take off … | ephemeral answer | no | `applications_remove_not_approved` | 2 |
| `black_bloc/applications.py:172` | The application is marked approved, but Discord refused to add **{role}** — Blac… | ephemeral answer | no | `applications_role_refused_after_decision` | 2 |
| `black_bloc/applications.py:177` | Nobody is waiting on staff right now. | ephemeral answer | no | `applications_nothing_pending` | 2 |
| `black_bloc/applications.py:178` | This server has no application forms yet. `/apply` → **New form** makes the firs… | ephemeral answer | no | `applications_no_forms_yet` | 2 |
| `black_bloc/applications.py:182` | **{name}** still has {count} application(s) waiting on staff, so it was not dele… | ephemeral answer | no | `applications_form_has_pending` | 2 |
| `black_bloc/applications.py:186` | Black Bloc has nowhere to put the Apply button, so nothing was posted. Say which… | ephemeral answer | no | `applications_panel_nowhere` | 2 |
| `black_bloc/applications.py:190` | Black Bloc could not put the Apply button up for **{name}** — the log says why. … | ephemeral answer | no | `applications_panel_stuck` | 2 |
| `black_bloc/applications.py:194` | Approved — **{name}** has **{role}** now.{extra} | ephemeral answer | no | `applications_approved_said` | 2 |
| `black_bloc/applications.py:195` | Approved — **{name}** is on the **{title}** list now. | ephemeral answer | no | `applications_approved_on_record` | 2 |
| `black_bloc/applications.py:196` | Denied, and they have been told why. | ephemeral answer | no | `applications_denied_said` | 2 |
| `black_bloc/applications.py:197` | Taken off the list, and they have been told why. | ephemeral answer | no | `applications_removed_said` | 2 |
| `black_bloc/applications.py:198` | Taken back — staff will not be deciding it. Apply again whenever you want. | ephemeral answer | no | `applications_withdrawn_said` | 2 |
| `black_bloc/applications.py:199` | <@{owner_id}> — next step: {next_step} | ephemeral answer | no | `applications_owner_nudge` | 2 |
| `black_bloc/applications.py:200` | Next step: {next_step} | ephemeral answer | no | `applications_next_step_unowned` | 2 |
| `black_bloc/applications.py:213` | The role runs out {stamp}. | ephemeral answer | no | `applications_expires_extra` | 2 |
| `black_bloc/applications.py:224` | You have not applied for anything here yet. | ephemeral answer | no | `applications_nothing_of_yours` | 2 |
| `black_bloc/applications.py:225` | **{title}** — {status}{extra} | ephemeral answer | no | `applications_your_application` | 2 |
| `black_bloc/applications.py:226` | , waiting on staff | ephemeral answer | no | `applications_status_waiting` | 2 |
| `black_bloc/applications.py:227` | Black Bloc has no application with that number, so there was nothing to show. Pi… | ephemeral answer | no | `applications_nothing_to_show` | 2 |
| `black_bloc/applications.py:232` | A form… | ephemeral answer | no | `applications_pick_a_form` | 2 |
| `black_bloc/applications.py:233` | Pick an application… | ephemeral answer | no | `applications_pick_an_application` | 2 |
| `black_bloc/applications.py:234` | Apply for… | ephemeral answer | no | `applications_apply_for` | 2 |
| `black_bloc/applications.py:235` | Take one back… | ephemeral answer | no | `applications_take_one_back` | 2 |
| `black_bloc/applications.py:237` | **{given}** is not an application number, so nothing was looked up. They look li… | ephemeral answer | no | `applications_not_a_number` | 2 |
| `black_bloc/applications.py:241` | The person took this back themselves, so there is nothing for staff to move. The… | ephemeral answer | no | `applications_withdrawn_is_theirs` | 2 |
| `black_bloc/applications.py:245` | **#{application_id}** is approved again, and they have been told. | ephemeral answer | no | `applications_reinstated_said` | 2 |
| `black_bloc/applications.py:246` | That application is **{status}**, so there was nothing to put back. Only a denie… | ephemeral answer | no | `applications_not_reinstatable` | 2 |
| `black_bloc/cogs/community/applications.py:50` | Take them off the list? | modal title | no | `applications_take_off_modal_title` | 2 |
| `black_bloc/cogs/community/applications.py:51` | One line they will be sent | modal title or field | no | `applications_take_off_modal_label` | 2 |
| `black_bloc/cogs/community/applications.py:52` | Why not? | modal title | no | `applications_deny_modal_title` | 2 |
| `black_bloc/cogs/community/applications.py:53` | One line the applicant will be sent | modal title or field | no | `applications_deny_modal_label` | 2 |
| `black_bloc/cogs/community/applications.py:54` | Yes, take it back | ephemeral answer | no | `applications_withdraw_yes` | 2 |
| `black_bloc/cogs/community/applications.py:56` | Applications only work inside the server, and this did not come from one, so not… | ephemeral answer | no | `applications_not_in_guild` | 2 |
| `black_bloc/cogs/community/applications.py:60` | Deciding an application needs <@&{role_id}>, so nothing was changed. Ask somebod… | ephemeral answer | no | `applications_not_an_approver` | 2 |
| `black_bloc/cogs/community/applications.py:69` | The Apply button for **{name}** is up in <#{channel_id}>. Post it again to move … | ephemeral answer | no | `applications_panel_posted` | 2 |
| `black_bloc/cogs/community/applications.py:72` | Created **{name}**. Put its questions on it with **Questions…** — up to {limit} … | ephemeral answer | no | `applications_form_created` | 2 |
| `black_bloc/cogs/community/applications.py:76` | Saved **{name}**. | ephemeral answer | no | `applications_form_saved` | 2 |
| `black_bloc/cogs/community/applications.py:77` | Deleted **{name}** and its questions. Nobody loses a role they already have, and… | ephemeral answer | no | `applications_form_deleted` | 2 |
| `black_bloc/cogs/community/applications.py:81` | Added **{label}** to **{name}** as question {position}. | ephemeral answer | no | `applications_question_added` | 2 |
| `black_bloc/cogs/community/applications.py:82` | Saved question {position} on **{name}**. | ephemeral answer | no | `applications_question_saved` | 2 |
| `black_bloc/cogs/community/applications.py:83` | Removed question {position} from **{name}**. Answers already sent keep the wordi… | ephemeral answer | no | `applications_question_removed` | 2 |
| `black_bloc/cogs/community/applications.py:87` | **{name}** has nothing in slot {position}, so nothing was changed. The list abov… | ephemeral answer | no | `applications_no_such_question` | 2 |
| `black_bloc/cogs/community/applications.py:95` | **{name}** hands over <@&{role}>, so there is no list to take them off; `/roleme… | ephemeral answer | no | `applications_remove_is_for_lists` | 2 |
| `black_bloc/cogs/community/applications.py:100` | Off. `/apply` still opens, but it says applications are off and offers nobody a … | ephemeral answer | no | `applications_mode_said` | 2 |
| `black_bloc/cogs/community/applications.py:100` | Shadow. Applications are still written down and still show on the dashboard, but… | ephemeral answer | no | `applications_mode_said_2` | 2 |
| `black_bloc/cogs/community/applications.py:100` | On. Members can apply, staff decide on the card, and an approval hands the role … | ephemeral answer | no | `applications_mode_said_3` | 2 |
| `black_bloc/cogs/community/applications.py:116` | No form is open for applications right now. | ephemeral answer | no | `applications_nothing_open_to_apply_for` | 2 |
| `black_bloc/cogs/community/applications.py:118` | Find an application | modal title or field | no | `applications_find_title` | 2 |
| `black_bloc/cogs/community/applications.py:119` | The number on the card, like #12 | modal title or field | no | `applications_find_label` | 2 |
| `black_bloc/cogs/community/applications.py:121` | A new application form | modal title or field | no | `applications_new_form_title` | 2 |
| `black_bloc/cogs/community/applications.py:122` | The words on {name} | modal title or field | no | `applications_words_title` | 2 |
| `black_bloc/cogs/community/applications.py:123` | The numbers on {name} | modal title or field | no | `applications_numbers_title` | 2 |
| `black_bloc/cogs/community/applications.py:124` | Applications — the numbers | modal title or field | no | `applications_settings_numbers_title` | 2 |
| `black_bloc/cogs/community/applications.py:125` | Question {position} on {name} | modal title or field | no | `applications_question_title` | 2 |
| `black_bloc/cogs/community/applications.py:126` | A new question on {name} | modal title or field | no | `applications_add_question_title` | 2 |
| `black_bloc/cogs/community/applications.py:127` | Delete **{name}** and its {questions} question(s)? Nobody loses a role they alre… | ephemeral answer | no | `applications_delete_confirm` | 2 |
| `black_bloc/cogs/community/applications.py:130` | Remove question {position}, **{label}**, from **{name}**? | ephemeral answer | no | `applications_remove_question_confirm` | 2 |
| `black_bloc/cogs/community/applications.py:131` | Questions are asked in the order below. Dragging them into a different order is … | ephemeral answer | no | `applications_reorder_is_on_the_site` | 2 |
| `black_bloc/cogs/community/applications.py:135` | Nobody is on this list yet. | ephemeral answer | no | `applications_roster_empty` | 2 |
| `black_bloc/cogs/community/applications.py:137` | (left the server) | ephemeral answer | no | `applications_roster_gone` | 2 |
| `black_bloc/cogs/community/applications.py:140` | Where does the Apply button go? | ephemeral answer | no | `applications_post_where` | 2 |
| `black_bloc/cogs/community/applications.py:141` | Fill it in | ephemeral answer | no | `applications_fill_it_in` | 2 |
| `black_bloc/cogs/community/applications.py:142` | A question… | ephemeral answer | no | `applications_pick_a_question` | 2 |
| `black_bloc/cogs/community/applications.py:143` | Take somebody off… | ephemeral answer | no | `applications_take_somebody_off` | 2 |
| `black_bloc/cogs/community/applications.py:145` | Mode… | ephemeral answer | no | `applications_settings_mode_pick` | 2 |
| `black_bloc/cogs/community/applications.py:146` | Where cards wait… | ephemeral answer | no | `applications_settings_channel_pick` | 2 |
| `black_bloc/cogs/community/applications.py:147` | Who decides… | ephemeral answer | no | `applications_settings_approver_pick` | 2 |
| `black_bloc/cogs/community/applications.py:148` | Who is pinged… | ephemeral answer | no | `applications_settings_ping_pick` | 2 |
| `black_bloc/cogs/community/applications.py:149` | Role it hands over… | ephemeral answer | no | `applications_edit_role_pick` | 2 |
| `black_bloc/cogs/community/applications.py:150` | Where its cards wait… | ephemeral answer | no | `applications_edit_channel_pick` | 2 |
| `black_bloc/cogs/community/applications.py:151` | Who decides it… | ephemeral answer | no | `applications_edit_approver_pick` | 2 |
| `black_bloc/cogs/community/applications.py:152` | Who is nudged next… | ephemeral answer | no | `applications_edit_owner_pick` | 2 |
| `black_bloc/cogs/community/applications.py:153` | Pick nobody to clear it. | ephemeral answer | no | `applications_cleared_by_empty` | 2 |
| `black_bloc/cogs/community/applications.py:1553` | Short name, like twitch-team | modal field label | no | `applications_modal_short_name_like_twitch_team` | 2 |
| `black_bloc/cogs/community/applications.py:1556` | The heading on the form | modal field label | no | `applications_modal_the_heading_on_the_form` | 2 |
| `black_bloc/cogs/community/applications.py:1559` | The line under the heading | modal field label | no | `applications_modal_the_line_under_the_heading` | 2 |
| `black_bloc/cogs/community/applications.py:2083` | The heading | modal field label | no | `applications_modal_the_heading` | 2 |
| `black_bloc/cogs/community/applications.py:2085` | The line under it | modal field label | no | `applications_modal_the_line_under_it` | 2 |
| `black_bloc/cogs/community/applications.py:2091` | What happens after a yes | modal field label | no | `applications_modal_what_happens_after_a_yes` | 2 |
| `black_bloc/cogs/community/applications.py:2097` | What an approved applicant is DM'd | modal field label | no | `applications_modal_what_an_approved_applicant_is_dm_d` | 2 |
| `black_bloc/cogs/community/applications.py:2141` | Days the role lasts, 0 for forever | modal field label | no | `applications_modal_days_the_role_lasts_0_for_forever` | 2 |
| `black_bloc/cogs/community/applications.py:2144` | Days before somebody may apply again | modal field label | no | `applications_modal_days_before_somebody_may_apply_again` | 2 |
| `black_bloc/cogs/community/applications.py:2380` | What the box is called | modal field label | no | `applications_modal_what_the_box_is_called` | 2 |
| `black_bloc/cogs/community/applications.py:2388` | Grey hint inside the box | modal field label | no | `applications_modal_grey_hint_inside_the_box` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | Mode | ephemeral answer | no | `applications_settings_lines` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | Where cards wait | ephemeral answer | no | `applications_settings_lines_2` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | Who decides | ephemeral answer | no | `applications_settings_lines_3` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | Who is pinged | ephemeral answer | no | `applications_settings_lines_4` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | Days before applying again | ephemeral answer | no | `applications_settings_lines_5` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | DM on a decision | ephemeral answer | no | `applications_settings_lines_6` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | Roster shows people who left | ephemeral answer | no | `applications_settings_lines_7` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | Panel minutes | ephemeral answer | no | `applications_settings_lines_8` | 2 |
| `black_bloc/cogs/community/applications.py:2440` | Members see their own list | ephemeral answer | no | `applications_settings_lines_9` | 2 |
| `black_bloc/cogs/community/applications.py:2621` | Days before applying again | modal field label | no | `applications_modal_days_before_applying_again` | 2 |
| `black_bloc/cogs/community/applications.py:2624` | Minutes this panel stays live | modal field label | no | `applications_modal_minutes_this_panel_stays_live` | 2 |

### honeypot

*52 strings — 0 keyed · 21 unkeyed pass 1 · 26 unkeyed pass 2 · 5 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/cogs/moderation/honeypot.py:86` | 🍯-do-not-post-here | channel / role name | no | `honeypot_trap_name` | 1 |
| `black_bloc/cogs/moderation/honeypot.py:96` | You have been banned from **{guild}** because you posted in a channel that exist… | DM | no | `honeypot_dm_before_ban` | 1 |
| `black_bloc/cogs/moderation/honeypot.py:444` | Ban now | button label | no | `honeypot_button_ban_now` | 1 |
| `black_bloc/cogs/moderation/honeypot.py:858` | How the honeypot panel behaves | card title | no | `honeypot_settings_title` | 1 |
| `black_bloc/cogs/moderation/honeypot.py:859` | Which trap channel to forget | card title | no | `honeypot_forget_title` | 1 |
| `black_bloc/cogs/moderation/honeypot.py:860` | Forgetting a channel only stops Black Bloc treating it as a trap — the channel i… | card description | no | `honeypot_forget_intro` | 1 |
| `black_bloc/honeypot.py:10` | The trap that catches spam bots | card title | no | `honeypot_panel_title` | 1 |
| `black_bloc/honeypot.py:11` | This panel has gone quiet — run /honeypot again | card description | no | `honeypot_panel_timeout_footer` | 1 |
| `black_bloc/honeypot.py:16` | off — nothing posted in the trap is read at all | card field | no | `honeypot_mode_labels` | 1 |
| `black_bloc/honeypot.py:16` | shadow — it deletes the post and logs it, and bans nobody | card field | no | `honeypot_mode_labels_2` | 1 |
| `black_bloc/honeypot.py:16` | on — it deletes the post and bans the account that made it | card field | no | `honeypot_mode_labels_3` | 1 |
| `black_bloc/honeypot.py:22` | What the trap does… | select placeholder | no | `honeypot_mode_placeholder` | 1 |
| `black_bloc/honeypot.py:23` | Roles the trap ignores… | select placeholder | no | `honeypot_exempt_placeholder` | 1 |
| `black_bloc/honeypot.py:24` | Forget a trap channel… | select placeholder | no | `honeypot_forget_placeholder` | 1 |
| `black_bloc/honeypot.py:71` | Numbers | card title | no | `honeypot_numbers_title` | 1 |
| `black_bloc/honeypot.py:72` | Minutes this panel stays live | card field | no | `honeypot_panel_minutes_label` | 1 |
| `black_bloc/honeypot.py:73` | Days of their messages a ban deletes | card field | no | `honeypot_purge_days_label` | 1 |
| `black_bloc/honeypot.py:74` | The trap channel | card title | no | `honeypot_trap_name_title` | 1 |
| `black_bloc/honeypot.py:75` | What the trap channel is called | card field | no | `honeypot_trap_name_label` | 1 |
| `black_bloc/honeypot.py:97` | ⚠️ **recorded but gone** — {ids}. Discord no longer has {them}; **Forget…** take… | channel post | no | `honeypot_dead_trap_line` | 1 |
| `black_bloc/honeypot.py:105` | ⚠️ **Test mode** — the trap is kept inside the test channel's category and nobod… | channel post | no | `honeypot_test_mode_line` | 1 |
| `black_bloc/cogs/moderation/honeypot.py:89` | This channel is a trap for bots. **Do not post here** — anything posted is treat… | ephemeral answer | no | `honeypot_notice` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:101` | That account was already banned for this post, so nothing changed. `/honeypot` s… | ephemeral answer | no | `honeypot_already_banned` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:105` | Black Bloc has no record of that trap post any more, so nobody was banned. It ma… | ephemeral answer | no | `honeypot_no_such_hit` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:109` | Black Bloc is in test mode, so it refused to ban anyone and logged what it would… | ephemeral answer | no | `honeypot_ban_in_test_mode` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:114` | Discord refused the ban, so the account is still here. Black Bloc needs the Ban … | ephemeral answer | no | `honeypot_ban_refused` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:119` | Discord refused to create the channel, so no trap was made. Black Bloc needs the… | ephemeral answer | no | `honeypot_cannot_create` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:123` | Black Bloc is in test mode and cannot see its test channel, so no trap was made.… | ephemeral answer | no | `honeypot_no_test_channel_trap` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:127` | The pinned notice was not posted, because test mode keeps Black Bloc out of ever… | ephemeral answer | no | `honeypot_notice_not_posted` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:131` | Black Bloc cannot work out who counts as staff, so the trap was left as it was. … | ephemeral answer | no | `honeypot_no_staff_roles` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:137` | ⚠️ **No staff roles resolve.** Only people with Manage Server are exempt, so a m… | ephemeral answer | no | `honeypot_no_staff_warning` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:141` | This server already has a trap channel — {where} — so a second one was not made.… | ephemeral answer | no | `honeypot_already_a_trap` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:146` | **{channel_id}** is not one of Black Bloc's trap channels, so nothing was forgot… | ephemeral answer | no | `honeypot_not_a_trap` | 2 |
| `black_bloc/cogs/moderation/honeypot.py:150` | Black Bloc has forgotten **{channel_id}** — it is no longer a trap, and posts th… | ephemeral answer | no | `honeypot_forgotten` | 2 |
| `black_bloc/honeypot.py:26` | #{name} | ephemeral answer | no | `honeypot_trap_option` | 2 |
| `black_bloc/honeypot.py:27` | a channel Discord no longer has ({ident}) | ephemeral answer | no | `honeypot_gone_channel` | 2 |
| `black_bloc/honeypot.py:77` | The trap is now **{mode}**. | ephemeral answer | no | `honeypot_mode_set` | 2 |
| `black_bloc/honeypot.py:78` | Nothing was given, so nothing changed. | ephemeral answer | no | `honeypot_settings_nothing` | 2 |
| `black_bloc/honeypot.py:79` | The panel stays live {minutes} minute(s), and a ban deletes {days} day(s) of the… | ephemeral answer | no | `honeypot_settings_done` | 2 |
| `black_bloc/honeypot.py:82` | **{given}** is not a whole number, so nothing at all was changed — not even the … | ephemeral answer | no | `honeypot_not_a_number` | 2 |
| `black_bloc/honeypot.py:86` | Those are already the roles the trap ignores, so nothing changed and nothing was… | ephemeral answer | no | `honeypot_exempt_nothing_changed` | 2 |
| `black_bloc/honeypot.py:89` | The trap ignores nobody but staff now. | ephemeral answer | no | `honeypot_exempt_now_nobody` | 2 |
| `black_bloc/honeypot.py:90` | now ignores {roles} | ephemeral answer | no | `honeypot_exempt_added` | 2 |
| `black_bloc/honeypot.py:91` | stops ignoring {roles} | ephemeral answer | no | `honeypot_exempt_removed` | 2 |
| `black_bloc/honeypot.py:92` | ⚠️ **{count} roles are exempt**, which is more than one Discord picker can edit … | ephemeral answer | no | `honeypot_exempt_too_many` | 2 |
| `black_bloc/honeypot.py:101` | The trap is armed, but there is no trap channel yet for anybody to fall into — p… | ephemeral answer | no | `honeypot_armed_with_no_trap` | 2 |
| `black_bloc/honeypot.py:109` | While the mode is **off** this command disappears from Discord within about a mi… | ephemeral answer | no | `honeypot_mode_is_off_way_back` | 2 |

### automod

*73 strings — 0 keyed · 22 unkeyed pass 1 · 48 unkeyed pass 2 · 3 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/automod.py:95` | **{given}** is not something an automod rule has, so nothing was changed. A rule… | card field | no | `automod_unknown_field` | 1 |
| `black_bloc/automod.py:460` | What automod is watching | card title | no | `automod_panel_title` | 1 |
| `black_bloc/automod.py:461` | This panel has gone quiet — run /automod again | card description | no | `automod_panel_timeout_footer` | 1 |
| `black_bloc/automod.py:465` | off — nothing is read and nothing is counted | card field | no | `automod_mode_labels` | 1 |
| `black_bloc/automod.py:465` | shadow — it logs what it would have done, and does none of it | card field | no | `automod_mode_labels_2` | 1 |
| `black_bloc/automod.py:465` | on — it deletes, warns and times people out for real | card field | no | `automod_mode_labels_3` | 1 |
| `black_bloc/automod.py:473` | role — {name} | card field | no | `automod_exempt_role_label` | 1 |
| `black_bloc/automod.py:474` | channel — #{name} | card field | no | `automod_exempt_channel_label` | 1 |
| `black_bloc/automod.py:478` | Seconds counted over (0 = one message) | card field | no | `automod_window_label` | 1 |
| `black_bloc/automod.py:479` | Timeout in seconds (0 = no timeout) | card field | no | `automod_timeout_label` | 1 |
| `black_bloc/automod.py:480` | Percent capitals, 1–100 | card field | no | `automod_caps_threshold_label` | 1 |
| `black_bloc/automod.py:481` | How many {plural} it allows | card field | no | `automod_threshold_label` | 1 |
| `black_bloc/cogs/moderation/automod.py:163` | delete what they posted | card field | no | `automod_action_labels` | 1 |
| `black_bloc/cogs/moderation/automod.py:163` | warn them | card field | no | `automod_action_labels_2` | 1 |
| `black_bloc/cogs/moderation/automod.py:163` | time them out | card field | no | `automod_action_labels_3` | 1 |
| `black_bloc/cogs/moderation/automod.py:176` | What automod never reads | card title | no | `automod_exempt_title` | 1 |
| `black_bloc/cogs/moderation/automod.py:177` | Staff are always exempt. These are the roles and channels automod skips on top o… | card description | no | `automod_exempt_intro` | 1 |
| `black_bloc/cogs/moderation/automod.py:180` | **never read either** — {channels}, because they are the honeypot's own traps. T… | channel post | no | `automod_honeypot_line` | 1 |
| `black_bloc/cogs/moderation/automod.py:186` | What automod does… | select placeholder | no | `automod_mode_placeholder` | 1 |
| `black_bloc/cogs/moderation/automod.py:189` | Watch it again… | select placeholder | no | `automod_remove_placeholder` | 1 |
| `black_bloc/cogs/moderation/automod.py:190` | How the automod panel behaves | card title | no | `automod_settings_title` | 1 |
| `black_bloc/cogs/moderation/automod.py:529` | Apply now | button label | no | `automod_button_apply_now` | 1 |
| `black_bloc/automod.py:65` | blocked word | ephemeral answer | no | `automod_rule_nouns` | 2 |
| `black_bloc/automod.py:65` | blocked words | ephemeral answer | no | `automod_rule_nouns_2` | 2 |
| `black_bloc/automod.py:74` | how many people or roles one member may mention in the window | ephemeral answer | no | `automod_rule_help` | 2 |
| `black_bloc/automod.py:74` | how many messages one member may post in the window | ephemeral answer | no | `automod_rule_help_2` | 2 |
| `black_bloc/automod.py:74` | how many links one member may post in the window | ephemeral answer | no | `automod_rule_help_3` | 2 |
| `black_bloc/automod.py:74` | how many Discord invites one member may post in the window | ephemeral answer | no | `automod_rule_help_4` | 2 |
| `black_bloc/automod.py:74` | how many files one member may post in the window | ephemeral answer | no | `automod_rule_help_5` | 2 |
| `black_bloc/automod.py:74` | the percentage of capital letters one message may be | ephemeral answer | no | `automod_rule_help_6` | 2 |
| `black_bloc/automod.py:74` | words that are not allowed; the bad_words rule's own word list holds them | ephemeral answer | no | `automod_rule_help_7` | 2 |
| `black_bloc/automod.py:91` | **{given}** is not one of Black Bloc's automod rules, so nothing was changed. Th… | ephemeral answer | no | `automod_unknown_rule` | 2 |
| `black_bloc/automod.py:99` | **{given}** is not an automod punishment, so nothing was changed. The punishment… | ephemeral answer | no | `automod_bad_actions` | 2 |
| `black_bloc/automod.py:475` | a role Discord no longer has ({ident}) | ephemeral answer | no | `automod_gone_role` | 2 |
| `black_bloc/automod.py:476` | a channel Discord no longer has ({ident}) | ephemeral answer | no | `automod_gone_channel` | 2 |
| `black_bloc/automod.py:482` | How many before it acts | ephemeral answer | no | `automod_threshold_fallback` | 2 |
| `black_bloc/cogs/moderation/automod.py:118` | Black Bloc cannot work out who counts as staff, so automod was left as it was. N… | ephemeral answer | no | `automod_no_staff_roles` | 2 |
| `black_bloc/cogs/moderation/automod.py:124` | ⚠️ **No staff roles resolve.** Only people with Manage Server are exempt, so a m… | ephemeral answer | no | `automod_no_staff_warning` | 2 |
| `black_bloc/cogs/moderation/automod.py:128` | Black Bloc has no record of that automod verdict any more, so nothing was applie… | ephemeral answer | no | `automod_no_such_verdict` | 2 |
| `black_bloc/cogs/moderation/automod.py:132` | That verdict has already been applied, so nothing changed. Open case #{case_id} … | ephemeral answer | no | `automod_already_applied` | 2 |
| `black_bloc/cogs/moderation/automod.py:136` | That member has left the server, so there is nothing to apply. | ephemeral answer | no | `automod_member_gone` | 2 |
| `black_bloc/cogs/moderation/automod.py:137` | Discord refused the timeout, so nothing was done to them. Black Bloc needs the M… | ephemeral answer | no | `automod_timeout_refused` | 2 |
| `black_bloc/cogs/moderation/automod.py:142` | **{given}** is not one of Black Bloc's automod rules, so nothing was changed. `/… | ephemeral answer | no | `automod_unknown_rule_choice` | 2 |
| `black_bloc/cogs/moderation/automod.py:146` | `staff_channel_id` is still the test channel, so everybody who can see it would … | ephemeral answer | no | `automod_staff_is_the_test_channel` | 2 |
| `black_bloc/cogs/moderation/automod.py:152` | Automod is now **{mode}**. | ephemeral answer | no | `automod_mode_set` | 2 |
| `black_bloc/cogs/moderation/automod.py:153` | <{mark}{ident}> was already {state}, so nothing changed. | ephemeral answer | no | `automod_already` | 2 |
| `black_bloc/cogs/moderation/automod.py:154` | <{mark}{ident}> is {state} | ephemeral answer | no | `automod_changed` | 2 |
| `black_bloc/cogs/moderation/automod.py:155` | exempt from automod now. | ephemeral answer | no | `automod_exempt_now` | 2 |
| `black_bloc/cogs/moderation/automod.py:156` | watched by automod again. | ephemeral answer | no | `automod_watched_again` | 2 |
| `black_bloc/cogs/moderation/automod.py:157` | Nothing was given, so nothing changed. | ephemeral answer | no | `automod_settings_nothing` | 2 |
| `black_bloc/cogs/moderation/automod.py:158` | The panel stays live {minutes} minute(s), and arming automod {what}. | ephemeral answer | no | `automod_settings_done` | 2 |
| `black_bloc/cogs/moderation/automod.py:159` | **how it counts** — one message at a time; nothing carries over from the message… | ephemeral answer | no | `automod_one_message_at_a_time` | 2 |
| `black_bloc/cogs/moderation/automod.py:162` | **how it counts** — everything one member does in {seconds} seconds, added up. | ephemeral answer | no | `automod_over_a_window` | 2 |
| `black_bloc/cogs/moderation/automod.py:168` | What it does… | ephemeral answer | no | `automod_what_it_does` | 2 |
| `black_bloc/cogs/moderation/automod.py:169` | A whole number | modal title or field | no | `automod_number_label` | 2 |
| `black_bloc/cogs/moderation/automod.py:172` | ⚠️ **Every rule is off**, so automod reads what people post and can never act on… | ephemeral answer | no | `automod_every_rule_off` | 2 |
| `black_bloc/cogs/moderation/automod.py:184` | Nothing extra is exempt yet. | ephemeral answer | no | `automod_nothing_exempt` | 2 |
| `black_bloc/cogs/moderation/automod.py:185` | A rule… | ephemeral answer | no | `automod_pick_a_rule` | 2 |
| `black_bloc/cogs/moderation/automod.py:187` | Stop watching a role… | ephemeral answer | no | `automod_add_role` | 2 |
| `black_bloc/cogs/moderation/automod.py:188` | Stop watching a channel… | ephemeral answer | no | `automod_add_channel` | 2 |
| `black_bloc/cogs/moderation/automod.py:196` | Turning automod **on** starts deleting messages, warning people and timing them … | ephemeral answer | no | `automod_arm_question` | 2 |
| `black_bloc/cogs/moderation/automod.py:200` | Change the numbers | modal title or field | no | `automod_numbers_title` | 2 |
| `black_bloc/cogs/moderation/automod.py:201` | Words that are not allowed | modal title or field | no | `automod_words_title` | 2 |
| `black_bloc/cogs/moderation/automod.py:202` | One per line, or separated by commas | modal title or field | no | `automod_words_label` | 2 |
| `black_bloc/cogs/moderation/automod.py:203` | This word list is longer than a Discord box holds, so it can only be edited on t… | ephemeral answer | no | `automod_words_too_long` | 2 |
| `black_bloc/cogs/moderation/automod.py:207` | Numbers | modal title or field | no | `automod_panel_numbers_title` | 2 |
| `black_bloc/cogs/moderation/automod.py:208` | Minutes this panel stays live | modal title or field | no | `automod_panel_minutes_label` | 2 |
| `black_bloc/cogs/moderation/automod.py:209` | **{given}** is not a whole number, so nothing was changed. {label} takes a numbe… | ephemeral answer | no | `automod_not_a_number` | 2 |
| `black_bloc/cogs/moderation/automod.py:213` | asks a second time first | ephemeral answer | no | `automod_asks_twice` | 2 |
| `black_bloc/cogs/moderation/automod.py:214` | takes one press | ephemeral answer | no | `automod_one_press` | 2 |

### mod commands

*82 strings — 0 keyed · 23 unkeyed pass 1 · 45 unkeyed pass 2 · 14 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/cogs/moderation/modcmds.py:905` | Deleted message(s) — case **#**. | channel post / DM | no | `mod_line_deleted_message_s_case` | 1 |
| `black_bloc/modcases.py:49` | timed out | DM | no | `mod_dm_actions` | 1 |
| `black_bloc/modcases.py:49` | let out of a timeout | DM | no | `mod_dm_actions_2` | 1 |
| `black_bloc/modcases.py:49` | warned by the automatic filter | DM | no | `mod_dm_actions_3` | 1 |
| `black_bloc/modcases.py:49` | timed out by the automatic filter | DM | no | `mod_dm_actions_4` | 1 |
| `black_bloc/modcases.py:60` | A case against you in **{guild_name}** has been **cancelled** by staff. It stays… | DM | no | `mod_dm_sentences` | 1 |
| `black_bloc/modcases.py:60` | A case against you in **{guild_name}** has been **put back** by staff after bein… | DM | no | `mod_dm_sentences_2` | 1 |
| `black_bloc/modcases.py:191` | Member | card field name | no | `mod_card_member` | 1 |
| `black_bloc/modcases.py:194` | Channel | card field name | no | `mod_card_channel` | 1 |
| `black_bloc/modcases.py:197` | Moderator | card field name | no | `mod_card_moderator` | 1 |
| `black_bloc/modcases.py:200` | For | card field name | no | `mod_card_for` | 1 |
| `black_bloc/modcases.py:202` | What tripped it | card field name | no | `mod_card_what_tripped_it` | 1 |
| `black_bloc/modcases.py:204` | Reason | card field name | no | `mod_card_reason` | 1 |
| `black_bloc/modcases.py:206` | Done | card field name | no | `mod_card_done` | 1 |
| `black_bloc/modcases.py:209` | Refused | card field name | no | `mod_card_refused` | 1 |
| `black_bloc/modcases.py:215` | Not done | card field name | no | `mod_card_not_done` | 1 |
| `black_bloc/modcases.py:220` | Note | card field name | no | `mod_card_note` | 1 |
| `black_bloc/modcases.py:222` | Voided | card field name | no | `mod_card_voided` | 1 |
| `black_bloc/modcases.py:524` | What Black Bloc has done | card title | no | `mod_panel_title` | 1 |
| `black_bloc/modcases.py:525` | This panel has gone quiet — run /mod again | card description | no | `mod_panel_timeout_footer` | 1 |
| `black_bloc/modcases.py:533` | Everyone's cases | card field | no | `mod_everyone_label` | 1 |
| `black_bloc/modcases.py:534` | Punishing somebody is still `/warn`, `/timeout`, `/untimeout`, `/kick`, `/ban`, … | card description | no | `mod_bare_actions_footer` | 1 |
| `black_bloc/modcases.py:543` | An empty note is a note nobody can read later, so nothing was changed. Say what … | card description | no | `mod_nothing_in_the_note` | 1 |
| `black_bloc/api/tools/mod.py:65` | time out | ephemeral answer | no | `mod_wording` | 2 |
| `black_bloc/api/tools/mod.py:65` | lift anyone's timeout | ephemeral answer | no | `mod_wording_2` | 2 |
| `black_bloc/api/tools/mod.py:65` | lift anyone's ban | ephemeral answer | no | `mod_wording_3` | 2 |
| `black_bloc/api/tools/mod.py:72` | **{user_id}** is not a member of this server, so nothing was done. Pick somebody… | ephemeral answer | no | `mod_not_a_member` | 2 |
| `black_bloc/api/tools/mod.py:84` | no reason given | ephemeral answer | no | `mod_no_reason` | 2 |
| `black_bloc/api/tools/mod.py:85` | **{given}** is not a number of days of messages to delete, so nobody was banned.… | ephemeral answer | no | `mod_bad_purge_days` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:104` | Discord itself refuses a timeout longer than 28 days, so nobody was timed out. P… | ephemeral answer | no | `mod_timeout_too_long` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:108` | Discord refused the timeout, so nothing was done to them. Black Bloc needs the M… | ephemeral answer | no | `mod_refused` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:108` | Discord refused to lift the timeout, so it is still running. Black Bloc needs th… | ephemeral answer | no | `mod_refused_2` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:108` | Discord refused the kick, so they are still here. Black Bloc needs the Kick Memb… | ephemeral answer | no | `mod_refused_3` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:108` | Discord refused the ban, so they are still here. Black Bloc needs the Ban Member… | ephemeral answer | no | `mod_refused_4` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:108` | Discord refused the unban, so they are still banned. Black Bloc needs the Ban Me… | ephemeral answer | no | `mod_refused_5` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:108` | Discord refused to delete those messages, so they are still there. Black Bloc ne… | ephemeral answer | no | `mod_refused_6` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:139` | **{given}** is not a member id, so nobody was unbanned. Right-click the account … | ephemeral answer | no | `mod_not_an_id` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:143` | **{user_id}** is not on this server's ban list, so there was nothing to lift. `/… | ephemeral answer | no | `mod_not_banned` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:151` | That is warning **{count}** — at or over the threshold of **{threshold}**, which… | ephemeral answer | no | `mod_warn_threshold_reached` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:155` | this server | ephemeral answer | no | `mod_this_server` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:156` | This case belongs to a channel rather than a member, so there is nobody to tell … | ephemeral answer | no | `mod_nobody_to_tell` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:159` | Why this case was opened | modal title or field | no | `mod_reason_title` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:160` | The reason — it is on the case card | modal title or field | no | `mod_reason_label` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:161` | A note on this case | modal title or field | no | `mod_note_title` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:162` | What the next moderator should know | modal title or field | no | `mod_note_label` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:163` | Void this case | modal title or field | no | `mod_void_title` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:164` | Why it was wrong — the member is told this | modal title or field | no | `mod_void_label` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:165` | Open a case by number | modal title or field | no | `mod_jump_title` | 2 |
| `black_bloc/cogs/moderation/modcmds.py:166` | The case number | modal title or field | no | `mod_jump_label` | 2 |
| `black_bloc/modcases.py:71` | ⏎ ⏎ Applied by <@{moderator_id}> at <t:{when}:f>. | ephemeral answer | no | `mod_applied_by` | 2 |
| `black_bloc/modcases.py:72` | Someone just applied this case, so nothing was done twice. Open case #{case_id} … | ephemeral answer | no | `mod_already_applied_by_somebody` | 2 |
| `black_bloc/modcases.py:77` | **{given}** is not a length Black Bloc can read, so nothing was done. Write it a… | ephemeral answer | no | `mod_bad_duration` | 2 |
| `black_bloc/modcases.py:82` | Black Bloc is in **test mode**, so it refused to {action} anyone and logged what… | ephemeral answer | no | `mod_test_mode_refusal` | 2 |
| `black_bloc/modcases.py:87` | Black Bloc has no case **#{case_id}**, so there is nothing to show. `/mod` lists… | ephemeral answer | no | `mod_no_such_case` | 2 |
| `black_bloc/modcases.py:91` | Black Bloc has no cases for {who} yet. | ephemeral answer | no | `mod_no_cases` | 2 |
| `black_bloc/modcases.py:527` | Cancelling a case does not undo the punishment: a cancelled ban is still a ban a… | ephemeral answer | no | `mod_void_undoes_nothing` | 2 |
| `black_bloc/modcases.py:531` | Whose cases? | ephemeral answer | no | `mod_whose_cases` | 2 |
| `black_bloc/modcases.py:532` | A case… | ephemeral answer | no | `mod_pick_a_case` | 2 |
| `black_bloc/modcases.py:538` | **{total}** case(s) for {who} — page {page} of {pages} | ephemeral answer | no | `mod_cases_header` | 2 |
| `black_bloc/modcases.py:539` | A case with no reason is a case nobody can read later, so nothing was changed. S… | ephemeral answer | no | `mod_nothing_to_say` | 2 |
| `black_bloc/modcases.py:547` | Cancelling a case with no reason leaves the next moderator guessing, so nothing … | ephemeral answer | no | `mod_void_needs_a_reason` | 2 |
| `black_bloc/modcases.py:551` | Somebody voided this case a moment ago, so nothing was done twice. | ephemeral answer | no | `mod_already_voided` | 2 |
| `black_bloc/modcases.py:552` | Somebody restored this case a moment ago, so nothing was done twice. | ephemeral answer | no | `mod_already_restored` | 2 |
| `black_bloc/modcases.py:553` | **{given}** is not a case number, so nothing was opened. A case number is the di… | ephemeral answer | no | `mod_not_a_case_number` | 2 |
| `black_bloc/modcases.py:557` | Case **#{case_id}**'s reason now reads what you wrote. | ephemeral answer | no | `mod_reason_saved` | 2 |
| `black_bloc/modcases.py:558` | Case **#{case_id}** carries your note. | ephemeral answer | no | `mod_note_saved` | 2 |
| `black_bloc/modcases.py:559` | Case **#{case_id}** is marked cancelled. It is still on the record. | ephemeral answer | no | `mod_voided_said` | 2 |
| `black_bloc/modcases.py:560` | Case **#{case_id}** is back on the record as it was. | ephemeral answer | no | `mod_restored_said` | 2 |

### chat

*568 strings — 0 keyed · 39 unkeyed pass 1 · 198 unkeyed pass 2 · 331 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/api/tools/chat.py:58` | Black Bloc has no chat line **#{line_id}** any more, so nothing was done. Somebo… | channel post | no | `chat_no_such_line` | 1 |
| `black_bloc/api/tools/chat.py:66` | **{name}** is one of Black Bloc's own intents and its name is what the bot looks… | channel / role name | no | `chat_built_in_keeps_its_name` | 1 |
| `black_bloc/api/tools/chat.py:74` | There is nothing to try yet, so nothing was worked out. Type the sentence somebo… | channel post | no | `chat_try_needs_text` | 1 |
| `black_bloc/chat.py:792` | An intent's name is lowercase letters, numbers and underscores — `cookout_hours`… | channel / role name | no | `chat_name_not_a_name` | 1 |
| `black_bloc/chat.py:816` | A line needs some words in it, so nothing was saved. | channel post | no | `chat_no_text` | 1 |
| `black_bloc/chat_data.py:57` | {who} — holds {roles}; staff: {staff} | card description | no | `chat_member_note` | 1 |
| `black_bloc/chat_llm.py:77` | timed out | card field | no | `chat_staff_words` | 1 |
| `black_bloc/chat_llm.py:110` | (Who they pointed at, from the server itself — this is the truth about them, so … | channel post | no | `chat_people_opener` | 1 |
| `black_bloc/chat_memory.py:246` | (What you remember about this person from earlier chats — preferences only; neve… | channel post | no | `chat_memory_opener` | 1 |
| `black_bloc/chat_panel.py:50` | How Black Bloc answers | card title | no | `chat_panel_title` | 1 |
| `black_bloc/chat_panel.py:51` | This panel has gone quiet — run /chat again | card description | no | `chat_panel_timeout_footer` | 1 |
| `black_bloc/chat_panel.py:79` | What Black Bloc remembers about a person is `/memory`'s, not this panel's — the … | channel post | no | `chat_memory_line` | 1 |
| `black_bloc/chat_panel.py:87` | That arrived with no voice in it, so nothing was changed. Pick the cookout voice… | channel / role name | no | `chat_mode_needs_a_name` | 1 |
| `black_bloc/chat_panel.py:115` | There is no note **{id}** in this server any more, so nothing was changed. Press… | card description | no | `chat_no_such_note` | 1 |
| `black_bloc/cogs/content/chat.py:94` | {who} asked for a mod in {where}. {link} | card description | no | `chat_staff_note` | 1 |
| `black_bloc/cogs/content/chat.py:98` | `/settings` ▸ **A setting group…** ▸ chat changes any of these, and the Chat pag… | card description | no | `chat_settings_footer` | 1 |
| `black_bloc/cogs/content/chat.py:138` | · **{name}** ({label}) — {state} | channel post | no | `chat_mood_line` | 1 |
| `black_bloc/cogs/content/chat.py:156` | The voice Black Bloc answers in | card title | no | `chat_personality_title` | 1 |
| `black_bloc/cogs/content/chat.py:157` | What Black Bloc knows about this server | card title | no | `chat_knowledge_title` | 1 |
| `black_bloc/cogs/content/chat.py:158` | Note {id} | card title | no | `chat_note_title` | 1 |
| `black_bloc/cogs/content/chat.py:159` | How chat is set up | card title | no | `chat_settings_title` | 1 |
| `black_bloc/cogs/content/chat.py:161` | The voice… | select placeholder | no | `chat_voice_placeholder` | 1 |
| `black_bloc/cogs/content/chat.py:162` | Turn a mood off… | select placeholder | no | `chat_mood_off_placeholder` | 1 |
| `black_bloc/cogs/content/chat.py:163` | Turn a mood on… | select placeholder | no | `chat_mood_on_placeholder` | 1 |
| `black_bloc/cogs/content/chat.py:164` | A note… | select placeholder | no | `chat_note_placeholder` | 1 |
| `black_bloc/cogs/content/chat_memory.py:57` | What Black Bloc remembers about you | card title | no | `chat_panel_title_2` | 1 |
| `black_bloc/cogs/content/chat_memory.py:58` | This panel has gone quiet — run /memory again | card description | no | `chat_panel_timeout_footer_2` | 1 |
| `black_bloc/cogs/content/chat_memory.py:59` | What Black Bloc remembers about you | card description | no | `chat_command_description` | 1 |
| `black_bloc/cogs/content/chat_memory.py:81` | **#{number}** It calls you **{text}**. | channel post | no | `chat_call_me_line` | 1 |
| `black_bloc/cogs/content/chat_memory.py:82` | **#{number}** {text} | channel post | no | `chat_note_line` | 1 |
| `black_bloc/cogs/content/chat_memory.py:83` | **#{number}** *still open:* {text} | channel post | no | `chat_thread_line` | 1 |
| `black_bloc/cogs/content/chat_memory.py:84` | *(learned in a DM — never used in a channel)* | DM | no | `chat_dm_mark` | 1 |
| `black_bloc/cogs/content/chat_memory.py:102` | Say a few words from the line you want dropped, the way the panel prints them, a… | card field | no | `chat_forget_this_needs_words` | 1 |
| `black_bloc/cogs/content/chat_memory.py:111` | Forget one of these… | channel post | no | `chat_pick_a_line` | 1 |
| `black_bloc/cogs/content/chat_memory.py:130` | what it calls you | card field | no | `chat_fact_words` | 1 |
| `black_bloc/cogs/content/chat_memory.py:130` | still open | card field | no | `chat_fact_words_2` | 1 |
| `black_bloc/knowledge.py:33` | Who has the {role} role | card title | no | `chat_role_holders_title` | 1 |
| `black_bloc/knowledge.py:34` | {role} — {count} {word}: {names}. | channel post | no | `chat_role_holders_body` | 1 |
| `black_bloc/knowledge.py:45` | (What the server's notes say, for your answer — quote it rather than inventing: | channel post | no | `chat_grounding_opener` | 1 |
| `black_bloc/api/tools/chat.py:54` | Black Bloc has no chat intent **#{intent_id}** any more, so nothing was done. Th… | ephemeral answer | no | `chat_no_such_intent` | 2 |
| `black_bloc/api/tools/chat.py:62` | **{name}** is one of Black Bloc's own intents, so it cannot be deleted — turn it… | ephemeral answer | no | `chat_built_in_stays` | 2 |
| `black_bloc/api/tools/chat.py:70` | This server already has an intent called **{name}**, so nothing was saved. Pick … | ephemeral answer | no | `chat_name_taken` | 2 |
| `black_bloc/api/tools/chat.py:78` | **{name}** is in. It will answer as soon as it has a line to say. | ephemeral answer | no | `chat_intent_made` | 2 |
| `black_bloc/api/tools/chat.py:79` | **{name}** is saved. | ephemeral answer | no | `chat_intent_saved` | 2 |
| `black_bloc/api/tools/chat.py:80` | **{name}** is gone. Nothing answers to those phrases any more. | ephemeral answer | no | `chat_intent_gone` | 2 |
| `black_bloc/api/tools/chat.py:81` | That line is in — **{name}** may say it from now on. | ephemeral answer | no | `chat_line_added` | 2 |
| `black_bloc/api/tools/chat.py:82` | That line is saved. | ephemeral answer | no | `chat_line_saved` | 2 |
| `black_bloc/api/tools/chat.py:83` | That line is gone. | ephemeral answer | no | `chat_line_gone` | 2 |
| `black_bloc/api/tools/chat.py:85` | Black Bloc has no note **#{section_id}** any more, so nothing was done. Somebody… | ephemeral answer | no | `chat_no_such_section` | 2 |
| `black_bloc/api/tools/chat.py:89` | **{title}** is one of the notes Black Bloc writes for itself out of the server —… | ephemeral answer | no | `chat_server_row_locked` | 2 |
| `black_bloc/api/tools/chat.py:95` | **{title}** is in. Black Bloc quotes it when somebody asks something it matches. | ephemeral answer | no | `chat_section_made` | 2 |
| `black_bloc/api/tools/chat.py:96` | **{title}** is saved. | ephemeral answer | no | `chat_section_saved` | 2 |
| `black_bloc/api/tools/chat.py:97` | **{title}** is gone. Black Bloc will not quote it again. | ephemeral answer | no | `chat_section_gone` | 2 |
| `black_bloc/api/tools/chat.py:99` | written here by staff | ephemeral answer | no | `chat_staff_wrote_it` | 2 |
| `black_bloc/api/tools/chat.py:100` | written by Black Bloc from the server itself, every day | ephemeral answer | no | `chat_server_wrote_it` | 2 |
| `black_bloc/api/tools/chat.py:102` | Black Bloc talks in the cookout voice from now on. | ephemeral answer | no | `chat_mode_set_cookout` | 2 |
| `black_bloc/api/tools/chat.py:103` | Black Bloc picks a voice out of the pool for each conversation from now on, and … | ephemeral answer | no | `chat_mode_set_pool` | 2 |
| `black_bloc/api/tools/chat.py:107` | Black Bloc is **{label}** with everybody from now on. | ephemeral answer | no | `chat_mode_set_trope` | 2 |
| `black_bloc/api/tools/chat.py:108` | **{label}** is back in the pool. | ephemeral answer | no | `chat_trope_on` | 2 |
| `black_bloc/api/tools/chat.py:109` | **{label}** is out of the pool. Black Bloc will not pick it again. | ephemeral answer | no | `chat_trope_off` | 2 |
| `black_bloc/api/tools/chat.py:111` | Everybody gets the cookout voice — warm, playful, the one the rest of the site i… | ephemeral answer | no | `chat_cookout_word` | 2 |
| `black_bloc/api/tools/chat.py:114` | Each conversation gets one of the {count} voices left on, and it moves a step at… | ephemeral answer | no | `chat_pool_word` | 2 |
| `black_bloc/api/tools/chat.py:118` | Black Bloc is **{label}** with everybody, and it does not drift. | ephemeral answer | no | `chat_trope_word` | 2 |
| `black_bloc/api/tools/chat.py:130` | Live. Grounded answers and longer questions go here. | ephemeral answer | no | `chat_tier_live` | 2 |
| `black_bloc/api/tools/chat.py:130` | Live. Greetings and one-liners that slipped past the phrases go here. | ephemeral answer | no | `chat_tier_live_2` | 2 |
| `black_bloc/api/tools/chat.py:134` | Not in use: `chat_llm_mode` is off, so Black Bloc answers from the phrases on th… | ephemeral answer | no | `chat_tier_mode_off` | 2 |
| `black_bloc/api/tools/chat.py:138` | Black Bloc has not been given a **{key}** yet, so this tier does not exist and t… | ephemeral answer | no | `chat_tier_no_key` | 2 |
| `black_bloc/api/tools/chat.py:142` | Closed until the 1st: this month's {cap} is spent. Black Bloc is answering from … | ephemeral answer | no | `chat_tier_capped` | 2 |
| `black_bloc/api/tools/chat.py:146` | {spent} of the {cap} Black Bloc may spend this month, so {left} is left. | ephemeral answer | no | `chat_month_word` | 2 |
| `black_bloc/api/tools/chat.py:147` | {spent} of the {cap} Black Bloc may spend this month, so the two model tiers are… | ephemeral answer | no | `chat_month_capped_word` | 2 |
| `black_bloc/api/tools/chat.py:151` | {turns} answers came from a model today, out of the {limit} a day Black Bloc giv… | ephemeral answer | no | `chat_today_word` | 2 |
| `black_bloc/api/tools/chat.py:152` | {turns} answers came from a model today. | ephemeral answer | no | `chat_today_word_no_limit` | 2 |
| `black_bloc/chat.py:542` | Good, {name}! Keeping an eye on {attendees} cookout attendees right now. | ephemeral answer | no | `chat_attendee_lines` | 2 |
| `black_bloc/chat.py:542` | Hey {name}! That makes {attendees} of us at the cookout today. | ephemeral answer | no | `chat_attendee_lines_2` | 2 |
| `black_bloc/chat.py:796` | An intent's name has to be {limit} characters or fewer, so nothing was saved. Sh… | ephemeral answer | no | `chat_name_too_long` | 2 |
| `black_bloc/chat.py:800` | **{name}** is one of Black Bloc's own intents, so a second one cannot take that … | ephemeral answer | no | `chat_name_is_built_in` | 2 |
| `black_bloc/chat.py:804` | An intent needs at least one trigger phrase, or nothing would ever reach it. Add… | ephemeral answer | no | `chat_no_triggers` | 2 |
| `black_bloc/chat.py:808` | An intent takes at most {limit} trigger phrases, so nothing was saved. Trim the … | ephemeral answer | no | `chat_too_many_triggers` | 2 |
| `black_bloc/chat.py:812` | A trigger phrase has to be {limit} characters or fewer, so nothing was saved. **… | ephemeral answer | no | `chat_trigger_too_long` | 2 |
| `black_bloc/chat.py:817` | A line has to be {limit} characters or fewer, so nothing was saved. Discord will… | ephemeral answer | no | `chat_text_too_long` | 2 |
| `black_bloc/chat.py:821` | **{given}** is not somewhere a line can go. They are {known} — `filled` is the o… | ephemeral answer | no | `chat_not_a_slot` | 2 |
| `black_bloc/chat_data.py:21` | no links | ephemeral answer | no | `chat_no_links` | 2 |
| `black_bloc/chat_data.py:22` | nothing from them yet | ephemeral answer | no | `chat_nothing_held` | 2 |
| `black_bloc/chat_data.py:23` | the mods | ephemeral answer | no | `chat_some_mods` | 2 |
| `black_bloc/chat_data.py:29` | @everyone | ephemeral answer | no | `chat_everyone` | 2 |
| `black_bloc/chat_data.py:34` | The menus are posted in {where}. | ephemeral answer | no | `chat_menus_live_in` | 2 |
| `black_bloc/chat_data.py:42` | no roles yet | ephemeral answer | no | `chat_no_roles_yet` | 2 |
| `black_bloc/chat_data.py:43` | no staff roles | ephemeral answer | no | `chat_no_staff_roles` | 2 |
| `black_bloc/chat_data.py:44` | Yes — that is staff, so they can help. | ephemeral answer | no | `chat_is_staff` | 2 |
| `black_bloc/chat_data.py:45` | They are not staff, which is nothing against them — ask me for a mod and I will … | ephemeral answer | no | `chat_not_staff` | 2 |
| `black_bloc/chat_data.py:49` | point at somebody with an @ and I will say what they hold — `is @somebody a mod`… | ephemeral answer | no | `chat_nobody_mentioned` | 2 |
| `black_bloc/chat_data.py:52` | that is me, and I am a bot, so there is nothing to vouch for. | ephemeral answer | no | `chat_only_me` | 2 |
| `black_bloc/chat_data.py:53` | I cannot see them in this server, so I cannot say what they hold. | ephemeral answer | no | `chat_member_unknown` | 2 |
| `black_bloc/chat_data.py:55` | Online right now: {names} — give one of them a shout. | ephemeral answer | no | `chat_online_now` | 2 |
| `black_bloc/chat_data.py:56` | None of them are online right now. | ephemeral answer | no | `chat_nobody_online` | 2 |
| `black_bloc/chat_data.py:59` | I did not catch which role you meant. Name it — `who has the Leads role` — and I… | ephemeral answer | no | `chat_no_role_asked` | 2 |
| `black_bloc/chat_data.py:63` | I can only count roles inside the server itself, and this is not in one. | ephemeral answer | no | `chat_not_in_a_server` | 2 |
| `black_bloc/chat_data.py:64` | there is no role here called **{asked}**, and nothing else comes close. | ephemeral answer | no | `chat_no_such_role` | 2 |
| `black_bloc/chat_data.py:65` | there is no role here called **{asked}**. The closest I have are {close}. | ephemeral answer | no | `chat_no_such_role_but` | 2 |
| `black_bloc/chat_data.py:66` | **{asked}** could be {close} — say which one and I will count it. | ephemeral answer | no | `chat_too_many_roles` | 2 |
| `black_bloc/chat_data.py:67` | **{role}** has nobody in it right now. | ephemeral answer | no | `chat_nobody_holds_it` | 2 |
| `black_bloc/chat_data.py:68` | …and {count} more | ephemeral answer | no | `chat_and_more` | 2 |
| `black_bloc/chat_data.py:69` | Any of them can help — or ask for a mod and I will point you at modmail. | ephemeral answer | no | `chat_escalate_modmail` | 2 |
| `black_bloc/chat_data.py:70` | Any of them can help — or ask for a mod and I will name the staff to ask. | ephemeral answer | no | `chat_escalate_staff` | 2 |
| `black_bloc/chat_memory.py:129` | last night | ephemeral answer | no | `chat_events` | 2 |
| `black_bloc/chat_memory.py:129` | last week | ephemeral answer | no | `chat_events_2` | 2 |
| `black_bloc/chat_memory.py:129` | this morning | ephemeral answer | no | `chat_events_3` | 2 |
| `black_bloc/chat_memory.py:129` | this afternoon | ephemeral answer | no | `chat_events_4` | 2 |
| `black_bloc/chat_memory.py:129` | was banned | ephemeral answer | no | `chat_events_5` | 2 |
| `black_bloc/chat_memory.py:129` | got banned | ephemeral answer | no | `chat_events_6` | 2 |
| `black_bloc/chat_memory.py:129` | was warned | ephemeral answer | no | `chat_events_7` | 2 |
| `black_bloc/chat_memory.py:129` | got warned | ephemeral answer | no | `chat_events_8` | 2 |
| `black_bloc/chat_memory.py:129` | was muted | ephemeral answer | no | `chat_events_9` | 2 |
| `black_bloc/chat_memory.py:129` | was kicked | ephemeral answer | no | `chat_events_10` | 2 |
| `black_bloc/chat_memory.py:129` | was timed out | ephemeral answer | no | `chat_events_11` | 2 |
| `black_bloc/chat_memory.py:129` | joined the call | ephemeral answer | no | `chat_events_12` | 2 |
| `black_bloc/chat_memory.py:129` | left the server | ephemeral answer | no | `chat_events_13` | 2 |
| `black_bloc/chat_memory.py:162` | timed out | ephemeral answer | no | `chat_outcomes` | 2 |
| `black_bloc/chat_memory.py:162` | was declined | ephemeral answer | no | `chat_outcomes_2` | 2 |
| `black_bloc/chat_memory.py:185` | years old | ephemeral answer | no | `chat_sensitive` | 2 |
| `black_bloc/chat_memory.py:185` | born in | ephemeral answer | no | `chat_sensitive_2` | 2 |
| `black_bloc/chat_memory.py:251` | they go by {name} | ephemeral answer | no | `chat_call_me_part` | 2 |
| `black_bloc/chat_memory.py:252` | still open: {threads} | ephemeral answer | no | `chat_threads_part` | 2 |
| `black_bloc/chat_memory.py:275` | (nothing) | ephemeral answer | no | `chat_nothing_said` | 2 |
| `black_bloc/chat_panel.py:62` | Answering @-mentions: **{mode}**. Conversation model: **{llm}**. | ephemeral answer | no | `chat_status_mode` | 2 |
| `black_bloc/chat_panel.py:63` | Every answer comes from Black Bloc's own written lines. | ephemeral answer | no | `chat_status_off_tail` | 2 |
| `black_bloc/chat_panel.py:64` | Tiers — the quick one: {simple}. The careful one: {important}. | ephemeral answer | no | `chat_status_tiers` | 2 |
| `black_bloc/chat_panel.py:65` | Answers today: **{today}** of {today_of}. Yours in the last hour: **{mine}** of … | ephemeral answer | no | `chat_status_turns` | 2 |
| `black_bloc/chat_panel.py:68` | This month so far: **{spent}** of {cap}. | ephemeral answer | no | `chat_status_money` | 2 |
| `black_bloc/chat_panel.py:69` | The models are resting until the 1st, so every answer comes from the written lin… | ephemeral answer | no | `chat_status_closed` | 2 |
| `black_bloc/chat_panel.py:73` | The last daily read did not finish: {why}. | ephemeral answer | no | `chat_status_ingest_trouble` | 2 |
| `black_bloc/chat_panel.py:74` | What the conversation models have spent is kept to server administrators here, s… | ephemeral answer | no | `chat_status_admin_only` | 2 |
| `black_bloc/chat_panel.py:83` | no ceiling | ephemeral answer | no | `chat_no_ceiling` | 2 |
| `black_bloc/chat_panel.py:85` | The voice is **{voice}** from the next answer on. | ephemeral answer | no | `chat_voice_changed` | 2 |
| `black_bloc/chat_panel.py:86` | **{name}** is {state}. | ephemeral answer | no | `chat_mood_changed` | 2 |
| `black_bloc/chat_panel.py:91` | **{name}** is not one of the voices Black Bloc knows, so nothing was changed. Th… | ephemeral answer | no | `chat_no_such_trope` | 2 |
| `black_bloc/chat_panel.py:95` | **{label}** is switched off in the pool, so Black Bloc cannot be it. Turn it bac… | ephemeral answer | no | `chat_trope_is_off` | 2 |
| `black_bloc/chat_panel.py:99` | Black Bloc is set to be **{label}** and nothing else, so that voice cannot be sw… | ephemeral answer | no | `chat_trope_in_use` | 2 |
| `black_bloc/chat_panel.py:103` | **{label}** is the last voice left on and the pool is what Black Bloc is using, … | ephemeral answer | no | `chat_last_trope_on` | 2 |
| `black_bloc/chat_panel.py:107` | A mood the pool cannot do without is not on the list: the voice Black Bloc is se… | ephemeral answer | no | `chat_pool_guards` | 2 |
| `black_bloc/chat_panel.py:112` | Saved as note **{id}** — **{title}**. Black Bloc will quote it when it fits. | ephemeral answer | no | `chat_note_saved` | 2 |
| `black_bloc/chat_panel.py:113` | Note **{id}** — **{title}** — is saved. | ephemeral answer | no | `chat_note_edited` | 2 |
| `black_bloc/chat_panel.py:114` | Note **{id}** — **{title}** — is gone. | ephemeral answer | no | `chat_note_removed` | 2 |
| `black_bloc/chat_panel.py:120` | **{key}** is now `{value}`. | ephemeral answer | no | `chat_mode_saved` | 2 |
| `black_bloc/chat_panel.py:121` | Nothing was given, so nothing changed. | ephemeral answer | no | `chat_settings_nothing` | 2 |
| `black_bloc/chat_panel.py:122` | Saved — | ephemeral answer | no | `chat_settings_saved` | 2 |
| `black_bloc/chat_panel.py:123` | **{key}** is now `{value}` | ephemeral answer | no | `chat_settings_one` | 2 |
| `black_bloc/chat_panel.py:139` | Answer @-mentions | ephemeral answer | no | `chat_answer_on` | 2 |
| `black_bloc/chat_panel.py:140` | Stop answering @-mentions | ephemeral answer | no | `chat_answer_off` | 2 |
| `black_bloc/chat_panel.py:141` | Turn the conversation models on | ephemeral answer | no | `chat_llm_on` | 2 |
| `black_bloc/chat_panel.py:142` | Turn the conversation models off | ephemeral answer | no | `chat_llm_off` | 2 |
| `black_bloc/chat_panel.py:143` | Remove note **{id}** — **{title}**? Black Bloc stops quoting it at once. | ephemeral answer | no | `chat_remove_question` | 2 |
| `black_bloc/chat_panel.py:144` | Yes, remove it | ephemeral answer | no | `chat_remove_yes` | 2 |
| `black_bloc/cogs/content/chat.py:102` | ⏎ **What Black Bloc remembers about a person** — `/memory` and the Chat page's M… | ephemeral answer | no | `chat_memory_settings_header` | 2 |
| `black_bloc/cogs/content/chat.py:110` | Nothing has been written down yet. **Write one down…** starts the list, and Blac… | ephemeral answer | no | `chat_no_notes` | 2 |
| `black_bloc/cogs/content/chat.py:114` | Nothing written down matches **{query}**. | ephemeral answer | no | `chat_no_notes_match` | 2 |
| `black_bloc/cogs/content/chat.py:115` | **{count}** note(s){about}. `server` notes are rewritten daily and cannot be edi… | ephemeral answer | no | `chat_notes_header` | 2 |
| `black_bloc/cogs/content/chat.py:120` | no key set, so it does not exist | ephemeral answer | no | `chat_tier_no_key_2` | 2 |
| `black_bloc/cogs/content/chat.py:121` | last call failed ({why}) | ephemeral answer | no | `chat_tier_trouble` | 2 |
| `black_bloc/cogs/content/chat.py:122` | The server's own notes: **{count}** written down, last read {when}. | ephemeral answer | no | `chat_status_notes` | 2 |
| `black_bloc/cogs/content/chat.py:123` | The server's own notes: **{count}** written down; the daily read has not run yet… | ephemeral answer | no | `chat_status_notes_never` | 2 |
| `black_bloc/cogs/content/chat.py:127` | The voice is **{voice}** — {what} | ephemeral answer | no | `chat_voice_now` | 2 |
| `black_bloc/cogs/content/chat.py:128` | the house voice, warm and easy, with no mood on top of it. | ephemeral answer | no | `chat_voice_means` | 2 |
| `black_bloc/cogs/content/chat.py:128` | each conversation picks one of the moods below and drifts a step at a time. | ephemeral answer | no | `chat_voice_means_2` | 2 |
| `black_bloc/cogs/content/chat.py:132` | every conversation sounds like this one mood until the setting changes. | ephemeral answer | no | `chat_voice_is_a_mood` | 2 |
| `black_bloc/cogs/content/chat.py:133` | Nothing is using it yet: `chat_llm_mode` is off, so every answer still comes fro… | ephemeral answer | no | `chat_voice_off` | 2 |
| `black_bloc/cogs/content/chat.py:137` | ⏎ **The pool** — a mood that is off is never picked: | ephemeral answer | no | `chat_moods_header` | 2 |
| `black_bloc/cogs/content/chat.py:139` | ⏎ The pool has not been written yet; it fills itself in when Black Bloc starts u… | ephemeral answer | no | `chat_no_moods` | 2 |
| `black_bloc/cogs/content/chat.py:165` | {shown} of {total} — the rest are on the Chat page's Knowledge section | ephemeral answer | no | `chat_note_capped` | 2 |
| `black_bloc/cogs/content/chat.py:167` | Write something down | modal title | no | `chat_add_modal_title` | 2 |
| `black_bloc/cogs/content/chat.py:168` | Edit this note | modal title | no | `chat_edit_modal_title` | 2 |
| `black_bloc/cogs/content/chat.py:169` | The numbers chat runs on | modal title | no | `chat_limits_modal_title` | 2 |
| `black_bloc/cogs/content/chat.py:170` | Find a note | modal title | no | `chat_find_modal_title` | 2 |
| `black_bloc/cogs/content/chat.py:171` | Words to look for, the way a member would ask | modal title or field | no | `chat_find_label` | 2 |
| `black_bloc/cogs/content/chat.py:173` | What the note is about, in a few words | modal title or field | no | `chat_title_label` | 2 |
| `black_bloc/cogs/content/chat.py:174` | The note itself | modal title or field | no | `chat_body_label` | 2 |
| `black_bloc/cogs/content/chat.py:175` | Optional one-word grouping, like events or rules | modal title or field | no | `chat_tag_label` | 2 |
| `black_bloc/cogs/content/chat.py:177` | Seconds between one person's answers | modal title or field | no | `chat_cooldown_label` | 2 |
| `black_bloc/cogs/content/chat.py:178` | Answers one person may have in an hour | modal title or field | no | `chat_hourly_label` | 2 |
| `black_bloc/cogs/content/chat.py:179` | Answers the whole server may have in a day | modal title or field | no | `chat_daily_label` | 2 |
| `black_bloc/cogs/content/chat.py:180` | Dollars the models may spend in a month | modal title or field | no | `chat_cap_label` | 2 |
| `black_bloc/cogs/content/chat.py:181` | Minutes this panel stays live | modal title or field | no | `chat_minutes_label` | 2 |
| `black_bloc/cogs/content/chat.py:183` | written by: {source} | ephemeral answer | no | `chat_card_source` | 2 |
| `black_bloc/cogs/content/chat.py:184` | tag: {tag} | ephemeral answer | no | `chat_card_tag` | 2 |
| `black_bloc/cogs/content/chat.py:185` | tag: none | ephemeral answer | no | `chat_card_no_tag` | 2 |
| `black_bloc/cogs/content/chat_memory.py:63` | Black Bloc is not remembering anybody here at the moment, so nothing new is bein… | ephemeral answer | no | `chat_memory_is_off` | 2 |
| `black_bloc/cogs/content/chat_memory.py:68` | Black Bloc keeps what it remembers per server, and this conversation is not in o… | ephemeral answer | no | `chat_no_server` | 2 |
| `black_bloc/cogs/content/chat_memory.py:72` | Black Bloc has not written anything down about you yet. It only keeps preference… | ephemeral answer | no | `chat_nothing_yet` | 2 |
| `black_bloc/cogs/content/chat_memory.py:76` | Black Bloc is not remembering you, so nothing new is being written down. **Remem… | ephemeral answer | no | `chat_you_are_opted_out` | 2 |
| `black_bloc/cogs/content/chat_memory.py:80` | Nobody else can read this. | ephemeral answer | no | `chat_header` | 2 |
| `black_bloc/cogs/content/chat_memory.py:85` | Cleared. Black Bloc remembers nothing about you here. | ephemeral answer | no | `chat_forgotten` | 2 |
| `black_bloc/cogs/content/chat_memory.py:86` | There was nothing written down about you, so nothing was cleared. | ephemeral answer | no | `chat_nothing_to_forget` | 2 |
| `black_bloc/cogs/content/chat_memory.py:87` | Dropped **{count}** line(s). What is left is above. | ephemeral answer | no | `chat_dropped` | 2 |
| `black_bloc/cogs/content/chat_memory.py:88` | Nothing written down matches **{words}**, so nothing was dropped. **Forget one o… | ephemeral answer | no | `chat_no_match` | 2 |
| `black_bloc/cogs/content/chat_memory.py:92` | Black Bloc will not write anything down about you from now on, and what it had i… | ephemeral answer | no | `chat_turned_off` | 2 |
| `black_bloc/cogs/content/chat_memory.py:96` | Black Bloc was already not remembering you. Nothing changed. | ephemeral answer | no | `chat_already_off` | 2 |
| `black_bloc/cogs/content/chat_memory.py:97` | Black Bloc may write down your preferences again — what to call you and how you … | ephemeral answer | no | `chat_turned_on` | 2 |
| `black_bloc/cogs/content/chat_memory.py:101` | Black Bloc was already allowed to remember you. Nothing changed. | ephemeral answer | no | `chat_already_on` | 2 |
| `black_bloc/cogs/content/chat_memory.py:106` | That line is not there any more — Black Bloc wrote your profile up again while t… | ephemeral answer | no | `chat_profile_moved` | 2 |
| `black_bloc/cogs/content/chat_memory.py:112` | {shown} of {total} — Forget by words… reaches the rest | ephemeral answer | no | `chat_pick_capped` | 2 |
| `black_bloc/cogs/content/chat_memory.py:113` | Forget by words | modal title or field | no | `chat_forget_words_title` | 2 |
| `black_bloc/cogs/content/chat_memory.py:114` | A few words from the line you want dropped | modal title or field | no | `chat_forget_words_label` | 2 |
| `black_bloc/cogs/content/chat_memory.py:115` | Clear everything Black Bloc has written down about you here? There is no undo. | ephemeral answer | no | `chat_forget_all_question` | 2 |
| `black_bloc/cogs/content/chat_memory.py:118` | Stop Black Bloc remembering you? It clears what it already has as well, and ther… | ephemeral answer | no | `chat_stop_question` | 2 |
| `black_bloc/groq.py:22` | openai/gpt-oss-120b | ephemeral answer | no | `chat_default_model` | 2 |
| `black_bloc/knowledge.py:31` | @everyone | ephemeral answer | no | `chat_everyone_2` | 2 |
| `black_bloc/knowledge.py:50` | A note needs a title, so nothing was saved. One short line naming what it is abo… | ephemeral answer | no | `chat_title_needed` | 2 |
| `black_bloc/knowledge.py:51` | A note's title has to be {limit} characters or fewer, so nothing was saved. The … | ephemeral answer | no | `chat_title_too_long` | 2 |
| `black_bloc/knowledge.py:55` | A note needs something in it, so nothing was saved. | ephemeral answer | no | `chat_body_needed` | 2 |
| `black_bloc/knowledge.py:56` | A note has to be {limit} characters or fewer, so nothing was saved. Split it int… | ephemeral answer | no | `chat_body_too_long` | 2 |
| `black_bloc/knowledge.py:60` | A note's tag has to be {limit} characters or fewer, so nothing was saved. | ephemeral answer | no | `chat_tag_too_long` | 2 |
| `black_bloc/knowledge.py:61` | This server already has a note called **{title}**, so nothing was saved. Edit th… | ephemeral answer | no | `chat_title_taken` | 2 |
| `black_bloc/knowledge.py:65` | **{given}** is not somewhere a note can come from. They are {known} — `staff` is… | ephemeral answer | no | `chat_not_a_source` | 2 |
| `black_bloc/knowledge.py:69` | That note is one Black Bloc writes from the server itself every day, so an edit … | ephemeral answer | no | `chat_server_row_is_not_yours` | 2 |
| `black_bloc/personas.py:24` | Black Bloc's personality pool manifest is missing: {path} is not there, so the r… | ephemeral answer | no | `chat_manifest_missing` | 2 |
| `black_bloc/personas.py:29` | Black Bloc's personality pool manifest at {path} could not be read as JSON ({rea… | ephemeral answer | no | `chat_manifest_unreadable` | 2 |
| `black_bloc/personas.py:33` | Black Bloc's personality pool manifest at {path} lists no tropes at all, so ther… | ephemeral answer | no | `chat_manifest_empty` | 2 |
| `black_bloc/personas.py:37` | The personality pool manifest lists {names}, and personas.py has no cookout voic… | ephemeral answer | no | `chat_voice_missing` | 2 |
| `black_bloc/personas.py:42` | personas.py holds a cookout voice for {names}, and the personality pool manifest… | ephemeral answer | no | `chat_voice_extra` | 2 |
| `black_bloc/personas.py:47` | The personality pool manifest's {clause} clause wants a {slot} slot and Black Bl… | ephemeral answer | no | `chat_slot_missing` | 2 |
| `black_bloc/personas.py:92` | the server's own notes | ephemeral answer | no | `chat_cookout_slots` | 2 |
| `black_bloc/personas.py:92` | this server has a range of ages, | ephemeral answer | no | `chat_cookout_slots_2` | 2 |
| `black_bloc/personas.py:109` | You are Black Bloc, the helper bot for the Black in a Flash! Discord server — th… | ephemeral answer | no | `chat_core` | 2 |
| `black_bloc/personas.py:155` | ## Your own commands ⏎ Everything a member can run. Half a line each; `/help` pr… | ephemeral answer | no | `chat_features` | 2 |
| `black_bloc/personas.py:192` | ## How you sound ⏎ You sound like the cookout: warm, easy, a little playful — so… | ephemeral answer | no | `chat_cookout_voice` | 2 |
| `black_bloc/personas.py:200` | ## How you sound right now ⏎ This is a mood, not a different person. You are sti… | ephemeral answer | no | `chat_trope_block` | 2 |
| `black_bloc/personas.py:215` | You are BRIGHT and fast today — genuinely delighted to be asked. Short exclamati… | ephemeral answer | no | `chat_voices` | 2 |
| `black_bloc/personas.py:215` | You are THEATRICAL today — grand pronouncements about small things, a flair for … | ephemeral answer | no | `chat_voices_2` | 2 |
| `black_bloc/personas.py:215` | You are PLAYFUL today — light teasing, a raised eyebrow, enjoying yourself. Neve… | ephemeral answer | no | `chat_voices_3` | 2 |
| `black_bloc/personas.py:215` | You are CHARMING today, with a playful wink — light compliments, affectionate te… | ephemeral answer | no | `chat_voices_4` | 2 |
| `black_bloc/personas.py:215` | You are WARM today — familiar, unhurried, glad to see them. You notice how they … | ephemeral answer | no | `chat_voices_5` | 2 |
| `black_bloc/personas.py:215` | You are COSY today — the voice of a folding chair in the shade and a full plate.… | ephemeral answer | no | `chat_voices_6` | 2 |
| `black_bloc/personas.py:215` | You are a little SHY today — soft, hedging, a bit apologetic about taking up roo… | ephemeral answer | no | `chat_voices_7` | 2 |
| `black_bloc/personas.py:215` | You are SCHOLARLY today — precise, fond of getting a detail exactly right, quiet… | ephemeral answer | no | `chat_voices_8` | 2 |
| `black_bloc/personas.py:215` | You are HARD-BOILED today — clipped sentences, a little world-weary, everything … | ephemeral answer | no | `chat_voices_9` | 2 |
| `black_bloc/personas.py:215` | You are DEADPAN today — flat, economical, dry. The joke is the flatness. Few wor… | ephemeral answer | no | `chat_voices_10` | 2 |
| `black_bloc/personas.py:215` | You are BRUSQUE today, and helping anyway — mildly put upon, "I suppose I can lo… | ephemeral answer | no | `chat_voices_11` | 2 |

### guides

*160 strings — 0 keyed · 2 unkeyed pass 1 · 54 unkeyed pass 2 · 104 not member-facing (not listed).*

*Guides text is not in the code: it is `guides` / `guide_steps` / `guide_faults` / `guide_facts`
rows the site already edits. The rows below are the Discord door only.*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/guides.py:81` | never fails | card field | no | `guides_promise_words` | 1 |
| `black_bloc/guides.py:119` | Step {position} has nothing in it, so nothing was saved. Write what to do, or re… | channel post | no | `guides_step_needs_text` | 1 |
| `black_bloc/api/tools/guides.py:27` | **{title}** is made. It is unpublished until you press Publish. | ephemeral answer | no | `guides_created_said` | 2 |
| `black_bloc/api/tools/guides.py:28` | **{title}** is saved. | ephemeral answer | no | `guides_saved_said` | 2 |
| `black_bloc/api/tools/guides.py:29` | **{title}** is published — members and `/help` can see it now. | ephemeral answer | no | `guides_published_said` | 2 |
| `black_bloc/api/tools/guides.py:30` | **{title}** is unpublished. Staff still see it; members and `/help` do not. | ephemeral answer | no | `guides_unpublished_said` | 2 |
| `black_bloc/api/tools/guides.py:31` | **{title}** is gone. | ephemeral answer | no | `guides_deleted_said` | 2 |
| `black_bloc/api/tools/guides.py:32` | **{title}** is back to the words it shipped with. | ephemeral answer | no | `guides_reset_said` | 2 |
| `black_bloc/api/tools/guides.py:33` | Thank you — **{title}** is marked as working. Staff read the count; nothing else… | ephemeral answer | no | `guides_confirmed_said` | 2 |
| `black_bloc/api/tools/guides.py:36` | The picture on step {position} is replaced. | ephemeral answer | no | `guides_media_said` | 2 |
| `black_bloc/api/tools/guides.py:37` | The picture on **{title}** is replaced. | ephemeral answer | no | `guides_media_guide_said` | 2 |
| `black_bloc/api/tools/guides.py:38` | {count} screenshots are marked for re-shooting. The capture runbook's stale list… | ephemeral answer | no | `guides_all_stale_said` | 2 |
| `black_bloc/api/tools/guides.py:42` | 1 screenshot is marked for re-shooting. The capture runbook's stale list is the … | ephemeral answer | no | `guides_one_stale_said` | 2 |
| `black_bloc/api/tools/guides.py:45` | Every screenshot was already marked. | ephemeral answer | no | `guides_already_all_stale` | 2 |
| `black_bloc/api/tools/guides.py:46` | **{slug}** was written here rather than shipped with Black Bloc, so there is no … | ephemeral answer | no | `guides_not_seeded` | 2 |
| `black_bloc/api/tools/guides.py:50` | That step is not part of **{slug}**, so the picture was not uploaded. Reload the… | ephemeral answer | no | `guides_no_such_step` | 2 |
| `black_bloc/api/tools/guides.py:54` | Guides are off for members right now, so nobody but staff can open this page. A … | ephemeral answer | no | `guides_guides_are_off_for_staff` | 2 |
| `black_bloc/api/tools/guides.py:58` | The {what} that arrived is not a number, so nothing was saved. It is a fault in … | ephemeral answer | no | `guides_not_a_number` | 2 |
| `black_bloc/api/tools/guides.py:62` | That change arrived with nothing in it, so nothing was saved. It is a fault in t… | ephemeral answer | no | `guides_nothing_to_save` | 2 |
| `black_bloc/guides.py:50` | image/png | ephemeral answer | no | `guides_media_types` | 2 |
| `black_bloc/guides.py:50` | image/jpeg | ephemeral answer | no | `guides_media_types_2` | 2 |
| `black_bloc/guides.py:50` | image/jpeg | ephemeral answer | no | `guides_media_types_3` | 2 |
| `black_bloc/guides.py:50` | image/webp | ephemeral answer | no | `guides_media_types_4` | 2 |
| `black_bloc/guides.py:56` | private, max-age=86400 | ephemeral answer | no | `guides_media_cache` | 2 |
| `black_bloc/guides.py:58` | This step asks for more than one thing. Split it so each step is one press. | ephemeral answer | no | `guides_lint_one_action` | 2 |
| `black_bloc/guides.py:61` | No control is named. Write the button, select or menu item in **bold**, spelled … | ephemeral answer | no | `guides_lint_name_the_control` | 2 |
| `black_bloc/guides.py:65` | This step opens with **{word}**. Start with the verb — Press, Type, Pick — and s… | ephemeral answer | no | `guides_lint_imperative` | 2 |
| `black_bloc/guides.py:69` | This step is {count} characters. Keep it under {limit}. | ephemeral answer | no | `guides_lint_do_long` | 2 |
| `black_bloc/guides.py:70` | This expect line is {count} characters. Keep it under {limit}. | ephemeral answer | no | `guides_lint_expect_long` | 2 |
| `black_bloc/guides.py:71` | The expect line starts with **{word}**. Say what is on the screen — The panel…, … | ephemeral answer | no | `guides_lint_expect_observable` | 2 |
| `black_bloc/guides.py:75` | **{word}** tells nobody anything. Say what to press instead. | ephemeral answer | no | `guides_lint_ease` | 2 |
| `black_bloc/guides.py:76` | **{word}** is a promise rather than a fact. Say what happens, and when it does n… | ephemeral answer | no | `guides_lint_promise` | 2 |
| `black_bloc/guides.py:82` | You can | ephemeral answer | no | `guides_openers` | 2 |
| `black_bloc/guides.py:82` | Simply | ephemeral answer | no | `guides_openers_2` | 2 |
| `black_bloc/guides.py:82` | Just | ephemeral answer | no | `guides_openers_3` | 2 |
| `black_bloc/guides.py:82` | Easily | ephemeral answer | no | `guides_openers_4` | 2 |
| `black_bloc/guides.py:82` | Please | ephemeral answer | no | `guides_openers_5` | 2 |
| `black_bloc/guides.py:88` | by=deploy.ps1 | ephemeral answer | no | `guides_deploy_marker` | 2 |
| `black_bloc/guides.py:90` | There is no guide called **{slug}**, so nothing was done. It may have been renam… | ephemeral answer | no | `guides_no_such_guide` | 2 |
| `black_bloc/guides.py:94` | Guides are turned off for this server, so there is nothing to show. A Lead turns… | ephemeral answer | no | `guides_guides_off` | 2 |
| `black_bloc/guides.py:98` | Editing a guide needs Manage Server on this server, and your account does not ho… | ephemeral answer | no | `guides_not_yours_to_edit` | 2 |
| `black_bloc/guides.py:103` | **{slug}** is one of the guides Black Bloc ships with, so it cannot be deleted —… | ephemeral answer | no | `guides_seeded_cannot_be_deleted` | 2 |
| `black_bloc/guides.py:108` | There is already a guide at **{slug}**, so nothing was made. Give this one a dif… | ephemeral answer | no | `guides_slug_taken` | 2 |
| `black_bloc/guides.py:112` | A guide needs a title Black Bloc can turn into a web address, and that one came … | ephemeral answer | no | `guides_slug_needed` | 2 |
| `black_bloc/guides.py:116` | A guide needs a title and a goal, so nothing was saved. Fill both in and save ag… | ephemeral answer | no | `guides_title_needed` | 2 |
| `black_bloc/guides.py:123` | A guide shows at most {limit} live values, and that one asked for {count}, so no… | ephemeral answer | no | `guides_too_many_facts` | 2 |
| `black_bloc/guides.py:127` | **{ref}** is not one of Black Bloc's settings, so nothing was saved. Pick a sett… | ephemeral answer | no | `guides_no_such_setting` | 2 |
| `black_bloc/guides.py:131` | **{ref}** is not a value a guide may show: it is one of the keys that decide who… | ephemeral answer | no | `guides_setting_is_private` | 2 |
| `black_bloc/guides.py:136` | **{ref}** only decides how much of a feature is repeated into the Discord log, w… | ephemeral answer | no | `guides_setting_is_a_log_level` | 2 |
| `black_bloc/guides.py:140` | **{ref}** is not one of the live values Black Bloc can read, so nothing was save… | ephemeral answer | no | `guides_no_such_probe` | 2 |
| `black_bloc/guides.py:144` | **{command}** already has a published guide (**{slug}**), and `/help` can only l… | ephemeral answer | no | `guides_command_taken` | 2 |
| `black_bloc/guides.py:149` | That picture is {size} and Black Bloc keeps guide screenshots under {limit}. Not… | ephemeral answer | no | `guides_media_too_big` | 2 |
| `black_bloc/guides.py:154` | **{name}** is not a picture Black Bloc can serve. Nothing was uploaded — send a … | ephemeral answer | no | `guides_media_wrong_type` | 2 |
| `black_bloc/guides.py:158` | That upload did not arrive as a picture Black Bloc could read, so nothing was up… | ephemeral answer | no | `guides_media_unreadable` | 2 |
| `black_bloc/guides.py:162` | That picture is {side} pixels on its longest side and Black Bloc keeps guide scr… | ephemeral answer | no | `guides_media_too_wide` | 2 |
| `black_bloc/guides.py:167` | That picture is not one of this server's guide screenshots, so nothing was shown… | ephemeral answer | no | `guides_no_such_media` | 2 |

### posts

*97 strings — 0 keyed · 10 unkeyed pass 1 · 66 unkeyed pass 2 · 21 not member-facing (not listed).*

*A post's BODY is a `posts` row the site already edits (`posts_seed.json` seeds it). The rows
below are the panel and the plumbing around it.*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/api/tools/posts.py:17` | Black Bloc is in test mode, so a post only reaches #{channel} or a channel it ma… | card description | no | `posts_test_mode_note` | 1 |
| `black_bloc/api/tools/posts.py:33` | Posts are in **shadow** and there is nowhere to put a shadow copy: this server h… | card description | no | `posts_no_shadow_channel_note` | 1 |
| `black_bloc/cogs/community/posts.py:327` | Edit… | button label | no | `posts_button_edit` | 1 |
| `black_bloc/posts.py:37` | a plain message | card field | no | `posts_style_words` | 1 |
| `black_bloc/posts.py:37` | an embed | card field | no | `posts_style_words_2` | 1 |
| `black_bloc/posts.py:75` | — or set the style to an embed, which holds 4096 | channel post | no | `posts_switch_to_embed` | 1 |
| `black_bloc/posts.py:141` | shadow — this goes to {shadow}, not {where}, until posts are on. | channel post | no | `posts_shadow_line` | 1 |
| `black_bloc/posts.py:170` | Posts | card title | no | `posts_panel_title` | 1 |
| `black_bloc/posts.py:171` | The messages Black Bloc keeps current in this server. | card description | no | `posts_panel_intro` | 1 |
| `black_bloc/posts.py:173` | This panel has gone quiet — run `/posts` again. | card description | no | `posts_panel_timeout_footer` | 1 |
| `black_bloc/api/tools/posts.py:22` | Posts are off for this server, so **Post it** and **Take it down** refuse in wor… | ephemeral answer | no | `posts_posts_are_off` | 2 |
| `black_bloc/api/tools/posts.py:27` | Posts are in **shadow**: **Post it** sends the real message to {where} and keeps… | ephemeral answer | no | `posts_posts_are_shadow` | 2 |
| `black_bloc/cogs/community/posts.py:83` | Edit this post | modal title or field | no | `posts_modal_title` | 2 |
| `black_bloc/cogs/community/posts.py:84` | A new post | modal title | no | `posts_new_modal_title` | 2 |
| `black_bloc/cogs/community/posts.py:85` | A post… | ephemeral answer | no | `posts_pick_a_post` | 2 |
| `black_bloc/cogs/community/posts.py:86` | New post… | ephemeral answer | no | `posts_new_post` | 2 |
| `black_bloc/cogs/community/posts.py:87` | Channel… | ephemeral answer | no | `posts_pick_a_channel` | 2 |
| `black_bloc/cogs/community/posts.py:88` | Style… | ephemeral answer | no | `posts_pick_a_style` | 2 |
| `black_bloc/cogs/community/posts.py:89` | Delete this post | ephemeral answer | no | `posts_delete_this_post` | 2 |
| `black_bloc/cogs/community/posts.py:90` | Yes, delete it | ephemeral answer | no | `posts_delete_yes` | 2 |
| `black_bloc/cogs/community/posts.py:91` | Yes, put it back | ephemeral answer | no | `posts_reset_yes` | 2 |
| `black_bloc/cogs/community/posts.py:92` | Posts are: off / shadow / on | ephemeral answer | no | `posts_mode_pick` | 2 |
| `black_bloc/cogs/community/posts.py:93` | Posts are: {mode} | ephemeral answer | no | `posts_mode_option` | 2 |
| `black_bloc/cogs/community/posts.py:94` | Back | ephemeral answer | no | `posts_back` | 2 |
| `black_bloc/cogs/community/posts.py:95` | Logs | ephemeral answer | no | `posts_logs` | 2 |
| `black_bloc/cogs/community/posts.py:100` | Nothing is in Discord for this one yet. | ephemeral answer | no | `posts_not_posted_yet` | 2 |
| `black_bloc/cogs/community/posts.py:101` | Every word goes back to the message Black Bloc ships with. Anything written here… | ephemeral answer | no | `posts_reset_question` | 2 |
| `black_bloc/cogs/community/posts.py:105` | Every word goes with it. Nothing puts it back. | ephemeral answer | no | `posts_delete_question` | 2 |
| `black_bloc/cogs/community/posts.py:469` | What is it called? | modal field label | no | `posts_modal_what_is_it_called` | 2 |
| `black_bloc/cogs/community/posts.py:491` | Title | modal field label | no | `posts_modal_title_2` | 2 |
| `black_bloc/cogs/community/posts.py:493` | The message | modal field label | no | `posts_modal_the_message` | 2 |
| `black_bloc/posts.py:62` | There is no post called **{slug}**, so nothing was done. It may have been rename… | ephemeral answer | no | `posts_no_such_post` | 2 |
| `black_bloc/posts.py:66` | Posts are turned off for this server, so nothing was done. A Lead turns them bac… | ephemeral answer | no | `posts_posts_off` | 2 |
| `black_bloc/posts.py:71` | That post is {count} characters and {style_word} holds {limit}, so nothing was {… | ephemeral answer | no | `posts_body_too_long` | 2 |
| `black_bloc/posts.py:76` | A post's title holds {limit} characters and that one is {count}, so nothing was … | ephemeral answer | no | `posts_title_too_long` | 2 |
| `black_bloc/posts.py:80` | An embed's title holds {limit} characters and that one is {count}, so nothing wa… | ephemeral answer | no | `posts_embed_title_too_long` | 2 |
| `black_bloc/posts.py:85` | **{title}** has no channel to go in yet, so there is nothing to post it to. Pick… | ephemeral answer | no | `posts_no_channel_yet` | 2 |
| `black_bloc/posts.py:89` | **{given}** is not a channel Black Bloc can see in this server, so nothing was s… | ephemeral answer | no | `posts_unknown_channel` | 2 |
| `black_bloc/posts.py:93` | **{title}** has nothing written in it yet, so there is nothing to post. Write th… | ephemeral answer | no | `posts_nothing_to_post` | 2 |
| `black_bloc/posts.py:97` | **{title}** is not posted anywhere right now, so there is nothing to take down. … | ephemeral answer | no | `posts_not_posted` | 2 |
| `black_bloc/posts.py:101` | Posts are in **shadow**, so **{title}** goes to the shadow channel rather than i… | ephemeral answer | no | `posts_no_shadow_channel` | 2 |
| `black_bloc/posts.py:106` | the channel is not one Black Bloc can see any more | ephemeral answer | no | `posts_channel_gone` | 2 |
| `black_bloc/posts.py:107` | no channel yet | ephemeral answer | no | `posts_no_channel_word` | 2 |
| `black_bloc/posts.py:108` | a channel Black Bloc cannot see | ephemeral answer | no | `posts_channel_unseen` | 2 |
| `black_bloc/posts.py:109` | Discord would not take that post, so **{title}** is unchanged: {reason}. That is… | ephemeral answer | no | `posts_post_failed_said` | 2 |
| `black_bloc/posts.py:114` | Discord would not remove that message, so **{title}** is still posted: {reason}.… | ephemeral answer | no | `posts_take_down_failed_said` | 2 |
| `black_bloc/posts.py:118` | **{slug}** is the post Black Bloc ships with, so it cannot be deleted — a deploy… | ephemeral answer | no | `posts_seeded_cannot_be_deleted` | 2 |
| `black_bloc/posts.py:123` | **{slug}** was written here rather than shipped with Black Bloc, so there is no … | ephemeral answer | no | `posts_not_seeded` | 2 |
| `black_bloc/posts.py:127` | **{title}** is still posted in Discord, so it was not deleted. Press **Take it d… | ephemeral answer | no | `posts_posted_cannot_be_deleted` | 2 |
| `black_bloc/posts.py:131` | There is already a post at **{slug}**, so nothing was made. Give this one a diff… | ephemeral answer | no | `posts_slug_taken` | 2 |
| `black_bloc/posts.py:135` | A post needs a title Black Bloc can turn into a web address, and that one came o… | ephemeral answer | no | `posts_slug_needed` | 2 |
| `black_bloc/posts.py:139` | A post needs a title, so nothing was saved. Fill it in and save again. | ephemeral answer | no | `posts_title_needed` | 2 |
| `black_bloc/posts.py:142` | shadow — this goes to {shadow}. It has no channel of its own yet, and nothing re… | ephemeral answer | no | `posts_shadow_line_nowhere` | 2 |
| `black_bloc/posts.py:146` | shadow — this goes to {shadow}, which is where it was going anyway. | ephemeral answer | no | `posts_shadow_line_same` | 2 |
| `black_bloc/posts.py:148` | **{title}** is saved. | ephemeral answer | no | `posts_saved_said` | 2 |
| `black_bloc/posts.py:149` | **{title}** is made. Nothing is in Discord until you press Post it. | ephemeral answer | no | `posts_created_said` | 2 |
| `black_bloc/posts.py:150` | **{title}** is posted in {where}. | ephemeral answer | no | `posts_posted_said` | 2 |
| `black_bloc/posts.py:151` | **{title}** is updated where it was already posted, in {where}. | ephemeral answer | no | `posts_updated_said` | 2 |
| `black_bloc/posts.py:152` | **{title}** is posted in {where} — the shadow copy, because posts are in shadow.… | ephemeral answer | no | `posts_shadow_posted_said` | 2 |
| `black_bloc/posts.py:156` | **{title}** is updated in {where} — the shadow copy, because posts are in shadow… | ephemeral answer | no | `posts_shadow_updated_said` | 2 |
| `black_bloc/posts.py:160` | **{title}** is taken down. Every word is still here. | ephemeral answer | no | `posts_taken_down_said` | 2 |
| `black_bloc/posts.py:161` | **{title}** is back to the words it shipped with. | ephemeral answer | no | `posts_reset_said` | 2 |
| `black_bloc/posts.py:162` | **{title}** is gone. | ephemeral answer | no | `posts_deleted_said` | 2 |
| `black_bloc/posts.py:163` | Posts are on. Staff can post from the site and from `/posts`. | ephemeral answer | no | `posts_mode_on_said` | 2 |
| `black_bloc/posts.py:164` | Posts are off. `/posts` disappears within about a minute; the text is all kept. | ephemeral answer | no | `posts_mode_off_said` | 2 |
| `black_bloc/posts.py:165` | Posts are in shadow. Post it sends the message to {where} and keeps it edited th… | ephemeral answer | no | `posts_mode_shadow_said` | 2 |
| `black_bloc/posts.py:172` | There are no posts yet. | ephemeral answer | no | `posts_panel_empty` | 2 |
| `black_bloc/posts.py:175` | Post it | ephemeral answer | no | `posts_post_it` | 2 |
| `black_bloc/posts.py:176` | Update the post | ephemeral answer | no | `posts_update_the_post` | 2 |
| `black_bloc/posts.py:177` | Take it down | ephemeral answer | no | `posts_take_it_down` | 2 |
| `black_bloc/posts.py:178` | Put the original back | ephemeral answer | no | `posts_put_the_original_back` | 2 |
| `black_bloc/posts.py:179` | Pin it | ephemeral answer | no | `posts_pin_it` | 2 |
| `black_bloc/posts.py:180` | Do not pin it | ephemeral answer | no | `posts_do_not_pin_it` | 2 |
| `black_bloc/posts.py:183` | posted (shadow) | ephemeral answer | no | `posts_status_posted_shadow` | 2 |
| `black_bloc/posts.py:185` | not posted | ephemeral answer | no | `posts_status_not_posted` | 2 |
| `black_bloc/posts.py:186` | changes not yet posted | ephemeral answer | no | `posts_status_pending` | 2 |

### minutes

*82 strings — 3 keyed · 20 unkeyed pass 1 · 43 unkeyed pass 2 · 19 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/minutes.py:37` | *(the key's value)* | read from the store at render | **yes → `minutes_notes_title`** (ns `events`, 1 read site(s)) | — | 1 |
| `black_bloc/minutes.py:36` | *(the key's value)* | read from the store at render | **yes → `minutes_prompt`** (ns `events`, 1 read site(s)) | — | 1 |
| `black_bloc/minutes.py:35` | *(the key's value)* | read from the store at render | **yes → `minutes_start_text`** (ns `events`, 1 read site(s)) | — | 1 |
| `black_bloc/api/tools/minutes.py:22` | Black Bloc is in test mode, so a meeting's announcement and its notes land in #{… | card description | no | `minutes_test_mode_note` | 1 |
| `black_bloc/api/tools/minutes.py:26` | There is no speech-to-text key on this host, so Start refuses in words. The key … | card description | no | `minutes_no_transcriber_note` | 1 |
| `black_bloc/api/tools/minutes.py:30` | The voice-recording extension is not installed on this host, so Start refuses in… | card description | no | `minutes_no_extension_note` | 1 |
| `black_bloc/cogs/community/minutes.py:41` | Edit the notes… | card field | no | `minutes_edit_label` | 1 |
| `black_bloc/cogs/community/minutes.py:42` | Write the notes again | card field | no | `minutes_rewrite_label` | 1 |
| `black_bloc/cogs/community/minutes.py:48` | The notes | card field | no | `minutes_notes_field` | 1 |
| `black_bloc/minutes.py:54` | somebody said stop notes | card field | no | `minutes_by_words` | 1 |
| `black_bloc/minutes.py:77` | Meeting minutes | card title | no | `minutes_panel_title` | 1 |
| `black_bloc/minutes.py:78` | Black Bloc joins the voice channel you are in, listens, and writes the meeting u… | card description | no | `minutes_panel_intro` | 1 |
| `black_bloc/minutes.py:83` | This panel has gone quiet — run /minutes again. | card description | no | `minutes_panel_timeout_footer` | 1 |
| `black_bloc/minutes.py:84` | Start taking notes | card field | no | `minutes_start_label` | 1 |
| `black_bloc/minutes.py:85` | Stop | card field | no | `minutes_stop_label` | 1 |
| `black_bloc/minutes.py:86` | Where notes go… | card field | no | `minutes_where_label` | 1 |
| `black_bloc/minutes.py:87` | Logs | card field | no | `minutes_logs_label` | 1 |
| `black_bloc/minutes.py:89` | Post again | card field | no | `minutes_post_again_label` | 1 |
| `black_bloc/minutes.py:90` | Delete | card field | no | `minutes_delete_label` | 1 |
| `black_bloc/minutes.py:186` | It is still a prototype: only staff can start one, and every meeting announces i… | card description | no | `minutes_mode_on_note` | 1 |
| `black_bloc/minutes.py:592` | Where | card field name | no | `minutes_card_where` | 1 |
| `black_bloc/minutes.py:594` | Started | card field name | no | `minutes_card_started` | 1 |
| `black_bloc/minutes.py:597` | Heard | card field name | no | `minutes_card_heard` | 1 |
| `black_bloc/api/tools/minutes.py:17` | Meeting minutes are off for this server, so `/minutes` is hidden and Start refus… | ephemeral answer | no | `minutes_minutes_are_off` | 2 |
| `black_bloc/cogs/community/minutes.py:38` | A meeting… | ephemeral answer | no | `minutes_pick_a_meeting` | 2 |
| `black_bloc/cogs/community/minutes.py:39` | Where the notes go… | ephemeral answer | no | `minutes_pick_a_channel` | 2 |
| `black_bloc/cogs/community/minutes.py:40` | Back | ephemeral answer | no | `minutes_back` | 2 |
| `black_bloc/cogs/community/minutes.py:43` | Yes, delete it | ephemeral answer | no | `minutes_delete_yes` | 2 |
| `black_bloc/cogs/community/minutes.py:44` | The notes and every word of the transcript go with it. Nothing puts them back. | ephemeral answer | no | `minutes_delete_question` | 2 |
| `black_bloc/cogs/community/minutes.py:47` | The notes for this meeting | modal title | no | `minutes_edit_modal_title` | 2 |
| `black_bloc/cogs/community/minutes.py:49` | No notes were written for this one. | ephemeral answer | no | `minutes_not_written_yet` | 2 |
| `black_bloc/cogs/community/minutes.py:50` | Notes and announcements will go to {where} from now on. | ephemeral answer | no | `minutes_channel_set` | 2 |
| `black_bloc/minutes.py:52` | by hand | ephemeral answer | no | `minutes_by_hand` | 2 |
| `black_bloc/minutes.py:53` | everyone left | ephemeral answer | no | `minutes_by_empty` | 2 |
| `black_bloc/minutes.py:55` | it ran past the longest a meeting may run | ephemeral answer | no | `minutes_by_max_hours` | 2 |
| `black_bloc/minutes.py:56` | the bot was restarted | ephemeral answer | no | `minutes_by_shutdown` | 2 |
| `black_bloc/minutes.py:71` | stop notes | ephemeral answer | no | `minutes_stop_phrase` | 2 |
| `black_bloc/minutes.py:82` | No meeting has been recorded here yet. | ephemeral answer | no | `minutes_panel_empty` | 2 |
| `black_bloc/minutes.py:92` | Meeting minutes are turned off for this server, so nothing was done. This is a p… | ephemeral answer | no | `minutes_minutes_off` | 2 |
| `black_bloc/minutes.py:97` | You are not in a voice channel, so there is no meeting for Black Bloc to join. J… | ephemeral answer | no | `minutes_not_in_voice` | 2 |
| `black_bloc/minutes.py:101` | Black Bloc is already taking notes in {where}, and it can only be in one meeting… | ephemeral answer | no | `minutes_already_running` | 2 |
| `black_bloc/minutes.py:105` | {names} {is_are} in that channel wearing a role that says do not record me, so B… | ephemeral answer | no | `minutes_opt_out_present` | 2 |
| `black_bloc/minutes.py:111` | There is no speech-to-text key on this host, so Black Bloc cannot turn a meeting… | ephemeral answer | no | `minutes_no_transcriber` | 2 |
| `black_bloc/minutes.py:116` | There is no writing key on this host, so the transcript was kept but no notes we… | ephemeral answer | no | `minutes_no_notes_writer` | 2 |
| `black_bloc/minutes.py:121` | Black Bloc is not allowed to join **{where}**, so nothing was recorded. It needs… | ephemeral answer | no | `minutes_cannot_connect` | 2 |
| `black_bloc/minutes.py:126` | Black Bloc could not join **{where}**: {reason}. That is a fault between the bot… | ephemeral answer | no | `minutes_join_broke` | 2 |
| `black_bloc/minutes.py:131` | No meeting is being recorded right now, so there was nothing to stop. Press **St… | ephemeral answer | no | `minutes_no_meeting_running` | 2 |
| `black_bloc/minutes.py:135` | There is no meeting **#{meeting_id}** on this server, so nothing was done. It ma… | ephemeral answer | no | `minutes_no_such_meeting` | 2 |
| `black_bloc/minutes.py:139` | Meeting **#{meeting_id}** is still being recorded, so there are no notes to work… | ephemeral answer | no | `minutes_still_recording` | 2 |
| `black_bloc/minutes.py:143` | Nobody said anything Black Bloc could make out, so there is no transcript and no… | ephemeral answer | no | `minutes_nothing_heard` | 2 |
| `black_bloc/minutes.py:147` | The transcript was kept but the notes could not be written: {reason}. Nothing is… | ephemeral answer | no | `minutes_notes_broke` | 2 |
| `black_bloc/minutes.py:152` | There is nowhere to put these notes: this meeting's channel has no text chat Bla… | ephemeral answer | no | `minutes_no_where_to_post` | 2 |
| `black_bloc/minutes.py:157` | Discord would not take that post, so the notes are still only on the site: {reas… | ephemeral answer | no | `minutes_post_broke` | 2 |
| `black_bloc/minutes.py:161` | Notes hold {limit} characters and those are {count}, so nothing was saved. Take … | ephemeral answer | no | `minutes_notes_too_long` | 2 |
| `black_bloc/minutes.py:165` | Notes cannot be empty, so nothing was saved. Write something, or press **Delete*… | ephemeral answer | no | `minutes_notes_are_blank` | 2 |
| `black_bloc/minutes.py:169` | Black Bloc is in test mode, so what it would post in {wanted} goes to {landed} i… | ephemeral answer | no | `minutes_test_mode_lands` | 2 |
| `black_bloc/minutes.py:172` | Black Bloc is in test mode and there is nowhere it is allowed to speak, so the a… | ephemeral answer | no | `minutes_test_mode_nowhere` | 2 |
| `black_bloc/minutes.py:176` | Recording **{where}**. Say **stop notes** in the voice chat or press **Stop** he… | ephemeral answer | no | `minutes_started_said` | 2 |
| `black_bloc/minutes.py:180` | Stopped recording {where}. Writing the notes now… | ephemeral answer | no | `minutes_stopped_said` | 2 |
| `black_bloc/minutes.py:181` | Notes written for meeting **#{meeting_id}**. | ephemeral answer | no | `minutes_notes_said` | 2 |
| `black_bloc/minutes.py:182` | Posted the notes for meeting **#{meeting_id}** in {where}. | ephemeral answer | no | `minutes_posted_said` | 2 |
| `black_bloc/minutes.py:183` | Saved the notes for meeting **#{meeting_id}**. | ephemeral answer | no | `minutes_edited_said` | 2 |
| `black_bloc/minutes.py:184` | Deleted meeting **#{meeting_id}** — the notes and the transcript went with it. | ephemeral answer | no | `minutes_deleted_said` | 2 |
| `black_bloc/minutes.py:185` | Meeting minutes are now **{mode}**. | ephemeral answer | no | `minutes_mode_said` | 2 |
| `black_bloc/minutes_audio.py:30` | The voice-recording extension is not installed on this host, so the bot cannot l… | ephemeral answer | no | `minutes_no_extension` | 2 |
| `black_bloc/minutes_audio.py:35` | The Opus audio library is not loaded on this host, so the bot cannot decode what… | ephemeral answer | no | `minutes_no_opus` | 2 |

### boot status / presence

*11 strings — 4 keyed · 0 unkeyed pass 1 · 10 unkeyed pass 2 · 1 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/presence.py:11` | *(the key's value)* | read from the store at render | **yes → `boot_status_text`** (ns `core`, 2 read site(s)) | — | 1 |
| `black_bloc/cogs/presence.py:18` | *(the key's value)* | read from the store at render | **yes → `bot_bio`** (ns `core`, 6 read site(s)) | — | 1 |
| `black_bloc/presence.py:12` | *(the key's value)* | read from the store at render | **yes → `shutdown_status_text`** (ns `core`, 2 read site(s)) | — | 1 |
| `black_bloc/presence.py:66` | *(the key's value)* | read from the store at render | **yes → `status_prefix`** (ns `core`, 2 read site(s)) | — | 1 |
| `black_bloc/cogs/presence.py:18` | Black Bloc's **About Me** now says what `bot_bio` says. | ephemeral answer | no | `boot_status_bio_changed` | 2 |
| `black_bloc/cogs/presence.py:19` | Black Bloc's **About Me** already said what `bot_bio` says, so it was left alone… | ephemeral answer | no | `boot_status_bio_same` | 2 |
| `black_bloc/cogs/presence.py:20` | Its status now reads `{text}`. | ephemeral answer | no | `boot_status_status_set` | 2 |
| `black_bloc/cogs/presence.py:21` | Its status could not be set, so it still reads whatever it read before — the rea… | ephemeral answer | no | `boot_status_status_failed` | 2 |
| `black_bloc/presence.py:20` | presence: no server in the cache yet, so the status and the About Me were left a… | ephemeral answer | no | `boot_status_no_guild` | 2 |
| `black_bloc/presence.py:21` | presence: server %s has no member count yet, so the status was left alone | ephemeral answer | no | `boot_status_no_count` | 2 |
| `black_bloc/presence.py:22` | presence: bot_bio is empty, so the About Me was left alone rather than wiped | ephemeral answer | no | `boot_status_no_bio` | 2 |
| `black_bloc/presence.py:23` | presence: Discord would not take the About Me, so it still says whatever it said… | ephemeral answer | no | `boot_status_bio_refused` | 2 |
| `black_bloc/presence.py:27` | presence: the shutdown status was not set — %s: %s | ephemeral answer | no | `boot_status_boot_refused` | 2 |
| `black_bloc/presence.py:28` | presence: the boot status could not be cleared — %s: %s | ephemeral answer | no | `boot_status_green_refused` | 2 |

### errors

*4 strings — 3 keyed · 0 unkeyed pass 1 · 4 unkeyed pass 2 · 0 not member-facing (not listed).*

| file:line | the text | where it shows | keyed? | proposed key | pass |
|---|---|---|---|---|---|
| `black_bloc/command_errors.py:17` | *(the key's value)* | read from the store at render | **yes → `error_retry_expired`** (ns `core`, 2 read site(s)) | — | 1 |
| `black_bloc/command_errors.py:19` | *(the key's value)* | read from the store at render | **yes → `error_retry_label`** (ns `core`, 2 read site(s)) | — | 1 |
| `black_bloc/command_errors.py:229` | *(the key's value)* | read from the store at render | **yes → `error_sentence`** (ns `core`, 2 read site(s)) | — | 1 |
| `black_bloc/command_errors.py:33` | Black Bloc hit an error running that command; it has been logged. Try again, and… | ephemeral answer | no | `error_command_failed` | 2 |
| `black_bloc/command_errors.py:37` | that command | ephemeral answer | no | `error_that_command` | 2 |
| `black_bloc/errors.py:14` | black-bloc: Discord rejected DISCORD_TOKEN. Reset it in the Developer Portal (Bo… | ephemeral answer | no | `error_login_failure` | 2 |
| `black_bloc/errors.py:18` | black-bloc: the Members / Message Content / Presence intents are not enabled for… | ephemeral answer | no | `error_privileged_intents` | 2 |

---

## 4. Recommendations

### 4.1 The order to key features in

Biggest unkeyed pass-1 block first, which is the order measured in §1:

| # | Feature | unkeyed pass 1 | note |
|---|---|---:|---|
| 1 | **polls** | 102 | |
| 2 | **events** | 96 | |
| 3 | **modmail + front door** | 65 | |
| 4 | **core** | 60 | |
| 5 | **pings** | 48 | |

⚠️ **One deliberate exception to that order: do EVENTS first anyway.** It is second by size (96 vs
polls' 102 — a 6-string difference, inside this audit's own error bars), and it is the only feature
that already has a written, reviewed design for the work
([`posted-strings-events-design.md`](posted-strings-events-design.md), §A the split, §B two leftovers
bundled, §C the tests and sweeps). Keying polls first means writing that design over again for polls
and then again for events. Events is also where the rule was born (deviation 10 of the forum build,
§H-10 of the move build).

After events: **polls → modmail + front door → core → pings**. `core` is an odd one out — its 60 are
spread across `panels.py`, `guard.py`, `settings_panel.py`, `logs_panel.py`, `selftest*.py` and
`handoff.py`, so they are the words EVERY panel inherits (`Back`, `Logs`, `Refresh`, the timeout
footer, the capped-select placeholder). ⚠️ **Keying those ~20 shared ones is worth doing BEFORE any
feature**, because every feature table below repeats them; key `panels.py` once and the per-feature
counts all drop.

### 4.2 The `/settings` group select at its 25-cap — yes, it needs a one-line plan

Measured, not assumed: `len({namespace_of(k) for k in KEY_TYPES})` is **25**, and
`settings_panel.SELECT_LIMIT` is **25**. The group select is **exactly full**. There is already a
mechanical guard — `tests/test_settings_store.py:1441` asserts the count is 25 — so a 26th namespace
fails the suite rather than silently dropping a group off the select. Good.

The plan is therefore not a redesign, it is a naming rule the build must follow, because
`namespace_of` takes **everything before the first `_`** as the group:

| If a key is named… | its group would be | so instead |
|---|---|---|
| `requests_*` | a 26th group `requests` | use **`request_*`** (the existing group) |
| `polls_*` | a 26th group `polls` | use **`poll_*`** |
| `birthdays_*` | a 26th group `birthdays` | use **`birthday_*`** |
| `minutes_*` | a 26th group `minutes` | already handled — `NAMESPACE_OVERRIDE` puts it on `events` |
| `frontdoor_*` | a 26th group `frontdoor` | already handled — `NAMESPACE_OVERRIDE` puts it on `modmail` |
| `mod_*` | a 26th group `mod` | already handled — `NAMESPACE_OVERRIDE` puts it on `automod` |
| `error_*`, `boot_status_*`, `rehearsal_*`, `status_*`, `bot_*` | a 26th group each | add to **`CORE_KEYS`**, which sends them to `core` |

If a genuinely new group is ever needed, five of the 24 are singletons that could be folded onto a
neighbour through `NAMESPACE_OVERRIDE` to free a slot: `cost` (1 key), `emoji` (1), `hide` (1),
`memory` (1), `voice` (1), `logs` (2).
⚠️ ~~`event` vs `events` is a real trap — `event_panel_minutes` is in `event`, everything else in
`events`.~~ **Folded 2026-09-20** on branch `events-group`: both `event_panel_*` keys are
`NAMESPACE_OVERRIDE`'d onto `events`, the `event` group is gone and the count is **24**.

⚠️ **The cap that actually bites is the one INSIDE a group, and this audit will hit it hard.**
`editable_options` shows `found[:25]` and `needs_find(group)` is already true for `events` (37 keys),
`modmail` (33), `chat` (28) and `core` (25). Keying events' 96 pass-1 strings takes the `events`
group to ~133, of which the Discord select shows **25** — the rest reachable only through the
**Find a setting…** modal and the site. That is not a blocker (it degrades exactly as designed, with
`capped_placeholder` saying *"{shown} of {total} — the rest are on the site"*), but it means **the
site's Settings page, and each feature's own Wording card, become the real door** for these keys and
the Discord panel becomes a search box. Worth the owner knowing before 800 keys land.

### 4.3 Strings that should NOT be keyed, and why

| String family | Example | Why the code must own it |
|---|---|---|
| **`DynamicItem` custom-id templates** | `rolereq:(?P<request_id>[0-9]+):(?P<action>approve\|deny)`, `honeypot:ban:(?P<hit_id>[0-9]+)` | Discord matches an already-posted button against this pattern. Edit it and every button posted before the edit stops working, silently. Filtered out of the tables above. |
| **Log kinds** | `event.room_forgotten`, `youtube.live_seen` | The Logs page filters on them, `tests/test_logkinds.py` asserts the whole set by AST, and `LOG_LEVEL_COMMANDS` maps them. They are identifiers that happen to be strings. |
| **Discord audit-log `reason=`** | `Black Bloc request forum` | Not member-facing — it lands in the server audit log, is capped at 512 characters by Discord, and nobody reads it in a card. |
| **Slash-command names and descriptions** | `Your YouTube channel, and how uploads are announced` | Discord metadata, synced at boot and rate-limited. The bot does not POST them; editing one needs a command re-sync, which is the one thing `docs/info/gotchas.md` warns about. |
| **Enum VALUES** | `off` / `shadow` / `on`, `room` / `forum` | These are stored in `guild_settings` and compared in code. Key the LABEL (`MODE_LABELS["on"] = "on — a new upload is announced"`), never the value. |
| **Placeholder tokens** | `{title}`, `{duration}`, `{who}` | They are the contract between a key and its filler. A validator must refuse an unknown `{…}` at set time — the `events_moved_line` validator is the pattern. |
| **Channel / file / role name slugs** | `modmail-ticket-{ticket_id}.txt`, the tempvoice slug | Discord constrains the charset and length. Keyable, but only behind a validator — `tempvoice_name_template` already is one, so copy that shape rather than adding a bare text key. |
| **`selftest.py` / `selftest_panels.py` strings** | the self-test's own probe labels | The self-test asserts on its own wording; keying them lets a settings edit fail the boot check. |

