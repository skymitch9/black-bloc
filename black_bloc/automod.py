from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

ACTIONS = ("delete", "warn", "timeout")
AUTOMOD_MODES = ("off", "shadow", "on")
MOD_DM_STYLES = ("none", "server_action", "server_action_reason")

RULE_ORDER = (
    "mention_spam",
    "slowmode",
    "linkspam",
    "invitespam",
    "attachmentspam",
    "caps",
    "bad_words",
)

WINDOW_MAX_SECONDS = 3600
THRESHOLD_MAX = 1000
TIMEOUT_MAX_SECONDS = 28 * 24 * 3600
CAPS_MIN_LETTERS = 8
WORDS_MAX = 200
WARN_THRESHOLD_DEFAULT = 8

DEFAULT_RULES: dict[str, dict[str, Any]] = {
    "mention_spam": {
        "enabled": True,
        "window_s": 30,
        "threshold": 5,
        "actions": ["delete", "warn", "timeout"],
        "timeout_s": 300,
    },
    "slowmode": {"enabled": True, "window_s": 4, "threshold": 6, "actions": [], "timeout_s": 0},
    "linkspam": {"enabled": True, "window_s": 1, "threshold": 1, "actions": [], "timeout_s": 0},
    "invitespam": {
        "enabled": False,
        "window_s": 30,
        "threshold": 1,
        "actions": ["delete", "warn", "timeout"],
        "timeout_s": 600,
    },
    "attachmentspam": {
        "enabled": False,
        "window_s": 30,
        "threshold": 5,
        "actions": [],
        "timeout_s": 0,
    },
    "caps": {"enabled": False, "window_s": 0, "threshold": 70, "actions": [], "timeout_s": 0},
    "bad_words": {
        "enabled": False,
        "window_s": 0,
        "threshold": 1,
        "actions": [],
        "timeout_s": 0,
        "words": [],
    },
}

RULE_NOUNS: dict[str, tuple[str, str]] = {
    "mention_spam": ("mention", "mentions"),
    "slowmode": ("message", "messages"),
    "linkspam": ("link", "links"),
    "invitespam": ("invite", "invites"),
    "attachmentspam": ("attachment", "attachments"),
    "bad_words": ("blocked word", "blocked words"),
}

RULE_HELP: dict[str, str] = {
    "mention_spam": "how many people or roles one member may mention in the window",
    "slowmode": "how many messages one member may post in the window",
    "linkspam": "how many links one member may post in the window",
    "invitespam": "how many Discord invites one member may post in the window",
    "attachmentspam": "how many files one member may post in the window",
    "caps": "the percentage of capital letters one message may be",
    "bad_words": "words that are not allowed; the bad_words rule's own word list holds them",
}

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
INVITE_PATTERN = re.compile(
    r"(?:discord(?:app)?\.com/invite|discord\.gg|discord\.me|dsc\.gg)/[A-Za-z0-9-]+",
    re.IGNORECASE,
)
EVERYONE_PATTERN = re.compile(r"@(?:everyone|here)")

UNKNOWN_RULE = (
    "**{given}** is not one of Black Bloc's automod rules, so nothing was changed. The rules are: "
    "{known}."
)
UNKNOWN_FIELD = (
    "**{given}** is not something an automod rule has, so nothing was changed. A rule has "
    "`enabled`, `window_s`, `threshold`, `actions`, `timeout_s` and (for bad_words) `words`."
)
BAD_ACTIONS = (
    "**{given}** is not an automod punishment, so nothing was changed. The punishments are "
    "`delete`, `warn` and `timeout`, written as a comma-separated list; leave it empty for a rule "
    "that only logs."
)


class RuleError(ValueError):
    """An automod rule object is the wrong shape, or one of its numbers is out of range."""


@dataclass(frozen=True, slots=True)
class MessageFacts:
    author_id: int
    channel_id: int
    message_id: int
    created_at: datetime
    mention_ids: tuple[int, ...] = ()
    everyone_count: int = 0
    links: tuple[str, ...] = ()
    invite_count: int = 0
    attachment_count: int = 0
    letters: int = 0
    capitals: int = 0
    content: str = ""

    @property
    def caps_ratio(self) -> float:
        return self.capitals / self.letters if self.letters else 0.0


