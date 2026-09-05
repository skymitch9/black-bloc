# Modmail — `/modmail` is ONE staff panel, and every ticket carries a sticky staff card

> **Audience:** the build agent and the reviewer; the owner for §I (the forks) and §H (the sweep).
> **Status:** TRACKED · ✅ **BUILD A SHIPPED 2026-09-05 as v80 (`b926d9d`, the merge commit)**, built on
> `worktree-agent-afdd9e23bbaf59be8`
> (the `/modmail` root panel, `Setup…`, `Blocked…`, `Snippets…`, `Forget…`, `Logs`; the six §F
> extractions for block/unblock/snippets/settings; the log-kind rename and the five route
> `note()` deletions; `modmail_panel_minutes`; the doc/string sweep — `commands synced`
> **36 → 35, measured**). **BUILD B IS STILL PLANNING — unbuilt:** the schema migration, the
> sticky ticket card and its reconciler job, `modmail_reply_style` and the relay gate, the
> practice ticket, and retiring `/areply` `/note` `/close`. ⚠️ **Nothing in either half has met
> live Discord**; Build A's whole verification is `pytest` and `ruff`.
> **Last verified: 2026-09-05** — every `path:line` below was READ against `main` at
> **`46fba16`** (`git rev-parse --short HEAD`; working tree clean at the time of reading), in
> `black_bloc/cogs/moderation/modmail.py` (**1657 lines**), `black_bloc/modmail.py` (**362**),
> `black_bloc/api/tools/modmail.py` (**294**), `black_bloc/panels.py` (**219**),
> `black_bloc/guard.py` (**166**), `black_bloc/settings_store.py`, `black_bloc/logkinds.py`,
> `black_bloc/command_visibility.py`, `black_bloc/command_errors.py`,
> `black_bloc/storage/db.py`, `black_bloc/actionlog.py`, `black_bloc/cogs/community/polls.py`,
> `tests/test_bot.py`, `tests/test_logkinds.py`, `tests/cogs/moderation/test_modmail.py`
> (**1262**), `tests/test_modmail.py` (**310**), `tests/api/tools/test_modmail.py` (**214**),
> `site/public/assets/page-modmail.js` (**242**), `site/mock/server.mjs`,
> `site/mock/contract.json`, `site/public/assets/labels.js`, `docs/access/sweeps.md`,
> `docs/info/feature-list.md`, `docs/info/code-notes.md`, `docs/KNOWN_ISSUES.md`,
> `docs/TODO.md`.
> **Counted, not estimated:** **11 leaf subcommands over 2 top-level slots** (`modmail`: logs,
> block, unblock, blocked, mode, forget, status, settings = 8; `snippet`: add, remove, list = 3)
> **plus 4 more top-level commands** (`/reply` `:1131`, `/areply` `:1147`, `/note` `:1192`,
> `/close` `:1243`) — **6 top-level slots for one feature**, the most of any feature in the app.
> `len(top) == 36` (`tests/test_bot.py:179`). `SCHEMA_VERSION == 28` (`storage/db.py:11`).
> `docs/access/sweeps.md` holds **182 numbered rows**. `discord.py` is **2.7.1** (read from
> `.venv/Lib/site-packages/discord/`).
> ⚠️ **NOT verified: anything was run.** No boot, no `pytest`, no `ruff`, no `check.mjs`, nothing
> against live Discord, and no rate-limit figure in §D was measured against Discord's real
> buckets — the debounce numbers are reasoned from the API's documented per-channel limits and
> are labelled as such. The `path:line` keys will drift as the two sibling wave-4 designs
> (`honeypot-panel-design.md`, `mod-panel-design.md`) and the `hide_commands_when_off` build
> merge — **trust the anchor text, not the number.**
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md);
> the shape copied here is [`role-menus-panel-design.md`](role-menus-panel-design.md) (the biggest
> precedent). Feature behaviour is [`phase7-design.md`](phase7-design.md); the code notes are
> `code-notes.md` `# Phase 7 — modmail (F11)` (`:1102–1240`).

---

## A. Measured today — two groups, four loose commands, one relay that already exists

`modmail` is a `Group` (`:819`, `default_permissions=STAFF_ONLY`); `snippet` is a `Group`
(`:1582`, also `STAFF_ONLY`); `/reply` `/areply` `/note` `/close` are four **top-level**
`app_commands.command`s, each with its own `@app_commands.default_permissions(STAFF_ONLY)`.

