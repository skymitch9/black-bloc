# The local CI mirror — run GitHub's `ci.yml` on this machine, in Linux, before pushing

> **Audience:** Claude sessions and the owner. **Status:** TRACKED — no secrets involved.
> Last verified: **2026-10-07** (branch `ci-mirror`, Docker Desktop 29.1.3, Linux engine, 32 CPUs / 31 GB to the VM):
> full run **GREEN, 15 steps, 174 s wall** (`11909 passed` in 161 s of it); image build **47 s** with `--no-cache`
> (48 s the first time); a deliberately broken test in a scratch clone outside the repo was **refused by the hook**
> (`1 failed, 11909 passed`, `PUSH REFUSED`, 3 min); a docs-only `git push` through the hook **skipped in 0.4 s**;
> `BB_SKIP_CI_MIRROR=1` **skipped and said so**. ⚠️ **NOT verified:** a run with `-Cpus 4` through the whole suite
> (only the site steps), a real `BB_FAKE_NOW` (the switch did not exist yet; only that the variable reaches the
> container), the hook on the MAIN checkout (only in a scratch clone), and any comparison against a red GitHub run.

## What it mirrors

| GitHub (`ci.yml`) | The mirror |
|---|---|
| `ubuntu-latest` | `python:3.12-slim` (Debian) in Docker Desktop's Linux VM — `Dockerfile.ci` |
| `setup-python` 3.12, `setup-node` 20 | Python 3.12 from the base image; node 20 copied from `node:20-bookworm-slim` |
| `Install: pip install -e ".[dev]"` | Run once at image build; the runner checks `ci.yml`'s command equals `Dockerfile.ci`'s and fails if not |
| Every other `run:` step | Read from `ci.yml` **at run time** by `scripts/ci_local.py`, run in the same order with `bash --noprofile --norc -eo pipefail` (GitHub's shell) |
| `CI=true` | Set |

There is no second list of steps to keep in sync: a step added to `ci.yml` runs in the mirror the next time.
A step key the mirror does not model (`env:`, `shell:`, `if:`, `working-directory:`, …) makes the runner stop with
its name, so drift is loud. `tests/scripts/test_ci_local.py` checks the parser against the real `ci.yml`.

The tree is mounted read-only at `/src` and copied into a tmpfs `/work` (`.git`, `.venv*`, `.claude`, `data/*`,
`.env`, caches left out) — nothing is written to the checkout. `/tmp` is a tmpfs too. Both matter for speed:
straight off the bind mount with `/tmp` on the overlay the suite took **390 s**; with both in memory **161 s**
(measured 2026-10-07). For comparison the native Windows suite at `-n 16` took **210 s** the same day.

## Run it

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ci-local.ps1            # everything, working tree
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ci-local.ps1 -Only tests # lint | tests | site
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ci-local.ps1 -FakeNow 2026-12-25T10:00:00+00:00
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ci-local.ps1 -Ref HEAD   # a commit, not the tree
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ci-local.ps1 -Cpus 4     # GitHub's runner size
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ci-local.ps1 -Rebuild
```

- The image is `black-bloc-ci:<12 hex of pyproject.toml's sha256><4 hex of Dockerfile.ci's>`; it is built when
  that tag is missing, so a dependency change rebuilds and a code change does not.
- Every `BB_*` variable in the shell goes into the container (`-FakeNow` sets `BB_FAKE_NOW`); the runner prints
  each one first.
- Output: `== <step>` then `== <step>: ok|FAILED (exit n) in Ns`; it stops at the first red step and ends with
  `CI MIRROR GREEN: …` or `CI MIRROR RED: '<step>' failed …`. Exit 0 green, 1 red, 3 not run (Docker down, image
  did not build, bad `-Ref`).
- `-Ref` exports the commit with `git archive` to `%TEMP%` (Windows `tar.exe` by full path — Git Bash's `tar` on
  `PATH` reads `C:` as a remote host) and deletes it after.

## The pre-push hook

`scripts/githooks/pre-push`. On a push to `main` whose new commits touch anything outside `docs/**` and top-level
`*.md` (the same `paths-ignore` as `ci.yml`), it runs `scripts/ci-local.ps1 -Ref <the pushed commit>` and refuses
the push if it is not green, naming the failed step and how to run it by hand. Docs-only pushes and pushes to other
branches skip in under a second. If the remote's old commit is not known locally it runs (safe side).

**Enable once, on the main checkout** (it is per clone, and this branch's worktree deliberately did not run it):

```powershell
git config core.hooksPath scripts/githooks
```

**Escape hatch:** `BB_SKIP_CI_MIRROR=1 git push` — the hook prints `CI MIRROR SKIPPED by BB_SKIP_CI_MIRROR=1`.
Emergency only; GitHub's run is then the only check.

## What it does NOT mirror

- **The runner's CPU count.** GitHub's standard Linux runner for a public repo has 4 vCPUs; `-n auto` here sees 32.
  `-Cpus 4` pins the container to 4 CPUs and xdist counts the affinity mask, so `-n auto` spawns 4 workers
  (checked 2026-10-07) — closer, but not the same machine or speed.
- **The `actions/*` steps themselves** (checkout, setup-python's pip cache, setup-node). Their effect is the image.
- **Network to GitHub / PyPI at run time.** Dependencies are frozen at image build; GitHub resolves them fresh on
  every run, so a new upstream release can break GitHub and not the mirror until `-Rebuild`.
- **The wall clock of GitHub's machine.** Date-dependent tests see this machine's clock unless `BB_FAKE_NOW` is set.
- **A checkout is not a copy of the tree.** Without `-Ref`, untracked files in the tree are in the run; GitHub has
  only what is committed. The hook always uses `-Ref`.