@dataclass(frozen=True, slots=True)
class Hit:
    at: datetime
    message_id: int
    token: Any = None


@dataclass(frozen=True, slots=True)
class Verdict:
    rule: str
    actions: tuple[str, ...]
    sentence: str
    timeout_s: int = 0
    message_ids: tuple[int, ...] = ()
    count: int = 0


@dataclass
class WindowState:
    """Per (rule, member) sliding windows of what they did, kept in memory only."""

    hits: dict[tuple[str, int], deque[Hit]] = field(default_factory=dict)

    def record(self, rule: str, user_id: int, entries: list[Hit]) -> None:
        if not entries:
            return
        self.hits.setdefault((rule, int(user_id)), deque()).extend(entries)

    def window(self, rule: str, user_id: int, since: datetime) -> list[Hit]:
        return [h for h in self.hits.get((rule, int(user_id)), ()) if h.at >= since]

    def prune(self, now: datetime, oldest_seconds: int) -> None:
        cutoff = now - timedelta(seconds=max(int(oldest_seconds), 0))
        for key, entries in list(self.hits.items()):
            while entries and entries[0].at < cutoff:
                entries.popleft()
            if not entries:
                del self.hits[key]

    def clear(self, rule: str, user_id: int) -> None:
        self.hits.pop((rule, int(user_id)), None)

    def forget(self, user_id: int) -> None:
        for key in [k for k in self.hits if k[1] == int(user_id)]:
            del self.hits[key]

    def __len__(self) -> int:
        return sum(len(entries) for entries in self.hits.values())


