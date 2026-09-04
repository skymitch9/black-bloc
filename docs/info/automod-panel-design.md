# Automod — `/automod` is ONE command that opens a panel (wave 3)

> **Audience:** the build agent and the reviewer, and the owner for §I. **Status:** TRACKED ·
> **PLANNING** — nothing here is built.
> **Last verified: 2026-09-04** — every `path:line` below was READ against `main` at `bf3e447`
> (the tree's HEAD is `4336a66`, a docs-only commit on top of it; no code differs), in
> `black_bloc/cogs/moderation/automod.py` (**830 lines**), `black_bloc/automod.py` (**451
> lines**), `black_bloc/panels.py` (194), `black_bloc/api/tools/mod.py` (297),
> `black_bloc/settings_store.py`, `black_bloc/logkinds.py`, `black_bloc/command_visibility.py`,
> `black_bloc/actionlog.py`, `tests/test_bot.py`, `tests/cogs/moderation/test_automod.py` (861),
> `tests/test_automod.py` (366), `tests/api/tools/test_mod.py`
> (302), `site/public/assets/page-automod.js` (141), `site/public/assets/labels.js`,
> `site/mock/server.mjs`, `site/mock/contract.json`, `docs/access/sweeps.md` (455 lines, last
> row **143**), `docs/access/OWNER_GUIDE.md`, `docs/info/feature-list.md`,
> `docs/info/phase6-design.md`, `docs/info/code-notes.md`.
>
> **Measured, not assumed:**
> `AUTOMOD_MODES = ("off", "shadow", "on")` (`black_bloc/automod.py:10`) — **three** modes, so
> every crossing below is three-way. `RULE_ORDER` holds **7** rules (`:13`), which is under
> Discord's 25-option select cap, so the rule picker needs no `capped_placeholder`.
> `tests/test_bot.py:190` asserts **38** top-level commands. `command_visibility.py:16–19`
> has **no** automod entry, so nothing vanishes when the mode is off.
> `docs/access/OWNER_GUIDE.md` names automod **nowhere** (zero matches, case-insensitive).
> ⚠️ `staff_channel_id`'s default is `settings.test_channel_id` **always**, not only in test
> mode (`settings_store.py:1355–1356`) — see §A's red block, it decides what the mode control
> can even offer.
> ⚠️ **NOT verified: anything was run.** No boot, no `pytest`, no `ruff`, no `check.mjs`,
> nothing against live Discord or the live dashboard. Whether a real client submits an EMPTY
> multi-`Select` at `min_values=0` is the same unproven edge
> [`events-panel-design.md`](events-panel-design.md) deviation 6 and
> [`pings-panel-design.md`](pings-panel-design.md) deviation 5 flag; §C builds both paths.
> Whether the LIVE guild has ever set `staff_channel_id` away from the test channel is **not
> knowable from the repo** — say so, do not guess.
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`voice-panel-design.md`](voice-panel-design.md)
> (wave 2's last, shipped v73) and its `## Deviations` foot, which is the trap list. Feature
> behaviour is [`phase6-design.md`](phase6-design.md) (F7, shadow beside Carl-bot).
>
> ⚠️ **This build changes how staff CONFIGURE automod and nothing about what it ENFORCES.**
> The listener path (`on_message` `:439`, `on_message_edit` `:476`, `_answer_for` `:499`,
> `_post_case` `:553`, `punish` `:178`, `do_delete` `:135`, `do_timeout` `:162`,
> `apply_case` `:342`) and the whole pure engine's evaluation half (`evaluate`
> `black_bloc/automod.py:412` and everything it calls) are **untouched**, their log kinds are
> untouched, and the `off → shadow → enforce` rollout rule (flipped only on the owner's
> measured judgement from the shadow log — [`feature-list.md`](feature-list.md):45) is
> untouched. One deliberate exception, argued in §F: `_as_words` learns to split on newlines
> as well as commas. It changes how a word list is TYPED, never which words are enforced.

## A. Measured today — one group, two sub-groups, eight leaf subcommands

`automod` is an `app_commands.Group` (`:427`, `default_permissions=STAFF_ONLY` `:429`);
`rule` (`:431`) and `exempt` (`:432`) are sub-groups of it. **3 + 3 + 2 = eight leaf
subcommands over ONE top-level slot.**

