# Phase 14 — Chat step 3: the real conversation (three tiers, knowledge, personas)

> ⚠️ **SUPERSEDED IN PART, 2026-09-04 (v75, `251dd14`), by [`chat-panel-design.md`](chat-panel-design.md)** —
> the tiers, the knowledge store, the personas and the spend cap are all as described, but the
> `/chat status`, `/chat knowledge …` and `/chat personality …` subcommands this doc walks
> through (`:78`, `:105`, `:126`, `:137`, `:144`) are retired: `/chat` is now ONE staff command
> that opens a panel, and every one of them is a button, a select or a modal on it.

> **Audience:** the Phase 14 build agents and the reviewer. **Status:** TRACKED ·
> ✅ **LIVE since 2026-09-01** (shipped DORMANT — `chat_llm_mode` off) — deployed
> `2026-09-01T13:21:45-07:00` as `a49e77d` (schema 20, `anthropic` in the image, 2451 tests,
> 106 routes / 17 pages, 35 commands synced); `DONE.md` → "2026-09-01 — Phase 14: the bot can
> really talk (three tiers, knowledge, personas — shipped dormant)". The keys were set an hour
> later (`2026-09-01T14:40:30-07:00`, `ANTHROPIC_API_KEY` + `GROQ_API_KEY`), and a
> **chat-hardening wave** the same afternoon (`45176ed`, `1ab76f8`, `503ce3a`, `bff7331`,
> `4cea469`, `9906bda`) fixed live findings — `DONE.md` → "2026-09-01 — The chat-hardening
> wave". ⚠️ Fly release numbers were not written into `deploys.log` until **v59** (2026-09-03),
> so this landing has a date and a commit but no `vNN`.
>
> ✅ **§4's "global personality pool ambition … future work" HAPPENED** — both halves live
> 2026-09-05 (Black Bloc **v90** `7c59eb1` + **v91** `604226f`; GABI `de4ef63`), closing KI-23.
> `black_bloc/personality_pool.json` is the shared manifest. See
> [`personality-pool-design.md`](personality-pool-design.md) and `DONE.md`.
>
> **Last verified: 2026-09-23 16:2x — the *Follow-up 2026-09-23* section's status only**, at the v162 docs ritual: the banter follow-up and its mention-id line are ✅ **LIVE as v162** (16:20, release commit `4e6e4e4c`; merges `d8278877` and `654570e9`), from `git log` and [`../deploys.log`](../deploys.log). ⚠️ Nothing else in this doc re-read; no live model reply under the new matching seen.
> Before that, **2026-09-11 10:28** — re-checked against the tree at `1d090e5`:
> `black_bloc/llm.py`, `groq.py`, `knowledge.py`, `personas.py`, `chat_llm.py` and
> `personality_pool.json` all exist; `tier_for` is `chat_llm.py:156`; `llm.py:17` still pins
> `MODEL = "claude-haiku-4-5"` and the price table still carries `llama-3.3-70b-versatile`;
> all **six** settings keys named below (`chat_llm_mode`, `chat_simple_model`,
> `chat_personality`, `chat_person_hourly_turns`, `chat_daily_turns`, `chat_monthly_cap_usd`)
> are in `KEY_TYPES`.
> ⚠️ **NOT checked:** whether `chat_llm_mode` is on or off on the live guild, the
> month-to-date spend against the $20 cap, whether either API key is still valid, and anything
> in Discord or a browser — nothing in this pass met either.
> Before that, **2026-09-01** — owner decisions taken that morning (one at a
> time, verbatim below); the GABI mechanics cited were surveyed that day from
> `catalog-platform` (agent report; file paths verified to exist, code read).

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
  the Chat page (add/edit/delete sections) AND `/chat knowledge add|list|remove` *(removed:
  retired at **v75**, 2026-09-04 — **Knowledge…** is a control on the `/chat` panel; both
  doors still exist, so checklist 33 holds)*
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
  `/chat personality` *(removed: retired at **v75**, 2026-09-04 — **Personality…** is a
  control on the `/chat` panel)*. **The owner's "global personality pool" ambition** (one
  pool shared across estate bots) is future work — for now the port carries a
  provenance header naming GABI's file as the source; a shared estate store is
  a TODO note, not this build. *(✅ **Built 2026-09-05**, both halves live — Black Bloc v90
  `7c59eb1` + v91 `604226f`, GABI `de4ef63`; `black_bloc/personality_pool.json` is the shared
  manifest and KI-23 closed. See [`personality-pool-design.md`](personality-pool-design.md).)*

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
- **Surfacing:** `/chat status` *(removed: retired at **v75**, 2026-09-04 — the root of the
  `/chat` panel IS the status card)* and the dashboard Chat page show month-to-date
  spend, turns today, and which tiers are live (worded, not bare numbers).

## 6. Test mode & review checklist notes

- TEST_MODE: replies already ride `on_message` → guarded sends; nothing new
  crosses the guard. The LLM tiers add NO new Discord side effects.
- Never log or echo a key; never send member messages to Groq/Anthropic beyond
  the current window + grounding (no bulk history); say so in code-notes.
- New log kinds (`chat.llm_reply`, `chat.llm_capped`, `chat.llm_error`, …)
  classified in `logkinds.py` (routine).
