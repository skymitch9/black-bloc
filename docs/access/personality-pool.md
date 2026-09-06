# The global personality pool — runbook

> **Audience:** Claude sessions and the owner. **Status:** TRACKED — secret NAMES only.
> **Last verified: 2026-09-05** — every command and file path below was run or read on the
> build branch `worktree-agent-a9f7e266cd87f5c2c`, off `main` at `a93f3e1`.
> ⚠️ **NOT verified:** nothing here has met live Discord, the live dashboard or the live Fly
> app; GABI's health route was **never fetched** (she does not publish
> `gabi_personality_pool_version` yet — her half of the design is a later build); and
> `scripts/sync_personality_pool.py` has never copied the real canonical file, because that
> file does not exist yet. The script's refusal path is the part that was exercised.
>
> The design and the reasoning are in [`../info/personality-pool-design.md`](../info/personality-pool-design.md).
> This file is only how to operate it.

---

## What it is, in three sentences

The eleven moods, their labels, the wings they can drift along, the drift constants and the
two clauses that ride every mood block are **one manifest**, not two codebases restating each
other. Black Bloc carries a synced copy at `black_bloc/personality_pool.json` and *derives*
its roster from it; the cookout's own voice bodies stay in `black_bloc/personas.py:VOICES`.
GABI is the origin — her repo owns the canonical file — and drift between the two bots is made
visible by one field on each health route and one self-test check that reads hers.

## The files

| Where | What |
|---|---|
| `black_bloc/personality_pool.json` | the synced copy. `synced_from` is the ONE field allowed to differ from the canonical |
| `black_bloc/personas.py` | derives `TROPES` / labels / neighbours / sort / `DRIFT_*` / `INVARIANT` / `REGISTER` from it; holds `VOICES` (this server's words) |
| `scripts/sync_personality_pool.py` | copies the canonical over the local copy and stamps the commit it came from |
| `catalog-platform/apps/discord-worker/src/personality-pool.json` | the canonical. ⚠️ **Does not exist yet** — the GABI half is a later build, and today's local copy is hand-built from her `personality.ts` |

## Order of operations for a roster change

⚠️ **A version that reached one bot and not the other is half-shipped**, exactly as the
both-catalogs rule says of the two libraries. Do all seven, in this order:

1. Edit the canonical `personality-pool.json` in `catalog-platform`.
2. **Bump `version`** — on ANY roster, graph, drift or clause change.
3. Run GABI's tests, then deploy the Worker by **that repo's** runbook.
4. Here: `python scripts/sync_personality_pool.py`
5. Here: `pytest -q` — the roster, graph and voice-coverage tests fail by name if the copy and
   `VOICES` disagree.
6. Here: deploy (`docs/access/deploy.md`). The boot sync brings the rows up on the way in.
7. Both `deploys.log` lines name the pool version.

Adding a mood means adding it to the canonical **and** writing a cookout voice body for it in
`personas.py:VOICES` — a name with no voice is a worded startup failure, not a blank block.

## The sync script

```powershell
python scripts/sync_personality_pool.py                 # the sibling checkout ../catalog-platform
python scripts/sync_personality_pool.py --from D:\some\personality-pool.json
```

It exits **1 with a sentence** when the canonical is not there, is not JSON, or lists no
tropes — it never prints success over a stale copy. On success it prints the source, the
destination, the pool version, the `synced_from` stamp, and says `(unchanged)` when the copy
already said exactly that.

⚠️ **Today it exits 1 every time**, because the canonical does not exist. That is correct
behaviour and not a fault to fix: the local manifest is hand-built until the GABI half lands.

## What the boot sync does, and the one column it never touches

`personas.sync_pool(bot)` runs from the chat cog's `on_ready`:

- a name in the manifest with no row → inserted, `source = 'gabi'`, `enabled = 1`;
- a row with `source = 'gabi'` whose `label` / `voice` / `neighbours` / `sort` differ from the
  manifest → brought up to it;
- a `source = 'gabi'` row whose name has LEFT the manifest → `source = 'retired'`,
  `enabled = 0`, and one `chat.pool_retired` log row. **It is not deleted** — its words and
  wings are still there, and staff can switch it back on from `/chat` ▸ Personality or the
  dashboard's Chat page;
- a row with any other `source` (one staff added by hand) is left entirely alone;
- ⚠️ **`enabled` is never written by the sync.** It is staff's column, and staff have the
  final say over which moods the bot may use.

One boot leaves **one** `chat.pool_synced` row per server naming what moved, and **nothing at
all** when nothing moved.

## The two settings

| Key | Default | What it decides |
|---|---|---|
| `personality_pool_sync` | `true` (core, bool) | whether the boot sync updates and retires, or only ever inserts missing names. Turn it OFF if a manifest change ever lands wrong; it never touches `enabled` either way |
| `personality_pool_peer_url` | `https://discord.heygabi.ai/api/health` (core, text) | the health address the self-test reads to compare pool versions |

Both reachable from the dashboard's Settings page
(https://blackbloc.heygabi.ai/settings.html, under **Core**) and from `/settings` ▸ **A
setting group…** ▸ **core**.

⚠️ **`personality_tropes` is a GLOBAL table with no `guild_id`**, so `personality_pool_sync`
being off in *any* server holds the update-and-retire half off for the table. With one server
that is the obvious behaviour; it is written down because a second server would make it
surprising.

## Reading the self-test row

Every self-test run — the boot one, `/settings` ▸ **Self-test…** ▸ **Run the self-test**, and
the dashboard's Health page — now includes one check named **`pool.in_step_with_gabi`**, in
the **Chat** feature. Its detail line is one of:

| It says | It means |
|---|---|
| `pool v1 on both; 11 moods here; GABI has the same 11` | in step |
| `pool v1 here; GABI does not say its pool version yet` | ✅ pass. Today's expected line — her half is not built |
| `could not reach GABI's health route (…) — the pool itself is fine` | ✅ pass. A network fault is NOT a drift fault |
| `pool v1 here; no peer address is set, so nothing was asked` | ✅ pass |
| **FAILED** *"GABI is on personality pool v2, this bot on v1…"* | ❌ the two rosters can differ. Run the sync script and redeploy |
| **FAILED** *"…she lists N moods where this bot has M…"* | ❌ same version, different rosters — one copy was edited rather than synced |

Health route: `GET https://blackbloc.heygabi.ai/health` now carries
`personality_pool_version` beside `version`, `ready`, `guilds` and `latency_ms`.

## When it goes wrong

| Symptom | What to do |
|---|---|
| the bot will not start and the log names a missing manifest | the file did not ship. Check `pyproject.toml`'s `package-data` and the Dockerfile's `COPY black_bloc`, then `python scripts/sync_personality_pool.py` |
| startup fails saying a trope has no voice | a name was added to the manifest and not to `personas.py:VOICES`. Write the cookout body |
| the self-test row is red after a GABI deploy | she moved first, which is the designed order. Run the sync script here and deploy |
| a mood vanished from the panel | it was retired by a manifest change. It is still a row — switch it back on, or put the name back in the canonical and bump the version |

⚠️ **One asymmetry a retired mood has, worth knowing before it surprises somebody.** Switching
a retired mood back ON returns it to the **pool** — the drift can land on it again, because
`enabled_tropes` reads the rows, not the manifest. Setting it as the server's **single pinned
voice** (`chat_personality = <name>`) is refused, because that setting's choices come from the
manifest. The fix in both directions is the same one: put the name back in the canonical and
bump the version. This was not asked for by the design and is not treated as a defect —
staff's re-enable does the thing staff would want it for.
