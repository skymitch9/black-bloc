# Phase 17 — Chat long-term memory (per-person profiles)

> **Audience:** the owner first (the five privacy decisions in §Decisions are
> HIS, asked one at a time), then the Opus builder, then reviewers.
> **Status:** TRACKED — DESIGN DRAFT, written 2026-09-02 by the Fable session
> (NEXT WAVE item 3). ⚠️ **Not buildable until the owner has answered D1–D5**
> — the TODO block says "privacy decisions from owner BEFORE building". The
> "proposed" column is the default the builder ships if he says "go with the
> proposal"; each is a settings key either way.
> Last verified: **2026-09-02** — the "what exists" rows were read in
> `black_bloc/chat_llm.py` (`remember`, `window_for`, `sweep_window`,
> `as_messages`, `user_turn`) and `cogs/content/chat.py:ingest_once` today.
> The three-tier shape is ported from the estate's precedent,
> `catalog-platform/docs/info/gabi-memory-design.md`. ⚠️ NOT verified: Groq's
> JSON-mode behaviour on the distil prompt — the builder measures it first (§J).

## The ask

TODO NEXT WAVE item 3: *"chat long-term memory"* — the bot remembers a person
across conversations ("you said you go by Sky", "you were asking about the
Thursday events last week") instead of forgetting them the moment the 30-minute
window closes. Today Phase 14's window IS the memory; it is deleted after an hour.

## What exists (reuse, do not rebuild)

| Piece | Where |
|---|---|
| **Tier 1 already exists**: `chat_window` (30 min / 10 exchanges / 600 chars a turn — the same numbers as GABI), written by `remember`, read by `window_for`, swept hourly by `sweep_window` from `ingest_once` | `chat_llm.py:217–282`, `cogs/content/chat.py:535` |
| The per-turn prompt assembly (`user_turn` = text + knowledge grounding + people notes) — the memory block slots in beside the people note | `chat_llm.py:488` |
| The cheap-model path (Groq, `chat_simple_model`) with the injectable-`request` client and the spend ledger | `groq.py`, `chat_llm.py:424`, the `chat_ledger` rows |
| Settings registry / labels / mock / exact-key-set test | `settings_store.py`, `site/public/assets/labels.js`, `site/mock/server.mjs`, `tests/test_settings_store.py` |
| Chat page + `/chat` group + `api/tools/chat.py` | the surfaces the memory controls extend |
| The privacy shape (only this person, preferences not content, no availability claims, drop don't guess, cron-time distillation never on the reply path, `/… memory` show/forget ships with the writing) | `catalog-platform/docs/info/gabi-memory-design.md` §Rules |

## Decisions — the owner's five, ONE AT A TIME (proposed defaults in bold)

| # | Question | Proposed | Key |
|---|---|---|---|
| D1 | **Consent model.** Is memory on for everyone until they turn it off, or off until they turn it on? | **Opt-out**: on for everyone; `/chat memory off` stops writing AND deletes the profile. Reason: an opt-in nobody discovers is a feature nobody has; the profile is preferences only (D2), so the downside of default-on is small. | `chat_memory_consent` = `optout` / `optin` |
| D2 | **What is remembered.** | **Preferences, not content**: what to call them, how they like to be talked to, up to 6 short notes (≤120 chars each), up to 5 open threads ("was asking about the Thursday event"). **Never**: quotes of what they said, anything about a third person, anything from a moderation/staff conversation (the `about_staff` gate already exists — those turns are excluded from distillation), availability ("they're usually on at 9"). | `chat_memory_notes_max` int 6, `chat_memory_threads_max` int 5 (the *never* list is code + prompt, not a setting) |
| D3 | **Retention.** How long does a profile live untouched, and are raw turns archived beyond the hour? | **Profile: 180 days** since last update, then deleted; **raw turns: no archive** (the hour-long window stays the only raw store — the GABI tier-3 90-day archive is NOT ported; nothing in the feature list asks for "what did I say last month"). Leaving the server deletes the profile at once. | `chat_memory_retention_days` int 180 (0 = forever) |
| D4 | **DMs vs the server.** Is what the bot learns in a DM usable in a public channel? | **Two scopes, one profile**: notes carry `where: dm|server`; a public-channel reply only sees the `server` notes, a DM sees both. The prompt-level guard GABI relies on becomes a data-level one — a DM note can never reach a public channel. | `chat_memory_dm_scope` = `separate` / `shared` |
| D5 | **Who can read a profile.** Can staff see a member's memory on the dashboard? | **Counts only**: the Chat page shows how many profiles exist, when each was updated, and a Forget button; the *contents* are visible only to the person themselves (`/chat memory show`, ephemeral) and to the owner via the DB. Reason: staff already have modmail and case notes for what they need to know; a bot's private impressions of a member are not a moderation record. | `chat_memory_staff_view` = `counts` / `full` |

Plus the non-privacy defaults, decided by the Fable session: `chat_memory_mode`
off/on (**off** at deploy — dark launch, flipped on the dashboard),
`chat_memory_model` (**blank = `chat_simple_model`**, the Groq tier),
`chat_memory_log_level` (**important**).

## A. Storage — schema **23** (22 is Phase 16's)

```sql
CREATE TABLE IF NOT EXISTS chat_profiles (
    user_id     INTEGER NOT NULL,
    guild_id    INTEGER NOT NULL,
    call_me     TEXT,
    notes       TEXT NOT NULL DEFAULT '[]',   -- JSON [{text, where, at}]
    threads     TEXT NOT NULL DEFAULT '[]',   -- JSON [{text, where, at}]
    turns_seen  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, guild_id)
);
CREATE TABLE IF NOT EXISTS chat_memory_optout (
    user_id     INTEGER NOT NULL,
    guild_id    INTEGER NOT NULL,
    at          TEXT NOT NULL,
    PRIMARY KEY (user_id, guild_id)
);
```

A profile is ≤ 2 KB by construction (`call_me` ≤ 40, notes ≤ `notes_max` × 120,
threads ≤ `threads_max` × 120). A DM turn is filed under the guild the person
shares with the bot (single-guild bot; `DEV_GUILD_ID`) with `where = dm` on
the note — one profile per person, two scopes inside it (D4).

## B. `black_bloc/chat_memory.py` — pure, testable

- `distil_prompt(profile, turns) -> (system, messages)`: the strict-JSON
  instruction, the current profile, the member's turns of the expired
  conversation (bot turns included for context, `about_staff` conversations
  excluded whole).
- `parse_distilled(text) -> Profile | None`: invalid JSON, unknown keys,
  over-length fields → `None` (**no-op, never a partial write**).
- `merge(old, new, *, notes_max, threads_max) -> Profile`: newest wins on
  `call_me`; notes/threads deduped by text, newest kept, clipped to the max;
  a `where` a note came from travels with it.
- `memory_note(profile, *, in_dm: bool) -> str`: the prompt block —
  `"(What you remember about this person from earlier chats — preferences
  only; never claim they are online or free: …)"`; filters `where = dm` notes
  out unless `in_dm` (D4 `separate`).
- `forget(db, user_id, guild_id)`, `opted_out(db, …)`, `set_optout(db, …)`,
  `expire(db, *, days)`, `profile_for(db, …)`.

## C. Where it runs

- **Distillation is on the sweep, never on the reply path.** `sweep_window`
  grows a hook: before deleting rows older than an hour, group the expiring
  rows by `(channel_id, user_id)`; a group with ≥ 2 member turns whose person
  is not opted out (D1) and whose turns are not `about_staff` → distil via
  the Groq client (`chat_memory_model`), merge, write, log
  `chat.memory_distilled` (info, with counts, never the text). Failure →
  `chat.memory_distil_failed` (important once per sweep) and the rows are
  deleted anyway — a missed distillation loses one conversation's worth of
  preference, never a reply.
- **Reading is one indexed SELECT on the reply path** in
  `conversational_reply`: `profile_for` → `memory_note` → appended to
  `user_turn` beside the people note. Missing profile → empty string.
- Distil spend goes on the ledger as tier `memory`; the monthly cap and the
  fuses apply to it (a capped month distils nothing).
- `on_member_remove` → `forget` (D3). `expire` runs on the same ingest loop.
- Mode `off` → no distil, no read, commands say "memory is off on this server".

## D. Surfaces (configurable both ways — checklist 33)

- **`/chat memory`** (member-visible, ephemeral): `show` (the profile in
  words), `forget` (wipe), `forget-this <text>` (drop one note/thread by
  substring), `off` (opt out + wipe), `on` (opt back in). `/help` entry;
  `chat_data.py` FEATURES line ("does the bot remember me? → `/chat memory show`").
- **Dashboard, Chat page, "Memory" section**: mode switch, the settings
  namespace `chat_memory_*`, the profiles table (member · updated · notes
  count · Forget) — contents shown only when `chat_memory_staff_view = full`
  (D5), Logs filtered to `chat.memory*`.
- **API** `api/tools/chat_memory.py`: `GET /api/chat/memory` (counts + table),
  `GET /api/chat/memory/{member_id}` (403-in-words unless `full` or the
  caller is that member), `DELETE /api/chat/memory/{member_id}`.

## E. Settings registry (+ labels.js, mock key list, exact-key-set test)

| Key | Type | Default |
|---|---|---|
| `chat_memory_mode` | mode (off/on) | `off` |
| `chat_memory_log_level` | level | `important` |
| `chat_memory_consent` | choice optout/optin | D1 |
| `chat_memory_retention_days` | int (0 = forever) | D3 |
| `chat_memory_dm_scope` | choice separate/shared | D4 |
| `chat_memory_staff_view` | choice counts/full | D5 |
| `chat_memory_notes_max` | int | 6 |
| `chat_memory_threads_max` | int | 5 |
| `chat_memory_model` | text (blank = simple model) | blank |

## F. Logs (`chat.memory*`)

`chat.memory_distilled` (info: user, notes/threads counts), `chat.memory_distil_failed`,
`chat.memory_forgot` (who asked: self / staff / leave / expiry), `chat.memory_optout`,
`chat.memory_optin`, `chat.memory_expired` (count per sweep).

## G. Tests (mirror)

`tests/test_chat_memory.py` (prompt shape, parse rejects bad JSON/over-length/
unknown keys, merge caps and dedupes, DM notes filtered from server replies,
availability phrases stripped), `tests/cogs/content/test_chat.py` (sweep distils
then deletes, opt-out skips, `about_staff` excluded, mode off is inert, member
leave forgets, ledger row), `tests/api/tools/test_chat_memory.py` (D5 gate in
words), `tests/storage/test_db.py` (schema 23), `tests/test_settings_store.py`.

## H. Docs landing with the build

`code-notes.md`; `access/sweeps.md` rows; `cutover-plan.md` ladder row;
`feature-list.md` (new row); `architecture.md` counts; `OWNER_GUIDE.md` — a
"what the bot remembers about people, and how they clear it" paragraph.

## I. Explicitly NOT in this phase (same list as GABI's, kept on purpose)

No cross-person memory ("what does X like"), no embeddings/semantic recall,
no raw-turn archive, no free-text profile editing by staff, no proactive
"welcome back", no memory of tool results, no memory of moderation content.

## J. First task for the builder — measure, don't assume

Run the distil prompt once against the real Groq model with three captured
windows (a normal chat, a one-liner, a staff-word conversation) and confirm
it returns parseable JSON in the schema, an empty profile for the one-liner,
and that the staff one is never sent. Record the measured behaviour in
`code-notes.md` beside `parse_distilled`. If JSON mode is unreliable, STOP
and report — do not build a retry loop around it.
