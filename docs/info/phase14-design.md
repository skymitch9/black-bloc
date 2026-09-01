# Phase 14 — Chat step 3: the real conversation (three tiers, knowledge, personas)

> **Audience:** the Phase 14 build agents and the reviewer. **Status:** TRACKED.
> **Last verified: 2026-09-01** — owner decisions taken this morning (one at a
> time, verbatim below); the GABI mechanics cited were surveyed today from
> `catalog-platform` (agent report; file paths verified to exist, code read).
> Nothing here is built yet.

## 0. Owner decisions (2026-09-01, verbatim)

| Q | Answer |
|---|---|
| Provider | *"can we do a mix of 1 and 3 to help save token cost?"* → three tiers |
| Models | *"lets do groq/llama for simple things and then Haiku for more important things. We'll do a context ingestion like we did for Gabi"* |
| Cost cap | **$20/month** (fallback = intents + an in-character canned line, never silence) |
| Personality | *"start with 1 [Cookout voice] but port over all the other personalities too. we can start building a global personality pool"* |

## 1. The three tiers (deterministic routing FIRST — GABI's hardest-won lesson)

GABI shipped tools three times and watched the model not route to them; every fix
was a deterministic router that fires BEFORE any model call. Same here:

```
@mention → 1. INTENTS (existing chat.py tables — free, already live)
             matched → answer, done. No LLM. This stays the front door.
         → 2. knowledge search (lexical, local, free) + tier decision:
             IMPORTANT → Claude Haiku 4.5   (claude-haiku-4-5 via the anthropic SDK)
             SIMPLE    → Groq / Llama        (their OpenAI-compat HTTP API, own module)
         → 3. any tier errors/capped → the existing canned reply_for lines
```

**IMPORTANT (Haiku) when any of:** the knowledge search returns hits (grounded
answer needed); the message contains a question mark + >12 words; the
conversation window already holds ≥2 LLM turns (a real conversation is
happening); the message mentions staff/mod/report topics. **SIMPLE (Groq)
otherwise** — greetings that slipped past intents, one-liners, banter.
The rule set lives in ONE pure function (`tier_for(message, hits, window)`)
with table-driven tests; thresholds are constants, not settings (tuning
numbers, not operator decisions — same call GABI made).

