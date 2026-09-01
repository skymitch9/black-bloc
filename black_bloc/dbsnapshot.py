"""Consistent snapshot of the live database, for the nightly backup pull."""

import sqlite3

from .config import load_settings


def snapshot(source: str, target: str) -> None:
    live = sqlite3.connect(source)
    copy = sqlite3.connect(target)
    try:
        live.backup(copy)
    finally:
        copy.close()
        live.close()


def target_for(source: str) -> str:
    return f"{source.rsplit('.', 1)[0]}-nightly-snapshot.sqlite3"


def main() -> None:
    source = str(load_settings().database_path)
    target = target_for(source)
    snapshot(source, target)
    print(f"snapshot written to {target}")


if __name__ == "__main__":
    main()