def _as_bool(name: str, key: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise RuleError(f"`{name}.{key}` takes true or false, not {value!r}.")
    return value


def _as_int(name: str, key: str, value: Any, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuleError(f"`{name}.{key}` takes a whole number, not {value!r}.")
    if value < low or value > high:
        raise RuleError(f"`{name}.{key}` has to be between {low} and {high}, not {value}.")
    return value


def _as_actions(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [part.strip().lower() for part in value.split(",") if part.strip()]
    elif isinstance(value, list | tuple):
        items = [str(part).strip().lower() for part in value]
    else:
        raise RuleError(BAD_ACTIONS.format(given=value))
    picked: list[str] = []
    for item in items:
        if item not in ACTIONS:
            raise RuleError(BAD_ACTIONS.format(given=item))
        if item not in picked:
            picked.append(item)
    return [action for action in ACTIONS if action in picked]


WORD_SEPARATORS = re.compile(r"[,\r\n]")


def _as_words(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [part.strip() for part in WORD_SEPARATORS.split(value)]
    elif isinstance(value, list | tuple):
        items = [str(part).strip() for part in value]
    else:
        raise RuleError(
            "`bad_words.words` takes a list of words, one per line or separated by commas."
        )
    words: list[str] = []
    for item in items:
        lowered = item.lower()
        if lowered and lowered not in words:
            words.append(lowered)
    if len(words) > WORDS_MAX:
        raise RuleError(f"`bad_words.words` cannot hold more than {WORDS_MAX} words.")
    return words


def normalise_rule(name: str, config: Any) -> dict[str, Any]:
    """One rule object, filled in from the defaults and checked against Discord's limits."""
    if name not in DEFAULT_RULES:
        raise RuleError(UNKNOWN_RULE.format(given=name, known=", ".join(RULE_ORDER)))
    base = dict(DEFAULT_RULES[name])
    if config is None:
        return base
    if not isinstance(config, dict):
        raise RuleError(f"`{name}` takes a rule object, not {config!r}.")
    for key in config:
        if key not in base:
            raise RuleError(UNKNOWN_FIELD.format(given=key))
    merged = base | {key: config[key] for key in config}
    out: dict[str, Any] = {
        "enabled": _as_bool(name, "enabled", merged["enabled"]),
        "window_s": _as_int(name, "window_s", merged["window_s"], 0, WINDOW_MAX_SECONDS),
        "threshold": _as_int(name, "threshold", merged["threshold"], 1, THRESHOLD_MAX),
        "actions": _as_actions(merged["actions"]),
        "timeout_s": _as_int(name, "timeout_s", merged["timeout_s"], 0, TIMEOUT_MAX_SECONDS),
    }
    if name == "caps":
        out["threshold"] = _as_int(name, "threshold", merged["threshold"], 1, 100)
    if "words" in base:
        out["words"] = _as_words(merged["words"])
    return out


def validate_rules(value: Any) -> dict[str, dict[str, Any]]:
    """The whole `automod_rules` object: every known rule, every field in range."""
    if not isinstance(value, dict):
        raise RuleError("`automod_rules` takes a rule object keyed by rule name.")
    for name in value:
        if name not in DEFAULT_RULES:
            raise RuleError(UNKNOWN_RULE.format(given=name, known=", ".join(RULE_ORDER)))
    return {name: normalise_rule(name, value.get(name)) for name in RULE_ORDER}


def rule_config(rules: Any, name: str) -> dict[str, Any]:
    source = rules if isinstance(rules, dict) else {}
    try:
        return normalise_rule(name, source.get(name))
    except RuleError:
        return dict(DEFAULT_RULES[name])


def largest_window(rules: Any) -> int:
    return max(rule_config(rules, name)["window_s"] for name in RULE_ORDER)


def rules_summary(rules: Any) -> str:
    parts = []
    for name in RULE_ORDER:
        cfg = rule_config(rules, name)
        if not cfg["enabled"]:
            continue
        punishment = "+".join(cfg["actions"]) if cfg["actions"] else "log only"
        parts.append(f"{name} {cfg['threshold']}/{cfg['window_s']}s {punishment}")
    return "; ".join(parts) if parts else "every rule is off"


def describe_rule(name: str, cfg: dict[str, Any]) -> str:
    punishment = ", ".join(cfg["actions"]) if cfg["actions"] else "log only"
    if "timeout" in cfg["actions"]:
        punishment += f" ({cfg['timeout_s']}s)"
    state = "on" if cfg["enabled"] else "off"
    window = cfg["window_s"]
    where = f"{cfg['threshold']} in {window}s" if window else str(cfg["threshold"])
    extra = f" · words: {len(cfg['words'])}" if "words" in cfg else ""
    return f"**{name}** — {state} · {where} · {punishment}{extra}"


def count_letters(content: Any) -> tuple[int, int]:
    text = str(content or "")
    letters = [ch for ch in text if ch.isalpha()]
    return len(letters), sum(1 for ch in letters if ch.isupper())


def facts_from(message: Any) -> MessageFacts:
    """Everything the engine is allowed to know about one message."""
    content = str(getattr(message, "content", "") or "")
    letters, capitals = count_letters(content)
    mentions = [
        int(getattr(entity, "id", entity))
        for entity in list(getattr(message, "mentions", ()) or ())
        + list(getattr(message, "role_mentions", ()) or ())
    ]
    created = getattr(message, "created_at", None) or datetime.now(UTC)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return MessageFacts(
        author_id=int(getattr(message.author, "id", 0)),
        channel_id=int(getattr(message.channel, "id", 0)),
        message_id=int(getattr(message, "id", 0)),
        created_at=created,
        mention_ids=tuple(mentions),
        everyone_count=len(EVERYONE_PATTERN.findall(content)),
        links=tuple(URL_PATTERN.findall(content)),
        invite_count=len(INVITE_PATTERN.findall(content)),
        attachment_count=len(list(getattr(message, "attachments", ()) or ())),
        letters=letters,
        capitals=capitals,
        content=content,
    )


def matched_words(content: Any, words: Any) -> list[str]:
    lowered = str(content or "").lower()
    found = []
    for word in words or ():
        if re.search(rf"(?<!\w){re.escape(str(word).lower())}(?!\w)", lowered):
            found.append(str(word).lower())
    return found


def _tokens(name: str, cfg: dict[str, Any], facts: MessageFacts) -> list[Any]:
    if name == "mention_spam":
        return list(facts.mention_ids) + ["@everyone"] * facts.everyone_count
    if name == "slowmode":
        return [facts.message_id]
    if name == "linkspam":
        return list(facts.links)
    if name == "invitespam":
        return ["invite"] * facts.invite_count
    if name == "attachmentspam":
        return ["attachment"] * facts.attachment_count
    if name == "bad_words":
        return matched_words(facts.content, cfg.get("words", ()))
    return []


def _sentence(name: str, count: int, window_s: int) -> str:
    one, many = RULE_NOUNS.get(name, ("event", "events"))
    noun = one if count == 1 else many
    if window_s:
        return f"{count} {noun} in {window_s}s"
    return f"{count} {noun} in one message"


def _caps_verdict(cfg: dict[str, Any], facts: MessageFacts) -> Verdict | None:
    if facts.letters < CAPS_MIN_LETTERS:
        return None
    percent = round(facts.caps_ratio * 100)
    if percent < cfg["threshold"]:
        return None
    return Verdict(
        rule="caps",
        actions=tuple(cfg["actions"]),
        sentence=f"{percent}% capitals in a {facts.letters}-letter message",
        timeout_s=int(cfg["timeout_s"]),
        message_ids=(facts.message_id,),
        count=percent,
    )


def _rule_verdict(
    name: str, cfg: dict[str, Any], facts: MessageFacts, state: WindowState, now: datetime
) -> Verdict | None:
    tokens = _tokens(name, cfg, facts)
    window_s = int(cfg["window_s"])
    if window_s <= 0:
        count = len(tokens)
        message_ids: tuple[int, ...] = (facts.message_id,)
    else:
        if not tokens:
            return None
        state.record(
            name, facts.author_id, [Hit(facts.created_at, facts.message_id, t) for t in tokens]
        )
        hits = state.window(name, facts.author_id, now - timedelta(seconds=window_s))
        count = len(hits)
        message_ids = tuple(dict.fromkeys(hit.message_id for hit in hits))
    if count < cfg["threshold"]:
        return None
    if window_s > 0:
        state.clear(name, facts.author_id)
    return Verdict(
        rule=name,
        actions=tuple(cfg["actions"]),
        sentence=_sentence(name, count, window_s),
        timeout_s=int(cfg["timeout_s"]),
        message_ids=message_ids or (facts.message_id,),
        count=count,
    )


def evaluate(
    facts: MessageFacts, state: WindowState, rules: Any, *, now: datetime | None = None
) -> list[Verdict]:
    """Every rule this message trips, given what the member did before it."""
    moment = now or facts.created_at
    verdicts: list[Verdict] = []
    for name in RULE_ORDER:
        cfg = rule_config(rules, name)
        if not cfg["enabled"]:
            continue
        verdict = _caps_verdict(cfg, facts) if name == "caps" else _rule_verdict(
            name, cfg, facts, state, moment
        )
        if verdict is not None:
            verdicts.append(verdict)
    state.prune(moment, largest_window(rules))
    return verdicts


def exempt_reason(
    member: Any, staff_ids: set[int], exempt_role_ids: set[int]
) -> str | None:
    """Why automod is ignoring this author, or None when the engine should see them."""
    if getattr(member, "bot", False):
        return "bot"
    perms = getattr(member, "guild_permissions", None)
    if perms is not None and getattr(perms, "manage_guild", False):
        return "manage_guild"
    role_ids = {getattr(role, "id", None) for role in getattr(member, "roles", ())}
    if role_ids & staff_ids:
        return "staff"
    if role_ids & exempt_role_ids:
        return "exempt_role"
    return None


def channel_exempt(channel: Any, exempt_channel_ids: set[int], honeypot_ids: set[int]) -> bool:
    ids = {getattr(channel, "id", None), getattr(channel, "parent_id", None)} - {None}
    return bool(ids & (exempt_channel_ids | honeypot_ids))


PANEL_MINUTES_KEY = "automod_panel_minutes"
ARM_CONFIRM_KEY = "automod_arm_needs_confirm"
PANEL_TITLE = "What automod is watching"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /automod again"

RULE_FIELDS = ("enabled", "window_s", "threshold", "actions", "timeout_s", "words")

MODE_LABELS: dict[str, str] = {
    "off": "off — nothing is read and nothing is counted",
    "shadow": "shadow — it logs what it would have done, and does none of it",
    "on": "on — it deletes, warns and times people out for real",
}

ROLE = "role"
CHANNEL = "channel"
EXEMPT_ROLE_LABEL = "role — {name}"
EXEMPT_CHANNEL_LABEL = "channel — #{name}"
GONE_ROLE = "a role Discord no longer has ({ident})"
GONE_CHANNEL = "a channel Discord no longer has ({ident})"

WINDOW_LABEL = "Seconds counted over (0 = one message)"
TIMEOUT_LABEL = "Timeout in seconds (0 = no timeout)"
CAPS_THRESHOLD_LABEL = "Percent capitals, 1–100"
THRESHOLD_LABEL = "How many {plural} it allows"
THRESHOLD_FALLBACK = "How many before it acts"

ENABLE = "enable"
DISABLE = "disable"
NUMBERS = "numbers"
LOG_ONLY = "log_only"
WORDS = "words"
BACK = "back"
EXEMPTIONS = "exemptions"
SETTINGS = "settings"
REFRESH = "refresh"
LOGS = "logs"
SITE = "site"
PANEL_NUMBERS = "panel_numbers"
ARM_CONFIRM = "arm_confirm"
ARM = "arm"
KEEP = "keep"


class AutomodMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 0
    modal: bool = False


TURN_ON_MOVE = AutomodMove(ENABLE, "Turn it on", "primary")
TURN_OFF_MOVE = AutomodMove(DISABLE, "Turn it off", "secondary")
NUMBERS_MOVE = AutomodMove(NUMBERS, "Change the numbers…", "secondary", modal=True)
LOG_ONLY_MOVE = AutomodMove(LOG_ONLY, "Log only", "danger")
WORDS_MOVE = AutomodMove(WORDS, "Words…", "secondary", modal=True)
BACK_MOVE = AutomodMove(BACK, "Back", "secondary")

EXEMPTIONS_MOVE = AutomodMove(EXEMPTIONS, "Exemptions…", "secondary", row=2)
SETTINGS_MOVE = AutomodMove(SETTINGS, "Settings…", "secondary", row=2)
REFRESH_MOVE = AutomodMove(REFRESH, "Refresh", "secondary", row=2)
LOGS_MOVE = AutomodMove(LOGS, "Logs", "secondary", row=2)
SITE_MOVE = AutomodMove(SITE, "Open on the site", "link", row=2)

EXEMPT_BACK_MOVE = AutomodMove(BACK, "Back", "secondary", row=3)
PANEL_NUMBERS_MOVE = AutomodMove(PANEL_NUMBERS, "Numbers…", "secondary", modal=True)
CONFIRM_ON_MOVE = AutomodMove(ARM_CONFIRM, "Stop asking before arming", "secondary")
CONFIRM_OFF_MOVE = AutomodMove(ARM_CONFIRM, "Ask before arming", "secondary")
ARM_MOVE = AutomodMove(ARM, "Yes, arm it", "danger")
KEEP_SHADOW_MOVE = AutomodMove(KEEP, "Keep it in shadow", "secondary")
KEEP_OFF_MOVE = AutomodMove(KEEP, "Keep it off", "secondary")

PANEL_MOVES = (
    TURN_ON_MOVE,
    TURN_OFF_MOVE,
    NUMBERS_MOVE,
    LOG_ONLY_MOVE,
    WORDS_MOVE,
    BACK_MOVE,
    EXEMPTIONS_MOVE,
    SETTINGS_MOVE,
    REFRESH_MOVE,
    LOGS_MOVE,
    SITE_MOVE,
    EXEMPT_BACK_MOVE,
    PANEL_NUMBERS_MOVE,
    CONFIRM_ON_MOVE,
    CONFIRM_OFF_MOVE,
    ARM_MOVE,
    KEEP_SHADOW_MOVE,
    KEEP_OFF_MOVE,
)


def card_buttons(cfg: dict[str, Any], *, has_words: bool) -> tuple[AutomodMove, ...]:
    """One rule card's first row: never both spellings of the toggle, never a dead button."""
    found = [TURN_OFF_MOVE if cfg.get("enabled") else TURN_ON_MOVE, NUMBERS_MOVE]
    if cfg.get("actions"):
        found.append(LOG_ONLY_MOVE)
    if has_words:
        found.append(WORDS_MOVE)
    found.append(BACK_MOVE)
    return tuple(found)


def root_buttons(*, has_site: bool) -> tuple[AutomodMove, ...]:
    found = [EXEMPTIONS_MOVE, SETTINGS_MOVE, REFRESH_MOVE, LOGS_MOVE]
    if has_site:
        found.append(SITE_MOVE)
    return tuple(found)


def settings_buttons(*, asks_twice: bool) -> tuple[AutomodMove, ...]:
    toggle = CONFIRM_ON_MOVE if asks_twice else CONFIRM_OFF_MOVE
    return (PANEL_NUMBERS_MOVE, toggle, BACK_MOVE)


def confirm_buttons(current: str) -> tuple[AutomodMove, ...]:
    return (ARM_MOVE, KEEP_SHADOW_MOVE if current == "shadow" else KEEP_OFF_MOVE)


def mode_options(current: str, may_arm: bool) -> list[tuple[str, str, bool]]:
    """P3: `on` is left off the picker while arming would refuse, never offered-and-refused."""
    return [
        (name, MODE_LABELS[name], name == current)
        for name in AUTOMOD_MODES
        if may_arm or name != "on"
    ]


def needs_confirm(current: str, wanted: str, asked: bool) -> bool:
    """Only arming asks twice; every quieter move fails safe and goes through in one press."""
    return bool(asked) and wanted == "on" and current != "on"


def rule_field_labels(name: str) -> dict[str, str]:
    """RULE_NOUNS has no `caps` entry, so the modal's labels are their own map, not a lookup."""
    if name == "caps":
        threshold = CAPS_THRESHOLD_LABEL
    else:
        nouns = RULE_NOUNS.get(name)
        threshold = THRESHOLD_LABEL.format(plural=nouns[1]) if nouns else THRESHOLD_FALLBACK
    return {"window_s": WINDOW_LABEL, "threshold": threshold, "timeout_s": TIMEOUT_LABEL}


def exempt_options(
    role_ids: Any, channel_ids: Any, names: Any = None
) -> list[tuple[str, int, str]]:
    """One removal select for both kinds; something Discord lost still gets a row to remove."""
    from .panels import SELECT_OPTION_LIMIT

    known = names or {}
    found: list[tuple[str, int, str]] = []
    for kind, ids, label, gone in (
        (ROLE, role_ids, EXEMPT_ROLE_LABEL, GONE_ROLE),
        (CHANNEL, channel_ids, EXEMPT_CHANNEL_LABEL, GONE_CHANNEL),
    ):
        for one in ids or ():
            ident = int(one)
            name = known.get((kind, ident))
            said = label.format(name=name) if name else gone.format(ident=ident)
            found.append((kind, ident, said[:SELECT_OPTION_LIMIT]))
    return found


def typed(field_name: str, raw: Any) -> Any:
    """One rule field as the engine wants it; RuleError carries the sentence when it is not."""
    text = str(raw or "").strip()
    if field_name == "enabled":
        if text.lower() in ("true", "yes", "on"):
            return True
        if text.lower() in ("false", "no", "off"):
            return False
        raise RuleError(f"`enabled` takes true or false, not {raw!r}.")
    if field_name in ("window_s", "threshold", "timeout_s"):
        if not text.isdigit():
            raise RuleError(f"`{field_name}` takes a whole number, not {raw!r}.")
        return int(text)
    if field_name in ("actions", "words"):
        return text
    raise RuleError(f"`{field_name}` is not something an automod rule has.")


def panel_minutes(store: Any, guild_id: int) -> int:
    from .panels import panel_minutes as _minutes

    return _minutes(store, guild_id, PANEL_MINUTES_KEY)


def arm_needs_confirm(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, ARM_CONFIRM_KEY))
