from types import SimpleNamespace

from black_bloc.chat_check import (
    HOME_CHANNEL_KEY,
    check_reply,
    checked,
    home_mention,
    role_words,
    tidy,
)

CHANNELS = ("general", "live-now", "black_bloc-logs")
ROLES = ("leads", "aunties / uncles", "aunties", "member", "everyone", "here")


def guild(*names, roles=()):
    return SimpleNamespace(
        id=7,
        default_role=SimpleNamespace(id=7, name="@everyone"),
        roles=[SimpleNamespace(name=name) for name in roles],
        text_channels=[
            SimpleNamespace(
                name=name,
                topic=None,
                category=None,
                category_id=None,
                permissions_for=lambda role: SimpleNamespace(view_channel=True),
            )
            for name in names
        ],
    )


class Store:
    def __init__(self, **values):
        self.values = values

    def get(self, guild_id, key):
        return self.values.get(key)


def test_a_real_channel_is_left_exactly_as_written():
    found = checked("Ask in #general and somebody will help.", channels=CHANNELS, roles=ROLES)
    assert found.text == "Ask in #general and somebody will help."
    assert found.fixed == 0


def test_an_invented_channel_becomes_the_home_channel_when_one_is_set():
    found = checked(
        "Head over to #black-support-hub for that.",
        channels=CHANNELS,
        roles=ROLES,
        home="<#800>",
    )
    assert found.text == "Head over to <#800> for that."
    assert found.channels == ["black-support-hub"]


def test_with_no_home_channel_the_sentence_is_written_without_it():
    found = checked("Ask in #black-support-hub.", channels=CHANNELS, roles=ROLES)
    assert found.text == "Ask."
    assert found.channels == ["black-support-hub"]


def test_an_invented_role_is_smoothed_away_whatever_the_home_channel_is():
    found = checked("Ping @Admin and they will sort it.", channels=CHANNELS, roles=ROLES,
                    home="<#800>")
    assert found.text == "Ping and they will sort it."
    assert found.roles == ["Admin"]


def test_a_role_named_by_its_first_word_is_left_alone():
    found = checked("Ask @Aunties or @Leads.", channels=CHANNELS, roles=ROLES)
    assert found.text == "Ask @Aunties or @Leads."
    assert found.fixed == 0


def test_everyone_and_here_are_never_treated_as_inventions():
    found = checked("I will not @everyone or @here anybody.", channels=CHANNELS, roles=ROLES)
    assert found.fixed == 0


def test_a_member_named_in_the_conversation_survives():
    found = checked("Try @Pawpette.", channels=CHANNELS, roles=ROLES, people=("Pawpette",))
    assert found.text == "Try @Pawpette."
    assert found.fixed == 0


def test_a_real_channel_mention_and_a_real_role_mention_are_never_touched():
    found = checked("Go to <#800> and ask <@&900>, <@7>.", channels=CHANNELS, roles=ROLES)
    assert found.text == "Go to <#800> and ask <@&900>, <@7>."
    assert found.fixed == 0


def test_a_hash_that_is_a_number_or_a_url_fragment_is_not_a_channel():
    found = checked("Rule #1 and https://x.test/y#top.", channels=CHANNELS, roles=ROLES)
    assert found.fixed == 0


def test_a_dangling_or_is_taken_off_with_the_thing_it_joined():
    found = checked("Try #nowhere or #alsonowhere.", channels=CHANNELS, roles=ROLES)
    assert found.text == "Try."
    assert found.channels == ["nowhere", "alsonowhere"]


def test_tidy_leaves_a_reply_with_nothing_to_fix_untouched():
    assert tidy("Ask in #general.") == "Ask in #general."


def test_the_role_vocabulary_is_the_names_and_their_first_words():
    found = role_words(guild(roles=("Leads", "Aunties / Uncles", "@everyone")))
    assert {"leads", "aunties / uncles", "aunties", "everyone", "here"} <= found
    assert "@everyone" not in found


def test_the_home_channel_is_read_from_the_registry_and_blank_when_unset():
    bot = SimpleNamespace(store=Store(**{HOME_CHANNEL_KEY: 800}))
    assert home_mention(bot, guild()) == "<#800>"
    assert home_mention(SimpleNamespace(store=Store()), guild()) == ""


def test_the_whole_check_reads_the_live_channels_and_roles():
    bot = SimpleNamespace(store=Store(**{HOME_CHANNEL_KEY: 800}))
    found = check_reply(
        bot,
        guild("general", "live-now", roles=("Leads",)),
        "Ask in #general, or in #black-support-hub, and ping @Admin.",
    )
    assert found.channels == ["black-support-hub"]
    assert found.roles == ["Admin"]
    assert "#general" in found.text and "<#800>" in found.text
    assert "@Admin" not in found.text
