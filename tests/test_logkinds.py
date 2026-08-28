import ast
import pathlib

import pytest

from black_bloc import logkinds
from black_bloc.logkinds import (
    ALL,
    FEATURES,
    IMPORTANT,
    IMPORTANT_ONLY,
    IMPORTANT_SUFFIXES,
    LEVELS,
    OFF,
    ROUTINE,
    SHADOW,
    bare,
    feature_of,
    heads_for,
    is_important,
    is_shadow,
    like_patterns,
    log_level_key,
    should_post,
)

PACKAGE = pathlib.Path(logkinds.__file__).resolve().parent
ROOT = PACKAGE.parent

# Every `log_action(...)` whose kind is not a plain string literal, keyed
# "<path>::<source of the kind expression>" so the table survives line moves.
# A call site the table does not cover fails `test_every_dynamic_kind_is_enumerated`
# by name, which is what stops a new kind going quietly unclassified.
KNOWN_DYNAMIC: dict[str, tuple[str, ...]] = {
    "black_bloc/api/writes.py::kind": (
        "web.birthday.clear",
        "web.birthday.import",
        "web.birthday.optin",
        "web.birthday.set",
        "web.chat.intent_created",
        "web.chat.intent_deleted",
        "web.chat.intent_edited",
        "web.chat.line_added",
        "web.chat.line_deleted",
        "web.chat.line_edited",
        "web.event.cancel",
        "web.golive.link",
        "web.golive.optin",
        "web.golive.optout",
        "web.golive.unlink",
        "web.honeypot.ban",
        "web.honeypot.setup",
        "web.mod.apply",
        "web.mod.rule",
        "web.modmail.block",
        "web.modmail.close",
        "web.modmail.reply",
        "web.modmail.snippet",
        "web.modmail.snippet_remove",
        "web.modmail.unblock",
        "web.poll.approved",
        "web.poll.cancel",
        "web.poll.created",
        "web.poll.denied",
        "web.poll.end",
        "web.poll.recur_deleted",
        "web.poll.recur_paused",
        "web.poll.recur_resumed",
        "web.request.approved",
        "web.request.comment",
        "web.request.declined",
        "web.request.done",
        "web.request.filed",
        "web.request.in_progress",
        "web.request.planned",
        "web.request.updated",
        "web.request.withdrawn",
        "web.role.ended",
        "web.role.extended",
        "web.role.granted",
        "web.rolemenu.create",
        "web.rolemenu.delete",
        "web.rolemenu.edit",
        "web.rolemenu.post",
        "web.settings.clear",
        "web.settings.set",
        "web.tempvoice.forget",
        "web.tempvoice.setup",
    ),
    "black_bloc/cogs/community/events.py::f'event.{kind}'": (
        "event.announce",
        "event.go_live",
    ),
    "black_bloc/cogs/community/events.py::f'event.would_{kind}'": (
        "event.would_announce",
        "event.would_go_live",
    ),
    "black_bloc/cogs/community/events.py::f'event.{kind}_failed'": (
        "event.announce_failed",
        "event.go_live_failed",
    ),
    "black_bloc/cogs/community/events.py::f'event.{status}'": (
        "event.approved",
        "event.denied",
    ),
    "black_bloc/cogs/community/events.py::kind": (
        "event.category_forgotten",
        "event.announce_channel_forgotten",
    ),
    "black_bloc/cogs/community/tempvoice.py::f'tempvoice.{kind}'": (
        "tempvoice.ban",
        "tempvoice.ban_failed",
        "tempvoice.bitrate",
        "tempvoice.bitrate_failed",
        "tempvoice.claim",
        "tempvoice.hide",
        "tempvoice.kick",
        "tempvoice.limit",
        "tempvoice.limit_failed",
        "tempvoice.lock",
        "tempvoice.permit",
        "tempvoice.permit_failed",
        "tempvoice.privacy_failed",
        "tempvoice.region",
        "tempvoice.region_failed",
        "tempvoice.rename",
        "tempvoice.rename_failed",
        "tempvoice.show",
        "tempvoice.transfer",
        "tempvoice.unban",
        "tempvoice.unban_failed",
        "tempvoice.unlock",
        "tempvoice.unpermit",
        "tempvoice.unpermit_failed",
    ),
    "black_bloc/cogs/community/requests.py::f'request.{status}'": (
        "request.approved",
        "request.declined",
        "request.planned",
        "request.in_progress",
        "request.done",
    ),
    "black_bloc/cogs/content/chat.py::LOG_KIND": ("chat.insult",),
    "black_bloc/cogs/content/chat.py::ROUTE_KIND": ("chat.route",),
    "black_bloc/cogs/content/golive.py::kind": (
        "golive.optin",
        "golive.optout",
        "golive.unlink",
    ),
    "black_bloc/cogs/moderation/automod.py::f'automod.would_{action}'": (
        "automod.would_delete",
        "automod.would_warn",
        "automod.would_timeout",
    ),
    "black_bloc/cogs/moderation/modcmds.py::f'mod.would_{kind}'": (
        "mod.would_timeout",
        "mod.would_untimeout",
        "mod.would_kick",
        "mod.would_ban",
        "mod.would_unban",
        "mod.would_purge",
    ),
    "black_bloc/cogs/moderation/modcmds.py::f'mod.{kind}_failed'": (
        "mod.timeout_failed",
        "mod.untimeout_failed",
        "mod.kick_failed",
        "mod.ban_failed",
        "mod.unban_failed",
    ),
    "black_bloc/cogs/moderation/modmail.py::kind": (
        "modmail.category_forgotten",
        "modmail.staff_channel_forgotten",
        "modmail.log_channel_forgotten",
    ),
    "black_bloc/command_visibility.py::LOG_KIND": ("commands.visibility",),
    "black_bloc/rolemenu_panels.py::kind": (
        "role_menu.unposted",
        "role_menu.unpost_failed",
        "role_menu.would_unpost",
        "role_menu.reposted",
        "role_menu.repost_failed",
        "role_menu.would_repost",
    ),
}