| Subcommand | Line | Gate | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/automod logs [count] [important_only]` | `:590` | `send_logs` carries its own `require_staff` (`actionlog.py:296`) | `send_logs(interaction, "automod", count=, important_only=)` `actionlog.py:287` |
| `/automod status` | `:603` | `require_staff` `:605` → `_database_ready` `:607` | ⚠️ **all inline** `:609–642`: the count query `:616–621`, the eight header lines `:622–634`, `describe_rule` `:636` per rule, `NO_STAFF_WARNING` `:638–639` |
| `/automod mode <off\|shadow\|on>` | `:644` | `require_staff` `:652` — ⚠️ **no `_database_ready`** | ⚠️ **inline** `:654–678`: the two arming refusals `:654–665`, `store.set` `:666`, the reply `:669`, `log_action("automod.mode")` `:672` — **bare, no `kind_via`** |
| `/automod rule enable <name>` | `:680` | `_set_field` → `require_staff` `:722` | `_set_field(…, "enabled", "true")` `:719` → `save_rule` `:289` |
| `/automod rule disable <name>` | `:685` | same | `_set_field(…, "enabled", "false")` |
| `/automod rule set <name> <field> <value>` | `:690` | same | `_set_field(…, field.value, value)`; `field` choices are `RULE_FIELDS` `:63` |
| `/automod exempt add [role] [channel]` | `:746` | `_change_exempt` → `require_staff` `:767` — ⚠️ **no `_database_ready`** | ⚠️ **inline** `:764–809`: the "name one of them" refusal `:769`, the two `(entity, key, mark)` pairs `:777–780`, the list edit + `store.set` `:783–795`, the sentence `:796`, `log_action("automod.exempt_add")` `:800` — **bare** |
| `/automod exempt remove [role] [channel]` | `:755` | same | same, `add=False`, `automod.exempt_remove` |

`rule_names` (`:706–717`) is the shared autocomplete for all three `rule` subcommands.

**Not a subcommand and NOT moving** (P14): **`ApplyNowButton`** (`:390`, a
`SafeDynamicItem`/`DynamicItem` re-registered in `cog_load` `:436`, attached by `_post_case`
`:576–579` only when nothing was done `:577`). That button belongs to the modlog case card in
the room, not to the caller. §I lists it under what is already settled.

**The seven rules and their fields**, from `DEFAULT_RULES` (`black_bloc/automod.py:30`) —
this table is what the modal is built from, so it is measured, not summarised:

| Rule | `:line` | default `enabled` | `window_s` | `threshold` | `actions` | `timeout_s` | has `words` |
|---|---|---|---|---|---|---|---|
| `mention_spam` | `:31` | **True** | 30 | 5 | delete+warn+timeout | 300 | no |
| `slowmode` | `:38` | True | 4 | 6 | — (log only) | 0 | no |
| `linkspam` | `:39` | True | 1 | 1 | — | 0 | no |
| `invitespam` | `:40` | False | 30 | 1 | delete+warn+timeout | 600 | no |
| `attachmentspam` | `:47` | False | 30 | 5 | — | 0 | no |
| `caps` | `:54` | False | **0** | 70 (a **percent**, bounded 1–100 `:248`) | — | 0 | no |
| `bad_words` | `:55` | False | **0** | 1 | — | 0 | **yes** |

⚠️ `window_s == 0` means *this message only* (`:381`, and the `code-notes.md` key against it),
which is what makes `caps` and `bad_words` per-message rules. ⚠️ `RULE_NOUNS` (`:65`) has
**six** entries — **`caps` is deliberately absent** and `_sentence` `:357` falls back to
"event(s)". A per-rule label map is therefore needed for the modal (§F), not a `RULE_NOUNS`
lookup.

**Bounds the engine enforces** (`normalise_rule` `:227`): `window_s` 0–`WINDOW_MAX_SECONDS`
3600 (`:23`), `threshold` 1–`THRESHOLD_MAX` 1000 (`:24`, 1–100 for `caps` `:248`), `timeout_s`
0–`TIMEOUT_MAX_SECONDS` 28 days (`:25`), `actions` ⊆ `ACTIONS` (`:9`), `words` ≤ `WORDS_MAX`
200 (`:27`, `_as_words` `:210`).

**Settings keys today**

| Key | `settings_store.py` | Notes |
|---|---|---|
| `automod_mode` | type `:210`, choices `:285`, help `:576`, default **`"shadow"`** `:1483–1484` | the three-way switch |
| `automod_rules` | type `:211` (**the registry's only `json` key**), help `:577`, default `validate_rules({})` `:1485–1486` | ⚠️ help text names `/automod rule` |
| `automod_exempt_role_ids` | type `:212`, help `:578` | `roles` |
| `automod_exempt_channel_ids` | type `:213`, help `:579` | `channels` |
| `automod_warn_threshold` | type `:214`, max `:305`, why `:383`, help `:580`, default `:1487–1488` | printed by status, **set nowhere in `/automod`** |
| `automod_log_level` | generated `:808–810` from `FEATURES` (`logkinds.py:26`) | help text built by `log_level_help` `:800`, whose `extra` reads `LOG_LEVEL_COMMANDS["automod"] = "automod"` `:783` |

Read but not owned by automod: `mod_dm_on_action` (`:625`), `modlog_channel_id` (`:628`),
`staff_channel_id` (through `store.staff_roles` `:1668`), `honeypot_channel_ids` (unioned into
the channel exemption at `:459`).

**Log kinds** — `automod.deleted` is `IMPORTANT` (`logkinds.py:134`); `automod.exempt_add`,
`automod.exempt_remove`, `automod.mode`, `automod.observed`, `automod.rule` are `ROUTINE`
(`:229–233`). `save_rule` already builds its kind with `kind_via` (`:308`); **`automod.mode`
and both exempt kinds are bare** and gain one in §F.

**The site, measured** — the dashboard already owns this feature end to end:

| Surface | Where | What it owns |
|---|---|---|
| `automod.html` (102 lines) + `page-automod.js` (141) | `site/public/` | Mode (`:92–99`, a `settingsPanel` over `automod_mode`), Rules (`:101–117`, a `ruleCard` `:32` per rule with every field as an input and a `words` textarea `:46`), Exemptions (`:119–125`, a `settingsPanel` over the two `automod_exempt*` keys), all remaining automod settings `:133`, and Logs `:134` |
| `GET /api/mod/rules` | `api/tools/mod.py:274` | `rule_row` `:129` per `RULE_ORDER` |
| `PUT /api/mod/rules/{name}` | `:280` | filters the payload to `DEFAULT_RULES[name]`'s keys `:288`, then `save_rule(..., via=VIA_WEBSITE)` `:290` |
| the whole router | `:137` | behind `staff_dependency` |

⚠️ **There is NO `api/tools/automod.py`** — automod's web half lives in `mod.py`, which imports
`apply_case` and `save_rule` **from the cog** (`:16`). That import edge is what makes
"`tests/api/tools/test_mod.py` stays green with no edit" the proof this build moved nothing
(§G). The mode and the exemptions are written from the site through the **generic settings
API**, not through a `/api/mod` route.

**`commands synced` — the number does NOT move.** `tests/test_bot.py:190` measures **38**
today, and one `Group` occupying one top-level slot becomes one `command` occupying one
top-level slot. This is the `/memory` shape ([`memory-panel-design.md`](memory-panel-design.md)),
not the `/voice` shape: **38 → 38.** ⚠️ The build still **re-measures and states both
numbers** (requests deviation 7, checklist 10) — if the count moves at all, something else
broke and the build stops rather than editing the assertion.

> 🔴 **The one measurement that decides what the panel can even render.**
> `staff_channel_id` defaults to `settings.test_channel_id` (`settings_store.py:1355–1356`)
> **on every guild, in every mode** — not just under `TEST_MODE`. While it is unset,
> `/automod mode on` is refused by `STAFF_IS_THE_TEST_CHANNEL` (`:94`, checked at `:656`), and
> if it IS set but resolves no roles, by `NO_STAFF_ROLES` (`:66`, checked at `:663`). So on a
> guild that has not been set up, **`on` is a mode the panel must not offer** (P3/P9), and the
> embed must say which of the two conditions is in the way. `sweeps.md:216` records this as an
> expected result: *"`/automod mode on` must REFUSE while the staff channel is still the test
> channel."* Whether the live guild has moved `staff_channel_id` is **not in the repo.**

## B. The decision — one `/automod`, staff only

**`/automod` becomes a single `app_commands.command`; the `automod`, `rule` and `exempt`
Groups all go.** It keeps `default_permissions=STAFF_ONLY`
(`command_visibility.py:14`, `manage_messages`), so `"automod"` **stays** in
`tests/test_bot.py:25`'s `STAFF_COMMANDS` and never joins `MEMBER_COMMANDS`. There is no
member half of this feature and inventing one is out of scope.

**One panel, no member/staff split** (the P2 split collapses to a single branch): every caller
who gets past the UX lock is checked at runtime by `still_staff` (`panels.py:31`) before every
move, exactly as P8 requires. A member who somehow reaches the command gets
`store.staff_refusal(guild_id)` (`settings_store.py:1681`) as a sentence, never a dead button.

**What the panel owns** — the eight subcommands and nothing more:

| Today | On the panel |
|---|---|
| `/automod status` | the ROOT embed, always rendered — never hidden behind a button (events deviation 10: a button that hides the loudest warning loses it, and `NO_STAFF_WARNING` `:72` is that warning) |
| `/automod rule enable\|disable` | one button on the rule card that says which it will do |
| `/automod rule set` | a 3-field numbers modal + an actions `Select` + a words modal (§C) |
| `/automod exempt add\|remove` | the Exemptions sub-panel: `RoleSelect` and `ChannelSelect` to add, one `Select` to remove |
| `/automod mode` | a `Select` on the ROOT, with `on` offered only when arming would succeed |
| `/automod logs` | a `Logs` button answering a NEW ephemeral followup (P11) |

**What stays site-only, said out loud on the panel** — `automod_warn_threshold` and
`mod_dm_on_action` are printed as status lines and have no control (see fork **F-A3**);
reordering or renaming rules (there is no such operation); the cases table and its filters
(`page-moderation.js`); `automod_log_level` (the generic settings page).

**The states.** Automod has no per-caller state — the panel is the same for every staffer —
so the state table is the FEATURE's condition crossed with the mode:

| # | Condition | mode `off` | mode `shadow` | mode `on` |
|---|---|---|---|---|
| S0 | database down | the panel does not open: `db_up` (`panels.py:58`) answers `DB_UNAVAILABLE` as a sentence. ⚠️ Today `mode`, `rule *` and `exempt *` skip this check entirely (§A) — the panel closes that hole | same | same |
| S1 | `staff_channel_id` is the test channel | mode select offers **off · shadow**; the embed carries `STAFF_IS_THE_TEST_CHANNEL` `:94` | same | ⚠️ unreachable from the panel, but a mode written from the site can put the guild here — the embed says so and the select still offers off/shadow |
| S2 | staff channel is real but `store.staff_roles` `:1668` is empty | mode select offers **off · shadow**; embed carries `NO_STAFF_ROLES` `:66` | same | same, plus `NO_STAFF_WARNING` `:72` at the foot (today's `:638–639` condition, `not staff and mode == "on"`) |
| S3 | armable (a real staff channel that resolves at least one role) | all three modes; embed says nothing is being watched | all three; embed says what it WOULD do | all three; embed says it is acting |
| S4 | every rule disabled (`rules_summary` `:276` returns "every rule is off") | — | the embed says so on its own line whatever the mode is: an armed automod with no armed rule is the quiet failure this line exists to make loud | — |

P3 in one line: **no state renders a control whose shared function would refuse it.**
`on` is absent from the mode select in S1 and S2; `Turn it on` and `Turn it off` are never both
on a rule card; `Log only` renders only when the rule has an action to clear; the removal
select renders only when there is an exemption to remove; `Words…` renders only for
`bad_words` (`"words" in DEFAULT_RULES[name]`, `black_bloc/automod.py:61`).

## C. The cards, the sub-panels, the modals

Each is a **re-render in place**: `retire(previous)` first (P6, `panels.py:40`), `defer()` then
`edit_original_response` (P5), `db_ready` (`panels.py:48`) on every click after a defer,
`still_staff` (`panels.py:31`) before **every** move including the reads (pings deviation 10 —
a demoted staffer opening the exemption list is the same defect one step earlier).

**The ROOT embed** is today's `/automod status` block `:622–639`, moved WHOLE into
`status_lines` (§F) and passed through `panels.clamped` (`:86`, `DESCRIPTION_LIMIT` 4000): the
mode, the resolved staff (`staff_roles_sentence` `settings_store.py:1276`), what the member is
told, the warn threshold, the modlog, exempt roles, exempt channels, the acted-on/logged-only
counts, then a blank line, then `describe_rule` (`black_bloc/automod.py:287`) per rule in
`RULE_ORDER`. **The panel's lines and the lines `/automod status` printed must never be two
shapes.** Added, because the panel replaces a command that could explain itself in prose: one
line naming the arming blocker when there is one (S1/S2), and the S4 "every rule is off" line.

**The ROOT view** — four rows of five:

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` **"A rule…"** over `RULE_ORDER` (7 options, label `f"{name} — {RULE_HELP[name]}"` clamped by `panels.option_label`/`SELECT_OPTION_LIMIT` 100) | always | — (opens the card) |
| 1 | `Select` **"What automod does…"** over `mode_options(current, may_arm)` — `AUTOMOD_MODES` `:10` minus `on` in S1/S2, `default=` the current mode | always | `set_mode` (§F) |
| 2 | `Exemptions…` → sub-panel | always | — |
| 2 | `Refresh` | always | — |
| 2 | `Logs` → a NEW ephemeral followup (P11) | always | `send_logs(interaction, "automod")` — keeps its own `require_staff` |
| 2 | `Open on the site` (link) | `panels.site_page_url(origin, "automod")` (`panels.py:101`, `logkinds.py:94` → `automod.html`) is not `None` | — |
| 3 | reserved for the arming confirm, which **replaces** the root controls rather than adding a row (youtube's `open_confirm` shape, pings deviation 8) | fork **F-A1** | — |

⚠️ **Seven rules is under 25, so `capped_placeholder` (`panels.py:66`) is NOT needed on the
rule picker.** It IS needed on the exemption removal select, which is unbounded.

**The rule card** — embed is `describe_rule(name, cfg)` `:287` plus `RULE_HELP[name]` `:74`
plus one line saying what the rule counts and, for a `window_s == 0` rule, that it judges one
message at a time:

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Turn it off` when `cfg["enabled"]` else `Turn it on` — **ONE button** | always | `save_rule(bot, guild, name, {"enabled": …}, actor)` `:289` |
| 0 | `Change the numbers…` → modal | always | `save_rule` with the parsed dict |
| 0 | `Log only` (danger) | `cfg["actions"]` is non-empty | `save_rule(… {"actions": []})` |
| 0 | `Words…` → modal | `"words" in DEFAULT_RULES[name]` — **`bad_words` only** | `save_rule(… {"words": …})` |
| 0 | `Back` | always | — |
| 1 | `Select` **"What it does…"** over `ACTIONS` `:9`, `min_values=0`, `max_values=3`, current actions as `default=` | always | `save_rule(… {"actions": picked})` |

⚠️ **`Log only` and the empty select are two doors onto one move, and that is deliberate.**
`min_values=0` is the unproven empty-submit edge (events deviation 6, pings deviation 5,
whose deviation 16 established that `discord.py` ACCEPTS `min_values=0` but that the CLIENT
half is untested). `Log only` is the fallback that works whatever the client does, and it is
the one P3 exception in this design — call it out in the build's deviations if it turns out
the empty submit works, so a later pass can drop one of them.

⚠️ **Row 0 carries five buttons for `bad_words` — exactly Discord's per-row cap.** Every other
rule shows four or fewer. Do not add a sixth.

**The Exemptions sub-panel** — embed lists the two sets as mentions (today's `:631–633`
wording) **plus** a line naming the honeypot channels automod also never reads
(`honeypot_channel_ids`, unioned at `:459` through `channel_exempt`
`black_bloc/automod.py:448`), so a staffer who cannot find a channel on the removal select is
told why rather than left guessing:

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `RoleSelect` **"Stop watching a role…"**, `min_values=1`, `max_values=1` | always | `set_exempt(…, "role", id, add=True)` (§F) |
| 1 | `ChannelSelect` **"Stop watching a channel…"**, `min_values=1`, `max_values=1` | always | `set_exempt(…, "channel", id, add=True)` |
| 2 | `Select` **"Watch it again…"** over `exempt_options(...)` — every exempt role AND channel on ONE select, each option carrying its own kind; ≤25 with `capped_placeholder(shown, total, pick=…)` | either list is non-empty | `set_exempt(…, kind, id, add=False)` |
| 3 | `Back` | always | — |

⚠️ **Row 2 is why `exempt add` and `exempt remove` do not become two spellings.** One control
whose options already know whether they are a role or a channel — the same shape voice's
"Undo for…" landed with. It also removes today's *"Name a role or a channel"* refusal
(`:770–773`) entirely: the panel cannot be pressed with neither.

⚠️ **A role or channel that no longer exists still appears** — the stored id is real even when
`guild.get_role`/`get_channel` returns `None`. Label it *"a role Discord no longer has (id)"*
so the only surface that can tidy it up still offers to. Staff-final-say: a stored decision
staff cannot leave is the state the rule forbids.

**The modals** — both `AnswersErrors` + `discord.ui.Modal` (P12, checklist 30). ⚠️ **A modal
has no `app_commands.Range`**, so the bound that vanished with the parameter is rebuilt where
the value now enters (checklist 22, voice deviation 13):

| Modal | Fields | Limits | Refusal |
|---|---|---|---|
| `NumbersModal` | 3 `TextInput`s, prefilled from `rule_config(book, name)` `:264`: **window** (label from `rule_field_labels(name)`, §F; help says `0` = this message only), **threshold** (for `caps`, *"Percent capitals, 1–100"* — `RULE_NOUNS` has no `caps` entry), **timeout seconds** | `max_length` sized to the engine's ceilings: window ≤ 4 digits (3600), threshold ≤ 4 (1000), timeout ≤ 7 (28 d = 2419200) | every field through `_typed` `:812` FIRST; the first `RuleError` is answered verbatim and **nothing at all is written** — not even the two fields that parsed |
| `WordsModal` | 1 paragraph field, prefilled with the current words, `max_length` 4000 (`panels.DESCRIPTION_LIMIT`) | `_as_words` `:210` caps at `WORDS_MAX` 200 `:27` and raises with its own sentence | the `RuleError` is answered; the card is **not** re-rendered, so a refused value can never read as a save |

⚠️ **`panels.NoteModal` is NOT used** — nothing here sends a person a free-text reason.

⚠️ **The atomicity is already there and must not be re-implemented.** `save_rule` `:289`
builds the whole rule object and calls `normalise_rule` `:302` **before** `store.set` `:303`,
so one `save_rule` call per modal submit is one write and one log row (checklist 34). Never
call it once per field.

## D. Settings (P13 · checklist 33)

Registered **in their own appended block** at the foot of the registry, exactly where
`voice_panel_minutes` sits (`settings_store.py:1070–1079` for `KEY_TYPES`/`KEY_HELP`,
`:1607–1608` for `default()`), so the four parallel wave-3 branches merge textually.

| Key | Type | Default | Status |
|---|---|---|---|
| `automod_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Help text carries KI-20's warning in the same shape as the five shipped keys: 15+ loses the "gone quiet" footer because Discord's interaction token expires at 15 minutes |
| `automod_arm_needs_confirm` | `bool` | **fork F-A1** | **NEW, whichever way F-A1 goes** — checklist 33 says a default decided in chat is a registry key, not a constant. If the owner picks "confirm", the default is `true` and a server that finds it tedious can turn it off from the site; if he picks "no confirm", the key still exists at `false` |

**Both keys also need their site rows**, following the shipped pattern exactly:

| File | Line to copy | What to add |
|---|---|---|
| `site/public/assets/labels.js` | `:51` (`voice_panel_minutes: 'How long the /voice panel stays live'`) | `automod_panel_minutes: 'How long the /automod panel stays live'` and `automod_arm_needs_confirm: 'Whether arming automod asks twice'` |
| `site/mock/server.mjs` | `:420` (the `voice_panel_minutes` row) | one row each, `['automod_panel_minutes', 'int', 10, 10, "…"]` and the bool |

`labels.js:181`'s `NAMESPACES` already contains `'automod'` — measured, no change.

**Existing keys this panel READS, all untouched:** `automod_mode`, `automod_rules`,
`automod_exempt_role_ids`, `automod_exempt_channel_ids`, `automod_warn_threshold`,
`automod_log_level`, `mod_dm_on_action`, `modlog_channel_id`, `staff_channel_id`,
`honeypot_channel_ids`.

**Nothing else here is a decision.** The 25-option cap, the 5-buttons-per-row cap and the
5-fields-per-modal cap are Discord's; the button table is the state machine in §B; the rule
bounds are `normalise_rule`'s and were decided in Phase 6; and the two behaviours a reader
might mistake for decisions — staff being re-checked before every move, and `on` being hidden
rather than offered-and-refused — are **settled by the standing rules** (P8, P3/P9), not chosen
here, so neither becomes a key.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `automod` Group | `:427–430` | one `@app_commands.command(name="automod")`, same `default_permissions=STAFF_ONLY` |
| `rule` Group | `:431` | the rule card |
| `exempt` Group | `:432–434` | the Exemptions sub-panel |
| the eight leaf commands | `:590`, `:603`, `:644`, `:680`, `:685`, `:690`, `:746`, `:755` | buttons, selects, modals |
| `rule_names` autocomplete | `:706–717` | **deleted** — nothing types a rule name any more, and there is no autocomplete behind a select |
| `RULE_FIELDS` | `:63` | **moves** to `black_bloc/automod.py` as the modal's field source, re-exported from the cog by name so no existing import changes |
| `_typed` | `:812` | **moves** to `black_bloc/automod.py` beside the other parsers it belongs with; the cog re-exports it |
| `_set_field` | `:719–744` | the card's buttons calling `save_rule` `:289` directly |
| `_change_exempt` | `:764–809` | `set_exempt` (§F) |
| `_database_ready` | `:583–588` | `panels.db_up` / `panels.db_ready` — and the three commands that skipped it (§A) stop skipping it |
| the "Name a role or a channel" refusal | `:770–773` | **deleted** — the panel cannot be pressed with neither |
| `UNKNOWN_RULE_CHOICE` | `:90–93` | ⚠️ **KEPT** — `save_rule` `:300` still raises it, and so does the web route through `save_rule`. Its TEXT is rewritten (it names `/automod status`) |
| `tests/test_bot.py` `LOGS_GROUPS["automod"]` | `:14` | **deleted** — `/automod` is no longer a Group with a `logs` child, so the loops that walk it would `KeyError` |
| `tests/test_bot.py` `STAFF_COMMANDS "automod"` | `:25` | **unchanged** — still staff-only |
| `tests/test_bot.py` `assert len(top) == 38` | `:190` | **unchanged, and re-measured to prove it** (§A) |
| `command_visibility.HIDDEN_WHEN_OFF` | `:16–19` | **nothing to change** — measured, automod has no entry, so `/automod` does not vanish when the mode is off (the settled precedent, §I) |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each
currently tells somebody to run something that will not exist:

| File:line | Today | Becomes |
|---|---|---|
| `cogs/moderation/automod.py:70` | `NO_STAFF_ROLES` — *"check `/automod status` lists the roles you expect"* | *"…check the panel lists the roles you expect"* |
| `:91–93` | `UNKNOWN_RULE_CHOICE` — *"`/automod status` lists them"* | *"`/automod` lists them"* |
| `:97` | `STAFF_IS_THE_TEST_CHANNEL` — *"check `/automod status` lists the roles you expect"* | same rewrite as `:70` |
| `black_bloc/automod.py:81` | `RULE_HELP["bad_words"]` — *"set them with /automod rule set bad_words words"* | *"set them with `/automod` ▸ **A rule…** ▸ **Words…**"*. ⚠️ **This string is also served to the website** by `rule_row` (`api/tools/mod.py:130`) and rendered by `page-automod.js:69` — so the wording has to read correctly on a web page too. Prefer *"the bad_words rule's word list"* over either command spelling |
| `settings_store.py:577` | `automod_rules` help — *"`/automod rule` is what changes it"* | *"`/automod` ▸ **A rule…** is what changes it"* |
| `settings_store.py:783` | `LOG_LEVEL_COMMANDS["automod"] = "automod"` → `log_level_help` `:800` renders *"and in `/automod logs`"* | ⚠️ There is no `/automod logs` after this build. Either point the `extra` at the panel, or drop the row. **Also REPORT, do not fix: `"pings": "pingroles"` (`:795`) is already stale** — `/pingroles` was retired in wave 2 and nobody noticed, which is the same bug one wave earlier |

**Site touch points** — the API needs **no** change (`api/tools/mod.py` imports `apply_case`
and `save_rule` by name and this build moves neither), and no route is added or removed.
Beyond §D's two label rows, the only edit is the `RULE_HELP["bad_words"]` rewording above,
which is served by the live route rather than copied into the mock. `site/mock/contract.json`
(`:268`, `:1787`, `:1807`, `:3382`, `:3446–3448`) is **untouched** — the new `kind_via` heads
in §F create no new *route*, and `kind_via(kind, VIA_DISCORD)` returns the bare kind, so no
existing row changes.

**Docs rewritten in the same commit** (P15):

| Doc | What |
|---|---|
| `docs/access/sweeps.md:210–216` | the Phase 6 appendix block — rewritten **in place**, not added to. It currently walks `/automod status` and asserts `/automod mode on` refuses; both become panel steps and the refusal becomes *"`on` is not even on the mode picker"* |
| `docs/access/OWNER_GUIDE.md` | ⚠️ **names automod NOWHERE today (measured, zero matches)** — so this build ADDS one "Keep an eye on what people post" row beside the existing feature rows, and moves the sweeps count in the header and the "Test something" row |
| `docs/info/feature-list.md:45` | the F7 row gains one clause: `/automod` is one command that opens a panel |
| `docs/info/phase6-design.md:83` | names `/automod status\|mode\|rule <name>` — gets a **dated "superseded by the panel" line at the top**, NOT a rewrite. The phase doc is the record of what was decided in Phase 6 |
| `docs/info/panels-program.md:84` | the Automod row → shipped, with the measured `commands synced` before/after |
| `docs/info/README.md:42–51` | a row for this file beside the other panel designs |
| `docs/info/code-notes.md` | re-keyed at the merge. The automod anchors cluster at `black_bloc/automod.py:13, 26, 30, 89, 148, 169, 227, 264, 304, 332, 341, 381, 431` and `black_bloc/cogs/moderation/automod.py:60, 61, 63, 93, 115, 134, 147, 161, 177, 288, 314, 341, 356, 389, 406, 475, 490, 497, 503, 551, 717`. ⚠️ **`cogs/moderation/automod.py:717`'s note names `/automod rule set` in its text** and needs rewriting, not just re-pointing. Trust the anchor text over the number |

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB/move layer stays in the COG**, as it does for applications and voice.
`api/tools/mod.py:16` imports `apply_case` and `save_rule` from
`cogs.moderation.automod`; moving them would be a mechanical diff across two files for no gain
this build needs, and keeping every existing import byte-identical is what makes the unchanged
assertions in `tests/api/tools/test_mod.py` the proof the refactor changed nothing (wave-0
deviation 4).

**Already shared, reuse unchanged:** `save_rule` `:289` (already takes `via` and builds its
kind with `kind_via` `:308`), `send_logs` (`actionlog.py:287`), `describe_rule`, `rule_config`,
`rules_summary`, `RULE_ORDER`, `RULE_HELP`, `DEFAULT_RULES`.

**New, module level in `black_bloc/cogs/moderation/automod.py`** — each does ONE write and ONE
log row, each takes `via: str = VIA_DISCORD` and builds its kind with `kind_via`
(checklist 34):

| Function | Replaces | Note |
|---|---|---|
| `set_mode(bot, guild, value, actor, *, via=VIA_DISCORD)` | inline `:654–678` | keeps BOTH arming refusals (`:656`, `:663`) so the panel and any future route refuse identically. ⚠️ Today's `log_action("automod.mode")` `:672` is **bare** — it gains `kind_via`, so a future route cannot double-post |
| `set_exempt(bot, guild, kind, entity_id, actor, *, add, via=VIA_DISCORD)` | the loop body of `_change_exempt` `:783–806` | ONE entity per call. `kind` is `"role"` or `"channel"` and picks the settings key and the `<@&`/`<#` mark. Returns the sentence the command built at `:789–799`, including the "was already exempt, so nothing changed" branch. Both log kinds gain `kind_via` |
| `case_totals(db, guild_id) -> dict[int, int]` | the query `:616–621` | so the embed can be built without an interaction |
| `status_lines(bot, guild, totals) -> list[str]` | the inline block `:622–639` | the panel embed and `/automod status`'s old output are ONE list. Takes the totals rather than the db, so it stays synchronous and testable |
| `arming_refusal(bot, guild) -> str \| None` | `:654–665` | the mode select and `set_mode` read the same answer, so the control offered and the function's verdict can never disagree |

**Pure, into the EXISTING `black_bloc/automod.py`** — appended at the foot, the shape
`black_bloc/youtube.py` and `black_bloc/pings.py` landed with (pings deviation 17). ⚠️ Nothing
already in that file is renamed or re-homed, so `api/tools/mod.py:8–15`'s six imports and every
existing test are unchanged:

| New | Signature / content |
|---|---|
| `RULE_FIELDS`, `_typed` | **moved** from the cog `:63`, `:812`; re-exported from the cog by name |
| `AutomodMove` + `PANEL_MOVES` + `card_buttons(cfg, *, has_words)` and `root_buttons(*, may_arm, has_site)` | §B/§C's tables AS DATA, proved by a parametrised test |
| `mode_options(current, may_arm) -> list[tuple[str, str, bool]]` | `AUTOMOD_MODES` minus `on` when `may_arm` is False, with the current one flagged |
| `rule_field_labels(name) -> dict[str, str]` | the modal's per-rule labels — `caps` gets *"Percent capitals, 1–100"*, `window_s == 0` rules say *"0 = this message only"*. ⚠️ **Not a `RULE_NOUNS` lookup**: `RULE_NOUNS` `:65` has no `caps` entry, measured |
| `exempt_options(role_ids, channel_ids, names) -> list[tuple[str, int, str]]` | the removal select's options, each carrying its kind; a missing role/channel still gets an option, labelled as gone |
| `PANEL_MINUTES_KEY = "automod_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:97`), exactly as the five shipped panels do |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER`, and the new panel sentences | wave-0 deviation 1: the footer is a whole sentence, not a format string |

**The one engine-adjacent change, and its justification.** `_as_words` `:210` splits a string
on **commas only**. The site's textarea joins and splits on **newlines**
(`page-automod.js:49`, `:59`), so a `WordsModal` prefilled the way the site prefills would
collapse a whole list into one word on submit. Options were (a) make the modal use commas —
unusable for 200 words on a phone, and a different shape from the site; (b) teach `_as_words`
to split on newlines as well as commas. **Take (b).** It is two characters of regex in the
split, commas keep working so no stored list changes, and it makes the two doors agree.
⚠️ It touches a validator the enforcement path reads, so it gets its own test asserting a
newline list, a comma list and a mixed list all produce the same words, and it is named in the
build's deviations whatever happens.

**What to ADD to `black_bloc/panels.py`: nothing, this build.** One candidate is real and is
handed to the CONDUCTOR instead — a **confirm helper**. `youtube.open_confirm` and pings'
deviation 8 are already two hand-rolled copies of "re-render this embed with an Are you sure?
field and two buttons", and fork **F-A1** makes automod the third (checklist 15). Adding it to
`panels.py` now would edit the one file **all four wave-3 branches touch**, and voice deviation
8 measured that a clean textual merge is worth more than one-fact-one-home for a handful of
lines. So: build it locally, name it in the deviations, and **the conductor folds all three
copies into `panels.py` at the merge**. That is exactly how `clamped` landed.

**Two things to reuse, never re-copy:** `panels.answer` (`:20`) — the cog has no copy today,
keep it that way; and `panels.site_page_url(origin, "automod")` (`:101`), never a private
`SITE_PAGE` constant (the youtube copy pings deviation 6 deliberately left behind is the
counter-example).

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains, and what it keeps |
|---|---|
| `tests/cogs/moderation/test_automod.py` (861 lines) | ⚠️ **The engine and Apply-now tests stay UNCHANGED in assertion** — `:315–:520` (the mode matrix, exemptions, guard, message types, edits, bursts), `:539–:635` (the Apply-now button), `:784–:858` (window deletes, apologies, staff caching, `cog_load`). That is **the proof the enforcement path did not move**, and it is the strongest evidence this build can produce. The subcommand tests `:646–:782` are rewritten to drive the panel: `/automod` answers ephemerally with a panel; **parametrised over S1–S4 × all three modes — each renders exactly its §B row and no other**; `on` is absent from the mode select in S1 and S2 and present in S3; `Turn it on` and `Turn it off` are never both present; `Log only` is absent on a log-only rule; `Words…` renders for `bad_words` and for no other rule; the removal select is absent with no exemptions and carries the right kind per option; a refused modal value writes **nothing** and does not re-render; every button calls `save_rule` / `set_mode` / `set_exempt` with `via` untouched (mock them); `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-card moves nothing (`still_staff` at every site, reads included); `db_ready` after a defer, and the three commands that skipped the DB check no longer can |
| `tests/test_automod.py` (366 lines) | `card_buttons` / `root_buttons` for every rule × enabled × has-actions × has-words; `mode_options` with and without `may_arm`; `rule_field_labels` for all seven rules, including `caps` having no `RULE_NOUNS` entry; `exempt_options` including a role Discord no longer has; **`_as_words` on newline, comma and mixed input**; `panel_minutes` |
| `tests/test_settings_store.py` | `automod_panel_minutes` round-trips, defaults 10, help mentions 15, is in `VALUE_KEYS`, refuses `-1` and the string `"15"` — the shape at `:1003–1013`; the same for `automod_arm_needs_confirm` |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `automod` (`:14`); `"automod"` **stays** in `STAFF_COMMANDS` (`:25`); the tree-limit test **re-measures and expects 38 UNCHANGED** (`:190`) |
| `tests/api/tools/test_mod.py` (302 lines) | ⚠️ **must stay green with no edit** — the proof the layer did not move |
| `tests/test_logkinds.py` (750 lines) | `automod.mode`, `automod.exempt_add` and `automod.exempt_remove` now go through `kind_via`; the three AST-walk guards named in checklist 34 must still pass |

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers — the
   expectation is NO CHANGE, 38 → 38** (one group's slot becomes one command's slot). ⚠️ **If
   it moves, stop** — something other than this build broke. With no token, measure it the only
   other way: `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`.
