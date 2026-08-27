import pytest

from black_bloc.config import load_settings


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    return load_settings(_env_file=None, database_path=tmp_path / "test.sqlite3")