def _source(node: ast.AST) -> str:
    return ast.unparse(node).replace('"', "'")


def _call_sites() -> tuple[list[tuple[str, int, str]], list[str]]:
    """Every `log_action(...)`: the literal kinds, and the keys of the dynamic ones."""
    literals: list[tuple[str, int, str]] = []
    dynamic: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name != "log_action" or len(node.args) < 3:
                continue
            wanted = node.args[2]
            branches = (
                [wanted.body, wanted.orelse] if isinstance(wanted, ast.IfExp) else [wanted]
            )
            for branch in branches:
                if isinstance(branch, ast.Constant) and isinstance(branch.value, str):
                    literals.append((rel, node.lineno, branch.value))
                else:
                    dynamic.append(f"{rel}::{_source(branch)}")
    return literals, dynamic


def emitted_kinds() -> set[str]:
    literals, dynamic = _call_sites()
    found = {kind for _, _, kind in literals}
    for key in dynamic:
        found.update(KNOWN_DYNAMIC.get(key, ()))
    return found


def _classification(kind: str) -> str:
    text = bare(kind)
    if SHADOW in text:
        return "routine (shadow)"
    if text in ROUTINE:
        return "routine"
    if text in IMPORTANT:
        return "important"
    for suffix in IMPORTANT_SUFFIXES:
        if text.endswith(suffix):
            return f"important ({suffix})"
    return "UNCLASSIFIED"


def test_every_dynamic_kind_is_enumerated():
    """A kind built at runtime is only safe if the table can still name every value."""
    _, dynamic = _call_sites()
    missing = sorted({key for key in dynamic if key not in KNOWN_DYNAMIC})
    assert not missing, (
        "log_action() is called with a kind that is not a string literal and is not in "
        f"KNOWN_DYNAMIC: {missing}. Add the concrete kinds it can produce."
    )
    stale = sorted(set(KNOWN_DYNAMIC) - set(dynamic))
    assert not stale, f"KNOWN_DYNAMIC names call sites that are gone: {stale}"


def test_every_emitted_kind_is_classified():
    """The whole point: silence is never accidental, so a new kind fails here by name."""
    unclassified = sorted(
        kind for kind in emitted_kinds() if _classification(kind) == "UNCLASSIFIED"
    )
    assert not unclassified, (
        "these kinds are neither in IMPORTANT, nor matched by an IMPORTANT_SUFFIXES entry, "
        f"nor in ROUTINE, so nobody has decided whether Discord sees them: {unclassified}"
    )


def test_every_emitted_kind_lands_in_a_feature_that_has_a_setting():
    for kind in emitted_kinds():
        assert feature_of(kind) in FEATURES, kind


def test_routine_and_important_do_not_overlap():
    assert not (ROUTINE & IMPORTANT)


def test_no_classification_entry_is_dead():
    """A named kind nothing emits is a table nobody maintains."""
    emitted = {bare(kind) for kind in emitted_kinds()}
    assert not sorted(IMPORTANT - emitted), sorted(IMPORTANT - emitted)
    assert not sorted(ROUTINE - emitted), sorted(ROUTINE - emitted)


