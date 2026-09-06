import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "sync_personality_pool.py"

spec = importlib.util.spec_from_file_location("sync_personality_pool", SCRIPT)
sync_script = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(sync_script)


MANIFEST = {
    "version": 2,
    "locked_by": "owner, 2026-08-18",
    "synced_from": "somewhere@0000000",
    "drift": {"every": 4, "chance": 0.25},
    "tropes": [{"name": "noir", "label": "noir", "neighbours": []}],
    "clauses": {"invariant": "i", "register": "r"},
    "slots": [],
}


def canonical(tmp_path, payload=None):
    source = tmp_path / "catalog-platform" / "apps" / "discord-worker" / "src"
    source.mkdir(parents=True)
    path = source / "personality-pool.json"
    path.write_text(json.dumps(payload if payload is not None else MANIFEST), encoding="utf-8")
    return path


def make_repo(path: Path) -> str:
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "T"],
        ["add", "-A"],
        ["commit", "-q", "-m", "manifest"],
    ):
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)
    found = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return found.stdout.strip()


def test_the_local_copy_ships_inside_the_package():
    """A Fly build installs the package; a manifest outside it would be missing at boot."""
    from black_bloc import personas

    assert personas.MANIFEST_PATH.is_file()
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert "personality_pool.json" in text


def test_a_missing_canonical_says_it_does_not_exist_yet_and_copies_nothing(tmp_path):
    local = tmp_path / "local.json"
    local.write_text('{"version": 1}', encoding="utf-8")

    with pytest.raises(SystemExit) as raised:
        sync_script.sync(tmp_path / "not-there.json", local)

    said = str(raised.value.code)
    assert "Nothing was copied" in said and "--from" in said
    assert local.read_text(encoding="utf-8") == '{"version": 1}'


def test_a_canonical_that_is_not_json_refuses_rather_than_writing_rubbish(tmp_path):
    source = canonical(tmp_path)
    source.write_text("{oops", encoding="utf-8")
    local = tmp_path / "local.json"

    with pytest.raises(SystemExit) as raised:
        sync_script.sync(source, local)

    assert "could not be read as JSON" in str(raised.value.code)
    assert not local.exists()


def test_a_canonical_with_no_tropes_is_not_a_usable_manifest(tmp_path):
    source = canonical(tmp_path, {"version": 3, "tropes": []})

    with pytest.raises(SystemExit) as raised:
        sync_script.sync(source, tmp_path / "local.json")

    assert "no tropes" in str(raised.value.code)


def test_a_copy_is_stamped_with_the_commit_it_came_from(tmp_path):
    source = canonical(tmp_path)
    head = make_repo(tmp_path / "catalog-platform")
    local = tmp_path / "local.json"

    said = sync_script.sync(source, local)
    found = json.loads(local.read_text(encoding="utf-8"))

    assert found["synced_from"] == f"catalog-platform@{head}"
    assert found["version"] == 2
    assert head in said and "pool v2" in said


def test_a_second_run_that_changes_nothing_says_so(tmp_path):
    source = canonical(tmp_path)
    make_repo(tmp_path / "catalog-platform")
    local = tmp_path / "local.json"

    sync_script.sync(source, local)

    assert "unchanged" in sync_script.sync(source, local)


def test_the_shipped_script_exits_non_zero_while_the_canonical_does_not_exist(tmp_path):
    """Today's real state: GABI's half is not built, so the script must fail loudly."""
    found = subprocess.run(
        ["python", str(SCRIPT), "--from", str(tmp_path / "nope.json")],
        capture_output=True,
        text=True,
    )

    assert found.returncode == 1
    assert "Nothing was copied" in found.stderr
