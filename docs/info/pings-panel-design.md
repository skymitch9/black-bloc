# Ping roles — `/pings` is ONE command that opens a panel (wave 2)

> **Audience:** the build agent and the reviewer (Claude sessions), and the owner for §I.
> **Status:** TRACKED · ✅ **LIVE since v72** (`a5ad521`, 2026-09-03 18:30; merged clean after Fable
> review, one merge-time fix: the Names… echo only follows a successful save; boot measured `commands
> synced` **39** — **29** today; 4050 tests; nothing run against Discord by eye — sweeps 126–134 and
> 38–42 are the owner's). Still live at **v108** (`73e2e44`, 2026-09-11 00:37).
> Written as BUILT 2026-09-03 on `worktree-agent-a86e71fd801362ca2` — see the
> `## Deviations` foot for what was built differently and what was measured.
>
> ✅ **The design body below was RESTORED 2026-09-11 10:40** (owner: *"Restore it"*). Commit `8426b1a`
> (2026-09-03, *"Pings: rewrite every string and doc that named a retired subcommand"*) had cut the
> file from 408 lines to 140 because §A and §E listed the twelve retired `/pingroles` subcommands —
> and took §B–§J, the spec of the panel that shipped, with them. §B, §C, §D, §F, §I and §J are back
> verbatim from `8426b1a^`; §A (the pre-build measurement), §E (every line that named a retired
> subcommand), §G (the test plan) and §H (the prove-before-merge list) are historical and live in
> [`../archive/pings-panel-design-prebuild-2026-09-03.md`](../archive/pings-panel-design-prebuild-2026-09-03.md).
> Verified at the restore: every control the §B/§C tables name exists by that string in
> `black_bloc/cogs/content/pings.py` / `black_bloc/pings.py` today (21 labels, `Turn event pings on` …
> `Open on the site`) and `pings_panel_minutes` is registered; the per-state rendering rules were NOT
> exercised in a client. ⚠️ Where a `## Deviations` item at the foot disagrees with the body, the
> deviation is what shipped. `/pingroles …` in the body names the commands this panel replaced (gone at v72).
>
> **Since then, three things this document predates:**
> 1. **v78** (`3429233`) gave `pings_mode` a `HIDDEN_WHEN_OFF` entry (`command_visibility.py:25`),
>    one of fourteen, so `/pings` vanishes while the mode is off behind `hide_commands_when_off`.
> 2. **v84** (`ce97de0`) corrected `LOG_LEVEL_COMMANDS` — the stale `"pings": "pingroles"` row
>    deviation 14 and `automod-panel-design.md` deviation 9 both reported now reads `"pings": "pings"`.
> 3. ✅ **Deviation 6's deliberately-unfolded youtube copy WAS folded, at v92** (`4b327cf`,
>    *"youtube site link shared"*): `cogs/content/youtube.py:273` is now a two-line delegate over
>    `panels.site_page_url` imported as `library_site_page_url` (`:29`), keeping the `""` return.
>    Deviation 8's hand-rolled confirm folded too, at **v88** — `cogs/content/pings.py:417
>    open_confirm` wraps `panels.confirm` + `confirm_items` (`:19–20`).
> Also: **v86** (`ad5b614`) fixed *"Take my ping role away renders with the mode off"*.
>
> **Last verified: 2026-09-11 10:40** — the body restored and its 21 control labels re-checked against `7406842` (above); **09:28** — re-measured in this tree at `1d090e5`: `pings_panel_minutes`
> registered beside seven other `pings_*` keys (registry **202**); every move label still reads the
> same string — `OWN_ADD_MOVE` "Start my own ping role" / `OWN_DROP_MOVE` "Take my ping role away"
> (`pings.py:675–678`), `STREAMERS_MOVE` "Streamers…" (`:685`), `SETUP_MOVE` "Set up the Events role"
> (`:686`), `SETTINGS_MOVE` "Settings" (`:687`), `LOGS_MOVE` (`:688`), `CARD_REMOVE_MOVE` "Remove
> their ping role" (`:690`), `CARD_REMAKE_MOVE` "Make the role again" (`:693`), and `NAMES_BUTTON`
> "Names…" (`cogs/content/pings.py:85`, `NAMES_MOVE` `:119`). `site/mock/contract.json` holds
> **150 routes / 17 pages** (142 at the build); sweeps run to row **350**.
> ⚠️ **NOT checked in this pass:** anything in a Discord client or a browser; no boot, no pytest, no
> ruff, no `check.mjs` run. The empty-`RoleSelect` submit (deviation 5) is **still unproven** — sweep
> row 132 is still the only thing that would settle it.
>
> **Before that, 2026-09-03** — every `path:line` below was READ in this working tree on `main`
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
> whose `## Deviations

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

