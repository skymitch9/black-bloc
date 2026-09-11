# Saved poll drafts — design

> **Audience:** the build agent and reviewers. **Status:** TRACKED, ✅ **LIVE as v94** — branch
> `poll-drafts` (off `main` at `9cd79d6`, v93), merge **`8405bea`**, **schema 32 → 33**, deployed by
> the owner **2026-09-06 11:13** Phoenix; Fly **v95 is the same commit**, a second run of the script
> 72 s later with no code change (`../deploys.log`). Landing entry in [`../DONE.md`](../DONE.md).
> See the `## Deviations` foot for what differs and why. ⚠️ **Never met live Discord** — no test can
> click a Discord button ([`../access/testing.md`](../access/testing.md)); the owner's by-eye rows are
> **300–304** in [`../access/sweeps.md`](../access/sweeps.md) (lettered `PD-a`–`PD-e` here; numbered
> at the merge, as §7 said the conductor would).
> Owner decision **2026-09-06 09:45**, verbatim: *"B but only save 1 draft per person max"*
> — answering "polls' `draft` status: (a) drop it or (b) make saved drafts real". This closes fork I-3 of
> [`polls-panel-design.md`](polls-panel-design.md) §I the other way: a member CAN leave the create flow
> and come back to it.
>
> **Last verified: 2026-09-11 08:36** (the header; the body is as at the design). Measured this pass
> against `main` at `f3ae743` (v108 live): the `poll_drafts` table is in `storage/db.py` (the schema
> has moved on to **34** since, for events' `where_kind`/`where_channel_id` — nothing here changed);
> `black_bloc/polls.py` carries `PollDraft.to_json`/`from_json`, `draft_row`, `load_draft`,
> `save_draft`, `drop_draft`, `drafts`, `stale_drafts`; `DRAFT = "draft"` survives as a name but is in
> **none** of `STATUSES` / `OPEN_STATUSES` / `TRANSITIONS` / `COLOURS` / `CARD_BUTTONS`, exactly as
> §2.1 required; `settings_store.py` registers `poll_drafts` (bool) and `poll_draft_days` (int,
> default `POLL_DRAFT_DAYS = 14`) with help sentences and a max; the three log kinds
> `poll.draft_saved` / `poll.draft_discarded` / `poll.draft_expired` are in `logkinds.py` and written
> by `cogs/community/polls.py`. ⚠️ **NOT checked this pass:** anything in Discord or a browser — no
> button was pressed, no page was opened, the bot was not booted. Before that, **2026-09-06 10:05** —
> every `path:name` below was read in the tree at `62ace89` (v93 + the fixture sweeps), before the
> build.

## 1. What exists

- `black_bloc/polls.py:DRAFT` sits in `STATUSES`, `OPEN_STATUSES`, `TRANSITIONS`, `COLOURS` and the
  button table, but **nothing ever writes it** — `store_poll` writes `pending_review` or `open`.
- `cogs/community/polls.py:PollDraft` is the in-memory step-2 preview (`DRAFT_INTRO` = "Nothing is
  saved until you press **Post it**"); `CreateButton` builds one and opens `NewPollModal`.
- `polls` table (`storage/db.py`, schema **32**) has `status … DEFAULT 'draft'` — a default no row uses.

## 2. The decision, as rules

1. **A draft is not a poll.** It lives in its own table, never in `polls` — so `polls` keeps its
   one-write-one-log-row shape (checklist 34) and no orphan poll rows exist. Therefore `DRAFT` LEAVES
   `STATUSES` / `OPEN_STATUSES` / `TRANSITIONS` / `COLOURS` / the button table, the `polls.status`
   column default becomes `'pending_review'`-free (no default needed — every writer sets it; keep the
   column NOT NULL, drop the `'draft'` default via `_add_missing_columns`-style migration only if
   SQLite allows it cheaply; otherwise leave the default and note it), and the parametrised
   every-status test loses one member. The design doc's §B/§C tables get a one-line deviation note.
2. **One draft per person per guild, max — enforced by the schema**, not by a check:
   `PRIMARY KEY (guild_id, user_id)`. Saving again REPLACES; the button says so.
3. **Configurable both ways** (checklist 33), two keys in `settings_store.py`, registered beside the
   `poll_*` family with descriptions, labels in `site/public/assets/labels.js` (sweep 3's guard
   `NO_LABEL_YET` must stay empty), and the mock's core-settings count updated if it counts them:
   - `poll_drafts` — bool, default **True**. False = no `Save for later` button, no `Resume` button,
     the panel line goes away; existing rows are kept, not deleted (turning it back on restores them).
   - `poll_draft_days` — int, default **14**, 0 = never. A draft older than this is dropped by the
     existing polls archive loop (one loop, not a new one), one log row per drop.
4. **Staff have the final say**: staff can see every saved draft and discard one, with a DM'd reason.

## 3. Storage — schema 32 → 33

```sql
CREATE TABLE IF NOT EXISTS poll_drafts (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    payload    TEXT    NOT NULL,          -- json of PollDraft fields, exactly the dataclass
    saved_at   TEXT    NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);
```

Pure helpers in `black_bloc/polls.py` (P4 — no discord objects): `save_draft(db, guild_id, user_id,
draft) -> bool` (returns whether it replaced one), `load_draft(db, guild_id, user_id) -> PollDraft | None`,
`drop_draft(db, guild_id, user_id) -> bool`, `drafts(db, guild_id) -> list[Row]`,
`stale_drafts(db, guild_id, days, now)`. `PollDraft` gains `to_json()` / `from_json()`; unknown keys in
stored json are ignored (a later field addition must not break an old draft), missing keys take the
dataclass default. `PollDraft` moves to `black_bloc/polls.py` if that is what makes the helpers pure;
the cog re-exports it.

## 4. The panel — every move is a button that renders only when valid

**Member, main panel (`build_panel`):** when `poll_drafts` is on and `load_draft` returns a row for the
actor, the embed gains one line — *"You have a saved draft: «{question}» — saved {age}"* — and row 0
gains **`Resume draft`** (primary) beside `Create`. `Create` still starts fresh; pressing `Post it` from
a fresh create while a saved draft exists leaves the draft alone (they are different polls).

**Step-2 preview (the re-render after `NewPollModal`):** row 0 gains **`Save for later`** (secondary)
when `poll_drafts` is on — label becomes **`Save (replaces your draft)`** when `load_draft` finds one.
Pressing it writes the row (one write, one log row `poll` / `draft_saved`, `via=panel`), then re-renders
the MAIN panel with a footer line *"Saved. Resume it from this panel any time."* — the create flow
ends; there is no "keep editing after save" state.

**Resumed preview:** `Resume draft` opens the step-2 preview built from the stored `PollDraft` (same
`review_card` + plan path; a stored draft whose plan now fails — e.g. a deleted channel — shows the
plan's refusal in the embed and keeps `Start over` / `Discard draft`). Row 0: `Post it` (or `Date
slots…`) · `Save (replaces your draft)` · `Start over` · **`Discard draft`** (danger → Yes/Keep confirm
on `panels.confirm`). `Post it` from a resumed draft deletes the draft row **in the same transaction**
as the poll insert; the poll's existing `created` log row gains `from_draft: true` in details — no
second row (checklist 34). `Discard draft` = one delete, one log row `draft_discarded`, `via=panel`.

**Staff:** `PANEL_COUNTS` gains `· {drafts} saved draft(s)` when > 0. A **`DraftPick`** select (staff
only, only when drafts exist, capped at `LIST_LIMIT` with the capped placeholder pattern) lists
*"@member — «question» — {age}"*; picking one renders a **draft card** (question, kind, options,
channel, saved-at, member) with `Discard` (danger → confirm → a modal asking for the reason → DM the
member *"Staff removed your saved poll draft «{question}»: {reason}"* — the DM goes through the
test-mode guard like every DM) and `Back`. Staff cannot edit or post someone else's draft (it is not
theirs; posting would forge a creator).

**Settings (staff):** row with `Drafts: on/off` toggle and the `poll_draft_days` control follows the
existing settings-render pattern for `poll_archive_days`.

## 5. Loops, logs, website

- The polls archive loop (`archive` path in the cog) also runs `stale_drafts` per guild and drops each
  with a `draft_expired` log row. No new loop. It must keep the `db.is_connected` check every other
  loop has.
- Log kinds: `draft_saved`, `draft_discarded`, `draft_expired` under feature `poll` — register wherever
  `KNOWN_DYNAMIC` / the AST-derived kinds guard needs them; `logkinds.py` needs no change (feature is
  still `poll`).
- Website: the two settings keys reach the Settings page through the registry + labels. **No drafts
  page or card on the website** — the staff view lives on the Discord panel, one surface (owner rule
  "one fact, one home applies to surfaces"). Say so in `site.md` only if a reader would look for it.
- `docs/info/architecture.md` header table: schema 33, key count +2, feature count unchanged.

## 6. Tests (mirror the package)

`tests/test_polls.py`: json round-trip incl. unknown/missing keys; save-replaces; one-per-person is the
PRIMARY KEY (a second save is an upsert, `drafts()` returns one row); stale selection at the boundary;
`DRAFT` gone from every table (the parametrised status test shrinks by one and a guard asserts
`"draft" not in STATUSES`). `tests/cogs/community/test_polls.py`: buttons render only when valid
(off → no buttons; no row → no `Resume`; staff → `DraftPick` only when rows exist); `Post it` from a
resumed draft leaves zero draft rows and ONE log row with `from_draft`; discard DMs the reason; the
settings toggles land in the store. `tests/storage/test_db.py`: schema 33, table present after
`connect()` on a 32 database. `tests/test_settings_store.py`: the two keys, defaults, bounds.
`tests/api/test_contract.py`: `contract.json` is untouched unless a settings route enumerates keys —
the mock check must still say 17 pages / 149 routes and its core-settings count. (149 was the count
at this build; the mock has read **150 routes, 17 pages, 14 core settings** since v96, which added
`POST /api/polls/recurrences` — [`recurrence-web-create-design.md`](recurrence-web-create-design.md)
— and it still reads that at v108.)

## 7. Prove before merge, and the sweep rows

`ruff` clean; full suite `-n auto` green forward and `BB_REVERSE=1`; `node site/mock/check.mjs` ok;
`python -m black_bloc` NOT booted in a worktree (no token) — say so. Sweep rows lettered `PD-a…` in
`docs/access/sweeps.md` (**numbered 300–304 at the merge**): save → resume → post; save twice
replaces; staff discard DMs; off hides everything; expiry after `poll_draft_days`. Code notes: a
`# Saved poll drafts` section at the foot of `code-notes.md`, keyed by name.

## 8. Not decided here (report, do not build)

Drafts for `recur create` (the cadence step) — out of scope; a recurrence draft is refused with the
existing `RECUR_NOT_A_DATE`-style sentence *"Recurring polls cannot be saved as drafts yet"* only if the
save button would otherwise appear there; simplest is to not render `Save for later` on the recurrence
path at all. Say which you did.

## Deviations

Written by the build agent, 2026-09-06, on `poll-drafts` off `main` at `9cd79d6`. **Status: ✅ LIVE
v94 — merged `8405bea`, deployed 2026-09-06 11:13 (v95 is the same commit).** Everything not
listed here was built as this document says. Details and reasoning for each are in
[`code-notes.md`](code-notes.md) § *Saved poll drafts*.

1. **`Resume draft` is on row 4 of the panel, not row 0 beside `Create`; `Save for later` and
   `Discard draft` are on row 4 of the preview, not row 0.** §4 puts all three in row 0.
   **Discord allows five components per action row and a staff panel's row 0 already holds
   exactly five** (`Create` · `Find #…` · `Refresh` · `Settings` · `Logs`) — a sixth raises at
   render time, so the panel would not open at all for a staffer with a draft. The preview's row
   0 can already reach four (`Date slots…` / `Post it` / `Repeat…` / `Start over` / `Cancel`).
   Row 4 is the drafts row; the site link moved from row 3 to row 4 so the staff `Saved drafts…`
   select could have row 3, and an empty row is not drawn, so nothing else moved visually. A test
   asserts row 0 never exceeds five.
2. **`polls.status` keeps its `DEFAULT 'draft'`.** §2 rule 1 allowed either ("drop it only if
   SQLite allows it cheaply; otherwise leave the default and note it"). SQLite has no
   `ALTER COLUMN`, so dropping it means rebuilding a 37-column table with an index and four child
   tables — real risk for a value nothing can reach, since `create_poll` requires `status` as a
   keyword. Left, and noted here and in the code notes.
3. **Saving answers with an ephemeral sentence, not a footer on the panel embed.** §4 asks for
   the main panel "with a footer line *Saved. Resume it from this panel any time.*". The words are
   exactly that, but they arrive the way every other move in this cog answers — a re-render plus
   `said_to(...)`. ⚠️ A footer would have been **overwritten by `Panel.on_timeout`**, which sets
   the "gone quiet" footer on the same embed, so the sentence would vanish at the ten-minute mark
   and read as if the save had been undone.
4. **`Save for later` and `Resume draft` are only rendered for somebody who could POST the poll**
   (`may_save` = `poll_drafts` on AND `may_create`), not merely when `poll_drafts` is on. A member
   who cannot create a poll cannot post a draft either, and a control nobody can use is not
   rendered (`CLAUDE.md`). Their saved row is never deleted by this — it is simply not offered
   until they can post again.
5. **The `poll_drafts` toggle is on row 4 of the Settings card, not row 0.** Same five-per-row cap:
   row 0 already holds the five existing toggles. Row 4 now holds `Drafts: on/off` · `Numbers…` ·
   `Clear ping role` · `Clear channel` · `Back` — five, exactly at the cap. ⚠️ `poll_draft_days` is
   the **fifth** field of the `Numbers…` modal, which is Discord's modal cap: a sixth poll number
   will need a second modal.
6. **The expiry sweep does nothing while `poll_drafts` is off.** §3 promises that turning drafts
   off keeps the rows "(turning it back on restores them)"; a sweep still running would have
   emptied the table a fortnight later and broken that promise silently. `poll_draft_days` still
   governs everything else, and `0` still means never.
7. **`load_draft` has a sibling, `draft_row`.** §3 names `load_draft(...) -> PollDraft | None`,
   which is what `Resume draft` uses. The panel line and the staff card also need `saved_at`,
   which the dataclass does not carry, so the row-returning read is its own one-line function and
   `load_draft` is written on top of it. One query text, two callers.
8. **`PollDraft.from_json` also replaces a value whose TYPE has changed**, not only unknown and
   missing keys. §3 asks for the latter two. A payload whose `question` came back as a number
   would otherwise raise inside a button callback — a permanent spinner (checklist 30) rather than
   a sentence.
9. **The panel line writes the question in bold rather than in «guillemets».** §4 writes
   *"You have a saved draft: «{question}»"*. Every other line this panel writes uses `**bold**`;
   the guillemets appear nowhere else in the estate.
10. **§8, the recurrence path: `Save for later` is simply not rendered once a draft is
    repeating** — the simplest of the two options the design offered, so no `RECUR_NOT_A_DATE`-style
    sentence was added and none is needed (there is no button to press). `Discard draft` still
    renders on a resumed draft that has since been given a cadence, because the saved row is still
    there. A test covers it.
11. **Two things beyond the design's list were deleted as dead code**, both consequences of `draft`
    leaving `STATUSES`: `CARD_BUTTONS[DRAFT]` (§2 asked for this) and, with it,
    `MOVE_FUNCS["post"]` in the cog — no card row can produce that action any more. The
    parametrised test case that exercised it went with it, which is part of why the count below
    moves the way it does.

### What §7 asked for, and what it got

| Asked | Result |
|---|---|
| `ruff check .` clean | ✅ |
| full suite `-n auto`, forward and `BB_REVERSE=1` | ✅ **5226 passed** both ways (5187 at the base `9cd79d6`). **+39 net = 43 added − 4 removed**, measured by diffing the collected ids, not by subtracting totals: the four are the `draft` cases of `test_a_bystander_is_offered_nothing_at_all`, `test_staff_get_exactly_the_row_the_table_names_for_every_status`, `test_the_card_renders_exactly_the_buttons_the_table_says` and `test_a_move_button_calls_its_shared_function_and_leaves_via_alone`. |
| `node site/mock/check.mjs` | ✅ **ok — 17 pages, 149 routes, 14 core settings** before and after; `labels.js` still parses as an ES module. |
| `python -m black_bloc` NOT booted | ✅ correct — there is no token in a worktree, so the bot was never started and **nothing here has been rendered by a real Discord client**. |