2. The parametrised state test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.automod, black_bloc.cogs.moderation.automod,
   black_bloc.api.tools.mod, black_bloc.panels"` — the substitute for a boot (wave-0 deviation
   5), and the line that catches the one new import edge this build creates (the cog →
   `panels`).
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (**expect the page/route counts
   unchanged** — no route is added or removed; the last measured figure is **17 pages / 142
   routes** at the voice landing, so state before AND after rather than trusting that number);
   `node --input-type=module --check < site/public/assets/labels.js`.
5. Checklist sweep before reporting — **1 and 2** (⚠️ *nothing in this build may change how a
   side effect is guarded or which kind a dry run gets*; the diff must show zero edits inside
   `punish` `:178`, `do_delete` `:135`, `do_timeout` `:162` and `_answer_for` `:499`), **8 and
   30** (`AnswersErrors` on every modal, select and view), **11** (`allowed_mentions` on every
   interpolated send — role and channel mentions are all over the exemption embed), **15/17**
   (the confirm-helper duplicate, §F), **21** (the arming gate reads COMPUTED permissions
   through `store.staff_roles`, unchanged), **22** (the bounds that vanished with the
   `app_commands.Choice`/`Range` parameters are rebuilt in the modal), **26** (both list-typed
   exemption keys keep a way to remove an entry — that is the removal select), **33** (§D),
   **34** (`set_mode`'s and `set_exempt`'s new `kind_via`).
