"""Copy the estate's canonical personality manifest over Black Bloc's synced copy."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOCAL = REPO / "black_bloc" / "personality_pool.json"
CANONICAL = (
    REPO.parent / "catalog-platform" / "apps" / "discord-worker" / "src" / "personality-pool.json"
)
SOURCE_REPO = "catalog-platform"

NO_SOURCE = (
    "Nothing was copied: the canonical personality manifest is not at {path}.\n"
    "That file is GABI's half of the shared pool and it does not exist yet — until the "
    "catalog-platform build lands it, {local} is hand-built from personality.ts and is the "
    "only copy there is.\n"
    "If the sibling checkout lives somewhere else, point at it with --from PATH."
)
NOT_JSON = "Nothing was copied: {path} could not be read as JSON — {reason}."
NO_TROPES = "Nothing was copied: {path} lists no tropes, so it is not a usable manifest."
NO_HEAD = (
    "Copied nothing: {path} was read, but `git rev-parse` could not name the commit of the "
    "repository it came from ({reason}), so the copy could not be stamped with its provenance.\n"
    "Run the script from a checkout, or fix the source repository's git state."
)
DONE = "Copied {path}\n     to {local}\n  pool v{version}, synced_from {stamp}{same}"
UNCHANGED = " (unchanged — the local copy already said this)"


def git_says(where: Path, *args: str) -> str:
    try:
        found = subprocess.run(
            ["git", "-C", str(where), "rev-parse", *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise SystemExit(NO_HEAD.format(path=where, reason=str(detail).strip())) from exc
    return found.stdout.strip()


def head_of(where: Path) -> str:
    """The short commit of the repository the manifest came from; its own worded failure."""
    return git_says(where, "--short", "HEAD")


def name_of(where: Path) -> str:
    """The main checkout's folder name, so a worktree at C:/lcw/pool still says catalog-platform."""
    common = Path(git_says(where, "--path-format=absolute", "--git-common-dir"))
    return common.parent.name or SOURCE_REPO


def repo_of(source: Path) -> Path:
    found = source.resolve().parent
    while found.parent != found:
        if (found / ".git").exists():
            return found
        found = found.parent
    return source.resolve().parent


def read_source(source: Path) -> dict:
    if not source.is_file():
        raise SystemExit(NO_SOURCE.format(path=source, local=LOCAL))
    try:
        found = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(NOT_JSON.format(path=source, reason=exc)) from exc
    if not isinstance(found, dict) or not found.get("tropes"):
        raise SystemExit(NO_TROPES.format(path=source))
    return found


def stamped(text: str, stamp: str) -> str:
    """The canonical's own bytes plus one key, so a diff between the two copies is one line."""
    if "synced_from" in json.loads(text):
        manifest = {key: value for key, value in json.loads(text).items() if key != "synced_from"}
        return json.dumps({**manifest, "synced_from": stamp}, indent=2, ensure_ascii=False) + "\n"
    body = text.rstrip().rstrip("}").rstrip()
    return f'{body},\n  "synced_from": {json.dumps(stamp)}\n}}\n'


def sync(source: Path, local: Path) -> str:
    manifest = read_source(source)
    repo = repo_of(source)
    stamp = f"{name_of(repo)}@{head_of(repo)}"
    was = local.read_text(encoding="utf-8") if local.is_file() else ""
    text = stamped(source.read_text(encoding="utf-8").replace("\r\n", "\n"), stamp)
    assert json.loads(text)["synced_from"] == stamp
    with local.open("w", encoding="utf-8", newline="\n") as out:
        out.write(text)
    return DONE.format(
        path=source,
        local=local,
        version=manifest.get("version"),
        stamp=stamp,
        same=UNCHANGED if was == text else "",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="source", type=Path, default=CANONICAL)
    parser.add_argument("--to", dest="local", type=Path, default=LOCAL)
    args = parser.parse_args(argv)
    print(sync(args.source, args.local))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            sys.exit(1)
        raise
