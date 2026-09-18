# Posted strings — EVENTS: every word the bot posts becomes a key (pass 1 of the standing rule)

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ⏸️ **DESIGN, HELD (owner, 2026-09-18 09:2x: "for the audit make a list but don't execute fixes yet")** — the build dispatched 09:22 as `events-strings` was stopped at 09:30 with nothing committed and its worktree discarded; the LIST comes first: [`posted-strings-audit.md`](posted-strings-audit.md), every posted string across every feature, for the owner to read before any key is added. This design is what pass 1 becomes when he says go. **Last verified: 2026-09-18 09:2x** against `main` `7e6c493` (v138): `black_bloc/events.py`
> carries **108** string constants and **86** tuple constants at module level; the pattern to copy is the front door
> (`frontdoor_title` / `frontdoor_text` / the three labels / `rehearsal_note` — registry `KEY_TYPES` / `KEY_HELP` /
> defaults + `TEXT_MAY_BE_BLANK` where a blank is allowed, a `site/mock/server.mjs` row, a `labels.js` label, read from
> the store at RENDER time, a `.replace()` fill for placeholders — never `.format()` on owner-edited text). The events
> keys already live under `events` (a Find… box exists); `events_moved_line` (v137) and `events_where_hint` (v138) are
> the two newest examples of the shape. ⚠️ Secret NAMES only.

## The rule, verbatim (owner, 2026-09-17)

*"lets make sure all the stuff in the need something ticket block is editable on the site, make that a standing black
bloc rule."* — written into `CLAUDE.md`: *every word the bot posts is editable on the site: a heading, a line, a button
label, a note, a template — each is a settings key the Settings page and the feature's own page can change, never a
string only the code knows.* Events is the biggest block still owned by the code (deviation 10 of the forum build and
§H-10 of the move build both named it). Owner 2026-09-18: *"start doing the builds you suggest"* — this is build 1.

## A. What counts as "posted", and what this pass keys

**Keyed in this pass** — anything the bot writes INTO A CHANNEL, A POST, A DM, or onto a CARD a member sees:

- the announcement (`events_announce_template`-style: the approved-event announcement, the go-live ping line, the
  "has ended" line, the cancelled announcement `CANCELLED_ANNOUNCEMENT`), the room / post opening line, the room notice
  (*"This post is Black Bloc's — …"*, both the room and the post wordings), `events_moved_line` (exists);
- every DM: `DM_APPROVED`, `DM_DENIED`, `DM_CANCELLED`, the reminder DMs, the moved / removed reasons;
- the review card's headings and field labels, the draft card's headings (*Where*, *When*, *How long* …), the Where
  panel title (`WHERE_PANEL_TITLE`) and its intro lines (`WHERE_PANEL_INTRO`, `WHERE_JOIN_NOTE`), the placeholders on the
  pickers (`WHERE_PLACEHOLDER`), the button labels the bot draws (Approve / Deny / Cancel / Delete this room / Delete this
  post / Move to the forum / Not an event — make it a request / Submit / Back / Where / Time zone / Title & details);
- the post title template (`{title} · {date}`), the room name template if one exists.

**NOT keyed in this pass, named as pass 2** — the ephemeral refusal and confirmation sentences (`*_SAID`, `POST_REFUSED_*`,
the gate's "only staff…" answers), the log summaries, exceptions. They are answers to the presser, not posts. Pass 2 is
its own design once the owner has seen pass 1 on the Settings page.

**Naming:** `events_<what>` (`events_dm_approved`, `events_card_where_label`, `events_button_approve`, …) — read
`settings_store.py`'s existing `events_*` names and do not collide; the help text says where the words show and which
placeholders are allowed (`{title}`, `{host}`, `{when}`, `{where}`, `{url}`, `{post}`, `{duration}` — list only the ones that
key actually fills). Placeholders are filled by `.replace()`; a validator refuses an unknown `{…}` at set time (the
`events_moved_line` validator is the pattern). Button labels clamp to Discord's 80. Blank: allowed only where a blank
makes sense (a note, a hint) — `TEXT_MAY_BE_BLANK`; a heading or a button label refuses blank in words.

**The site:** every key renders on the Settings page under **events** automatically; the events page's settings block
gains a **Wording** group (the way the Go-live page has its Wording card) listing these keys with a live preview of the
announcement through the existing `discordmd` renderer if a preview route exists for events (`/api/golive/preview` is the
pattern — add `/api/events/preview` only if it falls out cleanly; otherwise say so).

## B. The two events leftovers bundled here

1. **`event.room_forgotten` is logged TWICE per row at boot** (measured 2026-09-11, v110): `on_ready`'s reconcile and
   `_reconcile_loop`'s first tick both read the swept rows before either wrote the cleared id. One reconcile at boot, or a
   `review_channel_id` re-read before the write — one row per event per boot; a test with a fake that runs both.
2. **The site's Events / Raid-train create forms take a typed `YYYY-MM-DD HH:MM`**: replace with an `<input
   type="datetime-local">` plus a zone `<select>` fed by `timezone_choices` (default `default_timezone`), the two combined
   into the same value the route already accepts (both forms live in `page-events.js` — the event form ~155/182 and the raid-train slot form ~333/390; the routes, the mock); the
   typed field stays as the fallback when the browser has no picker (say how it is detected).

## C. Tests, docs, gate

Mirror the package: `tests/test_events.py` (each key read at render, a placeholder filled, an unknown placeholder refused,
blank rules), `tests/cogs/community/test_events.py` (an edited key shows on the next render of the card / announcement /
DM; the single boot reconcile row), `tests/test_settings_store.py` (counts), `tests/api/test_contract.py` (the form change
+ any route), the mock check. Both `pytest -n 8` orders, `ruff`, the ES-module parse, `check.mjs`, `discordmd.test.mjs`,
`labels.test.mjs`, env cleared. Docs: this doc's `## Deviations` (dated) + `## What was NOT verified`; `code-notes.md`;
`architecture.md` (keys); `docs/info/README.md` row; `sweeps.md` rows `ES-a…` (a: edit `events_dm_approved` on the
Settings page, approve a test event → the DM reads the new words; b: edit the announcement key → the next announcement;
c: the events page's Wording group; d: one `event.room_forgotten` row per event at a boot; e: the date picker on the
events page's create form). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.

## Deviations

*(the build agent writes here what it had to do differently, dated)*
