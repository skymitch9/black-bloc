# Chat memory — `/memory` is ONE command that opens a panel (wave 2)

> **Audience:** the build agent and the reviewer, then the owner for §I. **Status:** TRACKED ·
> ✅ **SHIPPED 2026-09-03 — v68 `cb941d9` 16:48** (built on `worktree-agent-aaaa13e778f0ba65a`, base
> `main` `8cbe453`, merged `cb941d9`; landing entry in `DONE.md`). Fork **I-M1 = OPEN IT** (owner, 2026-09-03 16:12), built as decided. The
> `## Deviations` foot names every place the build departed from this document.
> **Measured on the branch:** ruff clean · **3744 tests pass** (3710 at the base, +34, none
> lost) · `commands synced` **42, UNCHANGED** (measured through the real tree, not booted —
> no bot token here) · the five-module import check passes · `node site/mock/check.mjs` still
> reports **17 pages / 142 routes** · `labels.js` parses.
> ⚠️ **NOT verified: anything a person sees.** No panel has been opened in Discord and no
> sweep row (104–108) has been run.
>
> **Last verified: 2026-09-03** — every `path:line` below was READ against `main` as it stands
> after the applications panel merged (`1735ff8`, v66, `commands synced` **42**), in
> `black_bloc/{chat_memory,panels,settings_store,command_visibility,personas,actionlog,logkinds}.py`,
> `cogs/content/chat_memory.py`, `api/tools/chat_memory.py`, `tests/{test_bot,test_command_visibility}.py`,
> `site/mock/server.mjs`, `site/public/assets/labels.js`, `docs/access/sweeps.md` and
> `docs/info/code-notes.md`. The import cycle in §F was measured by reading the import blocks of
> all four modules, not guessed.
> ⚠️ **NOT verified: anything run.** No boot, no pytest, no ruff, no `check.mjs`, nothing against
> live Discord. The 25-option select cap is Discord's documented limit, not measured here.
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md),
> whose `## Deviations` foot is the trap list; the recent siblings are
> [`applications-panel-design.md`](applications-panel-design.md) and
> [`events-panel-design.md`](events-panel-design.md). Feature behaviour — the five privacy
> decisions D1–D5 and the §D2-definition rules — is [`phase17-design.md`](phase17-design.md);
> **this design undoes none of them.**

## A. Measured today — one group, five subcommands, member-only

`memory` is an `app_commands.Group` (`cogs/content/chat_memory.py:103`, **member-visible**, no
`default_permissions`) with five leaf subcommands over **one** top-level slot.

| Subcommand | Line | What it calls · what is INLINE in the cog |
|---|---|---|
| `/memory show` | `:150` | `ready` `:119` → `remembers` (`chat_memory.py:736`) → `profile_for` `:649`; ⚠️ **lines built inline** by `profile_words` `:88` |
| `/memory forget` | `:165` | `forget` `:689`; ⚠️ **inline** `:171–175`: the sentence + `noted(FORGOT_KIND, {"who_asked": BY_SELF})` `:142` |
| `/memory forget-this <words>` | `:177` | ⚠️ **inline** `:184–202`: the 200-char clamp, `profile_for`, `drop_matching` `:619`, `save_profile` `:662`, the sentence, one log row with `{"who_asked": …, "lines": n}` |
| `/memory off` | `:204` | ⚠️ **inline** `:210–217`: `remembers` → `set_remembered(wanted=False)` `:766` → `forget` → sentence → `OPTOUT_KIND`. **Opts out AND wipes**, in that order (D1) |
| `/memory on` | `:219` | ⚠️ **inline** `:226–231`: `set_remembered(wanted=True)` → sentence → `OPTIN_KIND` |

**Not a subcommand and not moving:** `on_member_remove` `:233` (D3, `forget_everywhere` `:702`)
and the whole distillation path (`chat_distil.py`). There is **no persistent post** for this
feature at all, so P14 has nothing to say here.

**There are no staff moves in this cog.** Staff read profiles on the site
(`api/tools/chat_memory.py`, gated by `chat_memory_staff_view`, D5 default `counts`), and
`/memory` has never had a `logs` subcommand — the kinds are `chat.memory_*`, so `/chat logs` and
the Chat page own them. **The panel is mine-only and adds no staff row** (§2: the site owns staff
views). `LOGS_GROUPS` (`tests/test_bot.py:11`) correctly has no `memory` entry. `ready` `:119`
gives three refusals, each its own sentence: `NO_SERVER` `:38`, `DB_UNAVAILABLE`, `MEMORY_IS_OFF`
`:34`.

