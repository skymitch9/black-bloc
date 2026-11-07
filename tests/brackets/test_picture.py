from __future__ import annotations

from io import BytesIO

from PIL import Image

from black_bloc.brackets import play, pools, sports_shape
from black_bloc.brackets.model import DOUBLE, ROUND_ROBIN, SINGLE, SWISS, Options, Plan
from black_bloc.brackets.picture import (
    BG,
    MARGIN,
    Extra,
    Words,
    draw,
    elimination_layout,
    fingerprint,
    fitted,
    font,
    scene,
    title_band,
    tree_size,
)

WORDS = Words(title="Knuck Up 12", format="Single elimination", state="Running", kind="List")


def built(count, format_=SINGLE, **options):
    return play.build(list(range(1, count + 1)), Options(format=format_, **options)).bracket


def names(count):
    return {one: f"Player {one}" for one in range(1, count + 1)}


def decided(bracket, key, a=2, b=0):
    return play.override(bracket, key, None, None, score_a=a, score_b=b, free=True).bracket


def opened(data):
    return Image.open(BytesIO(data)).convert("RGB")


def lit(image, box):
    return sum(sum(one) for one in image.crop(box).getdata()) - sum(BG) * (
        (box[2] - box[0]) * (box[3] - box[1])
    )


def brightness(image, box):
    crop = image.crop(box)
    pixels = list(crop.getdata())
    return max(sum(one) for one in pixels)


def test_a_picture_is_a_png_of_fixed_width_for_eight_or_more():
    image = opened(draw(built(8), names(8), words=WORDS))
    assert image.size[0] == 1600
    assert image.size[1] > 400


def test_a_tiny_bracket_is_narrower():
    image = opened(draw(built(4), names(4), words=WORDS))
    assert image.size[0] < 1600


def test_the_same_input_draws_the_same_bytes():
    bracket = decided(built(8), "W1-1")
    assert draw(bracket, names(8), words=WORDS) == draw(bracket, names(8), words=WORDS)


def test_the_title_band_is_not_background_only():
    image = opened(draw(built(8), names(8), words=WORDS))
    assert brightness(image, (32, 32, 600, 80)) > sum(BG) + 200


