from types import SimpleNamespace

import pytest

from black_bloc.mentions import named

KNUCK_UP = 1076003845232148580


class Guild:
    def __init__(self, me_id=1):
        self.me = SimpleNamespace(id=me_id)
        self.channels = {KNUCK_UP: SimpleNamespace(name="knuck-up")}
        self.roles = {22: SimpleNamespace(name="Tech Support")}
        self.members = {
            33: SimpleNamespace(name="raelcun", display_name="Raelcun"),
            44: SimpleNamespace(name="shane_m", display_name="Big Shane"),
            1: SimpleNamespace(name="blackbloc", display_name="Black Bloc"),
        }

    def get_channel(self, found_id):
        return self.channels.get(found_id)

    def get_role(self, found_id):
        return self.roles.get(found_id)

    def get_member(self, found_id):
        return self.members.get(found_id)


@pytest.mark.parametrize(
    ("text", "wanted"),
    [
        pytest.param(f"what goes in <#{KNUCK_UP}>", "what goes in #knuck-up", id="channel"),
        pytest.param("who has <@&22>", "who has @Tech Support", id="role"),
        pytest.param("ask <@33> or <@!33>", "ask Raelcun or Raelcun", id="both-member-forms"),
        pytest.param("is <@44> around", "is Big Shane around", id="nickname"),
        pytest.param("<#9> <@&9> <@9> <@!9>", "<#9> <@&9> <@9> <@!9>", id="unknown-ids-kept"),
        pytest.param("<@1> sup", "<@1> sup", id="own-mention-left-for-spoken"),
    ],
)
def test_a_mention_reads_as_the_name_a_person_would_type(text, wanted):
    assert named(Guild(), text) == wanted


def test_no_guild_changes_nothing():
    assert named(None, f"<#{KNUCK_UP}>") == f"<#{KNUCK_UP}>"


def test_a_guild_without_a_cache_changes_nothing():
    assert named(SimpleNamespace(id=7), "<#5> <@6>") == "<#5> <@6>"
