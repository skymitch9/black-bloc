# Personality per person — survey across the HeyGabi estate

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (secret NAMES only).
> ✅ **The §6 recommendation shipped as v159** (2026-09-23 14:07 Phoenix, release commit `c54f14a8`, merge `c1f0148d`) — see
> [`personality-tones-design.md`](personality-tones-design.md). Last verified for this line only: **2026-09-23 14:1x**
> (`deploys.log` line 158); the survey below is a dated snapshot and was not re-read.
> Owner ask, verbatim (2026-09-23): *"look in the Heygabi workspace, which is catalogplatform book
> buddy gamebuddy and maybe one other, find out how they do the personality mapping per person. I
> also want the cookout personality to be the main personality and all other personality are tones
> upon the main personalities lingo and mannerisms"*
> **Last verified: 2026-09-23**, read-only, from the working trees on this machine:
> `catalog-platform` @ `b79761c`, `bookbuddy/library_catalog` @ `e02f3df`,
> `bookbuddy/audiobook_catalog` @ `d03b2c2`, `boardbuddy/Board_Game_Catalog` @ `e667d6d`,
> `FanslyBuddy` @ `fc9be91`, `tome-of-lore/Tome-of-Lore` @ `00a5787`, this repo @ `e316581f`.
> **Measured:** the code paths cited below (read), and that GABI's canonical pool manifest equals
> Black Bloc's copy minus `synced_from` (parsed both: equal, version 1, `catalog-platform@de4ef63`).
> ⚠️ **NOT measured:** no live bot was asked anything; production setting values (e.g. what
> `chat_personality` is set to on the live server) were not read; no test suite was run; line
> numbers are as of the commits above and will move.

"gamebuddy" = **`boardbuddy/Board_Game_Catalog`** — `heygabi-ai.code-workspace` lists exactly three
folders: `bookbuddy`, `catalog-platform`, `boardbuddy`. The "maybe one other" is taken to be this
repo; `FanslyBuddy` and `tome-of-lore` were checked briefly and have no persona feature.

---

## 1. Comparison

| Repo | Q1 per-person mapping | Q2 unpinned choice | Q3 prompt stack | Q4 logged / surface | Q5 reusable |
|---|---|---|---|---|---|
| **catalog-platform** (GABI, Discord Worker) | ✅ YES — `pers:user:<discordUserId>` in the gateway Durable Object, durable (no TTL), follows the person across DMs/channels; hidden self-pin + devops pin/clear by detector | weighted random on each fresh conversation (30-min window), then drift one graph step every 4 exchanges at 25%; posture `GABI_PERSONALITY=on` | base (`GABI_CORE` + Discord suffix) always present; persona block APPENDED last, framed "a mood, not a different person… still GABI"; mood voices are generic, not written on top of a base lingo | trope NOT written to any log row found; devops-only roster by detector; self-query answers own trope | the manifest; the per-person state shape with `writer`/`pinnedAt`; the "still X" framing |
| **bookbuddy/library_catalog** (GABI site panel) | none | n/a — one voice; only the `GABI_EDGE` intensity dial (`full` default) | one canonical core `GABI_SYSTEM` + optional edge block; no moods | health route reports resolved edge mode; no per-person | "one canonical prompt, copied with a source comment" |
| **bookbuddy/audiobook_catalog** | none | none | no chat LLM persona | none | none |
| **boardbuddy/Board_Game_Catalog** ("gamebuddy") | none | none | only research/enrich system prompts (`packages/research/src/research.ts:106`, `enrich.ts:120`), no persona | none | none |
| **FanslyBuddy** | none (no hits for persona/personality/system prompt) | none | none | none | none |
| **tome-of-lore** | none (one unrelated regex hit, `prune.py:32`) | none | none | none | none |
| **black_bot_baf** (Black Bloc) | ❌ NO per-person store — the mood is derived per `channel:user` 30-min window, recomputed each turn, stored nowhere | server-wide setting `chat_personality` = `cookout` (no mood) \| `pool` (seeded random from the window key + drift) \| a trope name; staff enable/disable each trope | cached core ALWAYS carries `COOKOUT_VOICE`; the trope block is appended after it — but nothing tells a mood to keep cookout's lingo, and `COOKOUT_VOICE` has no lingo to keep | trope not in `llm_ledger` or `chat_window`; panel/site show the server MODE and `in_use` per trope, not who hears what | already shares the manifest (v1, in step) |

---

## 2. catalog-platform — GABI on Discord (the only per-person design in the estate)

Design: `docs/info/gabi-personality-design.md` (§§1–12). Code: `apps/discord-worker/src/`.