| Command | Line | Gate | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/modmail logs` | `:1381` | `send_logs` carries its own `require_staff` (`actionlog.py:296`) | `send_logs(interaction, "modmail", …)` |
| `/modmail block` | `:1394` | `_ready` `:1399` → `require_staff` `:1109` | ⚠️ **all inline** `:1401–1415`: `blocked_row` → `add_block` `:349` → answer → `modmail.blocked` (**bare kind**) |
| `/modmail unblock` | `:1417` | `_ready` `:1422` | ⚠️ **all inline** `:1424–1435`: `remove_block` `:357` + `modmail.unblocked` (**bare**) |
| `/modmail blocked` | `:1437` | `_ready` `:1439` | `blocked_rows` `:344` + `answer_lines` `:777`; the lines are **inline** `:1446–1452` |
| `/modmail mode` | `:1454` | `_ready` `:1459` | ⚠️ **inline** `:1463–1479`: `store.set` + `modes_sentence` `:359` + `modmail.settings` (**bare**) |
| `/modmail forget` | `:1481` | `_ready` `:1487` | ⚠️ **inline** `:1491–1501`: `store.clear` + `modmail.forgotten` (**bare**) |
| `/modmail status` | `:1503` | `_ready` `:1505` | `_status_lines` `:1510` — the one thing already extracted, because two commands share it (`code-notes.md` `modmail.py:1502`) |
| `/modmail settings` | `:1540` | `_ready` `:1560` | `_status_lines` + `store.set` per field + `modmail.settings` (**bare**) `:1578` |
| `/snippet add` | `:1587` | `_ready` `:1600` | `valid_snippet_name` `modmail.py:121` → `save_snippet` `:372` + `modmail.snippet_saved` (**bare**) |
| `/snippet remove` | `:1622` | `_ready` `:1626` | `remove_snippet` `:380` + `modmail.snippet_removed` (**bare**) |
| `/snippet list` | `:1641` | `_ready` `:1644` | `all_snippets` `:367`; the lines are **inline** `:1651` |
| `/reply` | `:1131` | `_reply` → `_ready` `:1172` | `_resolve` `:1111` → `resolve_ticket` `:782` → `_body` `:1119` → `send_reply` `:558` |
| `/areply` | `:1147` | same, `anonymous=True` | the same `_reply` `:1163` |
| `/note` | `:1192` | `_ready` `:1200` | ⚠️ **inline** `:1206–1217`: `add_message(NOTE)` `:268` + `relay_embed` + `speak` `:501`. **Writes no log row at all** |
| `/close` | `:1243` | `_ready` `:1257` | `close_ticket` `:616` — the one shared function that already takes `via` and builds `kind_via` `:646` |

**Not a command and NOT moving** (P14, program §7): the DM listener `on_message` `:824` →
`_inbound` `:837`; ticket creation `_open_or_find` `:898` / `_make_place` `:928`; the header
card `_post_header` `:984`; `speak` `:501`; `deliver_dm` `:534`; `react` `:548`; the transcript
path `post_transcript` `:665` and `remove_place` `:739`; the reconciler `:1274` `:1283` `:1298`
`:1306` `:1316` with `loop_health` `:814`; the three listeners `on_guild_channel_delete` `:1334`,
`on_member_remove` `:1350`, `on_thread_delete` `:1374`; the per-user lock `user_lock` `:386` and
the partial unique index `modmail_open_ticket` (`storage/db.py:276`).

### ⚠️ The relay this design "adds" ALREADY EXISTS

`_staff_message` `:1043` is the single most important thing to read before building §E. Today, a
plain message typed by a staff member in a ticket channel **is already relayed to the member**,
and one starting with `=` is already recorded as a private note. This is the incumbent ModMail
bot's behaviour, kept deliberately (`code-notes.md` `modmail.py:23` — *"staff already type
`=note`, and muscle memory is the whole reason not to invent a new prefix"*).

**So `modmail_reply_style` does not build a relay. It GATES one.** `typing` and `both` are
today's behaviour; `buttons` is the new thing — it turns the relay off. Any design that reads as
"we are adding a relay" has misread the file, and any build that writes a second relay path has
duplicated `_staff_message`.

**What does NOT relay today, measured, in the order the code asks:**

| Refused | Where | Why |
|---|---|---|
| a bot or a webhook | `on_message` `:826` | |
| a message whose `type` is not `default` or `reply` | `:828`, `RELAY_TYPES` `:77` | checklist 23 — pins and join notices carry a member as author |
| the database being down | `:830` | |
| a channel with no OPEN ticket, or a ticket in another guild | `:1045–1046` | `ticket_for_channel` `:233` |
| an author `store.is_staff` does not agree is staff | `:1048` | |
| a message starting with `settings.command_prefix` | `:1050–1052` | |
| a message starting with a mention of Black Bloc | `:1053–1055` | *"`@Black Bloc what is this ticket` is a question about the bot"* |
| a message starting with `=` | `:1056` → `is_note` `modmail.py:112` | recorded as a NOTE, never sent |

⚠️ **A slash command is an interaction, not a message**, so `/reply` typed inside a ticket never
reaches `on_message` and can never be double-relayed. Nothing in this design needs to guard that.

### The four asymmetries between Discord and the website

Measured, not inferred — each is a place the same move leaves two different rows, or one and none:

1. ⚠️ **A successful reply writes NO log row on the Discord side.** `send_reply` `:558` logs only
   `modmail.dm_failed` `:595` when the DM does not land. The website `note()`s
   `web.modmail.reply` (`api/tools/modmail.py:188`) on every reply, delivered or not. So today the
   dashboard's Logs page shows every website reply and no Discord one — and `modmail.reply` sits
   in `logkinds.ROUTINE` (`:245`) as a kind **nothing emits**.
2. ⚠️ **`/note` `:1192` writes no log row either**, and the website has no note route at all.
3. ⚠️ **Four kinds are spelled differently by the two doors.** Discord writes
   `modmail.blocked` / `modmail.unblocked` / `modmail.snippet_saved` / `modmail.snippet_removed`;
   the routes write `web.modmail.block` / `.unblock` / `.snippet` / `.snippet_remove`
   (`api/tools/modmail.py:281`, `:291`, `:253`, `:264`). `bare()` (`logkinds.py:360`) therefore
   collapses them onto **`modmail.block`**, not `modmail.blocked` — and both spellings are listed
   in `ROUTINE` (`:237`, `:247`, `:248`, `:249`, `:253`) as if they were four separate events.
   ⚠️ The consequence is a real classification bug: `modmail.unblocked` is **IMPORTANT**
   (`logkinds.py:142`) while its website twin `web.modmail.unblock` bares to `modmail.unblock`,
   which is **ROUTINE** — the same act is loud from one door and quiet from the other.
4. **Nine `modmail.*` kinds are bare**, so any route that ever calls the shared path would
   double-post — checklist 34's exact failure. Only `close_ticket` `:646` builds `kind_via` today.

**One duplicate-code finding:** `cogs/moderation/modmail.py:770 answer()` and `:777 answer_lines()`
are a second copy of `panels.py:36 answer()` (the modmail one passes `mentions()`
(`modmail.py:155`) where the library passes `AllowedMentions.none()` — the same effect, two
homes). Same shape as the standing `role_menus.py:392` finding in [`../TODO.md`](../TODO.md).

### Settings keys, measured

| Key | `KEY_TYPES` | Choices / help | Default |
|---|---|---|---|
| `modmail_enabled` | `:205` bool | help `:571` | **`False`** (`:1537`) — *"false leaves them to the old ModMail bot"* |
| `modmail_mode` | `:206` enum | `MODMAIL_MODES = ("channel","thread")` `:99`, choices `:284`, help `:572` | `CHANNEL_MODE` (`:1540`) |
| `modmail_category_id` | `:207` channel | help `:573` | `None` under test mode, else `MODMAIL_CATEGORY_ID` (`:1541`) |
| `modmail_staff_channel_id` | `:208` channel | help `:574` | ⚠️ **no default of its own** — falls back to `staff_channel_id` in ONE place, `staff_parent_id` `:397` (`code-notes.md` `modmail.py:396`) |
| `modmail_log_channel_id` | `:209` channel | help `:575` | the test channel under test mode, else `MODMAIL_LOG_CHANNEL_ID` (`:1543`) |
| `modmail_log_level` | generated by the log-level family, `LOG_LEVEL_COMMANDS["modmail"]` `:785` | | `important` |

### ⚠️ `/modmail` can never be hidden by `hide_commands_when_off` — by construction

The `hide_commands_when_off` build in flight ([`../TODO.md`](../TODO.md) `:215–232`) grows
`HIDDEN_WHEN_OFF` (`command_visibility.py:16`) to every **mode key whose choices include `off`**.
`MODMAIL_MODES` is `("channel", "thread")` (`settings_store.py:99`) — there is no `off`, so
`modmail_mode` can never read `off` and `hidden_names` `:38` (which compares `== OFF`, the literal
string `"off"`) can never match it. The on/off switch is **`modmail_enabled`, a `bool`**, and
`False` is not `"off"` either. **Say this in the build's report:** `/modmail` and `/reply` are
always in the tree, whatever the posture. That is also the right answer — `modmail_enabled`
defaults `False`, so hiding the command would hide the only Discord door to turning it on, exactly
the reasoning that deleted `HIDDEN_WHEN_OFF["rolemenu_mode"]`.

**Where the on/off lives after this panel:** `modmail_enabled` stays exactly the key it is, reached
three ways — the **Answer DMs** toggle inside the panel's `Setup…` (§C), `/settings set-value
modmail_enabled true`, and the dashboard's Settings page. Checklist 33 is satisfied by the key
already existing; the panel is a fourth-nothing, a new front door onto it.

### Site, measured

`/api/modmail` (`api/tools/modmail.py:143`, the whole router behind `staff_dependency` `:146`) —
`GET /tickets` `:149`, `GET /tickets/{id}` `:163`, `POST /tickets/{id}/reply` `:173`,
`POST /tickets/{id}/close` `:202`, `GET /snippets` `:235`, `POST /snippets` `:241`,
`DELETE /snippets/{name}` `:256`, `GET /blocks` `:267`, `POST /blocks` `:273`,
`DELETE /blocks/{user_id}` `:284` — **ten routes**. Page `site/public/modmail.html` +
`site/public/assets/page-modmail.js` (242 lines: `messageNode` `:30`, `ticketView` `:44`,
`snippetsCard` `:99`, `blocksCard` `:138`, `load` `:174`). `FEATURE_PAGES["modmail"] =
"modmail.html"` (`logkinds.py:97`).

⚠️ `POST /tickets/{id}/close` **already** passes `via=VIA_WEBSITE` `:224` and already does NOT
`note()` — it is the one route in this feature that is already checklist-34 correct, and the
`web.modmail.closed` kind in `site/mock/contract.json:3450` is `kind_via`'s output, not a
hand-rolled head. Copy its shape; do not rewrite it.

---

## B. The decision — one `/modmail` panel, one bare `/reply`, one sticky card per ticket

**`/modmail` becomes a single `app_commands.command` keeping `default_permissions=STAFF_ONLY`;
both `Group`s go, `/snippet` disappears entirely, and `/areply` `/note` `/close` retire into the
ticket card. `/reply` stays a bare typed command** (owner, 2026-09-05 06:41: *"we do the both …
buttons always appear to click reply at the bottom of a channel but also a /reply so they can
just start typing a response"*).

**`commands synced` drops by four: 36 → 32.** Six top-level slots become two. ⚠️ **State the
delta, not the number** — two sibling wave-4 designs and the `hide_commands_when_off` build may
land first, so the build **re-measures** `tests/test_bot.py:179` and edits it to what it reads.

- `STAFF_COMMANDS` (`tests/test_bot.py:18`) loses **`areply` `:19`, `close` `:25`, `note` `:30`,
  `snippet` `:36`**; `modmail` `:29` and `reply` `:33` stay.
- `GATE_IS_TWO_HOPS_AWAY = {"/reply", "/areply"}` (`:58`) loses `"/areply"`. ⚠️ `"/reply"` stays,
  and the reason it is there is unchanged (`code-notes.md` `tests/test_bot.py:57`): its gate is
  `reply` → `_reply` → `_ready` → `require_staff`, and the checker walks one hop.
- `LOGS_GROUPS["modmail"]` (`:13`) is **deleted** — `/modmail` is no longer a `Group` with a
  `logs` child, so the loops at `:160` and `:202` would `KeyError`. ⚠️ The sibling honeypot and
  `/mod` designs delete theirs; whichever merges last leaves the dict **empty**, and an empty dict
  makes both loops vacuous rather than failing. The last build to land says so in its report.
- Nothing changes in `HIDDEN_WHEN_OFF` (§A).

**Root panel** — `build_panel(bot, guild, actor)`, one ephemeral embed + a `Panel` subclass (P2).
**There is no member half:** every path here is `require_staff` today, so a non-staffer gets
`still_staff`'s refusal and no panel at all (P9 — the sentence, never a dead button). The member's
surface is their DM, and it does not change.

### The panel's states

`enabled` = `store.get(guild_id, "modmail_enabled")`; *pointed* = the mode's own place resolves
(`ticket_category` `:410` in channel mode, `thread_parent` `:428` in thread mode).

| # | This guild has | The embed says | The row that renders |
|---|---|---|---|
| S0 | not in a guild, or `db.is_connected` false | `GUILD_ONLY` / `DB_UNAVAILABLE` (`settings_store`) as words; **no panel at all** | — |
| S1 | ⚠️ **no staff role resolves** | `NO_STAFF_WARNING` `:176` verbatim, as the first line | Setup… · Blocked… · Snippets… · Logs · Refresh · site link. **Try a fake ticket is ABSENT** — `_make_place` `:931` refuses to open any ticket, real or practice, with no staff role (checklist 21) |
| S2 | staff resolve, `modmail_enabled` false | today's `status` lines (`_status_lines` `:1510`) + one line saying the incumbent still holds the inbox | the S1 row **plus Try a fake ticket** — practice needs no `modmail_enabled`, because it is not a DM |
| S3 | enabled, **not pointed** for the current mode | the status lines + `NO_CATEGORY` `:104` or `NO_STAFF_CHANNEL` `:112` reworded as a statement | the same, **plus Forget** only if something IS pointed (it can be pointed at a dead channel) |
| S4 | enabled and pointed, **no open ticket** | the status lines + "No ticket is open." (`:1535`) | the same |
| S5 | enabled and pointed, **≥1 open ticket** | + one line per open ticket (`:1529–1533`) | + **A ticket…** select |

**P3 in one line: no state renders a control whose shared function would refuse it.** The three
refusals that become unreachable from Discord are `NO_TICKET_HERE` `:117`, `MANY_OPEN` `:122` and
`NOT_A_TICKET_ID` `:125` — a ticket now arrives from a select or from the card it is printed on,
never from typed digits. ⚠️ **All three strings stay in the module**, because `/reply` still types
`ticket:` (fork **F-M5**) and `resolve_ticket` `:782` still answers with them.

---

## C. The panel — buttons per state, the sub-panels, the modals

Each is a **re-render in place**: `retire(previous)` first (P6 — `panels.py:62`, and ⚠️ never
guard it with `is_finished()`), `defer()` then `edit_original_response` (P5), `db_ready`
(`panels.py:70`) on every click, `still_staff` (`panels.py:55`) before **every** move **and before
every read**, since this feature is staff-only end to end (the pings deviation-10 precedent).

### The root

| Row | Control | Rendered when | Shared function | Log kind | Refusal, in words |
|---|---|---|---|---|---|
| 0 | `A ticket…` `Select` over `open_tickets` `:214`, ≤25 with `capped_placeholder` (`panels.py:88`), label from `panels.option_label` `:96` | S5 | — | — | — |
| 1 | `Setup…` → sub-panel | always | — | — | — |
| 1 | `Blocked…` → sub-panel | always | — | — | — |
| 1 | `Snippets…` → sub-panel | always | — | — | — |
| 1 | `Forget…` → sub-panel | ⚠️ **only when at least one of the three keys is set** (`FORGETTABLE` `:72`) | `forget_place` (§F) | `modmail.forgotten` | — |
| 1 | `Try a fake ticket` → confirm | S2–S5, i.e. **not** when no staff role resolves | `open_practice` (§F) | `modmail.opened` (`details.practice = true`) | S1's embed line already says why it is absent |
| 2 | `Logs` → a NEW ephemeral followup (P11) | always | `send_logs(interaction, "modmail")` `actionlog.py:287` — keeps its own `require_staff` | — | `LOGS_DB_DOWN` from the helper |
| 2 | `Refresh` | always | — | — | — |
| 2 | `Open on the site` (link) | an origin is configured | `panels.site_page_url(origin, "modmail")` `panels.py:123` | — | — |

Five components on row 1 is exactly Discord's cap and only reachable in S2–S5 with something
pointed; the build **asserts every state fits inside five rows of five** (role-menus deviation 3
is the precedent for getting this wrong on paper).

### `Setup…`

The four values as lines, then one button per value; each button re-renders `Setup…` with a single
select in row 0 (role-menus deviation 4's shape — a select needs a whole row, and four selects
plus a mode picker will not fit beside anything).

| Control | Opens | Shared function | Log kind |
|---|---|---|---|
| `Ticket category…` | a `ChannelSelect(channel_types=[category])` | `point_at(bot, guild, actor, "modmail_category_id", channel, via=…)` | `modmail.settings` |
| `Staff channel…` | a `ChannelSelect(text)` | `point_at(… "modmail_staff_channel_id" …)` | `modmail.settings` |
| `Transcripts…` | a `ChannelSelect(text)` | `point_at(… "modmail_log_channel_id" …)` | `modmail.settings` |
| `Mode…` | a `Select` of `MODMAIL_MODES` `:99` | `set_mode` (§F) | `modmail.settings` |
| `Answer DMs on` / `off` — **one button that says what it will do** | — | `set_enabled` (§F) | `modmail.settings` |
| `Reply style…` | a `Select` of `MODMAIL_REPLY_STYLES` (§D) | `set_reply_style` (§F) | `modmail.settings` |
| `Back` · `Refresh` | — | — | — |

⚠️ **`Mode…` keeps today's sentence** (`MODE_SET` `:160`): new tickets take the new mode, the ones
already open keep theirs, *"that is where their channel or thread already is"*. The count comes
from `open_tickets` `:214`, exactly as `:1470` computes it today.

⚠️ **Two spellings of one move is what P3 kills**, so `Answer DMs` is a button that names its own
effect, never a two-option select, and the mode picker is a select because it has two *values*,
not two *directions*.

### `Blocked…`

| Row | Control | Rendered when | Shared function | Log kind |
|---|---|---|---|---|
| 0 | the blocked list as embed lines — `<@id> — reason (date)`, exactly `:1449`'s shape, ⚠️ **capped at 25 lines** with a sentence naming the Moderation page for the rest | ≥1 block | `blocked_rows` `:344` | — |
| 1 | `Somebody…` `Select` over those rows, ≤25 with `capped_placeholder` | ≥1 block | — | — |
| 2 | `Unblock them` | a row is picked | `unblock_member` (§F) | `modmail.unblocked` |
| 2 | `Block someone…` → `UserSelect`, then `Block them…` → a reason modal | always | `block_member` (§F) | `modmail.blocked` |
| 3 | `Back` · `Refresh` | always | — | — |

⚠️ **The `UserSelect` is how somebody past the 25 cap is still reachable** — blocking is not
list-bounded, and the memory panel's "above the cap" precedent applies. `ALREADY_BLOCKED` `:148`
and `NOT_BLOCKED` `:150` stay in the module and stay reachable, because a `UserSelect` can name
somebody already blocked and because the website is a second door — the shared function keeps its
check and the panel prints its sentence.

### `Snippets…`

| Row | Control | Rendered when | Shared function | Log kind |
|---|---|---|---|---|
| 0 | the snippets as lines, `**name** — <content clamped to 120>` (`:1652`'s shape), ⚠️ **capped at 25 lines**, the rest named on the site | ≥1 snippet | `all_snippets` `:367` | — |
| 1 | `A snippet…` `Select`, ≤25 with `capped_placeholder` | ≥1 snippet | — | — |
| 2 | `Remove it` (danger) → `Yes, remove it` / `Keep it` | a snippet is picked | `drop_snippet` (§F) | `modmail.snippet_removed` |
| 2 | `Add one…` → `SnippetModal` (name + content) | always | `put_snippet` (§F) | `modmail.snippet_saved` |
| 2 | `Change it…` → `SnippetModal` prefilled | a snippet is picked | `put_snippet(overwrite=True)` | `modmail.snippet_saved` |
| 3 | `Back` · `Refresh` | always | — | — |

⚠️ **`overwrite` stops being an argument and becomes a state.** `/snippet add … overwrite:true`
`:1598` exists only because a typed command cannot know whether the name is taken. The panel does:
`Add one…` refuses a name that exists with `SNIPPET_EXISTS` `:169` **reworded** (it currently tells
the reader to re-run with `overwrite:true`, which will not exist), and `Change it…` is the
overwrite. `BAD_SNIPPET_NAME` `:164` stays — `valid_snippet_name` (`modmail.py:121`) still guards
the modal, and a modal has no pattern validator.

### The ticket card ON THE PANEL

Picking `A ticket…` re-renders the panel as the ticket's card: **the same embed the sticky card in
the channel carries** (`ticket_card_embed`, §F) — one shape, never two. Its buttons are §E's four
plus `Back`, and they call the same functions. ⚠️ This is a **second door onto a move the channel
card also offers, and that is safe by construction**: `close_ticket` `:627` re-reads the row inside
the per-user lock and returns `(False, None)` to whoever lost, which the panel prints as
`CLOSE_RACED` `:141`. The panel **never edits the channel card itself** — the sticky refresher
(§D) owns that.

### Modals — all `AnswersErrors` + `discord.ui.Modal`, one shape (P12)

⚠️ **discord.py 2.7.1 puts selects, radios and checkboxes inside a modal** via `discord.ui.Label`
(`.venv/Lib/site-packages/discord/ui/label.py:50` — *"a top-level layout component that can only be
used on `Modal`"*), and `Modal.add_item` caps at **five** (`ui/modal.py:270–271`). **This repo
already does it**: `NewPollModal` (`cogs/community/polls.py:2619`) uses five `Label`s including a
`RadioGroup` `:2608` and a `CheckboxGroup` `:2641`, and `picked_values` `:2593` is the shared reader
for both. **Use those, do not re-invent them.**

| Modal | Fields (≤5) | Bounds |
|---|---|---|
| `ReplyModal(anonymous: bool)` | `Label("What the member is sent", TextInput paragraph, required=False)` + `Label("Or a saved reply", Select over snippets, required=False)` | text `CONTENT_LIMIT` 3800 (`modmail.py:27`) but ⚠️ a `TextInput` caps at **4000** and Discord's own DM cap is 2000 — clamp with `clamp(…, CONTENT_LIMIT)` as `add_message` `:288` already does; the select is ≤25 with `capped_placeholder` |
| `NoteModal` | `panels.NoteModal` (`panels.py:176`) **reused**, label naming that the member never sees it | `CONTENT_LIMIT` |
| `CloseModal` | `Label("Why — the member is told this", TextInput, required=False)` + `Label(" ", CheckboxGroup[["Close without telling them"]], required=False)` | reason clamped to 400 (`mark_closed` `:325`) |
| `SnippetModal` | name `TextInput` + content `TextInput` paragraph | `SNIPPET_NAME_LIMIT` 40 (`modmail.py:30`), `CONTENT_LIMIT` |
| `BlockReasonModal` | `panels.NoteModal` **reused**, label naming that it is for the log | 400 (`add_block` `:352`) |
| `SpeakAsMemberModal` | one paragraph `TextInput` | `CONTENT_LIMIT` — practice only (§G) |

⚠️ **A `UserSelect` inside a modal is NOT built.** `discord.ui.Label` accepts any `Item`, so it may
work, but nothing in this repo does it and the failure mode is a modal Discord refuses to render.
Block picks its user on the sub-panel and types only the reason.

⚠️ **The snippet select COMBINES, it does not pre-fill.** A modal is submitted once and Discord
cannot re-render it mid-edit, so the select's value is only known at submit. `ReplyModal.on_submit`
therefore builds the body exactly as `_body` `:1119` does today — the snippet's content, plus the
typed text after a blank line when both are given — which keeps `/reply text: snippet:` and the
button byte-identical in meaning. The owner asked for "pre-fills"; the two-step shape that would
literally pre-fill is fork **F-M7**.

---

## D. The sticky card — the algorithm, step by step

**What it is:** one message at the bottom of every open ticket, carrying the ticket's card embed
and four buttons. **Exactly one exists per ticket, always last, and only one lands in the
transcript** (the owner's requirement, 2026-09-05 06:46).

### It is PERSISTENT, and that is settled by the standing rules, not a fork

`panels-program.md` §7 and P14: an ephemeral panel belongs to the **caller**; a post that belongs to
the **room** is a persistent `DynamicItem` view, and those *"already exist"* — `RequestButton`
(`role_menus.py:1148`), `ApplyButton`/`DecisionButton` (`applications.py:2637`), `BanNowButton`
(`honeypot.py:426`), `ApplyNowButton` (`automod.py:559`). A ticket card that answered *"This
interaction failed"* after every deploy would be the worst possible instance of KI-19, because the
ticket outlives the process by design.

**So each of the four buttons is a `SafeDynamicItem` (`command_errors.py:52`) whose `custom_id`
template carries the ticket id**, registered in `cog_load` `:1274` with
`self.bot.add_dynamic_items(...)`. `timeout=None`; there is no clock to fire.

⚠️ **This is why the `ui/view.py` gotcha does NOT apply to the card, and DOES apply to the panel.**
The gotcha ([`../TODO.md`](../TODO.md) `:47–49`, `discord/ui/view.py:940–968`) is that a `View`
replaced on a message keeps its timeout task and later edits the message it no longer owns. A
dynamic item has no per-message view instance and no timeout, so nothing can fire late. What
replaces the card is **deleting its message**. The `/modmail` panel and every sub-panel are
`Panel` subclasses with a real clock, and every one of their re-renders calls `retire(previous)`
(`panels.py:62`) — that is where `stop()` is mandatory. **A build that puts a timed `View` on the
card instead MUST call `retire` on the old one before deleting the message; say which shape was
built in the Deviations foot.**

### What triggers a refresh

**One place, not the listener.** Every function that writes into a ticket calls
`bump_card(bot, guild, ticket)` as its last step:

| Writer | Line today | Direction |
|---|---|---|
| `_relay_inbound` | `:1012` | the member's DM arrives |
| `send_reply` | `:558` | any staff reply — card, `/reply`, typed relay, or website |
| `add_note` (§F, extracted from `/note` `:1206` and `_staff_message` `:1058`) | | a private note |
| `on_member_remove`'s note | `:1359` | "they left the server" |

⚠️ **Never from `on_message`.** Posting the card is itself a message; a listener trigger would have
to exclude the bot, which would also exclude the reply echo `:612`, and the rule "ignore the card
but not the echo" is one refactor away from an infinite loop. Hooking the writers is deterministic,
covers every door including the website, and cannot recurse. Fork **F-M1** is whether a bot echo
counts as a write worth bumping for.

### The algorithm

```
bump_card(bot, guild, ticket):
  1. if ticket["status"] != OPEN: return                  # a closed ticket has no card
  2. schedule(ticket["id"])                               # coalesce; see the debounce below
