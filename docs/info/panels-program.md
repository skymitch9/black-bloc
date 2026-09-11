# Panels over slash commands — the program for the rest of the app

> **Audience:** the conductor (Fable), every design and build agent, the reviewer, the owner.
> **Status:** TRACKED · ⚠️ **COMPLETE.** Every wave has landed and all three forks in §6 are
> ANSWERED — the last of them, **F3 on `/settings`**, shipped as v84 on 2026-09-05 and took the
> `app_commands.Group` count to zero. The item moved WHOLE to [`DONE.md`](../DONE.md) on
> 2026-09-04 ("Panels over slash commands — the program"); this file stays as the record of what
> the program was and what it decided, not as work in flight.
> **Last verified: 2026-09-11 09:05** — docs-wide staleness pass, re-measured by import in a
> worktree of `main` at `1d090e5` (v108). **The program's end state HOLDS six days on:** the
> tree is still **29 top-level commands with ZERO `app_commands.Group`s**, still 18 of them
> opening a panel and 11 acting or answering a line, and the split has not moved since v84 —
> the five releases since (v100–v108, the When and Where pickers) all landed INSIDE panels,
> which is the program working as designed. **What that FIXED:** the registry-key figure this
> header and §3/§6 carry (**185 → 202**) and the namespace count (**22 → 23**). ⚠️ **NOT
> re-verified:** the other sixteen feature rows in §3, §2's pattern, and §4/§5, all of which
> are the record of earlier landings and were left as written; nothing here met Discord.
> Before that, **2026-09-05** — §3's Core row, its totals line and §6's F3 were re-measured
> against the tree at `aa03a01` (v87): `bot.tree.get_commands()` is **29 commands and ZERO
> `Group`s** (`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`), and
> `len(KEY_TYPES)` was **185**, not the "~120" F3 was asked with.

**The order, verbatim (owner, 2026-09-03):** *"Let's try and minimize slash commands and
maximize interactive windows"* → *"Let's start this process with request then carry it
through the rest of the app. Request first."* → after the panel shipped: *"do the change to
all / commands / I like how request works."*

**What that means for every feature:** ONE slash command opens an ephemeral panel (embed +
buttons + selects + modals). Every subcommand becomes a button, a select or a modal on that
panel. Members and staff get different panels from the same command. Nothing else changes —
the shared functions, the settings, the logs, the site, the channel cards all stay exactly
what they are; the panel is only a new front door onto them.

## 1. Why one document for the whole program

`/request` took four passes and a review that found three real defects (a replaced view's
timeout clock overwriting the live card; a "gone quiet" footer that could never be written
at 15 minutes; a staff check that only ran at render time). **Seventeen features each
re-implementing the same view would reproduce those three defects seventeen times.** So the
program has a wave 0 that turns the requests panel into a library every later panel
inherits from, and this document is the invariant list every per-feature design doc is
checked against. One canonical implementation (`review-checklist.md` item 17), one place
the rules live.

## 2. The pattern — what every panel MUST do (from `/request`, measured)

Every per-feature design doc restates nothing here; it links here and lists only what is
specific to its feature (the button table per state, the modals, the settings). A reviewer
checks the build against this list first.

