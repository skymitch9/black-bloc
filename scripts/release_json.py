"""Writes site/public/assets/release.json for scripts/deploy.ps1 (guides-design §C4.2)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from black_bloc import guides

USAGE = (
    "usage: BB_LAST_DEPLOY_LINE=<last deploys.log line> release_json.py <short commit> <out path>"
    "  (paths on stdin; the line travels in the environment because PowerShell 5.1 splits a"
    " native argument on the quotes a deploys.log line may carry)"
)
LINE_VAR = "BB_LAST_DEPLOY_LINE"


def main(argv: list[str]) -> int:
    last_line = os.environ.get(LINE_VAR, "")
    if len(argv) != 3 or not last_line.strip():
        print(USAGE, file=sys.stderr)
        return 2
    commit, out = argv[1], argv[2]
    paths = [one.strip() for one in sys.stdin.read().splitlines() if one.strip()]
    release = guides.next_release(last_line)
    if release is None:
        print(
            "release_json: no v<N> in the last deploys.log line, so this release is named after "
            "its commit. Every guide screenshot will be marked stale on the next boot.",
            file=sys.stderr,
        )
    payload = guides.release_payload(paths, release, commit)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
