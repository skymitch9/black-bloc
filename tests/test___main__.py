import importlib
import runpy
import sys

import pytest

from black_bloc import app


def _fake_main(calls):
    def main():
        calls.append(1)
        return 0

    return main


def test_importing_the_entry_runs_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(app, "main", _fake_main(calls))
    monkeypatch.delitem(sys.modules, "black_bloc.__main__", raising=False)
    importlib.import_module("black_bloc.__main__")
    assert calls == []


def test_running_the_package_calls_main(monkeypatch):
    calls = []
    monkeypatch.setattr(app, "main", _fake_main(calls))
    monkeypatch.delitem(sys.modules, "black_bloc.__main__", raising=False)
    with pytest.raises(SystemExit) as exited:
        runpy.run_module("black_bloc", run_name="__main__")
    assert calls == [1]
    assert exited.value.code == 0
