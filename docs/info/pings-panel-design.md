# Ping roles — `/pings` is ONE command that opens a panel (wave 2)

> **Audience:** the build agent and the reviewer (Claude sessions), and the owner for §I.
> **Status:** TRACKED · **DESIGN, unbuilt.**
> **Last verified: 2026-09-03** — every `path:line` below was READ in this working tree on `main`
> (the tree whose newest commit is `1735ff8`, after the four wave-1 panels merged), in
> `black_bloc/pings.py`, `black_bloc/cogs/content/pings.py`, `black_bloc/panels.py`,
> `black_bloc/api/tools/pings.py`, `black_bloc/settings_store.py`, `black_bloc/command_visibility.py`,
> `black_bloc/logkinds.py`, `black_bloc/personas.py`, `black_bloc/cogs/community/requests.py`,
> `tests/test_bot.py`, `docs/access/sweeps.md`, `docs/access/OWNER_GUIDE.md`, `docs/info/code-notes.md`.
> Counted, not estimated: **12 leaf subcommands over 2 top-level slots**; `len(top) == 42`
> (`tests/test_bot.py:198`); `tests/cogs/content/test_pings.py` **27 tests**, `tests/test_pings.py`
> **36**, `tests/api/tools/test_pings.py` **16**; `docs/access/OWNER_GUIDE.md` has **zero** matches
> for "ping".
> ⚠️ **NOT verified: anything against Discord.** Nothing was run — no boot, no pytest, no ruff, no
> `check.mjs`, no panel opened. Whether the client submits an EMPTY `RoleSelect` at `min_values=0`
> is the same unproven edge [`events-panel-design.md`](events-panel-design.md) flags (its deviation 6
> built BOTH paths); §C names the same fallback. The `path:line` keys will drift as sibling wave-2
> branches merge — **trust the anchor text, not the number.**
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md),
> whose `## Deviations` foot is the trap list. Feature behaviour is
> [`phase15-design.md`](phase15-design.md) (F14), whose seven defaults-as-settings (D1–D7) this
> design changes none of.

## A. Measured today — two groups, twelve subcommands

`pingroles` is a `Group` (`cogs/content/pings.py:98`, `default_permissions=STAFF_ONLY`) with a nested
`streamer` group (`:103`); `ping` is a `Group` named **pings** (`:106`, member-visible, no
`default_permissions`) with nested `events` (`:107`) and `fans` (`:110`) groups. **5 + 7 = twelve
leaf subcommands over two top-level slots.**

