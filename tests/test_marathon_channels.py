from black_bloc import marathon_channels as mc


def test_a_row_the_migration_has_not_reached_takes_marathons():
    assert mc.takes_marathons({"twitch_login": "gdq"})
    assert not mc.takes_marathons({"marathons": 0})
    assert mc.takes_marathons({"marathons": 1})


def test_esa_is_the_one_seeded_opt_out_and_its_marker_is_its_own():
    assert mc.OPTED_OUT_SEEDS == ("esamarathon",)
    assert mc.seed_key("ESAMarathon") == "optout:esamarathon"


def test_the_panel_line_says_on_or_off():
    assert mc.panel_line({"marathons": 1}) == "Marathons: **on**"
    assert mc.panel_line({"marathons": 0}).startswith("Marathons: **off")


class FakeCursor:
    def __init__(self, hit):
        self.hit = hit

    async def fetchone(self):
        return (1,) if self.hit else None


class FakeConn:
    def __init__(self, hits):
        self.hits = hits
        self.asked = []

    async def execute(self, sql, params):
        self.asked.append((sql, params))
        return FakeCursor(any(table in sql for table in self.hits))


class FakeDb:
    def __init__(self, *hits):
        self.conn = FakeConn(hits)


async def test_a_row_that_carries_nothing_marathon_shaped_is_held_by_nothing():
    db = FakeDb()
    assert await mc.carries_marathons(db, 7) == ()
    assert {params for _, params in db.conn.asked} == {(7,)}


async def test_each_signal_that_holds_a_row_is_named_in_order():
    assert await mc.carries_marathons(FakeDb("marathon_feeds"), 7) == (mc.HELD_BY_FEED,)
    assert await mc.carries_marathons(FakeDb("FROM marathons "), 7) == (mc.HELD_BY_MARATHON,)
    assert await mc.carries_marathons(FakeDb("spotlit_by_marathon"), 7) == (mc.HELD_BY_SPOTLIGHT,)
    assert await mc.carries_marathons(
        FakeDb("marathon_feeds", "FROM marathons ", "spotlit_by_marathon"), "7"
    ) == (mc.HELD_BY_FEED, mc.HELD_BY_MARATHON, mc.HELD_BY_SPOTLIGHT)