| # | Invariant | Where `/request` does it |
|---|---|---|
| P1 | **One command, no subcommands.** A `Group` and a command cannot share a name in discord.py, so the group goes. `commands synced` is UNCHANGED by this (a group already counted as one top-level slot — deviation 7); what shrinks is the tree. Two or three groups for one feature (`/apply` + `/applications` + `/question`) collapse to ONE command, which DOES lower the synced count | `cogs/community/requests.py` `request` |
| P2 | **Ephemeral embed + `discord.ui.View`**, one message, re-rendered in place. Member and staff panels from the same command, split on `store.is_staff` | `build_panel(bot, guild, actor)` |
| P3 | **Buttons render ONLY when the move is valid** — from the state machine plus the guards the shared function applies, so the panel never offers what the function would refuse. Never a status menu with two spellings of one move. The table is DATA, and a parametrised test proves every state renders exactly its row | `CARD_BUTTONS` |
| P4 | **Every move calls the shared function that exists today**, `via` at its Discord default. The panel never writes a row, never logs a line itself — one write, one log row (checklist 34). If a subcommand's logic is inline in the cog, extracting it into the pure module is part of the build (as `withdraw_request` was) | `apply_decision`, `mark_ready`, `accept`, `send_back`, `resume_request`, `withdraw_request` |
| P5 | **Slow work after `defer()`, then `edit_original_response`** — a non-`thinking` defer on a component interaction is a `deferred_message_update` (deviation 1). Every click re-checks `db_ready` (deviation 6) | `open_card`, `finish_card` |
| P6 | **`retire(previous)` before every re-render** — sets `replaced = True` and `stop()`s the view being replaced, so its timeout clock cannot fire over the live card (deviation 9). ⚠️ Never guard with `is_finished()` — it is already True inside a genuine timeout | `retire`, `RequestView.replaced` |
| P7 | **Timeout writes the "gone quiet" footer through the last interaction**, falling back to `message.edit`, both wrapped (deviation 10). Default `<feature>_panel_minutes` = **10**; 15+ loses the footer (KI-20) and the key's help text says so | `interaction_check`, `on_timeout` |
| P8 | **Staff re-checked before EVERY staff move**, not only at render — `still_staff` + `answer()`; never `require_staff` after a defer (deviation 11) | `still_staff` |
| P9 | **Refusals in words, never a dead button.** A control someone may not use is NOT rendered and the embed says who it is for; off / db-down / staff-only gates as sentences | `PANEL_*` strings |

