from __future__ import annotations

import re
import unicodedata
from typing import Any

RULE_SENSITIVE = "sensitive"
RULE_PERSONAL = "personal"
RULE_INSTRUCTION = "instruction"
RULE_LINK = "link"
RULE_CHARSET = "charset"

HEALTH = "health"
SEXUALITY_GENDER = "sexuality_gender"
AGE = "age"
LOCATION = "location"
IMMIGRATION = "immigration"
CRIMINAL = "criminal"
MONEY = "money"
RELIGION = "religion"
POLITICS = "politics"
LIFE = "life"

CATEGORIES: dict[str, tuple[str, ...]] = {
    HEALTH: (
        "depressed",
        "depression",
        "anxiety",
        "anxious",
        "adhd",
        "autistic",
        "autism",
        "bipolar",
        "ptsd",
        "ocd",
        "therapy",
        "therapist",
        "medication",
        "medicated",
        "meds",
        "diagnosed",
        "diagnosis",
        "disabled",
        "disability",
        "illness",
        "sick",
        "cancer",
        "chronic",
        "surgery",
        "hospital",
        "pregnant",
        "pregnancy",
        "self harm",
        "selfharm",
        "suicidal",
        "suicide",
        "trauma",
        "addiction",
        "addicted",
        "rehab",
        "sober",
        "drunk",
        "drugs",
        "their weight",
        "weight loss",
        "lose weight",
        "their body",
        "body image",
        "mental health",
    ),
    SEXUALITY_GENDER: (
        "gay",
        "lesbian",
        "bisexual",
        "pansexual",
        "asexual",
        "queer",
        "lgbt",
        "lgbtq",
        "closeted",
        "coming out",
        "sexuality",
        "gender",
        "trans",
        "transgender",
        "nonbinary",
        "non binary",
    ),
    AGE: (
        "years old",
        "year old",
        "age",
        "aged",
        "born in",
        "birthday",
        "minor",
        "underage",
        "teenager",
        "teenage",
        "is a teen",
        "a teen who",
        "is a kid",
        "just a kid",
        "high school",
        "middle school",
        "grade school",
        "in grade",
        "grader",
        "freshman",
        "sophomore",
    ),
    LOCATION: (
        "country",
        "city",
        "hometown",
        "home town",
        "neighborhood",
        "neighbourhood",
        "zip code",
        "postcode",
        "their address",
        "home address",
        "street address",
        "ip address",
        "email address",
        "is from",
        "are from",
        "comes from",
        "originally from",
        "moved to",
    ),
    IMMIGRATION: (
        "visa",
        "deported",
        "deportation",
        "undocumented",
        "immigrant",
        "immigration",
        "asylum",
        "refugee",
        "green card",
        "citizenship",
        "nationality",
        "ethnicity",
        "ethnic",
        "racial",
        "their race",
    ),
    CRIMINAL: (
        "arrested",
        "arrest",
        "prison",
        "jail",
        "probation",
        "parole",
        "convicted",
        "felony",
        "criminal record",
        "the police",
        "police record",
        "court date",
        "charged with",
    ),
    MONEY: (
        "is broke",
        "are broke",
        "being broke",
        "so broke",
        "too broke",
        "flat broke",
        "poor",
        "rich",
        "salary",
        "wage",
        "income",
        "rent",
        "mortgage",
        "loan",
        "unemployed",
        "money",
        "paycheck",
        "bills",
        "debt",
        "bankrupt",
        "welfare",
    ),
    RELIGION: (
        "christian",
        "muslim",
        "jewish",
        "hindu",
        "buddhist",
        "atheist",
        "religion",
        "religious",
        "church",
        "mosque",
        "synagogue",
        "faith",
        "believes",
        "belief",
        "beliefs",
    ),
    POLITICS: (
        "republican",
        "democrat",
        "conservative",
        "liberal",
        "politics",
        "political",
        "voted",
    ),
    LIFE: (
        "girlfriend",
        "boyfriend",
        "wife",
        "husband",
        "spouse",
        "their partner",
        "married",
        "divorced",
        "dating",
        "relationship",
        "relationships",
        "their family",
        "their mom",
        "their mum",
        "their mother",
        "their dad",
        "their father",
        "their parents",
        "their kids",
        "has kids",
        "their children",
        "their son",
        "their daughter",
        "their brother",
        "their sister",
        "their job",
        "new job",
        "day job",
        "job as",
        "career",
        "their boss",
        "in school",
        "at school",
        "their school",
        "goes to school",
        "college",
        "university",
        "lonely",
    ),
}
PERSONAL_CATEGORIES: frozenset[str] = frozenset({LIFE})
RAPPORT_ONLY: tuple[str, ...] = ("pronouns",)

