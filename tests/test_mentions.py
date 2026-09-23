from types import SimpleNamespace

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


def test_a_channel_mention_reads_as_the_typed_channel_name():
    assert named(Guild(), f"what goes in <#{KNUCK_UP}>") == "what goes in #knuck-up"


def test_a_role_mention_reads_as_the_role_name():
    assert named(Guild(), "who has <@&22>") == "who has @Tech Support"


def test_both_member_forms_read_as_the_display_name():
    assert named(Guild(), "ask <@33> or <@!33>") == "ask Raelcun or Raelcun"


def test_a_member_with_a_nickname_gives_the_nickname():
    assert named(Guild(), "is <@44> around") == "is Big Shane around"


def test_unknown_ids_are_left_exactly_as_they_were():
    text = "<#9> <@&9> <@9> <@!9>"
    assert named(Guild(), text) == text


def test_black_blocs_own_mention_is_left_for_spoken_to_take_out():
    assert named(Guild(), "<@1> sup") == "<@1> sup"


def test_no_guild_changes_nothing():
    assert named(None, f"<#{KNUCK_UP}>") == f"<#{KNUCK_UP}>"


def test_a_guild_without_a_cache_changes_nothing():
    assert named(SimpleNamespace(id=7), "<#5> <@6>") == "<#5> <@6>"
