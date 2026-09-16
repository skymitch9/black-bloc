import ast
import pathlib
from typing import Any

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
    VIA_BOOT,
    VIA_DISCORD,
    VIA_OPERATOR,
    VIA_WEBSITE,
    VIA_WORDS,
    WEB,
    bare,
    feature_of,
    heads_for,
    is_important,
    is_shadow,
    kind_via,
    like_patterns,
    log_level_key,
    should_post,
    via_of,
    via_word,
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
        "web.event.edited",
        "web.guide.confirmed",
        "web.guide.created",
        "web.guide.deleted",
        "web.guide.edited",
        "web.guide.media_replaced",
        "web.guide.published",
        "web.guide.reset",
        "web.guide.unpublished",
        "web.request.comment",
        "web.request.filed",
        "web.request.updated",
    ),
    # The self-test's four kinds are module constants, and every door writes the same four
    # through `kind_via`, so each one is dynamic in exactly the two spellings.
    "black_bloc/selftest.py::SELFTEST_STARTED": (
        "selftest.started",
        "web.selftest.started",
    ),
    "black_bloc/selftest.py::SELFTEST_CHECK": (
        "selftest.check",
        "web.selftest.check",
    ),
    "black_bloc/selftest.py::SELFTEST_FINISHED": (
        "selftest.finished",
        "web.selftest.finished",
    ),
    "black_bloc/selftest.py::SELFTEST_PURGED": (
        "selftest.purged",
        "web.selftest.purged",
    ),
    # The boot sync's two kinds are module constants, and the boot is the only door that
    # writes them — a website read syncs insert-only and logs nothing.
    "black_bloc/personas.py::CHAT_POOL_SYNCED": ("chat.pool_synced",),
    "black_bloc/personas.py::CHAT_POOL_RETIRED": ("chat.pool_retired",),
    # One `move_train` walks the transition table for both doors, so the kind is the target's.
    "black_bloc/cogs/content/raidtrain.py::MOVE_KINDS[to]": (
        "raidtrain.lock",
        "raidtrain.unlock",
        "raidtrain.live",
        "raidtrain.done",
        "web.raidtrain.lock",
        "web.raidtrain.unlock",
        "web.raidtrain.live",
        "web.raidtrain.done",
    ),
    "black_bloc/events.py::f'event.{kind}'": (
        "event.announce",
        "event.go_live",
    ),
    "black_bloc/events.py::f'event.would_{kind}'": (
        "event.would_announce",
        "event.would_go_live",
    ),
    "black_bloc/events.py::f'event.{kind}_failed'": (
        "event.announce_failed",
        "event.go_live_failed",
    ),
    "black_bloc/events.py::f'event.{kind}_room'": (
        "event.announce_room",
        "event.go_live_room",
        "event.ended_room",
        "event.cancelled_room",
        "event.denied_room",
    ),
    "black_bloc/events.py::f'event.would_{kind}_room'": (
        "event.would_announce_room",
        "event.would_go_live_room",
        "event.would_ended_room",
        "event.would_cancelled_room",
        "event.would_denied_room",
    ),
    "black_bloc/events.py::f'event.{kind}_room_failed'": (
        "event.announce_room_failed",
        "event.go_live_room_failed",
        "event.ended_room_failed",
        "event.cancelled_room_failed",
        "event.denied_room_failed",
    ),
    "black_bloc/events.py::f'event.{status}'": (
        "event.approved",
        "event.denied",
        "web.event.approved",
        "web.event.denied",
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
        # The dashboard's room actions (B4) go through the same helper with a website doer,
        # so the head is `web.` and these are the six-plus-failures it can leave.
        "web.tempvoice.hide",
        "web.tempvoice.limit",
        "web.tempvoice.limit_failed",
        "web.tempvoice.lock",
        "web.tempvoice.privacy_failed",
        "web.tempvoice.rename",
        "web.tempvoice.rename_failed",
        "web.tempvoice.show",
        "web.tempvoice.unlock",
    ),
    "black_bloc/cogs/community/requests.py::f'request.{look}'": (
        "request.declined",
        "request.done",
        "request.hold",
        "request.in_progress",
        "request.review",
        "request.sent_back",
        "web.request.declined",
        "web.request.done",
        "web.request.hold",
        "web.request.in_progress",
        "web.request.review",
        "web.request.sent_back",
    ),
    "black_bloc/cogs/community/requests.py::NOTIFY_SKIPPED_KIND": (
        "request.notify_skipped_test_mode",
    ),
    "black_bloc/cogs/community/requests.py::NOTIFY_FAILED_KIND": ("request.notify_failed",),
    "black_bloc/chat_distil.py::DISTILLED_KIND": ("chat.memory_distilled",),
    "black_bloc/chat_distil.py::kind": (
        "chat.memory_distil_failed",
        "chat.memory_expired",
    ),
    "black_bloc/cogs/content/chat_memory.py::kind": (
        "chat.memory_forgot",
        "chat.memory_optin",
        "chat.memory_optout",
    ),
    "black_bloc/cogs/content/chat_memory.py::FORGOT_KIND": ("chat.memory_forgot",),
    "black_bloc/cogs/content/chat.py::LOG_KIND": ("chat.insult",),
    "black_bloc/cogs/content/chat.py::ROUTE_KIND": ("chat.route",),
    "black_bloc/cogs/content/chat.py::KNOWLEDGE_INGESTED": ("chat.knowledge_ingested",),
    "black_bloc/cogs/content/chat.py::REPLY_KIND": ("chat.llm_reply",),
    "black_bloc/chat_llm.py::CAPPED_KIND": ("chat.llm_capped",),
    "black_bloc/chat_llm.py::ERROR_KIND": ("chat.llm_error",),
    "black_bloc/chat_llm.py::FIXED_KIND": ("chat.reply_reference_fixed",),
    "black_bloc/cogs/moderation/automod.py::f'automod.would_{action}'": (
        "automod.would_delete",
        "automod.would_warn",
        "automod.would_timeout",
        "web.automod.would_delete",
        "web.automod.would_warn",
        "web.automod.would_timeout",
    ),
    "black_bloc/cogs/moderation/modcmds.py::f'mod.would_{kind}'": (
        "mod.would_timeout",
        "mod.would_untimeout",
        "mod.would_kick",
        "mod.would_ban",
        "mod.would_unban",
        "mod.would_purge",
        "web.mod.would_timeout",
        "web.mod.would_untimeout",
        "web.mod.would_kick",
        "web.mod.would_ban",
        "web.mod.would_unban",
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
    "black_bloc/api/auth.py::OPERATOR_READ_KIND": ("web.operator.read",),
    # B7: one helper serves the staff picker and the dashboard, so the head and the word are
    # both built at call time rather than being two literals in two places.
    "black_bloc/cogs/community/role_menus.py::kind": (
        "role_menu.assign",
        "role_menu.unassign",
        "web.role_menu.assign",
        "web.role_menu.unassign",
    ),
    "black_bloc/rolemenu_panels.py::kind": (
        "role_menu.unposted",
        "role_menu.unpost_failed",
        "role_menu.would_unpost",
        "role_menu.reposted",
        "role_menu.repost_failed",
        "role_menu.would_repost",
        # B5: the dashboard's Un-post, and the panel move a channel change makes, both call
        # `unpost` with a website via, so the same three kinds arrive under a `web.` head.
        "web.role_menu.unposted",
        "web.role_menu.unpost_failed",
        "web.role_menu.would_unpost",
    ),
    "black_bloc/posts.py::kind": (
        "post.created",
        "post.deleted",
        "post.message_gone",
        "post.pin_failed",
        "post.pinned",
        "post.post_failed",
        "post.posted",
        "post.reset",
        "post.saved",
        "post.taken_down",
        "post.updated",
        "post.would_post",
        "post.would_take_down",
        # The dashboard's Posts page calls the same moves with a website via, so every kind
        # the panel writes arrives under a `web.` head as well.
        "web.post.created",
        "web.post.deleted",
        "web.post.message_gone",
        "web.post.pin_failed",
        "web.post.pinned",
        "web.post.post_failed",
        "web.post.posted",
        "web.post.reset",
        "web.post.saved",
        "web.post.taken_down",
        "web.post.updated",
        "web.post.would_post",
        "web.post.would_take_down",
    ),
}


