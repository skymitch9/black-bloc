"""The keys of a stored tone: how it settles, what moves it, and every word staff are told."""

from __future__ import annotations

from typing import Any

from .personas import DRIFT_CHANCE, MANIFEST

DRIFT_START_KEY = "chat_tone_drift_start_percent"
DRIFT_HALVES_KEY = "chat_tone_drift_halves_every"
DRIFT_FLOOR_KEY = "chat_tone_drift_floor_percent"
FEEDBACK_MODE_KEY = "chat_tone_feedback_mode"
FEEDBACK_CUES_KEY = "chat_tone_feedback_cues"
GENTLE_ORDER_KEY = "chat_tone_gentle_order"
CAREFUL_ORDER_KEY = "chat_tone_careful_order"

DRIFT_START_PERCENT = round(DRIFT_CHANCE * 100)
DRIFT_HALVES_EVERY = 4
DRIFT_HALVES_MAX = 1000
DRIFT_FLOOR_PERCENT = 2
PERCENT_MAX = 100
FEEDBACK_MODES = ("off", "on")
FEEDBACK_CUES = (
    "mean, rude, hurtful, harsh, uncalled for, not cool, not okay, not ok, offensive, "
    "disrespectful, condescending, patronizing, patronising, that hurt, hurt my feelings, "
    "be nice, wrong, incorrect, not true, not right, not correct, inaccurate, made that up, "
    "making things up, a lie, lying, misinformation, mistake"
)
GENTLE_ORDER = (
    "warm, cozy, shy, peppy, scholar, dramatic, flirty, noir, deadpan, mischievous, tsundere"
)
CAREFUL_ORDER = (
    "scholar, shy, warm, cozy, deadpan, noir, peppy, flirty, tsundere, mischievous, dramatic"
)
KNOWN_TONES = tuple(str(one["name"]) for one in MANIFEST.get("tropes", ()))
ORDER_UNKNOWN = (
    "**{name}** is not one of the tones Black Bloc knows, so nothing was changed. The tones are "
    "{known}."
)

TONE_SETTINGS: dict[str, tuple[str, Any, str]] = {
    DRIFT_START_KEY: (
        "int",
        DRIFT_START_PERCENT,
        "the chance, in percent, that a member's tone takes one step to a neighbouring tone "
        f"when it is checked (every few answers) while the tone is new. 0 to {PERCENT_MAX}; 0 "
        "means a tone never moves on its own",
    ),
    DRIFT_HALVES_KEY: (
        "int",
        DRIFT_HALVES_EVERY,
        "how many of a member's conversations pass before that chance is halved again, so a "
        f"tone settles the longer nobody complains. 0 means it never settles, up to "
        f"{DRIFT_HALVES_MAX}",
    ),
    DRIFT_FLOOR_KEY: (
        "int",
        DRIFT_FLOOR_PERCENT,
        "the lowest that chance ever falls to, in percent, however settled a tone is. 0 to "
        f"{PERCENT_MAX}; 0 means a fully settled tone stops moving on its own",
    ),
    FEEDBACK_MODE_KEY: (
        "enum",
        "on",
        "on (when a member genuinely tells Black Bloc it was mean or wrong, their tone moves "
        "one step gentler or more careful and is new again; joking never counts) or off "
        "(nothing a member says moves their tone)",
    ),
    FEEDBACK_CUES_KEY: (
        "text",
        FEEDBACK_CUES,
        "words and phrases, separated by commas, that might mean a member is telling Black "
        "Bloc it was mean or wrong. Only a message said TO Black Bloc (a reply to its answer, "
        "or an @-mention) with one of them is handed to the quick model to judge. Blank means "
        "no message is ever judged",
    ),
    GENTLE_ORDER_KEY: (
        "text",
        GENTLE_ORDER,
        "the tones from gentlest to sharpest, separated by commas. A member who says Black "
        "Bloc was mean moves to the nearest tone before theirs in this list that is switched "
        "on; a tone left out never moves this way",
    ),
    CAREFUL_ORDER_KEY: (
        "text",
        CAREFUL_ORDER,
        "the tones from most careful to least, separated by commas. A member who says Black "
        "Bloc was wrong moves to the nearest tone before theirs in this list that is switched "
        "on; a tone left out never moves this way",
    ),
}
ORDER_KEYS = (GENTLE_ORDER_KEY, CAREFUL_ORDER_KEY)
MAY_BE_BLANK = (FEEDBACK_CUES_KEY, *ORDER_KEYS)