--- inside the debounced task, per ticket ---
  3. fresh = get_ticket(db, ticket_id);  if not OPEN: return
  4. old_id = fresh["card_message_id"]                    # §F's new column
  5. target, missing = resolve_place(bot, guild, fresh)   # :481 — three answers, not two
     if target is None: log modmail.card_failed{reason: missing}; return
  6. message, why_not = speak(bot, guild, fresh,          # :501 — the guard is asked ONCE, here
                              embed=ticket_card_embed(fresh, ...),
                              view=card_view(fresh))
     if message is None: log modmail.card_failed{reason: why_not}; return
  7. set_card_message(db, ticket_id, message.id)          # WRITE THE NEW ID FIRST
  8. if old_id and old_id != message.id:
        if guard is not None and not guard.allows_channel(message.channel.id):
            log modmail.would_replace_card{ticket_id, message_id: old_id}
        else:
            try delete old_id                              # a 404 is success, not a failure
            except NotFound: pass
            except Exception as exc: log modmail.card_failed{reason: exc}
```

**Step 7 before step 8 is the contract** (checklist 12: the important thing first, cosmetics last).
If the delete fails, the ticket has two cards — ugly, and both work, because both carry the same
ticket id in their `custom_id`. If the order were reversed and the *write* failed, the ticket would
have an orphan card nothing can ever delete.

⚠️ **Deleting a MESSAGE is a side effect `guard.py` cannot see.** The guard patches
`http.send_message` `:108`, `http.edit_message` `:118` and `http.delete_channel` `:128` — **not**
`delete_message`. So step 8 asks `guard.allows_channel` (`:60`) by hand and logs
`modmail.would_replace_card` when refused, which is checklist 1 exactly, and checklist 2 keeps it a
distinct kind from `modmail.card_failed`. This is the same reasoning `react` `:548` already uses.

⚠️ **`speak` `:501` is the only send path, and it redirects.** While the guard is installed and the
ticket's own channel is not allowed, `speak` `:515–518` sends to the **test channel** instead. So
under `TEST_MODE` a real ticket's card appears in `#mute-me-bot-test-spam`, not in the ticket — and
`allows_interaction` `:97` still accepts its buttons, because the test channel is the test channel.
That is a real, visible difference from production, and §G is the reason the practice ticket exists.