6. ⚠️ **TEST MODE stands.** The bot speaks only in `#mute-me-bot-test-spam`
   (`TEST_CHANNEL_ID`) and DMs, enforced by `black_bloc/guard.py`. Run every sweep row in that
   channel. Two consequences worth stating rather than discovering: `_may_read` `:492` means
   the engine only ever sees the test channel while the guard is on, and **while a guard is
   installed `on` behaves like `shadow`** — nothing is punished, everything is logged
   (`code-notes.md` against `cogs/moderation/automod.py:503`). So a sweep that flips the mode
   to `on` proves the CONTROL works and proves nothing about enforcement, and the row must say
   so.

**Sweep rows — numbered at BUILD time, starting at the next free row.** `docs/access/sweeps.md`
holds 455 lines and its last row is **143** today, ⚠️ **but four wave-3 design docs are being
written in parallel and their builds may land first, so this document claims NO numbers.** The
build reads the file, starts at the next free row, and renumbers at landing. The Phase 6
appendix block at `:210–216` is rewritten **in place**, not added to.

| Do this | Expect |
|---|---|
| `/automod` as a Lead in `#mute-me-bot-test-spam` | ONE ephemeral panel: the whole block `/automod status` used to print — mode, resolved staff, what the member is told, warn threshold, modlog, both exemption lists, the acted-on/logged-only counts, then every rule on its own line — over **A rule… · What automod does… · Exemptions… · Refresh · Logs · Open on the site**. Nothing says `/automod status` or `/automod rule` anywhere |
| Look at the mode picker while `staff_channel_id` is still the test channel | it offers **off** and **shadow** and **NOT on**, and the panel says in words that the staff channel is still the test channel and what to set it to. Arming is not offered-and-refused; it is not offered |
| `A rule…` → `mention_spam` | its card: **Turn it off · Change the numbers… · Log only · Back**, and a *What it does…* picker showing delete, warn and timeout already ticked. **No Words…** — that button is `bad_words`' only |
| `Change the numbers…` → type `abc` in the window box | one sentence saying `window_s` takes a whole number — and **nothing is saved**: re-open the card and all three numbers are what they were, including the two that parsed |
| `Change the numbers…` → window `4000` | one sentence naming the 0–3600 range; again nothing saved |
| `Turn it off`, then re-open the card | the button now reads **Turn it on** — never both — and the line above it agrees, because both read the same rule object |
| `A rule…` → `bad_words` → `Words…` | the box is prefilled with the words there are; typing a list ONE PER LINE saves them all (not one long word), and so does a comma list; more than 200 is refused in words |
| `A rule…` → `caps` → `Change the numbers…` | the threshold box says it is a **percent, 1–100**, not a count — and 200 is refused |
| `Exemptions…` → *Stop watching a role…*, then *Stop watching a channel…*, then *Watch it again…* | each add says what happened and the lists above update; the removal select carries both the role and the channel with the right word each; a second add of the same thing says it was already exempt and changes nothing. Honeypot channels are named as also-never-read and are **not** on the removal select |
| Delete an exempt role in Server Settings, then `Exemptions…` | it is still on the removal select, labelled as a role Discord no longer has — the only surface that can tidy it up still offers to |
| `What automod does…` → **shadow**, then → **off**, then back to **shadow** | each leaves ONE `automod.mode` row in the log and the embed's first line changes; nothing is deleted and nobody is timed out in any of them |
| `Logs` | answers a **NEW** ephemeral message and the panel stays where it is |
| Leave the panel `automod_panel_minutes` (10) minutes | every control greys out and the footer reads *this panel has gone quiet — run /automod again* |
| Post five @mentions from a second account in the test channel | ⚠️ unchanged from today: ONE `automod.would_*` case card with **Apply now**, nothing deleted, a following "sorry" does not re-fire. **This row is the proof the panel changed nothing about enforcement** and it is the most important row in the set |

