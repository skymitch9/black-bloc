import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "ci_local.py"
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

spec = importlib.util.spec_from_file_location("ci_local", SCRIPT)
ci_local = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ci_local)


def test_every_step_of_ci_yml_is_read():
    text = WORKFLOW.read_text(encoding="utf-8")
    steps = ci_local.steps_of(text)
    assert len(steps) == len(re.findall(r"^\s+- (name|uses):", text, re.MULTILINE))
    runs = "\n".join(step.get("run", "") for step in steps)
    for line in re.findall(r"^\s+(?:run: )?(node [^\n&]+|ruff [^\n]+|python -m pytest[^\n]*)$",
                           text, re.MULTILINE):
        assert line.strip() in runs


def test_the_image_installs_with_the_command_ci_yml_runs(monkeypatch):
    monkeypatch.chdir(REPO)
    install = [s["run"] for s in ci_local.steps_of(WORKFLOW.read_text(encoding="utf-8"))
               if s.get("run", "").startswith("pip install")]
    assert install == [ci_local.install_line()]


def test_a_block_run_keeps_every_line_and_a_quoted_name_loses_its_quotes():
    text = (
        "jobs:\n  gate:\n    steps:\n"
        "      - uses: actions/checkout@v4\n"
        '      - name: "Install"\n        run: pip install -e ".[dev]"\n'
        "      - name: Two\n        run: |\n          echo a &\n\n          echo b\n"
        "      - name: Three\n        run: echo c\n"
    )
    steps = ci_local.steps_of(text)
    assert [s["name"] for s in steps] == ["actions/checkout@v4", "Install", "Two", "Three"]
    assert steps[1]["run"] == 'pip install -e ".[dev]"'
    assert steps[2]["run"] == "echo a &\n\necho b\n"


@pytest.mark.parametrize("key", ["env", "shell", "if", "working-directory", "continue-on-error"])
def test_a_step_key_the_mirror_does_not_model_is_refused(key):
    text = f"    steps:\n      - name: X\n        {key}: y\n        run: echo\n"
    with pytest.raises(ValueError, match=key):
        ci_local.steps_of(text)


def test_steps_fall_into_the_only_groups():
    assert ci_local.group_of({"run": "ruff check ."}) == "lint"
    assert ci_local.group_of({"run": "python -m pytest -q"}) == "tests"
    assert ci_local.group_of({"run": "node site/mock/x.test.mjs"}) == "site"
    assert ci_local.group_of({"run": 'pip install -e ".[dev]"'}) is None
    assert ci_local.group_of({"uses": "actions/checkout@v4"}) is None


@pytest.mark.skipif(sys.platform == "win32", reason="the runner shells out to Linux bash")
def test_the_first_red_step_stops_the_run(tmp_path, monkeypatch, capsys):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "    steps:\n      - name: Green\n        run: 'true'\n"
        "      - name: Red\n        run: exit 3\n      - name: Never\n        run: touch never\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert ci_local.main([]) == 1
    out = capsys.readouterr().out
    assert "== Red: FAILED (exit 3)" in out and "CI MIRROR RED: 'Red'" in out
    assert not (tmp_path / "never").exists()