### The debounce — reasoned, not measured

Discord's per-channel message bucket is roughly **5 sends per 5 seconds**, and deletes sit in their
own per-channel bucket. A member sending five DMs in two seconds today costs five relays; with a
naive refresh it would cost fifteen calls in the same window and discord.py would sleep through the
429s inside the listener.

| Constant | Value | Why |
|---|---|---|
| `CARD_DEBOUNCE_SECONDS` | **2.0** | a burst of DMs coalesces into ONE delete+post. Long enough to swallow a human typing three quick lines, short enough that the card is back under the last message before a staffer can read it |
| `CARD_MIN_GAP_SECONDS` | **8.0** | the floor between two card posts in one ticket. A conversation at one message every three seconds still only cycles the card every eight |

Both are **mechanism constants, not settings keys** — the precedent is
`command_visibility.DEBOUNCE_SECONDS = 5.0` and `MIN_SYNC_SECONDS = 60.0`, and
`modmail.RECONCILE_MINUTES = 5` `:68`. Checklist 33 is about *decisions*; a rate-limit floor is
arithmetic. ⚠️ **Say in the Deviations foot whether these were ever measured against a real
channel.** They have not been, here.

The debounce task is per-ticket, keyed in a dict on the **bot** (not the cog), for the same reason
`user_lock` `:386` lives there (`code-notes.md` `modmail.py:385`), and is cancelled in
`cog_unload` `:1280`.

### Reconciliation

`reconcile_tickets` `:1306` gains one job, beside the two it has: **an open ticket whose
`card_message_id` is null, or whose card message has gone, gets one.** That is what makes "exactly
one card, always last" survive a restart, a deploy and a staffer deleting the card by hand — and it
is checklist 4 and 25 applied to the new state. It runs at `cog_load`, at `on_ready` `:1298` and on
the five-minute loop, all of which already exist.

`close_ticket` `:616` deletes the card **before** `post_transcript` `:636`, so the transcript
carries one card, not two — and `remove_place` `:739` deletes the whole channel afterwards anyway
in channel mode, which makes the delete a no-op there and load-bearing in **thread** mode, where the
place is archived and locked `:753` rather than deleted.

---

## E. The ticket card and the relay

### The card, in the channel

**Embed** — `ticket_card_embed(ticket, member, blocked, counts)`: `#id`, the member as a mention
plus display name, when it opened, the mode, whether they are blocked, and the in/out/note counts
from `count_directions` (`modmail.py:234`). It deliberately does **not** repeat `header_embed`
(`modmail.py:195`), which is posted once at the top `:984` and carries account age, join date and
roles — the card is the *controls*, the header is the *dossier*.

| Row | Control | Rendered when | Shared function | Log kind | Refusal, in words |
|---|---|---|---|---|---|
| 0 | `Reply` → `ReplyModal(anonymous=False)` | ticket OPEN | `send_reply` `:558` | `modmail.reply` (`details.anonymous=false`) | `NOTHING_TO_SEND` `:131` when both fields are empty; `DM_FAILED_SAID` `:135` when the DM bounced |
| 0 | `Reply as Staff` → `ReplyModal(anonymous=True)` | ticket OPEN | `send_reply(anonymous=True)` | `modmail.reply` (`anonymous=true`) | as above |
| 0 | `Private note` → `panels.NoteModal` | ticket OPEN | `add_note` (§F) | `modmail.note` (**new kind**) | `NOTE_SAVED` `:134`, or `+ RELAY_FAILED_SAID` `:139` |
| 0 | `Close…` (danger) → `CloseModal` | ticket OPEN | `close_ticket` `:616` | `modmail.closed` | `CLOSE_RACED` `:141`; `NO_TRANSCRIPT_SAID` `:142`; `SILENT_SAID` `:146` |
| 1 | `Speak as the member` → `SpeakAsMemberModal` | ⚠️ **`ticket["practice"]` only** | `practice_message` (§G) | — (it writes an IN row, no action row) | — |
| 1 | `End the practice` | practice only | `close_ticket(silent=True)` | `modmail.closed` (`practice=true`) | — |

A closed ticket has no card at all — the card is deleted in `close_ticket` (§D) and the channel
usually goes with it. There is therefore **no "this ticket is closed" card state**; the panel's own
ticket card is where a closed ticket is read, and it renders no move buttons.

⚠️ **Every one of the four is `still_staff`-checked inside its own callback**, before any defer and
before any modal. A `DynamicItem` in a ticket channel is reachable by anyone who can see the
channel, and a ticket channel's overwrites `:442` grant `view_channel` to every staff role — so
the check is not theoretical the moment a role is demoted. `require_staff` is **not** reused: it
calls `interaction.response.send_message` directly and only works before a defer (requests
finding F3).

### The relay, and `modmail_reply_style`

`_staff_message` `:1043` gains **one gate and one log row**, and nothing else:

```
_staff_message(message):
    ... every check at :1045–1056 unchanged, in the same order ...
    if is_note(content):            -> add_note(...); react NOTE_REACTION      # unchanged
    style = store.get(guild.id, "modmail_reply_style")
    if style == BUTTONS:
        return                      # no relay, no reaction, no row — a message in a ticket
                                    # is just a message, and the card is how staff reply
    why_not = send_reply(..., via=VIA_DISCORD, source=TYPED)
    react(✅ or ⚠️)                  # unchanged
```

