"""Runs the steps of .github/workflows/ci.yml in order, inside the CI mirror's container."""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

WORKFLOW = Path(".github/workflows/ci.yml")
DOCKERFILE = Path("Dockerfile.ci")
STEP_KEYS = {"name", "run", "uses", "with"}
GROUPS = ("lint", "tests", "site")
BASH = ("bash", "--noprofile", "--norc", "-eo", "pipefail", "-c")


def steps_of(text: str) -> list[dict]:
    """The `gate` job's steps as {name, run, uses}; refuses any key the mirror does not model."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "steps:")
    indent = len(lines[start]) - len(lines[start].lstrip()) + 2
    steps: list[dict] = []
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        depth = len(line) - len(line.lstrip())
        if depth < indent:
            break
        body = line.strip()
        if depth == indent and body.startswith("- "):
            steps.append({})
            body = body[2:]
            depth += 2
        key, _, value = body.partition(":")
        if depth == indent + 2:
            if key not in STEP_KEYS:
                raise ValueError(f"ci.yml step key {key!r} is not mirrored (line {i + 1})")
            value = value.strip()
            if key == "run" and value in ("|", "|-"):
                block = []
                i += 1
                while i < len(lines) and (
                    not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > depth
                ):
                    block.append(lines[i].strip())
                    i += 1
                steps[-1]["run"] = "\n".join(block).strip() + "\n"
                continue
            if key != "with":
                quoted = len(value) > 1 and value[0] == value[-1] and value[0] in "\"'"
                steps[-1][key] = value[1:-1] if quoted else value
        i += 1
    for n, step in enumerate(steps, 1):
        step.setdefault("name", step.get("run", step.get("uses", f"step {n}")).splitlines()[0])
    return steps


def group_of(step: dict) -> str | None:
    """Which -Only group a step belongs to; None for setup steps."""
    run = step.get("run", "")
    if not run or run.startswith("pip install"):
        return None
    if run.startswith("ruff"):
        return "lint"
    if "pytest" in run:
        return "tests"
    return "site"


def install_line() -> str:
    """The pip command the image ran, read off Dockerfile.ci."""
    found = re.search(r"pip install [^\n&\\]+", DOCKERFILE.read_text(encoding="utf-8"))
    return found.group(0).strip() if found else ""


def main(argv: list[str]) -> int:
    only = argv[0] if argv else ""
    if only and only not in GROUPS:
        print(f"unknown group {only!r}; use one of {', '.join(GROUPS)}")
        return 2
    for name in sorted(n for n in os.environ if n.startswith("BB_")):
        print(f"== env {name}={os.environ[name]}")
    results: list[tuple[str, str, float]] = []
    started = time.monotonic()
    for step in steps_of(WORKFLOW.read_text(encoding="utf-8")):
        name, run = step["name"], step.get("run")
        if not run:
            print(f"== {name}: provided by the image")
            continue
        if run.startswith("pip install"):
            same = run.strip() == install_line()
            print(f"== {name}: done at image build ({'same command' if same else 'DIFFERS'})")
            if not same:
                print(f"   ci.yml runs `{run.strip()}`, Dockerfile.ci runs `{install_line()}`")
                return 1
            continue
        if only and group_of(step) != only:
            continue
        print(f"== {name}", flush=True)
        t0 = time.monotonic()
        code = subprocess.run([*BASH, run]).returncode
        took = time.monotonic() - t0
        outcome = "ok" if code == 0 else f"FAILED (exit {code})"
        print(f"== {name}: {outcome} in {took:.1f}s", flush=True)
        results.append((name, outcome, took))
        if code != 0:
            total = time.monotonic() - started
            print(f"CI MIRROR RED: '{name}' failed after {len(results)} step(s), {total:.0f}s")
            return 1
    total = time.monotonic() - started
    print(f"CI MIRROR GREEN: {len(results)} step(s) passed in {total:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
