# Personality tones — the cookout is the voice, every mood is a tone on it, and the tone follows the person

> **Audience:** Claude sessions and the owner. **Status:** TRACKED — **BUILT, NOT MERGED, NOT DEPLOYED**
> (branch `personality-tones`, worktree `C:/lcw/bb-personality-tones`, off `main` `083ca538`; built 2026-09-23
> by an Opus build agent from the conductor's brief). Secret NAMES only.
> **Last verified: 2026-09-23** — ruff clean, the full pytest suite green from the worktree, `node site/mock/check.mjs`
> ok against a mock on a private port, and `page-chat.js` loads as an ES module. ⚠️ **Nothing here has met live
> Discord, a live model or a browser** — see *Not verified* at the foot.

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
   line template either door says). The chat settings group is **66**, so `/settings` ▸ chat reads *25 of 66*; the
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
- **Not deployed; no migration run** — schema 55 is additive (one table, three nullable columns).