| Style | A plain staff message in a ticket | The card | `/reply` |
|---|---|---|---|
| `typing` | relays (today's behaviour) | posted, buttons work | works |
| `both` (**default**) | relays | posted, buttons work | works |
| `buttons` | **does nothing** | posted, buttons work | works |

**Three decisions inside the relay, settled here rather than put to the owner:**

1. **No new "don't relay me" prefix key.** The existing `settings.command_prefix` gate `:1050` and
   the `=` note prefix already give staff two ways to type in a ticket without sending. A third
   spelling of "this one is not for the member" is exactly the two-spellings-of-one-move that P3
   exists to kill, and `=` is the one the incumbent trained them on.
2. **The relay keeps its echo** (`send_reply(echo=True)` `:611`). It is tempting to drop the bot's
   `OUT` embed for a typed relay, since the staffer's own message is right there — but under
   `TEST_MODE` the ✅ reaction is **skipped** (`react` `:550` asks the guard) and the ticket's
   messages are redirected to the test channel, so the echo is the only evidence the relay
   happened. Changing it is fork **F-M3**.
3. **The `source` is recorded, not a separate kind.** One `modmail.reply` row carries
   `details = {ticket_id, anonymous, delivered, source}` where `source` is `card` | `typed` |
   `command` | `web`, and the kind is `kind_via("modmail.reply", via)`. Four kinds for one event
   would be four things to classify and four things to forget.

⚠️ **`buttons` is an access-REDUCING posture and fails safe**: with it on, a staff message that
would have reached a member does not. It therefore needs no confirmation and no guard. The reverse
— a guild that has been on `buttons` flipping to `both` — is the one worth a sentence on the
`Setup…` card: *"from now on, anything staff type in a ticket goes to the member."*

---

## F. Extractions (P4) — one function per move, called by BOTH doors, and the schema

⚠️ **The DB/move layer stays in the COG**, as it does for role menus, applications and temp voice.
`api/tools/modmail.py:8–22` imports thirteen names from the cog; moving them would be a large
mechanical diff for no gain this build needs, and the route tests' unchanged assertions are what
prove the refactor changed nothing (wave-0 deviation 4).

**New, module level in `cogs/moderation/modmail.py`** — each does ONE write and ONE log row, each
takes `via: str = VIA_DISCORD` and builds its kind with `kind_via` (checklist 34):

| Function | Replaces · what the route loses |
|---|---|
| `send_reply(..., *, via, source)` | **exists** `:558`; **gains** the log row it never had (§A finding 1). `api/tools/modmail.py:188` deletes `note("web.modmail.reply")` and passes `via=VIA_WEBSITE, source=WEB` |
| `add_note(bot, guild, ticket, author, text, *, via)` | inline `/note` `:1206–1217` **and** the `=` branch of `_staff_message` `:1058–1066`, which are two copies of one act today. **New kind `modmail.note`** → `logkinds.ROUTINE` |
| `block_member(bot, guild, actor, user_id, reason, *, via)` | inline `:1401–1415`; `modmail.blocked` gains `kind_via`. `api/tools/modmail.py:281` deletes its `note` |
| `unblock_member(bot, guild, actor, user_id, *, via)` | inline `:1424–1435`; `modmail.unblocked` gains `kind_via`. `:291` deletes its `note` |
| `put_snippet(bot, guild, actor, name, content, *, overwrite, via)` | inline `:1600–1620`; `modmail.snippet_saved` gains `kind_via`. `:253` deletes its `note` |
| `drop_snippet(bot, guild, actor, name, *, via)` | inline `:1626–1639`; `modmail.snippet_removed` gains `kind_via`. `:264` deletes its `note` |
| `point_at(bot, guild, actor, key, value, *, via)` · `forget_place(…)` · `set_mode(…)` · `set_enabled(…)` · `set_reply_style(…)` | the inline halves of `/modmail settings` `:1565–1580`, `forget` `:1491–1501` and `mode` `:1463–1479`; `modmail.settings` / `modmail.forgotten` gain `kind_via`. No route today — the dashboard writes these through the Settings page, which logs `web.settings.set` and is a different event |
| `bump_card(bot, guild, ticket)` · `card_view(ticket)` · `set_card_message(db, ticket_id, message_id)` | **new** (§D) |
| `open_practice(bot, guild, actor)` · `practice_message(bot, guild, ticket, text)` | **new** (§G) |

`close_ticket` `:616` is **unchanged** except for the card delete in §D — it already takes `via`,
already builds `kind_via` `:646`, and its ordering is a documented contract (`code-notes.md`
`modmail.py:1213`). ⚠️ **Do not touch the order inside it.**

### Pure, into `black_bloc/modmail.py` (it exists; append)

| New | What it is |
|---|---|
| `CardMove` + `CARD_MOVES` + `card_buttons(*, practice)` | §E's card table AS DATA, proved by a parametrised test |
| `root_buttons(*, enabled, pointed, has_staff, has_tickets, has_blocks, has_snippets)` | §B's state table |
| `ticket_card_lines(ticket, counts, blocked)` | the card embed's body |
| `status_lines(...)` | ⚠️ **NOT moved.** `_status_lines` `:1510` reads `store.staff_roles(guild)` and the cog's own `last_ok_at` — it stays a method and the panel calls it, exactly as `/modmail settings` does today |
| `MODMAIL_REPLY_STYLES = ("buttons", "typing", "both")`, `BUTTONS`/`TYPING`/`BOTH`, `relays_typing(style)` | §E's gate, one home |
| `SOURCES = ("card", "typed", "command", "web")` | the `details.source` vocabulary |
| `PANEL_MINUTES_KEY = "modmail_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:119`), exactly as `requests.py` does |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER`, the new sentences | wave-0 deviation 1 — a whole sentence, not a format string |

**Reuse, never re-copy:** `cogs/moderation/modmail.py:770 answer()` and `:777 answer_lines()` are a
second copy of `panels.py:36 answer()` (§A). **Import the library's `answer` and keep
`answer_lines` as a thin wrapper over it**, so the `mentions()` vs `AllowedMentions.none()`
difference is deleted rather than preserved. ⚠️ `modmail.py` also exports `mentions`
(`modmail.py:155`) — read `code-notes.md` `modmail.py:155` and `tests/test_modmail.py:168` before
touching anything to do with allowed mentions here; that test is the ping test.

### Schema — ⚠️ SCHEMA_VERSION 28 → 29, and migrate-before-deploy applies

Two additive columns on `modmail_tickets` (`storage/db.py:261`), through the existing
`ADDED_COLUMNS` / PRAGMA pattern at `:641`:

| Column | Type | Why |
|---|---|---|
| `card_message_id` | `INTEGER` (nullable) | the sticky card's message id. ⚠️ **Without it the card cannot survive a restart** — the next member message would post a second card and the first would never be deleted, so "exactly one card" would break on every deploy |
| `practice` | `INTEGER NOT NULL DEFAULT 0` | §G. A flag on the row, not a convention about the channel name, because `send_reply` and `close_ticket` must both be able to ask "is this real?" without looking at Discord |

**`SCHEMA_VERSION` goes 28 → 29** (`storage/db.py:11`). Both are `ALTER TABLE … ADD COLUMN` with a
default, so any merge order produces the same database — but the standing rule stands: **migrate
before deploy, always** (`access/deploy.md`, the global mechanical-guards rule). The build says in
its report that a migration is needed; the conductor runs it before the release.

### Log kinds after this build

| Move | Discord | Website | Class |
|---|---|---|---|
| reply | `modmail.reply` | `web.modmail.reply` | ROUTINE (already `:245`) |
| note | `modmail.note` | — | ROUTINE (**new**) |
| close | `modmail.closed` | `web.modmail.closed` | IMPORTANT by suffix `.closed` `:129` |
| block | `modmail.blocked` | `web.modmail.blocked` (**renamed** from `web.modmail.block`) | IMPORTANT by suffix `.blocked` `:128` |
| unblock | `modmail.unblocked` | `web.modmail.unblocked` (**renamed** from `web.modmail.unblock`) | IMPORTANT `:142` |
| snippet save | `modmail.snippet_saved` | `web.modmail.snippet_saved` (**renamed** from `web.modmail.snippet`) | ROUTINE `:250` |
| snippet remove | `modmail.snippet_removed` | `web.modmail.snippet_removed` (**renamed** from `web.modmail.snippet_remove`) | ROUTINE `:249` |
| the card | `modmail.card_failed` (**new**, IMPORTANT by `_failed`) · `modmail.would_replace_card` (**new**, ROUTINE by the shadow rule) | — | checklist 2 — a failure and a dry run never share a kind |

⚠️ **Four entries in `logkinds.ROUTINE` become DEAD and must be deleted in the same commit**:
`modmail.block` `:237`, `modmail.unblock` `:253`, `modmail.snippet` `:247`,
`modmail.snippet_remove` `:248`. They are `bare()` of the four web kinds being renamed, never
emitted by anything. `tests/test_logkinds.py::test_no_classification_entry_is_dead` `:555` fails if
they are left, and `::test_web_kinds_collapse_onto_the_kind_they_mirror` `:562` is what the rename
makes true. This is role-menus deviation 10's shape, and the same four files follow:
`logkinds.py`, `site/mock/contract.json:3449–3454`, `site/mock/server.mjs:3641–3721`, and the route
tests. `HEADS["modmail"]` (`logkinds.py:52`) is untouched, so rows already in the database still
classify.

⚠️ **`tests/test_logkinds.py:56–60`** lists the five `web.modmail.*` kinds inside
`KNOWN_DYNAMIC["black_bloc/api/writes.py::kind"]` — the routes' own set. **All five move into a
shared block** beside `black_bloc/rolemenu_panels.py::kind` (`:226`), or the AST walk
`test_a_route_never_notes_an_event_its_shared_path_already_logged` `:433` fails.

---

## G. The practice ticket — how it is allowed under `guard.py`, and why it exists

**The owner's reason, verbatim (2026-09-05 06:46): the practice ticket is how he decides
`modmail_reply_style`.** He presses `Try a fake ticket`, speaks as the member, watches the sticky
card move, tries a card reply, a typed reply and `/reply`, flips the style on `Setup…`, and tries
again. **Say that in the build's report and in the sweep row** — this button is not a toy, it is
the instrument for a settings decision that would otherwise need a real member and a real DM.

### Where it lives, read out of `guard.py` rather than assumed

`TestModeGuard` (`guard.py:19`) allows a send only where `allows_channel` `:60` says so: the test
channel, a DM, **or a channel the bot has claimed with `own_channel` `:45`**. Measured, only three
features claim anything — `polls.py:1461`, `raidtrain.py:2140` (both threads) and `tempvoice.py:438`
(voice channels). ⚠️ **Modmail claims nothing today**, which is exactly why `speak` `:515` redirects
a real ticket's messages into the test channel and why the sweep (`sweeps.md:241–243`) expects to
read them there.

**The practice ticket is a PRIVATE THREAD on the test channel, and the build claims it with
`guard.own_channel(thread)`.** Three reasons, in order:

1. **`thread_parent` `:428` already returns the test channel while a guard is installed**, so
   practice reuses the code path thread-mode tickets take under test mode — no second way of
   deciding where a ticket goes.
2. **Claiming it is what makes the card actually STICK where the owner can watch it.** Without
   `own_channel`, `speak` redirects the card into the test channel and the whole point — "watch the
   card move to the bottom" — is unobservable. `allows_interaction` `:99` then accepts the card's
   buttons too, because a **component** interaction in an owned channel is explicitly permitted.
3. **It is the narrowest possible widening.** One thread, made by the bot, under the test channel,
   claimed for the life of the practice and **disowned in `close_ticket` when
   `ticket["practice"]`** — `guard.disown_channel` `:51`. Polls and raidtrain set the precedent for
   exactly this.

⚠️ **Real ticket channels are NOT claimed** — fork **F-M6**. Widening where the bot may speak is
access-INCREASING and does not get made as a side effect of a practice button.

⚠️ **A consequence to state plainly, because it will look like a bug:** in the practice thread the
sticky card behaves as it will in production; in a REAL ticket under `TEST_MODE` the card appears
in `#mute-me-bot-test-spam` instead. That difference is the practice ticket's entire justification,
and the sweep row must say so or the owner will report the real ticket as broken.