REROLLED_KEY = "chat_voice_rerolled"
TONE_SET_KEY = "chat_voice_tone_set"
IS_PINNED_KEY = "chat_voice_is_pinned"
NO_TONES_KEY = "chat_voice_no_tones"
NO_ROLE_KEY = "chat_voice_no_role"
ROLE_ROLLED_KEY = "chat_voice_role_rolled"
ROLE_LINE_KEY = "chat_voice_role_line"
ROLE_PINNED_LINE_KEY = "chat_voice_role_pinned_line"
ROLE_PLACEHOLDER_KEY = "chat_voice_role_placeholder"
ROLE_TITLE_KEY = "chat_voice_role_title"
ROLE_ONLY_BUTTON_KEY = "chat_voice_role_only_button"
ROLE_EVERYONE_BUTTON_KEY = "chat_voice_role_everyone_button"
REROLL_BUTTON_KEY = "chat_voice_reroll_button"
START_PLACEHOLDER_KEY = "chat_voice_start_placeholder"
LINE_STORED_KEY = "chat_voice_line_stored"
STATE_ROLLED_KEY = "chat_voice_state_rolled"
STATE_SET_KEY = "chat_voice_state_set"
STATE_DRIFTED_KEY = "chat_voice_state_drifted"
STATE_FEEDBACK_KEY = "chat_voice_state_feedback"
STATE_PINNED_KEY = "chat_voice_state_pinned"
STATE_TONE_OFF_KEY = "chat_voice_state_tone_off"
SETTLED_NEW_KEY = "chat_voice_settled_new"
SETTLED_SETTLING_KEY = "chat_voice_settled_settling"
SETTLED_SETTLED_KEY = "chat_voice_settled_settled"

