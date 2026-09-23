# Black Bloc — Known Issues, Waivers & Exceptions

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then).
> Last verified: **2026-09-22 23:2x** — the `gate-names` build (branch, not merged or deployed): dated notes on **KI-26** (cause
> found — loopback port exhaustion — and fixed on the branch), **KI-32** (cause found and fixed: a shared media folder in the
> test harness), **KI-35** (names can no longer be lost) and **KI-37** (`-n 16`). All four stay `WATCHING` until the merge
> and the gates named in each note. ⚠️ Nothing else in this file was re-tested. Before that, **2026-09-22 21:2x** — the v156 docs ritual. **KI-39 ADDED**, `ACCEPTED`: a spotlighted marathon's pinned
> announcement is edited and logged on every title change (owner decision 21:2x). ⚠️ Its rate is unmeasured; nothing else in
> this file was re-tested. Before that, **2026-09-21 20:1x** — the v154 docs ritual. **KI-38 ADDED**, `WATCHING`: an Opus
> build agent can be dropped repeatedly by Anthropic-side `529`/`500` errors during a provider
> outage (measured 2026-09-21 17:5x–18:3x on the `golive-settings-help` build, five drops, zero
> work lost — checkpoint-committing after every step and handing the remainder to a Sonnet agent
> from the same worktree was the recovery). **KI-26 gains a finding**: an agent killing every
> `chrome-headless-shell` process BY NAME can hit another build's render mid-flight
> (2026-09-21 17:5x) — kill by process tree, never by image name, same as the existing `python.exe`
> warning. ⚠️ **Nothing else in this file was re-tested at v154:** no symptom was reproduced,
> nothing met live Discord, no browser rendered a page against production. Before that,
> **2026-09-21 12:2x** — the v153 docs ritual. **KI-36 and KI-37 ADDED**, both `WATCHING`:
> the every-key-lands-once JOIN FIXTURE is a hand-typed number that every concurrent build bumps, so a merge
> taking one side passes the count and drops a key — **twice now** (`autolink`'s Deviation 16, then both v153
> branches bumping 52 → 53 with **54** the merged truth, measured); and **a deploy gate can be killed by the
> OS** when another job on this machine holds more than 12 GB (the v153 gate's run 2 died at 99 % of pytest
> beside a whisper transcription job). **KI-26 rises from TWENTY-TWO to AT LEAST TWENTY-EIGHT** — twenty-two
> plus at least six today — and gains two findings: *a stalled gate is usually a SECOND gate*, and a new
> `exit 255` xdist worker-DEATH variant. **KI-32 reaches TWO sightings**, its own first trigger, and this one
> REFUSED a release. ⚠️ **Nothing else in this file was re-tested at v153:** no symptom was reproduced,
> nothing met live Discord or YouTube, and no browser rendered a page. Before that,
> **2026-09-21 10:38** — the v152 docs ritual. **KI-35 ADDED**, `WATCHING`: an unexplained
> random-order flake in the v152 deploy gate — **2 tests failed on ONE of six runs and the two names were LOST**;
> five later runs were clean. It is NOT KI-32 and NOT KI-26 on the evidence available, because nothing records
> which tests they were. ⚠️ **Nothing else in this file was re-tested at v152:** no symptom was reproduced, nothing
> met live Discord, no browser rendered a page, **KI-26's count stands unchanged at TWENTY-TWO** (the v152 gate
> runs did not stall) and **KI-32 stands at ONE sighting** (the v152 gate did not name that test). Before that,
> **2026-09-21 09:5x** — the v151 docs ritual. **KI-33 and KI-34 ADDED**, both `WATCHING`:
> a node fixture with a date written into it (`discordmock.test.mjs` went red on 2026-09-21 on unchanged code,
> on `main` AND on v150 alike), and one `say` node handed to two sections, which put the **Link from history**
> report inside the COLLAPSED Recent streams — five notices still share that node. Both were found by the v151
> builds, neither from an owner report. ⚠️ **Nothing else in this file was re-tested:** no symptom was
> reproduced, nothing met live Discord, no browser rendered a page, and **KI-26's count stands unchanged at
> TWENTY-TWO** — the v151 gate runs did not stall. Before that,
> **2026-09-19** — the docs staleness pass after the **TEST_MODE lift**
> (2026-09-18 16:08). What moved: **KI-5 is MOOT** (its whole subject was what test mode did
> and did not stop) and **KI-8's "which today is every panel outside `TEST_CHANNEL_ID`"**
> clause is history — each gains a dated banner and keeps its body, nothing deleted.
> **KI-26's count stands at TWENTY-TWO** (re-counted 2026-09-20 23:3x at the v150 landing; it read TEN here) (the tenth, 2026-09-18 16:5x, was the first on a `> file`
> run — its own *what would change it* is therefore MET, and the session it asks for is
> queued on [`TODO.md`](TODO.md)). ⚠️ **Nothing else in this file was re-tested:** no
> symptom was reproduced, nothing met live Discord, no browser rendered a page, and the two
> thresholds under KI-6 (">1 site user", ">1 person with `/data` access") are **still
> unmeasured** — and now sharper, because the bot is live to members. Every OPEN entry's
> `Status` word was re-read and is still the right word. Before that,
> **2026-09-18** — **KI-11, KI-12 and KI-13 CLOSED as moot** on branch
> `youtube-uploads-removal` (owner: *"the youtube uploader we should just fully trash"*; design
> [`info/youtube-uploads-removal-design.md`](info/youtube-uploads-removal-design.md)). All three
> described the UPLOADS half — the feed's flakiness, the ~25-minute lateness, and a live broadcast
> announced as a video — and that half no longer exists. Each keeps its body and gains a one-line
> banner; nothing was deleted. ⚠️ **Verified in the suite and by reading the tree, not against live
> Discord.** ⚠️ **Nothing else in this file was re-checked then** — KI-26's count still stands at
> eight, and this build's own `pytest -n 8` runs did not stall in either order. **KI-30 is
> UNAFFECTED and still `WATCHING`:** it is the LIVE half's scrape, which this build did not touch.
> Before that, **2026-09-17** — **KI-30 REWRITTEN** on branch `youtube-live-fix` with a MEASURED
> sighting: it is no longer "never triggered". From the Fly machine's datacenter address YouTube
> serves the *Sign in to confirm you're not a bot* page — `"isLive"` survives, the canonical link
> does not — so a live channel read as unannounceable and the feature went silently quiet in
> production (conductor's measurement 18:14–18:20; ⚠️ **this build could not re-measure the network
> from Fly and did not try**). The fix is **LIVE as v133** (2026-09-17 18:44, release `b20e4dc`); verified live: the bot's own probe_live, run inside the Fly container 18:5x, read Pawpette as live=True / video_id=None / botcheck=True (the wall page: isLive once, canonical href="undefined"); the site's status showed botcheck true, probed 2, quota 0, live_now 0 — nothing announced because her TWITCH go-live session #139 was still open (the one-announcement-per-person rule), and that path writes no row, so the probe's success was invisible — follow-up dispatched. Sweeps
> **586–590** are the owner's, on the live bot. ⚠️ **Nothing else in
> this file was re-checked then.** Before that, **2026-09-17** — **KI-31 ADDED** on branch `minutes` (`ACCEPTED`, the
> receive extension is a PRE-RELEASE and it pins the image to Python 3.12; filed by the
> prototype build from its own spike, never from an incident, and ⚠️ **nothing else in this
> file was re-checked then** — KI-26's count still stands at seven and this build's own
> `pytest -n 8` runs did not stall). Before that,
> **2026-09-17** — **KI-30 ADDED** on branch `youtube-live` (`WATCHING`, the `/live`-page
> scrape behind YouTube live detection; filed by the build because `info/youtube-live-design.md` §A told it to,
> never triggered, markers verified against ONE real page). Before that,
> **2026-09-17** — **KI-28 CLOSED** on branch `staff-reach` (§C.3 of
> [`info/staff-reach-design.md`](info/staff-reach-design.md)): the key modal reads
> `TEXT_MAY_BE_BLANK`, so the two go-live end keys can be emptied from Discord as well as from the
> dashboard. ⚠️ **Proved by the suite, not by a Discord modal** — the entry says so, and sweep row
> `SR-l` is the proof that is missing. ⚠️ **Nothing else in this file was re-checked then**, and
> **KI-26's count stands at seven** — this build's own `pytest -n auto` runs did not stall. Before
> that, **2026-09-11 10:55** — **KI-26 ADDED** (the xdist deploy-gate hang, `WATCHING`, 5 hangs v94–v100, 0 of 8 since v103); 10:50 — **KI-25 ADDED** (Discord-only sign-in, `WAIVED` by the owner: "A discord is fine"); **08:33** — every OPEN entry was re-read against the repo at
> `main` `1d090e5` (**v108 LIVE**). What moved:
> **KI-24 is now LIVE, not just closed on a branch** — it merged as `689eff5` and shipped
> **v97** (`aa44e3b`, 2026-09-06 13:52; `deploys.log:96`); `black_bloc/loops.py` exists and
> `wait_ready` has **27** call sites, with the only bare `bot.wait_until_ready()` left in the
> helper itself. **KI-20's symptom list was two panels and is now eighteen** — measured:
> **18** `*_panel_minutes` keys in `settings_store.KEY_TYPES`, every one defaulting to **10**.
> **KI-10's "15 cogs" is the 2026-09-03 boot line** and is left as the historical reading; the
> tree holds **19** cogs today. Re-confirmed unchanged: KI-22 (`mod.purged` / `mod.purge_failed`
> are still bare literals at `cogs/moderation/modcmds.py:874,895` and there is still **no**
> `POST /api/mod/purge`), KI-2 (`bot.py:setup_hook` still calls `sync_dev_guild` unconditionally),
> KI-11/KI-13 (`youtube_mode` default `off`, `youtube_poll_minutes` default **10**,
> `FEED_ATTEMPTS` **4**), KI-14 (`chat_memory_mode` default `off`), KI-6 (`SESSION_TTL_SECONDS`
> still 7 d). ⚠️ **NOT re-tested:** no entry's symptom was REPRODUCED — this was a read of the
> code, not a run; nothing met live Discord, no browser rendered a page, and the two thresholds
> flagged under KI-6 (">1 site user", ">1 person with `/data` access") are **still unmeasured and
> still waiting on the owner**. Before that,
> **2026-09-06 — KI-24 CLOSED** on branch `loop-guard`: the fourteen `before_loop`s
> now go through `black_bloc/loops.py:wait_ready`, the restart is proved against a real
> `tasks.Loop`, and two AST guards keep the helper the only copy — `info/loop-guard-design.md`
> carries the design and its Deviations. ⚠️ Verified by the suite in a worktree only: not merged,
> not deployed, and never exercised against live Discord (that caveat is **superseded** by the
> v97 line above). Nothing else here was re-checked.
> Before that, **2026-09-05 22:10 — KI-24 ADDED** by ENGINEERING SWEEP 3 on
> `worktree-agent-ab52a6d7c53bc1ecb`. It was found through a measured deploy-gate symptom that
> is now **FIXED in the same branch**: `pytest -q -n 4` off `main` at `6af0ba0` (v92) was green
> at 5188 passed while writing **1716 stderr lines / 143 tracebacks across 14 loops in 13
> cogs**; bisected to one fixture (`tests/test_selftest_panels.py::live`) and taken to **0
> stderr lines**, 5188 still passing. What the entry keeps is the PRODUCTION half the bisect
> exposed — that a `before_loop` failure bypasses `@loop.error` — read from the installed
> `discord/ext/tasks/__init__.py` (line 210 outside the try on 217, error dispatch on 278),
> **never from a running bot**. Nothing else was re-checked then. Before that, **2026-09-05 19:45 — KI-23 CLOSED and moved WHOLE to [`DONE.md`](DONE.md)** ("Personality
> pool, both halves"): both numbers it named arrived — GABI's `/api/health` answers
> `gabi_personality_pool_version: 1` (deployed by the owner, `755cfd54`) and `sync_personality_pool.py`
> exits 0 (`synced_from: catalog-platform@de4ef63`); Black Bloc v91 `604226f` compares her roster by name.
> Nothing else was re-checked then. Before that, **2026-09-05 — KI-23 ADDED** by the personality-pool
> build (Black Bloc half): nothing was verifying that the two bots' rosters agreed until the GABI half landed. Before that, **2026-09-05 — KI-21 RESOLVED and moved WHOLE to [`DONE.md`](DONE.md)** by the
> engineering sweep on `worktree-agent-accb69989b295c889`: `PUT /api/settings/{key}` hands
> `automod_mode`, `honeypot_mode` and `honeypot_exempt_role_ids` to the cog's own move, so the
> website reads the same verdict the Discord panel does. ⚠️ Fixed in tests only — the branch has
> not been merged, deployed, or exercised against the live dashboard. Before that, **2026-09-05 —
> KI-21 widened at the v79 (honeypot panel) landing: the same generic
> route bypasses `/honeypot`'s arming refusal and rewrites its exempt list with no log row; from the
> build's read of the code, not an incident.** Before that, **2026-09-04 — KI-21 added at the v74 (automod
> panel) landing from the design doc's
> read of `api/settings_api.py`, not from an incident; not exercised against the live site.** Before
> that, **2026-09-03 — KI-20 added by the requests fourth pass build, from
> reading its own code (the panel's View has a real timeout, not a persistent one)
> rather than an incident; not run against live Discord.** Before that, **2026-09-02
> — KI-17 and KI-18 added by the Phase 19 (applications)
> build; KI-15 and KI-16 by the Phase 18 (F19, raid trains) build, from reading its own
> code rather than from an incident; KI-14 by the Phase 17 build from its own §J
> measurement (two leaked third-person threads in run 1, none in run 2 after the fix).
> All five describe code that has never met live Discord, built in parallel, merged
> 17 → 18 → 19 and deployed `7b1c592` on 2026-09-03 with all three modes **off**. Before that,
> KI-11, KI-12 and KI-13 added from the Phase 16
> section-J measurements against the LIVE YouTube feed (30 timed requests, the
> response headers, and a real captured feed now kept as
> `tests/fixtures/youtube_feed.xml`); KI-10 added earlier the same day from a
> live Fly log line during the `d777f57` rolling deploy. Nothing else re-tested.**
> ⚠️ The three new entries describe a branch that has NEVER run against live
> Discord or a live YouTube API key. Before that, 2026-08-31 for the STATUS line only. ⚠️ **No entry below
> was re-tested then**, and two carry thresholds that may already have been
> crossed — see the note under KI-6. The dated history that follows is the
> 2026-08-27 reading: KI-9 added (anonymous poll votes are a per-poll hash, accepted); before that KI-8 added when the role-menu panels started
> following the mode (measured in tests only; no panel has ever been deleted
> against live Discord). Before that, KI-2 gained a second-sync note when command
> visibility landed (measured only in tests; no sync has been sent to Discord).
> Before that, KI-7 closed after the generic loop discovery
> landed (measured: seven loops, six cogs, `pytest -q` green). The other entries
> were written from reading the code, not from an incident, and were NOT
> re-checked today.
>
> **This file exists to stop the same non-bug being re-reported.** It holds
> things that ARE wrong, or look wrong, and are deliberately tolerated.
> Every entry: Symptom · Status · Why tolerated · What would change it.
>
> - Work in flight → [`TODO.md`](TODO.md)
> - Traps you fall INTO while working → [`info/gotchas.md`](info/gotchas.md)

## KI-39 — A spotlighted marathon's PINNED announcement is edited (and logged) on every title change — `ACCEPTED`

**Symptom.** Since v156 (2026-09-22 21:18) every poller tick (`spotlight_poll_minutes`, 5) that sees a changed GAME **or TITLE** on an
open Twitch session re-words the pinned announcement in place and writes `golive.spotlight_announcement_refreshed` (ROUTINE, so
the Logs page shows it and `#blackbloc-logs` does not at the default `golive_log_level`). A marathon such as GamesDoneQuick
retitles often, so its post is edited on many polls and the log fills with refresh rows. First live row: 04:18:00Z, GDQ,
two seconds after the v156 boot.
**Status.** `ACCEPTED` 2026-09-22 21:2x — owner, verbatim: *"i think gdq will always be log noisy during marathons, lets let it be
and deal with it then"*. Design: [`info/spotlight-design.md`](info/spotlight-design.md) ▸ *Follow-up 2026-09-22 (2)*.
**Why tolerated.** The owner's rule is that the pinned post names the game being played now; editing never re-pins, so members
see no pin churn — the cost is log rows and Discord edit calls, not noise in a channel.
**What would change it.** ⚠️ **The number is missing: edits per hour on a marathon has NOT been measured.** Count
`golive.spotlight_announcement_refreshed` rows per hour for one GDQ marathon day; if it runs high enough to crowd the Logs page
or draw a Discord rate limit (a `_refresh_failed` row), refresh on a GAME change only and leave title changes to the reminder.

## KI-38 — An Opus build agent can be DROPPED REPEATEDLY by Anthropic-side `529`/`500` errors during a provider outage — `WATCHING`

**Symptom.** During a minor Anthropic-side outage (2026-09-21 17:5x–18:3x), the Opus agent building
`golive-settings-help` was dropped **FIVE times** by `529 Overloaded` and `500` server errors —
errors on Anthropic's side, not this repo's. Each drop lost the in-flight turn but **zero committed
work**, because the agent had been checkpoint-committing after every step (`cf4c74b` was the last
checkpoint before the fifth drop, with three more files edited on top and not yet committed). The
build was finished by a **second, Sonnet, agent** resumed from the same worktree, which picked up
the checkpoint and made the remaining three commits (`71a3a37`, `dfda995`). **Status: WATCHING**
(one sighting, zero work lost).
**Why tolerated.** The mitigation already worked the one time it was needed: nothing was lost, and
the only cost was wall-clock time waiting out the outage and one hand-off between agents. The cause
is entirely outside this repo's control.
**What would change it.** ⚠️ **The number this entry is missing:** how often a provider outage of
this shape recurs — one sighting is not enough to say whether checkpoint-and-handoff should become
a standing instruction in every build brief, or stays an improvisation the next builder reaches for
on their own. A second sighting where the SAME recovery (checkpoint-commit + hand off to a
different model) is used again promotes this from a note to a documented standing move in the build
brief template; a sighting where work WAS lost changes the fix entirely (shorter checkpoint
intervals, or a pre-flight outage check before dispatching a long build).

## KI-37 — A deploy gate can be KILLED BY THE OS when another job on this machine holds more than 12 GB — `WATCHING`

> **2026-09-22 23:2x (branch `gate-names`) — the gate now runs `-n 16`, not `-n auto` (32 workers here).** Measured on
> the fixed tree: `-n auto` 42–46 s, `-n 16` 45–61 s (5 of 5 green), `-n 8` 72–177 s — the measured table is in [`access/deploy.md`](access/deploy.md) (*"The gate's pytest step"*). 16 halves the worker processes the OS
> has to hold, for ~13 % more wall time (mean 51 s against 45 s). ⚠️ **How much RAM that saves was NOT measured.** ⚠️ **New misdiagnosis risk:**
> `node down: Not properly terminated` is now ALSO what `pytest-timeout` prints when it kills a hung worker after
> 120 s, so the line alone no longer says "the OS". Tell them apart by the clock: a timeout kill lands 120 s after the
> test began and the run's wall time grows by ≥120 s; an OS kill does not wait. Run A5 of the measurement (**3.9 GB
> free** at its start) had 38 worker deaths, and they were the KI-26 port stall timing out, not memory. **What would
> change it:** unchanged — a second OS-kill sighting → `deploy.ps1` reads free memory before the gate and refuses in
> words. Before that —