## I. The genuine forks — the owner decides, one at a time

**Settled first, by the standing rules, so they are NOT put to him:**

- ✅ **`/automod` stays staff-locked** (`default_permissions=STAFF_ONLY`) and `"automod"` stays
  in `STAFF_COMMANDS`. There is no member half of this feature.
- ✅ **Staff are re-checked before every move, reads included** (P8, pings deviation 10).
- ✅ **`on` is hidden rather than offered-and-refused** in S1/S2 (P3/P9).
- ✅ **`/automod` does not vanish when the mode is off** — measured, `HIDDEN_WHEN_OFF`
  (`command_visibility.py:16–19`) has no automod entry, and the owner answered this shape on
  2026-09-03 ("Visible") for applications.
- ✅ **The `Apply now` button on modlog case cards is left exactly as it is** (P14) — it is a
  persistent `DynamicItem` that belongs to the room, and it is already the staffer's phone-side
  review surface during the shadow rollout. Adding a verdict queue to the panel would be a
  third copy of what the modlog card and `page-moderation.js:296` already show.
- ✅ **The shadow → enforce rollout rule is untouched.** The panel is a door onto `set_mode`;
  what makes the flip legitimate is still the owner's judgement from the shadow log
  (`feature-list.md:45`), not the existence of a button.