**The state, measured** — no status machine; the panel's state is three reads: the mode
(`store.get(home, MODE_KEY)` `:129`), whether I am remembered (`remembers(...)` `:156`, against
`chat_memory_consent` `:139`), and the `Profile` itself (`profile_for` `:159` → `chat_memory.py:376`
— `call_me`, `notes`, `threads`, each note carrying `where: dm|server`).

## B. The decision — one `/memory`, one panel, ephemeral and mine only

`memory` becomes a single `@app_commands.command(name="memory", description="What Black Bloc
remembers about you")`; the Group `:103` goes. ⚠️ **`commands synced` does NOT move** — a group
already counted as one top-level slot (requests deviation 7), so `tests/test_bot.py:198`
(`assert len(top) == 42`) is **unchanged by this feature**. Other wave-2 features each drop one;
the conductor reconciles the number at merge. `"memory"` stays in `MEMBER_COMMANDS`
(`tests/test_bot.py:63`) and no `default_permissions` is added.

**Privacy is the shape of this panel.** The message is ephemeral, so the facts are visible only
to the caller — the same guarantee `/memory show` gives today, and what makes a profile card safe
to render at all. Everything below follows: no staff row, no fact text in any log row (§C), and
no `Open on the site` button, **because the site's Memory section is staff-only and counts-only
(D5) — a member following that link would meet a 403** (P9).

**Embed** *What Black Bloc remembers about you* — `HEADER` `:50` ("Nobody else can read this."),
then the caller's facts as **numbered** lines (`CALL_ME_LINE` `:51`, `NOTE_LINE` `:52`,
`THREAD_LINE` `:53`, each keeping `scope_mark` `:84`'s `DM_MARK`), then one state line:

| State | The line |
|---|---|
| nothing stored | `NOTHING_YET` `:42` |
| not being remembered | `YOU_ARE_OPTED_OUT` `:46`, reworded off the retired `/memory on` |
| the feature is off here | `MEMORY_IS_OFF` `:34` as a LINE, never a whole-command refusal (requests deviation 3) — see fork **I-M1** |

`SHOW_FOOT` `:55` is **deleted**: it exists to tell people which three subcommands to type, and
the buttons are now the answer.

## C. The buttons — the table IS the design (P3), and the one modal

Six states over two axes; the mode is a LINE, not a branch, because a person's own choices stay
theirs whether or not the server is writing anything down. `N` = `len(facts_of(profile))`.

| Remembering me | N | Row 0 (select) | Row 1 (buttons) |
|---|---|---|---|
| yes | 0 | — | `Stop remembering me` (danger) · `Refresh` |
| yes | 1–25 | `Forget one of these…` | `Forget everything` (danger) · `Stop remembering me` (danger) · `Refresh` |
| yes | >25 | `Forget one of these…`, first 25, `capped_placeholder` (`panels.py:56`) | `Forget everything` · `Forget by words…` · `Stop remembering me` · `Refresh` |
| no | 0 | — | `Remember me again` (success) · `Refresh` |
| no | ≥1 | `Forget one of these…` | `Forget everything` (danger) · `Remember me again` · `Refresh` |

⚠️ **"Opted out with facts still stored" is REACHABLE and must render** — `/memory off` wipes,
but a Lead flipping `chat_memory_consent` from `optout` to `optin` re-reads every existing row
the other way round (`remembered` `chat_memory.py:715`), leaving people not-remembered with a
profile still on disk. The forget controls render from `N`, never from the consent state.

⚠️ **The capped placeholder cannot say "the rest are on the site"** — `panels.CAPPED_PLACEHOLDER`
(`panels.py:14`) is exactly that sentence, and for this feature it is false (D5). Pass the
`capped=` override: *"25 of {total} — Forget by words… reaches the rest"*. `capped_placeholder`
takes that argument for this reason.

⚠️ **`panels.SELECT_OPTION_LIMIT` (`panels.py:15`) is 100 and is the option LABEL's character
cap, not the option count.** The 25 is Discord's per-select maximum and is no constant in this
repo. Use `option_label` (`panels.py:64`) for the label and a plain `[:25]` for the count.
`N > 25` needs `chat_memory_notes_max` + `chat_memory_threads_max` raised far above their
defaults (6 + 5 = at most 12 facts today; the ceilings are 20 + 20, so 41 is the maximum) — rare,
but reachable, and a member with no site door must not be locked out of their own data.

**Confirms.** `Forget everything` and `Stop remembering me` are irreversible, so each re-renders
the panel with `Yes, forget it all` / `Yes, stop` (danger) + `Keep it` — the birthdays and
applications precedent. Dropping ONE line does not confirm: it is one line, and `/memory
forget-this` never confirmed either.