**Symptom.** The v153 deploy gate's **second run** (2026-09-21 12:0x) was killed at **99 % of pytest**. It was not a
failing test and not a stall: the operating system reclaimed the process for low memory, and the only trace in the log
was `[gw6] node down: Not properly terminated`. The cause was outside this project entirely — a **whisper
transcription job holding ~12 GB** on the same machine. Nothing reached Fly; a third run shipped **7237 passed, 3
skipped**. **Status: WATCHING** (one sighting).
**Why tolerated.** The gate is what protects the deploy, and it did its job — nothing shipped, and the cost was one
wasted run of a three-minute gate. The trigger is a neighbouring workload nobody in this repo controls, and lowering
`-n` or capping worker memory would slow every run to defend against a condition seen once.
⚠️ **The reason this is its own entry and not a note under KI-26: it is easy to MISDIAGNOSE as KI-26.** An 8-worker
run that stops near the end with a `node down` line looks exactly like the stall family. The distinguishing facts are
worth more than a fix: a **KI-26** stall makes NO progress and its workers sit flat at ~0.0156 s CPU, while this one
was **killed while running**, and the machine was short of RAM.
**What would change it.** ⚠️ **Check free RAM before starting a deploy gate whenever a whisper / ingest /
transcription job may be running** — that is the whole of the present remedy and it costs one command. A second
sighting → `scripts/deploy.ps1` reads available memory before the gate and refuses **in words**, naming the hog,
rather than burning a run; a third, or one that kills a gate with a deploy half-applied → the gate drops its worker
count when free memory is under a measured threshold. ⚠️ **The number this entry is missing: the machine's free RAM
at the moment of the kill, which was NOT captured** — only the ~12 GB figure for the other job was.

## KI-36 — The every-key-lands-once JOIN FIXTURE is a hand-typed number, so a merge that takes one side passes the count and DROPS A KEY — `WATCHING`

**Symptom.** `site/mock/golive-join.test.mjs` proves every settings key in the `golive` + `pings` + `youtube`
namespaces lands in exactly one drawer or named surface. It does it against `NAMESPACE_KEYS`, a **hand-typed array**,
and a **hand-typed count** beside it (`is(... NAMESPACE_KEYS.length, 54)`). Every concurrent build that adds a key
bumps both, so two branches off the same base write the same next number — and a merge that resolves the conflict by
**taking one side** leaves the fixture one key short while the test still PASSES on the side it took. **Twice now:**
the `autolink` build's **Deviation 16** was the first, and at v153 both `member-optout` and `youtube-video-link`
bumped **52 → 53** independently; merged, the honest number is **54** (measured by import at this ritual). Caught by
hand both times. **Status: WATCHING** (two sightings, zero escapes to `main`).
**Why tolerated.** Nothing has shipped wrong. The collision is loud at merge time because the number sits in the diff,
and both times the conductor saw it. The fixture is otherwise doing exactly what it exists for — it is the test that
makes an orphaned settings key impossible — and replacing it is a small change nobody has had a spare build for.
**What would change it.** ⚠️ **The fixture DERIVING the list from the registry instead of asserting a hand-typed
number** — `Object.keys(...)` over the mock's generated settings block, filtered to the three namespaces, so two
branches each adding a key produce no conflict and the merged tree measures **54** on its own. That is the whole fix,
it is roughly one line, and the next build that touches `site/mock/golive-join.test.mjs` takes it as a ride-along. A
**third** collision, or the first one that reaches `main` with a key silently dropped, promotes this to a build of its
own and stops it being a ride-along.

## KI-35 — The v152 deploy gate went red on TWO tests in one run of six and the names were LOST — `WATCHING`

