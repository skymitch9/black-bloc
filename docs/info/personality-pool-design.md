# The global personality pool — design (next-wave #4)

> **Audience:** Claude sessions in BOTH repos (this one and `catalog-platform`).
> **Status:** TRACKED — **BUILT (Black Bloc half) on `worktree-agent-a9f7e266cd87f5c2c`, not
> merged, not deployed** (2026-09-05). The GABI half (§5.1) is **NOT built**; until it lands,
> the self-test check reports *"GABI does not say its pool version yet"* as a pass, which is
> the landing order §8 asks for. The runbook for the built half is
> [`../access/personality-pool.md`](../access/personality-pool.md). ✅ All three forks decided (a) by the owner 2026-09-05 16:41–16:43. Written **2026-09-05** by Fable in the
> main loop. Last verified: **2026-09-05** — every fact about the two codebases
> below was read from `black_bloc/personas.py` (407 lines) and
> `catalog-platform/apps/discord-worker/src/personality.ts` (930 lines, last
> touched `2ff0037` 2026-08-18) this session. NOT verified: nothing was run;
> the GABI health route was not fetched.
> Owner ask (next-wave list, 2026-09-02): *"Global personality pool — one trope
> store shared across estate bots (Black Bloc's `personality_tropes` + GABI's
> `personality.ts` unify)."*

