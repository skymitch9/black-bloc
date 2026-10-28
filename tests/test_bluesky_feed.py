from black_bloc import bluesky_feed as feed
from tests.bluesky_fakes import FakeFetch


async def test_a_good_read_hands_back_the_feed_and_names_the_account():
    fetch = FakeFetch()

    found = await feed.read_feed("blackinaflash.bsky.social", 30, fetch=fetch)

    assert found.ok and found.status == 200 and len(found.feed) == 30
    url, headers = fetch.urls[0]
    assert url == (
        "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
        "?actor=blackinaflash.bsky.social&limit=30"
    )
    assert headers["User-Agent"].startswith("BlackBloc/")


async def test_a_403_is_a_failed_read_never_an_empty_feed():
    fetch = FakeFetch()
    fetch.status = 403

    found = await feed.read_feed("a.bsky.social", 30, fetch=fetch)

    assert not found.ok and found.feed == []
    assert found.status == 403 and found.why == "Bluesky answered 403"


async def test_a_timeout_is_a_failed_read_with_its_reason():
    fetch = FakeFetch()
    fetch.raises = TimeoutError()

    found = await feed.read_feed("a.bsky.social", 30, fetch=fetch)

    assert not found.ok and found.status is None and "TimeoutError" in found.why


async def test_bad_json_and_a_missing_feed_are_failed_reads():
    fetch = FakeFetch()
    fetch.body = b"<html>"
    not_json = await feed.read_feed("a.bsky.social", 30, fetch=fetch)
    fetch.body = b'{"cursor": "x"}'
    no_feed = await feed.read_feed("a.bsky.social", 30, fetch=fetch)

    assert not not_json.ok and "not JSON" in not_json.why
    assert not no_feed.ok and "no feed" in no_feed.why


async def test_the_handle_is_quoted_into_the_address():
    fetch = FakeFetch()

    await feed.read_feed("a b&c", 5, fetch=fetch)

    assert "actor=a%20b%26c&limit=5" in fetch.urls[0][0]


async def test_one_post_is_read_by_its_uri_as_a_one_entry_feed():
    post = FakeFetch().feed()[0]["post"]
    fetch = FakeFetch({"posts": [post]})

    found = await feed.read_post(post["uri"], fetch=fetch)

    assert found.ok and found.feed == [{"post": post}]
    assert fetch.urls[0][0] == (
        "https://public.api.bsky.app/xrpc/app.bsky.feed.getPosts?uris="
        "at%3A%2F%2Fdid%3Aplc%3A4lijy65gdkw6gwwctvm6kxoc%2Fapp.bsky.feed.post%2F3myuptyegac23"
    )


async def test_a_post_read_that_fails_says_why():
    fetch = FakeFetch()
    fetch.status = 502

    found = await feed.read_post("at://x/app.bsky.feed.post/y", fetch=fetch)

    assert not found.ok and found.why == "Bluesky answered 502"


async def test_an_answer_with_no_posts_list_is_a_failed_read():
    found = await feed.read_post("at://x/app.bsky.feed.post/y", fetch=FakeFetch({"feed": []}))

    assert not found.ok and found.why == "the answer had no posts list"
