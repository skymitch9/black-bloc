import ast
import pathlib
from typing import Any

import pytest

from black_bloc import logkinds
from black_bloc.logkinds import (
    ALL,
    ERROR_BUTTON,
    ERROR_COMMAND,
    ERROR_KINDS,
    ERROR_MODAL,
    ERROR_PANEL,
    FEATURE_PAGES,
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
    VIA_FORUM,
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
    # Meeting minutes keeps its kinds as module constants in `minutes.py` so the module, the
    # session, the cog and the routes name each one once. The four a website door can also
    # write are listed in both spellings.
    "black_bloc/cogs/community/minutes.py::mins.STARTED": ("minutes.started",),
    "black_bloc/cogs/community/minutes.py::mins.PURGED": ("minutes.purged",),
    "black_bloc/minutes_session.py::mins.ENDED": ("minutes.ended",),
    "black_bloc/minutes_session.py::mins.JOIN_FAILED": ("minutes.join_failed",),
    "black_bloc/minutes_session.py::mins.TRANSCRIBE_FAILED": ("minutes.transcribe_failed",),
    "black_bloc/minutes.py::NOTES_WRITTEN": (
        "minutes.notes_written",
        "web.minutes.notes_written",
    ),
    "black_bloc/minutes.py::NOTES_FAILED": (
        "minutes.notes_failed",
        "web.minutes.notes_failed",
    ),
    "black_bloc/minutes.py::POSTED": ("minutes.posted", "web.minutes.posted"),
    "black_bloc/minutes.py::POST_FAILED": ("minutes.post_failed", "web.minutes.post_failed"),
    "black_bloc/minutes.py::NOTES_EDITED": (
        "minutes.notes_edited",
        "web.minutes.notes_edited",
    ),
    "black_bloc/minutes.py::DELETED": ("minutes.deleted", "web.minutes.deleted"),
    "black_bloc/minutes.py::MODE_SET": ("minutes.mode", "web.minutes.mode"),
    # One helper records every draft decision, so the four moves pass their kind in.
    "black_bloc/channel_drafts.py::kind": (
        "chat.channel_draft_used",
        "web.chat.channel_draft_used",
        "chat.channel_draft_rewritten",
        "web.chat.channel_draft_rewritten",
        "chat.channel_draft_none",
        "web.chat.channel_draft_none",
        "chat.channel_draft_reset",
        "web.chat.channel_draft_reset",
    ),
    # `record()` writes one row per failure and the surface it failed on names the kind —
    # four, and only four (`errors-design.md` §A).
    "black_bloc/command_errors.py::surface": ERROR_KINDS,
    # `posted.py` deletes a message for whoever asked, and the caller names the shadow kind
    # it writes when test mode refuses the channel — two callers, three kinds.
    "black_bloc/posted.py::would_kind": (
        "modmail.would_take_down_panel",
        "frontdoor.would_take_down",
        "frontdoor.would_hide_ticket_button",
    ),
    # The front door's kinds are module constants so the cog, the route and the tests name
    # them once; the four a website door can also write are listed in both spellings.
    "black_bloc/cogs/community/frontdoor.py::POSTED": ("frontdoor.posted", "web.frontdoor.posted"),
    "black_bloc/cogs/community/frontdoor.py::MOVED": ("frontdoor.moved", "web.frontdoor.moved"),
    "black_bloc/cogs/community/frontdoor.py::TAKEN_DOWN": (
        "frontdoor.taken_down",
        "web.frontdoor.taken_down",
    ),
    "black_bloc/cogs/community/frontdoor.py::WOULD_POST": (
        "frontdoor.would_post",
        "web.frontdoor.would_post",
    ),
    # The rehearsal copy's three: the door writes them from the sweep and from either door,
    # so the website spelling is listed beside the bare one.
    "black_bloc/cogs/community/frontdoor.py::POSTED_SHADOW": (
        "frontdoor.posted_shadow",
        "web.frontdoor.posted_shadow",
    ),
    "black_bloc/cogs/community/frontdoor.py::UPDATED_SHADOW": (
        "frontdoor.updated_shadow",
        "web.frontdoor.updated_shadow",
    ),
    "black_bloc/cogs/community/frontdoor.py::TAKEN_DOWN_SHADOW": (
        "frontdoor.taken_down_shadow",
        "web.frontdoor.taken_down_shadow",
    ),
    "black_bloc/cogs/community/frontdoor.py::GONE": ("frontdoor.gone",),
    "black_bloc/cogs/community/frontdoor.py::moved_or_gone": (
        "frontdoor.below_post",
        "frontdoor.gone",
    ),
    "black_bloc/cogs/community/frontdoor.py::BELOW_POST": ("frontdoor.below_post",),
    "black_bloc/cogs/community/frontdoor.py::POST_FAILED": ("frontdoor.post_failed",),
    "black_bloc/cogs/community/frontdoor.py::TICKET_BUTTON_HIDDEN": (
        "frontdoor.ticket_button_hidden",
    ),
    "black_bloc/cogs/community/frontdoor.py::DUPLICATE_SEEN": ("frontdoor.duplicate_seen",),
    # The ticket button's rehearsal copy: three constants, each written from the sweep and
    # from either door, so the website spelling is listed beside the bare one.
    "black_bloc/cogs/moderation/modmail.py::PANEL_POSTED_SHADOW": (
        "modmail.panel_posted_shadow",
        "web.modmail.panel_posted_shadow",
    ),
    "black_bloc/cogs/moderation/modmail.py::PANEL_UPDATED_SHADOW": (
        "modmail.panel_updated_shadow",
        "web.modmail.panel_updated_shadow",
    ),
    "black_bloc/cogs/moderation/modmail.py::PANEL_TAKEN_DOWN_SHADOW": (
        "modmail.panel_taken_down_shadow",
        "web.modmail.panel_taken_down_shadow",
    ),
    "black_bloc/cogs/moderation/modmail.py::moved_or_gone": (
        "modmail.panel_below_post",
        "modmail.panel_gone",
    ),
    # Every hand-off writes one row naming both ends; `handoff.py` builds the kind from
    # the two words so the five moves have one home rather than five literals.
    # The question and the member's no are constants so the cog and the tests name them once.
    "black_bloc/handoff.py::ASKED_KIND": ("handoff.asked",),
    # The birthday post-today door is pressed from the panel and the site, so both spellings.
    "black_bloc/cogs/community/birthdays.py::POSTED_NOW": (
        "birthday.posted_now",
        "web.birthday.posted_now",
    ),
    "black_bloc/handoff.py::REFUSED_KIND": ("handoff.refused",),
    "black_bloc/handoff.py::handoff_kind(source, target)": (
        "handoff.event_to_request",
        "handoff.request_to_event",
        "handoff.request_to_ticket",
        "handoff.ticket_to_event",
        "handoff.ticket_to_request",
    ),
    "black_bloc/api/writes.py::kind": (
        "web.birthday.clear",
        "web.birthday.optin",
        "web.birthday.set",
        "web.chat.intent_created",
        "web.chat.intent_deleted",
        "web.chat.intent_edited",
        "web.chat.line_added",
        "web.chat.line_deleted",
        "web.chat.line_edited",
        "web.core.restart_requested",
        "web.event.edited",
        "web.guide.confirmed",
        "web.guide.created",
        "web.guide.deleted",
        "web.guide.edited",
        "web.guide.media_replaced",
        "web.guide.published",
        "web.guide.reset",
        "web.guide.shots_stale",
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
    # The streamer list's kinds are module constants. The two prunes and the first sighting are
    # the LISTENER's and the SWEEP's alone and have no website door; the rest have both.
    "black_bloc/pings.py::STREAMER_SEEN": ("pings.streamer_seen",),
    "black_bloc/pings.py::STREAMER_PRUNED": ("pings.streamer_pruned",),
    "black_bloc/pings.py::ROLE_PRUNED": ("pings.role_pruned",),
    "black_bloc/pings.py::STREAMER_HIDDEN": (
        "pings.streamer_hidden",
        "web.pings.streamer_hidden",
    ),
    "black_bloc/pings.py::STREAMER_RESTORED": (
        "pings.streamer_restored",
        "web.pings.streamer_restored",
    ),
    "black_bloc/pings_onboarding.py::SYNCED": (
        "pings.onboarding_synced",
        "web.pings.onboarding_synced",
    ),
    "black_bloc/pings_onboarding.py::FAILED": (
        "pings.onboarding_failed",
        "web.pings.onboarding_failed",
    ),
    "black_bloc/pings_onboarding.py::TOOK_OVER": (
        "pings.onboarding_took_over",
        "web.pings.onboarding_took_over",
    ),
    # Polls in shadow: ONE call writes either the rehearsal's kind or the real one, and the
    # pin's four kinds are module constants with no website door.
    "black_bloc/cogs/community/polls.py::OPENED_SHADOW": (
        "poll.opened_shadow",
        "poll.opened",
    ),
    "black_bloc/cogs/community/polls.py::PINNED": ("poll.pinned",),
    "black_bloc/cogs/community/polls.py::PIN_FAILED": ("poll.pin_failed",),
    "black_bloc/cogs/community/polls.py::UNPINNED": ("poll.unpinned",),
    "black_bloc/cogs/community/polls.py::UNPIN_FAILED": ("poll.unpin_failed",),
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
        "event.forum_forgotten",
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
        "modmail.forum_forgotten",
        "modmail.log_channel_forgotten",
    ),
    "black_bloc/command_visibility.py::LOG_KIND": ("commands.visibility",),
    "black_bloc/orphaned.py::PANEL_EXPIRED_CLICK": ("panel.expired_click",),
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
        "post.restored",
        "post.saved",
        "post.shadow_message_gone",
        "post.shadow_posted",
        "post.shadow_taken_down",
        "post.shadow_updated",
        "post.taken_down",
        "post.updated",
        "post.versions_trimmed",
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
        "web.post.restored",
        "web.post.saved",
        "web.post.shadow_message_gone",
        "web.post.shadow_posted",
        "web.post.shadow_taken_down",
        "web.post.shadow_updated",
        "web.post.taken_down",
        "web.post.updated",
        "web.post.versions_trimmed",
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
        ("panel.expired_click", "core"),
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


def test_adding_a_platform_is_loud_because_it_rewrote_a_post_and_dropping_one_is_not():
    """A co-stream edit changes what members are reading; one platform going quiet does not."""
    assert is_important("golive.costream_added") is True
    assert is_important("golive.costream_dropped") is False
    assert feature_of("golive.costream_added") == "golive"
    assert feature_of("golive.costream_dropped") == "golive"


def test_a_channel_with_no_spotlight_has_its_own_kinds_so_the_title_cannot_lie():
    """Owner, 2026-09-21: "why is gdq being spotlighted in the logs channel? its spot light
    isnt on". The kind IS the log embed's title, so the word has to match the behaviour."""
    assert "golive.channel_announced" in ROUTINE
    assert is_important("golive.channel_announced") is False
    assert "golive.channel_ended" in ROUTINE
    assert is_important("golive.channel_ended") is False
    for kind in ("golive.channel_announced", "golive.channel_ended"):
        assert feature_of(kind) == "golive"
        assert "golive.%" in like_patterns("golive")
    assert is_shadow("golive.would_channel_announce") is True
    assert is_important("golive.would_channel_announce") is False
    assert "golive.would_channel_announce" not in ROUTINE
    assert {"golive.channel_announced", "golive.channel_ended"} <= emitted_kinds()


# Owner, 2026-09-21 17:2x, verbatim: "okay that works, i dont want log messages appearing in
# black bloc logs for channel linking or channel spotlight or channel annouce". The rows are
# still written to `action_log` and still shown on the Logs page — only the Discord mirror goes
# quiet, and `golive_log_level = all` turns it back up with no deploy.
QUIET_CHANNEL_KINDS: tuple[str, ...] = (
    "golive.link",
    "youtube.link",
    "golive.history_swept",
    "golive.spotlight_added",
    "golive.spotlight_announced",
    "golive.spotlight_announcement_refreshed",
    "golive.spotlight_bumped",
    "golive.spotlight_expired",
    "golive.spotlight_pinned",
    "golive.spotlight_removed",
    "golive.spotlight_unpinned",
    "golive.spotlight_updated",
    "golive.channel_announced",
)


def test_linking_spotlighting_and_announcing_a_channel_leave_no_embed_in_the_log_channel():
    """The owner's words above: a whole family goes quiet in `#blackbloc-logs`, and nowhere else."""
    for kind in QUIET_CHANNEL_KINDS:
        assert kind in ROUTINE, kind
        assert is_important(kind) is False, kind
        assert is_important(f"web.{kind}") is False, kind
        assert should_post(kind, IMPORTANT_ONLY) is False, kind
        assert feature_of(kind) in ("golive", "youtube"), kind
    # Turning the mirror back up is the level, not a deploy — and nothing was taken off the page.
    for kind in QUIET_CHANNEL_KINDS:
        assert should_post(kind, ALL) is True, kind
        assert should_post(kind, OFF) is False, kind


def test_the_failed_twin_of_every_quiet_channel_kind_is_still_loud():
    """Checklist 2: a refusal must never go quiet with the success it is not."""
    for kind in (
        "golive.post_failed",
        "golive.post_delete_failed",
        "golive.spotlight_announcement_refresh_failed",
        "golive.spotlight_pin_failed",
        "golive.spotlight_post_failed",
        "golive.spotlight_unpin_failed",
        "golive.unpin_failed",
        "youtube.resolve_failed",
        "youtube.live_announce_failed",
    ):
        assert is_important(kind) is True, kind
        assert should_post(kind, IMPORTANT_ONLY) is True, kind
    # The alarms and the member's own choices the owner did NOT ask to quieten.
    assert is_important("golive.role_stuck") is True
    assert is_important("youtube.probe_unreadable") is True
    assert is_important("golive.costream_added") is True


def test_taking_somebody_off_an_application_list_is_routine_because_the_dm_is_the_loud_part():
    """`.removed` is a loud suffix; this one is listed as routine on purpose."""
    assert "application.removed" in ROUTINE
    assert is_important("application.removed") is False
    assert is_important("web.application.removed") is False
    assert feature_of("application.removed") == "applications"
    assert feature_of("web.application.removed") == "applications"


def test_a_channel_note_is_routine_from_either_door_and_files_under_chat():
    """Staff describing a channel is housekeeping; the row is for the Logs page, not Discord."""
    for kind in ("chat.channel_note_set", "chat.channel_note_cleared"):
        assert kind in ROUTINE
        assert kind in emitted_kinds() and f"{WEB}.{kind}" in emitted_kinds()
        assert is_important(kind) is False
        assert feature_of(kind) == feature_of(f"{WEB}.{kind}") == "chat"


def test_a_channel_draft_decision_is_routine_from_either_door_and_files_under_chat():
    """Reviewing the catalog's drafts is housekeeping, one row per decision, from either door."""
    for move in ("used", "rewritten", "none", "reset"):
        kind = f"chat.channel_draft_{move}"
        assert kind in ROUTINE
        assert kind in emitted_kinds() and f"{WEB}.{kind}" in emitted_kinds()
        assert is_important(kind) is False
        assert feature_of(kind) == feature_of(f"{WEB}.{kind}") == "chat"
    assert "chat.channel_drafts_seeded" in ROUTINE
    assert "chat.channel_drafts_seeded" in emitted_kinds()


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
    # A request adopted from a hand-made forum post records its own word, so the Logs page
    # does not read it as an ordinary Discord filing (blackmail-threads §G).
    assert via_of("request.filed", {"via": "forum"}) == VIA_FORUM
    assert via_word("request.filed", {"via": "forum"}) == "A forum post"
    assert set(VIA_WORDS) == {VIA_DISCORD, VIA_WEBSITE, VIA_OPERATOR, VIA_BOOT, VIA_FORUM}


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
    assert len(FEATURES) == 21
    assert len(set(FEATURES)) == 21
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
        "error.%",
        "web.error.%",
        "panel.%",
        "web.panel.%",
        "settings.%",
        "web.settings.%",
        "commands.%",
        "web.commands.%",
        "presence.%",
        "web.presence.%",
    )


