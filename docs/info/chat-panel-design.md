# Chat — `/chat` is ONE command that opens a panel (wave 3)

> **Audience:** the build agent and the reviewer, and the owner for §I. **Status:** TRACKED ·
> ✅ **LIVE since v75** (`251dd14`, 2026-09-04 15:58; built on `worktree-agent-ab33797d235cf0d96` for
> 441k, five commits off `5db58fb`; landing entry in `docs/DONE.md` 2026-09-04). Still live at
> **v108** (`73e2e44`, 2026-09-11 00:37). The `path:line`
> keys below are the PLANNING-time ones and were not re-read after the build — `code-notes.md`'s
> `# Chat panel (wave 3)` section is the post-merge map. Sweeps **155–162**.
>
> **Since then, four things this document predates:**
> 1. **v78** (`3429233`) — `HIDDEN_WHEN_OFF` grew from one key to fourteen, so `chat_mode:
>    ("chat",)` EXISTS now (`command_visibility.py:21`). §E's last row and §I's second settled
>    bullet are history: `/chat` DOES vanish while the mode is off, behind `hide_commands_when_off`.
>    ⚠️ **`/memory` is the one carve-out** — `chat_memory_mode` went in at v78 and was taken back
>    out the same day (`51b5164`, *"fourteen features hide, not fifteen"*), because memory off
>    deletes nothing and the site is staff-only, so the panel is a member's only door to the notes
>    held about them (KI-14).
> 2. **v84** (`ce97de0`) — `LOG_LEVEL_COMMANDS` corrected for all 17 features; `chat_log_level`'s
>    help now names `/chat` ▸ **Logs**, not a retired `/chat logs`.
> 3. **v88** (`794d3aa`) — the cog's remove-confirm goes through the library:
>    `cogs/content/chat.py:517 open_remove_confirm` wraps `panels.confirm` + `confirm_items`
>    (`:55–56`).
> 4. **v90/v91** (`7c59eb1`, `604226f`) — the personality roster became a SYNCED manifest:
>    `black_bloc/personality_pool.json` (11 tropes) drives `personas.py`, `sync_tropes`/`sync_pool`
>    replaced `seed_tropes`, two log kinds `chat.pool_synced` / `chat.pool_retired`
>    (`logkinds.py:166`, `:202`) and two keys `personality_pool_sync` / `personality_pool_peer_url`
>    joined the registry. The counts this header measured are unchanged by it —
>    `PERSONALITY_CHOICES` is still **13** and `TROPE_NAMES` still **11**, re-measured today.
>
> **Last verified: 2026-09-11 08:47** — re-measured in this tree at `1d090e5`: `chat_panel_minutes`
> registered (registry **202** keys), `black_bloc/chat_panel.py` exists, and every label §C names
> still reads the same string — `PERSONALITY_MOVE` / `KNOWLEDGE_MOVE` (`chat_panel.py:159–160`),
> `WRITE_MOVE` / `FIND_MOVE` (`:165–166`), `VOICE_PLACEHOLDER` / `MOOD_OFF_PLACEHOLDER` /
> `MOOD_ON_PLACEHOLDER` / `NOTE_PLACEHOLDER` (`cogs/content/chat.py:161–164`). `site/mock/contract.json`
> now holds **150 routes / 17 pages** (142 at the build — later features added them, not this one).
> ⚠️ **NOT checked in this pass:** anything in a Discord client or a browser, no boot, no pytest, no
> ruff, no `check.mjs` run, no model provider called; `chat_llm_mode` was not read on the live guild.
>
> **Before that, 2026-09-04** — every `path:line` below was READ against `main` at `bf3e447`
> (the working tree is `4336a66`, a docs-only commit on top of it; **no source file differs**),
> in `black_bloc/cogs/content/chat.py` (757 lines), `black_bloc/knowledge.py` (554),
> `black_bloc/personas.py` (407), `black_bloc/chat_llm.py` (705), `black_bloc/chat.py` (1100),
> `black_bloc/panels.py` (194), `black_bloc/settings_store.py` (1688),
> `black_bloc/api/tools/chat.py` (834), `black_bloc/logkinds.py` (462),
> `black_bloc/command_visibility.py`, `black_bloc/guard.py`, `tests/test_bot.py`,
> `tests/cogs/content/test_chat.py` (1252, **72 tests**), `site/public/assets/labels.js`,
> `site/mock/server.mjs`, `docs/access/sweeps.md`, `docs/access/OWNER_GUIDE.md`,
> `docs/info/code-notes.md`.
> **Measured, not assumed:** `CHAT_MODES = ("off", "on")` (`settings_store.py:108`) and
> `CHAT_LLM_MODES = ("off", "on")` (`:118`) — ⚠️ **there is no `shadow` mode anywhere in chat**, so
> every mode crossing below is two-way; `command_visibility.py:16–20` has **no** chat entry, so
> nothing vanishes when a chat mode is off; `tests/test_bot.py:190` asserts **38** top-level
> commands; `docs/access/sweeps.md` ends at row **143**; `docs/access/OWNER_GUIDE.md` has **zero**
> matches for "chat" (measured), so this build ADDS a row rather than editing one;
> `PERSONALITY_CHOICES` is **13** entries (`personas.py:228`) and `TROPE_NAMES` **11** (`:226`) —
> both under Discord's 25, so no select here is capped except Knowledge.
> ⚠️ **NOT verified: anything was run.** No boot, no pytest, no ruff, no `check.mjs`, nothing
> against live Discord. The `path:line` keys will drift as the three sibling wave-3 branches merge
> — **trust the anchor text, not the number.**
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`voice-panel-design.md`](voice-panel-design.md) for
> shape, [`pings-panel-design.md`](pings-panel-design.md) for the staff Settings sub-panel,
> [`memory-panel-design.md`](memory-panel-design.md) for the sibling feature. Feature behaviour is
> [`phase11-design.md`](phase11-design.md) (Chat 2) and [`phase14-design.md`](phase14-design.md)
> (Chat step 3). ⚠️ **`/memory` is NOT folded in** — it is a separate MEMBER panel, shipped v68 in
> wave 2; the only thing this design does with it is link to it from Status (§C).

## A. Measured today — one group, two nested groups, nine leaf subcommands

`chat` is an `app_commands.Group` (`cogs/content/chat.py:207`, `default_permissions=STAFF_ONLY`
`:209`) with two nested groups inside it: `knowledge` (`:211`) and `personality` (`:280`).
**Nine leaf subcommands over ONE top-level slot.** ⚠️ Every one is staff-gated — measured, there
is nothing member-facing to lose (`code-notes.md:4429` says the same).