def test_the_winner_slot_is_brighter_than_the_loser_slot():
    bracket = decided(built(8), "W1-1")
    made = scene(bracket, names(8), WORDS)
    width, size = tree_size(made.layout.cols, made.count)
    _, band = title_band(made, width)
    node = next(one for one in made.layout.nodes if one.key == "W1-1")
    used = made.layout.cols * size.col + (made.layout.cols - 1) * size.gap
    left = max(MARGIN, (width - used) // 2) + node.col * (size.col + size.gap) + size.pad
    top = band + size.head + 14 + round(node.y * size.unit) - size.box // 2 + size.pad
    winner_top = top + round(size.small * 1.15)
    loser_top = winner_top + round(size.name * 1.15)
    image = opened(draw(bracket, names(8), words=WORDS))
    room = size.col // 2
    winner = lit(image, (left, winner_top, left + room, winner_top + size.name))
    loser = lit(image, (left, loser_top, left + room, loser_top + size.name))
    assert winner > loser > 0


def test_byes_and_void_sets_are_not_drawn_like_the_page():
    bracket = built(6)
    made = scene(bracket, names(6), WORDS)
    drawn = {one.key for one in made.boxes}
    byes = {key for key, one in bracket.matches.items() if one.state == "bye"}
    assert byes and not byes & drawn


def test_pending_feeders_are_not_drawn():
    planned = [
        sports_shape.Planned("a", 1, 1, None),
        sports_shape.Planned("b", 1, 3, 4),
        sports_shape.Planned("f", 2, None, None),
    ]
    bracket, _ = sports_shape.shaped(planned, {"a": ("f", "a"), "b": ("f", "b")})
    assert any(sports_shape.is_pending(key) for key in bracket.matches)
    made = scene(bracket, names(4), WORDS)
    assert not any(sports_shape.is_pending(one.key) for one in made.boxes)


def test_a_play_in_round_takes_the_first_column():
    planned = [sports_shape.Planned("p", 0, 5, 6)]
    planned += [sports_shape.Planned(f"r{at}", 1, at * 2 + 1, at * 2 + 2) for at in range(2)]
    planned[1] = sports_shape.Planned("r0", 1, 1, None)
    planned.append(sports_shape.Planned("f", 2, None, None))
    links = {"p": ("r0", "b"), "r0": ("f", "a"), "r1": ("f", "b")}
    bracket, keys = sports_shape.shaped(planned, links)
    layout = elimination_layout(list(bracket.matches.values()))
    cols = {one.key: one.col for one in layout.nodes}
    play_in = next(key for key, match in bracket.matches.items() if match.round == 0
                   and not sports_shape.is_pending(key))
    assert cols[play_in] == 0
    assert min(col for key, col in cols.items() if bracket.matches[key].round == 1) == 1


def test_double_elimination_stacks_losers_under_winners_and_the_grand_final_last():
    bracket = built(8, DOUBLE)
    layout = scene(bracket, names(8), WORDS).layout
    sides = {one.side: [] for one in layout.nodes}
    for one in layout.nodes:
        sides[one.side].append(one)
    assert min(one.y for one in sides["losers"]) > max(one.y for one in sides["winners"])
    assert min(one.col for one in sides["grand"]) == layout.cols - 2


def test_round_robin_and_swiss_draw_a_table():
    for format_ in (ROUND_ROBIN, SWISS):
        bracket = built(6, format_)
        made = scene(bracket, names(6), WORDS)
        assert made.layout is None
        assert len(made.tables[0][1]) == 6
        assert opened(draw(bracket, names(6), words=WORDS)).size[0] == 1000


def test_the_pools_phase_draws_a_table_per_pool():
    plan = Plan(format=ROUND_ROBIN, count=2, advance=1)
    bracket = pools.build(list(range(1, 9)), Options(format=SINGLE), plan).bracket
    words = Words(title="T", pools={1: "Pool A", 2: "Pool B"})
    made = scene(bracket, names(8), words)
    assert [heading for heading, _ in made.tables] == ["Pool A", "Pool B"]


def test_votes_stand_in_for_the_score_while_open():
    bracket = built(8)
    made = scene(bracket, names(8), WORDS, {"W1-1": Extra(votes=(7, 5))})
    box = next(one for one in made.boxes if one.key == "W1-1")
    assert (box.a.score, box.b.score) == ("7", "5")


def test_a_sports_line_and_a_held_tag_ride_on_the_box():
    bracket = built(8)
    made = scene(bracket, names(8), WORDS, {"W1-2": Extra(line="Final 3–1", held=True)})
    box = next(one for one in made.boxes if one.key == "W1-2")
    assert box.top == "W1-2 · Final 3–1" and box.held


def test_a_forfeit_reads_w_and_ff():
    bracket = play.override(built(8), "W1-1", None, None, winner="a", forfeit=True).bracket
    box = next(one for one in scene(bracket, names(8), WORDS).boxes if one.key == "W1-1")
    assert (box.a.score, box.b.score) == ("W", "FF")


def test_a_long_name_is_ellipsised_to_the_room():
    face = font(24)
    text = fitted("A very long candy bar name that never ends", face, 120)
    assert text.endswith("…") and face.getlength(text) <= 120


def test_the_fingerprint_moves_with_a_result_and_not_without_one():
    bracket = built(8)
    before = fingerprint(scene(bracket, names(8), WORDS))
    assert before == fingerprint(scene(bracket, names(8), WORDS))
    assert before != fingerprint(scene(decided(bracket, "W1-1"), names(8), WORDS))


def test_sixty_four_entrants_stay_legible():
    made = scene(built(64), names(64), WORDS)
    _, size = tree_size(made.layout.cols, made.count)
    assert size.name >= 18
    assert opened(draw(built(64), names(64), words=WORDS)).size[0] == 1600


def test_the_champion_line_is_drawn_under_the_title():
    plain = opened(draw(built(4), names(4), words=WORDS))
    crowned = Words(title="Knuck Up 12", champion="Champion: Player 1")
    assert opened(draw(built(4), names(4), words=crowned)).size[1] > plain.size[1]
