import pytest

from black_bloc.cogs.community.role_menus import (
    SEED,
    RoleMenuView,
    add_option,
    create_menu,
    custom_id,
    delete_menu,
    get_menu,
    get_options,
    list_menus,
    max_values_for,
    panel_embed,
    parse_custom_id,
    posted_menus,
    remove_option,
    role_diff,
    seed_from_carl,
    set_message,
    summary,
)
from black_bloc.storage.db import Database

GUILD = 7


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "r.sqlite3")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


async def test_menu_crud(db):
    menu_id = await create_menu(db, GUILD, "pronouns", "Pronouns", "pick some", "multiple")
    assert menu_id is not None
    assert await create_menu(db, GUILD, "pronouns", "Pronouns") is None
    assert await create_menu(db, GUILD + 1, "pronouns", "Pronouns") is not None

    menu = await get_menu(db, GUILD, "pronouns")
    assert menu["title"] == "Pronouns" and menu["mode"] == "multiple"
    assert [m["name"] for m in await list_menus(db, GUILD)] == ["pronouns"]

    assert await delete_menu(db, GUILD, "pronouns") is True
    assert await delete_menu(db, GUILD, "pronouns") is False


async def test_option_crud_and_ordering(db):
    menu_id = await create_menu(db, GUILD, "m", "M")
    await add_option(db, menu_id, 1, "He/Him", "❤️")
    await add_option(db, menu_id, 2, "She/Her", "💙")
    await add_option(db, menu_id, 1, "He/Him (edited)", "❤️")

    options = await get_options(db, menu_id)
    assert [(o["role_id"], o["label"]) for o in options] == [
        (1, "He/Him (edited)"),
        (2, "She/Her"),
    ]
    assert await remove_option(db, menu_id, 2) is True
    assert await remove_option(db, menu_id, 2) is False
    assert len(await get_options(db, menu_id)) == 1


async def test_delete_menu_takes_its_options(db):
    menu_id = await create_menu(db, GUILD, "m", "M")
    await add_option(db, menu_id, 1, "One")
    await delete_menu(db, GUILD, "m")
    assert await get_options(db, menu_id) == []


async def test_posted_menus_only_lists_posted_ones(db):
    posted_id = await create_menu(db, GUILD, "posted", "P")
    await create_menu(db, GUILD, "draft", "D")
    await set_message(db, posted_id, 500, 600)
    rows = await posted_menus(db)
    assert [(r["name"], r["channel_id"], r["message_id"]) for r in rows] == [("posted", 500, 600)]


async def test_bad_mode_is_refused(db):
    with pytest.raises(ValueError, match="mode must be"):
        await create_menu(db, GUILD, "m", "M", None, "sometimes")


async def test_seed_is_idempotent(db):
    created, skipped = await seed_from_carl(db, GUILD)
    assert created == [name for name, _, _, _ in SEED] and skipped == []
    menu = await get_menu(db, GUILD, "pronouns")
    assert len(await get_options(db, menu["id"])) == 9

    created_again, skipped_again = await seed_from_carl(db, GUILD)
    assert created_again == [] and skipped_again == [name for name, _, _, _ in SEED]
    assert len(await list_menus(db, GUILD)) == len(SEED)
    assert len(await get_options(db, menu["id"])) == 9


def test_role_diff_only_touches_menu_roles():
    to_add, to_remove = role_diff({1, 2, 99}, [1, 2, 3], [2, 3])
    assert to_add == {3}
    assert to_remove == {1}


def test_role_diff_ignores_selections_outside_the_menu():
    to_add, to_remove = role_diff({1}, [1], [42])
    assert to_add == set() and to_remove == {1}


def test_role_diff_empty_selection_removes_everything_the_menu_owns():
    assert role_diff({1, 2, 99}, [1, 2], []) == (set(), {1, 2})


def test_single_mode_limits_the_picker():
    assert max_values_for("single", 9) == 1
    assert max_values_for("multiple", 9) == 9
    assert max_values_for("multiple", 0) == 1


def test_custom_id_round_trip():
    assert custom_id(12) == "rolemenu:12"
    assert parse_custom_id("rolemenu:12") == 12
    assert parse_custom_id("rolemenu:abc") is None
    assert parse_custom_id("other:12") is None


def test_summary_sentences():
    assert summary(["A"], ["B"]) == "Added: A · Removed: B"
    assert summary(["A"], []) == "Added: A"
    assert "Nothing changed" in summary([], [])


def test_view_is_persistent_and_keyed_by_menu_id():
    options = [
        {"role_id": 1, "label": "One", "emoji": "❤️"},
        {"role_id": 2, "label": "Two", "emoji": None},
    ]
    view = RoleMenuView(3, options, "multiple")
    select = view.children[0]
    assert view.timeout is None and view.is_persistent()
    assert select.custom_id == "rolemenu:3"
    assert select.min_values == 0 and select.max_values == 2
    assert [o.value for o in select.options] == ["1", "2"]
    assert select.role_ids == [1, 2]


def test_single_mode_view_allows_one_pick():
    options = [{"role_id": 1, "label": "One", "emoji": None}]
    assert RoleMenuView(4, options, "single").children[0].max_values == 1


def test_panel_embed_lists_the_options():
    menu = {"title": "Pronouns", "description": None}
    options = [
        {"role_id": 1, "label": "He/Him", "emoji": "❤️"},
        {"role_id": 2, "label": "She/Her", "emoji": None},
    ]
    embed = panel_embed(menu, options)
    assert embed.title == "Pronouns"
    assert embed.fields[0].value == "❤️ He/Him\nShe/Her"


def test_seed_data_is_well_formed():
    names = [name for name, _, _, _ in SEED]
    assert len(names) == len(set(names)) == 5
    for _, _, mode, options in SEED:
        assert mode in ("multiple", "single")
        assert options
        assert len({role_id for _, _, role_id in options}) == len(options)