| Subcommand | Line | Gate | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/chat status` | `:219` | `require_staff` `:221`, then ⚠️ **administrator** when `chat_status_admin_only` `:225` | ⚠️ **all inline** `:226–259`: `STATUS_MODE`/`STATUS_TIERS`/`STATUS_TURNS`/`STATUS_MONEY`/`STATUS_CLOSED` over `allowance` (`chat_llm.py:367`), `money` (`:213`), `tier_words` `:261`, `notes_words` `:274` |
| `/chat logs` | `:475` | `send_logs` carries its own `require_staff` | `send_logs(interaction, "chat", count, important_only)` (`actionlog.py:287`) |
| `/chat settings` | `:488` | `require_staff` `:490` | ⚠️ **inline** `:492–501`: `display_value` (`settings_store.py:1228`) over `CHAT_KEYS` `:96`. **Read-only on purpose** (`code-notes.md:3437`) |
| `/chat personality show` | `:284` | `require_staff` `:286` | ⚠️ **all inline** `:288–308`: `VOICE_NOW`/`VOICE_MEANS`/`VOICE_OFF`/`MOODS_HEADER`/`MOOD_LINE` over `list_tropes` (`personas.py:364`) |
| `/chat personality set` | `:310` | `require_staff` `:318` | ⚠️ **inline** `:320–334`: `store.set(PERSONALITY_KEY)` + reply + `log_action("chat.personality_mode")`. **No `kind_via`, no guards** |
| `/chat personality mood` | `:336` | `require_staff` `:341` | ⚠️ **inline** `:343–367`: `get_trope` `:347` → `set_enabled` (`personas.py:376`) → `forget_tropes` `:355` → `log_action`. **No `kind_via`, no guards** |
| `/chat knowledge add` | `:369` | `require_staff` `:378` | `clean_title`/`clean_body`/`clean_tag` `:385` → `add_section` (`knowledge.py:348`) → `log_action` `:402`. **No `kind_via`** |
| `/chat knowledge list` | `:410` | `require_staff` `:413` | `list_sections` (`knowledge.py:326`) + `search` (`:208`), rendered by `note_line` `:185`, capped at `KNOWLEDGE_LIST_MAX = 15` `:106` |
| `/chat knowledge remove` | `:442` | `require_staff` `:445` | `get_section` `:451` → guild check `:452` → ⚠️ **`SERVER` refusal** `:457` → `remove_section` `:461` → `log_action` `:467`. **No `kind_via`** |

**Shared functions the panel will call** (all already exist, none moves):
`knowledge.list_sections` `:326` · `get_section` `:341` · `add_section` `:348` · `update_section`
`:370` (⚠️ **no slash command calls it today — the site is its only door**) · `remove_section`
`:393` · `search` `:208` · `clean_title` `:294` / `clean_body` `:303` / `clean_tag` `:312` ·
`personas.list_tropes` `:364` / `get_trope` `:369` / `set_enabled` `:376` / `forget_tropes` `:388` ·
`chat_llm.allowance` `:367` / `money` `:213` / `tier_errors` `:396` · `actionlog.send_logs` `:287`.

**Limits, measured** — these are what the modals must respect:
`knowledge.TITLE_LIMIT = 100` `:27`, `BODY_LIMIT = 4000` `:28`, `TAG_LIMIT = 40` `:29`,
`SECTIONS_MAX = 200` `:25` (the ceiling `list_sections` reads). ⚠️ **Discord's `TextInput`
maximum is 4000, and `BODY_LIMIT` is exactly 4000** — so a note body fits a modal field with
nothing lost, and `clean_body` stays the refusal for anything longer arriving by another door.

**Settings keys, measured.** `KEY_TYPES` (`settings_store.py:225–250`) holds **26** keys starting
`chat_` — **18 chat proper** and **8 `chat_memory_*`**. The cog's `CHAT_KEYS` `:96` is
`tuple(key for key in KEY_TYPES if key.startswith("chat_"))`, so it also picks up `chat_log_level`
(generated at `:808`) and will pick up `chat_panel_minutes` **with no edit** once §D registers it.
Choices: `chat_mode` / `chat_llm_mode` two-way `:290–291`, `chat_personality` = the 13
`PERSONALITY_CHOICES` `:292`. Defaults at `:1521–1548`.

**Site routes, measured** (`api/tools/chat.py`, whole router behind `staff_dependency` `:317`):
`GET/POST /api/chat/intents` `:336`/`:353` · `PUT`/`DELETE /intents/{id}` `:387`/`:433` ·
`POST /intents/{id}/lines` `:452` · `PUT`/`DELETE /lines/{id}` `:486`/`:516` · `POST /try` `:533` ·
`GET /knowledge` `:583` · `POST /knowledge` `:589` · `PUT`/`DELETE /knowledge/{id}` `:616`/`:649` ·
`GET /personality` `:689` · `PUT /personality` `:696` · `PUT /personality/{name}` `:733` ·
`GET /spend` `:781`. Page: `chat.html` (`logkinds.FEATURE_PAGES["chat"]` `:105`), sections
**Intents · Try it · New intent · Knowledge · Personality · Spend & tiers · Settings · Memory**
(`site/public/assets/page-chat.js:437,507,556,743,827,898,940,1009`).

⚠️ **Five routes `note()` a `web.chat.*` kind by hand** — `:603`, `:636`, `:658`, `:718`, `:756` —
because the shared functions they call (`knowledge.add_section`, `personas.set_enabled`,
`store.set`) log nothing. The COG logs the same events with the bare kinds. That is checklist 34's
shape one step before it becomes a double-post, and §F is the fix.

**`commands synced` does NOT move.** `tests/test_bot.py:190` asserts **38** today (measured at the
v73 boot and pinned by `test_the_command_tree_stays_inside_discords_limits`). A `Group` already
counts as ONE top-level slot, so folding one group and its two nested groups into one command
leaves the count at **38** — exactly as `/memory`, `/poll` and `/birthday` did. ⚠️ **State the
delta (zero), never the absolute**: the build re-measures and edits `:190` only if a sibling
wave-3 merge moved it.

## B. The decision — one `/chat`, one staff panel

**`/chat` becomes a single `app_commands.command`; the `chat` group and both nested groups go.**
It **keeps `default_permissions=STAFF_ONLY`**, so `"chat"` stays in `STAFF_COMMANDS`
(`tests/test_bot.py:29`) and never joins `MEMBER_COMMANDS` — there is no member half to reveal
(§A, and `code-notes.md:4429` measured it). The runtime gate is still `still_staff`
(`panels.py:31`) before every move (P8); the UX lock is not the enforcement.

**What the panel owns:** the root Status block, **Personality…** (the voice select, the mood
pool), **Knowledge…** (list → pick → note card → Remove / Edit; Write one down…; Find…),
**Settings** (§D and fork F-C1), the two mode toggles, and **Logs**.

**What stays site-only** — the long tail the panel deliberately does not grow a second door for:
the **intents and lines** editor (four routes, an arbitrary number of rows per intent, trigger
chips), the **Try it** box, **New intent**, the **Spend & tiers** meters beyond the four Status
lines, and the **Memory** section. `chat.html` is behind `staff_dependency` (`:317`), so the
panel's **Open on the site** button is never a dead control for a caller who reached the panel.

**The states — three axes, all measured two-way.** There is no `shadow` anywhere.

| # | Where the caller is | `chat_mode` on | `chat_mode` off |
|---|---|---|---|
| S0 | staff, database down | `DB_UNAVAILABLE` (`settings_store.py:1100`) as the whole answer, no panel — `db_up` before the first read | same |
| S1 | staff, not administrator, `chat_status_admin_only` **on** (default `:1531`) | full panel, **no spend block**; a line saying what it is and who can read it (today's `STATUS_ADMIN_ONLY` `:91`, reworded — it must no longer say "run `/chat status`") | same |
| S2 | staff, spend readable | full panel with the spend block | + a line: @-mentions are not answered at all right now |
| S3 | any of the above, `chat_llm_mode` **off** (default `:1538`) | tiers block says every answer comes from the written lines (`STATUS_OFF_TAIL` `:127`); **Personality…** still opens and says the voice is not in use yet (`VOICE_OFF` `:158`) | same |
| S4 | any of the above, no notes written down | Knowledge… opens on an empty list with **Write one down…** only — no pick select, no **Find…** | same |
| S5 | any of the above, `chat_monthly_cap_usd` reached | the spend block carries `STATUS_CLOSED` `:136` | same |

⚠️ **The admin-only gate changes shape, and that is forced, not chosen.** Today
`chat_status_admin_only` refuses the WHOLE `/chat status` command. A panel cannot refuse itself —
the same command carries Knowledge and Personality, which a non-admin staffer may use. So the key
now hides the **spend block** and nothing else, and the panel says so in a sentence (P9). The key,
its default and its help text are untouched; only the unit it governs shrinks from a command to a
block.

P3 in one line: **no state renders a control whose shared function would refuse it.** **Remove**
never renders on a `server` note (`knowledge.py:69` would refuse it); a mood the site's own rules
forbid turning off is never on the *Turn a mood off…* select (§C, fork F-C4); **Find…** and the
pick select render only when notes exist; the spend block is absent, not greyed.

## C. The cards, the sub-panels, the modals

Each is a **re-render in place**, `retire(previous)` first (P6), `defer()` then
`edit_original_response` (P5), `db_ready` on every click (requests deviation 6), `still_staff`
before every move including the READS (pings deviation 10). `Refresh` and `Back` are **one button
each**, dispatched on a `where` attribute the view carries (pings deviation 9) — `root` /
`personality` / `knowledge` / `note` / `settings`.

**The root.** Embed = `status_lines` (§F) — today's `/chat status` output, unchanged in wording
except the admin sentence: mode + conversation model (`STATUS_MODE` `:126`), the two tiers
(`STATUS_TIERS` `:128` over `tier_words` `:261`), then, when readable, turns and money
(`STATUS_TURNS` `:132`, `STATUS_MONEY` `:135`), the notes count (`notes_words` `:274`) and any
ingest trouble (`STATUS_INGEST_TROUBLE` `:144`). ⚠️ **The status block is written out always, never
hidden behind a `Status` button** — the events build's deviation 10 precedent: a button that hides
the loudest warning loses it, and `last_ingest_error` `:199` is exactly such a warning.

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Personality…` → sub-panel | always | — |
| 0 | `Knowledge…` → sub-panel | always | — |
| 0 | `Settings` → sub-panel | always | — |
| 1 | `Stop answering @-mentions` / `Answer @-mentions` — **one button that says what it will do** | always | `set_mode(chat_mode)` (§F) |
| 1 | `Turn the conversation models off` / `on` — one button | always | `set_mode(chat_llm_mode)` (§F) — fork **F-C3** on the confirm |
| 2 | `Logs` → a NEW ephemeral followup (P11) | always | `send_logs(interaction, "chat")` — keeps its own `require_staff` |
| 2 | `Refresh` | always | — |
| 2 | `Open on the site` (link, `chat.html`) | an origin is configured | `panels.site_page_url(origin, "chat")` `:101` |

