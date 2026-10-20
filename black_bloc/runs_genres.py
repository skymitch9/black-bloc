from __future__ import annotations

import re
from typing import Any

Family = tuple[str, tuple[str, ...]]
Rule = tuple[tuple[str, ...], tuple[Family, ...]]

NOT_A_WORD = re.compile(r"[\W_]+")
QUALIFIER_SPLIT = re.compile(r"[,\n]")
NO_RULE: Rule = ((), ())


def normal(text: Any) -> str:
    return " ".join(NOT_A_WORD.sub(" ", str(text or "").lower()).split())


def parse_qualifiers(text: Any) -> tuple[str, ...]:
    found: list[str] = []
    for part in QUALIFIER_SPLIT.split(str(text or "")):
        word = normal(part)
        if word and word not in found:
            found.append(word)
    return tuple(sorted(found, key=lambda one: (-len(one.split()), -len(one))))


def family_lines(text: Any) -> tuple[tuple[Family, ...], tuple[tuple[int, str], ...]]:
    families: list[Family] = []
    bad: list[tuple[int, str]] = []
    for number, line in enumerate(str(text or "").splitlines(), start=1):
        if not line.strip():
            continue
        name, colon, rest = line.partition(":")
        key = normal(name)
        if not colon or not key:
            bad.append((number, line.strip()))
            continue
        aliases = tuple(dict.fromkeys(one for one in map(normal, rest.split(",")) if one))
        families.append((key, aliases))
    return tuple(families), tuple(bad)


def parse_families(text: Any) -> tuple[Family, ...]:
    return family_lines(text)[0]


def without_qualifiers(text: str, qualifiers: tuple[str, ...]) -> str:
    words = text.split()
    for qualifier in qualifiers:
        cut = qualifier.split()
        size = len(cut)
        at = 0
        kept: list[str] = []
        while at < len(words):
            if words[at : at + size] == cut:
                at += size
                continue
            kept.append(words[at])
            at += 1
        words = kept
    return " ".join(words)


def genre_family(text: Any, qualifiers: Any = (), families: Any = ()) -> str:
    full = normal(text)
    if not full:
        return ""
    stripped = without_qualifiers(full, tuple(qualifiers)) or full
    for candidate in (full, stripped):
        for name, aliases in families:
            if candidate == name or candidate in aliases:
                return name
    return stripped


def family_label(family: Any) -> str:
    text = str(family or "")
    return text[:1].upper() + text[1:]


def family_terms(family: Any, families: Any = ()) -> str:
    for name, aliases in families:
        if name == family:
            return " ".join((name, *aliases))
    return str(family or "")