Siblings: [`phase14-design.md`](phase14-design.md) (the port that created
`personas.py`), [`chat-panel-design.md`](chat-panel-design.md) (the Personality
tab staff use), and on the GABI side
`catalog-platform/docs/info/gabi-personality-design.md` (the origin; §2 locks
the roster, §3 the graph, §11.4 the estate's precedent for sharing prompt text).

---

## 1. What is actually shared today, measured

| Thing | GABI (`personality.ts`) | Black Bloc (`personas.py`) | In step? |
|---|---|---|---|
| Roster (11 names) | `TROPES` const, owner-locked 2026-08-18 | `TROPES` tuple, same 11 in the same order | ✅ identical |
| Neighbour graph | `TROPE_NEIGHBOURS`, symmetric chain of wings | `Trope.neighbours`, same edges | ✅ identical |
| Labels | `label` (scholar → "scholarly") | same | ✅ identical |
| Voice bodies | "the book or the question", "GABI, the estate's librarian" | "whatever is going on", "Black Bloc, the cookout's bot" | ⚠️ **deliberately different** — same skeleton, each bot's world |
| `INVARIANT` clause | facts, refusals, quotes, citations, spoiler limits | facts, refusals, the server's own notes, command sentences | ⚠️ same rule, each bot's nouns |
| `REGISTER` clause (PG-13 ceiling) | "a family server" | "this server has a range of ages" | ⚠️ one word apart |
| Drift constants | `DRIFT_EVERY_EXCHANGES=4`, `DRIFT_CHANCE=0.25` | `DRIFT_EVERY_TURNS=4`, `DRIFT_CHANCE=0.25` | ✅ identical |
| Where the roster LIVES | code constants in a Cloudflare Worker; changing one is a deploy | SQLite rows seeded once from code (`seed_tropes`, insert-if-missing); staff toggle `enabled` on the `/chat` Personality tab and the website | ❌ **different by design** — GABI has no staff; Black Bloc's staff get the final say |
| Per-person state | pin + drift in a Durable Object keyed by user | pick is a pure function of a conversation key + turn count; setting `chat_personality` = `cookout` / `pool` / `<name>` | ❌ different, and NOT what "pool" means |
| Intensity dial | `GABI_EDGE` (§11, 2026-09-01) | none | ❌ GABI-only |

**So the two are in step today by accident of timing** — `personality.ts` has
not changed since the port — and nothing would say so if either side moved.
That is the whole problem: not that they differ, but that **drift would be
silent**.

## 2. ⚠️ What "one store" must NOT mean

A live shared runtime store (a D1/KV table both bots read at boot) was the
obvious reading and is rejected, for three reasons that each stand alone:

1. **GABI's roster is owner-locked code**, reviewed and approved as a whole
   (§2 of her design). A store that a Black Bloc staff member can edit is not
   an owner-locked roster. The two bots have different authorities over the
   same list, and a single mutable store cannot serve both.
2. **The voices are supposed to differ.** A librarian's `peppy` celebrates a
   good find; the cookout's celebrates somebody's good news. Sharing the voice
   bodies would flatten both bots into the same character with two names,
   which is the opposite of what a persona is for.
3. **It puts a network fetch on a boot path** of a gateway bot (and an
   authenticated cross-Worker call on GABI's) to move data that changes at
   owner-decision cadence — months, not minutes. The estate already faced this
   exact choice for the core prompt and chose *"a copied prompt with a comment
   naming its source, not a shared package"* (`gabi-personality-design.md`
   §11.4). This design follows that precedent rather than reversing it.

## 3. The design in one paragraph

**Share the SKELETON, keep the SKIN.** One canonical machine-readable manifest
— the roster, the labels, the graph, the drift constants, the two clauses as
templates with a `{world}` slot, and a `version` — lives in the origin repo.
Each bot carries a **synced copy** and *derives* its roster and graph from it
instead of restating them in code; each bot keeps its **own voice bodies**,
keyed by trope name, and a test in each repo proves the voices cover the
manifest exactly (no missing trope, no extra one). Black Bloc's boot sync
brings its staff-editable rows up to the manifest without ever touching the
one column staff own (`enabled`). Drift between the two bots becomes
**visible** through one field on each health route and one Black Bloc
self-test check that reads GABI's.

## 4. The manifest

Canonical home (fork F-P1, recommended (a)):
`catalog-platform/apps/discord-worker/src/personality-pool.json`. GABI is the
origin, the roster is locked there, and `personas.py:POOL_SOURCE` already
points at that directory.

```jsonc
{
  "version": 1,                       // bump on ANY roster/graph/clause change
  "locked_by": "owner, 2026-08-18",   // provenance of the roster as a whole
  "drift": { "every": 4, "chance": 0.25 },
  "tropes": [                         // order = sort order = seed order
    { "name": "peppy",   "label": "peppy",     "neighbours": ["dramatic", "mischievous"] },
    { "name": "scholar", "label": "scholarly", "neighbours": ["noir", "deadpan"] },
    // … 11 total; the graph is checked symmetric by test in BOTH repos
  ],
  "clauses": {
    "invariant": "This is VOICE ONLY. Facts, refusals, {invariant_nouns} and any sentence a {tool_noun} told you to say are unchanged — say them in full and do not soften, dramatise or reword them. Colour the words AROUND them, never the sentences themselves.",
    "register":  "PG-13 is your CEILING, not your usual register. Start mild: {audience} and somebody whose tone you have not read yet — or who is reserved — gets the gentle end. …"
  }
}
```

What is **deliberately not** in it: voice bodies, the `TROPE_BLOCK` framing
line ("You are still GABI…" / "…still Black Bloc…"), the pin/roster/devops
machinery (GABI-only), the intensity dial (GABI-only), and per-person state.

Slots are filled per bot from constants in that bot's code. A slot the bot does
not fill is a test failure, not an empty string.

### 4.1 ⚠️ The FINAL slot list, as built (2026-09-05)

The manifest carries its own `"slots"` array so each bot's test can assert it
fills every slot without hard-coding the list. **Four slots**, chosen as the
minimum that reproduces both bots' *current* wording:

| Slot | Black Bloc fills | GABI fills | Why it exists |
|---|---|---|---|
| `invariant_nouns` | `the server's own notes` | `quotes, citations, spoiler limits` | each bot's own protected material |
| `tool_noun` | `command` | `tool` | a slash command vs a Worker tool call |
| `audience` | `this server has a range of ages,` | `this is a family server with a range of ages,` | the one word §1 called them apart on |
| `warn` | `` (empty) | `⚠️ ` | GABI's register clause carries an internal ⚠️ before *"The wiggle…"*; nothing in Black Bloc's prompts uses that marker. A slot is cheaper than changing either bot's live prompt |

⚠️ **One deliberate NORMALISATION, and it changes Black Bloc's prompt text by
one character:** the template keeps GABI's comma in *"clearly playing along,
you may lean in"*, which Black Bloc's copy had lost. Two spellings of one
sentence is exactly the accidental drift this design exists to kill, and the
comma is the grammatical one. Nothing else in either clause moved.

⚠️ **`black_bloc/personality_pool.json` is HAND-BUILT from `personality.ts`**
until the GABI half writes the canonical. Its `synced_from` says
`catalog-platform@03dcb91` — the commit its content was read from, not a commit
that contains the file.

## 5. Each bot's side

### 5.1 GABI (`catalog-platform`, TypeScript, Cloudflare Worker)

- `personality.ts` imports the JSON (Wrangler bundles JSON imports) and derives
  `TROPES`, `TROPE_NEIGHBOURS`, `DRIFT_EVERY_EXCHANGES`, `DRIFT_CHANCE`, and
  builds `INVARIANT`/`REGISTER` by filling the slots. `TROPE_VOICES` stays
  hand-written, keyed by name.
- `test/personality.test.ts` keeps every existing assertion (11, includes
  `flirty`, symmetric graph, every voice > 40 chars, both clauses on every
  block) — they now prove the manifest rather than the constants — and gains
  one: `Object.keys(TROPE_VOICES)` equals the manifest's names exactly.
- `/api/health` gains `gabi_personality_pool_version` beside the existing
  `gabi_personality_tropes` count.
- ⚠️ Type safety: `Trope` today is `(typeof TROPES)[number]`, a literal union
  the compiler checks `TROPE_VOICES: Record<Trope, …>` against. A JSON import
  is `string[]`, and that check is lost. Keep the literal union by keeping
  `TROPES` as the `as const` tuple in code AND asserting at test time that it
  equals the manifest's names in order — the compiler keeps the exhaustiveness
  check, the test keeps the sync. (Trade-off named so the builder does not
  "simplify" it away.)

### 5.2 Black Bloc (this repo, Python, Fly container)

- `black_bloc/personality_pool.json` — the synced copy, byte-identical to the
  canonical, with the header field `"synced_from": "catalog-platform@<commit>"`
  added by the sync script (the one field allowed to differ).
- `personas.py`: `TROPES` becomes *derived* — names, labels, neighbours and
  sort from the manifest; `VOICES: dict[str, str]` holds the cookout bodies
  keyed by name; `Trope` rows are built by zipping the two. `DRIFT_*` and the
  two clauses come from the manifest with the cookout slots filled.
  `POOL_SOURCE` becomes the manifest's `synced_from`.
- **Boot sync replaces seed** (`seed_tropes` → `sync_tropes`), still
  insert-if-missing for new names, and additionally for every row whose
  `source = 'gabi'`: bring `label`, `voice`, `neighbours`, `sort` up to the
  manifest when they differ. ⚠️ **`enabled` is never written by sync** — it is
  the staff column (staff final say). A name that has LEFT the manifest is not
  deleted: its row gets `source = 'retired'` and `enabled = 0`, one log row
  (`chat.pool_retired`), and staff can re-enable it from the panel if they
  want to keep it — a retired trope still has its voice text and neighbours
  (which will simply find no live wings and stay put in drift). One boot, one
  `chat.pool_synced` log row naming what changed, and nothing when nothing did
  (one write one log row — checklist 34).
- Setting `personality_pool_sync` (core, bool, default **on**) so the sync can
  be held off from the Settings page or `/settings set-value` if a manifest
  change ever lands wrong (checklist 33). Off means: seed missing names only,
  as today.
- `/health` gains `"personality_pool_version"`.
- `tests/test_personas.py` gains: manifest loads; graph symmetric; every
  manifest name has a voice and no voice lacks a name; every clause slot is
  filled; sync updates a stale `gabi` row, leaves `enabled` alone, retires a
  vanished name, and writes nothing when in step.

### 5.3 The sync convention (the "store" the owner asked for, in practice)

- `scripts/sync_personality_pool.py` (bot code — it makes the bot work, so it
  IS committed, unlike `scripts/scan/`): copies the canonical file from the
  sibling checkout `../catalog-platform/…/personality-pool.json` into
  `black_bloc/personality_pool.json`, stamps `synced_from` with that repo's
  `HEAD`, and exits non-zero if the canonical is not found (never silently
  keeps the stale copy while printing success — the CLI-quirk rule).
- Order of operations for a roster change, written in BOTH repos' access docs:
  edit the canonical → bump `version` → GABI tests → GABI deploy → run the
  sync script here → Black Bloc tests → deploy. Both `deploys.log` lines name
  the pool version. A version that reached one bot and not the other is
  half-shipped, exactly as the both-catalogs rule says of the two libraries.

### 5.4 ⚠️ Drift made visible — the part that earns the whole design

- Black Bloc's self-test gains one read check `pool.in_step_with_gabi`: GET
  `https://discord.heygabi.ai/api/health`, compare
  `gabi_personality_pool_version` and `gabi_personality_tropes` with the local
  manifest's version and count. A mismatch is a **FAILED** row that says which
  side is ahead ("GABI is on pool v2, this bot on v1 — run
  `scripts/sync_personality_pool.py`"), and a network error is a worded
  "could not reach GABI's health route" — NOT a failure of the pool (a
  network failure is not a drift failure, the same distinction the refusal
  rule draws). The GABI health URL is a setting `personality_pool_peer_url`
  (core, default the URL above) so a renamed host is a settings edit.
- Nothing on GABI's side polls Black Bloc; she has no self-test and this repo
  is private. One direction is enough to make drift visible on every boot and
  on every owner-pressed Run.

## 6. What is deliberately NOT built

- **No live shared store, no cross-bot fetch on a boot path** (§2).
- **No shared voice text.** Two bots, two worlds.
- **No shared per-person state.** GABI's pin is per user in her Durable
  Object; Black Bloc's pick is per conversation window. A person who is
  `noir` with GABI is not thereby `noir` with the cookout — nobody asked for
  that, and it would need person-identity sharing across the estate.
- **No dial for Black Bloc** in this wave. `GABI_EDGE` is a GABI posture
  answering a GABI ask; if the owner wants it here it is its own item.
- **No editing of voice bodies from the panel.** Staff toggle a trope on and
  off; the words stay the code's (and the sync would overwrite an edit, which
  is the reason not to offer one until a row can say it was hand-edited).

## 7. Forks for the owner — one at a time

| # | Fork | Recommend |
|---|---|---|
| F-P1 | Canonical home: (a) `catalog-platform/apps/discord-worker/src/personality-pool.json` — the origin, already locked there, public repo so the roster is readable by anyone who can read GABI; (b) a new estate-level repo/package | **(a)** — ✅ **owner chose (a)** 2026-09-05 16:41 |
| F-P2 | Boot sync rewrites `voice`/`neighbours`/`label` of untouched `gabi` rows (a) or only ever inserts missing names, as today (b) | **(a)** — otherwise a graph change never reaches a running bot, which is the silent drift this exists to kill; staff's `enabled` is untouched either way — ✅ **owner chose (a)** 2026-09-05 16:42 |
| F-P3 | A trope removed from the manifest is retired-but-kept (a) or deleted (b) | **(a)** — staff final say, and nothing is a terminal state — ✅ **owner chose (a)** 2026-09-05 16:43 |

## 8. Cost (labeled guesses, at the measured ~1.5–3× overrun)

Two dispatches, in this order, each `model: 'opus'` in its own worktree:

1. **Black Bloc half** — manifest copy + derived `personas.py` + `sync_tropes`
   + two settings + health field + self-test check + sync script + tests +
   `docs/access/` runbook + code-notes. Est. **150–220k**.
2. **GABI half** — JSON + derived constants + test + health field + her
   `docs/access/gabi-personality.md` §1 table line. Est. **80–120k**. ⚠️ The
   builder reads `catalog-platform/docs/` first (its own deploy rules, its own
   `deploys.log`), and the Worker deploy follows THAT repo's runbook, not
   `scripts/deploy.ps1`.

Black Bloc first: until GABI exposes the version field, the self-test check
reports "GABI does not say its pool version yet" in words — a WARN-shaped pass,
not a failure — so landing order cannot produce a red self-test.

## 9. Not verified

- The GABI health route's current fields were read from her access doc's
  PowerShell example, not fetched.
- Whether Wrangler's JSON import keeps `as const` literal types (§5.1 assumes
  not, and designs around it).
- The sibling-checkout path convention (`../catalog-platform`) is what this
  machine has; a fresh clone elsewhere needs the script's `--from` flag.
