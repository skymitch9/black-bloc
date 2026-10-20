from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from .runs_genres import normal

LETTERS_THEN_DIGITS = re.compile(r"([^\W\d_]+)(\d*)")
FUZZY_LETTERS = 5
INITIALS_LETTERS = 2

Line = tuple[tuple[str, ...], str]


def words_of(text: Any) -> tuple[str, ...]:
    return tuple(normal(text).split())


@lru_cache(maxsize=8192)
def prepared(haystack: str) -> tuple[Line, ...]:
    lines: list[Line] = []
    for line in haystack.splitlines():
        words = words_of(line)
        if words:
            lines.append((words, "".join(word[0] for word in words)))
    return tuple(lines)


def one_edit(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [at for at in range(len(a)) if a[at] != b[at]]
        if len(diff) == 1:
            return True
        return (
            len(diff) == 2
            and diff[1] == diff[0] + 1
            and a[diff[0]] == b[diff[1]]
            and a[diff[1]] == b[diff[0]]
        )
    short, long = (a, b) if len(a) < len(b) else (b, a)
    at = 0
    while at < len(short) and short[at] == long[at]:
        at += 1
    return short[at:] == long[at + 1 :]


def initials_hit(word: str, words: tuple[str, ...], initials: str) -> bool:
    found = LETTERS_THEN_DIGITS.fullmatch(word)
    if not found or len(found[1]) < INITIALS_LETTERS:
        return False
    letters, digits = found[1], found[2]
    start = initials.find(letters)
    while start >= 0:
        after = start + len(letters)
        if not digits or (after < len(words) and words[after] == digits):
            return True
        start = initials.find(letters, start + 1)
    return False


def hits(word: str, lines: tuple[Line, ...]) -> bool:
    if word.isdigit():
        return any(word in words for words, _ in lines)
    fuzzy = sum(char.isalpha() for char in word) >= FUZZY_LETTERS
    for words, initials in lines:
        for one in words:
            if one.startswith(word) or (fuzzy and one_edit(word, one)):
                return True
        if initials_hit(word, words, initials):
            return True
    return False


def matches(query: Any, haystack: Any) -> bool:
    """Every query word hits the haystack, in any order; an empty query matches nothing."""
    wanted = words_of(query)
    if not wanted:
        return False
    lines = prepared(str(haystack or ""))
    return all(hits(word, lines) for word in wanted)