⚠️ **The root also carries one LINE, not a button, pointing at `/memory`** for the eight
`chat_memory_*` keys and for what the bot remembers about a person. `/memory` is a member panel
(`cogs/content/chat_memory.py:574`) and its site half is counts-only (phase 17 D5) — a staff button
into it would be a second door onto somebody else's data, which D5 settled against.

**Personality sub-panel.** Embed = today's `/chat personality show` lines `:288–305`, unchanged.

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` "The voice…" — **13 options** (`PERSONALITY_CHOICES` `personas.py:228`), the current one `default=True` | always | `set_voice` (§F) |
| 1 | `Select` "Turn a mood off…" over the enabled tropes that CAN be turned off | at least one qualifies | `set_mood(..., False)` (§F) |
| 2 | `Select` "Turn a mood on…" over the disabled tropes | at least one is off | `set_mood(..., True)` (§F) |
| 3 | `Back` · `Refresh` | always | — |

⚠️ **Two selects, not one toggle.** A single "pick a mood to flip it" control is P3's *two
spellings of one move* wearing a disguise: the option label would have to say both what the mood
is and what picking it does. Two selects each offer exactly one unambiguous move, and a select
that would be empty is not rendered at all. **13 and 11 are both under 25**, so neither needs
`capped_placeholder` — measured, not assumed.

⚠️ **Which moods can be turned off is fork F-C4.** The website already refuses two cases
(`api/tools/chat.py:747` the mood that IS the current voice, `:752` the last enabled mood while
the voice is `pool`); the Discord door refuses neither. Whichever the owner picks, the select and
`set_mood` must agree — the select offers exactly what the function would accept.

**Knowledge sub-panel.** Embed = `NOTES_HEADER` `:118` + `note_line` `:185` per row, through
`panels.clamped` `:86` so a long list cannot exceed `DESCRIPTION_LIMIT` (4000).

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` "A note…" over up to **25** rows, `capped_placeholder(shown, total)` (`panels.py:66`) pointing at the Knowledge section on the site | at least one note | → the note card |
| 1 | `Write one down…` → `NoteAddModal` | always | `add_note` (§F) |
| 1 | `Find…` → one-field modal (query) → re-renders the list filtered by `search` (`knowledge.py:208`, `limit=KNOWLEDGE_LIST_MAX` `:106`) | at least one note | `search` — a pure read, no write, no log row |
| 2 | `Back` · `Refresh` | always | — |

⚠️ **The 25 cap is real here and only here.** `list_sections` reads up to `SECTIONS_MAX = 200`
(`knowledge.py:25`) and the daily ingest alone writes one `server` row per channel-with-a-topic
plus roles, events, role menus and small-role holders — so passing 25 is ordinary, not an edge.
`capped_placeholder`'s sentence and **Find…** are the two ways past it, and **Find…** is why the
cap is acceptable rather than a hidden list.

**The note card** (`where = "note"`). Embed = the note whole: title, `source`, tag, body clamped.

| Control | Rendered when | Shared function |
|---|---|---|
| `Remove` (danger) → `Yes, remove it` / `Keep it` | ⚠️ `source == STAFF` (`knowledge.py:12`) | `remove_note` (§F) |
| `Edit…` → `NoteEditModal`, prefilled | `source == STAFF` **and** fork **F-C2** = (a) | `edit_note` (§F) |
| `Back` | always | — |

⚠️ **A `server` note renders NEITHER, and the card SAYS why** — `SERVER_ROW_IS_NOT_YOURS`
(`knowledge.py:69`) as a line, not a refusal after a click. The daily loop owns those rows
(`replace_server_sections` `:537` deletes and rewrites them all), so a button here would be
undone by tomorrow. Hiding the row entirely would be worse: the list is how staff see what the bot
actually knows.

