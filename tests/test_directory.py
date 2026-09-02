from types import SimpleNamespace

from black_bloc.directory import (
    DIRECTORY_HEADING,
    DIRECTORY_NONE,
    channel_names,
    directory_block,
    everyone_sees,
    hidden_category_ids,
    is_archive,
    open_channels,
    within,
)

GUILD = 7
EVERYONE = SimpleNamespace(id=GUILD, name="@everyone")


class Store:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


class AngryStore:
    def get(self, guild_id, key):
        raise RuntimeError("no")


def category(category_id, name):
    return SimpleNamespace(id=category_id, name=name)


def channel(name, *, seen=True, cat=None, topic=None, broken=False):
    def permissions_for(role):
        if broken:
            raise RuntimeError("no")
        return SimpleNamespace(view_channel=seen and role is EVERYONE)

    return SimpleNamespace(
        id=abs(hash(name)) % 10_000,
        name=name,
        topic=topic,
        category=cat,
        category_id=getattr(cat, "id", None),
        permissions_for=permissions_for,
    )


def guild(*channels):
    return SimpleNamespace(id=GUILD, default_role=EVERYONE, text_channels=list(channels))


def bot(**values):
    return SimpleNamespace(store=Store(**values))


def test_a_category_is_an_archive_when_the_word_is_anywhere_in_its_name():
    assert is_archive(category(1, "archive")) is True
    assert is_archive(category(1, "ARCHIVE")) is True
    assert is_archive(category(1, "Old Archives")) is True
    assert is_archive(category(1, "Cookout")) is False
    assert is_archive(None) is False


def test_the_hidden_categories_are_the_modmail_one_and_whatever_staff_listed():
    found = hidden_category_ids(
        bot(modmail_category_id=11, chat_ignore_categories=[22, 33]), guild()
    )
    assert found == {11, 22, 33}


def test_nothing_set_hides_nothing():
    assert hidden_category_ids(bot(), guild()) == set()


def test_a_store_that_will_not_answer_hides_nothing_rather_than_raising():
    found = hidden_category_ids(SimpleNamespace(store=AngryStore()), guild())
    assert found == set()


def test_a_channel_everyone_can_see_is_the_only_visible_one():
    assert everyone_sees(guild(), channel("general")) is True
    assert everyone_sees(guild(), channel("staff", seen=False)) is False


def test_a_channel_that_will_not_say_what_everyone_sees_is_treated_as_private():
    assert everyone_sees(guild(), channel("odd", broken=True)) is False
    assert everyone_sees(SimpleNamespace(default_role=None), channel("odd")) is False
    assert everyone_sees(guild(), SimpleNamespace(name="odd")) is False


def test_the_ingest_takes_only_public_channels_outside_archive_and_modmail():
    archive = category(50, "Archive")
    modmail = category(11, "ModMail")
    quiet = category(60, "Cookout")
    open_one = channel("general", cat=quiet)
    found = open_channels(
        bot(modmail_category_id=11, chat_ignore_categories=[]),
        guild(
            open_one,
            channel("staff-room", seen=False),
            channel("black-support-hub", cat=archive),
            channel("ticket-0001", cat=modmail, topic="ModMail Channel 123 456"),
        ),
    )
    assert [one.name for one in found] == ["general"]


def test_a_category_staff_listed_is_left_out_too():
    listed = category(99, "Committee")
    found = open_channels(
        bot(chat_ignore_categories=[99]),
        guild(channel("general"), channel("planning", cat=listed)),
    )
    assert [one.name for one in found] == ["general"]


def test_a_guild_with_no_channels_gives_nothing():
    assert open_channels(bot(), guild()) == []


def test_the_directory_names_every_public_channel_and_trims_its_topic():
    said = directory_block(
        bot(),
        guild(
            channel("general", topic="Chat about anything you like."),
            channel("quiet"),
            channel("staff-room", topic="Staff only.", seen=False),
        ),
    )
    assert said.startswith(DIRECTORY_HEADING)
    assert "#general — Chat about anything you like." in said
    assert "#quiet" in said
    assert "staff-room" not in said


def test_a_topic_longer_than_the_trim_is_shortened_rather_than_dropped():
    said = directory_block(bot(), guild(channel("general", topic="x" * 400)))
    assert "…" in said
    assert len(said) < 400


def test_nothing_public_says_so_rather_than_leaving_the_model_to_guess():
    assert directory_block(bot(), guild()) == DIRECTORY_NONE
    assert directory_block(bot(), guild(channel("staff", seen=False))) == DIRECTORY_NONE


def test_past_the_cap_the_longest_topic_goes_first_and_the_names_all_stay():
    rows = [("general", "x" * 100), ("quiet", "y" * 10), ("loud", "z" * 50)]
    kept = within(rows, budget=60)
    assert [name for name, _ in kept] == ["general", "quiet", "loud"]
    assert [topic for _, topic in kept] == ["", "y" * 10, ""]


def test_when_even_the_bare_names_will_not_fit_the_last_ones_fall_off():
    kept = within([("aaaa", ""), ("bbbb", ""), ("cccc", "")], budget=12)
    assert [name for name, _ in kept] == ["aaaa", "bbbb"]


def test_the_guard_vocabulary_is_every_public_name_case_folded():
    found = channel_names(
        bot(), guild(channel("General"), channel("Quiet"), channel("staff", seen=False))
    )
    assert found == {"general", "quiet"}


MEMBER = SimpleNamespace(id=444, name="Member")


def member_gated_guild(*channels):
    found = SimpleNamespace(id=GUILD, default_role=EVERYONE, text_channels=list(channels))
    found.get_role = lambda role_id: MEMBER if role_id == MEMBER.id else None
    return found


def member_channel(name, topic=None):
    def permissions_for(role):
        return SimpleNamespace(view_channel=role is MEMBER)

    return SimpleNamespace(
        id=abs(hash(name)) % 10_000,
        name=name,
        topic=topic,
        category=None,
        category_id=None,
        permissions_for=permissions_for,
    )


def test_the_member_roles_view_is_the_map_on_a_rules_gated_server():
    home = member_gated_guild(member_channel("speed-and-pbs", topic="post your pbs here"))

    assert [c.name for c in open_channels(bot(chat_visibility_role_id=444), home)] == [
        "speed-and-pbs"
    ]
    assert open_channels(bot(), home) == []


def test_a_visibility_role_the_guild_does_not_hold_falls_back_to_everyone():
    home = member_gated_guild(member_channel("speed-and-pbs"))

    assert open_channels(bot(chat_visibility_role_id=999), home) == []
