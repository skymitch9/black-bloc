from black_bloc.brackets import picks, sports_shape
from black_bloc.brackets.model import BYE, COMPLETE, Bracket, Match, Options
from black_bloc.brackets.picks import HIT, MISS, Node, Rule, Tree

OPTS = Options(format="single", best_of=1, best_of_late=1, best_of_finals=1)


def four(**extra):
    """Two semi-finals into a final: 1 v 2 and 3 v 4."""
    sets = {
        "W1-1": Match("W1-1", "winners", 1, 1, 1, "ready", 1, 2, "W2-1", "a"),
        "W1-2": Match("W1-2", "winners", 1, 2, 1, "ready", 3, 4, "W2-1", "b"),
        "W2-1": Match("W2-1", "winners", 2, 1, 1, "waiting"),
    }
    for key, values in extra.items():
        for name, value in values.items():
            setattr(sets[key], name, value)
    return Bracket(OPTS, [1, 2, 3, 4], sets)


def done(match, winner, loser, a=None, b=None):
    match.state, match.winner, match.loser = COMPLETE, winner, loser
    match.score_a, match.score_b = a, b


def test_a_final_is_fed_by_the_members_own_semi_final_picks():
    tree = picks.tree_of(four())
    slots, winners = picks.predicted(tree, {"W1-1": 2, "W1-2": 3, "W2-1": 3})
    assert slots["W2-1"] == (2, 3)
    assert winners == {"W1-1": 2, "W1-2": 3, "W2-1": 3}


def test_changing_an_early_pick_clears_the_later_ones_that_hung_on_it():
    tree = picks.tree_of(four())
    sheet = {"W1-1": 1, "W1-2": 3, "W2-1": 1}
    assert picks.cleaned(tree, sheet) == sheet
    changed = {**sheet, "W1-1": 2}
    assert picks.cleaned(tree, changed) == {"W1-1": 2, "W1-2": 3}
    assert picks.wrong(tree, changed) == ["W2-1"]


def test_a_pick_on_a_team_not_in_the_set_or_a_set_not_in_the_tree_is_wrong():
    tree = picks.tree_of(four())
    assert picks.wrong(tree, {"W1-1": 3, "Z9-9": 1}) == ["W1-1", "Z9-9"]


def test_a_bye_and_a_decided_play_in_are_nobodys_pick():
    bracket = four()
    bracket.matches["W0-1"] = Match("W0-1", "winners", 0, 1, 1, "ready", 5, 4, "W1-2", "b")
    bracket.matches["W1-2"].slot_b = None
    tree = picks.tree_of(bracket)
    assert tree.nodes["W1-2"].b == Rule(sources=("W0-1",))
    assert picks.predicted(tree, {"W0-1": 5})[0]["W1-2"] == (3, 5)
    done(bracket.matches["W0-1"], 4, 5)
    bracket.matches["W1-2"].slot_b = 4
    tree = picks.tree_of(bracket)
    assert tree.nodes["W0-1"].fixed == 4
    assert picks.predicted(tree, {})[0]["W1-2"] == (3, 4)
    assert picks.cleaned(tree, {"W0-1": 4, "W1-2": 4}) == {"W1-2": 4}
    bracket.matches["W1-1"].state, bracket.matches["W1-1"].winner = BYE, 1
    assert picks.tree_of(bracket).nodes["W1-1"].fixed == 1


def test_a_pending_feeder_is_not_a_set_of_the_sheet():
    bracket = four(**{"W1-2": {"slot_b": None}})
    sports_shape.hold_open(bracket)
    assert "pending-W1-2-b" in bracket.matches
    tree = picks.tree_of(bracket)
    assert "pending-W1-2-b" not in tree.nodes
    assert tree.nodes["W1-2"].b == Rule(entrant=None)


def test_points_by_round_repeat_the_last_value_and_round_zero_scores_nothing():
    assert picks.points_table("1, 2,4") == (1, 2, 4)
    assert picks.points_table("1,x") is None
    assert picks.points_table("1,-2") is None
    assert picks.points_table("") is None
    assert [picks.round_points((1, 2, 4), r) for r in (0, 1, 2, 3, 5)] == [0, 1, 2, 4, 4]


def test_a_sheet_scores_hits_misses_and_what_is_still_reachable():
    bracket = four()
    done(bracket.matches["W1-1"], 1, 2)
    bracket.matches["W2-1"].slot_a = 1
    tree = picks.tree_of(bracket)
    sheet = {"W1-1": 1, "W1-2": 3, "W2-1": 3}
    found = picks.score(tree, sheet, bracket, (1, 2))
    assert (found.points, found.correct, found.played, found.possible) == (1, 1, 1, 3)
    assert found.marks == {"W1-1": HIT}
    done(bracket.matches["W1-2"], 4, 3)
    found = picks.score(tree, sheet, bracket, (1, 2))
    assert (found.points, found.correct, found.played, found.possible) == (1, 1, 3, 0)
    assert found.marks == {"W1-1": HIT, "W1-2": MISS, "W2-1": MISS}


def test_a_winner_scores_in_its_round_wherever_the_real_bracket_drew_it():
    tree = Tree(
        {
            "X1": Node("X1", 1, Rule(entrant=1), Rule(entrant=2)),
            "X2": Node("X2", 2, Rule(sources=("X1",)), Rule(entrant=9)),
        }
    )
    real = Bracket(
        OPTS,
        [1, 2, 9, 7],
        {
            "X1": Match("X1", "winners", 1, 1, 1, "complete", 1, 2, winner=1, loser=2),
            "X2": Match("X2", "winners", 2, 1, 1, "complete", 7, 1, winner=1, loser=7),
        },
    )
    found = picks.score(tree, {"X1": 1, "X2": 1}, real, (1, 2))
    assert (found.points, found.correct) == (3, 2)


def test_level_sheets_share_a_rank_unless_the_tiebreak_parts_them():
    scores = {
        5: picks.Score(points=4),
        6: picks.Score(points=4),
        7: picks.Score(points=9),
        8: picks.Score(points=1),
    }
    assert picks.ranked(scores, {}, None) == {7: 1, 5: 2, 6: 2, 8: 4}
    assert picks.ranked(scores, {5: 140, 6: 151}, 149) == {7: 1, 6: 2, 5: 3, 8: 4}
    assert picks.ranked(scores, {5: 140, 6: 151}, None) == {7: 1, 5: 2, 6: 2, 8: 4}


def test_the_finals_total_is_known_once_it_is_played():
    bracket = four()
    assert picks.final_total(bracket) is None
    done(bracket.matches["W2-1"], 1, 3, 70, 66)
    assert picks.final_total(bracket) == 136


def test_the_tree_goes_on_the_wire_as_rules():
    found = picks.tree_of(four(), {1: 1, 2: 2}).wire()
    assert found["sets"]["W2-1"] == {
        "round": 2,
        "a": {"from": ["W1-1"], "rank": 0},
        "b": {"from": ["W1-2"], "rank": 0},
        "fixed": None,
    }
    assert found["seeds"] == {"1": 1, "2": 2}