**Q1 — mapping.** Keyed by Discord user id alone: `gateway.ts:327`
`const kUserPersona = (id) => \`pers:user:${id}\``, in the gateway Durable Object's storage. State
shape (design §6): `{ trope, exchanges, since, pinned?, writer?: 'self' | 'devops:<snowflake>',
pinnedAt? }`. Lifetime: **indefinite** — *"It outlives the conversation deliberately. A pin that
evaporated after 30 minutes would not be a pin"* (design §6). The conversation itself is
person-keyed too (`personality.ts:626–627`, `PERSON_SURFACE = 'discord_person'`,
`PERSON_SPACE = 'all'`), so a DM and a channel are the same conversation.
- Person's door: a hidden **detector**, not a command — *"be tsundere"*, *"personality off"*
  (`personality.ts:567` `personaCommand`, handled `mention-flow.ts:2092–2103`); *"what personality
  are you using with me?"* answers from state read live (`mention-flow.ts:1839`, `personality.ts:784`).
  Owner rule: *"we can also have a command to pick a personality but don't tell end users that"*.
- Staff door: devops may pin/clear anyone by **mention only** — *"A BARE NAME IS REFUSED, NEVER
  RESOLVED"* (`personality.ts:904` `personaAdminCommand`, `mention-flow.ts:1902`). Gate is a real
  call to the auth Worker (200 = devops, 403 = not, anything else = outage, design §5c).
  Last-write-wins; a person may un-pin what an operator set.

**Q2 — unpinned choice.** `gateway.ts:737–754` `personaTurn`: no stored state or a fresh conversation
(no turns in the 30-min window, `packages/gabi-conversation/src/index.ts:223`
`CONVERSATION_WINDOW_MS = 30 * 60 * 1000`) → `pickTrope({ pinned })` (`personality.ts:432`): pin
wins, else weighted random (weights hook exists, nothing fills it). Otherwise `advancePersona`
(`personality.ts:457`): every `drift.every` (4) exchanges a `drift.chance` (0.25) roll to ONE
neighbour. State is written every turn. Posture: `GABI_PERSONALITY = "on"` (`wrangler.toml:516`).

**Q3 — prompt stack.** Base = `GABI_DISCORD_SYSTEM = \`${GABI_CORE}${DISCORD_SUFFIX}\``
(`gabi-prompt.ts:177`), always present. Extras appended in one line (`mention-flow.ts:2089–2090`):
`[memory?.block, cfg.edgeBlock, persona?.block].filter(Boolean).join('\n')` — the edge dial sits
BEFORE the persona so the persona's closing clauses qualify the licence (design §11.2). The persona
block (`personality.ts:509–516`):
```
How you sound right now — this is a mood, not a different person. You are still GABI, the estate's librarian.
${voice}
⚠️ ${REGISTER}
⚠️ ${INVARIANT}
```
Invariant (design §1): *"PERSONALITY IS TONE, NEVER TRUTH… the persona block is appended to the
system prompt and never replaces any part of it"*. ⚠️ Note what it protects: **facts and refusals**,
not GABI's *lingo*. The eleven voice bodies (`personality.ts:229+`) are self-contained registers
("You are BRIGHT and fast today…"); GABI's own voice is kept only by the one "still GABI" sentence.
So GABI is "base + mood appended", **not** "moods as tones on a base lingo" — the same gap Black
Bloc has.

**Q4 — logging / surface.** No trope field found in any log/event write (grep of `trope` across
`src/`); the persona path only `console.error`s failures (`gateway.ts:1536–1540`). Surfaces: the
devops-only roster by detector (`gateway.ts:813` `personaRoster`, `personality.ts:987`
`renderPersonaRoster`, capped `PERSONA_ROSTER_MAX = 100`) — one line per person: `<@id> — trope ·
pinned by <@writer> | drifting · last shift`; and `/api/health` → `gabi_personality_tropes` +
`gabi_personality_pool_version` (roster, not per person).

**Q5 — reusable.** The manifest `personality-pool.json` (27 lines): `version`, `locked_by`,
`drift {every, chance}`, `tropes[] {name, label, neighbours[]}`, `clauses {invariant, register}` as
templates, `slots [invariant_nouns, tool_noun, audience, warn]`. Black Bloc already consumes it.
The per-person state shape and the provenance lesson (*"PROVENANCE MUST SURVIVE A DRIFT STEP"* —
spread prior state, design §6) are the parts worth copying.

## 3. bookbuddy/library_catalog — GABI's site panel

No moods, no per-person mapping. `packages/research/src/gabi.ts:74–83`: *"The core personality,
identical for every turn… THIS IS THE CANONICAL PROMPT FOR THE WHOLE ESTATE"* — catalog-platform's
`GABI_CORE` is a copied subset with a source comment, no sync script. The only knob is the
`GABI_EDGE` intensity dial (`gabi.ts:223–224`, defaults `full`; `apps/worker/src/env.ts:404–423`),
reported by `apps/worker/src/routes/health.ts:340`. `gabi.ts:183` says outright the eleven tropes
*"are a Discord-only mechanism"*. `docs/info/gabi-unification.md` plans one personality for both
surfaces (Phase 3) — not moods.

