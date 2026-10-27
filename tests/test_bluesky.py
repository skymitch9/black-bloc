from datetime import UTC, datetime, timedelta

import pytest

from black_bloc import bluesky as rules
from tests.bluesky_fakes import NEWEST_URI, recorded


class Store:
    def __init__(self, **values):
        from black_bloc.settings_store import BLUESKY_DEFAULTS

        self.values = dict(BLUESKY_DEFAULTS) | values

    def get(self, guild_id, key):
        return self.values.get(key)


def feed():
    return recorded()["feed"]


def by_rkey(rkey):
    return next(entry for entry in feed() if entry["post"]["uri"].endswith(rkey))


def test_the_recorded_feed_holds_every_shape_the_mirror_reads():
    kinds = {rules.kind_of(entry) for entry in feed()}
    embeds = {(entry["post"].get("embed") or {}).get("$type") for entry in feed()}

    assert kinds == {rules.OWN, rules.REPOST, rules.REPLY}
    assert {
        "app.bsky.embed.images#view",
        "app.bsky.embed.video#view",
        "app.bsky.embed.record#view",
    } <= embeds


def test_a_repost_is_a_repost_even_when_it_reposts_a_reply():
    entry = next(one for one in feed() if one.get("reason") and one["post"]["record"].get("reply"))

    assert rules.kind_of(entry) == rules.REPOST


def test_kinds_follow_the_two_switches():
    store = Store()

    assert rules.wanted(store, 7, rules.OWN)
    assert rules.wanted(store, 7, rules.REPOST)
    assert not rules.wanted(store, 7, rules.REPLY)
    flipped = Store(bluesky_reposts=False, bluesky_replies=True)
    assert not rules.wanted(flipped, 7, rules.REPOST)
    assert rules.wanted(flipped, 7, rules.REPLY)


def test_a_reposts_age_is_the_moment_it_was_reposted_not_when_it_was_written():
    entry = next(one for one in feed() if one.get("reason") and not one["post"].get("embed"))
    item = rules.item_of(entry)

    assert item.seen_from == entry["reason"]["indexedAt"]
    reposted = rules.parsed(entry["reason"]["indexedAt"])
    assert not rules.too_old(item, reposted + timedelta(hours=23), timedelta(hours=24))
    assert rules.too_old(item, reposted + timedelta(hours=25), timedelta(hours=24))


def test_nine_fractional_digits_are_read():
    found = rules.parsed("2026-10-23T16:55:12.804653830Z")

    assert found == datetime(2026, 10, 23, 16, 55, 12, 804653, tzinfo=UTC)
    assert rules.parsed("not a date") is None
    assert rules.parsed("") is None


def test_an_unreadable_stamp_is_too_old_never_posted():
    item = rules.item_of(feed()[0])
    broken = rules.Item(**{**item.__dict__, "seen_from": "never"})

    assert rules.too_old(broken, datetime.now(UTC), timedelta(hours=24))


def test_the_post_url_is_the_bsky_app_address_of_the_original():
    item = rules.item_of(feed()[0])

    assert item.uri == NEWEST_URI
    assert item.url == "https://bsky.app/profile/blackinaflash.bsky.social/post/3myuptyegac23"


def test_a_link_facet_is_expanded_to_its_full_address():
    entry = next(
        one
        for one in feed()
        if any(
            feature.get("$type") == rules.LINK_FACET
            for facet in one["post"]["record"].get("facets") or ()
            for feature in facet.get("features") or ()
        )
    )
    record = entry["post"]["record"]
    links = [
        feature["uri"]
        for facet in record["facets"]
        for feature in facet["features"]
        if feature["$type"] == rules.LINK_FACET
    ]

    text = rules.expanded_text(record)

    assert all(link in text for link in links)
    assert "..." not in text and "…" not in text


def test_facets_count_bytes_not_characters():
    record = {
        "text": "🔥 see example.com/a… now",
        "facets": [
            {
                "index": {"byteStart": 9, "byteEnd": 25},
                "features": [{"$type": rules.LINK_FACET, "uri": "https://example.com/abc"}],
            }
        ],
    }

    assert rules.expanded_text(record) == "🔥 see https://example.com/abc now"


def test_images_video_and_quotes_become_embed_parts():
    images = rules.embed_of(by_rkey("3myuptyegac23")["post"]["embed"])
    video = rules.embed_of(by_rkey("3myisto7wfc2y")["post"]["embed"])
    quote = rules.embed_of(by_rkey("3myap2igkxk2o")["post"]["embed"])

    assert images["image"].startswith("https://")
    assert video["image"].startswith("https://")
    assert quote["quote"]["handle"] and "text" in quote["quote"]