| Subcommand | Line | Who | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/pings follow <streamer>` | `:181` | member; `_ready` `:114` + `_on` `:124`; autocomplete `_streamer_choices` `:143` | `_follow` `:199` — ⚠️ **all inline** `:204–234`: `_wanted_streamer` `:159`, `role_of` `:79`, `wears` `:83`, `pings.wear` (`pings.py:260`), the sentence, `log_action("pings.follow")` |
| `/pings unfollow <streamer>` | `:190` | member | the same `_follow` with `adding=False` |
| `/pings list` | `:236` | member; ⚠️ **`_on` is NOT asked** — reading works with the mode off | `pings.events_role_id` (`pings.py:468`), `all_fan_roles` (`:182`); ⚠️ **lines built inline** `:242–259`, paged by `_pages` `:136` |
| `/pings events on\|off` | `:262` `:266` | member | `_events` `:270` — ⚠️ **all inline** `:274–300`: unset / gone refusals, `wears`, `pings.wear`, sentence, `log_action("pings.events_on")` |
| `/pings fans on` | `:302` | member | ⚠️ **inline** `:307–316`: `CREATION_KEY == STAFF` gate, `_streams` `:331`, then `ensure_fan_role` (`pings.py:362`) — shared |
| `/pings fans off` | `:318` | member | ⚠️ **inline** `:323–329`: `get_fan_role` guard (`FANS_OFF_NONE` `:67`), then `remove_fan_role` (`pings.py:410`) — shared |
| `/pingroles setup [role]` | `:337` | `require_staff` `:344`; allowed with the mode OFF (`code-notes.md:4540`) | `setup_events_role` (`pings.py:489`) — shared, nothing inline |
| `/pingroles streamer add <member> [role]` | `:356` | `require_staff` `:364` | `ensure_fan_role(…, staff=True)` — shared; `staff=True` is the ONLY way past mode off (`code-notes.md:4536`) |
| `/pingroles streamer remove <member>` | `:381` | `require_staff` | `remove_fan_role` — shared |
| `/pingroles streamer list` | `:398` | `require_staff` | `all_fan_roles`; ⚠️ **lines inline** `:410–418` (`STREAMER_LINE` `:74`, `followers_word` `:87`) |
| `/pingroles logs` | `:421` | `send_logs` carries its own `require_staff` | `send_logs(interaction, "pings", count, important_only)` |

**Not subcommands and NOT moving** (P14, program §7): the auto-maintained **Streamer pings** role-menu
panels (`streamers`, `streamers-2`, … — `sync_streamer_menus` `pings.py:314`) and the **Notifications**
panel (`ensure_notifications_menu` `:472`). Those are `DynamicItem` posts that belong to the room and
survive restarts. The ephemeral panel is a SECOND door onto the same rows and the same helpers.

**There is no state machine.** Unlike every wave-1 feature, `golive_fan_roles` has no `status`
column and `pings.py` has no `TRANSITIONS`. The state a button renders from is a **tuple of
booleans**, not a status word — §C says which — so §G's parametrised test is over that tuple. A
builder looking for `TRANSITIONS` will not find one; that is correct, not a gap.

**The shared layer is ALREADY pure.** `black_bloc/pings.py` holds the store, the role calls, the two
`Outcome` paths and the menu sync, and `api/tools/pings.py:8` imports it from there — the opposite of
events, whose expensive half was moving the layer out of its cog. **No move is part of this build.**

## B. The decision — one `/pings`, member panel and staff panel

**`/pings` becomes a single `app_commands.command`; both `Group`s go and `/pingroles` disappears.**
`commands synced` drops by **one** relative to whatever it reads when this lands — 42 today, so 41
for this feature alone, but **the build MEASURES it at boot and edits `tests/test_bot.py:198` to what
it reads** (requests deviation 7). Other wave-2 features drop one each; the conductor reconciles at
merge.

The one command keeps **no `default_permissions`** — `pings` is member-visible today
(`tests/test_bot.py:65`) and stays in `MEMBER_COMMANDS`; `"pingroles"` leaves `STAFF_COMMANDS`
(`:40`) and `LOGS_GROUPS` (`:21`). The staff half is gated at runtime as it always was
(`require_staff` / `still_staff`), never by the UX lock.

**Root panel** — `build_panel(bot, guild, actor)`, one ephemeral embed + `Panel` subclass, split on
`store.is_staff(actor)`. Embed title **Your pings**; description = the `/pings list` lines (`:242–259`
extracted) plus, for staff, a counts line (**N** streamer(s) · **N** with a role Discord still has).

| Row | Control | Rendered when |
|---|---|---|
| 0 | Select **"Follow a streamer…"** — fan-role rows whose Discord role resolves and the caller does NOT wear, ≤25, `capped_placeholder` | mode on **and** ≥1 such row |
| 1 | Select **"Stop following…"** — the rows the caller DOES wear, ≤25 | ≥1 such row (**not** gated on the mode — see §C) |
| 2 | `Turn event pings on` / `Turn them off` · `Start my own ping role` / `Take my ping role away` · `Refresh` | per §C's table; `Refresh` always |
| 3 | **staff only:** `Streamers…` · `Set up the Events role` · `Settings` · `Logs` · `Open on the site` (link) | exactly Discord's five-per-row cap with an origin configured, four without |
| 4 | — | free; leave it free |

⚠️ **`Open on the site` renders for STAFF ONLY.** Every `/api/pings/*` route sits behind
`staff_dependency` (`api/tools/pings.py:59`) and the Pings section lives on `golive.html`
(`FEATURE_PAGES["pings"]` — `logkinds.py:102`), which a member cannot open. A link button that leads
to a sign-in wall is P9's dead button in another costume.

⚠️ **The 25-cap placeholder does NOT say "the rest are on the site" for the member selects.** The
library's `CAPPED_PLACEHOLDER` (`panels.py:14`) does, and for a member that is false. Pass
`capped=` (the parameter exists — `panels.py:57`) with a sentence naming the **Streamer pings**
panels, which page past 25 by design (`pings.py:299`, `code-notes.md:4532`). Staff's `A streamer…`
select keeps the library default.

## C. The button table per state, the sub-panels, the modals

Each is a **re-render in place**: `retire(previous)` first (P6), `defer()` then
`edit_original_response` (P5), `db_ready` on every click (requests deviation 6), `still_staff` before
every staff move (P8).

**The member half.** The state is `(mode_on, events_role: unset|gone|worn|not_worn, own_role: yes|no,
creation, streams, followed_count, unfollowed_count)`. Every refusal below is a LINE in the embed, not
a disabled button (P9), and `/pings` never refuses the whole command.

| State | Rendered | Calls |
|---|---|---|
| mode off | no move at all; embed carries `pings.OFF` (`pings.py:49`) reworded, plus the caller's current state so the panel is still worth opening | — |
| mode on · events role unset | no toggle; line from `LIST_EVENTS_UNSET` (`:64`) — staff press *Set up the Events role* | — |
| mode on · events role set, gone from the server | no toggle; line from `EVENTS_ROLE_GONE` (`pings.py:58`) reworded | — |
| mode on · resolves · not worn | `Turn event pings on` (success) | `set_event_pings(add=True)` — §F |
| mode on · resolves · worn | `Turn them off` (secondary) | `set_event_pings(add=False)` |
| mode on · own row exists | `Take my ping role away` (danger) → `Yes, take it away` / `Keep it` | `stop_own_fan_role` — §F · ⚠️ fork **I1** |
| mode on · no own row · `pings_fan_role_creation == staff` | no button; line from `STAFF_ONLY_CREATION` (`pings.py:82`) reworded | — |
| mode on · no own row · creation `self`/`auto` · not a streamer | no button; line from `NOT_A_STREAMER` (`:77`) reworded | — |
| mode on · no own row · creation `self`/`auto` · streams | `Start my own ping role` (primary) | `start_own_fan_role` — §F |
| mode on · no fan roles anywhere | neither select; line from `NO_STREAMERS` (cog `:28`) reworded | — |

⚠️ **"Stop following…" is NOT gated on the mode, and that is deliberate.** Today `/pings unfollow`
refuses while the mode is off (`_on` `:124`), which means a member who wants OUT of a ping cannot get
out until staff turn the feature back on. Taking a role OFF yourself is the access-REDUCING move; it
fails safe and it needs no feature switch. `Follow…`, both fan buttons and the Events toggle stay
mode-gated exactly as today. This is a deliberate behaviour change, one line in `follow_streamer`, and
sweeps row 108 tests it.

**The staff half** renders with the mode OFF as well as on — `setup_events_role` is allowed while off
and says so (`SETUP_STILL_OFF` `pings.py:121`, `code-notes.md:4540`), and `ensure_fan_role(staff=True)`
is the one path past it (`code-notes.md:4536`). The embed says the feature is off and nobody can opt
in yet; the staff controls stay.

**Streamers sub-panel** (`Streamers…`). Embed = the `/pingroles streamer list` lines verbatim
(`streamer_lines`, §F — `STREAMER_LINE` `:74` + `followers_word` `:87`), `STREAMER_LIST_EMPTY` (`:70`)
reworded when there are none, one query, clamped at 4000 characters (the applications roster
precedent: every row readable, only the select capped).

| Row | Control |
|---|---|
| 0 | Select **"A streamer…"** over `all_fan_roles`, ≤25, `panels.capped_placeholder`, label = `pings.option_label(guild, row)` (`pings.py:306`) |
| 1 | `discord.ui.UserSelect` **"Give somebody a ping role…"** (`max_values=1`) → the role-pick step |
| 2 | `Refresh` · `Back` |

**The streamer card** (staff picked one). Embed: display name, `<@&role_id>` or "the role is gone from
the server" (`FOLLOWERS_UNKNOWN` `:76` — never a `0`, `code-notes.md:4565`), the follower count,
`created_at`, who started it.

| Buttons (+ `Back` always) | Rendered when | Calls |
|---|---|---|
| `Remove their ping role` (danger) → `Yes, take it away` / `Keep it` | always | `remove_fan_role` (`pings.py:410`) |
| `Make the role again` (primary) | `guild.get_role(row["role_id"]) is None` | `ensure_fan_role(…, staff=True)` — a row whose Discord role was deleted by hand is already treated as no row and `INSERT OR REPLACE`d (`code-notes.md:4537`) |

That second button is the staff-final-say rule (`CLAUDE.md`, owner 2026-09-03): a streamer whose role
somebody tidied away is otherwise a row staff can only delete, never repair, from Discord.

**The role-pick step** — ONE shape, used twice, because both retired commands take an optional role
(`/pingroles setup [role]` `:340`, `/pingroles streamer add … [role]` `:357`) and a `UserSelect` cannot
carry a second value. Row 0: `RoleSelect` (`min_values=0`) *"Use this role instead — leave it empty and
one is made"*; row 1: `Set it up` / `Make the role` · `Back`. It mirrors the site's own card
(`page-golive.js:214–243`: member picker + optional role select + one button) — one shape, two doors.
⚠️ If the client will not submit an empty `RoleSelect` (unverified, see the header), the fallback is
that the confirm button ALSO works with nothing picked, which is the same write path with
`existing_role=None`; build both, as the events build did (its deviation 6).

**Settings sub-panel** (staff). Embed = today's six `pings_*` values as lines.

| Row | Control | Key |
|---|---|---|
| 0 | `Mode…` select | `pings_mode` (`PINGS_MODES`) |
| 1 | `Who may start one…` select | `pings_fan_role_creation` (`PINGS_CREATORS`) |
| 2 | `On unlink…` select | `pings_fan_role_on_unlink` (`PINGS_ON_UNLINK`) |
| 3 | `Names…` (modal: events-role name, fan-role template, panel minutes) · `Delete the role too: on/off` toggle · `Open on the site` (link) · `Back` | `pings_events_role_name`, `pings_fan_role_template`, `pings_panel_minutes`, `pings_fan_role_delete` |

⚠️ **Yes, a sub-panel, even though `golive.html` already renders the whole `pings` namespace**
(`page-golive.js:539`, `:557`). Events built one because the site had nowhere to point; here the
site DOES — but the applications build's deviation 4 settled the principle: a Lead should not have to
leave Discord to flip a decision the panel itself is about, and `pings_mode` is exactly that. The
`Open on the site` link on row 3 is what keeps one fact one home for the rest.

The `Names…` modal ECHOES what the template will produce (`fan_role_name` `pings.py:143` against the
caller's own display name) rather than only saving it — the fallback there swallows a broken template
silently (`code-notes.md:4528`), so a staffer who types `{game} pings` would otherwise see "saved" and
get `{name} pings`.

**Modals** — all `AnswersErrors` + `discord.ui.Modal`, one shape (P12). There is exactly one:
`Names…`. Nothing here sends a person a note, so `panels.NoteModal` has no caller in this feature —
do not import it for the sake of symmetry.

**`Logs`** — a button answering a NEW ephemeral followup (P11), `send_logs(interaction, "pings")`,
which carries its own `require_staff`. ⚠️ The `count` / `important_only` options (`:423–425`) are
LOST, as they were for `/request` and `/apply`; the site's Logs section under the Pings section has
both (`page-golive.js:562`).

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `pings_panel_minutes` | `int` | **10** | **NEW.** The only key this build adds. Registered in a `pings` block of its own — `KEY_TYPES`, `KEY_HELP`, `default()` — appended after the polls/events blocks (`settings_store.py:987` is the last such block) so parallel wave-2 branches merge textually. Help text carries KI-20's warning in the shape the other five use: 15+ loses the "gone quiet" footer because Discord's interaction token expires at 15 minutes. ⚠️ **No `KEY_MIN`/`KEY_MAX` entry** — none of the five existing `*_panel_minutes` keys has one, and inventing a bound for this one alone breaks one-fact-one-home |

**Read, not changed:** `pings_mode` (`:166`), `pings_events_role_name` (`:167`),
`pings_fan_role_creation` (`:168`), `pings_fan_role_template` (`:169`), `pings_fan_role_on_unlink`
(`:170`), `pings_fan_role_delete` (`:171`), `golive_ping_role_id` (`:156`), `events_ping_role_id`
(`:184`), `pings_log_level`.

⚠️ **There is NO own-list key here, and that is not an oversight.** `request_panel_own_list` /
`event_panel_own_list` / `applications_panel_own_list` decide whether a member sees rows OTHER people
could also see. This panel shows a member only which roles they are wearing — Discord shows them that
anyway — so a switch to hide it would hide the whole point of the command. Do not add one.

Also add the one label so the Settings page does not fall back to a raw key name:
`site/public/assets/labels.js` beside the `pings_*` block (`:39–45`) and the matching row in
`site/mock/server.mjs` (`:298–303`). ⚠️ Measured: only the applications pair took this step
(`labels.js:168–169`, `server.mjs:415`) — events, polls and birthdays skipped it and `check.mjs` is
still green, so this is a courtesy, not a gate.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit (P15). `HIDDEN_WHEN_OFF`
(`command_visibility.py:16`) has **no** pings entry today — measured — so nothing there changes.

| Thing | Where | Becomes |
|---|---|---|
| `pingroles` Group + `streamer` Group + 5 children | `:98`, `:103`, `:337`, `:356`, `:381`, `:398`, `:421` | the Streamers sub-panel, the streamer card, the role-pick step, `Set up the Events role`, `Logs` |
| `ping` Group + `events` + `fans` Groups + 7 children | `:106`, `:107`, `:110`, and the §A table | `@app_commands.command(name="pings")` + the buttons and selects of §B/§C |
| `_streamer_choices` `:143` · `_wanted_streamer` `:159` · `CHOICE_LIMIT` / `NAME_LIMIT` `:25` | — | **deleted with the autocomplete.** A select carries the `user_id` as its value, so the "somebody typed a display name" second try (`code-notes.md:4550`) has no caller. `NO_SUCH_STREAMER` `:32` survives only as the stale-select refusal |
| `_say` `:130` · `_pages` `:136` | — | `panels.answer`; the embed replaces the paged list. ⚠️ `pages_under_limit` keeps its `/rolemenu showall` and `/help` callers — do not delete it |
| `LOGS_GROUPS["pingroles"]` | `tests/test_bot.py:21` | **deleted** — `/pings` is not a `Group` with a `logs` child, so `:175` and `:221` would `KeyError` |
| `STAFF_COMMANDS` `"pingroles"` | `tests/test_bot.py:40` | **deleted**; `MEMBER_COMMANDS` `"pings"` (`:65`) stays |
| `assert len(top) == 42` | `tests/test_bot.py:198` | **one lower than whatever the build measures** — never a hard-coded absolute (§B) |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently tells
somebody to run something that will not exist. In `black_bloc/pings.py`: `:53` `NO_EVENTS_ROLE`, `:58`
`EVENTS_ROLE_GONE`, `:77` `NOT_A_STREAMER`, `:82` `STAFF_ONLY_CREATION`, `:87` `ALREADY_HAS_ONE`,
`:91` `NO_FAN_ROLE`, `:95` `CREATED`, `:100` `REUSED`. In `cogs/content/pings.py`: `:28` `:32` `:36`
`:39` `:43` `:48` `:52` `:55` `:58` `:63` `:65` `:67` `:70`. ⚠️ **Leave alone**: the `/rolemenu post`
half of `CREATED` `:95` and `SETUP_MENU_ADDED` `:119` (role menus is wave 3), the
`/settings set-value` half of `OFF` `:49` and `SETUP_STILL_OFF` `:121` (fork F3, wave 4), and the
`/twitch link` half of `NOT_A_STREAMER` `:77` (golive/twitch is a **sibling wave-2 build** — say
`/twitch link` and let the conductor reconcile).

⚠️ **`black_bloc/personas.py:80–82` is the chat bot's own answer** to "how do I get SuperNamu's
pings?" and names four dead subcommands (`/pings follow`, `/pings events on`, `/pings fans on`,
`/pings list`). Rewrite it to `/pings` and the panel's buttons — this is the applications build's
`personas.py:95–96` finding in the same place.

**Site strings** (no route changes; `api/tools/pings.py` is untouched): `settings_store.py:487`
(`pings_events_role_name` help names `/pingroles setup`) and `:491–492` (`pings_fan_role_creation`
help names `/pings fans on` and `/pingroles streamer add`), with their byte-mirrors in
`site/mock/server.mjs:299` and `:300`; `site/public/assets/page-golive.js:188` ("their own with
/pings fans on"); the mock's refusal strings `server.mjs:2618`, `:2638–2639`, `:2648`.
`page-golive.js:184` ("or with /pings") is still TRUE — leave it.

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md` rows **38–42** (`:96–100`)
rewritten in place, not added to; `docs/info/feature-list.md:52`; `docs/info/architecture.md:192–193`;
`docs/info/cutover-plan.md:43`; `docs/info/phase15-design.md` gets a dated "superseded by the panel"
line at the top, **not** a rewrite (its `:49`, `:63`, `:97–104`, `:117–121`, `:161–171`);
`docs/info/panels-program.md:79` (the Ping roles row → shipped); `docs/info/code-notes.md` re-keyed at
the merge — the pings sections at `:4523`, `:4543`, `:4561`, and specifically `:4548` (the
`ping`-vs-`pings` attribute trap, whose Group goes), `:4549` (`pages_under_limit`, whose `/pings list`
caller goes) and `:4550` (the typed-name second try, deleted). ⚠️ **`docs/access/OWNER_GUIDE.md` names
none of them** — measured, zero matches for "ping"; only its sweeps count (`:71`, "95 rows") moves.

## F. Extractions (P4) — one function per move, called by BOTH doors

All of these go into **`black_bloc/pings.py`**, which is already the pure module the site imports
(`api/tools/pings.py:8`). Each does ONE write and ONE log row, returns the sentence, and takes
`via: str = VIA_DISCORD` whose kind is built with `kind_via` (checklist 34) — as `ensure_fan_role`
`:362` and `remove_fan_role` `:410` already do.

| New | Replaces | Note |
|---|---|---|
| `async follow_streamer(bot, guild, member, row, *, add, via=VIA_DISCORD) -> str` | `_follow` `:199–234` | the `role_of` / `wears` / already-following guards, `wear`, the sentence, `log_action("pings.follow"/"pings.unfollow")` |
| `async set_event_pings(bot, guild, member, *, add, via=VIA_DISCORD) -> str` | `_events` `:270–300` | includes the unset / gone refusals and `pings.events_on`/`events_off` |
| `async start_own_fan_role(bot, guild, member, *, streams: bool, via=VIA_DISCORD) -> Outcome` | `fans_on` `:307–316` | ⚠️ **`streams` is an ARGUMENT, not a query.** `_streams` `:331` calls `get_link` / `latest_session`, which live in **`cogs/content/golive.py:137` and `:225`** — and that cog already does `from ... import pings` (`golive.py:14`). Querying them from `black_bloc/pings.py` is an import CYCLE. Moving them into `black_bloc/golive.py` would fix it and is mechanical — **do not**: the golive/twitch panel is a sibling wave-2 build rewriting that file. The cog keeps `_streams` and passes the boolean |
| `async stop_own_fan_role(bot, guild, member, *, via=VIA_DISCORD) -> Outcome` | `fans_off` `:323–329` | the `FANS_OFF_NONE` guard + `remove_fan_role` |
| `def notification_lines(guild, member, rows, events_role_id) -> list[str]` | `pings_list` `:242–259` | the member embed's body, `LIST_*` strings kept |
| `def streamer_lines(guild, rows) -> list[str]` | `streamer_list` `:410–418` | the Streamers sub-panel's body |
| `def role_of(guild, role_id)` · `def wears(member, role_id)` · `def followers_word(guild, role_id)` | cog `:79` `:83` `:87` | move whole; the cog re-exports nothing — nothing outside it imports them (measured) |
| `def counts_of(rows, guild) -> dict[str, int]` | new | the staff counts line: streamers · how many roles Discord still has |
| `def panel_state(...)` + `PANEL_BUTTONS` + `def panel_buttons(state) -> tuple[Move, ...]` | §C's table AS DATA | keyed by the boolean tuple, **not** by a status (§A) |
| `def panel_minutes(store, guild_id)` | one-liner over `panels.panel_minutes` (`panels.py:76`) | exactly `requests.py:510` |
| `def site_page_url(origin) -> str \| None` | ⚠️ **DO NOT write a fifth copy.** It exists four times already — `requests.py:503`, `events.py:1267`, `applications.py:624`, `cogs/community/polls.py:1872` — differing only in the `FEATURE_PAGES[...]` key. **Import one** (`requests.py`'s) and pass the key, or add `panels.site_page_url(origin, feature)` if `panels.py` is free of sibling edits at build time. This is checklist 15, reported in §J |

⚠️ **`pings.option_label(guild, row)` `:306` and `panels.option_label(ident, status, text)`
`panels.py:64` share a NAME and nothing else.** Do not fold them (wave-0 deviation 2 left the library
one deliberately) and do not `from ...panels import option_label` into a module that already defines
one — import the module, not the name.

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/content/test_pings.py` (27 today) | `/pings` answers ephemerally with a panel; a member sees the two follow selects and the two toggles and **no** `Streamers…` / `Settings` / `Logs` / `Open on the site`; staff see all of it, **including with `pings_mode` off**; **parametrised over every row of §C's table — the panel renders exactly its row and no other**; each button calls its shared function with `via` untouched (mock it); `Stop following…` renders with the mode off and `Follow a streamer…` does not; a select capped at 25 says so **and names the Streamer pings panels, not the site**; the streamer card's `Make the role again` appears only when the role is gone; the role-pick step writes with and without a role picked; `Names…` echoes the rendered template and a broken one falls back visibly; `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-card moves nothing (`still_staff`, every site); `db_ready` after a defer; timeout disables every item and a re-render `retire`s the view it replaced |
| `tests/test_pings.py` (36) | every new pure function in §F; `panel_buttons` over the whole state tuple; `notification_lines` / `streamer_lines` / `counts_of` / `panel_minutes`; `follow_streamer` and `set_event_pings` each leave exactly ONE log row with the right kind (assert the COUNT, not just the kind — checklist 34) |
| `tests/test_settings_store.py` | `pings_panel_minutes` round-trips, defaults 10, is in `KEY_TYPES` and has `KEY_HELP` |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `pingroles`; `STAFF_COMMANDS` loses `pingroles`; `MEMBER_COMMANDS` keeps `pings`; the tree-limit test **recounts** |
| `tests/api/tools/test_pings.py` (16) | ⚠️ **unchanged** — no route moves and no route is added. Unchanged assertions are the proof the refactor changed nothing (wave-0 deviation 4) |

The existing shared-function tests (`ensure_fan_role`, `remove_fan_role`, `setup_events_role`,
`sync_streamer_menus`, the 26-row paging, `announced_fan_role`) **stay green untouched.**

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers** — the drop must be
   exactly one for this feature. With no token, measure it the only other way:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` counts the real tree
   (events deviation 13, applications deviation 11).
2. The parametrised state test: every row of §C renders its buttons and no other.
3. `python -c "import black_bloc.pings, black_bloc.cogs.content.pings, black_bloc.api.tools.pings,
   black_bloc.cogs.content.golive, black_bloc.cogs.content.youtube, black_bloc.personas"` — the boot
   substitute (wave-0 deviation 5). ⚠️ `golive.py` and `youtube.py` are in the list on purpose: both
   `from ... import pings`, and §F's cycle trap is exactly what this catches.
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (the route count is **unchanged** — this design
   adds no route); `node --input-type=module --check < site/public/assets/labels.js` (⚠️ that file
   failed to parse once — `code-notes.md:5008`).
5. Checklist sweep before reporting — **8**, **11** (a fan role must never be mentioned in a panel
   reply — phase15 §Guard rails), **12**, **15** (the five `site_page_url` copies, §F), **17** (the
   template fallback, `pings.py:143`), **22**, **29** (the empty `RoleSelect` submit checked against
   the installed source, not guessed), **30**, **33** (§D), **34** (assert the log-row COUNT).

**Sweep rows — this feature takes 104 onward** (`docs/access/sweeps.md`'s last written row is **102**;
**103 is already claimed**, so start at 104 and **renumber at landing** if a sibling wave-2 branch got
there first). Rows **38–42** (`:96–100`) are rewritten in place, not added.

| # | Do this | Expect |
|---|---|---|
| 104 | `/pings` as a plain member with the mode ON | ONE ephemeral panel: your pings written out, **Follow a streamer…**, **Stop following…** if you follow one, the Events toggle, the fan button, **Refresh** — and no Streamers…, no Settings, no Logs, no site link |
| 105 | **Follow a streamer…** → a name, then **Stop following…** → the same name | the role goes on and comes off; the panel re-renders each time; `/pingroles logs`' successor shows `pings.follow` then `pings.unfollow`, one row each |
| 106 | Press the Events toggle twice | the role goes on and off; with the Events role NOT set up, there is no toggle at all and the panel says staff have not made it yet |
| 107 | As a linked streamer press **Start my own ping role**, then **Take my ping role away** → **Keep it**, then again → **Yes** | the role is made and appears on the **Streamer pings** panel; Keep it changes nothing; Yes removes it and the panel loses it |
| 108 | With `pings_mode` **off**: `/pings` as a member who follows somebody | the panel still opens, says ping roles are off, offers **no** Follow control — but **Stop following…** still works and takes the role off |
| 109 | `/pings` as a Lead | adds **Streamers…**, **Set up the Events role**, **Settings**, **Logs**, **Open on the site** — Logs answers a NEW message and the panel stays |
| 110 | **Set up the Events role** → leave the role picker empty → confirm; then again, picking an existing role | the first makes or reuses **Events** and points both feeds at it; the second reuses the one you picked; the reply says which, and says "still off" while the mode is off |
| 111 | **Streamers…** → **Give somebody a ping role…** → pick a member, leave the role picker empty → **Make the role**; then pick them on **A streamer…** → **Remove their ping role** → **Yes** | identical to `/pingroles streamer add` / `remove`: the role is made from the template, the Streamer pings panel refreshes, removal deletes the Discord role (`pings_fan_role_delete`) |
| 112 | Delete a streamer's role by hand in Server Settings, then open their card | the card says the role is gone and shows **Make the role again**; pressing it makes a fresh one and the panel picks it up |
| 113 | **Settings** → flip **Mode…**, flip **Who may start one…** to *staff*, open **Names…** and type `{game} pings` | the lines update; the template box shows what it will actually produce and refuses to pretend a broken one worked; with *staff* set, a member's **Start my own ping role** is gone and the panel says why |
| 114 | Leave the panel alone for `pings_panel_minutes` minutes | every button greys out and the footer says it went quiet |

## I. The genuine forks — the owner decides, one at a time

Settled first, by the standing rules, so they are NOT put to him:

- ✅ **The command is `/pings`.** It is the member word, it is already the member-visible half, and
  `/pingroles` is the staff group that goes — the same shape as the owner's applications answer
  (`/apply`, "it's gamer lingo"). The feature, the log kinds, the settings keys and the site section
  keep the name "pings" either way.
- ✅ **A gone-from-the-server role gets a staff repair** (`Make the role again`) — *"never design a
  terminal state staff cannot leave"* (`CLAUDE.md`, owner 2026-09-03).
- ✅ **Unfollowing is not mode-gated** (§C) — an access-REDUCING move fails safe, and a feature switch
  that traps a member in a ping is the wrong default.
- ✅ **The Settings sub-panel is built** despite `golive.html` owning the namespace — the applications
  build's deviation 4 settled it.
- ✅ **The Streamer pings / Notifications role-menu posts are untouched** — P14 and program §7.

Genuinely his, two:

- **I1 — may a streamer take away a ping role that STAFF started, when `pings_fan_role_creation` is
  `staff`?** Today yes: `/pings fans off` `:318` asks only whether a row exists, while `/pings fans on`
  `:307` refuses when the setting says `staff`. So the setting governs who may START one and nothing
  governs who may END one. The owner's standing answer for polls, birthdays and applications was *keep
  today's permission* ("if you can post it you can withdraw it") — but that premise fails here, because
  under `staff` the member did not make it. **Options:** (a) keep today's behaviour — `Take my ping role
  away` always renders; (b) hide it when the setting is `staff`, so only staff undo what only staff may
  do, and the panel says "an Auntie/Uncle started this one — ask them to take it off"; (c) a new
  `pings_fan_role_removal` key with the same three values, defaulting to match `creation`.
  **Recommended: (a)** — it is today's behaviour, it is the access-REDUCING direction, and a member
  who wants out of a role they wear should not need a ticket. Staff keep the card's own Remove either
  way. (c) is the only one that costs a second settings key.
- **I2 — when `golive_ping_role_id` and `events_ping_role_id` point at DIFFERENT roles, does the panel
  show one Events toggle or two?** D3 (`phase15-design.md:41`) kept them as two keys precisely so the
  feeds could be split later from the Go-live and Events pages; `events_role_id` `pings.py:468` reads
  `golive_ping_role_id or events_ping_role_id`, so after a split the one toggle silently moves the
  go-live role only and leaves the event role un-worn. **Options:** (a) one toggle, today's behaviour,
  and the split stays invisible; (b) one toggle while the two keys agree, two labelled toggles
  (`Go-live pings`, `Event pings`) when they differ; (c) always two. **Recommended: (b)** — it costs
  one branch in `panel_buttons`, nothing changes for anybody who has not split the feeds, and it is
  the only option where the button does what its label says. (c) makes the common case worse.

## J. What this build does NOT do

- **Does not touch the persistent posts** — `sync_streamer_menus` `:314`, `ensure_notifications_menu`
  `:472`, `menu_name` / `menu_title` / `pages_of`, or any `rolemenu_panels` path (P14, program §7).
- **Does not move `get_link` / `latest_session` out of `cogs/content/golive.py`** — the cycle is real
  (§F) and that file belongs to the sibling golive/twitch build this wave.
- **Does not add, move or rename an API route** (`api/tools/pings.py` and its 16 tests are untouched;
  no new web door, so nothing new needs `via=VIA_WEBSITE`) and **does not rename or re-home anything
  already in `black_bloc/pings.py`** — the site imports it by name.
- **Does not add a second settings key** (no own-list twin — §D), a `KEY_MIN`/`KEY_MAX` for the
  panel-minutes key, or a `HIDDEN_WHEN_OFF` entry.
- **Does not edit `black_bloc/panels.py`** unless it is demonstrably free of sibling wave-2 edits at
  build time — three branches editing the library at once is the merge conflict program §5 exists to
  avoid. `option_label` stays two separate functions.
- **Does not widen `guard.py`** to gate role add/remove (deliberate, `phase15-design.md` §Guard rails)
  and **does not touch the announcement path** (`golive.py:render`, `announced_fan_role` `:208`,
  `cogs/content/golive.py:416`) or `on_streamer_left` / `maybe_auto_create`.
- **Does not restore the `Logs` count / important_only options**, does not delete `pages_under_limit`
  (other callers), and **does not run against Discord** — nobody here can.

**Cost estimate: ~300–360k Opus tokens**, the low end of wave 1 (376k–458k). Cheaper than
applications because there is **no layer move** (the pure module already exists and the site already
imports it from there), **no schema change**, **no new route**, **no state machine** and **one modal**;
more than the floor because there are three sub-panels, a two-use role-pick step and thirteen strings
to rewrite. Commit at clean boundaries: (1) the extractions in `black_bloc/pings.py` with the existing
tests still green, (2) the cog rewritten onto the panel, (3) tests, (4) strings + docs.

## Deviations

_(Left empty for the build agent — write what you built differently and why, as the wave-1 builds did.)_