Written by the build agent, 2026-09-03, on `worktree-agent-a86e71fd801362ca2`.
Everything not listed here was built as this document says.

**Measured:** **4050 tests pass** (3872 on `main` before this branch, +178, none lost),
ruff clean over the whole tree, `node site/mock/check.mjs` **ok — 17 pages, 142 routes**
(unchanged, this build adds no route), `labels.js` parses, and the §H.3 import line —
including `cogs.content.golive` and `cogs.content.youtube` on purpose — succeeds.
`len(top)` measured through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`: **40 before, 39
after**, exactly one, and the test now pins 39.
⚠️ **NOT verified: anything against Discord.** Nothing was booted, no panel was opened, no
role was moved. The empty-`RoleSelect` submit is still unproven (deviation 5).

1. **The button table is a composing function over a `PanelState` NamedTuple, not a
   `PANEL_BUTTONS` dict keyed by the state tuple.** §F asks for `PANEL_BUTTONS` keyed by
   the boolean tuple; a dict cannot express this state, because I2 makes the events half a
   *variable-length list* — one entry while the feeds agree, two once they split — and
   `followed`/`unfollowed` are counts, not booleans. `panel_buttons(state, *, staff)`
   composes from `PANEL_MOVES` exactly the way the landed `youtube.card_buttons` does, and
   the parametrised test (2 modes × 2 own-role × 2 creation × 2 streams × 4 events-states ×
   2 staff = **128 cases**) asserts the rendered labels equal what the function returns, so
   the table is still proved as data.

2. **`notification_lines` takes the FEEDS, not one `events_role_id`.** §F's signature is
   `notification_lines(guild, member, rows, events_role_id)`. I2 (b) means the panel can
   have two Events rows with different wear-states, which one id cannot describe, so the
   fourth argument is the `((feed, role_id), …)` tuple `events_feeds` returns. Each line is
   parametrised on `{what}` (`Go-live and event pings` / `Go-live pings` / `Event pings`),
   so the single-feed case reads exactly as it does today.

3. **A fourth events wear-state — `gone` — got its own LINE, not just a missing toggle.**
   §C's table says a gone role renders no toggle; it did not say what the embed says. A
   panel that silently drops a control is P9's problem in reverse, so `LIST_EVENTS_GONE`
   names the id and says it is not a role in this server any more. `notification_lines`
   therefore has four branches, not three.

4. **`save_settings` and one new log kind `pings.settings` were added** — not named in §F.
   The Settings sub-panel (§C) writes six keys and had no shared function to call, and
   letting each select call `store.set` directly would have meant a settings sub-panel that
   is the only surface in the feature with no action-log row. It validates every key with
   `coerce_value` BEFORE the first write (so a bad value refuses the whole dict rather than
   writing half), takes `via=` and builds its kind with `kind_via`, and `pings.settings`
   joins `logkinds.ROUTINE` beside `pings.setup`. One dict, one log row (checklist 34).

5. **Both empty-`RoleSelect` paths are built, as §C's fallback asks.** An empty submit
   clears the pick and re-renders the step saying *"Nothing picked, so a fresh role is
   made"*; the confirm button (`Set it up` / `Make the role`) does the identical write with
   `existing_role=None` whether or not anything was picked. ⚠️ Which of the two a real
   client uses is **still unverified** — sweeps row 132 says so out loud.

6. **`panels.site_page_url(origin, feature)` was added and FIVE copies now delegate to it**
   (§F/checklist 15). The brief allowed the consolidation because `panels.py` was free of
   sibling edits. §F says the copies are four; measured, there were **six** — the two
   wave-2 panels that landed while this design was being written added `golive.py:444` and
   `cogs/content/youtube.py:270`. `requests.py`, `events.py`, `applications.py`,
   `cogs/community/polls.py` and `golive.py` each keep a one-line delegate with their own
   feature key, so **every existing import and every existing test is unchanged** — which
   is the proof the consolidation changed nothing. ⚠️ **`cogs/content/youtube.py`'s copy
   was deliberately left**: it returns `""` rather than `None` and names its page with a
   private `SITE_PAGE` constant rather than `FEATURE_PAGES`, so folding it would be a
   behaviour change in a file that landed hours ago. Reported, not fixed.
   ✅ **Folded at v92** (`4b327cf`): `cogs/content/youtube.py:273` is a two-line delegate over
   `panels.site_page_url` (imported as `library_site_page_url` `:29`) that keeps the `""` return,
   so the behaviour is unchanged and the seventh copy is gone.

7. **The `Names…` modal carries three fields, and the panel-minutes one is validated in
   the modal.** §C lists exactly those three. A modal has no `Range`, so a non-numeric
   minutes box is refused in words (`NOT_A_NUMBER`) and **nothing at all is saved** — the
   events-role name and the template do not sneak through on a bad third field. This is
   the youtube `NumbersModal` shape.

8. **The confirm step for `Take my ping role away` re-renders the ROOT embed with an
   "Are you sure?" field**, the way youtube's `open_confirm` does, rather than a card of
   its own; the staff card's `Remove their ping role` does the same over the card embed.
   §C only said "→ `Yes, take it away` / `Keep it`".

9. **`Refresh` and `Back` are ONE button each, dispatched on a `where` attribute the view
   carries.** §C lists `Refresh` on the root and on the Streamers sub-panel and `Back` on
   three different sub-panels; four spellings of one move is the anti-pattern P3 exists to
   kill, so `refresh_where` / `back_from` read `view.where` (`root` / `streamers` / `card`
   / `settings` / `role`) and go to the right place.

10. **`still_staff` runs on the staff READS too** — `Streamers…` and `Settings`, not only
    the writes. P8 says "before every staff move"; a demoted staffer being able to open the
    roster is the same defect one step earlier, and it costs one line each.

11. **Three assertions in `tests/cogs/content/test_pings.py` were rewritten in the
    extractions commit rather than the cog commit**, because the string rewrites (§E) land
    with the functions that own them and those three tests asserted the old wording
    (`/pingroles setup`, `/pingroles streamer add`). Every other test in that file was
    replaced wholesale when the cog was; `tests/api/tools/test_pings.py` is **untouched**,
    which is the proof no route moved.

12. **Two test doubles were repaired, not worked around.** `tests/cogs/content/test_pings.py`'s
    `FakeGuild.create_role` numbered roles `1000 + len(self.roles)`, so deleting a role and
    making another handed out the SAME id — which is exactly the *role deleted by hand, then
    repaired* case the `Make the role again` test exercises. It now uses a monotonic counter.
    `tests/test_pings.py`'s `FakeMember.add_roles` never appends to `role.members`, so a
    follower-count test has to append directly; left alone rather than changed, because
    thirty existing tests read that double.

13. **`docs/access/sweeps.md` rows are 126–134, not 104–114.** §H was written when the last
    written row was 102; `sweeps.md` ends at **125** (118–125 are the youtube panel's), so
    these start at 126 and the nine rows of §H's table became nine rows numbered 126–134.
    Rows **38–42** were rewritten in place as §E says. `docs/access/OWNER_GUIDE.md`'s count
    moved **125 → 134** in its header and its "Test something" row; measured, it still names
    no `/pings` subcommand anywhere (zero matches for "ping", as §E said).

14. **`black_bloc/pings.py:NOT_A_STREAMER` already said `/golive` → **Link my Twitch
    channel** on `main`** — the golive panel landed and rewrote it. §E's instruction to
    "say `/twitch link` and let the conductor reconcile" is therefore moot; only its
    `/pingroles streamer add` half needed rewriting, to `/pings` ▸ **Streamers…**.
    ✅ **The related stale row, `LOG_LEVEL_COMMANDS["pings"] = "pingroles"`, was fixed at v84**
    (`ce97de0`) along with the other sixteen features; it reads `"pings": "pings"` today.

15. **Checklist 15 caught one more duplicate during the sweep: the cog's own
    `LABEL_LIMIT = 100`.** `panels.SELECT_OPTION_LIMIT` is the same 100 and already has a
    home, so the constant was deleted and every select-option clamp reads the library's.
    `pings.ROLE_NAME_LIMIT` is left as a separate 100 on purpose — that one is Discord's
    role-NAME ceiling, a different fact that happens to share a number.

16. **Checklist 29, checked against the installed source rather than guessed:**
    `discord/ui/select.py`'s `RoleSelect` documents `min_values` as *"must be between 0 and
    25"* and does **not** validate it at construction, so `min_values=0` is accepted by the
    library. That settles the LIBRARY half of the empty-picker question; the CLIENT half —
    whether Discord's own UI will submit an empty selection — is still unproven and is why
    deviation 5's second path exists.

17. **The panel block was appended to the FOOT of `black_bloc/pings.py`**, after the
    existing shared layer, matching `black_bloc/youtube.py`'s shape rather than sitting
    between the string constants and `Outcome`. Nothing already in that file was renamed or
    re-homed (§J) — `api/tools/pings.py` imports it by name and its sixteen tests are
    unchanged.