**The one modal.** `Forget by words…` opens `panels.NoteModal(title="Forget by words",
label="A few words from the line you want dropped", max_length=WORDS_LIMIT (200),
required=True)` and calls the same `drop_matching` `:619` the subcommand did, so `/memory
forget-this`'s behaviour survives verbatim. **It renders only when the select is capped** —
rendering it always would be two spellings of one move, which P3 forbids. No other modal exists;
the select replaced the typed words everywhere else.

**Every click re-reads the profile and re-renders from what it finds:** `defer()` → `db_ready`
(`panels.py:46`) → read → move → `retire(previous)` → `edit_original_response` (P5, P6, requests
deviation 6). ⚠️ **A select option identifies a fact by KIND + INDEX and a distillation can land
between render and click** — so the handler compares the fact it re-reads against the one the view
rendered and, when they differ, re-renders saying the profile changed rather than dropping the
wrong line. `still_staff` (`panels.py:29`) is **unused here**: no staff move to re-check, and an
ephemeral message admits no other clicker.

**What each move logs — one write, one row, and never the text** (checklist 34):

| Move | Kind | Details |
|---|---|---|
| `Forget everything` | `chat.memory_forgot` | `{"who_asked": "self", "via": …}` |
| `Forget one of these…` / `Forget by words…` | `chat.memory_forgot` | `{"who_asked": "self", "lines": n, "via": …}` |
| `Stop remembering me` | `chat.memory_optout` | `{"via": …}` — the wipe it performs is part of the same move and does **not** log a second row (today's behaviour, `:204–217`) |
| `Remember me again` | `chat.memory_optin` | `{"via": …}` |

⚠️ **No log row, error message or refusal may carry a fact's TEXT.** The action log is
staff-readable and D5 says the contents are the member's alone; today's rows carry a COUNT and
nothing else (`:201`), and `Distilled.dropped` carries rule names rather than text for the same
reason. This is the item the build can fail silently: assert it.

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `memory_panel_minutes` | `int` | **10** | **NEW** — the only decision the panel introduces. Registered in its own appended block at the foot of the registry (after the polls block, `settings_store.py:987`) plus `KEY_HELP` and a `default()` branch, so wave-2 branches merge textually. Help text carries KI-20's warning in the shape the other five `*_panel_minutes` keys use verbatim |

**Existing keys it READS and never writes:** `chat_memory_mode` (`MODE_KEY`) and
`chat_memory_consent` (`CONSENT_KEY`). It does not read `chat_memory_notes_max` /
`_threads_max` / `_retention_days` / `_dm_scope` / `_staff_view` / `_model` — those govern
distillation and the site, and the panel renders whatever the profile actually holds.

⚠️ **"A member can always reach their own delete controls" is NOT made a key**, and that is
deliberate: phase 17 §D2-definition settles the shape — *"rules 1–7 are code and prompt, not
settings — there is no dial that turns quotes back on"*. A dial that lets a Lead take away
somebody's ability to delete what is stored about them is the same class of dial. Checklist 33
governs decisions the server may reasonably differ on; a privacy floor is not one.

**Also needed for the key to be usable, both ways:** `site/public/assets/labels.js` gains
`memory_panel_minutes: 'How long the /memory panel stays live'` beside `:168`. (⚠️ Finding, not
this build's job: `request_`/`event_`/`poll_`/`birthday_panel_minutes` have **no** `labels.js`
entry at all — only `applications_panel_minutes` `:168` does.)

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit — and it names nothing here
today (measured: zero matches for "memory" in that file). P15.

| Thing | Where | Becomes |
|---|---|---|
| the `memory` Group | `cogs/content/chat_memory.py:103` | `@app_commands.command(name="memory")` |
| `show` · `forget` · `forget-this` · `off` · `on` | `:150` `:165` `:177` `:204` `:219` | the embed, the buttons, the select, the one modal |
| `SHOW_FOOT` | `:55` | **deleted** — the buttons say it |
| `assert len(top) == 42` | `tests/test_bot.py:198` | **unchanged** (§B) |
| `LOGS_GROUPS` / `STAFF_COMMANDS` / `MEMBER_COMMANDS` | `tests/test_bot.py:11` `:27` `:63` | **unchanged** — no `memory` logs group exists, `"memory"` stays a member command |
| `HIDDEN_WHEN_OFF["chat_memory_mode"] = ("memory",)` | `command_visibility.py:19` | fork **I-M1** — kept as-is (the command name does not change), or dropped |

**Strings that name a retired subcommand, rewritten in the SAME commit** — each tells somebody to
type something that will not exist: `cogs/content/chat_memory.py:46` `:55–57` (deleted) `:61`
`:62–65` `:67–69` `:71–74` `:76–79` (kept — it is the empty-modal refusal now) `:178` (the
`describe`, deleted with the parameter); `api/tools/chat_memory.py:37` ("…read their own with
`/memory show`" → "`/memory`"); `black_bloc/personas.py:90–91` (⚠️ **the chat bot's own answer to
"does the bot remember me?"**, naming four subcommands); `site/mock/server.mjs:4225`
(`MEMORY_IS_PRIVATE`, the copy of that string).
⚠️ **Already wrong before this build, fix while here:** `settings_store.py:688–689` and `:702`
say `/chat memory off` / `on` / `show` — a command that has never existed (phase 17 deviation 1
moved it to `/memory`) — while their byte-copies at `site/mock/server.mjs:379` `:382` say
`/memory`. The pair is already out of sync; make both name the panel.

**Docs rewritten in the same commit** (P15): `docs/KNOWN_ISSUES.md:53–54` (KI-14 names `/memory
show` and `/memory forget-this` as its residual-risk mitigation — the mitigation is unchanged,
the wording is the panel's); `docs/info/feature-list.md:48` (lists the five subcommands);
`docs/info/phase17-design.md` gets a dated "superseded by the panel" line at the TOP, not a
rewrite (§D `:168–171`, deviation 1 `:288–297`, deviation 2 `:298–303`);
`docs/info/panels-program.md:83` (the Chat memory row → shipped); `docs/access/sweeps.md` gains
§H's rows; `docs/access/OWNER_GUIDE.md` names memory nowhere (measured) — only its sweeps count
(`:17`, `:71`) moves; `docs/info/code-notes.md` re-keyed at the merge, specifically the
`## black_bloc/cogs/content/chat_memory.py — /memory` section `:4729–4739` (its `:4733` group
note and `:4734` visibility note are the two that change meaning) and `:4711` (`drop_matching`,
which now has a modal caller rather than a subcommand one).

## F. Extractions (P4) — and the ONE import rule that governs where they go

⚠️ **`black_bloc/chat_memory.py` is imported BY `settings_store.py:18` for its choice tuples.**
It therefore may NOT import `settings_store`, `actionlog` (which imports `settings_store:25`),
`panels` (which imports `settings_store:10`) or `chat` at module level — `normalise`
`chat_memory.py:278` already late-imports for exactly this reason, and `code-notes.md:4698`
records it. **So the move layer lives in the COG at module level**, as it does for applications
and events, and `api/tools/chat_memory.py` imports from the cog (the precedent is
`api/tools/applications.py:10`). Getting this backwards is an import error at boot, which is
what §H item 3 exists to catch.

**Pure, into `black_bloc/chat_memory.py`** (no new imports — these touch only `Profile` and
`Note`):

| New | Signature · why |
|---|---|
| `FACT_KINDS = ("name", "note", "thread")` · `Fact(kind, index, text, where)` | one identity for a thing the person can point at; `name` is `call_me`, which `drop_matching` `:626` can already clear |
| `facts_of(profile) -> tuple[Fact, ...]` | name first, then notes, then threads — the order `profile_words` `:88` already prints |
| `fact_key(fact) -> str` / `fact_at(profile, key) -> Fact \| None` | `"note:2"`; `fact_at` returns `None` when the profile moved under the click (§C) |
| `drop_fact(profile, key) -> tuple[Profile, int]` | exactly one fact, by identity. ⚠️ **`drop_matching` `:619` is the wrong instrument for a select** — it drops every fact whose normalised text CONTAINS the words, which is right for typed words and wrong for a picked line. Both exist; neither replaces the other |

**Module level in `cogs/content/chat_memory.py`** — each does ONE write and ONE log row, each
takes keyword-only `via: str = VIA_DISCORD` and builds its kind with `logkinds.kind_via`
(checklist 34), each returns the sentence plus the fresh profile:

| Function | Replaces |
|---|---|
| `forget_profile(bot, guild, target, actor, *, who_asked=BY_SELF, via)` | inline `:171–175` **and** the route's `forget` + `note()` (`api/tools/chat_memory.py:130`, `:132–139`). `kind_via(FORGOT_KIND, VIA_WEBSITE)` produces exactly the `f"web.{FORGOT_KIND}"` the route hand-builds today, so this is textually safe and deletes one `note()` — the same move requests deviation 8 made. ⚠️ The route's row gains `details["via"]`; check `tests/api/tools/test_chat_memory.py` for an exact-dict assertion |
| `drop_one_fact(bot, guild, member, home, profile, key, *, via)` | the tail of `:188–202`, over `drop_fact` |
| `drop_by_words(bot, guild, member, home, profile, words, *, via)` | `:184–202` verbatim, over `drop_matching` — the modal's path |
| `stop_remembering(bot, guild, member, home, *, via)` | inline `:210–217`, order preserved (opt out, then wipe — `code-notes.md:4738` says why) |
| `start_remembering(bot, guild, member, home, *, via)` | inline `:226–231` |
| `MemoryMove` NamedTuple + `PANEL_MOVES` + `moves_for(*, remembered, facts)` | §C's table AS DATA, parametrised test against it |
| `profile_words(profile) -> list[str]` | **stays in the cog**, rewritten: numbered lines, no `SHOW_FOOT`. Keeping the name keeps `code-notes.md:4737` (which calls it "the enforcement mechanism for rule 7") and `__all__` `:258` valid |

`ready` `:119`, `home` `:107`, `usable_db` `:115`, `consent` `:139` and `noted` `:142` stay as
they are; `say` `:134` is replaced by `panels.answer` (`panels.py:18`) — ⚠️ it is a fourth
byte-for-byte copy of it (checklist 15/17).

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/content/test_chat_memory.py` (358 today) | `/memory` answers ephemerally with one panel; **parametrised over every row of §C's table — exactly those controls and no others**; the opted-out-with-facts row renders the forget controls; nothing stored renders no select and no Forget everything; the mode being off renders the LINE (per I-M1) and never a dead button; both confirms (Keep it changes nothing, Yes writes once); the select caps at 25 and its placeholder does **not** say "on the site"; `Forget by words…` is absent below the cap and present above it; a fact that moved between render and click re-renders instead of dropping the wrong line; each move calls its `§F` function with `via` untouched (mock it); **no log row carries fact text** (assert the details dict, not just the kind); `db_ready` after a defer; timeout disables every item and writes the footer; a re-render `retire`s the view it replaced; `NO_SERVER` and `DB_UNAVAILABLE` still answer in words with no panel |
| `tests/test_chat_memory.py` (361) | `facts_of` ordering and DM marks; `fact_key`/`fact_at` round-trip; `fact_at` returns `None` for a stale key; `drop_fact` drops exactly one and leaves the rest, including `call_me`; `drop_matching`'s existing tests **stay green untouched** — that is the proof this build changed nothing about it |
| `tests/api/tools/test_chat_memory.py` (147) | `DELETE /api/chat/memory/{id}` answers the same shape and leaves **one** `web.chat.memory_forgot` row (assert the COUNT, not just the kind) |
| `tests/test_settings_store.py` | `memory_panel_minutes` round-trips, defaults 10, has help text; the eight `chat_memory_*` keys unchanged |
| `tests/test_bot.py` | `len(top)` still 42; `"memory"` still in `MEMBER_COMMANDS`; no `LOGS_GROUPS` entry appears |
| `tests/test_command_visibility.py:229–236` | per fork I-M1 — either unchanged, or rewritten to assert the entry is gone |
| `tests/test_personas.py` | the member-command block still names `/memory`, in the panel's words |

The distillation tests (`tests/test_chat_distil.py`, `tests/cogs/content/test_chat.py`) must stay
green **untouched**: this build does not go near the write path.

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; read `commands synced` and record it. **Expect 42, UNCHANGED** —
   measure it, never assert it (requests deviation 7). If no token is available, measure through
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, as wave 1 did.
2. The parametrised state test: every row of §C renders exactly its controls and no others.
3. `python -c "import black_bloc.chat_memory, black_bloc.cogs.content.chat_memory,
   black_bloc.api.tools.chat_memory, black_bloc.settings_store, black_bloc.personas"` — ⚠️ **this
   is the check that proves §F's cycle rule was obeyed**, and it is what a boot would catch.
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (expect **17 pages / 142 routes**, unchanged
   — this design adds no route); `node --input-type=module --check < site/public/assets/labels.js`
   (⚠️ that file failed to parse once before — `code-notes.md:5008`).
5. Checklist sweep before reporting — **8** (`AnswersErrors` on the view and the modal, both from
   the library), **11** (`allowed_mentions` on every send: a `call_me` is attacker-supplied text),
   **15**/**17** (`say` `:134` is a fourth copy of `panels.answer`), **30**, **33** (§D), **34**
   (the route dedup), plus the feature-specific one: **no fact text in a log row or a refusal**.
6. Test mode is unaffected — every response here is ephemeral, as `/memory show` already is.

**Sweep rows — this feature takes 104 onward (renumber at landing; 103 is taken).**

| # | Do this | Expect |
|---|---|---|
| 104 | `/memory` in `#mute-me-bot-test-spam` after a conversation or two | ONE ephemeral panel: *What Black Bloc remembers about you*, "Nobody else can read this", your lines NUMBERED (one learned in a DM marked as such), a **Forget one of these…** picker, **Forget everything**, **Stop remembering me**, **Refresh**. No Logs, no site link, nothing staff-shaped |
| 105 | **Forget one of these…** → pick line 2 | the panel re-renders with that line gone and the rest renumbered; the Chat log carries ONE `chat.memory_forgot` with `lines: 1` and **no trace of what the line said** |
| 106 | **Forget everything** → **Keep it**; then again → **Yes, forget it all** | Keep it changes nothing; Yes clears it, the panel re-renders saying nothing is written down and offers only **Stop remembering me** / **Refresh**; one log row |
| 107 | **Stop remembering me** → confirm, then **Remember me again** | the first wipes and opts out (`chat.memory_optout`), and the panel then offers **Remember me again** only; the second brings the writing back (`chat.memory_optin`) |
| 108 | Leave the panel alone for `memory_panel_minutes` (10) minutes; then `/settings set-value key:chat_memory_mode value:off` and try `/memory` again | every control greys out and the footer reads *This panel has gone quiet — run /memory again*. With the mode off, the answer is whichever way **I-M1** was decided — write the row to match what was built |

## I. The genuine fork — one, for the owner

Settled first, by the standing rules, so they are NOT put to him: the panel is member-only (D5
gives staff the site); `Stop remembering me` still wipes as well as opting out (D1); no fact text
reaches a log row (D5 + rule 7); the delete controls are not a settings key (§D). **The
staff-final-say rule has nothing to reverse here** — every stored decision on this panel is the
member's own, and staff already have the site's Forget button, which §F now routes through the
same function.

- ⚠️ **I-M1 — can a member reach their own memory while `chat_memory_mode` is OFF?**
  Today: no, twice over. `HIDDEN_WHEN_OFF["chat_memory_mode"] = ("memory",)`
  (`command_visibility.py:19`) takes `/memory` out of the tree within about five seconds of the
  switch flipping, and `ready` (`cogs/content/chat_memory.py:129`) refuses anyway. But turning the
  mode off **does not delete the profiles already stored** — `settings_store.py:685` says exactly
  that — so a Lead switching memory off leaves every member holding data they can no longer read
  or delete from Discord, and the site will not show it to them either (D5). **Recommended: drop
  the `HIDDEN_WHEN_OFF` entry and let the panel open**, saying `MEMORY_IS_OFF` as a LINE while the
  Forget controls keep working on what is already stored. That matches the owner's 2026-09-03
  answer for `/apply` (I-A2: "Visible") and P9. The alternative keeps today's vanishing act, which
  is tidier and costs a member the only door to their own data while the switch is off; if he
  picks it, `MEMORY_IS_OFF` still covers the seconds between a flip and the next sync. **Either
  way it is one line of code**, plus `tests/test_command_visibility.py:229–236` and sweep row 108.

## J. What NOT to build, and what it should cost

**Not in this build**, and each of these is a deliberate no rather than an omission:

- **No staff panel, no staff row, no "look somebody up".** D5 decided it; the site's Memory
  section is the staff surface and §2 says the panel does not duplicate it.
- **No `Logs` button** (`/memory` never had one, and a member may not read the action log) and
  **no `Open on the site` link** (staff-gated, it would 403 — P9).
- **No editing a fact.** Drop is the only verb: free-text profile editing is on phase 17's §I
  never-list, and a member typing their own "preference" bypasses every rule in §D2-definition.
- **No "write my profile up now" button.** Distillation is on the sweep and never on a person's
  click (phase 17 §C) — it costs money and it is the architecture of the feature.
- **No changes to distillation, the phrase lists, `parse_distilled`, the retention sweep, or
  KI-14's residual risk**, and no new schema. This build changes the door, not the room.
- **No second settings key** beyond `memory_panel_minutes`, and no touching the eight
  `chat_memory_*` keys. **No fixing the four wave-1 `*_panel_minutes` keys that lack `labels.js`
  entries** — reported in §D, not this build's job.

**Cost.** Wave-1 builds measured 376k–458k Opus tokens each, carrying staff panels, sub-panels,
form CRUD and a shared-layer move. This one is one panel, one select, one modal, no schema, no
site page, no staff surface — roughly 200 lines of production code over two files plus one route
edit. **Estimate 120–180k**, the test rewrite being the largest single piece. Past 250k means
something has been misread: stop and say so.

## Deviations

Written by the build agent, 2026-09-03. Everything not listed here was built as this document
says, including the decided fork **I-M1** (open it: `HIDDEN_WHEN_OFF["chat_memory_mode"]` is
gone and `MEMORY_IS_OFF` is a LINE).

1. ⚠️ **`Forget by words…` renders above the cap for an OPTED-OUT member too, which §C's table
   does not.** The table's last row lumps `no · ≥1` into one case with no `Forget by words…`;
   its PROSE says the modal "renders only when the select is capped". Built to the prose, because
   the table's reading locks an opted-out member with more than 25 stored facts out of the ones
   past #25 — the exact "no door to their own data" defect I-M1 exists to close, and reachable by
   the same `chat_memory_consent` flip that makes that row reachable at all. `moves_for` is
   therefore two independent questions (`facts` for the forget controls, `remembered` for the
   stop/start one) rather than six hard-coded rows, and the parametrised test asserts all six of
   §C's rows plus the missing seventh.
2. **`forget_profile` takes a keyword-only `home`; §F's signature has none.** Every other move
   function in §F's table carries `home` beside `guild`, and this one derives it from `guild.id`
   — which a DM does not have. The cog passes the `home` it already resolved and the route passes
   nothing, so the website's call is exactly the shape §F asks for. With `guild` `None` the write
   still happens and the log row is skipped, which is what the old `noted()` did.
3. **The move functions return `(sentence, fresh_profile)` as §F says, and every caller throws
   the profile away.** §C requires that every click re-reads and re-renders from what it finds,
   so `run_move` and `drop_picked` re-read rather than trusting the returned copy. The second
   element is kept because it is what a future non-Discord caller would want and because
   dropping it would have made the five signatures disagree.
4. ⚠️ **`db_up` was moved INTO `black_bloc/panels.py` and the applications cog now imports it,
   rather than a second copy being written here.** Applications deviation 15 added it as a
   private helper; this panel needs the same gate before its `Forget by words…` modal, and a
   second copy is checklist item 17's exact defect. `applications.db_up` is still importable by
   name, `__all__` still lists it, and every applications test passed unchanged. It has its own
   two tests in `tests/test_panels.py`. **This is the one file outside the feature that the
   build touched.**
5. **`PANEL_MINUTES_KEY`, `PANEL_TIMEOUT_FOOTER` and the panel's strings stayed in the COG**,
   where `requests.py`, `events.py`, `polls.py`, `birthdays.py` and `applications.py` all keep
   theirs in the PURE module instead. §F's cycle rule forbids it: `black_bloc/chat_memory.py`
   is imported by `settings_store.py`, so the minutes helper (which reads `panels.panel_minutes`)
   cannot live there. Only the four pure fact helpers moved into the module.
6. **The select's option labels are `option_label(number, kind_words, text)`**, giving
   `#1 · what it calls you · Sky`, `#2 · likes short answers`, `#3 · still open · was asking
   about it`. §C says to use `option_label`; it does not say what the `status` slot holds. A
   bare `#1 · Sky` would not have told anybody what `#1` was.
7. **The staleness check compares the fact's TEXT, and the rendered facts are held on the
   SELECT, not encoded in its value.** §C asks the handler to compare what it re-reads against
   what the view rendered; a select value caps at 100 characters and a note runs to 120, so the
   comparison could not travel in the value. `ForgetOnePick.shown` is a `{key: Fact}` map built
   at render time. Two tests cover it: a line whose text changed under the click, and a line
   that vanished.
8. **`HEADER` is now the bare sentence "Nobody else can read this." and the rest of it is the
   embed TITLE.** §B asks for the title *What Black Bloc remembers about you* and for `HEADER`
   under it; the old constant carried both, so keeping it whole would have printed the title
   twice.
9. **`SHOW_FOOT` is deleted as §E says, and eight further strings were rewritten** because each
   told somebody to type a command that no longer exists — a dead end inside the product is
   worse than a stale doc (P9, the same call events deviation 8 made): `YOU_ARE_OPTED_OUT`,
   `DROPPED`, `NO_MATCH`, `TURNED_OFF`, `TURNED_ON`, `FORGET_THIS_NEEDS_WORDS`, `MEMORY_IS_OFF`
   (rewritten as a panel LINE) and the `describe` that went with the deleted parameter.
   `PROFILE_MOVED` is new — deviation 7 needed a sentence.
10. ⚠️ **`MEMORY_IS_OFF` now says `/settings set-value key:chat_memory_mode value:on`, not
    `/settings set chat_memory_mode on`.** The old wording named `/settings set`, which takes a
    CHANNEL; a Lead following it would have been refused. **Finding, NOT fixed here:** the same
    wrong shape survives in `api/tools/chat_memory.py`'s `CONTENTS_ARE_PRIVATE` and its mock
    byte-copy (`/settings set chat_memory_staff_view full`), left alone to keep this build's
    diff to its own feature.
11. **`tests/test_logkinds.py`'s AST guard needed one edit.** Its
    `test_a_route_never_notes_an_event_its_shared_path_already_logged` asserted that exactly one
    computed `note()` kind was *unchecked* — `chat_memory.py::memory_forget::f'web.{FORGOT_KIND}'`
    — and §F's dedup deletes it. The list is now asserted EMPTY, which is strictly stronger: no
    route anywhere hand-builds a kind the walker cannot read.
12. **§H item 1 (a real boot reading `commands synced`) was NOT run** — no bot token here, the
    same as every wave-1 build. Measured the only other way:
    `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` counts
    `bot.tree.get_commands()` after loading every cog, which is what `command_sync.py` syncs —
    **42 before, 42 after**, and `/memory` is in the tree as a plain command rather than a
    `Group`. §H items 2, 3 and 4 were all run and pass, including `check.mjs` (17 pages / 142
    routes, unchanged — this build adds no route) and the `labels.js` parse.
13. **Sweep rows 104–108 were written to match what was built**, with row 108 saying the panel
    still opens with the mode off (I-M1). ⚠️ The `sweeps.md` header warns that a sibling wave-2
    branch may have claimed 104+ too; nothing outside that file points at these numbers, so the
    conductor can renumber the block freely.
14. **Every `edit_original_response` carries `allowed_mentions=none()`, which the wave-1 panels'
    edits do not.** The build brief asks for it on every send AND edit; a `call_me` is text the
    member chose and it is rendered into an embed on every re-render. Discord does not ping from
    an embed, so this is belt-and-braces rather than a fix — but the cost is one keyword and
    `test_every_send_and_every_edit_carries_allowed_mentions` now pins it, `call_me` set to
    `@everyone`. ⚠️ **Finding, not fixed here:** `requests.py`, `events.py`, `polls.py`,
    `birthdays.py` and `applications.py` all edit their panels without it.
15. ⚠️ **`docs/TODO.md`, `docs/DONE.md` and `docs/deploys.log` were NOT touched** — the build
    brief reserves those for the conductor. `docs/TODO.md:215` still lists `/memory` among the
    commands waiting for a panel and `:257` records the I-M1 decision; both want a dated line
    saying it shipped.

### What §H could and could not prove

| # | §H item | Proven? |
|---|---|---|
| 1 | boot reports `commands synced` **42, unchanged** | **Measured, not booted** — the real tree counts 42 with every cog loaded, and `/memory` is no longer a `Group`. A live boot is deviation 12 |
| 2 | the parametrised state test | **Proven** — `test_every_state_renders_exactly_its_row_of_the_button_table` over all six of §C's rows, plus `test_no_state_offers_both_spellings_of_one_move` sweeping eleven states for duplicate labels and for the two mutually exclusive ones |
| 3 | the five-module import check | **Proven** — run, passes; it is what a boot would catch and this build creates a real new edge (`api/tools/chat_memory` → the cog) |
| 4 | ruff, full pytest, `check.mjs`, `labels.js` | **Proven** — ruff clean, 3744 pass, 17 pages / 142 routes, `labels.js` parses |
| 5 | the checklist sweep | **Proven on paper**: 8 (`AnswersErrors` reaches the view through `Panel` and the modal through `NoteModal`), 11 (`allowed_mentions` on the one `send_message`; every other write is an `edit_original_response` on an ephemeral message), 15/17 (`say` is gone, `db_up` de-duplicated), 30 (the mixin), 33 (§D), 34 (the route dedup, asserted by COUNT), and the feature-specific one — **no fact text in a log row**, asserted on the details DICT in four tests |
| — | anything a person sees | **NOT proven** — no panel has been opened in Discord, no sweep row run, and `chat_memory_mode` is still `off` in production |
| — | the 25-option Discord cap | **NOT measured** — it is Discord's documented limit; the code caps at 25 and the test asserts the cap, but no client has rendered a 25-option select here |