def test_web_kinds_collapse_onto_the_kind_they_mirror():
    assert bare("web.role.granted") == "role.granted"
    assert bare("role.granted") == "role.granted"
    assert bare("web") == "web"
    assert feature_of("web.settings.set") == "core"
    assert is_important("web.role.granted") is True


@pytest.mark.parametrize(
    ("kind", "feature"),
    [
        ("golive.announce", "golive"),
        ("role.approved", "rolemenu"),
        ("role_menu.update", "rolemenu"),
        ("web.rolemenu.post", "rolemenu"),
        ("mod.banned", "mod"),
        ("case.opened", "mod"),
        ("event.approved", "events"),
        ("events.approved", "events"),
        ("birthday.set", "birthday"),
        ("settings.set", "core"),
        ("presence.bio_set", "core"),
        ("commands.visibility", "core"),
        ("nonsense.happened", "core"),
        ("", "core"),
    ],
)
def test_feature_of_reads_the_dotted_head(kind, feature):
    assert feature_of(kind) == feature


def test_every_shadow_kind_is_routine_by_rule_not_by_being_listed():
    """Owner, 2026-08-27: "lets mute all the would calls too, keep that in discord logs"."""
    shadows = sorted(kind for kind in emitted_kinds() if SHADOW in bare(kind))

    assert len(shadows) >= 25
    assert all(is_shadow(kind) for kind in shadows)
    assert not [kind for kind in shadows if is_important(kind)]
    assert not [kind for kind in shadows if bare(kind) in ROUTINE], (
        "a .would_ kind is routine by rule; listing it as well is a second home for the decision"
    )
    assert not [kind for kind in shadows if should_post(kind, IMPORTANT_ONLY)]
    assert all(should_post(kind, ALL) for kind in shadows)


def test_the_shadow_rule_beats_a_suffix_that_would_have_matched():
    """A dry run may not borrow the word it is only pretending to do."""
    for kind in ("mod.would_ban", "automod.would_timeout", "web.mod.would_kick"):
        assert is_important(kind) is False
    assert is_important("mod.would_something_that_failed") is False
    assert is_important("mod.banned") is True
    assert is_shadow("mod.wouldnt_ban") is False


def test_the_routine_set_beats_a_suffix():
    """`.closed` and `.ban` are modmail and moderation words; polls and temp voice borrow them."""
    assert is_important("poll.closed") is False
    assert is_important("modmail.closed") is True
    assert is_important("tempvoice.ban") is False
    assert is_important("mod.banned") is True


def test_a_request_is_loud_only_when_it_is_answered_or_fails():
    """Filing, triage and a withdrawal are the member's own housekeeping; a decision is not."""
    for kind in (
        "request.filed",
        "request.auto_approved",
        "request.withdrawn",
        "request.planned",
        "request.in_progress",
        "request.updated",
        "request.comment",
    ):
        assert is_important(kind) is False, kind
        assert is_important(f"web.{kind}") is False, kind
    for kind in ("request.approved", "request.declined", "request.done"):
        assert is_important(kind) is True, kind
        assert is_important(f"web.{kind}") is True, kind
    assert is_important("request.dm_failed") is True
    assert is_important("request.notify_failed") is True
    assert feature_of("request.filed") == "request"
    assert feature_of("web.request.approved") == "request"


def test_should_post_reads_the_three_levels():
    assert should_post("mod.banned", OFF) is False
    assert should_post("poll.created", OFF) is False
    assert should_post("mod.banned", IMPORTANT_ONLY) is True
    assert should_post("poll.created", IMPORTANT_ONLY) is False
    assert should_post("poll.created", ALL) is True


def test_an_unknown_level_is_todays_behaviour():
    for level in (None, "", "quiet", "IMPORTANT"):
        assert should_post("poll.created", level) is True


def test_every_feature_has_one_settings_key():
    assert len(FEATURES) == 13
    assert len(set(FEATURES)) == 13
    assert log_level_key("golive") == "golive_log_level"
    assert LEVELS == (OFF, IMPORTANT_ONLY, ALL)


def test_like_patterns_cover_every_head_of_a_feature():
    assert set(heads_for("rolemenu")) == {"role", "role_menu", "rolemenu"}
    patterns = like_patterns("rolemenu")
    assert "role.%" in patterns and "web.role.%" in patterns
    assert like_patterns("core") == (
        "settings.%",
        "web.settings.%",
        "commands.%",
        "web.commands.%",
        "presence.%",
        "web.presence.%",
    )
