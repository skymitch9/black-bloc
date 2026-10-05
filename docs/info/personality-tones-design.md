# Personality tones — the cookout is the voice, every mood is a tone on it, and the tone follows the person

> **Audience:** Claude sessions and the owner. **Status:** TRACKED — ✅ **LIVE as v159** (2026-09-23 **14:07** Phoenix, release commit `c54f14a8`, merge `c1f0148d`).
> **Verified live at the v159 boot:** the boot log (21:07:23Z) read `database: added personality_tropes.voice_edited_by`,
> `…voice_edited_at`, `…llm_ledger.trope`, `database ready`, `personas: pool v1 synced — 0 inserted, 11 updated,
> 0 retired` — the eleven rewritten tone bodies are in the live table; `GET /api/chat/voices`, read at the ritual through
> the operator token, answers setting **`cookout`**, 11 tones, 0 voices, 0 pins. ⚠️ With the server on `cookout` the
> precedence turns tones OFF for everyone, so no live reply carries a tone until staff pick **pool** or a mood.
> ⚠️ **NOT verified live:** no model reply under a tone has been read; no Discord (`/chat` ▸ Who hears what…); no browser
> on the Chat page's new sections. **Until the deploy the status read:** BUILT, NOT MERGED, NOT DEPLOYED
> (branch `personality-tones`, worktree `C:/lcw/bb-personality-tones`, off `main` `083ca538`, with `main` merged in
> twice — `562e27c9` (birthday-post-today, three append-only conflicts) and `654be0c8` (channels-page, twelve files:
> schema 56 kept, the Chat page's channel section is main's link card, both sides' keys/tests/docs kept); built 2026-09-23 by an Opus build agent from
> the conductor's brief). Secret NAMES only.
> **Last verified: 2026-09-23 14:1x** — the status lines above only, at the v159 docs ritual; the body (including
> *Not verified* at the foot, whose boot-sync line is now answered above) was not re-read.
> Before that, **2026-09-23, on the tree with `654be0c8` merged** — `ruff check black_bloc tests site` clean;
> `pytest -q -n 16` **7604 passed, 3 skipped**; `node site/mock/check.mjs` **ok — 22 pages, 209 routes, 25 core settings** against a mock
> on a private port; `page-chat.js` and `page-settings.js` load as ES modules (fail only on `document is not defined`).
> ⚠️ **Nothing here has met live Discord, a live model or a browser** — see *Not verified* at the foot.

> ➕ **2026-10-05 — a follow-up at the foot of this file** (*a tone is stored, settles, and moves on real feedback*,
> branch `tone-settles`, BUILT, NOT MERGED): the pool no longer rolls a fresh tone per conversation. *Who hears which
> tone — precedence* row 4 and *The roll (4)* below describe the code BEFORE it.

## The owner's asks (verbatim, 2026-09-23)

> "i want to see what personality is connected to each person for the bot"

> "I also want the cookout personality to be the main personality and all other personality are tones upon the main
> personalities lingo and mannerisms"

The estate survey written an hour before this build is the evidence base and its §6 is the design this follows:
[`personality-per-person-survey.md`](personality-per-person-survey.md). The pool this builds on is
[`personality-pool-design.md`](personality-pool-design.md) (its roster, graph, drift and two clauses are unchanged).

## What was built

| Part | Where |
|---|---|
| The cookout sheet — a real lingo-and-mannerisms guide, 21 lines, still headed `## How you sound` | `personas.py:COOKOUT_VOICE`, and the settings key **`chat_cookout_voice`** (text, group chat; default = the sheet) |
| The tone sentence under every mood | `personas.py:TONE_CLAUSE`, key **`chat_tone_clause`** |
| The mood block re-headed `## Today's tone (on top of the cookout voice)`, the eleven bodies rewritten as cookout tones | `personas.py:TROPE_BLOCK`, `VOICES` |
| A body staff rewrite on the Chat page, kept across the boot sync | `personality_tropes.voice_edited_by` / `voice_edited_at` (schema 55), `write_voice` / `reset_voice` |
| The tone each member hears, and a staff pin | table **`chat_voice`** (schema 55), `black_bloc/chat_voice.py` |
| The tone on the record | `llm_ledger.trope` (schema 55) and `trope` in the `chat.llm_reply` details |
| Who hears what, on the site | `GET/PUT/DELETE /api/chat/voices[/{user_id}]`; the Chat page's **Who hears what** section |
| Who hears what, in Discord | `/chat` ▸ **Personality…** ▸ **Who hears what…** (staff only) |
| Every sentence either door answers with | 25 `chat_voice_*` / `chat_tone_*` word keys (`settings_store.py:VOICE_WORDS`) |

## The cookout sheet (the shipped default of `chat_cookout_voice`)

```
## How you sound
You sound like the cookout: warm, easy, a little playful — somebody's favourite uncle working the
grill who is glad you came. That voice is yours in every answer, whatever the day's tone is.
The words you reach for: "fam", "cousin", "y'all", "pull up a chair", "grab a plate", "the
spread", "on the grill", "say less", "real talk", and "bless" when somebody shares good news.
Everyday words over fancy ones.
How you greet: by name, like they just came through the gate — "Look who pulled up", "There
they are", "Ayy, come on in".
How you help: the answer first, then the warmth. One plain sentence beats three clever ones.
How you tease: gently, and never about who somebody is — you rib a bad take the way an uncle ribs
the nephew who burned the hot dogs, then you help anyway.
How you agree: "Facts.", "Say less.", "You already know."
How you disagree: easy and friendly — "Nah, cousin, hear me out" — then your reason.
How you celebrate: loud and quick — "Ayyy!", "That's what I'm talking about!", "Somebody get
this one a plate!"
How you close, when it fits: "Holler if you need me", "Plate's here when you're hungry", "I got
you." Never a sign-off on every line.
Your habits: you use people's names, you talk like the food is nearly ready, and you treat a
newcomer like family you had not met yet.
What you never do: sound stiff or corporate, lecture, pile on slang until it reads like a
costume, put on an accent, or use slang to make fun of anybody. Given the choice, be brief and
friendly rather than long and correct-sounding.
```

⚠️ **This is the build agent's draft, not the owner's.** The survey (§6b.1) said the sheet should be owner-authored; it is
a key precisely so he can rewrite it on the Chat page (Personality ▸ *The cookout voice*) or on Settings. "no cap" was
deliberately left out: `cap` is one of `chat_llm.BUDGET_WORDS` and a test forbids any budget word in the voice.

## The tone sentence (the shipped default of `chat_tone_clause`)

> This is a TONE on the cookout voice above, not a different voice. Keep the cookout's words, names and mannerisms from
> "How you sound" in every line; this tone changes only your energy, pace and attitude. A noir cookout uncle is still
> the cookout uncle, just world-weary about it.

The stack a model reads, in order: the cached core (`CORE` + `FEATURES` + the sheet) → the channel list → the tone
block: `## Today's tone (on top of the cookout voice)`, the mood body, **the tone sentence**, `REGISTER`, `INVARIANT`.
The sentence sits right after the body, as survey §6b.2 placed it. `## How you sound` appears exactly once, before the
tone heading (tested).

## Who hears which tone — precedence

| # | When | Tone | Written to `chat_voice`? |
|---|---|---|---|
| 1 | `chat_personality = cookout` | none — the cookout voice alone, **for everybody, pins included** (the off switch) | no |
| 2 | the member has a **pin** and that mood is switched on | the pin | yes (trope, turns, since) |
| 3 | `chat_personality` names one mood and it is on | that mood | yes |
| 4 | `chat_personality = pool` | the member's own roll | yes |
| — | a pin whose mood is switched off | falls through to 3 / 4 (and the roster says the pin is *waiting*) | — |
| — | a DM (no guild) | unchanged: the per-conversation roll keyed `channel:user`, and a DM reads the registry default (`cookout`) | no |

**The roll (4).** Keyed by **(guild_id, user_id)**, not by channel: the seed is `guild:user:since`, where `since` is when
the member's current 30-minute window opened. The window is *their model turns in the last 30 minutes anywhere in the
server* (`chat_voice.window_turns`, read off `chat_window`), so the same member hears the same tone in every channel.
An empty window re-rolls (`since` = now, turns 0); inside it the tone drifts exactly as before — `DRIFT_EVERY_TURNS`,
`DRIFT_CHANCE`, `personas.drifted`, deterministic from the seed.

## Decisions (the conductor's, recorded here as reversible)

- **D1 — no member self-serve door in this build.** GABI hides her self-pin on the owner's orders (survey
  §catalog-platform). A member can still ask `/memory` what the bot knows; a `/chat` "my tone" button is one small
  follow-up if the owner wants it. *Reversible:* add a member half to the `/memory` panel calling `chat_panel.pin_voice`.
- **D2 — `chat_voice` is its own table**, not columns on `chat_profiles`, so `/memory` "forget the lot", opt-out and
  retention never clear a staff pin (tested: `tests/test_chat_voice.py::test_forgetting_a_members_memory_never_clears_their_pin`).
- **D3 — a pin is not DM'd to the member.** GABI does not notify either; the staff-final-say rule asks for a DM only
  where a person is *affected by a decision about them*, and a tone is presentation. *Reversible:* one `send_dm` in
  `pin_voice`.
- **D4 — the pin is `pinned TEXT` (the mood's name)**, not a boolean beside `trope`: `trope` is what was last *used*,
  `pinned` is what staff *chose*, and a pin to a mood that is off keeps both facts.
- **D5 — a staff-edited body is marked with `voice_edited_at`**, and `_stale` / `_update_trope` leave its wording alone
  while still taking a new label, wings and order from the manifest. A blank edit (`voice: ""`) puts the shipped body
  back and hands it back to the sync. One log kind, `chat.tone_edited`, with `reset: true|false`.
- **D6 — the tropes table is global**, so a body edit is global across guilds (Black Bloc runs in one server; the pool
  design already made the table global).

## Doors

- **Site:** Chat page ▸ **Personality** — the *cookout voice* card (the sheet and the tone sentence, tall textareas,
  saved through the ordinary settings route), and on every tone card a wording box with **Save the wording** and, when
  it is yours, **Put the shipped wording back**. Chat page ▸ **Who hears what** — the roster table (member + *talking
  now*, the tone heard, pinned by whom and when or *rolled*, turns, and a tone select with **Pin** / **Clear**), a
  member picker to pin somebody not listed yet, and the 25 words in a fold.
- **Discord:** `/chat` ▸ **Personality…** ▸ **Who hears what…** — 25 members a page (Previous / Next render only when
  there is somewhere to go); Discord's member picker opens one member's card: a select of the moods that are on pins
  one, **Clear the pin** renders only on a pin. Both cards carry *Try again* (checklist 36).
- **One write path:** `chat_panel.pin_voice`, `clear_voice`, `edit_tone`, `voice_roster` — the routes pass
  `via=website` (checklist 34). Kinds `chat.voice_pinned`, `chat.voice_cleared`, `chat.tone_edited`, all ROUTINE.
- **Refusals in words:** an unknown or switched-off mood (or `cookout`/`pool`/blank) is a **422**, a member who is not
  in the server (or a bot) a **404**, a body over 1200 characters a **422** — each a keyed sentence.

## Deviations from the brief

1. **The brief's `chat_voice.pinned` column** is `pinned TEXT` (the mood name), not a flag — D4.
2. **A pin to a switched-off mood falls through to the server's setting**, per the brief's precedence ("while it is
   enabled; else…"). The survey (§6a) said it should fall back to *cookout*; the brief won.
3. **`conversational_reply` now answers `(text, tier, tone)`** — a 3-tuple — so the cog can put the tone on the
   `chat.llm_reply` row. Every caller and test was moved.
4. **27 new keys, not 2 + "a few"**: the sheet, the tone sentence and 25 words (every sentence, label, placeholder and
   line template either door says). The chat settings group is **66** on this branch alone and **70** with `channels-page` merged (its four draft words), so `/settings` ▸ chat reads *25 of 70*; the
   `/chat` Settings card leaves the wording keys to the site (they would swamp it).
5. **The roster's `trope`** is what the member hears *now* as far as it can be known (cookout when the setting is
   cookout, the pin when it is on, the named mood, else the last roll); `last_trope` in the helper is the stored one.
6. **Paging helpers** `chat_panel.page_count` / `wanted_page` mirror `modcases.page_count` / `wanted_page` with a page
   of 25 rather than `CASES_PER_PAGE` — near-duplicates on purpose, NOT interchangeable (different page size).
7. **The mood bodies are the agent's drafts** (each keeps the safety line of the old body: shy still gives the whole
   answer, charm not heat, the grumbling is all surface, the weariness is a style). They are editable per mood.

## Not verified

- **No live model has read the new stack.** A test proves the sheet and the sentence are *present*, not *obeyed* —
  read replies under `noir`, `scholar` and `deadpan` first after a deploy (survey §6b.4).
- **No live Discord:** the `/chat` cards were driven with the test fakes only; the UserSelect's behaviour with a real
  member cache, and the embed length with 25 real lines, were not seen.
- **No browser:** the Chat page's two sections were not opened; only the module load and the mock's contract were
  checked. The textarea heights are a CSS guess.
- **The boot sync on the live table:** the rewritten bodies reach `personality_tropes` at the next boot sync, and only
  while `personality_pool_sync` is on (it is on by default). Not seen on the live bot.
- **Not deployed; no migration run** — the schema-55 change is additive (one table, three nullable columns). ⚠️ **Schema number:** this branch built 55; `main` meanwhile went 54 → **56** (`channels-page`, `channel_drafts`) and left 55 free, so the merged tree's `SCHEMA_VERSION` is **56** with this branch's 55 kept as history — every migration here is `CREATE TABLE IF NOT EXISTS` / `ADDED_COLUMNS`, which run on every connect whatever the stored number.


---

## Follow-up 2026-10-05 — a tone is stored, settles, and moves on real feedback

> **Status: BUILT, NOT MERGED, NOT DEPLOYED** — branch `tone-settles`, worktree `C:/lcw/bb-tone-settles`, off `main`
> `3335d929`, built 2026-10-05 by an Opus build agent from the conductor's brief. **Last verified: 2026-10-05**, on the
> branch only: the suite, `check.mjs` and a headless browser against this worktree's mock. ⚠️ Nothing here has met live
> Discord, a live model or the live database — see *Not verified* at the foot of this section.
> ⚠️ **Schema 86 → 87 on this branch.** `memory-rapport` is being built in parallel; if it also takes 87, one of the two
> must move to 88 at the merge, and the pin conversion below runs only on the boot that crosses THIS branch's number.

### The owner's words (verbatim, 2026-10-05)

> "I don't want these to be pins just starting points. Maybe we need a reroll and a pin option."

> "I want this to be stored in memory in the sense that it's not just 30 minutes of conversation…"

> "I still want personality to be able to drift but less as time goes on. Basically if the responses match the tone we
> keep it, if the response is genuinely about how the bot was mean or wrong we adjust the tone."

### The rules

Precedence is unchanged: **cookout** (no tone for anybody) > a member's **pin** (while that tone is on) > a **named
mood** > **pool**. Everything below is the pool branch only; under cookout, a named mood or a pin the stored tone is
neither read nor written (tested).

| Rule | How |
|---|---|
| A member has ONE stored tone | `chat_voice.tone`. The first pool answer to a member with none rolls one (seeded by guild, member and the moment) and writes it. A new conversation starts from it — nothing is re-rolled per window. |
| Staff may set a start ahead of time | **Set tone…** writes `tone` with `how = set`; it is used from the next answer and drifts like any other. It is not a pin. |
| It may still take a step | Weighed every `DRIFT_EVERY_TURNS` (4, the shared manifest's) model answers **heard in this tone**, counted across conversations (`chat_voice.heard`). At most one step, to a graph neighbour that is switched on (`personas.step_from`, unchanged). |
| …but less as time goes on | The chance is `max(floor, start × 0.5 ^ (settled ÷ halves))`. `settled` is how many of the member's conversations have **ended** in this tone since it was rolled, set or moved; it goes up by one when a new conversation opens at least 30 minutes after the last one began. |
| Any move un-settles it | A drift step, a feedback move, a Reroll and a Set tone all put `settled` and `heard` back to 0. |
| Real feedback moves it | See *Feedback* below. One move per member per conversation. |
| A pin holds | A pinned member is never drifted, never settled and never moved by feedback; the stored tone underneath is kept and is what **Unpin** hands them back to. |
| A stored tone that is switched off | is rolled again from the tones that are on, at the member's next answer (`how = rolled`). The roster shows `cookout` for them until then. |

`chat_voice.trope` is still what was LAST HEARD (a pin or a named mood writes it); `chat_voice.tone` is the member's
own. The two differ exactly when a pin or a named mood is in force.

### The keys (all `chat`, Settings page ▸ chat, Chat ▸ Who hears what ▸ *How a tone settles and moves*, `/settings`)

| Key | Default | Bounds | What |
|---|---|---|---|
| `chat_tone_drift_start_percent` | **25** (the manifest's `drift.chance` × 100) | 0–100 | the chance of a step while a tone is new; 0 = never moves on its own |
| `chat_tone_drift_halves_every` | **4** conversations | 0–1000 | how many conversations halve that chance; 0 = never settles |
| `chat_tone_drift_floor_percent` | **2** | 0–100 | the lowest the chance gets; 0 = a settled tone stops moving |
| `chat_tone_feedback_mode` | **on** | off / on | whether a member's words may move their tone at all |
| `chat_tone_feedback_cues` | 28 words and phrases (`tone_keys.FEEDBACK_CUES`) | may be blank | the free pre-filter: only a message with one of them is judged |
| `chat_tone_feedback_minutes` | **5** | 0–30 | how long after an answer the member's next words in that channel may be judged; a Discord reply to the answer counts for 30 minutes regardless |
| `chat_tone_gentle_order` | `warm, cozy, shy, peppy, scholar, dramatic, flirty, noir, deadpan, mischievous, tsundere` | known tones only, may be blank | gentlest → sharpest |
| `chat_tone_careful_order` | `scholar, shy, warm, cozy, deadpan, noir, peppy, flirty, tsundere, mischievous, dramatic` | known tones only, may be blank | most careful → least |

Plus **23 word keys** (`tone_keys.TONE_WORDS`): every sentence, button, placeholder and state word either door says —
`chat_voice_rerolled`, `_tone_set`, `_is_pinned`, `_no_tones`, `_no_role`, `_role_rolled`, `_role_line`,
`_role_pinned_line`, `_role_placeholder`, `_role_title`, `_role_only_button`, `_role_everyone_button`,
`_reroll_button`, `_start_placeholder`, `_line_stored`, `_state_rolled|set|drifted|feedback|pinned`,
`_settled_new|settling|settled`. **31 keys in all: the registry is 737 → 768**, the chat group 128 → 159.
Two shipped defaults changed: `chat_voice_cleared` (it said the tone "is rolled again", which is no longer true) and
`chat_voice_tone_placeholder` (now the PIN picker's placeholder, *Pin… (fix {member}'s tone)*).

**Worked numbers at the defaults** (measured, `chat_voice.drift_chance`): a new tone **25 %**; after 4 quiet
conversations **12.5 %**; after 8 **6.25 %**; after 12 **3.1 %**; from 15 on **2 %**, the floor. The meter on the page
is 0 at 25 % and full at the floor; the word is *new* under half way, *settling* from half way (4 conversations at the
defaults), *settled* at the floor (15).

### The two orders, and why

The shared manifest has a graph, not an order, and its two clusters barely touch (`scholar/noir/deadpan` reach the
rest only through `tsundere`), so "gentler" is defined in Black Bloc as an ordered list and a step is **the nearest
tone earlier in the list that is switched on** — along the list, NOT along the graph (Deviation 2).

- **Gentle**, read off each tone's own body in `personas.VOICES`: `warm` ("kind… you notice how they are") and `cozy`
  ("calm") are the soft end; `shy` is soft but hedging; `peppy` is loud but kind; `scholar` is "pedantic about
  accuracy"; `dramatic` is big; `flirty` carries "affectionate teasing"; `noir` is "world-weary"; `deadpan` is "flat";
  `mischievous` is "light teasing"; `tsundere` grumbles — the one most likely to read as actually rude.
- **Careful**: `scholar` ("cannot let an imprecision pass") is the careful end, then `shy` (hedging, apologetic), the
  plain kind pair, the few-words pair, and last the tones whose bit is confidence or play (`dramatic` makes "grand
  pronouncements about small things").

Both are the build agent's reading, not the owner's; they are keys so he can reorder them.

### Feedback — how a complaint is detected, and what it costs

**Not the review tagger.** The tagger (`chat_review.tag_one`) is handed the member's question and the bot's answer; it
never sees the member's NEXT message, which is the one that says "that was rude". So the second route of the brief was
taken: `black_bloc/chat_feedback.py`.

1. The cog keeps, in memory, the last **model** answer each member got (a written line is never kept).
2. The member's later message is weighed when it is a Discord reply to that answer (for 30 minutes), or is in the same
   channel within `chat_tone_feedback_minutes`.
3. **Free, local:** it must contain one of `chat_tone_feedback_cues` (matched the way the review loop matches phrases).
   No cue → nothing else happens. The server must be on `pool`, the member must have a stored tone, and this
   conversation must not already have had its one verdict.
4. **One call to the quick model** (`chat_simple_model`, Groq, ledger tier `feedback`, JSON only) with the bot's answer
   and the member's message, each clipped to 500 characters. It must answer
   `{"reaction": "none"|"mean"|"wrong", "genuine": true|false, "cue": "<their words or null>"}`.
   `parse_verdict` is strict: not JSON, an unknown reaction, a `genuine` that is not a real boolean, or a non-string
   cue → no verdict, a warning in the log, nothing moved. `genuine: false` (banter) moves nothing.
5. `mean` → one step toward the front of `chat_tone_gentle_order`; `wrong` → one step toward the front of
   `chat_tone_careful_order`. `settled` and `heard` go to 0, `how = feedback`, `moved_at/from/why` are written, and a
   `chat.voice_feedback` row carries member, from, to, why, the cue words and the message id.
6. **Held, and said so** (`chat.voice_feedback_held`, `held: pinned | no_step`): a pinned member, or no gentler / more
   careful tone switched on. Either way it counts as this conversation's one verdict.

**Cost per message:** nothing for a message with no cue word (no model call, no ledger row). A cue-matched follow-up
costs one Groq call — priced **$0** in `llm.PRICES` today (`llama-3.3-70b-versatile`, `openai/gpt-oss-120b`), a few hundred
input tokens (a 969-character instruction plus two messages of at most 500 characters each; estimated, not measured)
— and one turn toward `chat_daily_turns`. At most
**2** messages are judged after one answer (`JUDGED_PER_ANSWER`, a constant) and at most one MOVE per conversation.
**The caps hold:** no Groq key, the month at `chat_monthly_cap_usd`, or the day at `chat_daily_turns` → nothing is
judged and nothing is adjusted, logged ONCE per closing (`chat feedback: nothing is judged in <guild> for now
(<why>)`), not per message. The judging prompt is code (`JUDGE_SYSTEM`), like the tagger's, and for the same reason.

**Privacy:** nothing of the member's message is stored except the model's `cue` (≤ 80 characters) on the action row,
and not even that for a member the `/memory` consent says is not remembered (`chat_review.keeps_text`, tested).
A `wrong` complaint still reaches the review queue exactly as before (`not_it` / `reask`); this build changed nothing
there.

### Reroll and Pin — two moves, both doors

One write path: `black_bloc/chat_tones.py` — `reroll_voice`, `start_voice`, `roll_role` — beside the existing
`chat_panel.pin_voice` / `clear_voice`. Kinds (all ROUTINE, `web.` from the site): `chat.voice_rerolled`,
`chat.voice_set`, `chat.voice_role_rolled`; the bot's own `chat.voice_drifted`, `chat.voice_feedback`,
`chat.voice_feedback_held`.

| Move | Site | Discord (`/chat` ▸ Personality… ▸ Who hears what…) | Route | Refused |
|---|---|---|---|---|
| **Reroll** | row button | button on the member's card | `POST /api/chat/voices/{id}/reroll` | pinned → 409 `voice_is_pinned`; no tone on → 409 `no_tones_on`; not a member → 404 |
| **Set tone…** | row button → a tone dialog | the first picker on the member's card | `PUT /api/chat/voices/{id}/tone` `{trope}` | the same, plus an unknown / switched-off tone → 422 |
| **Pin…** / **Unpin** | row buttons | the second picker / *Clear the pin* | `PUT` / `DELETE /api/chat/voices/{id}` (unchanged) | as before |
| **Roll for a role…** | button on the section → role + *Only members with no tone* (default) / *Everyone in it* | a role picker on the list → a card with the two buttons | `POST /api/chat/voices/roll` `{role_id, everyone}` | role gone → 404; no tone on → 409 |

A reroll never lands on the tone the member already has while another one is on. Roll for a role skips bots, leaves
pinned members alone and lists them, and (by default) leaves members who already have a tone. On Discord a move renders
only where it is valid: Reroll and the starting-tone picker are absent on a pinned member, *Clear the pin* only on one,
and no picker at all while every tone is off. The page's row shows the tone, how it got there as a word (+ who / how
long ago), a small meter with *new / settling / settled*, and the moves.

### Storage (schema 87)

`chat_voice` gains nine columns, all additive (`ADDED_COLUMNS`): `tone`, `how` (`rolled|set|drifted|feedback`),
`settled`, `heard`, `set_by`, `moved_at`, `moved_from`, `moved_why`, `fed_since`. A row from before has none of them
set; `_store_the_tones` (runs ONCE, on the boot that finds a stored schema under 87) copies `trope` into `tone`
(`how = rolled`) for every row whose `trope` is a tone — a row whose `trope` is `cookout` or NULL has no stored tone
and gets one rolled at its next pool answer.

### The nine placeholder pins

In that same one-time step — **a migration step, not a boot routine**, because it must run exactly once: staff may pin
one of the nine again, on the same UTC day, after the deploy, and a boot routine would undo it at the next restart
(tested: a re-pin after the first connect survives the second) — every row with a pin, a `pinned_at` on
**2026-10-05 UTC** and a `user_id` among the nine listed in `db.py:PLACEHOLDER_PINNED` becomes a starting tone:
`tone = pinned`, `how = set`, `set_by = pinned_by`, `moved_at = pinned_at`, `settled = 0`, `since` cleared, and the pin
cleared. The row reads *set by staff* on both doors. Any other pin — an older one, one made on 10-06, one on a member
not in the list even if made that day — is left alone. The boot log says `database: N pin(s) of 2026-10-05 are
starting tones now`. ⚠️ "By the owner" is not checked from `pinned_by`: the build did not know which id the session's
pins were written under, so the rule is the nine ids AND the day (Deviation 5).

### Deviations

1. **The feedback verdict is its own cheap call, not an extension of the review tagger** — the tagger does not see the
   follow-up message. The brief allowed either.
2. **A feedback step goes along the staff-editable order, skipping tones that are off**, not to a graph neighbour. The
   brief's "if no gentler neighbour is enabled" is read as "no gentler tone in the order is on".
3. **Drift is weighed every 4 answers heard in the tone, across conversations**, not every 4 turns inside one. With a
   stored tone the old cadence would never fire for a member whose conversations are shorter than four answers.
4. **Percent keys, not fractions** — the registry has no float type.
5. **The nine pins are matched by id and day**, not by who pinned them.
6. **A new module `tone_keys.py` holds the 31 keys' data**; `settings_store.py` registers them in one block, so the
   parallel `memory-rapport` build and this one touch few of the same lines. Likewise `chat_tones.py` (staff moves)
   and `chat_feedback.py` (the feedback move) rather than more lines in `chat_panel.py` / `chat_review.py`.
7. **`chat_llm.mood_for` gained the settle numbers and one log call** (`tone_drifted`) — a file the brief did not name.
8. **A reroll or Set tone on a pinned member is refused in words** (409) rather than silently changing the tone under
   the pin; staff unpin first. The buttons are not drawn there.
9. **One more behaviour key than the brief listed**: `chat_tone_feedback_minutes`.
10. **The mock's `chat_personality` is `pool`** (was `cookout`), so the section shows states on the local mock; its
    default is still `cookout`. The page's *pinned tone is switched off* badge now reads *pin is off* (the full
    sentence is its tooltip) so the table fits at 1280 without scrolling sideways inside its frame.
11. **Three older words were left alone** (`chat_voice_intro`, `chat_voice_empty`, `chat_voice_line_waiting`) —
    the last still says "the setting decides for now", which under `pool` now means the member's own tone.

### Not verified

- **No live model.** Whether Groq's model tells banter from a real complaint is NOT measured: every verdict in the
  tests is a faked model answer. The first real `chat.voice_feedback` rows should be read by a person (sweep `TS-g`).
- **No live Discord:** the member card's two pickers and Reroll, the role picker and its card were driven with the
  test fakes only. Discord's `RoleSelect` with a real role cache was not seen.
- **No live database:** the 86 → 87 step ran on test files only (a schema-86 file made from the current schema with
  the nine columns dropped). The live nine rows, and whose id is in `pinned_by`, were not read.
- **The cue list** was written, not measured against real messages; it may be too wide or too narrow.
- **The in-memory "last answer"** is lost on a restart, like the review loop's — a complaint about an answer from
  before a restart is not seen.
- **A DM** has no stored tone (unchanged: the per-conversation roll) and is never judged.
- **The mock** rolls for the eight named members only; a role's real size was not exercised in a browser.