**Three questions are genuinely his:**

- **F-A1 — does flipping the mode to `on` from the panel need a confirm step?** Every other
  transition is one press. `on` is the one that starts deleting messages and timing people out,
  and on the panel it is a single click on a picker — the shortest path to enforcement this
  app has ever had. The two existing refusals (`:656`, `:663`) stop an UNSAFE arm; nothing
  stops a *hasty* one.
  - **(a) Yes — off/shadow → `on` re-renders the root embed with "Are you sure?" and two
    buttons (`Yes, arm it` / `Keep it in shadow`), naming what will start happening. Every
    other transition, including `on` → `shadow` and `on` → `off`, stays one press.
    `automod_arm_needs_confirm` defaults `true`. Recommended.** Access-INCREASING moves get
    confirmed and access-REDUCING ones fail safe — the same asymmetry pings shipped with
    (fork I1) and the same one the global rules state.
  - (b) No — one press, and the panel simply says loudly what changed. Faster, and the two
    refusals plus the shadow log are already the real safety rail. `automod_arm_needs_confirm`
    still exists, defaulting `false`.
  - (c) Confirm on **every** mode change. Consistent, and wrong: it puts a speed bump in front
    of turning automod OFF, which is the move somebody makes when it is misfiring.

- **F-A2 — how does staff edit `bad_words` from Discord?** The site has a textarea, one word
  per line. On the panel it has to be a modal, and a modal is replace-the-whole-list.
  - **(a) One paragraph field, prefilled with the current list, one word per line — the site's
    shape exactly. Recommended.** Nothing is lost by accident because the box arrives full, it
    is the same mental model as the dashboard, and 200 words fits a 4000-character field with
    room to spare. Cost: a staffer who clears the box clears the list, with no undo.
  - (b) `Add a word…` / `Remove a word…` — two controls, no wipe risk, and the removal select
    caps at 25 so a long list is not fully reachable from Discord. Two more controls on a card
    that already carries five buttons.
  - (c) Site-only: the card says the word list is edited on the dashboard and links there.
    Cheapest, and it makes `bad_words` the one rule Discord cannot fully configure — which the
    "configurable both ways" rule points away from.

