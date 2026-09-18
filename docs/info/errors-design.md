# Errors — every command error on the site's Logs page, and a Try again that keeps the member's place

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus 2026-09-17 17:3x as
> branch `errors`** (v131 or v132, whichever lands first beside `minutes`). **Last verified: 2026-09-17 17:2x** against
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
