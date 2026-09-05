# Panels over slash commands — the program for the rest of the app

> **Audience:** the conductor (Fable), every design and build agent, the reviewer, the owner.
> **Status:** TRACKED · **PLANNING**, except **§4 wave 0, which is SHIPPED** (`black_bloc/panels.py`,
> `feat/panels-library` → `main` `1861923`, 2026-09-03 ~11:50, Fable-reviewed: no defect, five
> deviations all accepted; live in release v60 at 11:39, `deploys.log` line 59). Waves 1–4 are unbuilt; the template is
> `/request` ([`requests-panel-design.md`](requests-panel-design.md)).
> **Last verified: 2026-09-03** — §4's BUILT line was measured on `feat/panels-library`
> (3371 tests, ruff clean, import check); the command inventory in §3 was measured by grep
> against `black_bloc/cogs/` at `a392a3f` (one row per `app_commands.Group` /
> `@<group>.command`) and is unchanged by wave 0, which added no command and retired none;
> the pattern in §2 was read out of `requests-panel-design.md` and its twelve deviations.
> ⚠️ **NOT verified:** which features the owner wants first (§5 is a proposal), and the
> three forks in §6, which are his to decide one at a time.

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
| Honeypot | `moderation/honeypot.py` | `/honeypot` | 0 | 1 | staff | ✅ **BUILT — wave 3**, 2026-09-05, branch `worktree-agent-a7ea6b0dbeac7f753`; `/honeypot` opens the panel and the `honeypot` and `exempt` groups and all **seven** leaf subcommands are retired. `commands synced` does **NOT** move (a group was already one slot — **36, measured** through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`). Owner forks: **F-H1 = (a)** — the `RoleSelect` at `min_values=0` PLUS an **Exempt nobody** button, because whether a client submits an empty multi-select is unproven and the exempt list IS the select. **F-H2 = (a)** — **Forget…** opens a card with a picker over every recorded id, one Discord no longer has labelled as such. **F-H3 = (a)** — `honeypot_purge_days` gets a second field on the Settings `Numbers…` modal. `honeypot.exempt_add`/`exempt_remove` are retired for one `honeypot.exempt_set` carrying the added/removed diff; `honeypot.settings` is new. The catching path is untouched. One key: `honeypot_panel_minutes`. [`honeypot-panel-design.md`](honeypot-panel-design.md) |
| Modmail | `moderation/modmail.py` | `/modmail` (logs, block, unblock, blocked, mode, forget, status, settings), `/snippet` (add, remove, list), top-level `/reply`, `/areply`, `/note`, `/close` | 11 | 6 | staff, in-thread | `/modmail`: Status card (Mode, Forget, Settings); Blocked (list → pick → Unblock; Block via UserSelect + reason modal); Snippets (list → pick → Remove; Add modal); Logs. ⚠️ **Fork F2** on the four in-thread commands |
| Mod commands | `moderation/modcmds.py` | `/mod` (logs), top-level `/warn`, `/timeout`, `/untimeout`, `/kick`, `/ban`, `/unban`, `/purge`, `/case`, `/cases` | 1 | 10 | staff | `/mod`: UserSelect → member card (Warn/Timeout/Kick/Ban via reason modal, Cases for them); Cases (pick → card); Purge modal; Logs. ⚠️ **Fork F1** on the direct commands |
| Core | `core.py` | `/ping`, `/about`, `/help`, `/settings` (show, set, set-role, set-value, clear), `/presence` (1) | 6 | 5 | anyone / staff | `/ping` `/about` `/help` stay. ⚠️ **Fork F3** on `/settings` |

**Totals today:** ~177 subcommands (nested groups like `poll recur` and `automod rule`
counted inside their parent) over the 44 top-level commands `commands synced` reports.
⚠️ **The honeypot row above is now 0 / 1** — the panel build retired its **seven** leaf
subcommands (2026-09-05), so the surviving subcommand total is seven lower than this line's
figure and the top-level count is unchanged at **36, measured**.
**After the program**, if every fork goes the panel way: 0 subcommands, **~21 top-level
commands** — 17 feature panels + `/ping` `/about` `/help` `/presence`. Discord's cap is 100
top-level; the gain is for people, not the limit.

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

- **F1 — mod commands.** `/warn @user reason` is one line typed; the panel is UserSelect →
  card → button → modal (four clicks). Keep the direct commands beside `/mod`, or panel only?
  A user context-menu command ("Moderate…" on right-click) is a third shape that is
  genuinely an interactive window and one click.
- **F2 — modmail's in-thread `/reply` `/areply` `/note` `/close`.** Typing text is the
  whole job; a modal per reply is slower. Keep them, or a single in-thread `/modmail` panel
  with Reply/Anon reply/Note (modals) and Close?
- **F3 — `/settings`.** The site already owns settings (~120 keys; a 25-option select cannot
  list them). A paged panel, keep the group as the site's fallback, or retire the Discord
  path entirely and point at the site?

## 7. What this program does NOT touch

Persistent posts (role-menu posts, the applications panel post, the pings Streamers panels,
lineup posts, poll messages) — those are `DynamicItem` views that survive restarts and
belong to the room, not the caller. The site. The shared functions and their logs. The
settings keys that exist. Test mode.