def test_an_external_card_and_a_record_with_media_are_read():
    card = rules.embed_of(
        {
            "$type": "app.bsky.embed.external#view",
            "external": {"uri": "https://gdq.com", "title": "GDQ", "thumb": "https://t/x.jpg"},
        }
    )
    both = rules.embed_of(
        {
            "$type": "app.bsky.embed.recordWithMedia#view",
            "media": {"$type": "app.bsky.embed.images#view", "images": [{"fullsize": "https://i"}]},
            "record": {
                "record": {
                    "author": {"handle": "a.bsky.social", "displayName": "A"},
                    "value": {"text": "quoted"},
                }
            },
        }
    )

    assert card == {
        "external": {"title": "GDQ", "uri": "https://gdq.com"},
        "image": "https://t/x.jpg",
    }
    assert both["image"] == "https://i" and both["quote"]["text"] == "quoted"


def test_oldest_first_keeps_the_post_and_drops_its_later_repost():
    walked = rules.oldest_first(feed())
    uris = [item.uri for item in walked]

    assert len(uris) == len(set(uris))
    twice = by_rkey("3mydhiqbers2w")["post"]["uri"]
    [kept] = [item for item in walked if item.uri == twice]
    assert kept.kind == rules.OWN
    assert walked[-1].uri == NEWEST_URI


def test_newest_first_keeps_feed_order():
    items = rules.items_of(feed())

    assert items[0].uri == NEWEST_URI
    assert len({item.uri for item in items}) == len(items)


def test_a_repost_carries_the_repost_line_with_the_accounts_name():
    entry = by_rkey("3mylf6l7byz2q")
    item = rules.item_of(entry)

    content, embed = rules.message_of(Store(), 7, item)

    first = content.splitlines()[0]
    assert first == f"🔁 {entry['reason']['by']['displayName']} reposted"
    assert content.endswith(item.url)
    assert embed.author.name.endswith(f"@{item.handle}")
    assert embed.url == item.url


def test_a_rehearsal_names_where_it_would_have_gone_and_never_pings():
    item = rules.item_of(feed()[0])

    content, _ = rules.message_of(Store(), 7, item, rehearsal_for=444, rehearsing=True, role=555)

    assert content.splitlines()[0] == ("Test copy · while bluesky_mode is on this goes to <#444>")
    assert "<@&555>" not in content


def test_a_real_post_mentions_the_role_first():
    item = rules.item_of(feed()[0])

    content, _ = rules.message_of(Store(), 7, item, role=555)

    assert content.splitlines()[0] == "<@&555>"
    allowed = rules.post_mentions(555)
    assert [role.id for role in allowed.roles] == [555]
    assert allowed.everyone is False and allowed.users is False
    assert rules.post_mentions(None).roles is False


def test_staff_wording_that_cannot_be_filled_falls_back_to_the_shipped_one():
    item = rules.item_of(feed()[0])
    store = Store(bluesky_template="{text} {nope}")

    content, _ = rules.message_of(store, 7, item)

    assert content == f"{item.text}\n{item.url}"


def test_a_long_post_is_cut_to_discords_limit():
    item = rules.item_of(feed()[0])
    long = rules.Item(**{**item.__dict__, "text": "x" * 5000})

    content, embed = rules.message_of(Store(), 7, long)

    assert len(content) == rules.MESSAGE_LIMIT
    assert len(embed.description) == rules.DESCRIPTION_LIMIT


def test_the_note_lets_one_member_be_mentioned_and_nothing_else():
    allowed = rules.note_mentions()

    assert allowed.users is True
    assert allowed.roles is False and allowed.everyone is False


@pytest.mark.parametrize(
    ("minutes", "failures", "wanted"),
    [(5, 0, 5), (5, 1, 10), (5, 2, 20), (5, 4, 60), (5, 30, 60), (60, 1, 60)],
)
def test_backoff_doubles_to_an_hour(minutes, failures, wanted):
    assert rules.backoff_minutes(minutes, failures) == wanted


def test_due_reads_the_stored_clock_and_the_failures():
    last = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
    row = {"last_read_at": last.isoformat(), "failures": 0}

    assert rules.is_due(None, 5, last)
    assert not rules.is_due(row, 5, last + timedelta(minutes=4))
    assert rules.is_due(row, 5, last + timedelta(minutes=5))
    assert not rules.is_due(row | {"failures": 2}, 5, last + timedelta(minutes=19))
    assert rules.is_due(row | {"failures": 2}, 5, last + timedelta(minutes=20))


def test_an_unknown_mode_reads_as_off():
    assert rules.mode_of(Store(bluesky_mode="sideways"), 7) == rules.OFF
    assert rules.mode_of(Store(), 7) == rules.SHADOW