- `poll_degraded`-style honesty: a tier that is down shows in `/chat status` *(now the
  `/chat` panel's root card)*.

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

## Follow-up 2026-09-23 — banter gets banter (branch `chat-banter`)

✅ **LIVE as v162** — deployed 2026-09-23 **16:20** Phoenix (release commit `4e6e4e4c`; merge `d8278877`, 4 commits; the mention-id line below merge `654570e9`, 1 commit); boot log `database ready` 23:19:53Z, `logged in` 23:19:57Z ([`../DONE.md`](../DONE.md) ▸ 2026-09-23 v162).

**The complaint** (owner, 2026-09-23 15:19 Phoenix, live Discord, verbatim paste). A member wrote
`@Black_Bloc What up`; the bot answered:

> "Smoke was thick that night, cousin. > #upcoming-events: Upcoming community events and when they
> happen. > Who has the Tech Support role: Tech Support — 1 member: Raelcun. > #knuck-up: Fighting
> games — matches, tech and trash talk. Check #upcoming-events for the next cookout, ping Raelcun
> if tech's acting up, and swing by #knuck-up for some fight‑game fire. Holler if you need
> anything else."

Owner: **"this response was too much."**

**Measured** (action row 10199, `chat.llm_reply tier=simple, trope=noir`): the noir opener is the
pool doing its job and NOT the problem. The three `> ` lines were knowledge hits echoed verbatim —
`tokenize` kept the two-letter token `up`, `score` matched it as a SUBSTRING (`upcoming`,
`knuck-up`, `support`), the loose any-token pass returned three notes, `user_turn` attached them
under a header that literally said *"quote it rather than inventing"*, and the simple-tier model did
exactly that. `tier_for` was right to choose SIMPLE.

**What changed** — §1's *"the knowledge search returns hits"* rule and §3's scoring are amended:

1. **Matching cannot fire on small talk** (`knowledge.py`, the one home). `tokenize` drops the
   `STOP_WORDS` frozenset — a module CONSTANT, not a settings key: it is a tokenising rule, not an
   operator decision, and `search` stays pure — and keeps tokens of 3+ characters, edges `._/-`
   stripped. `score` and `occurrences` count WHOLE words only (`up` is never inside `upcoming`).
   Hits rank by distinct tokens landed, then points. The staff note filter on `/chat` ▸ Knowledge
   reads the same `search`, so it is whole-word too (typing `cook` no longer finds *Cookout*).
2. **`is_strong` = two distinct tokens landing on the top note, OR one token naming the channel or
   role that note is about** (`name_of`: a `#channel` title, or the role in *Who has the X role*).
   So `#knuck-up` or `@Tech Support` typed as such is enough, and so is `pbs` for
   `#speed-and-pbs`. The old all-tokens-pass + title-score (`STRONG_SCORE`) rule is gone.
3. **Banter gets banter** (`chat_llm.grounded`): notes are dropped ONLY on a SIMPLE turn that is
   not a question at all (no `?`) and whose hits are weak — a question of any length, a strong hit,
   or an IMPORTANT turn keeps them (conductor narrowing, same day: a short factual question must not
   lose its note). *What up* stays clean because the stop list leaves it no hits to drop. The directory block (the channel list in the
   system prompt) is unchanged, so a banter turn can still point somewhere.
4. **Grounding says use them silently**: the header is the key `chat_grounding_note` (group chat)
   — *these are notes for you — use them silently: never quote, list or bullet them back; mention a
   channel only when the person's question needs it*.
5. **A banter length hint in the cached core**: `chat_banter_style` sits in `stable_core` right
   after the cookout sheet, so both tiers read it and it rides the prompt cache.

Chat group 75 → 77 keys, registry 366 → 368; both keys are edited in the Chat page's
*Personality* section and on Settings (checklist 33, every word editable).

| Message | Before | After |
|---|---|---|
| *What up* | 3 hits on `up`, quoted back | 0 tokens, 0 hits, SIMPLE, no notes |
| *where do I post my PBs* | substring hits | `#speed-and-pbs` top, strong (`pbs` names it), IMPORTANT, grounded silently |
| *who has the tech support role* | role section | role section top, strong (3 words) |
| *when is the cookout* / *when is the cookout?* | `?` form only: SIMPLE, note attached | both: SIMPLE, note attached under the silent-use header |
| *sup fam, cookout vibes* | SIMPLE, weak *Cookout hours* hit attached | SIMPLE, weak hit, no notes |

⚠️ **The question test is a `?` OR a question opener as the FIRST word** (`is_a_question`,
second conductor narrowing: Discord folk rarely type the `?`). The openers are one frozenset,
`chat_llm.QUESTION_OPENERS` (who what when where why how which can could would should does do did
is are am was were any anyone anybody). So *when is the cookout* keeps its note with no `?`;
*What up* now counts as a question but still carries nothing, because it has no hits; a mid-sentence
*how* (*I wonder how the cookout went*) does not count. `a_real_question` reads the same test, so a
13+ word message that opens with an opener now reaches the careful tier too.

Not verified: no live model was called — every test fakes both clients; nobody has said *what up*
to the deployed bot (sweep `CB-a`) — still true after v162 went live (16:2x). The canned greeting intent answers *whats good* before any model, so
this follow-up never sees a greeting at all (owner, 16:17, under v161; TODO ▸ 🔧 👋).

**2026-09-23 — the mention-id trade-off is closed** (owner: *"fix the mention ids too"*, branch `mention-names`): `hits_for` now matches on `mentions.named(guild, text)`, which turns a popup-picked `<#id>` into `#name`, `<@&id>` into `@role`, `<@id>`/`<@!id>` into the member's display name from the guild cache (unknown ids and the bot's own mention stay as sent), so a picked `#knuck-up` tokenises and is strong exactly like a typed one. Matching text only — the model still receives Discord's raw text, and nothing logged changes. ✅ LIVE as v162 (16:20, merge `654570e9`). Not verified live: no popup-picked mention tried since (sweep `CB-b`).