**Settings sub-panel** — read-only lines plus, on fork **F-C1** = (a), one modal. Embed =
`display_value(key, store.get(guild_id, key))` per key, the shape `/chat settings` prints today
`:493–496`, through `clamped` and split into two blocks: the **chat** keys and the eight
`chat_memory_*` keys under a line naming `/memory` and the Chat page's Memory section as their
home. Row 0: `Limits…` (F-C1 (a) only). Row 1: `Open on the site` · `Back` · `Refresh`.

**Modals** — all `AnswersErrors` + `discord.ui.Modal`, one shape (P12). `panels.NoteModal`
(`:154`) is a ONE-field modal and is used for **Find…** only; the others are new multi-field
modals of the same shape.

| Modal | Fields | Bounds |
|---|---|---|
| `NoteAddModal` | title · body (paragraph) · tag (optional) | `max_length` = 100 / 4000 / 40, from `knowledge.TITLE_LIMIT` `:27` / `BODY_LIMIT` `:28` / `TAG_LIMIT` `:29` — **imported, never re-typed**. `clean_*` still runs and its `KnowledgeError` is answered in words (`:75`) |
| `NoteEditModal` (F-C2 (a)) | the same three, `default=` the stored values | same |
| `FindModal` (`panels.NoteModal`) | one line, the query | 200, the shape `memory`'s `ForgetWordsModal` uses (`cogs/content/chat_memory.py:536`) |
| `LimitsModal` (F-C1 (a)) | `chat_cooldown_seconds` · `chat_person_hourly_turns` · `chat_daily_turns` · `chat_monthly_cap_usd` · `chat_panel_minutes` | ⚠️ **five fields is Discord's maximum, so nothing else can join it.** A modal has no `app_commands.Range`: each field is validated with `coerce_value` (`settings_store.py:1111`) which already knows `KEY_MAX`/`KEY_MIN` `:300`/`:323`, and a bad field refuses the **whole** dict — the pings `NamesModal` rule (its deviation 7), so a good field cannot sneak through beside a bad one |

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `chat_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Registered in its own appended block exactly where `voice_panel_minutes` sits — `settings_store.py:1070` (`KEY_TYPES.update`), `:1071` (`KEY_HELP.update`), and a `default()` branch beside `:1607` — so the parallel wave-3 branches merge textually. Help text carries KI-20's warning **verbatim in shape**: 15 or more loses the "gone quiet" footer because Discord's interaction token expires at 15 minutes. ⚠️ **No `KEY_MAX` entry** — measured, no `*_panel_minutes` key has one, and KI-20 says the value is deliberately not clamped |

**Site rows the new key needs** (three edits, no route change):

| File | Row |
|---|---|
| `site/public/assets/labels.js` | `chat_panel_minutes: 'How long the /chat panel stays live'` — beside `voice_panel_minutes` `:51` |
| `site/mock/server.mjs` | the settings tuple, copying `voice_panel_minutes` `:420` byte-for-byte with the name and command swapped: `['chat_panel_minutes', 'int', 10, 10, "minutes the /chat panel stays live …", null, 1440]` |
| `site/mock/server.mjs:3736–3740` | append `'chat_panel_minutes'` to `CHAT_SETTING_KEYS`, so the mock Chat page's Settings section shows it the way the real one will |

**Existing keys this panel READS or WRITES, all otherwise untouched:** `chat_mode` (`:225`,
choices `:290`, default `"on"` `:1521`), `chat_llm_mode` (`:236`, choices `:291`, default `"off"`
`:1537`), `chat_personality` (`:238`, choices `:292`, default `COOKOUT` `:1541`),
`chat_status_admin_only` (`:242`, default `True` `:1531`), and — on fork F-C1 (a) —
`chat_cooldown_seconds` `:226`, `chat_person_hourly_turns` `:239`, `chat_daily_turns` `:240`,
`chat_monthly_cap_usd` `:241`. `chat_log_level` reaches the panel through `send_logs`.

⚠️ **`chat_panel_minutes` appears on the Settings card for free.** `CHAT_KEYS`
(`cogs/content/chat.py:96`) is computed from `KEY_TYPES` by prefix, so registering the key is the
only edit; nothing in the cog lists keys by hand. Say so in `code-notes.md` — a reader will
otherwise look for the missing edit.

**Nothing else here is a decision.** The 25 cap, the five-field modal ceiling and the five-per-row
button cap are Discord's; the button table is the state machine in §B; the title/body/tag limits
are `knowledge.py`'s and predate this build; and the two behaviours a reader might mistake for
decisions — staff reaching every control, and the panel refusing in words rather than dying — are
**settled by the standing rules**, not chosen here, so neither becomes a key.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `chat` Group | `cogs/content/chat.py:207` | the one `@app_commands.command(name="chat")`, keeping `default_permissions=STAFF_ONLY` |
| `chat_knowledge` Group + 3 children | `:211`, `:369`, `:410`, `:442` | the Knowledge sub-panel, its note card and two modals |
| `chat_personality` Group + 3 children | `:280`, `:284`, `:310`, `:336` | the Personality sub-panel and its three selects |
| `chat_status` · `chat_settings` · `chat_logs` | `:219`, `:488`, `:475` | the root status block, the Settings sub-panel, the `Logs` button |
| the inline status/voice/mood/note bodies | `:226–259`, `:288–308`, `:320–334`, `:343–367`, `:385–408`, `:451–473`, `:492–501` | the §F functions |
| `LOGS_GROUPS["chat"]` | `tests/test_bot.py:17` | **deleted** — `/chat` is no longer a Group with a `logs` child, so the loops at `:167` and `:213` would `KeyError` |
| the children assertion | `tests/test_bot.py:172–178` | **deleted** — there are no children |
| `"chat"` in `STAFF_COMMANDS` | `tests/test_bot.py:29` | **kept** (§B) |
| `assert len(top) == 38` | `tests/test_bot.py:190` | ⚠️ **unchanged** — a group was already one slot. Re-measure; edit only if a sibling merge moved it |
| `HIDDEN_WHEN_OFF` | `command_visibility.py:16–20` | **nothing to change** at the build — measured, chat had no entry. ⚠️ **Since v78** it has one (`chat_mode: ("chat",)`, `command_visibility.py:21`), so `/chat` DOES vanish when the mode is off unless `hide_commands_when_off` is turned off. `/memory` is deliberately NOT in the map (`51b5164`) |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently
tells somebody to run something that will not exist:
`cogs/content/chat.py:92` (`STATUS_ADMIN_ONLY` — "`/chat status` shows…"; and see §B, its *unit*
changes too) · `:110` (`NO_SUCH_NOTE` — "`/chat knowledge list` shows…") · `:114` (`NO_NOTES` —
"`/chat knowledge add` starts the list") · `:165` (`NO_SUCH_MOOD` — "`/chat personality show`
lists them") · `:443` (the `note_id` describe string — the parameter goes with the subcommand) ·
`black_bloc/chat_llm.py:397` (docstring, "so `/chat status` can say a tier is down") ·
`black_bloc/settings_store.py:620` (`chat_home_channel_id` help — "`/chat logs` and the Logs page
count how often it happens") · `:679` (`chat_status_admin_only` help — "on keeps `/chat status`…
to server administrators", ⚠️ **and its meaning changed**, per §B).

**Site touch points** — no route is added, removed or renamed, so `node site/mock/check.mjs` must
report the **same** page/route counts before and after (17 pages / 142 routes at v73, measured in
`voice-panel-design.md`'s Deviations foot — re-measure, do not trust the number):
`site/public/assets/labels.js:129` (`chat_status_admin_only: 'Whether /chat status is for
administrators only'`) · `site/mock/server.mjs:357` (the `chat_home_channel_id` help copy) ·
`:370` (the `chat_status_admin_only` help copy). `site/mock/contract.json` is untouched.

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md:122` (row 33), `:123` (row 34),
`:124` (row 36), `:125` (row 37), `:141` (row 35) — rewritten in place, not added to;
`docs/info/feature-list.md:48` (the F10 row) · `docs/info/phase11-design.md` and
`docs/info/phase14-design.md` each get a dated "superseded by the panel" line at the top,
**not** a rewrite (phase 14 `:78`, `:105`, `:126`, `:137`, `:144` describe the subcommands) ·
`docs/info/panels-program.md:82` (the Chat row → shipped) · `docs/info/README.md` gains a row for
this doc · `docs/access/OWNER_GUIDE.md` — ⚠️ **it names chat NOWHERE today (measured, zero
matches)**, so this build ADDS one "Change how the bot talks, or what it knows" row beside the
voice row (`:79`) and moves the sweeps count (`:5`, `:82`) · `docs/info/code-notes.md` re-keyed at
the merge — the chat anchors cluster at `:2019–2031`, `:3018`, `:3057–3063`, `:3437`, `:4160–4161`,
`:4272`, `:4315`, `:4399–4401`, `:4429`, under the headings at `:1982`, `:3001`, `:4082`, `:4247`,
`:4352`, `:4450`. ⚠️ **`code-notes.md:3437` states the read-only-settings rationale and must be
superseded or confirmed by whatever fork F-C1 lands on** — it is the one note this build can make
into a lie.

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB layer stays exactly where it is.** `knowledge.py` and `personas.py` are already pure
modules that both doors import; nothing moves out of them, so `tests/test_knowledge.py`,
`tests/test_personas.py` and `tests/api/tools/test_chat.py` keep their assertions — which is what
makes their staying green the proof the refactor changed nothing (wave-0 deviation 4).

**New, in a NEW pure module `black_bloc/chat_panel.py`** (there is none today; nothing existing
moves into it, so no import outside the cog and the router changes). ⚠️ **Not the foot of
`black_bloc/chat.py`**: that module is the INTENTS engine, `api/tools/chat.py` imports 24 names
from it (`:11–35`), and it already reaches the cogs through `chat_data` (`chat_data.py:9–11`) —
a new file keeps the import edge one-way and testable. Each function does **ONE write and ONE log
row**, takes `via: str = VIA_DISCORD`, and builds its kind with `kind_via` (`logkinds.py:365`,
checklist 34):

| Function | Replaces · what it adds |
|---|---|
| `set_voice(bot, guild, actor, wanted, *, via)` | cog `:320–334` **and** route `:717–724`. Gains the route's two guards (unknown name `:711`, the trope is disabled `:713`) so both doors refuse identically, and `kind_via("chat.personality_mode", via)` |
| `set_mood(bot, guild, actor, name, enabled, *, via)` | cog `:343–367` **and** route `:741–762`. Gains the route's guards per fork **F-C4**, calls `forget_tropes` `:355` on every path, and `kind_via("chat.trope_enabled"/"chat.trope_disabled", via)` |
| `add_note(bot, guild, actor, title, body, tag, *, via)` | cog `:385–408` **and** route `:594–609`. `clean_*` inside, `KnowledgeError` returned as words, `kind_via("chat.knowledge_added", via)` |
| `remove_note(bot, guild, actor, section_id, *, via)` | cog `:451–473` **and** route `:654–664`. Keeps the guild check `:452` and the `SERVER` refusal `:457`, `kind_via("chat.knowledge_removed", via)` |
| `edit_note(bot, guild, actor, section_id, fields, *, via)` | route `:623–642` only today. `kind_via("chat.knowledge_edited", via)` — ⚠️ **the bare kind `chat.knowledge_edited` is ALREADY registered** (`logkinds.py:178`) and nothing has ever written it; this is what makes fork F-C2 (a) cheap |
| `set_mode(bot, guild, actor, key, value, *, via)` | the two root toggles. New kind `chat.mode` joining `logkinds.ROUTINE` beside `chat.route` `:189` — ⚠️ **there is no chat mode log kind today**, because no command has ever set a chat mode; `/settings set-value` is the only door and it logs through the store |
| `save_settings(bot, guild, actor, changes, *, via)` | fork **F-C1** (a) only. The `pings.save_settings` shape byte-for-byte (`black_bloc/pings.py:958–980`): validate **every** key with `coerce_value` BEFORE the first write, then one `store.set` per key, then ONE `chat.settings` row (new, joining `ROUTINE`) |
| `status_lines(bot, guild, actor, *, spend, notes, tiers)` | the pure half of `:226–259`, so the embed and any later `/api/chat/status` read one list |
| `panel_state(...)` + `PANEL_MOVES` + `panel_buttons(state, *, staff)` | §B/§C's tables AS DATA, proved by a parametrised test. The `youtube.card_buttons` / `pings.panel_buttons` shape (a composing function over a `NamedTuple`, pings deviation 1), not a dict keyed by a boolean tuple |
| `PANEL_MINUTES_KEY = "chat_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:97`), exactly as `chat_memory.minutes_for` does (`cogs/content/chat_memory.py:207`) |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER`, and the panel sentences | wave-0 deviation 1: the footer is a whole sentence, not a format string |
| `mood_options(rows, voice)` | which tropes may be turned off and which on — the ONE place fork F-C4's rules live, read by both the select and `set_mood` so they cannot disagree |