- **F-A3 — does the panel get controls for `automod_warn_threshold` and `mod_dm_on_action`?**
  `/automod status` PRINTS both (`:625`, `:626`) and no automod subcommand sets either; today
  they are reached through `/settings set-value` and the dashboard, so the "both ways" rule is
  already satisfied.
  - **(a) No — they stay lines on the embed, and the panel is exactly the eight subcommands'
    door. Recommended.** Both keys belong to moderation as a whole (`mod_dm_on_action` is read
    by `punish` `:279` AND by the manual mod commands), so a control on the automod panel would
    quietly edit the mod commands' behaviour from a page that does not say so.
  - (b) Yes — add a `Settings…` sub-panel with a threshold modal and a DM-style select. One
    window for a Lead arming the feature for the first time, at the cost of a second surface
    owning a shared key.

## J. What NOT to build, and what this costs

**Not in this build:**

- **Anything inside the enforcement path.** `on_message` `:439`, `on_message_edit` `:476`,
  `_answer_for` `:499`, `_post_case` `:553`, `punish` `:178`, `do_delete` `:135`, `do_timeout`
  `:162`, `contributing_messages` `:148`, `apply_case` `:342`, `message_to_delete` `:315`,
  `rewrite_card` `:324`, and every evaluation function in `black_bloc/automod.py` from
  `facts_from` `:304` to `channel_exempt` `:448`. The `_as_words` split (§F) is the sole
  exception and it changes parsing, not enforcement.
- **The `ApplyNowButton` and a verdict queue on the panel.** §I, settled.
- **Any new API route or site control.** No `/api/mod/*` route is added, removed or renamed;
  `site/mock/contract.json` is untouched.
- **A rules "reset to defaults" button.** `DEFAULT_RULES` `:30` is measured to be Carl-bot's
  live config (`code-notes.md` against `black_bloc/automod.py:30`), so a reset is a real
  operation — but it is a NEW capability, not a door swap, and it would be the first
  irreversible bulk write in the feature.
- **`count` / `important_only` on `Logs`.** Lost exactly as they were for `/request`,
  `/apply` and `/voice`; the site's Logs page has both.
- **Touching `AUTOMOD_MODES`.** Three modes, and none of them is renamed to rhyme with
  anything.
- ⚠️ **REPORT, do not fix — two measured defects found while writing this.** (1) The website
  can set `automod_mode` to `on` through the **generic settings API**, which validates against
  `KEY_CHOICES` (`settings_store.py:285`) only — so **neither arming refusal (`:656`, `:663`)
  applies on the web path**, and a guild with no resolved staff can be armed from the
  dashboard. Wiring `set_mode` into the settings route is a settings-API change, not a panel
  change, and belongs in its own pass. (2) `LOG_LEVEL_COMMANDS["pings"] = "pingroles"`
  (`settings_store.py:795`) names a command wave 2 retired, so `pings_log_level`'s help text is
  already wrong. Both go in the build's report, and (1) is a `KNOWN_ISSUES.md` candidate.

**Cost.** Measured wave-2 builds: memory **329k** (estimated 250–300k), golive **464k**
(230–300k), youtube **371k** (180–250k), pings **379k** (300–360k), voice **385k** (420–480k).
⚠️ **Four of the five ran OVER their band** — only voice, the one estimated highest, came in
under — so treat a band as a floor, not a midpoint.