## 4. audiobook_catalog, Board_Game_Catalog, FanslyBuddy, tome-of-lore

None. Ripgrep for `personalit|tsundere|trope|persona|system_prompt` over code and docs: audiobook —
no hits; Board_Game_Catalog — only the research/enrich extraction prompts (fact-finding, no voice)
and unrelated doc prose; FanslyBuddy — no hits; tome-of-lore — one unrelated regex (`prune.py:32`).

## 5. Black Bloc today (this repo)

Design: `docs/info/personality-pool-design.md`; runbook `docs/access/personality-pool.md`.

**Q1 — mapping: none per person.** `chat_llm.py:611–616`:
`pick_trope(read_setting(..., PERSONALITY_KEY, COOKOUT), await pooled(bot), key=window_key(channel_id,
user_id), turns=llm_turns(window))`. `window_key` = `"{channel_id}:{user_id}"` (`chat_llm.py:194`);
the window is the last 30 min / 10 turns of `chat_window` (`chat_llm.py:52–53`, `window_for`
`:258`). Nothing about the mood is stored — it is re-derived each turn. Consequences: the same
member in two channels can hear two moods; after 30 quiet minutes the key is the same so the
**start** mood repeats (seeded by `random.Random(key)`, `personas.py:386`), but the drift step count
resets with the window. No person or staff door per member.

**Q2 — unpinned choice.** Per-guild setting `chat_personality` (`settings_store.py:263`, enum
`PERSONALITY_CHOICES = (cookout, pool, *11 tropes)`, `:478`, described `:1116`), default
`cookout`. `personas.py:390–401`: `cookout` → no trope; `pool` → deterministic start from the key,
then `drifted()` one step per `DRIFT_EVERY_TURNS` (4) with chance 0.25, seeded `f"{key}:{step}"`
(`:373–387`); a name → that trope while enabled, else cookout with a log warning. Staff own
`personality_tropes.enabled` (`db.py:487`) from the `/chat` panel (`chat_panel.py:351–387`) and the
site (`api/tools/chat.py:668–693`). Boot sync from the manifest never touches `enabled`.

**Q3 — prompt stack.** `personas.py:315–326` `system_blocks`: block 1 = `stable_core()` =
`CORE + FEATURES + COOKOUT_VOICE` (cached), block 2 = channel directory, block 3 = `trope_block`.
So **the cookout voice is always present and a mood is appended after it** — structurally a mood
cannot delete a rule ("Core first and cached… a trope cannot delete a rule"). But:
- `COOKOUT_VOICE` (`:192–195`) is four lines: *"warm, easy, a little playful — somebody's favourite
  uncle working the grill who is glad you came. Use people's names. Never be stiff."* It names a
  **mood**, not lingo or mannerisms — there is no vocabulary, no turns of phrase, nothing for a tone
  to sit on.
- `TROPE_BLOCK` (`:200–204`) opens `## How you sound right now` — a heading that competes directly
  with `## How you sound`, arrives later (recency wins in practice), and says only *"This is a mood,
  not a different person. You are still Black Bloc, the cookout's bot."* — identity, not voice.