**The route half is not optional, and it is mechanically enforced.** After the extraction, the
five `note()` calls at `api/tools/chat.py:603`, `:636`, `:658`, `:718`, `:756` are **deleted** and
each route calls the function above with `via=VIA_WEBSITE`. ⚠️ **The log rows do not change**:
`kind_via("chat.knowledge_added", VIA_WEBSITE)` is `"web.chat.knowledge_added"`, byte-identical to
what `note()` writes today (`logkinds.py:365–367`). What changes is that there is now exactly one
writer. Leaving a `note()` in place makes
`tests/test_logkinds.py::test_a_route_never_notes_an_event_its_shared_path_already_logged` `:447`
fail — an AST walk that finds a route calling a shared path that logs and then logging the same
bare kind on top of it. That test is the guard; do not work around it.

⚠️ **`details` shape changes for those five rows.** Today the routes pass e.g.
`{"title": title, "via": VIA_WEBSITE}` `:608`; afterwards the shared function's details win
(`{"id": …, "title": …, "via": …}`, the cog's shape at `:407`). That is the point — one event, one
shape — but it is a visible difference on the Logs page and belongs in the Deviations foot.

**Two things to reuse, never re-copy:** the cog's own `usable_db` `:215` duplicates what
`panels.db_up` `:58` and `db_ready` `:48` do at the interaction boundary — the panel uses the
library's and `usable_db` survives only for the `_ingest` loop `:513` and `seed_guilds` `:572`,
which have no interaction to answer through. And `panels.clamped` `:86` for every embed
description, never a fourth local copy (checklist 15; `voice`'s deviation 8 is the standing note).

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/content/test_chat.py` (1252 lines, **72 tests** today) | `/chat` answers ephemerally with a panel; **parametrised over S0–S5 × `chat_mode` × `chat_llm_mode` × admin/not — each renders exactly its §B row and no other**; the two mode buttons are never both spellings at once; `Remove` and `Edit…` are absent on a `server` note and the card says why; the note pick select is absent with no notes; `Find…` is absent with no notes; the spend block is absent for a non-admin while `chat_status_admin_only` is on and PRESENT when it is off; every move calls its §F function with `via` untouched (mock it); `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-card moves nothing (`still_staff` at every site, reads included); `db_ready` after a defer; timeout disables every item and a re-render `retire`s what it replaced. ⚠️ **The 72 existing tests that exercise `on_message`, the cooldown, the wave, the staff note and the ingest loop must survive UNCHANGED** — none of that is touched, and their staying green is the proof |
| `tests/test_chat_panel.py` (**new file**) | `panel_buttons` for every state; `mood_options` against fork F-C4's rules; `status_lines`; `panel_minutes`; each `set_*` / `*_note` function writing once and logging once, with `via` at both values, asserting `kind_via` produced the `web.` head |
| `tests/test_settings_store.py` | `chat_panel_minutes` round-trips, defaults **10**, has help text, and is picked up by a prefix scan the way `CHAT_KEYS` does |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `chat`; the children assertion `:172–178` goes; `"chat"` stays in `STAFF_COMMANDS`; the tree-limit test **recounts and is expected to be UNCHANGED at 38** |
| `tests/test_logkinds.py` | `chat.mode` (and `chat.settings` on F-C1 (a)) classify as routine; the AST guard at `:447` passes with the five `note()`s gone |
| `tests/api/tools/test_chat.py` | ⚠️ the five rewritten routes' tests move to asserting the shared function was called with `via=VIA_WEBSITE`; **every other test in the file must stay green with no edit** — that is the proof no route moved |
| `tests/test_knowledge.py` · `tests/test_personas.py` (unchanged) | ⚠️ **must stay green with no edit** — the proof the DB layer did not move |

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers — the delta must
   be ZERO** (a group was already one slot; requests deviation 7). With no token, measure it the
   only other way: `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` counts
   the real tree. Checklist 10 — a check that could not run is not a check that passed.
2. The parametrised state test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.chat_panel, black_bloc.cogs.content.chat,
   black_bloc.api.tools.chat, black_bloc.knowledge, black_bloc.personas,
   black_bloc.settings_store"` — the substitute for a boot, and it is what catches the one new
   import edge this build creates (wave-0 deviation 5). ⚠️ `settings_store` is in the line on
   purpose: it already imports `personas` (`:34`) and `chat_memory` (`:18`), and a careless
   `chat_panel` → `settings_store` → `personas` edge is where a cycle would appear.
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (**expect the counts unchanged** — no route
   changes); `node --input-type=module --check < site/public/assets/labels.js`.
5. Checklist sweep before reporting — **8** and **30** (`AnswersErrors` on every modal, select and
   view), **11** (`allowed_mentions` on every interpolated send; note titles, note bodies and mood
   names are all staff-editable text), **15/17** (the duplicate `usable_db`, §F), **22** (the
   `LimitsModal` fields have no `app_commands.Range` — `coerce_value` is the bound, and the
   `NoteAddModal` lengths come from `knowledge.py`'s constants, never re-typed), **24** (defer
   before the knowledge reads — `list_sections` is a query per click), **26** (`chat_ignore_channels`
   and `chat_ignore_categories` are list-typed and stay site-only; this build adds no list key),
   **28** (`loop_health` `:202` and the `_ingest` error still surface in the status block), **33**
   (§D), **34** (§F's five deleted `note()`s — run the AST guard explicitly).

⚠️ **TEST_MODE stands and it bites this feature specifically.** `black_bloc/guard.py:147`
installs a tree `interaction_check` that refuses any command whose `channel_id` is not
`TEST_CHANNEL_ID` and is not a DM (`allows_interaction` `:94`), so **`/chat` must be run in
`#black_bloc-logs`** — every sweep row below assumes that. The panel itself is ephemeral and
posts nothing to a room; the only thing chat sends into a channel is the `on_message` reply and the
staff route note, and both already go through `allows_channel` (`cogs/content/chat.py:645`, `:738`)
and are untouched by this build.

**Sweep rows — the build claims them, this document does not.** `docs/access/sweeps.md`'s last row
today is **143**, but ⚠️ **four wave-3 design docs are being written in parallel and their builds
will land in an order nobody has fixed yet**, so the build **numbers these at BUILD time starting
at the next free row** and renumbers at landing. Rows 33, 34, 35, 36 and 37 are rewritten in
place, not added.

| Do this | Expect |
|---|---|
| `/chat` in `#black_bloc-logs` as a Lead | ONE ephemeral panel: the mode and tier lines, the notes count, then **Personality… · Knowledge… · Settings**, the two mode toggles, **Logs · Refresh · Open on the site**. Nothing says `/chat status`, `/chat knowledge` or `/chat personality` anywhere |
| the same as a staffer who is NOT an administrator, `chat_status_admin_only` on | the whole panel opens; the turns-and-money lines are absent and one sentence says what they are and who can read them. Then set the key off and re-open: they appear |
| `Personality…` → **The voice…** → `noir`; then **Turn a mood off…** → `peppy`; then **Turn a mood on…** → `peppy` | the voice line changes and says it applies from the next answer on; the mood moves between the two selects; ONE `chat.personality_mode` and one `chat.trope_disabled`/`chat.trope_enabled` row each, `via: discord`. With `chat_llm_mode` off the card also says nothing is using the voice yet |
| `Personality…` with the voice set to a mood, then **Turn a mood off…** | that mood is **not on the select at all** (fork F-C4) — the panel never offers a move its own function would refuse |
| `Knowledge…` → **Write one down…** → title/body/tag; then pick it on **A note…** | the note is saved and named by number, one `chat.knowledge_added` row; the card shows it whole with **Remove** and **Edit…** |
| pick a `server` note on **A note…** | the card shows it, has **neither** Remove nor Edit, and says the daily read owns it and to change the channel/role/event instead |
| **Remove** → **Yes, remove it**; then **Find…** with a word from a note | the note goes and the list re-renders without it, one `chat.knowledge_removed` row; **Find…** filters the list to what matches and says so. Past 25 notes the picker's placeholder says how many of how many and points at the site |
| the two mode toggles, then `@Black Bloc hello` | with answering off the bot says nothing at all; turning it back on answers again. Each flip leaves ONE `chat.mode` row |
| `Settings`, then `Logs`, then leave the panel `chat_panel_minutes` (10) minutes | Settings lists every `chat_*` key with its value and names `/memory` as the home of the memory ones; **Logs** answers a NEW message and the panel stays; then every control greys out and the footer reads *This panel has gone quiet — run /chat again* |
| the website: Chat page → Knowledge → add a note; Personality → change the voice | one `web.chat.knowledge_added` and one `web.chat.personality_mode` row each — **not two**, and the Discord panel picks the change up on **Refresh** |

## I. The genuine forks — the owner decides, one at a time

Settled first, by the standing rules, so they are NOT put to him:

- ✅ **`/chat` stays staff-locked** (`default_permissions=STAFF_ONLY`). Every one of its nine
  subcommands is `require_staff` today and there is no member half; `code-notes.md:4429` measured
  it. Members reach chat by @-mentioning the bot, which is not a command.
- ✅ **`/chat` does not vanish when a mode is off.** `command_visibility.HIDDEN_WHEN_OFF`
  (`:16–20`) has no chat entry to remove, and the owner answered this shape on 2026-09-03 13:47
  ("Visible") for applications. ⚠️ **REVERSED at v78** (2026-09-05, *"a feature turned off on the
  portal takes its `/command` with it"*): the map now names all fifteen features, `chat_mode`
  included, behind `hide_commands_when_off` (default true).
- ✅ **`chat_status_admin_only` now hides the spend BLOCK, not the whole command.** Forced by §B:
  the command that carried Status also carries Knowledge and Personality, which a non-admin
  staffer may use.
- ✅ **`/memory` is not folded in and gets no staff button** — phase 17 D5 made staff's view of a
  profile counts-only; a button here would be a second door onto somebody else's data.
- ✅ **The five route `note()`s go.** Checklist 34, and the AST guard enforces it.

**Four questions are genuinely his:**

- **F-C1 — how much does the Settings card WRITE?** `code-notes.md:3437` says `/chat settings` is
  read-only *on purpose*: "`/settings set` already changes any key, and a second writer would be a
  second home for the same decision." The pings panel went the other way and made its Settings
  writable. Chat has ~20 keys, which is past what a panel can edit without becoming the Settings
  page.
  - **(a) Read-only lines, plus one `Limits…` modal for the five numbers** — `chat_cooldown_seconds`,
    `chat_person_hourly_turns`, `chat_daily_turns`, `chat_monthly_cap_usd`, `chat_panel_minutes`.
    Exactly Discord's five-field maximum, and they are the numbers a staffer actually changes
    (the cap drill is sweep row 35). Everything else stays read-only and site-owned.
    **Recommended.**
  - (b) Fully read-only, as today. Cheapest, and checklist 33 is already satisfied twice over
    (Settings page + `/settings set-value`) — but a panel that can show a number and not change it
    is the thing the panels program exists to stop.
  - (c) A full editor: selects for every enum and bool. Five bool toggles plus three enum selects
    plus the numbers is two more sub-panels, and it duplicates the Settings page wholesale.
- **F-C2 — does the panel EDIT a knowledge note?** `knowledge.update_section` (`:370`) exists and
  the log kind `chat.knowledge_edited` is **already registered** (`logkinds.py:178`), but the
  website is its only door today; a staffer in Discord can add and remove but not fix a typo.
  - **(a) Add `Edit…` on the note card** — one prefilled modal reusing `NoteAddModal`'s three
    fields and `edit_note` (§F), which the route then also calls with `via`. Small, and it removes
    the one asymmetry between the two doors. **Recommended.**
  - (b) Site-only. Remove-and-rewrite is two clicks and a modal, which is not much worse, and it
    keeps the card at two buttons.
- **F-C3 — does turning the conversation models ON need a confirm?** `chat_llm_mode` is the switch
  that starts spending money (`chat_monthly_cap_usd`, default $20, `:1547`). Every other panel's
  mode toggle is one click.
  - **(a) One click, like every other panel**, with the money line already on the root embed above
    it so nobody flips it blind. **Recommended** — the cap is the real guard, it is enforced on
    every call (`chat_llm.py:367`), and a confirm on one of two adjacent toggles reads as an
    inconsistency rather than as care.
  - (b) A `Yes, start spending` / `Keep it off` confirm on the ON direction only, the shape
    `/memory`'s destructive moves use. The OFF direction stays one click, because
    access-reducing moves fail safe.
- **F-C4 — do the mood-pool guards move onto the Discord door?** The website refuses two things
  the Discord command allows: turning off the mood that IS the current voice
  (`api/tools/chat.py:747`), and turning off the LAST enabled mood while the voice is `pool`
  (`:752`). Today `/chat personality mood` does neither, and doing it leaves the pool empty —
  `pick_trope` (`personas.py:320`) then falls back to the cookout voice with a `log.warning`
  nobody reads.
  - **(a) Both guards apply to both doors**, and the *Turn a mood off…* select simply does not
    offer those moods, with the embed saying why. **Recommended** — it makes the two doors agree,
    it is not terminal (switch the voice to `cookout` first and the guard lifts), and a silent
    fallback to a voice you did not choose is exactly the kind of quiet wrong the panels program
    is meant to end.
  - (b) Neither guard; the website drops its two refusals and both doors allow it. Simpler, and it
    keeps staff's current freedom — at the cost of a `pool` that silently is not a pool.

## J. What NOT to build, and what this costs

**Not in this build:**

- **The intents and lines editor.** Four routes, arbitrary rows per intent, editable trigger chips
  — the Chat page owns it and a select cannot express it. §B.
- **The Try it box.** `POST /api/chat/try` (`:533`) is a dry run over free text; as a modal it
  would be a second, worse copy of a page control.
- **Anything in the Memory section**, and no staff view of a profile. Phase 17 D5.
- **New `/api/chat/*` routes.** `site/mock/contract.json` is untouched; the only site edits are
  §D's three rows and §E's three string copies.
- **Moving `knowledge.py` or `personas.py`.** §F — both are already shared pure modules, and their
  tests staying green untouched is the proof.
- **`count` / `important_only` on `Logs`.** Lost exactly as they were for `/request` and `/voice`;
  the site's Logs page has both.
- **A shadow mode for chat.** ⚠️ Measured: `CHAT_MODES` and `CHAT_LLM_MODES` are both two-way
  (`settings_store.py:108`, `:118`). Do not add `shadow` to make it rhyme with other features.
- **Anything the daily ingest does.** `_ingest` `:513`, `ingest_once` `:537` and
  `replace_server_sections` are untouched; there is no "run the ingest now" button, because a
  button that rewrites every `server` row on demand is a second writer for rows that already have
  exactly one.

**Cost.** Wave-2 builds measured **memory 329k · youtube 371k · pings 379k · voice 385k · golive
464k** Opus tokens. This one sits **mid-band — budget 300–360k**, the pings figure. It is the
**shortest cog in wave 3** (757 lines against tempvoice's 1986 and pings' 965) with nine
subcommands rather than twenty-two, and its DB layer needs no extraction at all — those pull the
estimate down. Pulling it up: a brand-new pure module with its own test file, **three sub-panels
plus a note card**, **four modals**, and ⚠️ **surgery on five website routes with a mechanical AST
guard that fails the build if it is half-done** — which none of the wave-2 panels except memory had
to do, and memory had one route, not five.

**Prep before dispatch:** clean tree, a fresh usage read, and a brief that tells the agent to
commit at clean boundaries — **one layer at a time: (1) `chat_panel.py` + `tests/test_chat_panel.py`,
(2) the route rewrites + the AST guard green, (3) the cog panel, (4) the doc and string sweep** —
so a kill costs the last layer rather than the build. Layer 2 before layer 3 on purpose: it is the
one that can fail a test nobody expected, and it is worth nothing half-finished.

## Build deviations

Written by the build agent, 2026-09-04, on `worktree-agent-ab33797d235cf0d96`. Everything
not listed here was built as §A–§J say, with the owner's four forks all at **(a)**.
⚠️ **NOT verified: anything against live Discord.** No boot (no token), no panel opened, no
note written, no model called. The substitutes are named in the measurements at the foot.

1. **The shared functions return an `Outcome` dataclass, not the bare string
   `pings.save_settings` returns.** §F specified "the `pings.save_settings` shape
   byte-for-byte". A string cannot carry the HTTP status and error code the website door has
   to raise `Refused` with, and the alternative — the route re-deriving a status by matching
   on the message — is exactly the drift one shared function exists to stop. `Outcome(ok,
   message, code, status, value)` is what both doors read; Discord uses `message`, the
   website adds `status`/`code`, and `value` carries the new note's id.

2. **`status_lines` takes `(store, guild_id, *, tiers, spend, hidden, notes, trouble)`, not
   `(bot, guild, actor, *, spend, notes, tiers)`.** Nothing in the lines depends on who is
   looking: the admin gate decides whether `spend` is passed at all, and the caller passes
   `hidden=True` in its place. An `actor` the function never reads would be an argument a
   later reader has to disprove.

3. **The `/memory` line is appended by the COG, not by `status_lines`.** §C puts it on the
   root; §F describes `status_lines` as "the pure half of `:226–259`, so the embed and any
   later `/api/chat/status` read one list". A `/memory` pointer is a Discord-panel sentence,
   not a status fact, and a future JSON status route should not carry it. It lives as
   `chat_panel.MEMORY_LINE` so it still has one home.

4. **The routes KEEP their `_wanted_section` and `_staff_row_only` pre-checks in front of the
   shared functions.** §F says `remove_note` "keeps the guild check and the `SERVER`
   refusal", and it does — but the route's own guards fire first, so the website's wording
   and status codes are unchanged (`SERVER_ROW_LOCKED` "cannot be changed by hand", 409;
   `NO_SUCH_SECTION`, 404). Removing them would have moved two messages and two status codes
   that `tests/api/tools/test_chat.py` pins, for no gain: the shared guards are still what
   the Discord door hits, and both doors still refuse the same moves. The cost is that two
   sentences exist for the `server` refusal — as they already did on `main`.

5. **The five refusal strings moved to `chat_panel.py` and were DELETED from the router**
   (`NO_SUCH_TROPE`, `MODE_NEEDS_A_NAME`, `TROPE_IS_OFF`, `TROPE_IN_USE`, `LAST_TROPE_ON`),
   along with the router's three `clean_*` wrappers and `note_refused`. §E did not list them;
   leaving them would have been a second home for a sentence the shared function now returns
   (checklist 15). The strings themselves are byte-identical, which is why every personality
   test in `tests/api/tools/test_chat.py` stayed green with no edit.

6. **`edit_note` does not refuse an unchanged edit.** It was written that way first and taken
   out: the website route has always saved an unchanged PUT and returned 200, and a new 400
   there would be a behaviour change nobody asked for. A no-op edit therefore leaves one
   `chat.knowledge_edited` row on both doors.

7. **`KNOWN_DYNAMIC` in `tests/test_logkinds.py` lost five entries and six kinds.** The five
   `cogs/content/chat.py::<CONSTANT>` call sites are gone (the shared functions build their
   kinds with `kind_via` over string LITERALS, which the guard reads directly and which need
   no entry), and the six `web.chat.*` kinds no route can produce any more left the `note()`
   enumeration. The stale half of `test_every_dynamic_kind_is_enumerated` is what caught
   both — it is not cosmetic tidying.

8. **Sweep rows were written as `C1`–`C8`, not from 144.** §H told the build to number from the
   next free row; a second wave-3 build was numbering from 144 concurrently and the merge
   order is not fixed, so letters make a half-renumbered table impossible to mistake for a
   finished one. The conductor numbered them **155–162** at the merge (automod landed
   first, 144–154). Rows **33, 34, 35, 36, 37** were rewritten in place as §E asked.

9. **`docs/access/OWNER_GUIDE.md` gains its chat row but the sweeps COUNT is left alone**
   (`:5`, `:82` still say 143). The count depends on both wave-3 builds landing, and this
   branch cannot know the total — the conductor set it to **162** at the merge.

10. **`docs/TODO.md`, `docs/DONE.md`, `docs/info/README.md` and this document's header were
    not touched**, per the brief — the conductor owns them at landing. This foot is the one
    thing this build appends to the design.

11. **`chat_panel.py` imports `panels.py`, which imports `discord`.** The brief called the new
    module "pure (no discord imports)", and it has none of its own — but `panel_minutes` and
    `site_page_url` are one-liners over the library, exactly as `pings.py` does it, and
    re-implementing them would be a second home for two functions wave 0 exists to share.
    Nothing in `chat_panel.py` touches a Discord object.

12. **A `NoteFieldsModal` field is called `note_title`, not `title`.** `discord.ui.Modal`
    already owns `title`; the class attribute would have collided with the modal's own.

13. **The note card carries the list's `Find…` words.** §C does not say so — `Back` just
    returns to the list. But `Find…` is the answer to the 25-cap, and throwing the filter away
    the moment you open a note would make the cap bite again on the way back. The card, and the
    remove confirm behind it, copy `query` from the view they replaced.

### What §J measured

| Check | Result |
|---|---|
| `commands synced` | ⚠️ **No boot — no token.** Measured the only other way: every cog loaded and the real tree counted. **38 top-level, delta ZERO**, and `/chat` is an `app_commands.Command`, no longer a `Group`. `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` still asserts 38, unedited |
| Full suite | **4338 passed**, 0 failed (baseline measured on this worktree at `5db58fb` before any change: **4268**). `tests/cogs/content/test_chat.py` went 72 → **98** tests; `tests/test_chat_panel.py` is new at **43** |
| `ruff check .` | clean |
| Import edge | `python -c "import black_bloc.chat_panel, black_bloc.cogs.content.chat, black_bloc.api.tools.chat, black_bloc.knowledge, black_bloc.personas, black_bloc.settings_store"` — passes, no cycle |
| `node site/mock/check.mjs` | **17 pages / 142 routes, all keys present** — unchanged, as §E predicted (no route added, removed or renamed). **150 routes today** (v108), none of them chat's |
| `labels.js` / `server.mjs` parse | both parse |
| The AST guard | `test_a_route_never_notes_an_event_its_shared_path_already_logged` passes with the five `note()`s gone |
| Not measured | anything live: no Discord, no dashboard in a browser, no model provider called. `chat_llm_mode` is still `off` and this build does not change it |