Sizing this one: eight subcommands (fewer than pings' twelve and voice's twenty-two, more than
memory's five); an **830-line cog of which roughly 450 lines are the untouched enforcement
half**, so the surface actually being rewritten is about 380 lines — the smallest of wave 3;
an **861-line cog test file whose engine half must not move**, which is cheaper than rewriting
it but demands care; **three sub-panels** (rule card, exemptions, arming confirm) against
voice's four; **two modals**; **no new module and no new test file** — `black_bloc/automod.py`
and `tests/test_automod.py` both already exist, which is the single biggest saving against
voice; **no site route change**; and eleven string/doc rewrite sites.

**Estimate: 300–360k Opus tokens.** The pure-module and test-file savings pull it below pings
and voice; the three-way mode, the seven-rule modal matrix and the do-not-touch-the-engine
discipline pull it above memory.

**Prep before dispatch** (per the ≥150k rule): clean tree, a fresh usage read, and a brief that
tells the agent to **commit at clean boundaries, one layer at a time** — (1) the pure-module
additions + `_as_words` + their tests, (2) the cog extractions (`set_mode`, `set_exempt`,
`case_totals`, `status_lines`, `arming_refusal`) + their tests, (3) the panel itself, (4) the
string and doc sweep — so a kill costs the last layer rather than the build. The brief carries
`docs/info/review-checklist.md`, `docs/info/panels-program.md` and this file, and the standing
rule that **`git stash` is never run in a shared tree**.

## Build deviations

Written by the build agent, 2026-09-04, on `worktree-agent-ae7bb4ba9c5540ad4`. Everything
not listed here was built as this document says.

1. **There IS a Settings sub-panel, which §C's table does not list.** §I's fork F-A3 was
   answered (a) — no controls for `automod_warn_threshold` / `mod_dm_on_action` — and the
   brief spelled that as *"read-only lines on the Settings sub-panel saying they are set on
   the Moderation page"*. The two keys §D adds also need a Discord door of their own
   (checklist 33, and every shipped panel puts its `*_panel_minutes` on the panel rather than
   only in `/settings set-value`). So the root's row 2 carries **Exemptions… · Settings… ·
   Refresh · Logs · Open on the site** — exactly Discord's five — and the sub-panel holds
   `Numbers…` (panel minutes), one toggle for `automod_arm_needs_confirm` that says which way
   it is set, `Back`, and the two read-only lines with a sentence naming where they live.
   Both keys are still reachable from the Settings page and `/settings set-value`.
2. **`root_buttons` takes `has_site` only, not `may_arm`.** §F gives the signature
   `root_buttons(*, may_arm, has_site)`; `may_arm` changes nothing about the buttons — it
   governs the mode SELECT (`mode_options`) and, through `needs_confirm`, the confirm view.
   A parameter the function cannot use is dead weight, so it was dropped rather than passed
   and ignored.
3. **`_typed` moved as `typed`, public.** §E says it moves and is "re-exported from the cog by
   name so no existing import changes" — measured, **nothing outside the cog imported it**
   (or `RULE_FIELDS`), so there was nothing to preserve, and a module-private name that
   crosses a module boundary is not private. `RULE_FIELDS` moved unchanged.
4. **`black_bloc/automod.py` imports `panels` INSIDE two functions, not at module level.**
   §F's `panel_minutes` is "a one-liner over `panels.panel_minutes`, exactly as the five
   shipped panels do" — but the five shipped pure modules are not imported BY
   `settings_store.py`, and this one is (`validate_rules`). `panels` imports
   `DB_UNAVAILABLE` from `settings_store`, so a module-level import closes the loop and every
   import of `settings_store` dies. `panel_minutes` and `exempt_options` (which needs
   `SELECT_OPTION_LIMIT`) each do a function-local import instead — cheaper than a second copy
   of either fact. The §H import check is what would have caught it.
5. **The confirm's second button is labelled from the current mode.** §I's (a) names
   `Keep it in shadow`; from `off → on` that sentence is wrong, so the button reads **Keep it
   off** there. `Yes, arm it` is unchanged.
6. **The rule picker's option labels are sliced, not built with `panels.option_label`.** §C
   says "clamped by `panels.option_label`/`SELECT_OPTION_LIMIT`"; `option_label`'s shape is
   `#<id> · <status> · <text>` and would render `#mention_spam · how many…`. The label is
   `f"{name} — {RULE_HELP[name]}"[:SELECT_OPTION_LIMIT]`, which is the clamp without the
   request-row prefix.
7. **`status_lines` decides "every rule is off" from the rules, not from `rules_summary`'s
   sentence.** Comparing the summary string to the literal `"every rule is off"` would put
   one fact in two homes; the line renders when no `rule_config(book, name)["enabled"]` is
   true, which is the same condition `rules_summary` uses.
8. **`_as_words`' type error now names lines as well as commas.** §F's change is the split;
   the sentence for a non-string value still said "takes a comma-separated list of words",
   which would have been the one place still telling somebody the old rule.
   `RULE_HELP["bad_words"]` was reworded to *"the bad_words rule's own word list holds them"*
   per §E — it is served to the website by `rule_row`, so it names no command at all.
9. **`LOG_LEVEL_COMMANDS["automod"]` was REMOVED, not re-pointed** (§E left the choice open).
   `log_level_help` renders *"and in `/<command> logs`"*, and there is no `/automod logs`
   after this build; with no row the help text simply says the lines are kept on the
   dashboard, which is true. ⚠️ This makes automod the only correct row in that map: **eight
   of the remaining thirteen now name a retired subcommand too** (`pings` → `pingroles`,
   already flagged by §J; plus `tempvoice` → `voice`, `events` → `event`, `poll`, `birthday`,
   `golive`, `request`, `applications`). Reported, not fixed — it wants one pass of its own.
10. **A new log kind, `automod.settings`** (ROUTINE, beside `automod.rule`), for the Settings
    sub-panel's write. §F lists no function for those two keys because §D treated them as
    registry-only; `save_settings` follows `youtube.save_setup`'s shape exactly — validate
    every key before writing any, then ONE log row with `kind_via`.
11. **`AutomodMove` has no `question` / `yes` fields.** §F asks for `AutomodMove` +
    `PANEL_MOVES` + the two button functions; the confirm's question and its two labels are
    one each, so they are module constants (`ARM_QUESTION`, `ARM_MOVE`, `KEEP_*_MOVE`) rather
    than fields carried on every move. `PANEL_MOVES` is the whole set and a test proves every
    entry is distinct.
12. **The confirm helper was built LOCALLY and nothing was added to `panels.py`**, as §F
    instructs. `open_confirm` / `build_confirm` here is the third hand-rolled copy after
    `youtube.open_confirm` and pings' deviation 8 — **handed to the conductor to fold into
    `panels.py` at the merge**, the way `clamped` landed.

⚠️ **What was NOT verified.** Nothing was run against Discord: no boot (there is no bot
token in this environment), no panel opened, no modal submitted, no message judged. The
substitutes actually run are `python -c "import black_bloc.automod,
black_bloc.cogs.moderation.automod, black_bloc.api.tools.mod, black_bloc.panels"` (passes),
the full `pytest` suite (**4330 passed**, 4268 before), `ruff check .` (clean), `node
site/mock/check.mjs` (**17 pages / 142 routes**, unchanged) and `node --input-type=module
--check < site/public/assets/labels.js` (passes). `commands synced` was measured through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` at **38, unchanged**.
Whether a real client submits an EMPTY multi-`Select` at `min_values=0` is still unproven —
`Log only` is the fallback and both paths are built.
