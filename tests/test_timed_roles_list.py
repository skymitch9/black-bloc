from types import SimpleNamespace

from black_bloc import timed_roles_list as tl


def person(user_id, name, display=None, global_name=None):
    return SimpleNamespace(
        id=user_id, name=name, display_name=display or name, global_name=global_name
    )


ADA = person(123456789012345678, "ada", "Ada L")
BO = person(223456789012345678, "bo", "Sam")
SAM = person(323456789012345678, "sam")
CASS = person(423456789012345678, "cassasaur", "Cass", "Cass")
EVERYONE = [ADA, BO, SAM, CASS]


def test_lines_are_trimmed_blanks_dropped_and_repeats_kept_once():
    assert tl.lines_of("  ada \n\n<@123>\r\nada\n") == ["ada", "<@123>"]
    assert tl.lines_of(None) == []


def test_ids_mentions_and_names_match_exactly_whatever_the_case():
    typed = [str(ADA.id), f"<@!{BO.id}>", "CASS", "@sam", "Ada L"]

    matched, unmatched = tl.match(EVERYONE, typed)

    assert [(one.typed, one.member.id) for one in matched] == [
        (str(ADA.id), ADA.id),
        (f"<@!{BO.id}>", BO.id),
        ("CASS", CASS.id),
    ]
    assert [(one.typed, one.why) for one in unmatched] == [("@sam", tl.AMBIGUOUS)]


def test_a_name_two_members_share_names_nobody_and_a_stranger_is_unknown():
    matched, unmatched = tl.match(EVERYONE, ["sam", "nobody", "123", "<@999999999999999999>"])

    assert matched == []
    assert [(one.typed, one.why) for one in unmatched] == [
        ("sam", tl.AMBIGUOUS),
        ("nobody", tl.UNKNOWN),
        ("123", tl.UNKNOWN),
        ("<@999999999999999999>", tl.UNKNOWN),
    ]


def test_one_member_named_twice_is_matched_once_and_part_of_a_name_is_not_a_match():
    matched, unmatched = tl.match(EVERYONE, ["ada", str(ADA.id), "cass"])

    assert [one.member.id for one in matched] == [ADA.id, CASS.id]
    assert tl.match(EVERYONE, ["cassa"]) == ([], [tl.Unmatched("cassa", tl.UNKNOWN)])
    assert unmatched == []