def _source(node: ast.AST) -> str:
    return ast.unparse(node).replace('"', "'")


def _branches(node: ast.AST, headed: bool = False) -> list[tuple[ast.AST, bool]]:
    """One kind argument split into what it can be, with `kind_via(...)` unwrapped."""
    if isinstance(node, ast.IfExp):
        return _branches(node.body, headed) + _branches(node.orelse, headed)
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "kind_via" and node.args:
        return [(inner, True) for inner, _ in _branches(node.args[0])]
    return [(node, headed)]


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
            for branch, headed in _branches(node.args[2]):
                if isinstance(branch, ast.Constant) and isinstance(branch.value, str):
                    literals.append((rel, node.lineno, branch.value))
                    if headed:
                        literals.append((rel, node.lineno, f"{WEB}.{branch.value}"))
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


# Checklist 34: a route that calls a shared path which already logs must NOT `note()` the same
# event again — that is the 2026-09-03 "double posted all messages with a web.request and a
# request" defect. Nothing needs an exception today; an entry here is "<route fn>::<note kind>"
# with the reason the second line is a DIFFERENT event, not the same one twice.
DOUBLE_LOG_ALLOWED: dict[str, str] = {}


def _owner(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Each node's nearest enclosing function, so a nested route is read on its own."""
    found: dict[ast.AST, ast.AST] = {}

    def walk(node: ast.AST, holder: ast.AST | None) -> None:
        for child in ast.iter_child_nodes(node):
            mine = child if isinstance(child, FUNCTIONS) else holder
            if holder is not None:
                found[child] = holder
            if mine is not None and isinstance(child, FUNCTIONS):
                found[child] = holder if holder is not None else child
            walk(child, mine)

    walk(tree, None)
    return found


FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _defs(tree: ast.AST) -> dict[str, ast.AST]:
    return {node.name: node for node in ast.walk(tree) if isinstance(node, FUNCTIONS)}


def _called_names(node: ast.AST) -> set[str]:
    """Every plain and dotted call name made anywhere under one function."""
    found: set[str] = set()
    for call in ast.walk(node):
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if isinstance(func, ast.Name):
            found.add(func.id)
        elif isinstance(func, ast.Attribute):
            found.add(func.attr)
            if isinstance(func.value, ast.Name):
                found.add(f"{func.value.id}.{func.attr}")
    return found


def _kind_args(node: ast.AST, name: str) -> list[ast.AST]:
    return [
        call.args[2]
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and (
            call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
        )
        == name
        and len(call.args) > 2
    ]


def _modules() -> dict[str, tuple[ast.AST, dict[str, ast.AST]]]:
    found: dict[str, tuple[ast.AST, dict[str, ast.AST]]] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found[path.relative_to(ROOT).as_posix()] = (tree, _defs(tree))
    return found


def _logged_by(rel: str, name: str, modules: Any, seen: set[tuple[str, str]]) -> set[str]:
    """The bare kinds one shared function leaves, following the helpers it calls in its module."""
    if (rel, name) in seen or rel not in modules:
        return set()
    seen.add((rel, name))
    tree, defs = modules[rel]
    node = defs.get(name)
    if node is None:
        return set()
    found: set[str] = set()
    for wanted in _kind_args(node, "log_action"):
        for branch, _ in _branches(wanted):
            if isinstance(branch, ast.Constant) and isinstance(branch.value, str):
                found.add(bare(branch.value))
            else:
                found.update(
                    bare(kind)
                    for kind in KNOWN_DYNAMIC.get(f"{rel}::{_source(branch)}", ())
                )
    for called in _called_names(node) & set(defs):
        if called != name:
            found |= _logged_by(rel, called, modules, seen)
    return found


def _imported(rel: str, tree: ast.AST) -> dict[str, tuple[str, str]]:
    """`from ...cogs.x import f` and `from ... import y as z` resolved to (module file, name)."""
    here = pathlib.PurePosixPath(rel).parent
    found: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        base = here
        for _ in range(node.level - 1):
            base = base.parent
        stem = base.joinpath(*(node.module or "").split(".")) if node.module else base
        for alias in node.names:
            local = alias.asname or alias.name
            module = f"{stem}.py"
            if module in _MODULES:
                found[local] = (module, alias.name)
            elif f"{stem / alias.name}.py" in _MODULES:
                found[local] = (f"{stem / alias.name}.py", "")
    return found


_MODULES = _modules()
# The routes' own `note()` wrapper lives here and logs whatever kind it is handed, so a helper
# from under `api/` is never the "shared path" this guard is about.
API = "black_bloc/api/"


def test_a_route_never_notes_an_event_its_shared_path_already_logged():
    """The 2026-09-03 double-post: `request.done` from the cog AND `web.request.done` from the
    route. One write leaves one row, so the shared path takes `via` and the route deletes its
    `note()`. Only literal `note()` kinds are read; a computed one is reported as unchecked."""
    doubles: list[str] = []
    unchecked: list[str] = []
    for path in sorted((PACKAGE / "api" / "tools").glob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        tree, defs = _MODULES[rel]
        imports = _imported(rel, tree)
        owner = _owner(tree)
        for name, node in defs.items():
            mine = [
                call
                for call in ast.walk(node)
                if isinstance(call, ast.Call) and owner.get(call) is node
            ]
            shared: set[str] = set()
            for call in mine:
                func = call.func
                local = (
                    f"{func.value.id}.{func.attr}"
                    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                    else getattr(func, "id", None)
                )
                if local is None:
                    continue
                where, called = imports.get(local, (None, None))
                if where is None and local and "." in local:
                    head, _, tail = local.partition(".")
                    where, called = imports.get(head, (None, None))
                    called = tail if where else None
                if where is None or not called or where.startswith(API):
                    continue
                shared |= _logged_by(where, called, _MODULES, set())
            for call in mine:
                if getattr(call.func, "id", None) != "note" or len(call.args) < 3:
                    continue
                for branch, _ in _branches(call.args[2]):
                    if not (
                        isinstance(branch, ast.Constant) and isinstance(branch.value, str)
                    ):
                        unchecked.append(f"{rel}::{name}::{_source(branch)}")
                        continue
                    key = f"{name}::{branch.value}"
                    if bare(branch.value) in shared and key not in DOUBLE_LOG_ALLOWED:
                        doubles.append(f"{rel}::{key}")
    assert not sorted(doubles), (
        "these routes call a shared path that already logs the event and then note() it again, "
        "so one write leaves two rows and two embeds. Pass via=VIA_WEBSITE to the shared "
        f"function and delete the note(): {sorted(doubles)}"
    )
    assert sorted(unchecked) == [], unchecked


def test_the_note_table_names_exactly_the_kinds_routes_still_write():
    """A row for a kind nothing notes any more is how the 2026-09-03 fix went half-recorded.

    The five application-form kinds sat here for two days after the routes stopped writing
    them, which reads as "the website logs this twice" to anybody auditing the table.
    """
    written: set[str] = set()
    for rel, (tree, _defs) in _MODULES.items():
        if not rel.startswith(API):
            continue
        for wanted in _kind_args(tree, "note"):
            for branch, _ in _branches(wanted):
                if isinstance(branch, ast.Constant) and isinstance(branch.value, str):
                    written.add(branch.value)
    assert sorted(KNOWN_DYNAMIC["black_bloc/api/writes.py::kind"]) == sorted(written)


# The via-labelling audit (2026-09-05). A shared function a ROUTE calls should take `via` so
# the Logs page can say Via = Website. These do not, and each is here because its rows are a
# CONSEQUENCE the bot emits on its own — no actor, and the same rows come from a sweep with
# no person behind them — which checklist 34 says keeps the bare kind.
VIA_NOT_NEEDED: dict[str, str] = {
    "black_bloc/events.py::rename_channel": "cosmetic; would_rename/rename_failed carry no actor",
    "black_bloc/cogs/community/polls.py::send_review_card": "poll.card_failed is a failure row",
    "black_bloc/cogs/community/polls.py::post_poll": (
        "poll.opened has no actor and the recurrence sweep posts too; the creation row "
        "(store_poll) is the one that carries via"
    ),
}


def test_every_shared_function_a_route_calls_takes_via():
    """`raidtrain.cancel_train` logged one row and called a website cancel Via = Discord."""
    missing: list[str] = []
    for rel, (tree, _defs) in _MODULES.items():
        if not rel.startswith(API):
            continue
        for where, name in _imported(rel, tree).values():
            if not name or where.startswith(API):
                continue
            found = _MODULES[where][1].get(name)
            if found is None or not _kind_args(found, "log_action"):
                continue
            spec = found.args
            if any(arg.arg == "via" for arg in spec.args + spec.kwonlyargs):
                continue
            key = f"{where}::{name}"
            if key not in VIA_NOT_NEEDED:
                missing.append(key)
    assert not sorted(missing), (
        "these log an event and are called from a route, but take no `via`, so a website "
        f"action is written as though somebody typed it in Discord: {sorted(missing)}"
    )


def test_a_shared_logger_stays_discord_unless_a_route_says_otherwise():
    """The slash commands never pass `via`, so the default is what keeps their kinds bare.

    A private helper may take `via` with no default — it is always handed one — but anything
    that HAS a default must default to Discord, or a slash command starts writing `web.` kinds.
    """
    wrong: list[str] = []
    for rel, (_tree, defs) in _MODULES.items():
        if rel.startswith(API):
            continue
        for name, node in defs.items():
            spec = node.args
            for holder, room in ((spec.args, spec.defaults), (spec.kwonlyargs, spec.kw_defaults)):
                names = [arg.arg for arg in holder]
                if "via" not in names:
                    continue
                slot = names.index("via") - (len(holder) - len(room))
                given = room[slot] if 0 <= slot < len(room) else None
                if given is None:
                    continue
                if not (isinstance(given, ast.Name) and given.id == "VIA_DISCORD"):
                    wrong.append(f"{rel}::{name}")
    assert not sorted(wrong), (
        "a shared function's `via` must default to VIA_DISCORD, or a slash command would start "
        f"writing `web.` kinds: {sorted(wrong)}"
    )


def test_kind_via_is_bare_read_backwards():
    assert kind_via("request.done", VIA_WEBSITE) == "web.request.done"
    assert kind_via("request.done", VIA_DISCORD) == "request.done"
    assert bare(kind_via("request.done", VIA_WEBSITE)) == "request.done"
    assert via_of(kind_via("request.done", VIA_WEBSITE)) == VIA_WEBSITE
    assert via_of(kind_via("request.done", VIA_DISCORD)) == VIA_DISCORD


def test_no_module_builds_the_web_head_for_itself():
    """One implementation: `kind_via` is the only place `web.` is put on a kind."""
    guilty = [
        path.relative_to(ROOT).as_posix()
        for path in PACKAGE.rglob("*.py")
        if path.name != "logkinds.py"
        and 'f"{WEB}." if via ==' in path.read_text(encoding="utf-8")
    ]
    assert not guilty, f"these build the head by hand instead of calling kind_via: {guilty}"


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
        "request.withdrawn",
        "request.resumed",
        "request.check_asked",
        "request.in_progress",
        "request.updated",
        "request.comment",
        "request.notify_skipped_test_mode",
    ):
        assert is_important(kind) is False, kind
        assert is_important(f"web.{kind}") is False, kind
    for kind in ("request.hold", "request.declined", "request.done"):
        assert is_important(kind) is True, kind
        assert is_important(f"web.{kind}") is True, kind
    assert is_important("request.dm_failed") is True
    assert is_important("request.notify_failed") is True
    assert feature_of("request.filed") == "request"
    assert feature_of("web.request.hold") == "request"


def test_taking_somebody_off_an_application_list_is_routine_because_the_dm_is_the_loud_part():
    """`.removed` is a loud suffix; this one is listed as routine on purpose."""
    assert "application.removed" in ROUTINE
    assert is_important("application.removed") is False
    assert is_important("web.application.removed") is False
    assert feature_of("application.removed") == "applications"
    assert feature_of("web.application.removed") == "applications"


def test_memory_is_loud_when_something_is_forgotten_and_quiet_the_rest_of_the_time():
    """Writing a profile is housekeeping; losing one, and somebody opting out, are not."""
    for kind in ("chat.memory_distilled", "chat.memory_expired", "chat.memory_optin"):
        assert is_important(kind) is False, kind
    for kind in ("chat.memory_forgot", "chat.memory_optout"):
        assert is_important(kind) is True, kind
    assert is_important("chat.memory_distil_failed") is True
    assert feature_of("chat.memory_distilled") == "chat"
    assert feature_of("web.chat.memory_forgot") == "chat"


def test_via_reads_what_the_writer_recorded_and_falls_back_to_the_web_head():
    """Owner, 2026-08-27: a log line says whether Discord or the website did it."""
    assert via_of("settings.set", {"key": "golive_mode"}) == "discord"
    assert via_of("web.settings.set", {"key": "golive_mode"}) == "website"
    # what the writer recorded wins over the head, which is what a website path
    # logging a bare feature kind needs.
    assert via_of("request.approved", {"via": "website"}) == "website"
    assert via_of("web.request.approved", {"via": "discord"}) == "discord"
    # anything that is not one of the two words is not a decision, so the head decides
    assert via_of("settings.set", {"via": "carrier pigeon"}) == "discord"
    assert via_of("web.settings.set", {"via": ""}) == "website"
    assert via_of("settings.set", None) == "discord"
    assert via_of("settings.set", "not a dict") == "discord"
    # `web` on its own is not a head with anything under it
    assert via_of("web") == "discord"
    assert via_word("web.settings.set") == "Website"
    assert via_word("settings.set") == "Discord"
    # The self-test's boot door records its own word, so a boot run is not read as Discord.
    assert via_of("selftest.started", {"via": "boot"}) == VIA_BOOT
    assert via_word("selftest.started", {"via": "boot"}) == "By the bot at boot"
    assert set(VIA_WORDS) == {VIA_DISCORD, VIA_WEBSITE, VIA_OPERATOR, VIA_BOOT}


def test_an_operator_read_says_so_only_because_the_writer_recorded_it():
    """The kind carries a `web.` head, so nothing but `details["via"]` can make it operator."""
    assert via_of("web.operator.read") == VIA_WEBSITE
    assert via_of("web.operator.read", {"via": VIA_OPERATOR}) == VIA_OPERATOR
    assert via_word("web.operator.read", {"via": VIA_OPERATOR}) == "Operator token"
    assert via_of("web.operator.read", {"via": "the operator"}) == VIA_WEBSITE
    assert feature_of("web.operator.read") == "core"
    assert is_important("web.operator.read") is False
    assert "operator.read" in ROUTINE


def test_should_post_reads_the_three_levels():
    assert should_post("mod.banned", OFF) is False
    assert should_post("poll.created", OFF) is False
    assert should_post("mod.banned", IMPORTANT_ONLY) is True
    assert should_post("poll.created", IMPORTANT_ONLY) is False
    assert should_post("poll.created", ALL) is True


def test_a_carded_important_kind_only_posts_at_all():
    assert should_post("request.done", IMPORTANT_ONLY, carded=True) is False
    assert should_post("request.done", IMPORTANT_ONLY, carded=False) is True
    assert should_post("request.done", ALL, carded=True) is True
    assert should_post("request.done", OFF, carded=True) is False


def test_an_unknown_level_is_todays_behaviour():
    for level in (None, "", "quiet", "IMPORTANT"):
        assert should_post("poll.created", level) is True


def test_every_feature_has_one_settings_key():
    assert len(FEATURES) == 20
    assert len(set(FEATURES)) == 20
    assert log_level_key("golive") == "golive_log_level"
    assert LEVELS == (OFF, IMPORTANT_ONLY, ALL)


def test_the_test_feature_is_the_one_the_logs_page_leaves_out_until_it_is_asked_for():
    """Owner, 2026-09-05: 'keep the logs on the website tho under test' — kept, and out of
    the way. The exclusion is derived from HIDDEN_BY_DEFAULT, so there is one home for it."""
    assert "selftest" in FEATURES
    assert logkinds.FEATURE_LABELS["selftest"] == "Test"
    assert logkinds.FEATURE_PAGES["selftest"] == "health.html"
    assert logkinds.HIDDEN_BY_DEFAULT == ("selftest",)
    assert logkinds.hidden_by_default_patterns() == ("selftest.%", "web.selftest.%")
    assert feature_of("selftest.check") == "selftest"
    assert feature_of("web.selftest.check") == "selftest"
    # Not important, or the Logs page's Important switch would fill up with test rows —
    # and `.purged` would otherwise be caught by IMPORTANT_SUFFIXES.
    assert not any(is_important(kind) for kind in logkinds.SELFTEST_KINDS)


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
