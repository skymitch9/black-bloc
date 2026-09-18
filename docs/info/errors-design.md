# Errors — every command error on the site's Logs page, and a Try again that keeps the member's place

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v131** — merge `64684d6`, release `709defe`, deployed **2026-09-17 18:12** Phoenix; the `## Deviations` foot is the truth where it departs from the body; sweeps **565–571** are the owner's. Was: ✅ BUILT on branch `errors` (off `main` `e7093d7`), not merged — §A–§D in `5177040` (code +
> tests) and the docs commit after it; see `## Deviations`. (v131 or v132, whichever lands first beside `minutes`). **Last verified: 2026-09-17 17:2x** against
> `main` `479fe29`: `black_bloc/command_errors.py` (`report` → `log.exception` + one sentence `COMMAND_FAILED`;
> `AnswersErrors.on_error`, `SafeDynamicItem`, `on_tree_error`), `black_bloc/panels.py` (`opened`, `Panel`, `retire`),
> `black_bloc/actionlog.py` (`log_action`), the Logs page (`site/public/assets/logs.js`, `/api/actions?feature=`),
> `logkinds.py` (`HEADS`, `IMPORTANT`), the zone-picker crash of 17:15 (fixed in v130). ⚠️ Secret NAMES only.

## Owner asks, verbatim (2026-09-17 17:1x–17:2x)

*"there is an error on event creation the bot just posted in discord. do we have a lot of that and why?"* →
*"I also want to know how that experiences effects the end users, it should prompt them to try again and not just
kick them out and make them start over. deep dive this"* → *"was that logged on the discord site? it should be if not
so other staff that aren't us can view the error logs and assist"* → *"timezone stuff seems to be a reoccuring issue
with multiple people when trying to use the events"*.

## What was measured (the 17:15 crash)

| Question | Answer |
|---|---|
| How many | ONE traceback in Fly's 100-line log window (`ZonePanel failed`, `InteractionResponded`); no way to count further back — the action log has no row for command errors at all |
| Why | `panels.opened` deferred unconditionally; the event draft's zone picker stored the zone, then handed the same interaction to `open_draft`, which opened it again → the second `defer()` raised. It fired for **every member whose first Propose had to ask for a time zone** — which is every new member. Fixed in v130 (`opened` defers only when not already answered) |
| What the member saw | one ephemeral sentence: *"Black Bloc hit an error running that command; it has been logged. Try again, and tell a Lead if it keeps happening."* Their draft card stayed on screen but STALE (the render that failed never happened), with nothing to press that said "continue". Their zone WAS stored, so a second Propose would have worked — nobody could know that. Most re-ran `/event` and started over |
| Was it on the site | **No.** `command_errors.report` writes `log.exception` only. The Logs page reads the action log; nothing there |

## A. Every error is an action-log row

`command_errors.report` / `on_tree_error` / `SafeDynamicItem.callback` / `AnswersErrors.on_error` all end in ONE
new function `record(bot, interaction, error, where)` that writes `log_action(bot, guild, "error.<surface>",
actor=the member, details={"where": where (the view / modal / command name), "error": type name, "message":
str(error)[:200], "step": the innermost repo frame `file:line` from the traceback, "interaction": command name or
custom id})`, kind family `error.*` — `error.command`, `error.panel`, `error.modal`, `error.button` — all
**IMPORTANT** (`logkinds.IMPORTANT`), head `HEADS["error"] = "core"` so they show on the Logs page under
**Core** and in the site's important filter. ⚠️ **No member words**: never the modal's field values, never
message content — the exception message is truncated and, for `discord.HTTPException`, reduced to its code + text.
When the action log itself cannot be written (database down) the Python log still gets the traceback (today's
behaviour is the floor, never removed). A second failure inside `record` is swallowed with one `log.warning`.

The Logs page gains **Errors** as a feature filter (the head is core, but the page's filter list adds an
`error.*` kind-prefix filter so staff can open "just the errors") — read `logs.js` for how filters are built and add
one entry, not a second mechanism. `docs/info/logkinds` (or wherever the kinds are catalogued) gains the family.

## B. Try again — the member keeps their place

`COMMAND_FAILED` becomes a sentence PLUS one button when the surface can re-render itself:

- `AnswersErrors.on_error` looks for `self.render_again(interaction)` (a coroutine the panel/modal defines) or,
  for a modal, `self.previous.render_again`. When found, the error answer carries **Try again** (an ephemeral
  message with one button; pressing it calls `render_again` on the ORIGINAL message the member was on — the draft
  card, the panel — with the same fields object, so nothing typed is lost) and the sentence reads
  *"Black Bloc hit an error at that step; it has been logged for staff. Press **Try again** to pick up where you
  were — your answers are kept."* When no `render_again` exists the sentence is today's, unchanged.
- `Panel` gains a default `render_again` that re-renders its own root (every panel already has a root builder —
  find the one shape they share, likely `render_root` / `build_panel`, and use it; a panel that cannot is left with
  the plain sentence and named in Deviations). The event DRAFT's view gets `render_again` = `render_draft(...)` with
  its `EventDraft` fields — the case that started this — and so do the zone modal's `previous` and the request /
  ticket modals' `previous` where a fields object exists.
- The Try-again button is a plain `discord.ui.Button` on a short-lived view (`error_retry_minutes`, int 1–30,
  default **10**, under `core`); a press after it expires says so in words and offers the command name to run.
- Keys: `error_sentence` (text, the sentence above, `{where}`-free — every word the bot posts is a key),
  `error_retry_label` (text, `Try again`), `error_retry_minutes`. Under `core` (the group select is at its 25-cap).

