import json
import re

from black_bloc import marathon_near_miss as mnm

USERS = {"cassasaur": 1, "peasplays": 2, "gz_hero": 3, "bobbeigh": 4}


def person(name, login=None, parts=("runner",), user_id=None):
    return {"name": name, "login": login, "parts": list(parts), "user_id": user_id}


def test_an_exact_login_matches_whatever_the_case():
    assert mnm.exact_match(person("Cass", "CassaSaur"), USERS) == ("cassasaur", 1)


def test_an_exact_schedule_name_matches():
    assert mnm.exact_match(person("Bobbeigh", "bobbeightv"), USERS) == ("bobbeigh", 4)


def test_fuzzy_near_misses_do_not_match():
    assert mnm.exact_match(person("Peas", "peasplay"), USERS) is None
    assert mnm.exact_match(person("gz"), USERS) is None
    assert mnm.exact_match(person("Cassa Saur", "cassa_saur"), USERS) is None


def test_a_member_is_never_a_near_miss():
    assert mnm.exact_match(person("cassasaur", "cassasaur", user_id=1), USERS) is None


def test_a_host_counts_only_when_hosts_match():
    host = person("cassasaur", "cassasaur", parts=("host",))
    assert mnm.exact_match(host, USERS, match_hosts=False) is None
    assert mnm.exact_match(host, USERS, match_hosts=True) == ("cassasaur", 1)


def row(kind, **details):
    return {"kind": kind, "details": json.dumps(details)}


def test_seen_keeps_posts_per_place_and_answers_per_runner():
    rows = [
        row(mnm.POSTED, runner_key="cassasaur", channel_id=10, message_id="5"),
        row(mnm.WOULD_POST, runner_key="gz", channel_id=11, message_id="6"),
        row(mnm.RESOLVED, runner_key="bob", outcome="not"),
        {"kind": mnm.POSTED, "details": "not json"},
    ]
    seen = mnm.seen_of(rows)
    assert seen.posted == {("cassasaur", 10), ("gz", 11)}
    assert seen.resolved == {"bob"}
    assert mnm.post_for(rows, 6)[1]["runner_key"] == "gz"
    assert mnm.post_for(rows, 7) is None
    assert mnm.answered(rows, "bob")["outcome"] == "not"
    assert mnm.answered(rows, "cassasaur") is None


def test_custom_ids_fit_the_template_and_labels_are_capped():
    for action in mnm.ACTIONS:
        assert re.fullmatch(mnm.TEMPLATE, mnm.custom_id(12, action))
    assert len(mnm.label("x" * 200)) == mnm.LABEL_LIMIT
    assert mnm.label("  ") == "…"