TONE_WORDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    REROLLED_KEY: (
        "Rolled **{tone}** for **{member}**, from their next answer on.",
        ("member", "tone"),
        "what staff are told when a member's tone is rerolled, on /chat and on the Chat page. "
        "It takes {member} and {tone}",
    ),
    TONE_SET_KEY: (
        "**{member}** starts from **{tone}** from their next answer on.",
        ("member", "tone"),
        "what staff are told when a member is given a starting tone. It takes {member} and "
        "{tone}",
    ),
    IS_PINNED_KEY: (
        "**{member}** is pinned to **{tone}**, so nothing was changed. Clear the pin first.",
        ("member", "tone"),
        "what staff are told when they reroll or set a tone for a member who is pinned. It "
        "takes {member} and {tone}",
    ),
    NO_TONES_KEY: (
        "No tone is switched on in the pool, so nothing was rolled. Turn one on under "
        "Personality first.",
        (),
        "what staff are told when a tone is rolled while every tone is switched off",
    ),
    NO_ROLE_KEY: (
        "That role is not in this server, so nothing was rolled. Pick one from the list again.",
        (),
        "what staff are told when the role a tone was rolled for is not in the server",
    ),
    ROLE_ROLLED_KEY: (
        "Rolled a tone for **{rolled}** member(s) of **{role}**. Left alone: **{pinned}** "
        "pinned, **{kept}** who already had a tone.",
        ("rolled", "role", "pinned", "kept"),
        "the first line of the answer when a tone is rolled for everybody in a role. It takes "
        "{rolled}, {role}, {pinned} and {kept}, the three counts and the role's name",
    ),
    ROLE_LINE_KEY: (
        "{member} — **{tone}**",
        ("member", "tone"),
        "one member's line in that answer. It takes {member} and {tone}",
    ),
    ROLE_PINNED_LINE_KEY: (
        "{member} — pinned to **{tone}**, left alone",
        ("member", "tone"),
        "the line for a pinned member in that answer. It takes {member} and {tone}",
    ),
    ROLE_PLACEHOLDER_KEY: (
        "Roll for a role…",
        (),
        "the role picker's placeholder on the Who hears what card. Discord shows at most 150 "
        "characters",
    ),
    ROLE_TITLE_KEY: (
        "A tone for everybody in {role}",
        ("role",),
        "the heading of the card that rolls a tone for a role. It takes {role}",
    ),
    ROLE_ONLY_BUTTON_KEY: (
        "Only members with no tone",
        (),
        "the button that rolls a tone for the members of the role who have none yet. Discord "
        "shows at most 80 characters on a button",
    ),
    ROLE_EVERYONE_BUTTON_KEY: (
        "Everyone in it",
        (),
        "the button that rolls a new tone for every member of the role who is not pinned. "
        "Discord shows at most 80 characters on a button",
    ),
    REROLL_BUTTON_KEY: (
        "Reroll",
        (),
        "the button that rolls a member a new starting tone. Discord shows at most 80 "
        "characters on a button",
    ),
    START_PLACEHOLDER_KEY: (
        "Set tone… (a starting tone for {member})",
        ("member",),
        "the placeholder of the picker that gives a member a starting tone. It takes "
        "{member}; Discord shows at most 150 characters",
    ),
    LINE_STORED_KEY: (
        "{member} — **{tone}** · {state} · {settled}",
        ("member", "tone", "state", "settled"),
        "the line of a member who has a tone of their own on the Who hears what card. It takes "
        "{member}, {tone}, {state} (how the tone got there) and {settled} (how settled it is)",
    ),
    STATE_ROLLED_KEY: (
        "rolled",
        (),
        "how a tone got there, when Black Bloc or staff rolled it",
    ),
    STATE_SET_KEY: (
        "set by staff",
        (),
        "how a tone got there, when staff chose it as a starting tone",
    ),
    STATE_DRIFTED_KEY: (
        "drifted",
        (),
        "how a tone got there, when it took a step on its own",
    ),
    STATE_FEEDBACK_KEY: (
        "moved after feedback",
        (),
        "how a tone got there, when the member said Black Bloc was mean or wrong",
    ),
    STATE_PINNED_KEY: (
        "pinned",
        (),
        "how a tone got there, when staff pinned it",
    ),
    STATE_TONE_OFF_KEY: (
        "rolled · tone was switched off",
        (),
        "how a tone got there, when the member's own tone was switched off and Black Bloc "
        "rolled them another at their next answer",
    ),
    SETTLED_NEW_KEY: (
        "new",
        (),
        "how settled a tone is, while it is still likely to take a step",
    ),
    SETTLED_SETTLING_KEY: (
        "settling",
        (),
        "how settled a tone is, once it is less than half as likely to take a step",
    ),
    SETTLED_SETTLED_KEY: (
        "settled",
        (),
        "how settled a tone is, once it is as unlikely to take a step as it ever gets",
    ),
}
STATE_KEYS = {
    "rolled": STATE_ROLLED_KEY,
    "set": STATE_SET_KEY,
    "drifted": STATE_DRIFTED_KEY,
    "feedback": STATE_FEEDBACK_KEY,
    "pinned": STATE_PINNED_KEY,
    "tone_off": STATE_TONE_OFF_KEY,
}
SETTLED_KEYS = {
    "new": SETTLED_NEW_KEY,
    "settling": SETTLED_SETTLING_KEY,
    "settled": SETTLED_SETTLED_KEY,
}


def unknown_tone(given: Any) -> str | None:
    """The first name in an order that no tone carries, or None when every one is known."""
    for one in str(given or "").replace("\n", ",").split(","):
        name = one.strip().lower()
        if name and name not in KNOWN_TONES:
            return name
    return None