# The `error.*` family (`docs/info/errors-design.md` §A): four kinds, all IMPORTANT, headed
# core, and offered on the site's Logs page as a filter of their own.


def test_every_error_kind_is_important_because_a_failure_is_never_routine():
    assert ERROR_KINDS == (ERROR_COMMAND, ERROR_PANEL, ERROR_MODAL, ERROR_BUTTON)
    for kind in ERROR_KINDS:
        assert is_important(kind), kind
        assert kind in IMPORTANT and kind not in ROUTINE


def test_every_error_kind_is_headed_core_so_it_lands_on_the_dashboard():
    for kind in ERROR_KINDS:
        assert feature_of(kind) == "core"
    assert logkinds.HEADS[logkinds.ERROR_HEAD] == "core"


def test_the_logs_page_offers_the_error_family_as_a_filter_of_its_own():
    """`error.*` is headed core, so without this chip the failures are buried in Core."""
    assets = ROOT / "site" / "public" / "assets"
    logs = (assets / "logs.js").read_text(encoding="utf-8")
    audit = (assets / "page-audit.js").read_text(encoding="utf-8")

    assert f"kind: '{logkinds.ERROR_HEAD}'" in logs
    assert "label: 'Errors'" in logs
    assert "entry.kind" in audit


def test_the_two_kinds_a_trains_event_writes_are_classified_the_way_they_were_decided():
    """`event_made` is a member-visible decision; the cascade behind a cancel is routine."""
    assert is_important("raidtrain.event_made") is True
    assert is_important("web.raidtrain.event_made") is True
    assert is_important("raidtrain.event_cancelled") is False
    assert feature_of("raidtrain.event_made") == "raidtrain"
    assert feature_of("web.raidtrain.event_cancelled") == "raidtrain"


def test_raid_trains_own_page_is_the_one_the_footer_and_the_panel_link_to():
    assert FEATURE_PAGES["raidtrain"] == "raidtrain.html"


def test_the_member_optout_end_rows_are_routine_and_their_failures_important():
    """A refused delete or unpin must never look like a quiet success (checklist 2)."""
    assert _classification("golive.post_deleted") == "routine"
    assert _classification("golive.unpinned") == "routine"
    assert _classification("golive.post_delete_failed") == "important (_failed)"
    assert _classification("golive.unpin_failed") == "important (_failed)"
