# Saved poll drafts — design

> **Audience:** the build agent and reviewers. **Status:** TRACKED. Last verified: **2026-09-06 10:05** —
> every `path:name` below was read in the tree at `62ace89` (v93 + the fixture sweeps); nothing has been
> built yet. Owner decision **2026-09-06 09:45**, verbatim: *"B but only save 1 draft per person max"*
> — answering "polls' `draft` status: (a) drop it or (b) make saved drafts real". This closes fork I-3 of
> [`polls-panel-design.md`](polls-panel-design.md) §I the other way: a member CAN leave the create flow
> and come back to it.

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
the mock check must still say 17 pages / 149 routes and its core-settings count.

## 7. Prove before merge, and the sweep rows

`ruff` clean; full suite `-n auto` green forward and `BB_REVERSE=1`; `node site/mock/check.mjs` ok;
`python -m black_bloc` NOT booted in a worktree (no token) — say so. Sweep rows lettered `PD-a…` in
`docs/access/sweeps.md` (the conductor numbers them at the merge): save → resume → post; save twice
replaces; staff discard DMs; off hides everything; expiry after `poll_draft_days`. Code notes: a
`# Saved poll drafts` section at the foot of `code-notes.md`, keyed by name.

## 8. Not decided here (report, do not build)

Drafts for `recur create` (the cadence step) — out of scope; a recurrence draft is refused with the
existing `RECUR_NOT_A_DATE`-style sentence *"Recurring polls cannot be saved as drafts yet"* only if the
save button would otherwise appear there; simplest is to not render `Save for later` on the recurrence
path at all. Say which you did.
