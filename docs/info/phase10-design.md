# Phase 10 — Polls (F15): native Discord polls, wrapped

> ⚠️ **SUPERSEDED IN PART, 2026-09-03: every `/poll …` subcommand this document names is
> gone.** `/poll` is now ONE command that opens an interactive panel — see
> [`polls-panel-design.md`](polls-panel-design.md) (wave 1 of
> [`panels-program.md`](panels-program.md)). Nothing else here changed: the surfaces, the
> kinds, the review flow, the loop, the settings keys and the dashboard page are all as
> written. Read the subcommand names below as the history of how a move used to be
> reached, not as something you can type today.

> 🟢 **10b IS BUILT (2026-08-27)** — branch `worktree-agent-a9f9dbcabf9636130`
> off `main` @ `3eb7e4f` (10a's own tip), **five commits**: `16c1db4` the date
> kind · `8906032` the panel surface · `a7d8216` recurring polls · `85d05da`
> `POST /api/polls` + the dashboard tab · `e4b5dca` the shared pager fix.
> `pytest -q` **1819 passed** (1738 before), `ruff` clean, `check.mjs` **15
> pages / 72 routes** clean, and a browser pass on the mock found **no console
> errors on any of the fifteen pages** and **zero horizontal overflow at 1280
> and 390 px in Discord dark and Cyberpunk**. Per-file notes:
> [`code-notes.md`](code-notes.md) § *polls (10b)*; routes:
> [`phase8b-design.md`](phase8b-design.md) § *Phase 10b*.
>
> ⚠️ **The `<t:…>` question is HALF settled and the other half is one look
> away.** One real poll was posted into the test channel by REST (message
> **`1542651824950218792`**) and read back: the API stores `<t:1788400000:d>`
> **verbatim**, escaping and altering nothing. Whether the *client* renders it
> as a date is a pixel question nobody has looked at. Date labels therefore
> default to the plain "Sat 30 Aug · 7 pm" form in the server's zone, and
> `poll_date_labels` flips them to timestamps once the owner has looked.
>
> **What 10b built:** the panel surface (anonymous · results-at-close · more
> than ten options · date polls past ten slots), the date/availability kind,
> recurring polls (`/poll recur create|list|pause|delete`, daily / weekly /
> monthly), `POST /api/polls` with three recurrence routes, and the fifteenth
> dashboard page. **F15 is feature-complete except the v2 kinds** (free text,
> number, ranked), which `surface_for` still refuses by name.
>
> ⚠️ **Still not merged, not deployed, and nobody has ever voted** — on either
> surface. No panel button has been pressed, no vote modal has been opened, and
> no recurrence has fired. The owner's sweep at the bottom of this file is the
> thing that would prove it.

> 🟢 **10a WAS BUILT (2026-08-27)** — branch `worktree-agent-aa83500e6aae1280f`
> off `main` @ `6e08223`, four commits: `033e1c7` storage (schema 13 → 14, the
> four tables) · `a0fe975` the pure module + ten settings keys · `d3d1234` the
> cog, the loop and the raw vote listeners · `09d8654` the API, the contract
> and the mock. `pytest -q` **1738 passed** (1596 before), `ruff` clean,
> `check.mjs` 14 pages / 68 routes clean. ⚠️ **Not merged, not deployed, and
> nothing has run against Discord — this code has never posted a poll.** The
> per-file notes are in [`code-notes.md`](code-notes.md) § *polls (10a)*; the
> routes are in [`phase8b-design.md`](phase8b-design.md) § *Phase 10a*.
>
> **10b then took all of it** — the panel surface, recurrence, the dashboard
> tab, `POST /api/polls` and the `<t:…>` measurement. See the banner above.

> **Audience:** the Phase 10 build agents and the reviewer. **Status:** TRACKED (2026-08-31; private repo).
> Last verified: **2026-08-27** — the 15 owner decisions were taken one at a time (`TODO.md`, the
> polls decisions entry); every technical claim below is inherited from
> [`polls-research.md`](polls-research.md) §4 (measured against discord.py 2.7.1) and §6 (the
> recommended design). NOT verified: nothing has run; the `<t:…>` inside a poll answer label question
> (research §9) is still open and must be tested first.

**Priority: after Phase 9 and the polish/verification work — the owner: "it's not an urgent feature."**

## The asks (owner, verbatim, 2026-08-27)
- "can we also have a poll app, copy polly or any other popular polling app in discrd"
- "also in that poll let them set a data type for the box so if they pick date or checkbox etc it changes how the poll functions"

Polly is a Slack/Teams product; the Discord equivalents are EasyPoll / Simple Poll. The design copies
their **feature set**, with Discord's native polls as the voting surface (research §1, §5).

## Decisions (all 15 settled)

| # | Decision | Owner's call |
|---|---|---|
| 1 | Answer types in v1 | single choice · checkbox (multi) · yes/no · rating scale · **date/availability**; free text, number, ranked = v2 |
| 2 | Who may create | **staff only** (`poll_who_can_create`, widen later) |
| 3 | Staff review before posting | **off by default, but a switch** `poll_review_mode` off/on, editable from `/poll settings` AND the dashboard |
| 4 | Default duration | **24 h**, per-poll override, ceiling 32 d (Discord's) |
| 5 | Anonymous votes | **creator chooses per poll**; anonymous forces the panel (native exposes voters) and the creator is told |
| 6 | Results visibility | **creator chooses per poll, default live**; hide-until-close forces the panel |
| 7 | Channel | **the channel the command was run in**; `poll_channel_id` = dashboard-create default; test channel under TEST_MODE |
| 8 | Ping on open | **none by default**; `poll_ping_role_id` + per-poll override |
| 9 | Reminder before close | **60 min**, in the poll's channel, no ping; `poll_reminder_minutes`, 0 = off |
| 10 | Recurring polls v1 | **yes**, staff-only, daily / weekly / monthly |
| 11 | Weighted votes | **no** |
| 12 | Reopen a closed poll | **no** |
| 13 | Auto-thread | **off by default**, `poll_auto_thread` |
| 14 | Retention + export | **archive after 365 d, never delete**: summary kept forever, per-vote rows may drop at archive; Archive section on the dashboard; CSV export |
| 15 | Priority | **after the current phase** |

## Design — deltas from research §6 (which is otherwise the spec)

- **Surface choice is derived, not chosen:** `surface = "native"` unless the poll needs something native
  cannot do — anonymous (D5), hide-until-close (D6), a date/availability type with > 10 slots, free
  text / number (v2) — then `surface = "panel"`. The creation flow says which surface it picked and why.
- **Review switch (D3):** `poll_review_mode` off → posts immediately; on → a review card in
  `staff_channel_id` with Approve / Deny `SafeDynamicItem` buttons (the events/role-request shape),
  creator DM'd either way.
- **Per-poll flags (D5, D6, D8):** `anonymous`, `results` (`live`/`close`), `ping_role_id` on the
  `polls` row, set at creation (modal / dashboard form), defaults from the settings keys.
- **Archive (D14):** `polls.status` gains `archived`; a daily job (in the same loop as the reminder)
  moves polls closed > `poll_archive_days` (default 365) to `archived`, deletes their `poll_votes`
  rows only if `poll_archive_drop_votes` (default true), keeps `poll_results` (per-option totals,
  voter count, closed_at). Dashboard: Archive = collapsed section, export still works.
- **Date/availability type (D1):** slots generated from a start date + count + step (research §3a);
  ≤ 10 slots → native multi-select poll with `<t:…:d>`-style labels **if that renders inside an answer
  label (TEST FIRST — research §9)**, else plain "Sat 30 Aug"; > 10 → panel with buttons (≤ 25).
- **Everything else** — status machine, four tables, commands, settings keys, loop, results embed,
  dashboard tab, action-log kinds — as research §6.2–6.9, with the settings keys above added.

## Test-mode rule (research §4.5, measured)
`guard.py` patches `send_message` / `edit_message` / `delete_channel` only. **`poll.end()`
(`http.end_poll`) and interaction-response sends are NOT gated** — the polls cog checks
`bot.guard.allows_channel(...)` by hand before creating, ending, reminding, or posting results, exactly
like `cogs/moderation/automod.py` does. A test asserts a poll cannot be created or ended outside the
test channel while TEST_MODE is on.

## Slices
- **10a** (~250–350k, one worktree): storage + status machine + `/poll create|end|results|settings` on
  native polls (single/checkbox/yes-no/rating), review switch, reminder + close loop, results embed,
  `poll_results` history, action log, API read routes, contract + mock entries, tests.
- **10b** (~200–300k, after 10a lands): the panel surface (anonymous, hide-until-close, date
  slots > 10), recurring polls, archive job, CSV export, the dashboard tab (list / create / close /
  results / archive), Members-style search.

## Definition of done
Every branch above tested (mirror layout); `pytest -q` green; `ruff` clean; `check.mjs` clean;
code-notes keyed `path:line`; nothing run against Discord — the owner's sweep: `/poll create` of each
v1 type in the test channel, vote, wait for the reminder, `/poll end`, read the results embed and the
dashboard row; one date poll with 12 slots to see the panel.