> **2026-09-22 23:2x (branch `gate-names`) — a red gate can no longer lose its names.** `scripts/deploy.ps1` now runs
> pytest with `-rfE` (every failure and error in the short summary) and `--junitxml=%TEMP%\black-bloc-gate\gate-junit.xml`,
> and on a non-zero exit prints `FAILED TESTS:` with one nodeid per line read from that file BEFORE it refuses; if no
> junit file was written it says the run itself was killed. Exercised against a synthetic junit file (plain, class and
> unknown-path cases) and a missing one — ⚠️ **not yet exercised by a real deploy gate**. A hang now also names its
> test (KI-26's timeout). Guess, labelled: v152's two nameless failures were most likely the guides-media pair
> **KI-32** fixed today — both are "two tests, one run, green on re-run", and that pair failed together in the
> reproduction. **What would change it:** the first real deploy gate on this script → `CLOSED` as "cannot recur";
> the lost names themselves are unrecoverable. Before that —

**Symptom.** Running the v152 gate (`pytest`, random order) the suite reported **2 failed** on **one of six runs**;
**five later runs were clean** and the release shipped on a green pair (**7189 passed, 3 skipped**, both orders). ⚠️
**The two test names were not captured** — the summary was read and the run scrolled away — so there is nothing to
reproduce, nothing to name, and no file to point at. **Status: WATCHING** (one sighting, zero evidence).
**Why tolerated.** Nothing in the bot is known to misbehave: the release's own gate was green in both orders before
the deploy, and the boot, `/health` and `release.json` all answered correctly on live afterwards. The three shapes
this could be are all already tolerated and all already say *read the log, re-run, move on* — a Windows file-handle
race (**KI-32**), the xdist stall family (**KI-26**, which this was not: the run finished and reported) and a
date-dependent fixture (**KI-33**, whose fuse fires at midnight and fired the day before). Chasing a failure with no
name would mean re-running the suite until it reproduces, which costs more than the next sighting costs — and the
next sighting, if the names are captured, resolves it into one of the three or into a real bug in one call.
**What would change it.** ⚠️ **A re-run that CAPTURES THE TWO NAMES** — that is the whole ask, and it is the number
this entry is missing. Any gate or agent that sees a red run on unchanged code writes the `FAILED` lines down before
re-running; with the names in hand this entry either folds into KI-32 / KI-33 or becomes a build of its own. A second
nameless sighting promotes it anyway: the gate starts running with the failures teed to a file
(`pytest --tb=no -q > <file>`) so a name can never be lost again. Until then this stays a **read the log** item — a
two-test red on a random-order run that is green on a re-run the same day is this entry, not the build.

## KI-34 — One `say` node handed to two sections lives in ONE of them, so a notice can render inside a COLLAPSED section — `WATCHING`

**Symptom.** On the Go-live page, `load()` hands **one** `say` node to both `streamersSection` and `recentSection`. A DOM
node lives in exactly one place, so the notice is physically inside **Recent streams** — which is collapsed — and
`keepSaying('golive.links', …)` put the **Link from history** report *in the tree and out of sight*. The accessibility
tree said the sentence was there; the pixels did not. Found 2026-09-21 by the `autolink` build, which looked at the
rendered page after the tree said it was fine, and fixed for that one door in `d56e899` — `sayAgain('golive.sweep',
notice())`, under the button that was pressed. **Status: WATCHING** — one door fixed, **five notices still share the
node**: `golive.links`, `golive.optouts`, `youtube.links`, `pings.streamers`, `pings.streamer`.
**Why tolerated.** Each of the five is invisible only while the section that physically owns the node is collapsed, and
each is a one-line fix at the door that needs it; re-plumbing the page's notices wholesale is a larger change than the
symptom justifies. None of the five has been REPORTED invisible by anyone — this was found by reading the pixels, not
from an incident — and every one of them is a *report*, never a refusal, so nobody is blocked by it.
**What would change it.** ⚠️ **Each door keeping its OWN notice** — a per-door `sayAgain('<door>', notice())` beside the
button that was pressed, the way the sweep report now does — taken as a ride-along by the next build that touches
`site/public/assets/page-golive.js`. A report from the owner or staff that a move on this page "did nothing" promotes it
from `WATCHING` to a build of its own; a sixth notice on the shared node promotes it too.

## KI-33 — A node fixture with a DATE written into it goes red the next day, on unchanged code — `WATCHING`

**Symptom.** `site/mock/discordmock.test.mjs` asserted the embed stamp read *Today at …*, against a fixture timestamp
hard-coded as **2026-09-20**. On **2026-09-21** the same unchanged test read *Yesterday at …* and went red — and it went
red **on `main` AND on the v150 release commit alike**, so nothing had regressed; the calendar had moved. Found by the
`channel-streamers` build, fixed in `59716fe` by accepting all three stamp shapes (*Today at* / *Yesterday at* / a plain
date). **Status: WATCHING** — one sighting of the PATTERN, one fixture repaired.
**Why tolerated.** The fix is per-fixture and there is no guard: any node or python fixture that hard-codes a date and
then asserts a human-readable RELATIVE stamp carries the same fuse, and it fires at midnight rather than at a commit.
Sweeping the tree for every such literal today would cost more than the next sighting costs, and the failure is loud,
dated and harmless — a red gate on a test nobody touched, green the moment the shape is widened. Nothing in the bot
misbehaves; the test measures the wrong instant.
**What would change it.** A second sighting in a DIFFERENT file → a sweep for date literals in fixtures plus a shared
helper that builds the expected stamp from `Date.now()` instead of asserting a rendered word; a third, or one that
blocks a deploy gate at an awkward hour → the node tests get a pinned fake clock the way the python suite freezes time.
⚠️ Until then this stays a **read the log** item: a one-test red on a date-shaped assertion, green on a re-run the same
day, is this issue and not the build — check the fixture's date before debugging the code.

## KI-32 — `test_replacing_a_steps_picture_takes_the_old_one_away` fails about one gate in N on Windows, and passes alone — `WATCHING`

> 🟢 **2026-09-22 23:2x (branch `gate-names`) — CAUSE FOUND AND FIXED; it was a TEST-HARNESS defect, not the bot.**
> The api tests' `web_settings_now()` never set `database_path`, so every api test bot's guide media folder
> (`guides.media_root` = the database's folder + `guides/`) was ONE folder shared by every xdist worker — the default
> `data/guides`, or, when the shell exported `DATABASE_PATH`, the operator's own `C:\Users\nbasl\black-bloc-data\guides`
> (it did in this session; the test PNGs found there, 88 bytes each, were written by test runs and were left alone).
> Every worker's per-module database hands out media id **1**, so one worker's replace deleted or overwrote another
> worker's `1.png`: the upload test then served a 404 and the replace test found the "removed" file back on disk —
> both of this entry's sightings. **Reproduced deterministically:** `pytest -n 8 -p no:randomly
> tests/api/tools/test_guides.py -k picture` red **3 of 3**, the whole file red **3 of 5**; after the fix (commit
> `fdfa6de4`: `web_settings_at(path)` gives every api test bot the database path of its own tmp database, in
> `tests/api/conftest.py`) **0 of 8**, and every full-suite run since has been green on these tests. The bot's own
> replace path (`guides.drop_media`) was correct and is unchanged. **Status stays `WATCHING` only until the merge:**
> → `CLOSED` at the landing if that gate is green; a sighting after the merge means a second cause. Before that —

**Symptom.** The v148 deploy gate (2026-09-20 18:3x) went red on exactly one test, `tests/api/tools/test_guides.py:494`
`assert not pure.media_path(web, f"{first['id']}.png").exists()` — the replaced picture's file was still on disk when
the test looked — while the other 6919 passed. Re-run alone, straight after: **1 passed in 0.95 s**. The second gate run
was green with nothing changed. **Status: WATCHING** (one sighting).
**Why tolerated.** The shape is a Windows file-handle race: the old picture is unlinked while something (an xdist
sibling, an antivirus scan, the just-served response) still holds it, and `Path.unlink` on Windows either raises
`PermissionError` (swallowed by the replace path) or the directory entry lingers a beat. Nothing in the bot misbehaves — the
replace's next sweep or the next replace removes it — so this is a test that measures the wrong instant, not a leak.
**What would change it.** A second sighting → the test waits up to one second for the unlink (poll `exists()`), or the
replace path retries the unlink; a third → the media store is given a `remove()` that retries on `PermissionError` the way
`shutil.rmtree`'s Windows handler does. Either way it stays a **read the log** item: the gate names the test, and a
one-test red on THIS test with a green re-run is this issue, not the build.

🔴 **2026-09-21 12:0x — SECOND sighting, and this one REFUSED a release.** The v153 deploy gate's **first run**
went red on `tests/api/tools/test_guides.py::test_a_picture_is_uploaded_against_a_step_and_served_back_to_a_member`,
with **7236 passed** beside it. ⚠️ **It is a DIFFERENT test from the one this entry is titled for, in the SAME
file** — which widens the symptom from one assertion about a replaced picture to the guides media-file family as
a whole, and is itself the new information. Nothing reached Fly; the release shipped on the third run (**7237
passed, 3 skipped**; run 2 died of something else entirely — **KI-37**). ⚠️ **This MEETS the entry's own first
trigger.** *A second sighting → the test waits up to one second for the unlink (poll `exists()`), or the replace
path retries the unlink.* That work is now **owed, not conditional** — queued on [`TODO.md`](TODO.md) beside
KI-26's debugging session. Status stays `WATCHING` only because nothing has been spent on it yet; ⚠️ do not read
that word as *still undecided*. Before that —

**2026-09-20 23:3x — still ONE sighting, so nothing changes.** The v150 gate (**7118 passed, 3 skipped**) did not reproduce it and no build report between v148 and v150 names this test; the only test-run trouble across thirteen builds was KI-26. Status unchanged: `WATCHING`.

## KI-31 — Voice RECEIVE rests on a PRE-RELEASE extension, and it pins the image to Python 3.12 — `ACCEPTED`

**Symptom.** discord.py sends voice and does not receive it, so meeting minutes needs
**`discord-ext-voice-recv`**. Measured 2026-09-17 in a throwaway venv: the newest thing PyPI
will install is **`0.5.2a179`** — an ALPHA. There is no stable release. Two consequences the
prototype lives with:

1. `pyproject.toml` has to name a pre-release (`>=0.5.2a179,<0.6`) for pip to consider it at
   all, so `pip install` picks up whatever alpha is newest inside that range. An alpha that
   changes `AudioSink`'s shape breaks `black_bloc/minutes_audio.py:build_sink` at import time
   on the next image build, not on the next deploy of unchanged code.
2. ⚠️ **`discord/ext/voice_recv/sinks.py` imports `audioop`, which was REMOVED in Python
   3.13.** The image is `python:3.12-slim` today, so this is fine — but the base image can no
   longer be bumped without checking it. `discord.py`'s own `player.py` imports `audioop` too
   and already warns about it on every test run.

**Status.** `ACCEPTED` 2026-09-17, filed by the `minutes` prototype build from its own spike,
never from an incident. It installed and imported cleanly on Python 3.12.10 against the pinned
discord.py 2.7.1, and an Opus frame round-tripped 96 bytes → 3,840 bytes of PCM.

**Why tolerated.** There is no alternative: receiving Discord voice in Python means this
extension or writing the RTP/Opus layer by hand, and the feature ships **off** behind
`minutes_mode`, staff-only, on one prototype. The blast radius of a bad alpha is a `/minutes`
Start that refuses **in words** (`black_bloc/minutes_audio.py:NO_EXTENSION`) — the bot boots
and every other feature is untouched, because nothing imports the extension at module level.

**What would change it.** A stable `discord-ext-voice-recv` release — pin it exactly and drop
the pre-release specifier — or **one** image build whose `pip install` picks an alpha that will
not import, at which point the version gets pinned to `==0.5.2a179` in the same commit. Number:
**1** failed build, or **1** `Dockerfile` bump past Python 3.12.

## KI-30 — YouTube live detection reads the `/live` PAGE, and from a DATACENTER address that page is a bot check — `WATCHING`

> **2026-09-22 — branch `youtube-walled` (NOT merged, NOT deployed): (a) now rings a bell, and the channel-row path searches.** The live ESA rows (`youtube.live_seen … botcheck=True, video_id=None, announced=True`, 2026-09-21/22) came from the CHANNEL-ROW path, which never ran the 100-unit id search and wrote `announced: true` before `announce_info`'s opt-out gate silently dropped it (ESA's announce cell is off); five of the six rows sit on a deploy's boot minute because `live_video` is in memory. Now: the channel-row path searches + confirms once per broadcast like the member path, an opted-out channel's row reads `announced: false, because: opted_out` and spends nothing, and a walled page (bot check, no canonical link) writes ONE routine `youtube.probe_walled` row per state change with `live` True/False/**None** (None = the wall hid the marker; routing still counts it a miss). `/api/youtube/status` gains `walled` + `id_unknown`, and the Go-live card and `/youtube` staff lines say walled / id found or not / what a post links. Design ▸ *The walled channel rows*; sweeps `YW-a`…`YW-d`. **Still `WATCHING` — the page is still a scrape.** New number for *what would change it*: a `youtube.probe_walled` row with `live: null` for a channel whose stream was demonstrably still running (its Twitch/co-stream session open, or the streamer's own report); **one such row** is the proof that (a) has happened for real, and that a walled `None` must stop counting as a miss.

> **2026-09-18 10:07 — the wall is INTERMITTENT, not constant:** the v139 boot probe (17:05:49Z) read Pawpette's page with `botcheck false` from the same Fly address that got the wall on every probe of 2026-09-17 18:1x–19:11. So the id-from-canonical path and the searched-id path will both be exercised over time; `botcheck` on the status line is the tell for which one ran.

**Symptom.** The quota-free half of YouTube live detection (v126, `info/youtube-live-design.md` §A)
is a scrape: `GET https://www.youtube.com/channel/<id>/live`, parsed for `"isLive":true` and the
canonical `watch?v=<id>`. YouTube publishes no contract for either. ⚠️ **It has already happened
once, and not as a rename:** measured 2026-09-17 18:14–18:20 against a channel that WAS live
(`UC7ydYSU1nZOHB7nVV-As_XA`), the page differs by *where the request comes from* —

| | home machine | the Fly machine (datacenter) |
|---|---|---|
| status / size | 200, ~1.29 MB | 200, ~180 KB — *"Sign in to confirm you're not a bot"* |
| `"isLive":true` | ×2 (live) | ×1 live, ×0 offline — **the live signal survives** |
| `<link rel="canonical">` | the watch page | **absent** |
| `ytInitialData` | present | present — so the page reads as READABLE |
| `"videoId":"…"` | the live video | ~180 **unrelated** videos; the first is NOT the stream |

So v126 read live-without-an-id, `announceable` was false, and **nothing was logged, announced or
counted** — `quota_today` stayed 0 and both `probe_all` runs reported no error. The feature went
quiet in production while every test and every home-machine check stayed green.

**Status.** `WATCHING` — filed 2026-09-17 by the `youtube-live` build; **rewritten 2026-09-17 with
the measured shape, and the fix is on branch `youtube-live-fix`** (design ▸ Deviations ▸ *The
datacenter page*; sweeps **586–590**, which ⚠️ **can only be run against the live bot on Fly**).
⚠️ **2026-09-19 — "on branch `youtube-live-fix`" is STALE: the fix MERGED and SHIPPED as v133**
(2026-09-17 18:44, release `b20e4dc`) and the open-session row followed as **v135**
(`2dd8fcd`, 19:11). The banner at the top of this entry and the 10:07 intermittency note are
the current reading; this sentence is left in place, corrected rather than rewritten, because it
is what the entry said when it was filed. Sweeps **586–590** are still the owner's and still
un-run.
What the fix does: `video_id` comes ONLY from the canonical link (the `"videoId"` fallback is gone —
it returned a stranger's video); `live` is the routing fact, so *live, id unknown* is its own
outcome; with `YOUTUBE_API_KEY` **one** `search.list(eventType=live)` — **100 units, once per
broadcast, never per probe** — finds the id, and without a key the announcement links the channel's
own `/live` page with the title *Live now*; `Probe.botcheck` reaches the `/youtube` staff half,
`/api/youtube/status` and the Go-live page so staff can see why an id was missing.

**Why still tolerated / what is still open.** The probe is still a scrape of a page nobody
contracts. Three things would still break it and none of them rings a bell:
**(a)** the wall dropping `"isLive"` too — the channel then reads as a plain, quiet, *readable*
offline channel and writes **no** `youtube.probe_unreadable` row, because `ytInitialData` is still
there; **(b)** a keyless install behind the wall announcing a stream it cannot name (title *Live
now*, no thumbnail) — correct, but it looks like a bug to anyone who has not read this;
**(c)** the 100-unit search: one linked channel going live once a day is **101 of 10,000 units**,
ten channels is 1,010, but a regression that searched per probe instead of per broadcast would burn
the allowance before lunch (sweep `YL-m` is the human check, and the cog remembers the channel as
live in `live_video` so it cannot ask twice).
The blast radius is still bounded: `on_presence_update` catches a YouTube stream whenever the
streamer's Discord status is Streaming with a youtube.com link, which is how Pawpette's stream was
caught on 2026-09-17 before any of this existed.

**What would change it.** YouTube publishing a cheap live endpoint. ⚠️ **Two routes were measured
and are NOT one:** oEmbed on the `/live` URL is **404 everywhere**, and
`https://www.youtube.com/embed/live_stream?channel=<id>` carries **no `videoId` anywhere**. Until
then the regexes in `black_bloc/youtube_live.py` are the whole fix and the five fixtures under
`tests/fixtures/youtube_*_page.html` — including the two hand-written bot-check pages — are where a
new shape is pinned. `youtube_live_mode` still ships `off`. ⚠️ **The DEFAULT is off; the LIVE
value on this guild is `on`** (set by the owner 2026-09-17, read back on `/api/youtube/status`
at the v139 boot, 2026-09-18 10:07) — so this entry describes a feature that is running, not a
dormant one. ⚠️ **Not re-read 2026-09-19:** `/api/youtube/status` now answers `not_signed_in` to
an anonymous request, so the live mode cannot be confirmed without a Discord session.

## KI-29 — A WITHDRAWN request's forum post keeps its tag and is never archived — `ACCEPTED`

**Symptom.** With `request_forum_channel_id` set (v119), every request is a forum post tagged by where it is, and a decision tags + archives it. A member who WITHDRAWS a request (`withdraw_request` in `black_bloc/requests.py`) leaves the post open and still tagged as it was — the withdrawal reaches no Discord surface at all, and never did (it predates the forum).
**Status.** `ACCEPTED` 2026-09-17. Sweep row **483** (was `BT-m`) finds it.
**Why tolerated.** The build kept ONE place that edits a post (`notify_move`); giving `withdraw_request` its own tagger would be a second. Withdrawals are rare and the post is visibly stale to staff who open it.
**What would change it.** Route `withdraw_request` through `notify_move` with a look of its own (`withdrawn`), a seventh tag, and the archive — one small change in the next requests build.

## KI-28 — (RESOLVED 2026-09-17) A blank `golive_end_template` / `golive_end_author` cannot be set from Discord — `CLOSED`

✅ **Closed on branch `staff-reach`** (design [`info/staff-reach-design.md`](info/staff-reach-design.md) §C.3), by the one line
this entry's own *what would change it* named: `KeyModal.__init__` in `black_bloc/cogs/core.py` now
sets `self.field.required = key not in TEXT_MAY_BE_BLANK`, so Discord itself accepts an empty submit
for those two keys and only those two. The empty string then travels the path every other typed
value takes — `parse_value` → `set_key` → `SettingsStore.set` → `coerce_value`, which has allowed
`""` for `TEXT_MAY_BE_BLANK` since v117 — so one `settings.set` row is written and the value stored
is the same one the dashboard's **Just add the ending instead** button stores. **Clear** still
restores the shipped default, which is the other half of the pair and is right.

⚠️ **Verified in the test suite only** (`tests/cogs/test_core.py`: the modal's field is not required
for `golive_end_template` and is required for `golive_template`; an empty submit stores `""` and
leaves one `settings.set` row; an empty submit for any other text key is still refused in words).
**No Discord modal has been submitted** — sweep row `SR-l` is what proves it against the client.

The original text is kept below rather than deleted, as this file's other closed entries are.

## KI-28 (original text, kept for the record) — A blank `golive_end_template` / `golive_end_author` cannot be set from Discord — `ACCEPTED`

**Symptom.** The go-live end wording has a "blank = keep the live sentence and append the suffix" shape (v117, `info/golive-end-design.md` §A). From the dashboard it is reachable (the **Wording** card's *Just add the ending instead* button sends `PUT ""`). From Discord it is not: `/settings` ▸ the key card's modal is a `discord.ui.TextInput` with `required=True` (`cogs/core.py:1284`), so Discord itself refuses an empty submit, and **Clear** restores the shipped default rather than blanking.
**Status.** `ACCEPTED` 2026-09-17.
**Why tolerated.** The modal is shared by every text key; letting two keys submit empty means a per-key "may be blank" flag through that modal, which the go-live build was told not to touch while two other builds were in the file. The dashboard reaches the shape, and checklist 33's "both ways" holds for every VALUE except the empty one.
**What would change it.** `settings_store.TEXT_MAY_BE_BLANK` already names the two keys; teaching the key modal to read it (required = key not in that tuple) is the whole fix — one line in `cogs/core.py`, one test. Do it in the next build that touches `cogs/core.py`.

## KI-27 — Guide wording and screenshots are edited on the WEBSITE only; there is no Discord door — `WAIVED`

**Symptom:** the "every decision configurable BOTH ways" rule (`CLAUDE.md`, checklist 33) has a
Discord half for every setting, but a guide's steps, faults, facts and pictures can only be changed
on `guides.html` (**Edit this guide**). Discord's half of the feature is `/help`'s guide links and
nothing more. The six `guides_*` KEYS are both ways as always.

**Status:** `WAIVED` — owner, 2026-09-16 06:5x, verbatim *"A"* (fork F-G1 in
[`info/guides-design.md`](info/guides-design.md) §G: (a) none, (b) a `/guides` staff panel).

**Why tolerated:** a guide is up to forty steps of long text plus a table and pictures; Discord's
modal holds five fields, so a Discord editor would be a modal per step with no way to reorder or
see the whole. The website exists for exactly this shape of edit (the same reason `bot_bio` is the
Settings page's). The rule is about DECISIONS; guide copy is CONTENT.

**What would change it:** a staffer asking for it **once** — then fork (b) as designed, a `/guides`
panel with **A guide…** → **A step…** → a modal, built on `panels.py`.

## KI-26 — `deploy.ps1` hangs mid-pytest with every xdist worker idle, roughly one run in four — `WATCHING`

> 🟢 **2026-09-22 23:2x (branch `gate-names`, not yet merged or deployed) — THE CAUSE IS FOUND, WITH STACKS, AND A FIX IS MEASURED.**
> A hang-watch plugin (scratch, not committed) dumped every thread of every worker that sat on one test for 30 s. On a
> hung `-n auto` run **32 of 32 workers** were blocked in the same frame: `asyncio.new_event_loop` →
> `ProactorEventLoop._make_self_pipe` → `socket._fallback_socketpair` → `lsock.accept()`. On Windows every new asyncio
> loop builds its self-pipe as a **TCP connection over 127.0.0.1**, and each close leaves **one loopback `TIME_WAIT`**
> (measured: 300 loops → 300 `TIME_WAIT`). A run makes thousands (pytest-asyncio's per-test loops plus every
> `TestClient` portal); the machine's dynamic range is **16,384 ports** (`netsh int ipv4 show dynamicport tcp`) and
> **13,565** loopback `TIME_WAIT` were counted mid-run with other suites on the box. When the range runs dry the
> fallback's non-blocking `connect` fails silently and `accept()` waits for ever — every worker at once, CPU flat,
> exactly this entry's symptom. It also explains the old clues: worse with a *second* suite on the box, worse at
> `-n auto` (faster churn), late in the run (ports accumulate), and even a serial run can hit it on a crowded machine.
> **Fix:** `tests/loopback.py` (loaded for every run by `-p tests.loopback` in `pyproject.toml`) sets `SO_LINGER 0` on
> both ends of every `socket.socketpair`, so a close is a reset and leaves no `TIME_WAIT` (300 loops → **0**). Across
> a whole suite the loopback `TIME_WAIT` count now stays at **~50** from start to end (it read 6,306 before the first
> fixed run). **Measured:** before the fix `-n auto` was green **2 of 6** (four runs hung all their workers);
> after it **3 of 3** at `-n auto`, **5 of 5** at `-n 16`, and 2 of 3 at `-n 8` — the measured table is in [`access/deploy.md`](access/deploy.md) (*"The gate's pytest step"*).
> Also new: **`pytest-timeout` (120 s, thread method)** turns any hang into a NAMED failure — `worker 'gwN' crashed
> while running '<nodeid>'`, exit 1, in the junit file and the gate's `FAILED TESTS:` block — so a stall can no
> longer sit idle; and the gate now runs **`-n 16`**.
> ⚠️ **One hang of a DIFFERENT shape remained** (run D8, `-n 8`, after the fix): ONE worker, loopback `TIME_WAIT` at
> 49, stuck in an async FIXTURE setup for `tests/cogs/moderation/test_modmail.py::test_two_reconciles_at_boot_post_exactly_one_ticket_button`,
> the proactor loop idle and **no aiosqlite thread alive** in `threading.enumerate()`. One sighting; the timeout
> named it after 120 s. It came back ONCE more, same test, on the first gate-shaped run of the tree merged with `main`
> (23:2x, `-n 16`, real shell environment: **1 failed, 7357 passed**; the re-run and eight more were green) — so
> **2 sightings in 21 full runs after the loopback fix, 0 in ~27 before it**. ⚠️ That split is suggestive, not proof
> (and the pre-fix runs were also dying of the port stall), but it means the reset-on-close change is a SUSPECT for
> this shape — a lost self-pipe wake-up would look exactly like an idle proactor loop with its work already done.
> Hypotheses only, neither measured: that, or a module-scoped `aiosqlite` connection whose worker thread is gone
> while `is_connected` still reads true. A hang-watch plugin that also dumps each open loop's `_ready` queue was
> armed for eight more runs and they were all green, so the queue was never seen.
> ⚠️ **Other worktrees and the main tree do not have the fix until this merges**, and TIME_WAIT is machine-wide: their
> suites still drain the same range. Four stray `pytest` controllers from other sessions (started 20:31, 22:27,
> 22:33, 22:58) were running at 23:14 and were NOT touched.
> **Status stays `WATCHING`** — a named failure is not no failure. **What would change it now:** **ten consecutive
> deploy gates on the merged fix with zero `crashed while running` lines** → `CLOSED`. Any gate that prints one →
> read its test name: `test_two_reconciles_at_boot_post_exactly_one_ticket_button` (or any single-worker
> fixture-setup hang) is the D8 shape — a THIRD sighting of it gets its own entry and a session with the loop dump; a
> `_fallback_socketpair` stack means the fix is not loaded. Before that —

> 🔴 **2026-09-21 17:5x — a new finding, not a new sighting of the stall itself: an agent that kills every `chrome-headless-shell` process BY NAME can hit ANOTHER BUILD'S render mid-flight.** During the `golive-settings-help` build's headless CDP render (deviation 2 of that follow-up), a process-name kill aimed at cleaning up its own scratch profile risked taking out a sibling agent's `chrome-headless-shell` too — the same class of mistake this entry already warns about for `python.exe` and `.venv` workers, now confirmed for the browser side as well. ⚠️ **Count and target by PID or process tree, never by image name**, for any process family a concurrent agent might also be running. This is a finding filed under KI-26 because it is the same root cause (killing a shared-name process on a machine with concurrent agents), not a new count. Before that —
> 🔴 **2026-09-21 12:2x — TWENTY-TWO PLUS AT LEAST SIX TODAY, so the count is AT LEAST TWENTY-EIGHT — and the debugging session this entry has asked for since 2026-09-19 is STILL not run.** The two v153 builds hit it **six times between them**: three on `member-optout` (stalls at 89 / 98 / 93 % of pytest) and three on `youtube-video-link` (stalls and one crash). ⚠️ **The `member-optout` builder's finding is the most useful thing this entry has gained in a dozen sightings, and it says the diagnosis has often been WRONG: a stalled gate is usually a SECOND GATE.** The PowerShell tool BACKGROUNDS a run it has timed out on, so the retry starts a second 8-worker suite beside the first, the two fight for the cores, and the newer one looks deadlocked — it is not. ⚠️ **Count the `.venv` python workers before killing anything** (`Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*.venv*python*' }`), and kill by process tree, never by image name. ⚠️ **New variant, from the `youtube-video-link` builder: `exit 255` — an xdist worker DEATH**, not the silent idle-worker stall this entry was filed for; same remedy (read the log, retry), different signature, so a gate reporting `exit 255` is this entry too. None of the six reached Fly and none produced a bad deploy — the cost is still only lost time. ⚠️ **The count is now approximate on purpose** (*at least* twenty-eight): sightings are still recorded where each build reports them, which is the same gap that once let this entry say thirteen while the real figure was twenty-two. Before that —
> 🔴 **2026-09-20 23:3x — the count stands at TWENTY-TWO, and the debugging session this entry's own triggers called for has STILL not been run.** Nine sightings (fourteen to twenty-two) piled up between the note below and the v150 landing; each was recorded where its build reported it (`TODO.md` / `DONE.md`) and not here, which is how this entry came to say THIRTEEN while the real figure was twenty-two — that gap is the finding. Tonight's, in order: the **sixteenth** killed a v150 deploy attempt outright (stalled at 99 % for 14 minutes with three suites on the box, killed by its own process tree; nothing shipped and its stray `Release v150` commit was dropped unpushed); **seventeen** and **eighteen** on the `end-wording` build and **twenty-one** on its wording-default fix; **nineteen** and **twenty** on the `discord-mock` build; **twenty-two** on the `raidtrain-page` build. Every one was green on a retry, and the v150 gate that finally shipped passed **7118 passed, 3 skipped**. ⚠️ So the cost is still lost time and never a bad deploy — but it is now lost time on nine runs and one killed deploy. Before that —
> **2026-09-20 17:2x — THIRTEEN sightings: the `costream` build hit it TWICE, both on `> file` runs** (spawn-shape, 8 workers flat at 0.0156 s CPU, no output for 10+ minutes against an 82 s baseline; both green on one retry). Its trick for killing the right tree with two suites on the box: `-o cache_dir=<its worktree>/.pytest_cache` so its own root is identifiable on the command line. Before that —
> **2026-09-20 16:5x — ELEVEN sightings, the SECOND on a `> file` run, and ⚠️ this entry's own trigger is now met on both counts** (the `golive-page` build's `BB_REVERSE=1 pytest -n 8` stalled at 87 % with the log untouched for seven minutes; killed by its own process tree — picked out by the `PYTHONPATH` in its `env -i` line, because a sibling suite was running beside it; green in 83 s on the retry). ⚠️ New measured fact: **the killed xdist run's exit code read 0** while the log said `[gw0] node down: Not properly terminated` — a wrapper that trusts the code will call a killed run green; read the log. The debugging session this entry asks for is on the TODO's queue. Before that —
> **2026-09-18 16:5x — TEN sightings, and ⚠️ one of them was on a `> file` run** (the `frontdoor-shadow` build's post-commit `BB_REVERSE=1` run stalled at ~91 % with the log untouched for 8 minutes, 10 idle workers; killed by process tree, green in 58 s on the retry). The `boot-reconcile-once` build also hit a SERIAL hang with output going to the tool's pipe (empty log past 600 s; 8.9 s with `> file`). This entry's own *what would change it* says a `> file` hang means spend a session on it — that session is queued after the Sunday reset. Before that —
> **2026-09-18 16:3x — NINE sightings.** The ninth: the `posts-paste` build's `BB_REVERSE=1 pytest -n 8` hung silent at spawn for ten minutes; killed by process tree, green in 61 s on the retry with output to a file. Before that —
> **2026-09-17 23:1x — EIGHT sightings.** The eighth: the `events-where-hint` build's `BB_REVERSE=1 pytest -n 8` hung at spawn (8 workers flat at 0.0156 s CPU, 10 min in; the forward run had taken 66 s) — killed by process tree, passed in 53 s on the retry with output redirected to a file. Before that —
> **2026-09-17 — seven sightings.** Three of today's were PLAIN `pytest -n auto` runs inside build worktrees (not `deploy.ps1`), one of them serial (`-p no:cacheprovider`, no xdist) — so the hang is not xdist-only and not deploy-only; and one build's `taskkill /F /IM python.exe` during a stall killed every python on the machine (the run was not hung, three agents were sharing the cores). Kill by process tree, never by image name.

**Symptom:** the deploy gate's `pytest -q -n auto` stops making progress — 33 idle pythons,
the log untouched for over a minute, CPU flat — at spawn (twice) or at 81–92 % of the run
(three times). Five times so far, measured off `deploys.log` 2026-09-11: the runs before **v94**
(10:42, detached, 92 %), **v97** (13:45, detached, 88 %), **v98** (14:09, foreground console, at
spawn), **v99** (19:52, 81 %) and **v100** (15:55, detached, 82 %) — 2026-09-06 and 2026-09-10.
(`gotchas.md` and the docs-pass finding said "v103 attempt 1"; the v103 line itself says *no hang*.) Not a failing test: the same commit passes
forward and under `BB_REVERSE=1` on the retry, in 26–30 s. The hung tree cannot be stopped from
the session; the owner kills it.

**Status:** `WATCHING` — filed 2026-09-11 10:55 from the docs-pass finding (c). The retry is in
[`info/gotchas.md`](info/gotchas.md) (*"`deploy.ps1` hangs mid-pytest…"*), which owns the
what-to-do; this entry owns the count.

**Why tolerated:** the retry has shipped every time and costs two minutes; nothing reaches Fly
until the gate passes, so a hang is lost time, never a bad deploy. Cause unestablished — the
pattern — detached runs and one foreground console run hung; every run through the PowerShell
tool with `*> file` (the ritual since v98) has passed, 0 of 7 — points at console stdout handling of
xdist workers rather than the suite.

**What would change it:** a sixth hang **on a PowerShell-tool `*> file` run** (none of the five was),
or the count passing **10** — then spend a session on it: run the gate under `-n auto -p no:cacheprovider`
with `PYTEST_DEBUG` and a worker log, and compare a hung run's `py-spy dump` against a live one.
Runs since v103: v103–v110 (eight) all passed the gate first time.

🔴 **2026-09-19 — BOTH TRIGGERS ARE NOW MET, and this entry is the record of that.** The tenth
sighting (2026-09-18 16:5x) was on a `> file` run — the exact case the first clause said none of
the five was — and the count has reached **10**, which is the second clause. So the debugging
session above is no longer conditional; it is owed. It is queued on [`TODO.md`](TODO.md) behind
the Sunday reset, and the two CI runs CANCELLED at the workflow's 20-minute timeout
(2026-09-17 night) are the same stall reaching GitHub Actions, where nobody is watching for it.
Status stays `WATCHING` only because nothing has been spent on it yet — ⚠️ **do not read that
word as "still undecided"**. Number now: **0** — the next thing to do is the session, not another
sighting.

## KI-25 — Discord is the ONLY sign-in; the phase-8 Google SSO for the owner was never built — `WAIVED`

**Symptom:** phase 8 decision 3 (2026-08-26, [`info/phase8-design.md`](info/phase8-design.md))
planned two identity providers — Discord OAuth2 for staff and Google OAuth2 allow-listed to the
owner's account, linked by a `user_identities` table. Neither the Google flow nor the table exists
(`grep -ri google black_bloc/` finds only the YouTube Data API host). The owner signs in through
Discord like every staffer and gets owner rights because `api/auth.py:222` matches the guild's
`owner_id`.

**Status:** `WAIVED` — owner, 2026-09-11 10:50, verbatim *"A discord is fine"* (answer to the
docs-pass question, option A: drop it).

**Why tolerated:** every gate on the site is a Discord role, so a Google identity would grant no
permission the Discord one does not already carry; a second provider is a second login surface
and a second secret to hold. The one thing it would buy is a Discord-independent door if the
owner's Discord account were locked or Discord were down.

**What would change it:** the owner being locked out of Discord with something on the site that
cannot wait — that is the break-glass case. If it ever happens, the design is still written in
`phase8-design.md` decision 3; build it then, not before.

## KI-24 — (RESOLVED 2026-09-06, **LIVE v97**) A `before_loop` failure bypasses `@loop.error` — `CLOSED`

**Was:** all fourteen `before_loop`s awaited `bot.wait_until_ready()` bare, and discord.py 2.7.1
runs `before_loop` outside the `try` that dispatches to `error`, so a failure there killed the
loop with no restart and no `last_error`. **Now:** one helper, `black_bloc/loops.py:wait_ready`,
hands the exception to the loop's own `@loop.error` handler; two AST guards in
`tests/test_loops.py` keep it that way and a real `tasks.Loop` test proves the restart. The whole
design, what was measured, and what deviated from it:
[`info/loop-guard-design.md`](info/loop-guard-design.md).

✅ **Resolved and SHIPPED — merge `689eff5`, deployed as v97 (`aa44e3b`, 2026-09-06 13:52,
`deploys.log:96`)**, in the same deploy that took `OPERATOR_READ_TOKEN` live. Re-measured
2026-09-11: `black_bloc/loops.py` is present, `wait_ready` has **27** call sites across the
package, and the only bare `bot.wait_until_ready()` left in `black_bloc/` is the one inside the
helper (`loops.py:12`). ⚠️ Still never exercised against a real `before_loop` failure on the live
bot — the proof is the suite plus the AST guards, not an incident. Kept here rather than deleted
so the reasoning stays findable; nothing about it is open.

## KI-22 — `/purge`'s two log kinds cannot say which door made them — `ACCEPTED`

**Symptom.** Every other moderation kind is built with `kind_via` (`logkinds.py`), so the same
action taken from the dashboard is written `web.mod.<kind>` and the Logs page can label it
Via=Website. `mod.purged` and `mod.purge_failed` are built as bare string literals inside
`ModCommands.purge` and cannot. They are the last two mod kinds without it — measured while
writing `mod-panel-design.md`, and unchanged by the wave-4 build, which was scoped to how the
case record is READ and CORRECTED.

**Status:** `ACCEPTED`.

**Why tolerated.** `/purge` has **no web door**: there is no `POST /api/mod/purge`, so nothing
can currently write a `web.mod.purged` row, and nothing double-posts. The defect is latent, not
live. Adding `kind_via` now would be an edit inside the punishment path, which the panel build
deliberately left with a zero-line diff — that zero diff is the evidence the punishment path did
not move, and spending it on a kind nobody can emit twice is a poor trade.

**What would change it.** **One** — the moment a `POST /api/mod/purge` route is proposed. At that
point the two kinds get `kind_via` and a `via` parameter in the same commit as the route, and
`tests/test_logkinds.py`'s AST guard is what catches it if they do not.

✅ **Re-measured 2026-09-11 (v108):** unchanged in both halves — the two literals are still bare
at `black_bloc/cogs/moderation/modcmds.py:874` (`"mod.purge_failed"`) and `:895` (`"mod.purged"`),
and `grep` over `black_bloc/api/` finds **no** `POST /api/mod/purge`, so the defect is still
latent. The number stands.

## KI-14 — A memory note about a THIRD PERSON is prevented, not proved impossible — `ACCEPTED`

**Symptom.** `chat_memory.parse_distilled` is what stops a preference note
naming somebody other than the person whose profile it is (§D2-definition rule
1). It is three layers, all of them heuristics: the distil prompt says so; a
phrase list catches the obvious carriers (`said`, `told`, `according to`, `<@`,
the departure family); and `other_names(guild, user_id)` drops any note
containing another member's display name. None of them is a proof, and the last
one only works for a name the guild cache actually holds — a nickname the person
typed that no member wears would pass.

**Status.** `ACCEPTED` for the dark launch (`chat_memory_mode` ships **off**).

**Why tolerated.** The blast radius is one sentence, visible to one person, and
that person can read every note the bot holds about them and drop any of them —
`/memory` opens one panel with the lines numbered, a **Forget one of these…**
picker and **Forget everything**; §D2-definition rule 7 makes that panel the
enforcement of last resort. A note is also never a quote: the
six-word shingle check against the window text (`shingles`) means whatever leaks
is the model's paraphrase, not somebody's words. **Measured 2026-09-02, §J:** in
run 1 the model produced third-person threads twice in six attempts on a window
containing a third-person question; after the `OUTCOMES` fix all three run-2
attempts were dropped. There is no measurement of the rate against real
conversations — none have been distilled.

**What would change it.** Number: **one leaked note reported by a member**, or
**one note about a third person found by the owner in the DB**. At that point
the fix is not a longer phrase list — it is to stop keeping `threads` at all
(§I already excludes cross-person memory), since the note leaks measured so far
were all threads, never preferences.

## KI-15 — A raid-train slot keeps the Twitch name it was claimed with — `ACCEPTED`

**Symptom.** `raid_slots.twitch_login` is COPIED at claim time from
`golive_links`. A member who presses **Unlink** on `/golive`, or who re-links to a
different channel, keeps their slot and the lineup keeps naming the OLD login —
so the streamer before them may raid a channel that no longer belongs to
anybody. Nothing tells the organizer.

**Status.** `ACCEPTED` (Phase 18, §I). Measured only in the test suite; no raid
train has ever run against live Discord.

**Why tolerated.** The copy is deliberate: reading the link live would mean a
lineup that silently rewrites itself between the reminder DM and the hour it
describes, and a slot that empties itself when somebody unlinks for an unrelated
reason. A stale name is visible and fixable (`/raidtrain unassign` then claim
again); a lineup that changes under people is neither.

**What would change it.** **1 report** of a raid landing on a wrong channel.
The fix is a sweep step that re-reads `golive_links` for un-started slots and
logs `raidtrain.login_stale` rather than rewriting anything.

## KI-16 — Raid-train check-in sees only what go-live sees — `ACCEPTED`

**Symptom.** D9's check-in (`checked_in_at`, and the "the train moves" line in
the thread) reads `golive.open_sessions`. A slot holder whose Discord presence
is hidden and who is not Twitch-linked never has an open session, so they are
never marked live and the thread never says the train moved on — even though
they are streaming.

**Status.** `ACCEPTED` (Phase 18, §I). Test-suite evidence only.

**Why tolerated.** It is the same limit as F1 go-live, from the same source, and
the phase deliberately reuses that one signal rather than growing a second
detector. Nothing breaks: the lineup, the reminders and the raid order are all
unaffected — only the ✅ and the one thread line are missing.

**What would change it.** Whatever closes the go-live gap closes this one too
(Twitch EventSub with a public callback, or a `/raidtrain checkin` command a
holder runs by hand). Number: **1 report** of a train whose lineup showed nobody
checked in while it was visibly running.

## KI-19 — Log rows written before 2026-09-03 keep their retired kinds — `ACCEPTED`

**Symptom.** The double-post fix (owner report, 2026-09-03) stopped the routes
writing a second `web.<kind>` line, and eight kinds are now never written again:
`web.event.cancel`, `web.honeypot.ban`, `web.mod.apply`, `web.mod.rule`,
`web.modmail.close`, `web.poll.cancel`, `web.poll.end`, `web.tempvoice.forget`
(plus `web.mod.warn`/`timeout`/`untimeout`/`kick`/`ban`/`unban`). Rows already in
`action_log` keep them. They still render, still filter onto the right feature
page (`feature_of` reads the head, which is unchanged) and still classify as
routine — with **one exception**: `honeypot.ban` was removed from `ROUTINE`, and
`.ban` is an `IMPORTANT_SUFFIXES` entry, so historical `web.honeypot.ban` rows
now read as *important* rather than routine.

⚠️ **Four more joined them on 2026-09-05** (the modmail panel, Build A): the website's
`web.modmail.block`, `web.modmail.unblock`, `web.modmail.snippet` and
`web.modmail.snippet_remove` are now written as `web.modmail.blocked`, `.unblocked`,
`.snippet_saved` and `.snippet_removed`, so both doors spell the same act the same way.
The four old spellings were deleted from `logkinds.ROUTINE` in the same commit, because a
classification entry nothing emits is a table nobody maintains
(`tests/test_logkinds.py::test_no_classification_entry_is_dead`). Rows already in
`action_log` keep the old kinds and are now **unclassified**, which `is_important` reads as
*not important* — the same quiet they had as `ROUTINE` entries, so nothing on the Logs page
moves. ⚠️ The reverse is worth knowing: the NEW `web.modmail.blocked` and `.unblocked` are
**important**, where `web.modmail.block`/`.unblock` were routine — that is the
classification bug this rename fixes (blocking somebody was loud from Discord and quiet
from the website).

**Why tolerated.** Rewriting history in `action_log` is worse than a handful of
retired kind strings: the log is the audit trail, and a migration that edits it
destroys the thing it exists to prove. The one classification change moves a
honeypot ban from quiet to loud, which matches how the replacement kind
(`honeypot.banned`) classifies — so the old rows now agree with the new ones
rather than disagreeing.

**What would change it.** Nothing planned. Number: **1 report** of a stale kind
confusing somebody reading the Logs page — the fix would be a display alias, not
a migration.

## KI-20 — An ephemeral panel's buttons die on a bot restart — `WATCHING`

**Symptom.** Every panel built on `black_bloc/panels.py` — ⚠️ **measured 2026-09-11 there are
now EIGHTEEN of them, not the two this entry was written about**: `applications`, `automod`,
`birthday`, `chat`, `event`, `golive`, `honeypot`, `memory`, `mod`, `modmail`, `pings`, `poll`,
`raidtrain`, `request`, `rolemenu`, `settings`, `voice`, `youtube` (one `<feature>_panel_minutes`
key each in `settings_store.KEY_TYPES`, **every one defaulting to 10**). It was `/request`
(`requests-panel-design.md`) and, from 2026-09-03, `/poll`
(`polls-panel-design.md`) alone when this was written. Each
opens an ephemeral `discord.ui.View` with a real
timeout (`<feature>_panel_minutes`), not a persistent `View(timeout=None)` re-registered
with `bot.add_view()` on `cog_load` (the pattern `TempVoicePanel` uses). If the
bot restarts while a member's panel or request card is still open, every button
and select on it answers Discord's own "This interaction failed" — the view's
Python object is gone, and nothing on the message itself says so. ⚠️ **A second way the same footer goes
missing, and this one is a setting anybody can walk into:** `<feature>_panel_minutes`
of **15 or more** loses the "this panel has gone quiet" footer entirely, because
the footer is written through a Discord interaction token that expires 15 minutes
after the click that made it — the buttons simply stop answering with nothing to
explain why. All **eighteen** such keys ship at **10** for exactly this reason
(re-measured 2026-09-11: `SettingsStore.default` returns 10 for every one) and each one's own
help text in `settings_store.py` `KEY_HELP` carries the warning; the value is deliberately NOT
clamped.

**Why tolerated.** A panel is a moment, not a post: it exists for the seconds a
member spends filing or a staffer spends triaging, then it is gone (its own
timeout disables it and says "run /request again"). Restarts are rare and short,
and the only other affected surface today with a real timeout, `MemberPickView`
in temp voice, has carried the same limitation since Phase 2 with no report.

**What would change it.** A persistent `DynamicItem`-based panel (`custom_id`
carrying the request id, so a restart can re-derive an item's target) if staff
ask for it — the same shape `TempVoicePanel`'s own buttons already use, minus
the request-card state that currently lives only in the View's Python object.
Number: **0 reports** so far; nothing planned.

> ⚠️ **2026-09-19 — the EXPOSURE changed, the defect did not.** Until 2026-09-18 16:08 a panel
> could only be opened in `#blackbloc-logs` by the owner or a mod, so "restarts are rare and
> short" was a claim about two or three people. `TEST_MODE` is off and events, requests and
> modmail are **live to members**, so an ordinary member can now be mid-`/request` when a deploy
> lands — and every deploy is a restart. Nothing about the code moved; what moved is who meets
> it. The number to watch is unchanged (**1 report** from a member that a card stopped
> answering), but it is now a number a member can generate. Still `WATCHING`, still **0
> reports**, and ⚠️ **not re-measured** — the eighteen `*_panel_minutes` keys were last counted
> 2026-09-11 and were not re-imported today.

## KI-18 — Editing a question changes the form, never the answers already sent — `ACCEPTED`

**Symptom.** An application stores its answers as a snapshot of `{label, answer}` pairs
(`black_bloc/applications.py:answers_json`). Rewording question 3, or removing it, changes
what the NEXT applicant is asked and leaves every card already on the record exactly as it
was — so two cards side by side can show different questions.

**Status.** `ACCEPTED` — chosen, not discovered (Phase 19 §A).

**Why tolerated.** The alternative is worse in both directions: joining answers to the
live question rows would silently relabel somebody's answer with a question they were
never asked, and refusing to edit a question once anybody has applied would freeze the
form at its first draft. A card is a record of what was asked and what was said.

**What would change it.** Staff reporting confusion between two cards. The fix then is a
version number on the question set and a "asked as it stood on <date>" line on the card,
not live joins.

## KI-17 — Black Bloc cannot confirm the twitch.tv Team invite was ever sent — `ACCEPTED`

**Symptom.** Approving a Twitch Team application grants the Discord role and names the
person who has to send the twitch.tv invite (`owner` + `next_step` on the form), but the
invite itself is a human clicking a button on twitch.tv. Black Bloc has no way to see
whether it was sent, accepted, or forgotten — so an application can read **approved** here
while the person is not on the Team at all.

**Status.** `ACCEPTED` — measured at design time, 2026-09-02: Twitch publishes **no Teams
API**. Only the Team owner can add members, and only from twitch.tv.

**Why tolerated.** Everything around the click is automated — the form, the review, the
role, both DMs — and the design turns the one manual step into a named nudge on the card
rather than pretending it does not exist. The alternative (asking the applicant to confirm)
adds a step that can also be forgotten and proves nothing.

**What would change it.** Twitch publishing a Teams API, or **1** applicant reporting they
never got an invite. The cheap fix for the second is a per-form reminder on the card after
N days, not a new integration.

## KI-13 — (CLOSED 2026-09-18, moot) An upload announcement can be up to ~25 minutes late — `CLOSED`

✅ **CLOSED (moot) 2026-09-18 — the uploads half was removed.** Owner: *"the youtube uploader we should just fully trash"*; branch `youtube-uploads-removal`, design [`info/youtube-uploads-removal-design.md`](info/youtube-uploads-removal-design.md). There is no upload announcement any more, and no sweep to be late: `poller`, `poll_once`, `fetch_feed` and `youtube_poll_minutes` are all gone. The LIVE half has its own clock, `youtube_live_poll_minutes` (2–60, default 5), and its own lateness story — which is not this one, because a probe reads a page rather than a 15-minute-cached feed. The body below is kept for the record, as this file's other closed entries are. ⚠️ **Verified in the suite and by reading the tree, not against live Discord** — a worktree holds no token.

**Symptom.** Two delays add up. The feed is edge-cached: the live response
carries `Cache-Control: public, max-age=900` and an `Age` header (measured
2026-09-02: `Age: 56` on a fresh fetch), so a publish can be up to **15
minutes** old before the feed even shows it. On top of that the sweep runs
every `youtube_poll_minutes` — **10** by default. Worst case is therefore about
**25 minutes** between hitting publish and the post appearing.

**Status.** `ACCEPTED` — there is no push path without a key, and no push path
at all short of PubSubHubbub, which needs a public callback URL this bot does
not have.

**Why tolerated.** An upload is not time-critical the way a go-live post is;
nobody is being told to come and watch something that is already half over. The
gap is a setting, so the owner can shorten it — but not below 5 minutes, and the
validator says why: below the feed's own 15-minute cache, a shorter sweep
re-fetches the same bytes and finds nothing new any sooner.

**What would change it.** The owner reporting the lateness as a problem, or
uploads becoming time-critical (a premiere people are meant to arrive for). The
fix then is PubSubHubbub with a public callback, not a shorter poll.

## KI-12 — (CLOSED 2026-09-18, moot) YouTube's own uploads feed answers only about half the time — `CLOSED`

✅ **CLOSED (moot) 2026-09-18 — the uploads half was removed.** Owner: *"the youtube uploader we should just fully trash"*; branch `youtube-uploads-removal`, design [`info/youtube-uploads-removal-design.md`](info/youtube-uploads-removal-design.md). Nothing fetches that feed any more — `FEED_URL`, `FEED_ATTEMPTS`, `fetch_feed` and the Atom parser are deleted, and `tests/fixtures/youtube_feed.xml` went with them. ⚠️ **The measurement that killed the feature is worth keeping: on 2026-09-17 21:07 the endpoint answered 404 for every channel from every address, 20/20** — the ~50% of 2026-09-02 had become 0%. The one thing the feed still did, handing back a channel TITLE at link time, now costs one `channels.list` unit and only where `YOUTUBE_API_KEY` is set; without a key a channel simply goes by its `UC…` id. The body below is kept for the record, as this file's other closed entries are. ⚠️ **Verified in the suite and by reading the tree, not against live Discord** — a worktree holds no token.

**Symptom.** `https://www.youtube.com/feeds/videos.xml?channel_id=UC…` returns
HTTP 404 or 500 for a channel that plainly exists, at random. Measured
2026-09-02 from this machine, one channel, 30 requests two seconds apart:
**15 × 200, 12 × 404, 3 × 500**. It is not per-channel — two other well-known
channels took 11 and 24 tries respectively before their first 200 — and it is
not the network: `youtube.com/robots.txt`, the channel page itself and an
unrelated Atom feed all answered 200 throughout, and the failures carry
YouTube's own `Server: YouTube RSS Feeds server` header.

**Status.** `ACCEPTED` — worked around, not fixed. `YouTubeClient.fetch_feed`
retries up to `FEED_ATTEMPTS` (4) per sweep, and a feed that never answers
raises `YouTubeError`, which the poller treats as a **transient fetch failure**
— never as "that channel is gone". Nothing is unlinked and nothing is seeded on
a failure; the next sweep tries again.

**Why tolerated.** It is YouTube's server, there is no alternative keyless
source of the same data, and a 10-minute sweep with 4 tries each makes a missed
upload very unlikely to be missed twice. The cost of a failure is lateness, not
a wrong announcement.

**What would change it.** A measured 200-rate below **~25%** (at which four
tries stops being enough), or **1 upload confirmed missed for a whole day**.
Either would mean moving to the Data API's `playlistItems.list` on the uploads
playlist, which needs `YOUTUBE_API_KEY` and spends quota per channel per sweep.

## KI-11 — (CLOSED 2026-09-18, moot) Without `YOUTUBE_API_KEY` a live broadcast can be announced as an upload — `CLOSED`

✅ **CLOSED (moot) 2026-09-18 — the uploads half was removed.** Owner: *"the youtube uploader we should just fully trash"*; branch `youtube-uploads-removal`, design [`info/youtube-uploads-removal-design.md`](info/youtube-uploads-removal-design.md). Nothing is announced as an upload any more, so there is no wrong sentence left to write: `render`, `classify`, `classify_row`, `youtube_template` and `youtube_announce_shorts` are gone. A YouTube broadcast is announced by the LIVE half through go-live, which is what this entry's *what would change it* was reaching for. ⚠️ **`youtube_mode` shipped `off` and has been removed; the feature's on/off is `youtube_live_mode` now, which also ships `off`.** The keyless gap the live half still has is a different one and lives in **KI-30**. The body below is kept for the record, as this file's other closed entries are. ⚠️ **Verified in the suite and by reading the tree, not against live Discord** — a worktree holds no token.

**Symptom.** The Atom feed carries no duration and no live-stream marker — it is
`yt:videoId`, `title`, `published`, `link` and the author, and nothing else
(measured 2026-09-02 against a real feed). So a scheduled or live broadcast that
appears in the feed is indistinguishable from an ordinary upload. D6's keyless
fallback skips an entry only while its uploader has an **open go-live session on
platform `youtube`**; a broadcast published while they have no such session open
is announced as "just dropped a new video".

**Status.** `ACCEPTED` — the design decided this (D6) rather than discovering it.

**Why tolerated.** Go-live presence already covers streams, so the overlap is
narrow: it needs a YouTube broadcast whose author is linked here AND who is not
showing as live on Discord at that moment. Shorts do NOT have this problem —
the feed links them as `/shorts/<id>`, so they are told apart with no key at
all, which is better than the design assumed.

**What would change it.** `YOUTUBE_API_KEY` being set (the cog then asks
`videos.list` for `liveStreamingDetails` and marks it `live`), or **1
mis-announcement** the owner notices. Until then `youtube_mode` ships `off`.

## KI-10 — The OLD process logs `asyncio: Unclosed client session` while a rolling deploy replaces it — `WATCHING`

**Symptom.** In the Fly log stream during the `d777f57` deploy (2026-09-03
00:42:59Z), the machine being retired printed `ERROR asyncio: Unclosed client
session` on its way down. The NEW process booted clean (15 cogs — that is the
**2026-09-03** boot line, kept as read; the tree holds **19** cogs today — logged in,
birthdays import ran) and the line has not reappeared since.

**Status.** `WATCHING` — seen **twice**, both at shutdown only, on the process that was
already being stopped: the `d777f57` deploy (2026-09-03) and the **v111** deploy (2026-09-16 16:06:56Z,
the retiring machine's last line before the new one's `database ready` at 16:07:02Z). Still never on a
running machine, still one per deploy.

**Why tolerated.** An aiohttp `ClientSession` that was never `close()`d is
reported by its finaliser at interpreter exit; it costs nothing after the
process is gone and cannot affect the replacement machine. Candidates are the
Twitch/YouTube/Groq/webhook clients that are opened lazily and never closed in
`bot.py`'s `close()` path — not confirmed; the log line does not name the
owner.

**What would change it.** The same line appearing on a RUNNING machine (not at
shutdown), or more than one per deploy — then it is a leak, not a finaliser
grumble, and `bot.py`'s shutdown path gets an explicit close for each lazily
opened session. Next deploy: read the retiring machine's tail and count.

## KI-1 — (CLOSED 2026-09-01) SQLite database lives inside a OneDrive-synced folder

**Was:** the entry below. **Now:** local `.env` `DATABASE_PATH` points at
`C:/Users/nbasl/black-bloc-data/black_bloc.sqlite3` (outside OneDrive); the old
file was copied there and the original under `data/` is inert (deletable at
will). The hosted deployment always used the Fly volume and was never affected.

## KI-1 (original text, kept for the record) — SQLite database lives inside a OneDrive-synced folder — `WATCHING`

**Symptom:** the default `DATABASE_PATH=data/black_bloc.sqlite3` sits under
`OneDrive/Documents/...`. OneDrive syncing a live SQLite file (plus its `-wal`
and `-shm` sidecars) is a known source of "database is locked" errors and, in
the worst case, a torn copy in the cloud.
**Why tolerated:** the DB is empty and the bot is not yet running unattended;
the hosted deployment uses a Fly volume at `/data`, not this folder.
**What would change it:** the first real table with data, OR the bot running
locally for more than a test session. Fix is one line in `.env`
(`DATABASE_PATH=C:\...\outside-onedrive\black_bloc.sqlite3`).

## KI-2 — Slash commands are re-synced to the dev guild on EVERY startup — `ACCEPTED`

**Symptom:** `bot.py:setup_hook` calls `tree.sync(guild=...)` unconditionally
when `DEV_GUILD_ID` is set. Command sync is rate-limited by Discord; frequent
restarts can trip it (symptom is a 429 in the log and a startup delay).
**Why tolerated:** guild-scoped sync is instant and the limit is generous for
a single dev guild; the convenience of "restart and the new command is there"
is worth it during development.
**What would change it:** the bot serving more than one guild — then commands
sync globally, once, via an explicit command, not at boot. Number: **>1 guild**.

⚠️ **Second sync on the same boot, 2026-08-27 — `ACCEPTED` too.** Command
visibility (`info/code-notes.md` § `command_visibility.py`) re-applies the
stored feature modes right after the startup sync, so a boot with
`rolemenu_mode` **off** spends a *second* guild sync about five seconds after
the first. It only happens when a hidden-when-off feature is actually off and
the tree therefore had to change; a boot with everything on syncs once, as
before. The alternative — applying visibility *before* the startup sync — was
rejected because `copy_global_to` re-seeds the guild mapping from the globals
and would put the hidden command straight back. **What would change it:** a 429
on startup in the log. Number: **1 observed 429**.

## KI-4 — Modmail transcripts link to attachments that expire — `ACCEPTED`

**Symptom:** transcripts store attachment URLs as Discord CDN links, which
carry signed `?ex=…&is=…&hm=…` parameters and stop resolving after ~24 h.
A transcript read a week later has dead attachment links (the text is
intact).
**Why tolerated:** re-uploading every attachment into the log channel would
double storage and re-post member content; the incumbent Modmail bot has the
same limitation. The transcript header says the links expire.
**What would change it:** a staff request to keep attachments — then mirror
them to the Fly volume (or R2) at close time. Number: **any** such request.

## KI-5 — (MOOT 2026-09-18 — test mode is OFF) Test mode does not stop a web modmail reply or a web `/warn` from reaching a member — `ACCEPTED`

> ⚠️ **MOOT since 2026-09-18 16:08.** The owner lifted `TEST_MODE` (cutover **P5**), so there is
> no guard in production and nothing is being "stopped" for anything to leak past. Every door
> this entry describes — a web modmail reply, a web `/warn`, honeypot and temp-voice setup —
> now reaches a real member or makes a real channel **by design**, which was always the point
> of the lift. What SURVIVES the lift and is worth keeping: **nothing in modmail may be read as
> "safe because test mode is on"** — that sentence was true then and is trivially true now, and
> the **practice ticket** is still the one place a reply DMs nobody. The proposed fix
> (`TEST_DM_ALLOWLIST`) is dead with the guard; if a future rehearsal ever turns `TEST_MODE`
> back on, read the body below as it stands. The body is kept, not deleted, as this file's other
> closed entries are. ⚠️ Read from the settings/secret state reported at the lift, **not**
> re-measured against the live bot.

**Symptom:** while `TEST_MODE`, `POST /api/modmail/tickets/{id}/reply` and
`POST /api/mod/warn` (and their slash-command twins) still DM the real
member; `POST /api/honeypot/setup` and `POST /api/tempvoice/setup` still
create real channels (inside the test category). The guard sees channel
sends and edits, not DMs or channel creation.
**Why tolerated:** DMs are inside the owner's test policy ("you're allowed to
be dm'd to test too"); the slash commands behave identically, so the web is
not a wider door; channel creation is place-gated to the test category.
**What would change it:** the first time a real member receives a test DM by
mistake — then add a `TEST_DM_ALLOWLIST` of user ids the guard permits.
Number: **1 incident**.
⚠️ **The modmail PRACTICE ticket is the one modmail DM test mode does stop**
(2026-09-05, Build B): a practice reply and a practice close send nothing at
all, and log **no** `modmail.dm_failed` — a suppressed DM is not a failed one.
That is deliberate and is why the practice ticket is the safe place to try the
card. A REAL ticket's **Reply** button reaches a real member exactly as
`/reply` does, test mode or not — nothing in modmail may be read as "safe
because test mode is on".

## KI-6 — (SUPERSEDED 2026-08-31) A stolen session cookie stays valid after sign-out — `CLOSED`

**Was:** the entry below — a stateless signed cookie that logout could not revoke,
accepted while the owner was the only site user. **Its threshold (">1 site user")
was crossed by Phase 13**, which opened the dashboard to any signed-in guild
member. **Now:** schema 17 adds a `sessions` table; the cookie payload carries a
session id, every authenticated request checks it live (30 s in-process verdict
cache, logout poisons the cache before the row), and `POST /api/auth/logout`
revokes. Deployed 2026-08-31 (`0c49257`) — every cookie minted before it became
invalid at that deploy, one sign-in each. **Residual, accepted:** if the database
is down, `alive()` answers True and the request proceeds on signature + expiry
alone — refusing would turn a sqlite blip into "everyone signed out" while every
data route already refuses via `require_db`; revocation is unenforceable exactly
while nothing else works.

## KI-6 (original text, kept for the record) — A stolen session cookie stays valid for up to 7 days after sign-out — `ACCEPTED`

**Symptom:** the site session is a stateless signed cookie
(`__Host-bb_session`); `/api/auth/logout` clears it in the browser but
cannot revoke a copy taken elsewhere until it expires (`SESSION_TTL_SECONDS`,
7 d).
**Why tolerated:** every request re-checks staff status against the live
guild cache, so a stolen cookie is useless the moment the account loses its
staff role or leaves; the cookie is `__Host-`, `Secure`, `HttpOnly`, so
theft needs the browser itself.
**What would change it:** a second staff member (i.e. any user other than
the owner) signing in — then add a `sessions` table with a per-session id
in the signed payload and a revocation on logout. Number: **>1 site user**.

⚠️ **THRESHOLD LIKELY CROSSED — owner decision needed (flagged by the docs
audit, 2026-08-31, not acted on).** Phase 13 (live `8036918`, 2026-08-27 20:15)
opened the dashboard to **any signed-in guild member** in the member-only
Requests view, so ">1 site user" is no longer a hypothetical: the design intends
many. The same reasoning touches **KI-9** (anonymous poll votes: "Number: >1
person with `/data` access, or 1 sensitive poll"). Neither number was measured
today — nobody checked how many distinct accounts have actually signed in. Both
entries stay `ACCEPTED` until the owner rules; this note exists so the next
session does not read the old threshold as still un-met.

## KI-8 — A role-menu panel in a channel Black Bloc cannot reach is retried on every flip — `ACCEPTED`

> ⚠️ **2026-09-19 — one clause below is history: `role_menu.would_unpost`'s "which today is
> every panel outside `TEST_CHANNEL_ID`".** `TEST_MODE` went off 2026-09-18 16:08, so the guard
> no longer refuses any channel and `would_unpost` is not the normal path any more. **The entry
> itself is UNAFFECTED and still `ACCEPTED`** — the real symptom is `role_menu.unpost_failed`
> for a channel that is gone, invisible or refuses the delete, which has nothing to do with test
> mode. ⚠️ `rolemenu_mode` is still **off**, so nothing here has been exercised either way.

**Symptom:** turning `rolemenu_mode` **off** logs `role_menu.unpost_failed` for
any menu whose channel is gone, invisible, or refuses the delete, and keeps the
row's `message_id`. Every later flip tries that menu again and logs the same
line, forever. `role_menu.would_unpost` behaves the same way while test mode
refuses the channel — which today is **every** panel outside
`TEST_CHANNEL_ID`.
**Why tolerated:** the alternative is worse. Clearing `message_id` on a failure
would tell the database the panel is down while it is still up in the channel,
and the next `on` would post a **second** panel beside it — two live selects
with the same `custom_id`. A repeated log line is cheap; a duplicated panel is
the kind of thing somebody has to clean up by hand. The sweep never blocks on
it: one failure costs one menu and the loop carries on
(`info/code-notes.md` § `rolemenu_panels.py:108`).
**What would change it:** a menu whose channel has genuinely been **deleted**
(`on_guild_channel_delete`) should clear both `channel_id` and `message_id`, at
which point the row stops being retried because there is nothing left to
reconcile. Number: **any menu logging `unpost_failed` on more than 2
consecutive flips** with a channel that no longer exists.

## KI-7 — (SUPERSEDED 2026-08-27) The dashboard Health tab lists no loops but the presence one — `CLOSED`

**Was:** `api/status.py` built the loop list by asking every cog for
`get_tasks()`. `commands.Cog` in discord.py 2.7.1 has no such method — measured
2026-08-27 at runtime, `hasattr(commands.Cog, "get_tasks")` is `False` — and only
`cogs/presence.py` defined one, so the other five loop-owning cogs contributed
nothing and their `loop_health` readers were never called.
**Now:** `api/status.py:_loops` discovers loops **generically**, by walking each
cog's class and instance dicts for `discord.ext.tasks.Loop` instances and asking
`cog.loop_health(<attribute name>)` for the health beside each one. `get_tasks`
is gone from `presence.py` — one home, and the fix was one reader rather than
the five near-identical three-line methods this entry proposed. The Health tab
now lists **seven** loops across six cogs; every cog's `loop_health` already
accepted its own attribute name, so no mapping table was needed. The API shape
(`cog`, `name`, `running`, `failed`, `state`, `next_iteration`, `last_ok_at`,
`last_error`) is unchanged, so `site/` and `site/mock/contract.json` needed no
edit. A parametrised test in `tests/api/test_status.py` builds each real cog and
asserts every loop it owns reaches `/api/status` with the `last_ok_at` the cog
records — so a cog added later with a loop is covered by adding one row.
**Residual, accepted:** discovery is by TYPE, so a loop a cog holds somewhere
`getattr` cannot reach (inside a list, a dict, a lazily-built object) is still
invisible. Nothing in the tree does that, and the honest "this loop does not
record its last success yet" text still covers a cog with no `loop_health`.

## KI-3 — (SUPERSEDED 2026-08-26 by Phase 8a) The FastAPI companion has no authentication — `CLOSED`

**Was:** off by default, localhost only, no auth. **Now:** the API is public
on `https://blackbloc.heygabi.ai` with Discord-OAuth sessions on every route
except `/health`; rate-limited login/callback; CSP/HSTS. The three original
"why tolerated" premises are all false, so the entry is closed rather than
edited. `/health` exposing guild count + latency publicly is the residual
and is accepted (it is what a status page is for).

## KI-3 (original text, kept for the record) — The FastAPI companion has no authentication — `ACCEPTED`

**Symptom:** `/health` (and anything added later) answers anyone who can reach
the port.
**Why tolerated:** `API_ENABLED` defaults to `false`; when on, it binds to
`127.0.0.1` and `fly.toml` deliberately has no `[http_service]`, so nothing is
reachable from outside the machine/container.
**What would change it:** the first route that is exposed beyond localhost
(a dashboard, a webhook receiver). At that point auth is a blocker for the
exposure, not a follow-up.

## KI-9 — (SUPERSEDED 2026-08-31) Anonymous panel-poll votes are hashed, not unlinkable — `CLOSED` for new polls

**Was:** the entry below — a truncated per-poll SHA-256 anyone with the DB could
confirm a guess against; its "what would change it" (a second person with data
access / the member-facing turn) arrived with Phase 13. **Now:** schema 18 stores
a `vote_scheme` per poll; polls created while `POLL_VOTE_SECRET` is set (it was
set 2026-08-31) use HMAC-SHA256, so confirming a guess needs the key, not just
the table. Old polls keep their scheme — changing it under an open poll would
hand voters a second vote. A poll keyed to a lost secret refuses votes in words
(never double-counts). The live `poll_votes` table was empty at cut-over, so in
practice every real anonymous vote will be keyed.

## KI-9 (original text, kept for the record) — Anonymous panel-poll votes are hashed, not unlinkable — `ACCEPTED`

**Symptom:** a poll created with `anonymous` on runs on Black Bloc's own panel and stores one `poll_votes` row per voter keyed by a truncated per-poll SHA-256 of the member id (no name, no id). Someone holding BOTH the database and a member list could confirm a guess ("did member X vote?") by recomputing the hash; they cannot enumerate voters from the table alone.
**Why tolerated:** a panel must store one row per person to stop double voting; a keyed MAC would need a secret that has to live somewhere (env + Fly secret + recovery doc) for a threat that requires database access, which already exposes far more than poll choices. The dashboard and every embed never show per-voter rows for anonymous polls. Recorded in `info/code-notes.md` § "polls (10b)".
**What would change it:** a second staff member with database access, or the first anonymous poll about anything sensitive (staff elections, conduct). Number: **>1 person with `/data` access**, or **1 sensitive poll** — then move to an HMAC with a `POLL_VOTE_SECRET`.