⚠️ **Creating a thread is invisible to the guard** — the guard patches `send_message`,
`edit_message` and `delete_channel` (`:140–142`), not thread creation. Checklist 1 therefore
applies: `open_practice` asks `guard.allows_channel(test_channel.id)` explicitly before creating
anything, and with no guard installed it creates the thread on `thread_parent`'s answer as normal.
There is no `would_open_practice` shadow kind, because there is no shadow mode here — either the
test channel resolves and the thread is made, or `NO_TEST_CHANNEL` `:100` is the refusal.

### What is fake about it

| | Real ticket | Practice ticket |
|---|---|---|
| the member | a Discord user who DM'd | **the staffer who pressed the button** — `user_id = actor.id`, so the header card and the transcript are real-looking and name somebody who exists |
| the row | `practice = 0` | `practice = 1` |
| inbound messages | the DM listener `:837` | the `Speak as the member` modal → `practice_message` → `add_message(IN)` `:268` + `relay_embed(IN)` + `speak` — **the same three calls `_relay_inbound` `:1012` makes** |
| ⚠️ a DM to the member | `deliver_dm` `:534` | ⚠️ **never.** `send_reply` and `close_ticket` short-circuit the DM when `ticket["practice"]`, and they log **no `modmail.dm_failed`** — a suppressed DM is not a failed one (checklist 2, and checklist 10: do not claim a check that was skipped) |
| the opening DM `opening_dm` | sent `:871` | not sent |
| the ✅ reaction | `react` `:548` | there is no member message to react to |
| the transcript | filed to `modmail_log_channel_id` | ⚠️ **filed, marked PRACTICE** — fork **F-M4**, recommended (a) |
| closing | `Close…` on the card | `End the practice`, which is `close_ticket(silent=True, reason="practice")`; the thread is archived and locked `:753` and disowned |

⚠️ **`open_practice` must not collide with a real open ticket.** The partial unique index
`modmail_open_ticket` (`storage/db.py:276`) is `(guild_id, user_id) WHERE status='open'`, so a
staffer who already has a real open modmail ticket of their own cannot also have a practice one.
That is a correct constraint and the button says so in words (`ALREADY_PRACTISING` /
"you already have a ticket open") rather than raising `sqlite3.IntegrityError` — which
`_open_or_find` `:905` already catches for the real path.

The website's `GET /api/modmail/tickets` `:149` **excludes practice rows by default** and
`ticket_row` `:80` gains `"practice": bool(row["practice"])`, so the dashboard can show a chip on
the one place a practice ticket can still be seen (`?status=` with a new `practice=1` query would be
a route change; it is not one, and the field on the row is enough).

---

## H. What goes away, every line that names it, tests, and §J

