from pathlib import Path

import pytest

from black_bloc import __version__
from black_bloc.api.assets import build_id, stamp


def site(tmp_path: Path) -> Path:
    root = tmp_path / "public"
    (root / "assets").mkdir(parents=True)
    (root / "assets" / "site.css").write_text("body{}", encoding="utf-8")
    (root / "index.html").write_text('<link href="/assets/site.css">', encoding="utf-8")
    return root


def test_the_build_id_carries_the_version(tmp_path):
    assert build_id(site(tmp_path)).startswith(f"{__version__}-")


@pytest.mark.parametrize(
    ("name", "text"),
    [("site.css", "body{color:red}"), ("extra.js", "")],
    ids=["an-asset-changes", "an-asset-is-added"],
)
def test_the_build_id_changes_when_the_assets_do(tmp_path, name, text):
    root = site(tmp_path)
    before = build_id(root)
    (root / "assets" / name).write_text(text, encoding="utf-8")
    assert build_id(root) != before


def test_the_build_id_is_the_same_when_nothing_changed(tmp_path):
    root = site(tmp_path)
    assert build_id(root) == build_id(root)


def test_stamp_puts_the_build_id_on_every_asset_url():
    html = '<link rel="stylesheet" href="/assets/site.css"><script src="/assets/app.js"></script>'

    stamped = stamp(html, "v1")

    assert 'href="/assets/site.css?v=v1"' in stamped
    assert 'src="/assets/app.js?v=v1"' in stamped


def test_stamp_leaves_urls_that_are_not_assets_alone():
    html = '<link rel="icon" href="/favicon.ico"><a href="/index.html">home</a>'

    assert stamp(html, "v1") == html


def test_stamp_does_not_stamp_a_url_twice():
    once = stamp('<script src="/assets/app.js"></script>', "v1")

    assert stamp(once, "v1") == once
