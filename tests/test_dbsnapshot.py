import sqlite3

from black_bloc.dbsnapshot import snapshot, target_for


def test_snapshot_copies_rows(tmp_path):
    source = tmp_path / "live.sqlite3"
    live = sqlite3.connect(source)
    live.execute("CREATE TABLE things(name TEXT)")
    live.execute("INSERT INTO things VALUES ('kept')")
    live.commit()
    live.close()

    target = tmp_path / "copy.sqlite3"
    snapshot(str(source), str(target))

    copy = sqlite3.connect(target)
    assert copy.execute("SELECT name FROM things").fetchone() == ("kept",)
    copy.close()


def test_target_sits_beside_the_source():
    assert target_for("/data/black_bloc.sqlite3") == "/data/black_bloc-nightly-snapshot.sqlite3"