- `REGISTER` (PG-13 ceiling) and `INVARIANT` (*"This is VOICE ONLY. Facts, refusals, the server's
  own notes… are unchanged"*) protect **truth and rating**, never the cookout lingo.
- Most `VOICES` bodies (`:215–270`) are GABI's with book words swapped out; only `cozy` ("a folding
  chair in the shade and a full plate") is cookout-skinned. `noir` ("metaphor about rain"),
  `scholar`, `deadpan` pull the opposite way from the uncle at the grill.

⚠️ **Answer to the owner's question: yes, a mood today can override cookout's lingo** — not by
deleting the base text, but because the later `## How you sound right now` block gives a full,
self-contained voice and nothing says "keep the cookout's words underneath". The *base-plus-tones*
shape exists structurally; the *wording* that makes a mood a tone does not.

**Q4 — logging / surface.** `llm_ledger` (`db.py:534–549`) and `chat_window` (`db.py:499–508`)
carry tier/model/tokens, no trope. Mode changes and enable/disable are action-logged
(`chat.personality_mode`, `chat.trope_enabled/disabled`, `chat_panel.py:362,387`); pool syncs log
`chat.pool_synced`/`chat.pool_retired` (`personas.py:537–545`). The site's personality view shows
each trope's `enabled` and `in_use` (= the server mode, `api/tools/chat.py:227–236`) — **no
surface shows who is hearing which mood**, because nothing records it.

---

## 6. What Black Bloc should borrow

### (a) Per-person mapping — take GABI's shape, adapted to the house rules

| Decision | Recommendation | Source |
|---|---|---|
| Key | **(guild_id, user_id)** — follows the member across channels and DMs, like `pers:user:<id>`; drop `channel` from the mood key (keep it for the conversation window) | GABI design §5, §6 |
| Storage | its own table, e.g. `chat_voice(guild_id, user_id, trope, turns, since, pinned, writer, pinned_at)` PK `(guild_id, user_id)` — NOT columns on `chat_profiles`, so `/memory` "forget the lot"/opt-out does not silently clear a staff pin (or decide deliberately that it should — owner fork) | GABI §6 "its own key" |
| Lifetime | the **pin is durable** until cleared; an unpinned mood re-rolls when the 30-min window is empty and drifts one step per 4 model turns inside it; `turns` resets on a fresh window, the pin does not | GABI §4, §6 |
| Precedence | server `chat_personality = cookout` still means *no tone for anyone* (the off switch); otherwise **person pin > server named trope > pool roll**; a pin to a disabled trope falls back to cookout with a worded note on the panel | staff final say |
| Staff door | on the `/chat` panel's Personality view: **Set a member's tone…** (user select + trope select) and **Clear**, plus a **roster** (`<@id> — tone · pinned by <@staff> / drifting · last shift`), and the same table + editor on the site; each write one action-log row with the writer's id; DM'd reason only if the owner wants the person told (GABI deliberately does NOT notify) | CLAUDE.md panels, staff-final-say, both-ways |
| Person door | ⚠️ **owner fork** — GABI hides the self-pin by order; Black Bloc's panels rule would put it on a panel (e.g. `/memory`). Ask, one question | GABI §5 |
| Record | add `trope` to `llm_ledger` (and/or `chat_window`) so every reply says which tone wrote it — the roster's "last shift" and any audit then read a fact, not a recomputation | GABI gap; checklist "silent vs success" |

Reuse `pick_trope`/`drifted` as they are; they already take a key and a turn count. The change is
where the key comes from and that the result is stored (write `...prior` first so provenance
survives a drift, GABI §6).

### (b) Cookout as the main voice, moods as tones on it

What already fits: cookout voice is in the cached core on **every** reply, and the mood is appended,
never substituted (`personas.py:311–326`). What does not: the lingo is not written down, and the
mood block is worded as a replacement voice. Concretely:

1. **Give the base something to keep.** Expand `COOKOUT_VOICE` into a real lingo-and-mannerisms
   sheet — the words, greetings, sign-offs and habits the owner wants (owner-authored; per the
   every-word-editable rule it becomes a settings key with the current text as default).
2. **Re-word `TROPE_BLOCK` as a tone, and rename the heading** so it stops competing, e.g.
   `## Today's tone (on top of the cookout voice)` + *"This is a TONE on the cookout voice above, not
   a different voice. Keep the cookout's words, names and mannerisms from "How you sound" in every
   line; the tone changes only your energy, pace and attitude. A noir cookout uncle is still the
   cookout uncle, just world-weary about it."* Put this sentence right after `{voice}` and before
   `REGISTER`/`INVARIANT`.
3. **Re-skin the eleven bodies as cookout tones** (as `cozy` already is): each starts from the uncle
   at the grill and says what changes — "peppy: the uncle who just heard the good news", not "You
   are BRIGHT". `VOICES` is Black Bloc's own skin, so this needs **no manifest change or pool
   bump** — the manifest carries names, graph, drift and the two clauses only.
4. **Pin it by test** (mirroring GABI's literals): every `system_text(trope)` contains
   `COOKOUT_VOICE` in full; every trope block contains the tone clause; the base heading appears
   once and before the tone heading. A test proves the instruction is present, not obeyed — read
   replies under `noir`/`scholar`/`deadpan` first after deploy.
5. Optional, and a cross-repo fork: a third manifest clause (`base`, slot `{base_voice}`) would put
   "a tone on your own voice" into GABI too (she has the same gap, §2 above). That is a pool
   **version bump + re-sync in both bots**, so only if the owner wants GABI changed as well.

---

## 7. What this survey could not find

- Any place in the estate where a mood/trope is written per reply to a log or audit row (GABI and
  Black Bloc both: none found by grep).
- Any per-person personality in `library_catalog`, `audiobook_catalog`, `Board_Game_Catalog`,
  `FanslyBuddy` or `tome-of-lore`.
- Live values: GABI's production `GABI_PERSONALITY`/`GABI_EDGE` were read from `wrangler.toml`, not
  from the live Worker; Black Bloc's live `chat_personality` value was not read.
- How any mood actually reads to a person — GABI's own doc says nobody has graded the tropes
  (design §10, §11.7); the same holds here.