> ⚠️ **P9's "off" half is NARROWED, 2026-09-04** (owner: *"if we turn a feature off on the web
> portal … make the /youtube command not appear until it turns back on"*). With
> `hide_commands_when_off` at its default **true**, a mode-off feature's command is removed from
> the guild's tree, so **the mode-off panel is only reachable during the ≤60 s sync lag** between
> the portal write and Discord catching up. The other half of P9 is untouched and now matters
> more: `hide_commands_when_off` set **false** puts every command back permanently, and that is
> the posture in which "a mode-off panel still opens and says so" is the whole story. Nothing in
> a panel changed — no `PANEL_*` string was edited — but a design doc that says "the panel
> explains that the feature is off" should now say "…when the command is still reachable".
> The way back is `/settings set-value <feature>_mode on`; `settings` is in `NEVER_HIDDEN` and
> cannot itself be hidden. See `command_visibility.py` and the code-notes section
> **Hide commands when off**.
| P10 | **Selects cap at 25** (Discord's) with a placeholder "25 of N — the rest are on the site" where the site has the list | staff "Pick a request…" |
| P11 | **`Logs` is a button that answers a NEW ephemeral followup** so the panel stays; it calls the same `send_logs` the subcommand did (which carries its own `require_staff`) | `LogsButton` |
| P12 | **Modals share one shape**: `AnswersErrors` + `discord.ui.Modal`; a generic note modal whose label names what the note is for and who is sent it | `ReadyModal`, `NoteModal(kind)` |
| P13 | **Settings both ways (checklist 33)**: every decision the panel makes is a key with a type, help text and a `default()` branch — at minimum `<feature>_panel_minutes`. The 25 cap and the button table are not decisions | `request_panel_minutes`, `request_panel_own_list` |
| P14 | **Not persistent**: after a restart the buttons answer "This interaction failed" — accepted (KI-19 pattern). If a feature needs a POST that survives restarts (role menus, applications panel, pings' Streamers panel, tempvoice's control post) that is a persistent `DynamicItem`, a different thing, and it already exists — the ephemeral panel is for the caller, the post is for the room | KI-19 |
| P15 | **`/help` follows the tree** (`cogs/core.py`) — no edit needed; every doc naming a retired subcommand is rewritten in the same commit (`access/OWNER_GUIDE.md`, `access/sweeps.md`, `info/feature-list.md`, the phase doc gets a dated "superseded by the panel" line) | deviation list |
| P16 | **Tests mirror the package**: the cog test parametrises every state against the button table; the pure module tests the table and any extracted function; `test_settings_store.py` round-trips each new key; `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` and `LOGS_GROUPS` are updated for the groups that vanish | `tests/cogs/community/test_requests.py` |
| P17 | **§J before merge**: boot (`python -m black_bloc`) and read `commands synced`; ruff; full pytest; `node site/mock/check.mjs`; `labels.js` parse | every phase doc's §J |

## 3. The inventory — every command today (measured at `a392a3f`)

"Sub" counts subcommands; "Top" counts top-level commands (what `commands synced` counts).
The panel column is the SHAPE, not the design — the design doc decides the tables.

| Feature | Cog | Groups / top-level today | Sub | Top | Who | Panel shape |
|---|---|---|---|---|---|---|
| Requests | `community/requests.py` | `/request` | 0 | 1 | member + staff | ✅ shipped — the template |
| Events | `community/events.py` | `/event` | 0 | 1 | member + staff | ✅ **SHIPPED v64** (`e670542`, 2026-09-03 14:05; wave 1) — `/event` opens the panel; the `event` group and the whole `timezone` group are retired, so this is the program's first real `commands synced` drop (44 → 43). [`events-panel-design.md`](events-panel-design.md) |
| Polls | `community/polls.py` | `/poll` | 0 | 1 | member + staff | ✅ **SHIPPED v65** (`d13e1a4`, 2026-09-03 14:14; wave 1) — `/poll` opens the panel; the eleven subcommands are retired (the group was already one top-level, so no `commands synced` drop). [`polls-panel-design.md`](polls-panel-design.md) |
| Birthdays | `community/birthdays.py` | `/birthday` | 0 | 1 | member + staff | ✅ **SHIPPED v63** (2026-09-03 13:58; wave 1) — `/birthday` opens the panel; the twelve subcommands are retired (no `commands synced` drop). [`birthdays-panel-design.md`](birthdays-panel-design.md) |
| Applications | `community/applications.py` | `/apply` | 0 | 1 | member + staff | ✅ **SHIPPED v66** (`853776c`, 2026-09-03 15:00; wave 1 COMPLETE) — `/apply` opens the panel; BOTH groups and all seventeen subcommands are retired, so this is the program's second real `commands synced` drop (43 → 42). [`applications-panel-design.md`](applications-panel-design.md) |
| Role menus | `community/role_menus.py` | `/rolemenu` | 0 | 1 | staff | ✅ **BUILT — wave 3**, 2026-09-04, branch `worktree-agent-ace2086f9f7cfa541`; `/rolemenu` opens the panel and BOTH the `rolemenu` and `role` groups and all **eighteen** leaf subcommands are retired, so `commands synced` really drops — **37, measured** through `test_the_command_tree_stays_inside_discords_limits` (was 38). `HIDDEN_WHEN_OFF["rolemenu_mode"]` is deleted: the mode ships **off**, so hiding `/rolemenu` would hide the only Discord way to turn it back on. Owner forks: **F-R1 = (a)** the pending-requests queue is built into the panel; **F-R2 = (a)** a grant may have no end date (0 days), matching the website, plus his amendment — **Grants… opens as an AUDIT** of every active timed role, soonest first; **F-R3 = (a)** an edit that changes what a posted panel says refreshes that panel in place. Nine routes lose their `note()` and pass `via=VIA_WEBSITE`; `grant`/`extend` had two divergent implementations and are now one. [`role-menus-panel-design.md`](role-menus-panel-design.md) |
| Temp voice | `community/tempvoice.py` | `/voice` | 0 | 1 | member + staff | ✅ **SHIPPED v73 `4d64b36`** 2026-09-03 22:08 (built on `worktree-agent-a386d425f5527fe95`); `/voice` opens the panel and BOTH groups and all twenty-two subcommands are retired, so the top-level count drops by one (**38, measured** through `test_the_command_tree_stays_inside_discords_limits`). Owner fork **F1 = (a)**: the per-channel control post is left exactly as it is, a second door onto the same `do_*` functions. Staff bypass the allowed-role gate and can hand ANY open channel to somebody else, with a DM to the displaced owner. [`voice-panel-design.md`](voice-panel-design.md) |
| Go-live / Twitch | `content/golive.py` | `/golive` | 0 | 1 | member + staff | ✅ **BUILT** (wave 2, 2026-09-03, `worktree-agent-a87a00d41b8dc47d1`) — `/golive` opens the panel; the `golive` and `twitch` groups and all eight subcommands are retired, so this is a real `commands synced` drop (42 → 41, measured). [`golive-panel-design.md`](golive-panel-design.md) |
| Ping roles | `content/pings.py` | `/pings` | 0 | 1 | member + staff | ✅ **BUILT — wave 2**, 2026-09-03, branch `worktree-agent-a86e71fd801362ca2`; `/pings` opens the panel and BOTH groups and all twelve leaf subcommands are retired, so `commands synced` drops by one (**39**, measured through `test_the_command_tree_stays_inside_discords_limits`). Owner forks: **I1 = (a)** — *Take my ping role away* always renders when the member has an own row; **I2 = (b)** — one Events toggle while `golive_ping_role_id` and `events_ping_role_id` agree, two labelled ones once they differ. **Stop following… is deliberately NOT mode-gated** — the access-REDUCING move fails safe. [`pings-panel-design.md`](pings-panel-design.md) |
| YouTube | `content/youtube.py` | `/youtube` | 0 | 1 | member + staff | ✅ **SHIPPED — wave 2**, 2026-09-03, branch `worktree-agent-a74823f4d9293d080`; `/youtube` opens the panel and BOTH groups and all nine subcommands are retired, so `commands synced` drops by one (**41, measured**). The mode select sits on the ROOT, not inside Setup, because turning the feature on is why a Lead opens it. Owner forks: **F-Y1 = keep `/youtube` and `/golive` separate**; **F-Y2 = flip `youtube_mode` to shadow at landing**, which is operational, not a build change. [`youtube-panel-design.md`](youtube-panel-design.md) |
| Raid trains | `content/raidtrain.py` | `/raidtrain` | 0 | 1 | member + organizer + staff | ✅ **BUILT — wave 3**, 2026-09-04, branch `worktree-agent-aba5d44f8e27a8e28`; `/raidtrain` opens the panel and BOTH groups and all fifteen leaf subcommands are retired, so the top-level count drops by one (**37, measured** through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`). Owner forks: **F-R1 = (a)** the lineup post stays text-only; **F-R2 = (a)** upcoming only, the Events page owns history; **F-R3 = (a)** the `Take an hour…` select alone, no second one-click button. `/raidtrain` stays visible with the mode **off** because the `Mode…` select is now the only door back to `on`. The six website routes' `note()` calls are gone — they call the shared functions with `via`, and `POST /status status=cancelled` writes `web.raidtrain.cancel` for the first time. [`raidtrain-panel-design.md`](raidtrain-panel-design.md) |
| Chat | `content/chat.py` | `/chat` | 0 | 1 | staff | ✅ **BUILT — wave 3**, 2026-09-04, branch `worktree-agent-ab33797d235cf0d96`; `/chat` opens the panel and the `chat` group, both nested groups and all nine leaf subcommands are retired. `commands synced` does **not** move (a group was already one slot — **38, measured** through `test_the_command_tree_stays_inside_discords_limits`). Owner forks: **F-C1 = (a)** read-only settings plus one `Limits…` modal for the five numbers; **F-C2 = (a)** `Edit…` on the note card; **F-C3 = (a)** one click to turn the models on, no confirm; **F-C4 = (a)** both mood-pool guards on both doors, implemented once in `black_bloc/chat_panel.py`. The five website `note()` calls are gone — the routes call the shared functions with `via`. [`chat-panel-design.md`](chat-panel-design.md) |
| Chat memory | `content/chat_memory.py` | `/memory` | 0 | 1 | member | ✅ **SHIPPED — wave 2**, 2026-09-03, branch `worktree-agent-aaaa13e778f0ba65a`; `/memory` opens the panel and the five subcommands are retired. `commands synced` does NOT move (the group was already one slot — **42, measured**). Member-only: no staff row, no Logs, no site link (D5 makes the site staff-only and counts-only, so a link would 403). Owner fork **I-M1** = open it — `HIDDEN_WHEN_OFF["chat_memory_mode"]` is gone and the panel says memory is off as a LINE. [`memory-panel-design.md`](memory-panel-design.md) |
| Automod | `moderation/automod.py` | `/automod` | 0 | 1 | staff | ✅ **BUILT — wave 3**, 2026-09-04, branch `worktree-agent-ae7bb4ba9c5540ad4`; `/automod` opens the panel and the `automod`, `rule` and `exempt` groups and all eight leaf subcommands are retired. `commands synced` does **NOT** move (a group was already one slot — **38, measured** through `test_the_command_tree_stays_inside_discords_limits`). Owner forks: **F-A1 = (a)** — arming asks *Are you sure?* first, behind `automod_arm_needs_confirm` (default true); every quieter move is one press. **F-A2 = (a)** — one prefilled paragraph modal for `bad_words`, one word per line, and `_as_words` learned to split on newlines so the modal and the site's textarea agree. **F-A3 = (a)** — no controls for `automod_warn_threshold` / `mod_dm_on_action`; they are read-only lines on the Settings sub-panel naming the Moderation page. The enforcement path is byte-identical by AST. [`automod-panel-design.md`](automod-panel-design.md) |
| Honeypot | `moderation/honeypot.py` | `/honeypot` | 0 | 1 | staff | ✅ **SHIPPED — wave 3**, 2026-09-05 as v79 (`361eaa2`), branch `worktree-agent-a7ea6b0dbeac7f753`; `/honeypot` opens the panel and the `honeypot` and `exempt` groups and all **seven** leaf subcommands are retired. `commands synced` does **NOT** move (a group was already one slot — **36, measured** through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`). Owner forks: **F-H1 = (a)** — the `RoleSelect` at `min_values=0` PLUS an **Exempt nobody** button, because whether a client submits an empty multi-select is unproven and the exempt list IS the select. **F-H2 = (a)** — **Forget…** opens a card with a picker over every recorded id, one Discord no longer has labelled as such. **F-H3 = (a)** — `honeypot_purge_days` gets a second field on the Settings `Numbers…` modal. `honeypot.exempt_add`/`exempt_remove` are retired for one `honeypot.exempt_set` carrying the added/removed diff; `honeypot.settings` is new. The catching path is untouched. One key: `honeypot_panel_minutes`. [`honeypot-panel-design.md`](honeypot-panel-design.md) |
| Modmail | `moderation/modmail.py` | `/modmail`, top-level `/reply`, `/areply`, `/note`, `/close` | 0 | 5 | staff, in-thread | ✅ **BUILT — wave 4 (Build A)**, 2026-09-05, branch `worktree-agent-afdd9e23bbaf59be8`; `/modmail` opens the panel and BOTH the `modmail` and `snippet` groups and all eleven leaf subcommands are retired, so the top-level count really drops — **36 → 35, measured** through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`. The panel is the root status card + `Setup…` (the three places, the mode, one Answer-DMs button that names its own effect), `Blocked…` (list → pick → Unblock; Block via a `UserSelect` + reason modal), `Snippets…` (list → pick → Remove/Change; Add modal), `Forget…`, `Logs` and the site link. `/modmail` is never hidden by `hide_commands_when_off` (`modmail_mode` has no `off`, and the switch is the bool `modmail_enabled`). Five website routes lose their `note()` and pass `via=VIA_WEBSITE`, four log kinds are renamed so the two doors agree, and a Discord reply writes a `modmail.reply` row for the first time. ⚠️ **Fork F2 answered in full by Build B**, 2026-09-05, branch `worktree-agent-a4bebd98196e3ca14` (**NOT merged, NOT deployed**): the sticky ticket card (a persistent `DynamicItem` carrying **Reply · Reply as Staff · Private note · Close…**, bumped to the bottom on every write, reconciled after a restart), schema **29 → 30** (`card_message_id`, `practice`), `modmail_reply_style` gating the typed relay, the practice ticket, and the retirement of `/areply` `/note` `/close` — **33 → 30, measured**. `/reply` survives with its `ticket:` (fork F-M5). [`modmail-panel-design.md`](modmail-panel-design.md) |
| Mod commands | `moderation/modcmds.py` | `/mod [member]` + the seven bare actions `/warn`, `/timeout`, `/untimeout`, `/kick`, `/ban`, `/unban`, `/purge` | 0 | 8 | staff | ✅ **BUILT — wave 4**, 2026-09-05, branch `worktree-agent-ab5740f777a3dfd80`; `/mod [member]` opens a panel over the case record and `/case`, `/cases` and the `mod` group's `logs` child are all retired — `commands synced` **36 → 34 on its branch, 35 → 33 on `main` after modmail A, measured** through `test_the_command_tree_stays_inside_discords_limits`. ⚠️ **Fork F1 is ANSWERED, not open: the seven bare actions STAY BARE** (owner, 2026-09-04, proposal 3 of 6 — "typed mid-incident with autocompleted arguments; a panel would be three clicks slower at the wrong moment"), so no member card with Warn/Timeout/Kick/Ban was built. The panel's own additions are the four corrections a case never had — edit its reason, note it, void it, restore it — behind schema **29** (`mod_cases` gains six nullable columns), through four shared functions that both Discord and four new API routes call with `via`. Owner forks: **F-M1 = (a)** voided cases stay in the list, struck through; **F-M2 = (a)** a voided warn stops counting toward `automod_warn_threshold`; **F-M3 = (a)** the website gets the four moves in the same build. `/mod` is never hidden — moderation has no mode key. [`mod-panel-design.md`](mod-panel-design.md) |
| Core | `core.py` | `/ping`, `/about`, `/help`, `/settings` | 0 | 4 | anyone / staff | ✅ **SHIPPED — wave 4**, 2026-09-05 as **v84** (`ce97de0`); `/settings` opens the panel and its five subcommands AND the whole `presence` group are retired, taking the top-level count **30 → 29** and the `app_commands.Group` count to **ZERO**. Fork **F3 = the paged panel**: **A setting group…** over the namespaces (22 at the landing; **23** measured 2026-09-11), **Find a setting…** within one, so every key is reachable through 25-option selects (**185** at the landing; **202** measured 2026-09-11). `/ping` `/about` `/help` stay as they were. [`settings-panel-design.md`](settings-panel-design.md) |

**Totals today, measured 2026-09-05 at `aa03a01` (v87):** **ZERO subcommands, zero
`app_commands.Group`s, and 29 top-level commands** — 18 of them open a panel, the other eleven
take an argument and act (`/ban`, `/warn`, `/timeout`, `/untimeout`, `/kick`, `/unban`,
`/purge`, `/reply`) or answer one line (`/ping`, `/about`, `/help`). ⚠️ **This line used to read
"~177 subcommands over 44 top-level commands"; that was the figure the program started from.**
The program's own estimate of where it would land ("~21 top-level") was low, because it counted
one slot per feature and the seven bare moderation actions plus `/reply` were kept deliberately
(fork F1). Discord's cap is 100 top-level; the gain was for people, not the limit.

## 4. Wave 0 — the library the template becomes (build first, alone)

**BUILT** — 2026-09-03, branch `feat/panels-library`, commits `5da0081` (library + cog
refactor + `tests/test_panels.py`) and the docs commit that follows it. **3371 tests pass**
(1127 `tests/cogs` + 2244 the rest — 3345 before, +26 new, none lost), ruff clean, and
`import black_bloc.cogs.community.requests, black_bloc.panels` succeeds. The 163 requests
tests passed **unchanged in assertion**, which is the proof the refactor changed nothing.
⚠️ A real boot (`python -m black_bloc`, invariant P17) was NOT run — the build agent has no
bot token; the import check is the substitute. See `### Wave 0 deviations` at the foot of
this section.

**`black_bloc/panels.py`** (pure module; tests in `tests/test_panels.py`) extracted from
`cogs/community/requests.py` with NO behaviour change — the requests tests stay green
untouched except for import paths:

| Piece | From |
|---|---|
| `class Panel(discord.ui.View)` — `replaced`, `last_interaction`, `interaction_check` recording it, `on_timeout` writing the gone-quiet footer through the last interaction then `message.edit`, both wrapped | `RequestView` |
| `retire(previous)` | module-level in the cog |
| `still_staff(interaction)`, `answer(interaction, text)`, `db_ready(interaction)` | the cog's helpers |
| `NoteModal(kind, on_submit)` — one paragraph field, label names the purpose and the recipient | `NoteModal` |
| `panel_minutes(store, guild_id, key)`, `option_label(id, status_words, text)` (the 100-char clamp), `capped_placeholder(shown, total)` | `requests.py` helpers |
| `PANEL_GONE_QUIET`, the footer sentence, parametrised on the command name | `requests.py` strings |

`/request` is then refactored to subclass `Panel` and call the library — the diff should be
mostly deletions. **Proof:** 3345 tests still pass (count may rise by the library's own),
`ruff`, boot. This wave is one Opus agent; nothing else runs beside it because every later
wave imports it.

### Wave 0 deviations

Written by the build agent, 2026-09-03. Everything not listed here was built as the table
above says.

1. **The gone-quiet footer is a constructor argument, not a `PANEL_GONE_QUIET` constant
   "parametrised on the command name".** The table's last row asked for a shared sentence
   with the command name substituted in; `Panel(minutes, *, footer)` takes the whole
   sentence instead. Two reasons: `requests.PANEL_TIMEOUT_FOOTER` stays exactly the string
   it is today (so no requests test moved), and a feature whose panel is not named after
   its command (`/voice` renders a channel card, `/pings` a notifications card) can say
   something that reads correctly rather than something a format string produced. The cost
   is one string per feature; the invariant P7 wording ("writes the gone-quiet footer
   through the last interaction") is untouched.
2. **`option_label(id, status_words, text)` was NOT extracted.** The table lists it; the
   build brief's piece list does not, and `requests.option_label` reads `row_value`,
   `STATUS_WORDS` and `SELECT_OPTION_LIMIT` — a request row's shape, not a panel's. The
   100-character clamp it exists for is `clamp`, which is already shared. Left for the
   first feature wave that actually needs a second copy of it, which is when its generic
   signature will be knowable rather than guessed.
3. **`CAPPED_PLACEHOLDER` is a named module constant, so it can be the default AND be read
   by name.** The brief spelled `capped_placeholder`'s default as an inline literal; a
   literal cannot also be what `requests.PICK_CAPPED` reads, and the brief asks for exactly
   that ("so the sentence has ONE home"). Same value, one name.
4. **No requests test was MOVED into `tests/test_panels.py`.** The brief permitted it. Not
   moving them means every one of the 163 stayed green *unchanged in assertion*, which is
   the strongest available proof the refactor changed nothing — and the requests copies now
   double as the integration test of the subclasses (`RequestView(Panel)`, the thin
   `NoteModal`) that the library's own tests cannot give. 26 tests were ADDED for the
   library on its own; nothing is tested only through the cog.
5. **`python -m black_bloc` (invariant P17) was not run** — no bot token in the build
   environment. `python -c "import black_bloc.cogs.community.requests, black_bloc.panels"`
   was run instead and passes; the import edge this wave adds (`requests` → `panels` →
   `settings_store`) is what a boot would have caught, and it is clean. `node
   site/mock/check.mjs` and the `labels.js` parse were not run either: the site is
   untouched by this wave.

### What the library gained after wave 0

Wave 0 shipped the pieces in the table above. Two more were added on **2026-09-05**, by the
confirm/opened fold — both are things seventeen panels had each re-implemented, which is the
same argument §1 makes for the library existing at all:

| Piece | What it replaced |
|---|---|
| `confirm(interaction, view, embed, items, previous, *, question, title)` plus `confirm_items(...)` and `ConfirmButton` | **Eight** hand-built Keep it / Yes cards (`/memory`, `/birthday` ×3, `/youtube`, `/pings` ×2, `/automod`, `/chat`, `/rolemenu` ×3, `/voice`) and the twelve one-off Button subclasses under them. `items` stays a parameter so automod and role menus keep drawing their confirm from their own move table (P3); `question` is optional because three cards put the question in the embed rather than in a field |
| `opened(interaction, *, staff=True)` | The `still_staff` → `defer` → `db_ready` triplet: five cogs' identical `opened`, `role_menus.ready` (the same function renamed) and **fourteen** inline repeats in `cogs/content/chat.py`. `staff=False` covers the panels that open for members (`/raidtrain`, `/memory`) |

⚠️ **`/event`, `/request` and `/apply`'s confirm cards were deliberately left out** — they edit
without `allowed_mentions`, so folding them would have changed behaviour inside a refactor. See
the `Confirm/opened fold` section of `code-notes.md`.

## 5. Waves — proposed sequence (the owner picks; one feature at a time where a fork exists)

Parallel agents in worktrees, three or four per wave, each on ONE feature. Shared files
(`settings_store.py` registry, `code-notes.md`, `sweeps.md`, `feature-list.md`,
`OWNER_GUIDE.md`, `tests/test_bot.py`) are **append-only in the feature's own block** so
merges are textual; the conductor merges in wave order, re-keys `code-notes.md` after each
merge, and deploys per wave, not per feature.

| Wave | Features | Why together |
|---|---|---|
| 0 | the library (§4) | everything imports it |
| 1 | events · polls · birthdays · applications | community, the owner's stated priority; applications folds three groups into one; all four have a clean list → pick → card shape |
| 2 | voice · pings · golive/twitch · youtube · memory | member-facing self-service panels; each folds two or more groups |
| 3 | raidtrain · role menus · chat · automod | staff/organizer panels with the most sub-panels (questions, grants, rules) |
| 4 | modmail · honeypot · mod commands · settings | the three forks in §6 live here — decided before the wave is briefed, not during |

**Per feature, the ritual:** an Opus **Plan** agent writes `info/<feature>-panel-design.md`
(button table per state, modals, settings, what goes away, tests, §J — nothing that §2
already says) → Fable reviews it against §2 and the feature's existing phase doc → owner sees
only the genuine forks → Opus **build** in a worktree with the design doc + `review-checklist.md`
+ this file in the brief → Fable review → merge → re-key → sweep rows → `DONE.md` entry with
the deviations foot.

**Cost calibration (measured on `/request`):** the fourth-pass build was one subsystem at
~280k Opus tokens; the own-list follow-up 152k. Budget ~250k per feature build, ~60k per
design doc. Read usage before every dispatch and after every landing; the project's 90 %
weekly cut-off stands.

## 6. The forks — owner decisions, one at a time, before wave 4

- ✅ **F1 — mod commands. ANSWERED by the owner, 2026-09-04 (proposal 3 of 6): the seven bare
  actions STAY BARE.** *"Typed mid-incident with autocompleted arguments; a panel would be three
  clicks slower at the wrong moment."* `/mod [member]` opens a panel over the case RECORD only
  (built 2026-09-05, wave 4); `/warn`, `/timeout`, `/untimeout`, `/kick`, `/ban`, `/unban` and
  `/purge` are untouched, and the panel's footer names them so a moderator who opened `/mod` to
  punish somebody is told where that lives. The user context-menu shape was not built and is not
  asked for. The original question, for the record: `/warn @user reason` is one line typed; the
  panel would have been UserSelect → card → button → modal (four clicks).
- **F2 — modmail's in-thread `/reply` `/areply` `/note` `/close`.** ✅ **Decided
  (owner, 2026-09-05): BOTH.** *"we do the both … buttons always appear to click reply at
  the bottom of a channel but also a /reply so they can just start typing a response"* —
  `/reply` stays a typed command, and the other three retire into a sticky card on the
  ticket. **Build A (2026-09-05) left all four alone; Build B (2026-09-05, branch
  `worktree-agent-a4bebd98196e3ca14`, NOT merged) built the card and retired the three** —
  `33 → 30, measured` ([`modmail-panel-design.md`](modmail-panel-design.md) §J).
- **F3 — `/settings`.** ✅ **Decided and BUILT — the paged panel** (wave 4, 2026-09-05, live as
  **v84**; [`settings-panel-design.md`](settings-panel-design.md)). The Discord path was neither
  retired nor left as a group: `/settings` opens a panel whose **A setting group…** select walks
  the namespaces (22 then, **23** on 2026-09-11) and whose **Find a setting…** modal filters within one, so all keys
  are reachable through a 25-option select without paging. `show`, `set`, `set-role`, `set-value`
  and `clear` are retired with it, and so is the whole `presence` group — the last two
  `app_commands.Group`s in the tree. The question's premise ("~120 keys") was stale even when it
  was asked; the figure was **185** at the landing, counted off `KEY_TYPES`, and is **202** as of
  2026-09-11.

## 7. What this program does NOT touch

Persistent posts (role-menu posts, the applications panel post, the pings Streamers panels,
lineup posts, poll messages) — those are `DynamicItem` views that survive restarts and
belong to the room, not the caller. The site. The shared functions and their logs. The
settings keys that exist. Test mode.
