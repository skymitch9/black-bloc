from black_bloc.sports import espn, nfl
from black_bloc.sports.model import FINAL, SCHEDULED
from tests.sports_fakes import Recorded, payload

DEN, NE, JAX, PIT, HOU, BUF, LAC = "7", "17", "30", "23", "34", "2", "24"
SEA, NFC_CHAMPION = "26", "26"


def seeds():
    return espn.parse_seeds(payload("espn_standings_nfl"))[0]


def results():
    teams = {one for conference in seeds().values() for one in conference[:7]}
    return nfl.postseason(payload("espn_scoreboard_nfl_post")["events"], teams)


def test_the_pro_bowl_is_not_a_playoff_game():
    assert len(results()) == 13


def test_the_wild_card_round_is_two_v_seven_three_v_six_four_v_five():
    built = nfl.build(seeds(), [], "2025")
    pairs = [(one.a_ext_id, one.b_ext_id) for one in built.games if "WC" in one.source_key]
    assert pairs[:3] == [(NE, LAC), (JAX, BUF), (PIT, HOU)]
    first = built.game("AFC-DIV-1")
    assert (first.a_ext_id, first.b_ext_id, first.status) == (DEN, None, SCHEDULED)
    assert all("WC" not in key for key in built.links)


def test_after_the_wild_card_round_the_one_seed_hosts_the_lowest_left():
    built = nfl.build(seeds(), results()[:6], "2025")
    first, second = built.game("AFC-DIV-1"), built.game("AFC-DIV-2")
    assert (first.a_ext_id, first.b_ext_id) == (DEN, BUF)
    assert (second.a_ext_id, second.b_ext_id) == (NE, HOU)
    assert built.links["AFC-WC-2"] == ("AFC-DIV-1", "b")
    assert built.links["AFC-WC-1"] == ("AFC-DIV-2", "a")
    assert built.links["AFC-WC-3"] == ("AFC-DIV-2", "b")
    assert "AFC-DIV-1" not in built.links


def test_the_whole_2025_postseason_ends_with_seattle_winning_the_super_bowl():
    built = nfl.build(seeds(), results(), "2025")
    final = built.game("SB")
    assert (final.a_ext_id, final.b_ext_id, final.status) == (NE, SEA, FINAL)
    assert nfl.winner_of(final) == NFC_CHAMPION
    assert built.game("AFC-CONF").a_ext_id == DEN
    assert built.links["AFC-CONF"] == ("SB", "a")
    assert built.seeds[HOU] == 5
    for source, (target, slot) in built.links.items():
        after = built.game(target)
        assert (after.a_ext_id if slot == "a" else after.b_ext_id) == nfl.winner_of(
            built.game(source)
        ), source


async def test_the_bracket_reads_the_standings_and_each_playoff_week():
    every = payload("espn_scoreboard_nfl_post")
    fetch = Recorded({"standings?season=2025": "espn_standings_nfl", "seasontype=3": every})
    answer = await nfl.bracket("2025", fetch=fetch)
    assert (answer.ok, answer.via, answer.value.season) == (True, "espn", "2025")
    assert answer.value.names[SEA] == "Seattle Seahawks"
    assert len([url for url in fetch.urls() if "week=" in url]) == 5


async def test_no_seeds_yet_is_worded():
    fetch = Recorded({"standings": {"children": []}})
    answer = await nfl.bracket("2026", fetch=fetch)
    assert answer.why == "ESPN sent no 2026 NFL playoff seeds"


def played_out(seeds_by_conf, choose):
    """The bracket nfl.build makes when each game's winner is the side `choose` names."""
    from black_bloc.sports.model import Game

    games = []
    while True:
        built = nfl.build(seeds_by_conf, games, "2025")
        fresh = [
            one for one in built.games if one.a_ext_id and one.b_ext_id and one.status != FINAL
        ]
        if not fresh:
            return built
        for one in fresh:
            a_wins = choose(one.source_key) == "a"
            games.append(
                Game(
                    f"x{len(games)}",
                    one.source_key,
                    one.a_ext_id,
                    one.b_ext_id,
                    1 if a_wins else 0,
                    0 if a_wins else 1,
                    FINAL,
                    None,
                    None,
                    one.round,
                )
            )


def test_the_reseed_rules_pair_every_round_as_the_builder_does():
    from black_bloc.brackets.picks import Node, Rule, Tree, predicted

    conferences = {conf: [f"{conf}{at}" for at in range(1, 8)] for conf in nfl.CONFERENCES}
    ids = {ext: at for at, ext in enumerate(sum(conferences.values(), []), start=1)}
    seeds_of = {ids[ext]: int(ext[3:]) for ext in ids}
    blank = nfl.build(conferences, [], "2025")
    rules = nfl.reseed_rules()
    afc = [one.source_key for one in blank.games if one.source_key.startswith("AFC")]
    nodes = {}
    for one in blank.games:
        held = rules.get(one.source_key, {})
        slots = {}
        for slot, ext in (("a", one.a_ext_id), ("b", one.b_ext_id)):
            if slot in held:
                slots[slot] = Rule(sources=held[slot][0], rank=held[slot][1])
            else:
                slots[slot] = Rule(entrant=ids.get(ext) if ext else None)
        nodes[one.source_key] = Node(one.source_key, one.round, slots["a"], slots["b"])
    tree = Tree(nodes, seeds_of)
    checked = 0
    for bits in range(2 ** len(afc)):
        for final in ("a", "b"):

            def choose(key, bits=bits, final=final):
                if key in afc:
                    return "a" if (bits >> afc.index(key)) & 1 == 0 else "b"
                return final if key == nfl.SUPER_BOWL else "a"

            built = played_out(conferences, choose)
            sheet = {
                one.source_key: ids[nfl.winner_of(one)]
                for one in built.games
                if nfl.winner_of(one)
            }
            slots, _ = predicted(tree, sheet)
            for one in built.games:
                wanted = (ids[one.a_ext_id], ids[one.b_ext_id])
                assert slots[one.source_key] == wanted, (bits, final, one.source_key)
            checked += 1
    assert checked == 2 ** len(afc) * 2