`/help` reads the tree (`cogs/core.py tree_commands`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `modmail` Group + 8 children | `:819` and §A | the root panel and its four sub-panels |
| `snippet` Group + 3 children | `:1582` | the `Snippets…` sub-panel |
| `/areply` | `:1147` | `Reply as Staff` on the card |
| `/note` | `:1192` | `Private note` on the card |
| `/close` | `:1243` | `Close…` on the card |
| `/reply` | `:1131` | ⚠️ **STAYS**, and keeps `text` and `snippet`. `ticket` is fork **F-M5** |
| `_reply` `:1163` (the `anonymous` fork) | | keeps only the `anonymous=False` caller |
| `LOGS_GROUPS["modmail"]` | `tests/test_bot.py:13` | **deleted** |
| `STAFF_COMMANDS` `areply` `close` `note` `snippet` | `tests/test_bot.py:19,25,30,36` | **deleted**; `modmail` `:29` and `reply` `:33` stay |
| `GATE_IS_TWO_HOPS_AWAY` `"/areply"` | `tests/test_bot.py:58` | **deleted**; `"/reply"` stays |
| `assert len(top) == 36` | `tests/test_bot.py:179` | **four lower than whatever the build measures** — never a hard-coded absolute |

### Strings that name a retired command, rewritten in the SAME commit

| Line | String | Names |
|---|---|---|
| `modmail.py` (cog) `:104` | `NO_CATEGORY` | `/modmail settings category:` |
| `:108` | `NOT_A_CATEGORY` | `/modmail settings category:` |
| `:112` | `NO_STAFF_CHANNEL` | `/modmail settings staff_channel:` **and** `/modmail mode channel` |
| `:117` | `NO_TICKET_HERE` | `/modmail status` — ⚠️ shown by `/reply`, which survives, so this one is **reworded, not deleted** |
| `:126` | `NO_SUCH_TICKET` | `/modmail status` |
| `:132` | `NO_SNIPPET` | `/snippet list` — ⚠️ also reachable from `/reply snippet:` |
| `:147` | `BLOCKED_SAID` | `/modmail unblock` |
| `:156` | `FORGOTTEN` | `/modmail settings` |
| `:168` | `SNIPPET_SAVED` | `/reply snippet:{name}` — **the one that stays true**; keep it |
| `:169` | `SNIPPET_EXISTS` | `overwrite:true` — reworded to name `Change it…` (§C) |
| `:175` | `NO_SNIPPETS` | `/snippet add` |
| `:1135` `:1151` | the two `describe` texts | `/snippet list` |
| `api/tools/modmail.py:64` | `CLOSE_WOULD_DELETE` | ⚠️ **`/modmail close`, a command that has never existed** (it is `/close`) — and after this build the right words are "close it from the ticket's card in the test channel" |
| `settings_store.py:572–575` | four `KEY_HELP` entries | they describe the keys, not commands — **measured: no command named; untouched** |

### Docs rewritten in the same commit (P15)

| File | Lines | What |
|---|---|---|
| `docs/access/sweeps.md` | `:239–247` (the Phase 7 block) | rewritten **in place** — every one of `/modmail status`, `/modmail settings`, `/reply ticket:`, `/areply`, `/note`, `/close`, `/snippet add`, `/modmail block` is named there |
| `docs/info/feature-list.md` | `:26`, `:49`, `:85` | F11's rows |
| `docs/info/panels-program.md` | `:86` (the Modmail row → BUILT), `:196` (fork **F2** → decided, with the answer) | |
| `docs/info/phase7-design.md` | `:23`, `:69–82`, `:108–110` | a dated **"superseded by the panel"** line at the top, **not** a rewrite of history |
| `docs/info/architecture.md` | `:188` | the tree comment naming `/reply, /close` |
| `docs/info/code-notes.md` | `:1102–1240`; specifically `:1175` (`/modmail status`, `/modmail blocked`, `/snippet list`), `:1203` (the `/reply` test-mode note — ⚠️ **this is the note fork F-M5 turns on**), `:1209`, `:1502`'s note | re-keyed at the merge; the anchors are `path:line` and will move |
| `docs/access/site.md` `:230` · `docs/access/operator-read.md` `:125` · `docs/info/phase8b-design.md` `:66` · `docs/info/site-feature-audit.md` `:44` | | these name **routes**, not commands — measured, **no edit needed** |
| `docs/KNOWN_ISSUES.md` KI-5 | | unchanged in substance; the practice ticket is a new sentence in it — a practice reply reaches nobody, which is the one modmail DM test mode *does* stop |
| `docs/access/OWNER_GUIDE.md` | | **measured: zero matches for `modmail` or `snippet`** — nothing to rewrite; the build may add a `/modmail` row if the sibling designs are adding theirs |

### Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/moderation/test_modmail.py` (1262 lines) | `/modmail` answers ephemerally with a panel; **parametrised over S0–S5 — each renders exactly its §B row and no other**; `Try a fake ticket` absent with no staff role; `Forget…` absent with nothing pointed; `A ticket…` absent with none open and capped at 25 with its placeholder; every button calls its shared function with `via` untouched (mock it); a staffer demoted mid-card moves nothing (`still_staff` at every site, reads included); `db_ready` after every defer; a re-render `retire`s what it replaced and a timeout disables every item and writes the footer. **The card:** four buttons on an open ticket, `Speak as the member` only on a practice one; a member message deletes the old card and posts a new one and writes the new id **before** deleting the old; a delete refused by the guard logs `would_replace_card` and **not** `card_failed`; a burst of five messages produces ONE card cycle; a restart with a null `card_message_id` gets a card from the reconciler. **The relay:** `buttons` sends nothing and reacts to nothing; `typing` and `both` relay exactly as today (the existing `:520` and `:535` tests stay green **unchanged in assertion** — that is the proof the gate did not move the relay); `=` is a note in all three styles. **Practice:** a practice reply never calls `deliver_dm` and never logs `dm_failed`; closing it archives, disowns and files a PRACTICE transcript; a staffer with a real open ticket is refused in words |
| `tests/test_modmail.py` (310) | the two button tables against every flag combination; `ticket_card_lines`; `relays_typing` over all three styles; `panel_minutes`. ⚠️ **`:69`, `:168`, `:182` and `:269` are load-bearing and must not move** — `code-notes.md` says why for each |
| `tests/api/tools/test_modmail.py` (214) | ⚠️ **mostly unchanged — that is the proof no route moved.** Only the assertions reading a `web.modmail.*` row change: five become one row carrying `via`, and four of them change NAME (§F) |
| `tests/test_settings_store.py` | `modmail_panel_minutes` round-trips and defaults 10; `modmail_reply_style` round-trips, defaults `both`, and refuses a value outside `MODMAIL_REPLY_STYLES` |
| `tests/storage/test_db.py` | the two new columns exist after a migration from 28, and an existing row reads `practice = 0` |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `modmail`; four names leave `STAFF_COMMANDS`; `"/areply"` leaves `GATE_IS_TWO_HOPS_AWAY`; the tree-limit test **recounts** |
| `tests/test_logkinds.py` | the five `web.modmail.*` entries move from `:56–60` into a shared block; the four dead ROUTINE entries go; `modmail.note`, `modmail.card_failed`, `modmail.would_replace_card` are classified |
| `tests/test_panels.py` | **unchanged** — nothing is added to `panels.py` (§F) |

### §J — prove before merge (P17), and the checklist sweep

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers** — the drop must
   be exactly **four**. With no token, measure it the only other way:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` counts the real tree
   (checklist 10 — a check that could not run is not a check that passed).
2. The parametrised state test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.modmail, black_bloc.cogs.moderation.modmail,
   black_bloc.api.tools.modmail, black_bloc.panels, black_bloc.bot"` — the substitute for a boot
   (wave-0 deviation 5). ⚠️ `black_bloc/modmail.py` must **not** import the cog; the cog imports it
   (`:25–54`), and closing that loop is the import cycle this build risks.
4. **The migration, on a copy of the live database**, before anything is deployed: 28 → 29, both
   columns present, every existing row readable. Migrate-before-deploy is not optional here.
5. `ruff`; full `pytest`; `node site/mock/check.mjs` (**expect the page/route counts unchanged** —
   no route is added or removed); `node --input-type=module --check < site/public/assets/labels.js`.
6. Checklist sweep before reporting — **1** (deleting the card message is invisible to the guard;
   creating the practice thread is too), **2** (`card_failed` vs `would_replace_card`; a suppressed
   practice DM is neither), **4** and **25** (the card reconciler runs at `cog_load`, `on_ready`
   and on the loop), **6** (`user_lock` `:386` and the partial index still cover the open ticket;
   the card debounce is per-ticket and does not need one), **8** and **30** (`AnswersErrors` on
   every modal, select and view; `SafeDynamicItem` on every card button), **10** (a practice run
   that skipped the transcript would be a claimed check that did not run — fork F-M4),
   **11** (`allowed_mentions` on every interpolated send — `mentions()` `modmail.py:155`, and read
   `tests/test_modmail.py:168` first), **12** (write the new card id before deleting the old),
   **22** (`clamp` on every modal field — a modal has no `app_commands.Range`), **23** (`RELAY_TYPES`
   `:77` unchanged), **24** (defer before every card move — `send_reply` DMs and `close_ticket`
   uploads a file), **26** (`Forget…` is the list-removal path and `on_guild_channel_delete` `:1334`
   is its listener — both survive), **28** (`_reconcile_loop` `:1283` and `loop_health` `:814`
   untouched), **32** (`reconcile_tickets` `:1310` still skips `guild.unavailable`), **33** (§D),
   **34** (five routes lose their `note()` and gain `via=VIA_WEBSITE`).

⚠️ **TEST_MODE stands, and this feature is where it bites hardest.** Creating a ticket channel is a
REAL side effect the guard cannot see (`code-notes.md` `modmail.py:409`), and it is enforced by
PLACE — tickets are made in the test channel's own category `:410` or as threads on the test
channel `:428`, and nowhere else. The card's message delete gets an explicit guard check (§D) and a
`would_replace_card` shadow row. **The one thing test mode does NOT stop is a DM** (KI-5), so a real
ticket's `Reply` button reaches a real member exactly as `/reply` does today — nothing in this
design may read as "safe because test mode is on".

### Sweep rows — lettered here, numbered by the conductor at merge

`docs/access/sweeps.md` holds **182 numbered rows** as this is written, and **two sibling wave-4
designs are being written in parallel**, so this document claims **no numbers**: the build reads the
file's last row and starts after it. The Phase 7 block at `:239–247` is rewritten **in place**.

| # | Do this | Expect |
|---|---|---|
| M1 | `/modmail` with `modmail_enabled` false | one ephemeral panel: today's `status` lines, a line saying the incumbent still holds the inbox, and Setup… · Blocked… · Snippets… · Try a fake ticket · Logs · Refresh · Open on the site. **No Forget…** if nothing is pointed |
| M2 | `Setup…` → `Transcripts…` → the test channel; `Mode…` → `thread`; `Answer DMs on` | each re-renders in place with the new value on the card; the mode reply says the open tickets keep theirs; one `modmail.settings` row per change and **no second row from the website** |
| M3 | `Snippets…` → `Add one…` (`ban-appeal`) → `Add one…` again with the same name → `Change it…` | saved; the second is refused in words naming `Change it…`; changing it overwrites. `/reply snippet:ban-appeal` still sends it — **the one command that survives** |
| M4 | `Blocked…` → `Block someone…` → yourself → a reason; then `Somebody…` → `Unblock them` | both land, both leave ONE log row, and the row for unblocking is **loud** (important) while blocking is loud too — check the Logs page shows one line each, not two |
| M5 | **`Try a fake ticket`** | a private thread appears **on** the test channel with the header card and, under it, the staff card: Reply · Reply as Staff · Private note · Close… · Speak as the member · End the practice |
| M6 | `Speak as the member` → "hello?" three times quickly | the member message appears each time and the card **moves to the bottom once**, not three times (the 2-second debounce). ⚠️ The old card is gone, so the thread has exactly one |
| M7 | `Reply` → type text; then `Reply` → pick the snippet and add a line; then `Reply as Staff` | all three land in the thread as `Sent to the member` embeds; the anonymous one says **Staff** and carries **no role colour** (`code-notes.md`'s corrected note); ⚠️ **no DM reaches anybody** and there is **no `modmail.dm_failed`** — it is practice |
| M8 | `Setup…` → `Reply style…` → `typing`; back in the thread, type `hello` as yourself; then type `=this is private` | the plain line relays as a `Sent to the member` embed with a ✅; the `=` line does not, and gets 📝. Then set `buttons` and type again — **nothing at all happens**, no relay and no reaction. This is the choice `modmail_reply_style` is for |
| M9 | `/reply text:hi` typed **in the practice thread**, then in the test channel | ⚠️ **fork F-M5 decides the first one.** In the test channel it finds the only open ticket, as today |
| M10 | `End the practice` | the transcript `.txt` + summary land in the transcripts channel marked **PRACTICE** (fork F-M4), the thread is archived and locked, the card is gone, and the member (you) is **not** DM'd |
| M11 | Turn `modmail_enabled` on, DM the bot from a second account, then close from the card | a real ticket channel in the test category; ⚠️ **its card appears in the test channel, not in the ticket** — that is `speak`'s redirect and it is expected (§G); `Close…` with a reason DMs the member for real, files the transcript, deletes the channel |
| M12 | Leave the panel `modmail_panel_minutes` minutes | it goes quiet with its footer and every button disables |

---

## I. The genuine forks — the owner decides, one at a time

**Settled first, by the standing rules, so they are NOT put to him:**

- ✅ **`/modmail` stays `STAFF_ONLY`, and there is no member panel.** Every one of the fifteen
  commands is staff-gated today; the member's surface is their DM.
- ✅ **`/modmail` is never hidden by `hide_commands_when_off`** — `modmail_mode` has no `off` and
  `modmail_enabled` is a bool (§A). Nothing to decide.
- ✅ **The card is a persistent `DynamicItem`, not a timed `View`** — program §7 and P14: a post
  that belongs to the room survives restarts.
- ✅ **Staff may move a ticket from the panel as well as from the card.** Staff-final-say, and
  `close_ticket`'s re-read inside the lock `:628` makes two doors safe rather than racy.
- ✅ **The DM listener, the ticket creation, the transcript and the reconciler are untouched.**
- ✅ **No new "don't relay me" prefix** (§E decision 1) — `=` and `command_prefix` already exist.
- ✅ **The debounce numbers are constants, not keys** (§D) — a rate-limit floor is arithmetic.

**Seven questions are genuinely his.** Each has a recommendation; none is a coin-flip.

- ✅ **F-M1 — ANSWERED (a) by the owner 2026-09-05 ("A"): every write into the ticket.**
  Original question kept for the record — what makes the card jump to the bottom. The owner said *"whenever the member writes"*
  and also *"always appear … at the bottom of a channel"*, and after a run of staff replies those
  two differ.
  - **(a) Every write into the ticket** — a member message, a staff reply (from any door), a private
    note, the "they left" note. The card is then genuinely always last, which is the reason he gave
    for wanting it. Costs one delete+post per staff reply, absorbed by the 8-second floor.
    **Recommended.**
  - (b) Member messages only, exactly as the words say. Fewer API calls; the card sits above a
    staff conversation until the member speaks again.

- ✅ **F-M3 — ANSWERED (a) by the owner 2026-09-05 ("Do a"): the echo stays, unchanged.** If the
  redundancy grates once test mode is lifted it becomes a settings key, not a rewrite.
  Original question — does a TYPED reply still echo the bot's embed into the ticket?
  - **(a) Yes, unchanged** — `send_reply(echo=True)` `:611` as today. Slightly redundant in
    production (the staffer's own message is right there), but under test mode the ✅ is skipped and
    the echo is the only proof the relay happened. **Recommended** — it is also a zero-diff answer.
  - (b) No — drop the echo for `source == "typed"` and rely on the ✅. Cleaner-reading tickets;
    invisible confirmation under test mode, and one more branch in the one function every reply goes
    through.

- ✅ **F-M4 — ANSWERED (a) by the owner 2026-09-05 ("A"): file it, marked PRACTICE.**
  Original question — the practice ticket's transcript.
  - **(a) File it, marked PRACTICE** in the embed title, the filename
    (`modmail-practice-ticket-N.txt`) and the transcript header. The close path is a third of this
    feature's risk and practice that skips it has not practised it; under test mode the transcripts
    channel defaults to the test channel anyway (`settings_store.py:1543`), so he sees it. **Recommended.**
  - (b) Never file one. A tidier log channel; a practice run that proves less than it appears to.

- ✅ **F-M5 — ANSWERED (a) by the owner 2026-09-05 ("A"): `/reply` keeps `ticket:`, optional, last.**
  Original question — does `/reply` keep its `ticket:` argument? The decision list says *"`[ticket]`
  arguments go away — `/reply` keeps finding the ticket from the channel it is typed in."* ⚠️
  **Measured, that breaks `/reply` under his own test policy.** `tree.interaction_check`
  (`guard.py:147`) only accepts a slash command typed in the test channel or a DM, so `/reply`
  **cannot be run inside a ticket channel while test mode is on** — and `code-notes.md`
  `modmail.py:1203` records `ticket:` as the deliberate affordance for exactly that.
  - **(a) Keep `ticket:` on `/reply` alone**, optional, last. `/areply` `/note` `/close` lose theirs
    by retiring. The typed command stays usable from the test channel with two tickets open.
    **Recommended** — the alternative removes the only typed door while the standing test policy is
    in force.
  - (b) Drop it. `/reply` then works only from inside a ticket, i.e. only once test mode is lifted;
    until then the card's `Reply` button is the door (it works, because the card lands in the test
    channel and a component there is allowed). Cleaner command, a feature that is half-usable today.

- ✅ **F-M6 — ANSWERED (a) by the owner 2026-09-05 ("A"): real tickets are NOT claimed; only the
  practice thread is.** Original question — do REAL ticket channels get claimed with `guard.own_channel`?
  - **(a) No.** Only the practice thread is claimed. Real tickets keep today's redirect into the
    test channel, which is what `sweeps.md:241–243` expects and what every existing modmail test
    asserts. **Recommended** — widening where the bot may speak is access-increasing and is not made
    as a side effect of a practice button.
  - (b) Yes — tickets become owned, so cards and relays land in the real ticket even under test
    mode. Much more realistic; it also silently makes `TEST_MODE` weaker for one feature, and
    rewrites `test_modmail.py:377`, the test `code-notes.md` calls *"the test-policy proof"*.

- ✅ **F-M7 — ANSWERED (a) by the owner 2026-09-05 ("A"): combine, in one modal.** (b) stays a
  clean follow-up if editing canned replies before sending turns out to be wanted.
  Original question — does the snippet select COMBINE or PRE-FILL? He said *"a snippet select that pre-fills
  the text"*; a modal is submitted once, so a select inside it cannot pre-fill anything.
  - **(a) Combine, in one modal** — `Label(Select)` + `Label(TextInput)`, and on submit the body is
    the snippet plus the typed text, byte-identical to `_body` `:1119` and to `/reply text: snippet:`
    today. One click, one shape, the `polls.py:2619` precedent. **Recommended.**
  - (b) Truly pre-fill, in two steps — a `Use a snippet…` button on the card opens an ephemeral
    select; picking one opens `ReplyModal` with the snippet's text already in the box, editable
    before sending. That is literally what he asked for, and editing a canned reply is a real
    workflow — at one extra click and one extra surface per reply, and the card's row 0 goes to five
    buttons exactly.

- **F-M8 — does `Reply as Staff` stay a separate button, or become a checkbox in one modal?**
  discord.py 2.7.1 puts a `CheckboxGroup` in a modal (`polls.py:2641`), so *"send this without my
  name on it"* could be a tick inside `ReplyModal` and the card would drop to three buttons.
  - **(a) Two buttons, as decided.** Anonymity is a decision made **before** typing, and a tick
    that is easy to miss on a reply that cannot be unsent is the wrong shape. **Recommended.**
  - (b) One button, one tick. A shorter card and room for `Use a snippet…` if F-M7 goes (b).

---

## J. What NOT to build, and what this costs

**Not in this build:**

- **The DM listener, ticket creation, the header card, `speak`, `deliver_dm`, the transcript path
  and the reconciler** — apart from the one card job §D adds to the reconciler and the one card
  delete §D adds to `close_ticket`. ⚠️ The order inside `close_ticket` `:616` is a documented
  contract (`code-notes.md` `modmail.py:1213`); do not touch it.
- **Moving the DB/move layer out of the cog** (§F) — thirteen route imports say don't.
- **Any new API route or site page.** `site/mock/contract.json`'s route list is untouched;
  `check.mjs` counts must be identical before and after. The only site edits are the two settings
  rows, the four renamed kinds, and one `practice` field.
- **A `UserSelect` inside a modal** (§C) — untested in this repo, and a modal Discord refuses to
  render is a dead button by another name.
- **A member-facing panel.** There is none today and this is a door swap.
- **`count` / `important_only` on `Logs`** — lost exactly as they were for every other panel; the
  site's Logs page has both.
- **Editing or deleting a message already relayed.** Neither door has it today, and a relayed DM
  cannot be unsent — inventing half of it would be worse than none.
- **A second `modmail_mode` value.** Two modes, not three; do not add `off` to make the
  `hide_commands_when_off` table rhyme (§A).
- **Rewriting the 1657-line cog.** Append the panel block at the FOOT, as the pings build did
  (its deviation 17); nothing already in the file is renamed or re-homed except the six inline
  bodies §F extracts.

### Cost, and the split

**Measured, wave-3, against its own estimates:** automod **370k**, chat **441k**, raidtrain
**473k**, role menus **529k** (est 420–500k). The calibration that matters:
**every build over ~450k ran past its estimate.**

This is bigger than role menus in *new behaviour* while being smaller in *cog size* (1657 lines
against 2164). Against that band it carries five things no wave-3 build had:

1. a **persistent sticky card** — a new `DynamicItem` set, a delete+post cycle, a debounce, a
   reconciler job and an explicit guard check for a side effect the guard cannot see;
2. a **schema migration** (two columns, 28 → 29) — the first panel build in the program to need one;
3. a **practice ticket** — effectively a second ticket lifecycle, with `own_channel` /
   `disown_channel`, a fake inbound path and four DM suppressions;
4. a **four-way log-kind rename** across `logkinds.py`, `contract.json`, `server.mjs` and two test
   files, plus five route `note()` deletions;
5. the panel itself — root, four sub-panels, six modals, a card, and the relay gate.

**Budget 480–600k, ~540k the likely landing, as one agent.** That is past the line.

⚠️ **SPLIT IT — two dispatches, in this order:**

| | Scope | Estimate | Lands |
|---|---|---|---|
| **Build A** | the `/modmail` root panel, `Setup…`, `Blocked…`, `Snippets…`, `Forget…`, `Logs`; the six §F extractions for block/unblock/snippets/settings; the log-kind rename + the five route `note()` deletions; `modmail_panel_minutes`; the doc/string sweep for the two Groups | **230–290k** | `/snippet` retired, `commands synced` 36 → **35** |
| **Build B** | the schema migration; the sticky card + reconciler job; `modmail_reply_style` + the relay gate; the ticket card's four moves + `send_reply`/`add_note` extraction; the practice ticket; retiring `/areply` `/note` `/close`; `/reply`'s F-M5 answer | **270–330k** | `commands synced` 35 → **32** |

**Why this cut and not another:** A is mechanical — extract, rename, re-point, sweep — and touches
no runtime behaviour a member can see. B is where every genuine risk lives (a migration, a message
delete, a relay gate on a path that already works, and a guard widening). Two 280k agents that each
land beat one 540k agent that dies at 90%. B depends on A only for `Panel` subclass and
`modmail_panel_minutes`, so it starts from A's merge.

**Prep before either dispatch:** clean tree, a fresh usage read, and a brief telling the agent to
commit at clean boundaries, one layer at a time —

*Build A:* (1) the pure additions to `black_bloc/modmail.py` + `tests/test_modmail.py`; (2) the
extractions + the route `note()` deletions + `logkinds` + `tests/test_logkinds.py` +
`tests/api/tools/test_modmail.py` (the riskiest layer, worth landing alone); (3) the panel +
`tests/cogs/moderation/test_modmail.py`; (4) the doc/string/site sweep + `tests/test_bot.py`.

*Build B:* (1) the migration + `tests/storage/test_db.py`, **landed and merged on its own**;
(2) the card + `bump_card` + the reconciler job; (3) the relay gate + `modmail_reply_style`;
(4) the practice ticket; (5) the retirement of the three commands + the sweep.

— so a kill costs the last layer rather than the build.

### Expected deviations

Things the build will most likely have to do differently; naming them here is cheaper than
discovering them at review:

1. **The card's rows are Discord's rows, not this document's groupings** (role-menus deviation 3).
   Five buttons is exactly the cap; if F-M7 goes (b) the snippet button needs the sixth slot and
   something moves to row 1.
2. **`ReplyModal`'s snippet select may need to be a `RadioGroup`** for small sets and a `Select`
   above some threshold, the way `vote_picker` (`polls.py:1060–1090`) already branches. Follow that
   function rather than inventing a second rule.
3. **`bump_card` may need to live on the bot rather than the cog** if the website's reply route
   reaches it — `api/tools/modmail.py` calls module-level functions, not cog methods, so
   `bump_card` is module-level and takes `bot`.
4. **The `practice` short-circuit may be cleaner as a `deliver_dm` guard than four call-site
   checks.** One place beats four; the build says which it chose.
5. **`answer_lines` `:777` may not survive at all** — the panel renders lines into an embed, and
   `clamped` (`panels.py:108`) is the embed-side equivalent of `chunk_lines`
   (`modmail.py:54`). Do not delete `chunk_lines`; `/reply`'s refusals still use it.
