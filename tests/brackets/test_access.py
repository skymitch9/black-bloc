from __future__ import annotations

from types import SimpleNamespace

from black_bloc.brackets import access, may_run

TO_ROLE = 77
GUILD = SimpleNamespace(id=1)


class Store:
    def __init__(self, role=None, staff=()):
        self.role = role
        self.staff = set(staff)

    def get(self, guild_id, key):
        assert key == access.TO_ROLE_KEY
        return self.role

    def is_staff(self, member):
        return member.id in self.staff


def person(user_id, *roles):
    return SimpleNamespace(
        id=user_id, guild=GUILD, roles=[SimpleNamespace(id=role) for role in roles]
    )


def test_staff_may_run_a_tournament_without_the_role():
    assert may_run(Store(staff={5}), GUILD, person(5))


def test_a_holder_of_the_organiser_role_may_run_one():
    assert may_run(Store(role=TO_ROLE), GUILD, person(6, TO_ROLE))


def test_the_role_decides_so_losing_it_loses_the_right():
    assert not may_run(Store(role=TO_ROLE), GUILD, person(6))


def test_a_blank_role_means_staff_only():
    assert not may_run(Store(role=None), GUILD, person(6, TO_ROLE))
    assert not may_run(Store(role="nonsense"), GUILD, person(6, TO_ROLE))


def test_nobody_without_a_guild_or_a_person():
    assert not may_run(Store(staff={5}), None, person(5))
    assert not may_run(Store(staff={5}), GUILD, None)


def test_a_person_not_cached_in_the_server_is_never_staff():
    stranger = SimpleNamespace(id=5, roles=[])
    assert not access.is_staff(Store(staff={5}), stranger)
    assert not may_run(Store(staff={5}), GUILD, stranger)