- **Haiku request shape:** `client.messages.create(model="claude-haiku-4-5",
  max_tokens=400, ...)` — no thinking (not wanted for banter; on Haiku 4.5
  thinking needs budget_tokens and we don't want it), `system` = persona stack
  (§4) with `cache_control: {"type": "ephemeral"}` on the stable core. GABI
  measured 400 max_tokens as right for chat.
- **Groq shape:** plain aiohttp POST (aiohttp is already a dependency) to their
  chat-completions endpoint, model `llama-3.3-70b-versatile` (a
  **`chat_simple_model` setting** so it survives Groq's model churn), same
  400-token ceiling, same persona system text. Own module `black_bloc/groq.py`
  — never mixed into the Anthropic client module.
- **Failure ladder:** Groq error/ratelimit → try Haiku once → canned line.
  Haiku error → canned line. Never silence, never a stack trace, never the
  words "budget/cap/quota/limit" in a user-facing sentence (GABI rule — those
  read as malfunction).

## 2. Keys, gating, posture

- `ANTHROPIC_API_KEY` + `GROQ_API_KEY` via `config.py` ONLY (blank = unset).
  ⚠️ **The owner mints both** (console.anthropic.com / console.groq.com) and
  sets them: `flyctl secrets set NAME=... --app black-bloc` + local `.env`.
  Names go in RECOVERY/runbook custody tables at merge (parent session does docs).
- **Affirmative-only gate** (GABI posture): `chat_llm_mode` registry key,
  `off` (default) / `on`. Off, or a tier's key missing → that tier silently
  doesn't exist and the ladder continues; the bot never breaks on a missing key.
  With mode `on` but no keys at all, step 2 is skipped entirely (today's
  behaviour, unchanged).

## 3. Context ingestion (GABI's docs lane, sized for a Discord server)

GABI: allowlisted markdown → H2 sections → one bundle → **lexical keyword
scoring, deliberately no vector store** (headings ×8, path ×4, title ×3, body
occurrences; AND-of-tokens falling back to OR; snippets, per-turn byte budget,
refuse-don't-trim). Port `searchBundle`'s scoring shape onto SQLite:

- **Schema 20** (additive): `knowledge_sections(id, title, body, source, tag,
  updated_at, updated_by)`.
- **Two sources:** (a) **staff-written** — a dashboard **Knowledge** section on
  the Chat page (add/edit/delete sections) AND `/chat knowledge add|list|remove`
  (checklist 33: both doors); (b) **server-ingested** — a daily loop rewrites
  `source='server'` rows from live Discord: channel names+topics, role names,
  upcoming approved events, active role menus. Staff rows are never touched by
  the loop; server rows are never editable by hand (one writer per row, no
  drift).
- **At question time:** top 3 sections within a 6 KB budget ride the user turn
  as grounding (GABI's catalog-lane inline pattern — simpler than tool_use for
  a bot with no tool loop): `"(What the server's notes say, for your answer —
  quote it rather than inventing: …)"`. Budget refuses (drops the section)
  rather than trims.

## 4. Personality: Cookout core + the ported trope pool

- **Persona stack, additive, order fixed** (GABI's structural safety argument —
  a trope is APPENDED so it can never delete a rule):
  `CORE (identity + hard rules: tone-never-truth, no invented facts about
  members, never claim mod powers it isn't using, no budget-words)` +
  `COOKOUT VOICE (default: warm, playful, community-BBQ — the site's R2 copy
  voice)` + `[optional trope block]`.
- **The pool:** port GABI's 11 tropes from
  `catalog-platform/apps/discord-worker/src/personality.ts` as DATA into a
  `personality_tropes` table (schema 20), text adapted from her book-world to
  this server where needed. `chat_personality` registry key: `cookout`
  (default) / `pool` (per-conversation trope with gradual drift, GABI's
  selection shape) / a specific trope name. Dashboard: a Personality section on
  the Chat page listing tropes with enable/disable + preview; slash:
  `/chat personality`. **The owner's "global personality pool" ambition** (one
  pool shared across estate bots) is future work — for now the port carries a
  provenance header naming GABI's file as the source; a shared estate store is
  a TODO note, not this build.

## 5. Conversation window + fuses + the $20 cap

- **Window** (GABI shape, SQLite): per-channel-per-person rolling window,
  30 min, max 10 exchanges, 600-char clip per turn — `chat_window` table
  (schema 20), swept by the existing loop pattern.
- **Fuses, each its own counter, never folded** (GABI: a cheap turn's
  forgiveness must not buy an expensive one): per-person **20 LLM turns /
  rolling hour**; server-wide **200 / UTC day**; monthly **$-cap** below.
  Registry keys: `chat_person_hourly_turns`, `chat_daily_turns`,
  `chat_monthly_cap_usd` (default **20**).
- **The ledger:** every LLM call writes `llm_ledger(at, provider, model,
  input_tokens, output_tokens, cost_microdollars)` (schema 20) computed from
  the pinned price table in code (Haiku 4.5: $1/$5 per MTok; Groq tier: $0
  while free — still recorded with real token counts). Month-to-date sum ≥ cap
  → tier 2 closed until the 1st; the bot answers with intents + an in-character
  line; `chat.llm_capped` logged ONCE (routine) when it first closes.
- **Surfacing:** `/chat status` and the dashboard Chat page show month-to-date
  spend, turns today, and which tiers are live (worded, not bare numbers).

## 6. Test mode & review checklist notes

- TEST_MODE: replies already ride `on_message` → guarded sends; nothing new
  crosses the guard. The LLM tiers add NO new Discord side effects.
- Never log or echo a key; never send member messages to Groq/Anthropic beyond
  the current window + grounding (no bulk history); say so in code-notes.
- New log kinds (`chat.llm_reply`, `chat.llm_capped`, `chat.llm_error`, …)
  classified in `logkinds.py` (routine).
- `poll_degraded`-style honesty: a tier that is down shows in `/chat status`.

## 7. Build slices

- **14a — core + bot** (~350–450k): schema 20 (4 tables), `black_bloc/llm.py`
  (anthropic SDK wrapper + ledger), `black_bloc/groq.py`, `tier_for`, knowledge
  store + lexical search + server-ingest loop, persona stack + trope port,
  window, fuses, cog wiring behind `chat_llm_mode`, `/chat knowledge|personality|status`,
  settings keys, tests.
- **14b — dashboard** (~200–300k, after or parallel with contract): Chat page
  gains Knowledge + Personality + Spend sections; `/api/chat` grows the
  matching routes; contract + mock + check.mjs.

Ships with `chat_llm_mode off` — flipping it on is the owner's move after the
keys are set. No deploy risk: everything degrades to today's behaviour.
