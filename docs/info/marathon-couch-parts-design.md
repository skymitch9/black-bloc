# A couch is not a runner — commentators are listed everywhere and posted nowhere (request #16)

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-11-13 09:3x Phoenix)** — dispatches
> to Opus as branch `couch-parts` once the before-dispatch usage read exists. **Last verified: 2026-11-13 09:2x** against `main`
> `8556fcc8` by reading the code, and against the live site through the operator token (request #16; `GET /api/marathons/2`).
> ⚠️ NOT verified: anything in Discord; the bot was not run; no browser.

## 1. The ask

Request #16 (*[Tech Bro] Sky*, 2026-11-13 15:25Z, `open`): *"fix couch and inter.... whatever that word is roles so they dont get
tracked as runners but show up similar to host. interviewee, interviewer, talent, inter...., host, couch, etc not runner should be a
category for notice but not shout out. Runner should remain as is."* The owner (09:2x): *"lets setup request 16 too"*.

## 2. Measured

- Three parts exist: `runner` · `host` · `commentator` (`marathon_sources.py:52-55`). The GDQ tracker reader fills them from its
  `runners` / `hosts` / `commentators` columns (`:311`). **Couch = `commentator`.** Horaro (`:377`) and Oengus (`:450`) make every
  named person a `runner`; Horaro reads only the players column (`PLAYER_COLUMNS`, `:130`) — no couch column exists there.
- **Interviewee / interviewer / talent exist in no reader.** The tracker serves interviews from a separate endpoint the bot never
  fetches (`grep -ri interview black_bloc` → nothing). They are a NEW FEED, not a reclassification — out of scope here (§6).
- `commentators_count` (`marathon.py:385`, passed at `cogs/content/marathon.py:2379`) is a code constant: `False` only for
  `gdq_hotfix`, `True` for every other source. So on a tracker marathon a matched commentator carries `counts` unset and is one of
  `mt.ours()`.
- Three places say *"not a host, so a runner"*: `marathon_announce.role_of` (`:288`, the shoutout and every public post),
  `marathon_hosts.is_runner_run` (`:170`, run EVENTS — ignores `counts` entirely), `marathon_overlay` (`:219`).
  `marathon_baf_event.has_runner` (`:222`) and the schedule page's `baf_run` are already runner-only.
- **It bites today.** GDQ Express (`marathons.id 2`, tracker) run_list 09:2x: *Yakuza Kiwami 2* 2026-11-13 21:42Z (14:42 Phoenix)
  `PopNoTarts:commentator`, `ours=True`, `shoutable=True`, `shouted=False`; *Mighty Morphin Power Rangers* 2026-11-14 20:24Z
  `AshSaidHi:commentator`, same flags. Without the fix both get the runner shoutout.

## 3. Design — invert the negative tests; never alias couch to host

A commentator is **listed and visible everywhere, posted nowhere** unless the new switch says otherwise. Hosts are untouched:
host blocks (`marathon_host_highlights.py:56,61`), the host spotlight note and `host_only` keep meaning HOST only.

| Surface | Today for a BaF couch | After |
|---|---|---|
| Live shoutout (`marathon_announce`) | `role_of` → RUNNER → shouted under *Runner announcements* | role `COUCH`; `decide()` answers the new `marathon_couch_announcements` switch (default **off**) |
| Runner posts / public highlight (`marathon_runner_posts`, `marathon_public`) | through `baf_on()` as RUNNER | role `COUCH` → not posted while the switch is off |
| Reminder line (15-min heads-up) | named as a runner | named with the couch part word, same line, no ping of their own |
| Run EVENT (`marathon_hosts.is_runner_run`) | couch-only run makes an event | `part == RUNNER` only (positive test) |
| Overlay (`marathon_overlay:219`) | couch shown among runners | runners only |
| Schedule page `baf_run`, `has_runner` | runner-only already | unchanged |
| People drawer / Who is who, `/runs` | listed with part tag | unchanged — the LISTING is the "notice" |
| `/runs` BaF archive (`baf_runs.py:244` uses `mt.ours`) | a couch counts as a BaF run | **unchanged in this build** — ask the owner separately if couch appearances belong on `/runs` |

- New role constant `COUCH` in `marathon_announce` beside `RUNNER` / `HOST`; `role_of` becomes a three-way positive mapping
  (`RUNNER` → RUNNER, `HOST` → HOST, else COUCH). `runs_it` stays `role == RUNNER`.
- New settings key (rule 33, every word editable): `marathon_couch_announcements` (bool, default false; label beside *Host
  announcements* on the marathon drawer's Posts card and on Settings). The part words already exist
  (`marathon_part_commentator`, `_done`); the owner may rename the word to *couch* on the site.
- `commentators_count` stays as is (it decides *who is ours*, not *who is posted*); do not touch it in this build.
- Log kinds: `marathon.shout_skipped` gains `because: couch` when the switch is off. No schema change. Registry +1 key.

## 4. Tests (mirror the package)

`tests/test_marathon_announce.py` (role_of three-way; decide() with couch on/off), `tests/test_marathon_hosts.py` (couch-only run is
not makeable), `tests/test_marathon_overlay.py`, `tests/cogs/content/test_marathon_announce.py` (the live shoutout for a couch-only
run is skipped with `because: couch`; a runner on the same run still shouts), a mock row + label for the new key, `check.mjs` green.

## 5. Rollout

Branch `couch-parts` off `main`; merge, gate, deploy per `access/deploy.md` with the previous release noted in `deploys.log`;
**target: live before 14:42 Phoenix today.** Verify live: `GET /api/marathons/2` run_list still lists PopNoTarts as commentator;
at 14:42 the thread shows no runner shoutout for Yakuza Kiwami 2 and `/api/actions?kind=marathon.shout_skipped` has the row.
Request #16 stays `open` → staff press *in progress* at dispatch; *ready to check* only on the owner's sign-off.

## 6. Out of scope, asked separately

Interviews (interviewee / interviewer) — a new tracker feed, notice-only, same COUCH treatment. ✅ Owner Q1 DECIDED (a)
2026-11-13 09:3x: *"interviewers and interviewees are apart of intersitial"* — the tracker files them under INTERSTITIALS, so the
follow-up build reads that feed, not a runs column. Tracked in `TODO.md` 2026-11-13 as a follow-up after this build.