## C. Tests (mirror the package)

`tests/test_command_errors.py`: `record` writes the row with the right kind, the truncated message, the step, and
never the modal's values; a database-down write leaves the Python log line; the retry button re-renders the same
fields; an expired retry says so; `tests/cogs/community/test_events.py`: the zone-picker path end to end with a
render that raises once → the member gets Try again, presses it, and the draft comes back with the title they
typed; `tests/test_logkinds.py`: the family is IMPORTANT and headed core; a site test that the Logs page's Errors
filter exists (`site/mock` check or the contract). Both orders.

## D. Docs

`code-notes.md`; this doc's `## Deviations`; `docs/info/review-checklist.md` gains item **36**: *"every surface a
member can be on has `render_again`, so an error offers Try again"* (traced to the 17:15 crash); the guides: a fact
line in the events guide's faults (*"Black Bloc hit an error — press Try again"*); `sweeps.md` rows `ER-a…`;
`architecture.md` the new kind family. NOT `TODO.md` / `DONE.md` / `deploys.log`.

## Deviations

*(the build agent writes here what it had to do differently, dated)*

**2026-09-17, branch `errors` off `main` `e7093d7`.** Built §A–§D. Seven departures:

1. **`record` takes a fifth argument.** §A writes `record(bot, interaction, error, where)`, but the
   kind is `error.<surface>` and `where` is only the class/command NAME — nothing in those four
   arguments says which of the four kinds to write. It is
   `record(bot, interaction, error, where, *, surface=ERROR_COMMAND)`, and `report` grew the same
   keyword plus `again=`. `surface_of()` decides it by `isinstance` (Modal → `error.modal`,
   View → `error.panel`, Item → `error.button`, anything else → `error.command`).
2. **A FOURTH key, `error_retry_expired`.** §B lists three. The design also says a press after the
   window "says so in words and offers the command name to run" — words the bot posts, and the
   standing rule is that every one of those is a key. `{command}` is filled by `.replace()` (never
   `.format()`, so an owner-edited sentence with a stray brace cannot raise) with `/name` when the
   interaction knows its command and with **that command** when it does not. ⚠️ A component
   interaction never knows: `interaction.command` is None for every button and select, so a panel
   failure's expired sentence says "that command", not "/event". Carrying the command name down
   onto every panel would have touched every cog; it was not worth it.
3. **`Panel` does NOT get a default `render_again`.** §B says it should re-render "its own root",
   and there is no one shape to find: `cogs/core.py` sets `view.rerender` as an `(interaction,
   view)` move, `EventDraftPanel.rerender` and `raidtrain`'s take `(interaction)` alone, and
   modmail dispatches on `view.surface`. One name with two arities is a quiet break, so `Panel`
   takes an `again` move (`(interaction, previous)` — the shape every `render_*` / `open_*`
   already has) and exposes `render_again` as a property that answers **None** when no builder set
   one. A panel with no `again` keeps today's plain sentence, by design.
4. **Which surfaces got one** — the event draft (`EventDraftPanel.reopen`, same `fields` object),
   the zone panel (`again=back`, see 5), the requests panel and the request card, every
   `/modmail` surface (through the new `render_surface`, lifted out of `MoveButton.go_back`) and
   every `/settings` card. ⚠️ **Left with the plain sentence, deliberately:** every other cog's
   panels — automod, honeypot, polls, role menus, temp voice, birthdays, applications, raid
   trains, go-live, YouTube, pings, chat, guides, posts, the Where panel and the Logs panel. Each
   is one line (`again=` at its builder) and none was touched, because a `render_again` that has
   not been exercised is a button that might fail a second time in front of a member. The
   checklist's item 36 is what makes the next build add its own.
5. **The zone panel's Try again goes where BACK goes, not back to the zone panel.** §B says the
   zone modal's `previous` gets a `render_again`; it does, but the move is `back` — the draft it
   was raised from. By the time this fires the zone is already stored (that is exactly the 17:15
   crash), so redrawing the picker would ask the member to choose twice. §C's own end-to-end test
   requires it this way: *"presses it, and the draft comes back with the title they typed"*.
6. **§A and §B landed in ONE commit** (`5177040`), not two. They share `command_errors.py`:
   `report` cannot write the row without `record` and cannot offer Try again without `offer`, and
   a commit holding half of it is a commit whose tests do not pass. The docs are the second
   commit. Everything else in the order the brief set was followed.
7. **The Logs page's Errors filter narrows by KIND, and the chip bar learned one new trick.**
   `error.*` is headed `core`, so a feature chip could never isolate it. One entry was added to
   `LOG_FEATURES` carrying `kind` instead of `feature`; `page-audit.js`'s chip builder now reads
   the entry rather than a bare value, sets `state.kind` for it, and writes the prefix into the
   Kind box so the two filters never disagree. The per-feature Logs block (`logsSection`) is
   untouched — it is scoped to one feature and has nothing to narrow.

**Verified:** `ruff check .` clean; `pytest -n 8` **6479 passed** forward and **6479 passed** under
`BB_REVERSE=1` (6456 before), with the bot-shaped env cleared; every `site/public/assets/*.js`
parses as an ES module; `node site/mock/check.mjs` *ok — 19 pages, 180 routes, 21 core settings,
all keys present*; `discordmd.test.mjs` and `labels.test.mjs` both ok. No pytest stall (KI-26)
in any run. ⚠️ **NOT verified:** nothing met live Discord — no button was pressed, the bot was
never booted, and no browser rendered the Logs page. `ruff format --check` was not run (known red
repo-wide, not a gate). The Try-again *deletion* of the error message and the view's own timeout
edit are exercised only against fakes.