INSTRUCTIONS: tuple[str, ...] = (
    "you",
    "your",
    "yours",
    "yourself",
    "ignore",
    "ignores",
    "ignoring",
    "disregard",
    "override",
    "overrides",
    "bypass",
    "jailbreak",
    "pretend",
    "obey",
    "comply",
    "must",
    "prompt",
    "prompts",
    "system message",
    "instruction",
    "instructions",
    "act as",
    "developer mode",
    "debug mode",
    "admin mode",
    "unrestricted mode",
    "grant",
    "grants",
    "granted",
    "permission",
    "permissions",
    "allowed to",
    "authorised",
    "authorized",
    "password",
    "token",
    "api key",
    "secret",
    "secrets",
    "reveal",
    "admin",
    "administrator",
    "moderator",
    "staff",
    "owner",
    "unban",
    "from now on",
    "from this point",
    "always say",
    "always says",
    "always said",
    "always reply",
    "always replies",
    "always respond",
    "always responds",
    "always answer",
    "always answers",
    "always agree",
    "always agrees",
    "never refuse",
    "never refuses",
    "never say no",
    "never says no",
    "say yes",
    "says yes",
    "said yes",
    "reply with",
    "replies with",
    "respond with",
    "responds with",
    "role request",
    "role requests",
    "any role",
    "every role",
    "give the role",
    "gives the role",
    "no rules",
)
INSTRUCTIONS_OUTSIDE_A_TOPIC: tuple[str, ...] = ("rule", "rules")

LINKS: tuple[str, ...] = ("http", "www.", "://", "discord.gg", ".com/", ".gg/")
LINK_WORDS: tuple[str, ...] = ("http", "https", "www", "discord gg", "dot com")

RAPPORT_OTHERS: tuple[str, ...] = (
    "friend",
    "friends",
    "another member",
    "other members",
    "other people",
    "others",
    "someone",
    "somebody",
    "everybody",
    "people",
    "members",
    "he",
    "she",
    "him",
    "his",
    "hers",
)

TYPOGRAPHY = str.maketrans(
    {
        "—": "-",
        "–": "-",
        "‐": "-",
        "‑": "-",
        "−": "-",
        "’": "'",
        "‘": "'",
        "…": "...",
    }
)
INVISIBLE = ("Cc", "Cf", "Co", "Cs", "Cn")
PLAIN = re.compile(r"^[A-Za-z0-9 .,;:!?'()\-/&+#%*=_~À-ÖØ-öø-ɏ]*$")

LOOKALIKES = str.maketrans(
    {
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "х": "x",
        "у": "y",
        "і": "i",
        "ѕ": "s",
        "ј": "j",
        "ԁ": "d",
        "һ": "h",
        "ո": "n",
        "ս": "u",
        "ο": "o",
        "α": "a",
        "ε": "e",
        "ι": "i",
        "ν": "v",
        "ρ": "p",
        "τ": "t",
        "υ": "u",
    }
)
LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "$": "s", "!": "i"}
)
NOT_A_WORD = re.compile(r"[^0-9a-z ]+")


def clean(text: Any) -> str:
    """What is judged and what is stored: composed, visible, one line, plain punctuation."""
    said = unicodedata.normalize("NFKC", str(text or "")).translate(TYPOGRAPHY)
    kept = [
        " " if mark.isspace() else mark
        for mark in said
        if mark.isspace() or unicodedata.category(mark) not in INVISIBLE
    ]
    return " ".join("".join(kept).split())


def is_plain(text: Any) -> bool:
    """Latin letters with or without an accent, digits, spaces and everyday punctuation."""
    return PLAIN.match(str(text or "")) is not None


def unaccented(text: str) -> str:
    split = unicodedata.normalize("NFKD", text)
    return "".join(mark for mark in split if unicodedata.category(mark) != "Mn")


def forms(text: Any) -> tuple[str, ...]:
    """Every way the words might be read: as typed, with leet undone, and with marks closed up."""
    low = unaccented(str(text or "").lower().translate(LOOKALIKES)).replace("'", "")
    found: list[str] = []
    for one in (low, low.translate(LEET)):
        for gap in (" ", ""):
            found.append(" ".join(NOT_A_WORD.sub(gap, one).split()))
    return tuple(dict.fromkeys(found))


def says(read: Any, phrases: Any) -> bool:
    return any(f" {phrase} " in f" {one} " for one in read or () for phrase in phrases or ())


def category_of(read: Any, *, rapport: bool = False) -> str | None:
    """The private category a line touches, by name, or None."""
    for name, phrases in CATEGORIES.items():
        if says(read, phrases):
            return name
    if rapport and says(read, RAPPORT_ONLY):
        return SEXUALITY_GENDER
    return None


def private_rule(read: Any, *, rapport: bool = False) -> str | None:
    found = category_of(read, rapport=rapport)
    if found is None:
        return None
    return RULE_PERSONAL if found in PERSONAL_CATEGORIES else RULE_SENSITIVE


def is_an_instruction(read: Any, *, thread: bool = False) -> bool:
    if says(read, INSTRUCTIONS):
        return True
    return not thread and says(read, INSTRUCTIONS_OUTSIDE_A_TOPIC)


def is_a_link(text: Any, read: Any) -> bool:
    low = str(text or "").lower()
    return any(mark in low for mark in LINKS) or says(read, LINK_WORDS)


__all__ = [
    "CATEGORIES",
    "INSTRUCTIONS",
    "INSTRUCTIONS_OUTSIDE_A_TOPIC",
    "PERSONAL_CATEGORIES",
    "RAPPORT_ONLY",
    "RAPPORT_OTHERS",
    "RULE_CHARSET",
    "RULE_INSTRUCTION",
    "RULE_LINK",
    "RULE_PERSONAL",
    "RULE_SENSITIVE",
    "category_of",
    "clean",
    "forms",
    "is_a_link",
    "is_an_instruction",
    "is_plain",
    "private_rule",
    "says",
]
