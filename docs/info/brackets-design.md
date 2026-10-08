# Tournament brackets — the engine, the storage and the API (layer 1), the Discord side (layer 2), and what layer 3 builds

> **Audience:** the conductor, reviewers, and the agents that build layer 3 from this page alone.
> **Status:** TRACKED · ✅ **LAYER 1 MERGED** on `main` (`b78e91cc`, fixed `aba3b1ee`), NOT deployed; schema **89 → 90**;
> registry keys **946 → 1000**. 🔨 **LAYER 2 BUILT on branch `brackets-discord`** (off `main` `aba3b1ee`), **NOT merged,
> NOT deployed**; no schema change; registry keys **1000 → ~~1064~~ 1065** (the layer-2 review fixes added
> `brackets_moved_line`); §E is now *as built*, its decisions are §G 27–55; the layer-2 review's findings and their pins
> are under *Review fixes (layer 2) 2026-10-07*.
> 🔨 **LAYER 3 BUILT on branch `brackets-site`** (off `main` `7850359b`), **NOT merged, NOT deployed**; no schema change; registry
> keys **1065 → 1075**; contract routes **344 → 345**, pages 25 → 26; §F is now *as built*, decisions §G 56–72.
> **Last verified: 2026-10-07** (layer 3 build; layer 2 before it) — by the hermetic test suite, `ruff`, `site/mock/check.mjs` against the
> branch's own mock on port 8813, every `site/mock/*.test.mjs` and the Docker CI mirror (figures under *Gate*).
> ⚠️ **NOT checked:** nothing here has met the REAL Discord — layer 2 is tested against fakes of threads, messages and
> interactions only; no browser has rendered anything (there is no page); the schema change has not run on the live
> database. Secret NAMES only (none here).

## The ask and the owner's decisions (verbatim, 2026-10-07)

- The ask: *"can we also get a feature that makes fighting game tournament brackets? get all the popular configs like
  double elim, double elim double elim finals single elim etc"*.
- **Q1** *"c. but start with a and yes on the finals reset, make it optional tho. check start.gg and steal all their
  basic tourney options"* → Black Bloc's own engine first; a start.gg mirror later. The grand-final reset is a
  per-tournament option. The data leaves room for a mirror: `tournaments.source` (`own` | `startgg`) and
  `source_ref`, like a marathon's source — nothing reads `startgg` yet.
- **Q2** *"b"* → staff **plus** holders of a Tournament Organiser role (`brackets_to_role_id`, blank until picked)
  create and run tournaments; staff keep the final say over every bracket. Players sign themselves up.
- **Q3** *"a, they'll always be threads of knuck up while not in shadow mode, during shadow we use black bloc
  logs"* → one thread per tournament under `#knuck-up` (`1076005097617760296`, a TEXT channel,
  `brackets_channel_id`); in shadow the thread goes to the shadow home. Layer 1 stores the ids only.
- **Q4** *"b"* → entrants are members who sign up themselves AND names a TO adds by hand, guests included (no user
  id; the TO reports for them).
- **Q5** *"a"* → either player reports, the opponent confirms; a report stands after `brackets_confirm_minutes`
  (12, start.gg's verify timer); Dispute flags it for the TO; the TO and staff report, correct or reset any set at
  any time.
- **Q6** *"b, start this in shadow mode. we dont have an urgent need for this either"* → single elimination
  (optional third-place set), double elimination (optional grand-final reset, **default on**), round robin, Swiss.
  `brackets_mode` off | shadow | on, default **shadow**.

Research input: [`brackets-research-2026-10-07.md`](brackets-research-2026-10-07.md) (start.gg's basic options).

## The layer plan

| Layer | What | State |
|---|---|---|
| **L1** | Pure engine `black_bloc/brackets/`, storage (schema 90), the moves both doors call, the API `/api/brackets`, settings keys, log kinds, contract + mock | ✅ merged (`b78e91cc`, `aba3b1ee`) |
| **L2** | Discord: the tournament thread under `#knuck-up` (or the shadow home), the players' buttons, the TO panel, the two sweeps | 🔨 branch `brackets-discord` — §E as built |
| **L3** | The site page `brackets.html`: the bracket drawn, the TO's moves, the player's moves | 🔨 branch `brackets-site` — §F as built |

## A. The engine (`black_bloc/brackets/`, pure — no database, no Discord)

Every function takes plain data (`Bracket`, `Match`, `Options` in `model.py`) and returns plain data. A move works on a
deep copy and returns `Moved(bracket, changed, removed)`; the caller persists `changed` and deletes `removed`. A refused
move raises `BracketError(code, **fields)`; the caller turns the code into words (`brackets_<code>_said`).

| Module | Does |
|---|---|
| `model.py` | Constants (formats, sides, states, slots), `Options`, `Match` (a set: structure + result), `Bracket`, `BracketError`, `order_key` (play order), `key_of` (`W2-3`, `L1-1`, `G1-1`, `T1-1`, `R3-2`, `S1-4`) |
| `seeding.py` | `bracket_size`, `standard_order` (1 v N, then the halves split), `first_round` (byes to the top seeds), `randomised`, `reordered` (the TO's order) |
| `bestof.py` | `wins_needed`, `fits` (a score finishes the best-of), `checked`, `valid_length` (odd, 1–15), `length_for` (default / late / finals) |
| `elimination.py` | `single`, `double`: every set and its explicit links (`winner_to`/`winner_slot`, `loser_to`/`loser_slot`, `reset_of`), structural places, the drop pattern (`drop_target`, `flipped`); `alive` and the best-of are set by `play.pace` |
| `roundrobin.py` | `schedule` (circle method, rounds), `match_count`, `build` |
| `swiss.py` | `rounds_for` (default ceil(log2 n)), `most_rounds` (n − 1), `pairings` (score groups, no rematch, backtracking), `pair_round` (bye to the lowest-ranked without one), `next_round_due`, `add_round`, `build` |
| `tally.py` | `records` (sets, games, byes, opponents, who beat whom), `met` (every pair ever paired) |
| `play.py` | `build`, `settle` (byes, voids, forfeits, deliveries, the next Swiss round), `rehearsed` / `pace` / `sets_to_play`, the moves `call` / `report` / `confirm_report` / `accept` / `confirm_due` / `dispute` / `override` / `reset` / `withdraw` / `reinstate`, `downstream`, `finished`, `confirms_at` |
| `standings.py` | `placements`, `table` (round robin and Swiss), `ranked` (tiebreaks), `waiting_on` (what each entrant waits on) |
| `checkin.py` | `closes_at`, `due`, `no_shows`, `present` |
| `access.py` | `may_run(store, guild, person)` — the ONE write rule (staff, or a holder of `brackets_to_role_id`) |

### A1. Seeding and byes

Seeds are an ordered entrant list. The bracket is the next power of two ≥ the field (min 2); `standard_order(8)` is
`1 8 4 5 2 7 3 6` (positions pair 1v8, 4v5, 2v7, 3v6). A seed past the field is a bye, so byes fall to the top
seeds and no first-round set ever holds two byes. Seeding is sign-up order until the TO reorders (`seed` with an
order naming every active entrant once) or shuffles (`randomise`). At **Start** the active entrants (not dropped,
not DQ'd) are re-seeded 1…n in their current order.

### A2. Single elimination

Round r has `size / 2^r` sets; set p's winner goes to round r+1 set ⌈p/2⌉, slot a if p is odd. Placements: the
final's winner 1, loser 2; semi-final losers 3 and 3 — or, with the third-place set (`T1-1`, fed by both
semi-final losers), its winner 3 and loser 4; a loser of a round with k sets is placed k+1 (5, 9, 17 …). A bye
places nobody. With 3 entrants and a third-place set, `T1-1` is itself a bye: the one semi-final loser is 3rd.

### A3. Double elimination and the drop pattern

Size N = 2^k. Winners rounds 1…k as single elimination; the winners final's winner goes to the grand final slot a.
Losers rounds 1…2k−2: round ℓ has `N / 2^(⌈ℓ/2⌉+1)` sets. Odd losers rounds pair losers-side survivors; even
losers rounds are **drop rounds** (survivor in slot a, the dropped winners-side loser in slot b). The losers final's
winner goes to the grand final slot b. With 2 entrants there are no losers rounds: the winners-round loser drops
straight into the grand final.

- Winners round 1 losers: pairwise into losers round 1 (W1-1 and W1-2 → L1-1, …).
- Winners round r ≥ 2 losers drop into losers round 2r−2 at the **neighbouring** position — `flipped(p)` is p+1 for
  odd p and p−1 for even p (a "pair flip") — and at position 1 when that round has one set (the forced last drop).

**Why the pair flip.** By induction, the survivor arriving at a drop-round set at position q has only ever met players
from the winners subtree that feeds position q; the flip sends the dropped player to the OTHER subtree of the pair,
so **an arriving player never meets anyone they have already played**, until the forced last drop into the losers
final (and the 4-entrant bracket, whose only drop round has one set). `tests/brackets/test_elimination.py::
test_a_dropped_player_never_meets_anyone_they_have_already_played_on_arrival` proves it by simulation for 8, 16, 32
and 64 with random results, and fails when the flip is replaced by the natural order. For 8 and 16 the pattern is
the one the open-source `brackets-manager.js` uses for start.gg-style brackets (natural, reverse-half-shift /
reverse, natural); for 32+ it keeps pair-flipping where that library alternates other orders. ⚠️ start.gg does not
document its drop order (research §3); "the convention start.gg uses" could not be confirmed from a source, so the
choice above is justified by the no-rematch property, not by imitation.

**8 entrants** (who feeds each losers set; *alive* is the count still in when it is played; *loser place* is where
its loser finishes). These losers-side numbers are unchanged by review fix 2; the winners side now reads W1 8, W2 6,
W3 3 (it was 8, 8, 4):

| Set | Slot a | Slot b | Alive | Loser place |
|---|---|---|---|---|
| L1-1 | loser of W1-1 | loser of W1-2 | 8 | 7 |
| L1-2 | loser of W1-3 | loser of W1-4 | 8 | 7 |
| L2-1 | winner of L1-1 | loser of **W2-2** | 6 | 5 |
| L2-2 | winner of L1-2 | loser of **W2-1** | 6 | 5 |
| L3-1 | winner of L2-1 | winner of L2-2 | 4 | 4 |
| L4-1 | winner of L3-1 | loser of W3-1 | 3 | 3 |
| G1-1 | winner of W3-1 | winner of L4-1 | 2 | 2 |
| G2-1 | the reset: G1-1's two players, only if slot b won G1-1 | | 2 | 2 |

Worked with the higher seed always winning: W1 1>8, 4>5, 2>7, 3>6 → L1-1 8 v 5 (8 out, 7th), L1-2 7 v 6 (7 out,
7th). W2 1>4, 2>3 → 4 drops to **L2-2** against 6 (4 met 5 and 1; the natural order would have sent 4 against 5
again), 3 drops to L2-1 against 5. 5 and 6 out (5th), L3 3>4 (4th), W3 1>2 → 2 drops to L4-1 and beats 3 (3rd);
grand final 1 v 2. Places **1, 2, 3, 4, 5, 5, 7, 7** — asserted in `test_double_elimination_places_…[8]`.

**16 entrants:**

| Set | Slot a | Slot b | Alive | Loser place |
|---|---|---|---|---|
| L1-1 … L1-4 | losers of W1-(2q−1) | losers of W1-(2q) | 16 | 13 |
| L2-1 | winner of L1-1 | loser of **W2-2** | 12 | 9 |
| L2-2 | winner of L1-2 | loser of **W2-1** | 12 | 9 |
| L2-3 | winner of L1-3 | loser of **W2-4** | 12 | 9 |
| L2-4 | winner of L1-4 | loser of **W2-3** | 12 | 9 |
| L3-1 | winner of L2-1 | winner of L2-2 | 8 | 7 |
| L3-2 | winner of L2-3 | winner of L2-4 | 8 | 7 |
| L4-1 | winner of L3-1 | loser of **W3-2** | 6 | 5 |
| L4-2 | winner of L3-2 | loser of **W3-1** | 6 | 5 |
| L5-1 | winner of L4-1 | winner of L4-2 | 4 | 4 |
| L6-1 | winner of L5-1 | loser of W4-1 | 3 | 3 |
| G1-1 / G2-1 | winners final winner v losers final winner; reset as above | | 2 | 2 |

L3-1 only ever holds players from the top half of the winners bracket and L3-2 only the bottom half, so the
winners-semifinal loser from the top half (W3-1) drops against a bottom-half survivor (L4-2) and never meets anyone
they have played. Places with the higher seed always winning: **1, 2, 3, 4, 5, 5, 7, 7, 9×4, 13×4**; 17 entrants
add 17th (asserted).

**Placements** in general: a losers-round-ℓ loser is placed `3 + (sets in every later losers round)` — 1, 2, 3, 4, 5,
5, 7, 7, 9×4, 13×4, 17×8, 25×8 … The grand final's loser is 2nd; with the reset on and slot b winning G1-1, G1-1
places nobody and G2-1 decides 1 and 2.

**Grand-final reset** (`grand_final_reset`, default on, from `brackets_grand_final_reset_default`): G2-1 is built
with the bracket and wakes READY with G1-1's two players only when G1-1 completes with slot b (the losers-side
player) winning and not by forfeit; otherwise it becomes `void`. Off: G2-1 is not built and G1-1 decides.

### A4. Best-of

Each set stores its `best_of` at build. `length_for`: the last set of an elimination bracket (single elimination's
final, the grand final and its reset) plays `best_of_finals`; a set played with `best_of_from_round` or fewer
entrants still **alive** plays `best_of_late`; everything else `best_of`. ~~*Alive* (stored per set): winners round 1
= the bracket size; winners round r ≥ 2 = 4 × its sets; an odd losers round = 4 × its sets; a drop round = 3 × its
sets; the grand final = 2; a single-elimination round = 2 × its sets; the third-place set = 4. So "8" means top 8:
in a 16 bracket, W3, L3 and later.~~ *(Superseded by review fix 2, 2026-10-07: it was the bracket's size, not who
was left, so W2 of a full 8 read 8 while L2 beside it read 6.)* **Alive** (stored per set, `play.pace`) = the
entrants not yet placed when the set's round is played: n minus everyone eliminated in a round that plays earlier.
Rounds play in `order_key` order (W1, L1, W2, L2, L3, W3, L4, L5, W4, …); the third-place set plays with the final
and both grand-final sets together. Which sets eliminate someone never depends on who wins, so `pace` reads the
count per round off a rehearsal (`rehearsed`: a copy played out with slot a winning). For a full 16: W1 16, L1 16,
W2 12, L2 12, L3 8, W3 6, L4 6, L5 4, W4 3, L6 3, G 2 — the losers side as before; "8" (top 8) now starts at L3 and
W3. A field with byes counts only real sets: 9 entrants in double elimination stay 9 through W2 and L2 (the W1 loser
takes a bye in L1), so top 8 starts at L3/W3; in single elimination it starts at W2. Round robin and Swiss play `best_of` throughout. A score fits only when one side
reached `best_of // 2 + 1` wins and the other has fewer (`bestof.fits`); anything else is refused in words.

### A5. Round robin

Every pair once (`n(n−1)/2` sets) in `n−1` rounds (n rounded up to even; with an odd field one entrant sits each
round out), so sets can be called round by round. Every set is READY from the start. Standings: set wins, then game
wins, then head to head inside the tie (set wins among the tied), then the TO's final order — which breaks a tie
only when it names **everyone** in it; a tie nothing breaks shares the place (1, 2, 2, 4). Places are written only
when every set is final.

### A6. Swiss

Rounds: `swiss_rounds`, else ceil(log2 n). Round 1 pairs the top half against the bottom half (1v5, 2v6 … for 8).
Each later round is paired when the round before is all final (`settle` makes it): entrants ordered by points (set
wins, a bye counting as one) then seed; the partner tried first for the top unpaired player is halfway down their
own score group, then outward, then lower groups; a pairing that would be a rematch is skipped and the search
backtracks; if no rematch-free pairing exists within a search budget the order is paired top-down, and every set
that repeats a pair carries **`rematch`** (stored, in the view and on every `set_*` log row) so layers 2 and 3 can
show it. **Start refuses `swiss_rounds` past n − 1** in words (`too_many_rounds`) — more rounds than that cannot
avoid a rematch; at the default rounds no rematch was found for n = 4…100 (review). The fallback can still fire
with fewer active players after drops and DQs, which is what the flag is for. An odd field
gives a bye (a `bye` set, a set win) to the lowest-ranked entrant who has not had one. A withdrawn entrant is never
paired again. Standings: points, then opponents' win rate (the mean of each opponent's set wins ÷ sets played, byes
counted for the opponent, the entrant's own byes excluded), then head to head, then the TO's order; places when the
last round is final.

### A7. The set state machine

| State | Means | Reached by |
|---|---|---|
| `waiting` | a slot is not known yet | build; a reset that cleared a slot |
| `ready` | both players known | `settle` once both slots fill; `reset` of a reported / called / disputed set |
| `called` | the TO called it to be played | `call` (TO) from `ready` |
| `reported` | one player reported a score | `report` (player) from `ready`/`called`; the same player may re-report |
| `disputed` | the opponent flagged the report | `dispute` (the opponent, with an optional note) from `reported` |
| `complete` | final | the opponent's `confirm`, or the opponent reporting the SAME score; `confirm_due` after the confirm time; `accept` (TO lets a reported/disputed score stand); `override` (TO, any score or a forfeit, from any playable state, or correcting a final set); a forfeit when an entrant is withdrawn |
| `bye` | one side can never be filled | `settle` — the other side advances, no score |
| `void` | neither side can be filled, or a grand-final reset that is not needed | `settle` |

*Confirmed* is not a resting state: a confirmed set is `complete` the same instant, and the row says how
(`confirmed_how` = `opponent` / `time` / `to`, `confirmed_by`, `confirmed_at`). The opponent reporting a DIFFERENT
score is refused with the score already reported (*confirm that, or dispute it*). The reporter cannot confirm or
dispute their own report.

**Withdrawal** (`withdraw(entrant, dq|drop)`): every open set they are in is forfeited now (`forfeit` = `dq`/`drop`,
no score, the opponent wins), and every set they reach later is forfeited the moment it fills — so a DQ'd
winners-side player drops into losers and forfeits there too, and is placed where that leaves them. If both players
are withdrawn, slot a "wins" and forfeits onward. A withdrawn player facing an empty side takes the bye and forfeits
the next set. `reinstate` lifts the flag only: forfeits already recorded stand until the TO resets those sets.

**Reset and "downstream".** Resetting a `complete` set takes back its result and everything that result fed:
- elimination: the set its winner went to and the set its loser dropped to (only where that player is still sitting
  there), the grand-final reset it opened, and recursively everything those decided. A set the result never reached
  — the other half, another branch of the losers bracket — is never touched (`test_a_reset_in_single_elimination_
  undoes_the_winners_path_and_never_the_other_half`, `test_a_reset_in_double_elimination_takes_back_the_drop_into_
  losers`);
- round robin: nothing — every set stands alone;
- Swiss: every set in every later round (their pairings came from the standings), which are deleted; a reset round
  is re-paired once it is final again.
A reset of a `reported`/`called`/`disputed` set just puts it back to `ready`. A bye cannot be reset; a set with no
result answers *nothing to reset*. ~~An override of a `complete` set is a reset plus the new result.~~ *(Superseded
by review fix 4, 2026-10-07.)* An override of a `complete` set that **keeps the winner** (a score correction)
changes that set only — in every format, what it fed stands, Swiss later rounds included, since pairing reads only
set wins and seed. An override that **flips the winner** is a reset plus the new result (Swiss later rounds are
deleted and re-paired). Round robin has nothing to re-pair either way. One exception: a grand final that opens a
reset set always takes the full reset, because forfeit-or-not decides whether G2-1 is played.

A reporter **re-reporting restarts the confirm clock** (`reported_at` is the latest report) — decided, review fix 12:
the opponent gets the full confirm time to answer the score that now stands.

### A8. Check-in (start.gg's "remove and rebalance")

Optional. The TO opens it (`check_in_minutes`, default `brackets_check_in_minutes` 30); guests are checked in when it
opens (nobody else can check them in) — the TO can take that back. Members check themselves in; the TO can check
anyone in or out. When it closes — by the TO, or by the layer-2 sweep once `check_in_closes_at` passes — everyone
still in and not checked in is taken out (`dropped_why = no_show`), and the bracket is built later from who is left.
Start is refused while check-in is open.

## B. Storage (schema 90)

`black_bloc/storage/db.py` gains three tables (no column migration; `test_a_schema_89_file_gains_the_bracket_
tables_and_loses_nothing`). `black_bloc/brackets_store.py` is the only module that reads or writes them.

- **`tournaments`** — `guild_id`, `name`, `game`, `format`; options as columns: `third_place`, `grand_final_reset`,
  `swiss_rounds`, `best_of`, `best_of_from_round`, `best_of_late`, `best_of_finals`, `entrant_cap`,
  `check_in_minutes`, `confirm_minutes`; `rules_text`, `starts_at`; `state` (draft / signups / check_in / seeding /
  running / complete / cancelled), `state_before` (what a cancel restores); `created_by`, `to_user_id`; `source`
  (`own` | `startgg`), `source_ref`; for layer 2, nullable `channel_id`, `thread_id`, `message_id`, `shadow`;
  `check_in_opened_at`, `check_in_closes_at`, `started_at`, `completed_at`, `cancelled_at`, `created_at`,
  `updated_at`.
- **`tournament_entrants`** — `tournament_id`, `user_id` (NULL = a guest), `name`, `seed`, `checked_in`,
  `checked_in_at`, `dropped`, `dropped_why` (`removed` by a TO / `left` themselves / `no_show` / `dropped` mid-bracket),
  `dropped_at`, `dq`, `final_rank` (the TO's tie order), `placement` (written at completion), `added_by`, `added_at`.
  Partial UNIQUE `(tournament_id, user_id) WHERE user_id IS NOT NULL` — one row per member; a member who left and
  signs up again gets the same row back.
- **`tournament_sets`** — every `Match` field as a column: `key`, `side`, `round`, `position`, `best_of`, `state`,
  `slot_a`/`slot_b` (entrant ids), the explicit links `winner_to`/`winner_slot`/`loser_to`/`loser_slot`/`reset_of`,
  `alive`, `winner_place`/`loser_place` (structural), and the result: `score_a`/`score_b`, `winner`, `loser`,
  `forfeit`, `called_at`/`called_by`, `reported_by`/`reported_side`/`reported_at`, `confirmed_by`/`confirmed_at`/
  `confirmed_how`, `disputed_by`/`disputed_at`/`dispute_note`, `completed_at`, `placement_winner`/`placement_loser`,
  `rematch` (0/1, review fix 1); and for layer 2 (review fix 3, not `Match` fields so a save never touches them)
  nullable `message_id` (the set's card in the thread) and `card_at` (when it was posted). UNIQUE
  `(tournament_id, key)`; a save is an upsert on it. `brackets_store.cards` / `set_card` read and write the card;
  a save answers the removed sets' cards and `clear_sets` every card it dropped.

Every write runs under `brackets_moves.lock_for(bot, tournament_id)` (one `asyncio.Lock` per tournament, kept on the
bot) with the unique indexes behind it (checklist 6; `test_two_sign_ups_at_once_leave_one_entrant`).

## C. The moves and the API

The moves are the ONE implementation both doors call (layer 2's buttons and the site's routes); each takes
`via` (default `VIA_DISCORD`), logs ONE row and returns an `Outcome` whose message is ~~a settings key's words~~ a
player-facing settings key's words or an organiser line from `brackets_moves.TO_WORDS` (review fix 13). Every
`Outcome` carries **`changed`** — the set keys the move changed or removed, in play order (empty for a move that
touches no set) — and **`gone`** — `{key: message_id}` for removed sets that had a card (a Swiss correction, Back
to seeding), so layer 2 edits exactly those cards without diffing the view (review fix 3).

| Module | Moves |
|---|---|
| `brackets_moves.py` | the shared helpers (`lock_for`, `mode_of`, `said`, `note`, `require_*`, `engine`); `create`, `edit`, `open_signups`, `close_signups`, `seed`, `start`, `unstart`, `complete`, `reopen`, `cancel`, `restore` |
| `brackets_people.py` | `join`, `add_entrant`, `remove_entrant`, `restore_entrant`, `drop`, `dq`, `open_check_in`, `close_check_in`, `set_check_in`, `close_due_check_ins` (sweep) |
| `brackets_sets.py` | `call`, `report`, `confirm_report`, `dispute`, `override`, `reset`, `confirm_due` (sweep) |
| `brackets_view.py` | `summary`, `full` — the tournament as both doors read it |

**Who may do what.** `brackets.may_run(store, guild, person)` = staff OR a holder of `brackets_to_role_id`. **The role
decides, not authorship:** a TO who loses the role loses the right even on a tournament they created (staff still
have it). Gated by `may_run`: everything except a player's own moves. A player's own moves: `join`; `drop` and
`set_check_in` on their own entrant; `report`, `confirm`, `dispute` on a set they are in. A TO who is also playing
in a set acts there as a player (their report waits for the opponent) and decides it with `override`. `brackets_mode
= off` refuses every move in words; reads still answer.

**The API** (`black_bloc/api/tools/brackets.py`, prefix `/api/brackets`). Reads need a signed-in member (the read
bucket); writes need a signed-in member and spend the staff write bucket (60 a minute — a TO reporting a round must
not hit the member bucket's 10), then the move decides. Every write answers `{tournament, message}`; every refusal is
`{error, message}` with the status the move chose — never a bare status.

| Route | Move | Who |
|---|---|---|
| `GET /api/brackets` | `{mode, may_run, tournaments[]}` | member |
| `GET /api/brackets/{id}` | the full view: options, entrants, sets (with `a_name`, `b_name`, `confirms_at`), standings, `waiting_on`, `may_run`, `mine` | member |
| `POST /api/brackets` | create `{name, game?, format?, …options}` | TO |
| `PATCH /api/brackets/{id}` | edit options, before the start | TO |
| `POST …/{id}/signups/open` · `/signups/close` | draft/seeding → signups → seeding | TO |
| `POST …/{id}/checkin/open` · `/checkin/close` | signups/seeding → check_in → seeding | TO |
| `POST …/{id}/join` | sign me up | member |
| `POST …/{id}/entrants` `{name?, user_id?}` | add a member or a guest | TO |
| `DELETE …/{id}/entrants/{eid}` | remove before the start | TO |
| `POST …/{id}/entrants/{eid}/restore` | undo a removal, leave, no-show, drop or DQ | TO |
| `POST …/{id}/entrants/{eid}/checkin` `{checked_in?: false}` | check in / out | self or TO |
| `POST …/{id}/entrants/{eid}/drop` | leave before the start; forfeit the rest after it | self or TO |
| `POST …/{id}/entrants/{eid}/dq` | DQ, running only | TO |
| `POST …/{id}/seed` `{order: [eid…]}` or `{randomise: true}` | seeding | TO |
| `POST …/{id}/start` · `/unstart` | build the bracket · back to seeding, sets cleared | TO |
| `POST …/{id}/complete` `{order?: [eid…]}` · `/reopen` | placements written (the order splits a table tie) · back to running | TO |
| `POST …/{id}/cancel` · `/restore` | cancel · back to the state before | TO |
| `POST …/{id}/sets/{key}/call` | call | TO |
| `POST …/{id}/sets/{key}/report` `{score_a, score_b}` | a player's report; a TO's is final | player or TO |
| `POST …/{id}/sets/{key}/confirm` | the opponent confirms; a TO lets it stand | player or TO |
| `POST …/{id}/sets/{key}/dispute` `{note?}` | flag for the TO | the opponent |
| `POST …/{id}/sets/{key}/override` `{score_a, score_b}` or `{winner: "a"\|"b"\|eid, forfeit: true}` | decide / correct | TO |
| `POST …/{id}/sets/{key}/reset` | take back, with what it decided | TO |

All 28 routes are in `site/mock/contract.json` (the real router answers them in `tests/api/test_contract.py`
against `seed_brackets`; the mock in `site/mock/server.mjs` against eight seeded tournaments, one per state).

**Log kinds** — one head, `brackets.` (filed under `core`, as `pbfeed` is), each with `via`, `tournament` and, for a
set, `set`; the `web.` twin via `kind_via` when the site is the door: `created`, `edited`, `signups_opened`,
`signups_closed`, `check_in_opened`, `check_in_closed`, `checked_in`, `checked_out`, `entrant_added` (`by_self` for a
sign-up, `guest`), `entrant_removed`, `entrant_restored`, `dropped` (`before_start` when it is a leave), `dq`,
`seeded`, `started`, `unstarted`, `completed`, `reopened`, `cancelled`, `restored`, `set_called`, `set_reported`,
`set_confirmed` (`how`), `set_disputed`, `set_overridden` (`cleared`: the sets it reset), `set_reset` (`cleared`,
`removed`). IMPORTANT: `dq`, `entrant_removed`, `cancelled`, `unstarted`, `set_disputed`, `set_overridden`,
`set_reset`; the rest ROUTINE. The two sweeps log `set_confirmed` (`how = time`, no actor) and `check_in_closed`
(no actor).

## D. Settings (~~85~~ 54 keys after the review fold, all under `core` — `brackets_` would be a 26th `/settings` group)

| Key | Type | Default |
|---|---|---|
| `brackets_mode` | enum off / shadow / on | **shadow** |
| `brackets_channel_id` | channel | `1076005097617760296` (#knuck-up) |
| `brackets_shadow_channel_id` | channel | blank → `shadow_channel_id` chain |
| `brackets_to_role_id` | role | blank (staff only) |
| `brackets_format_default` | enum single / double / round_robin / swiss | double |
| `brackets_best_of` · `_late` · `_finals` | enum 1/3/…/15 | 3 · 5 · 5 |
| `brackets_best_of_from_round` | int 2–1024 | blank = never |
| `brackets_grand_final_reset_default` | bool | true |
| `brackets_third_place_default` | bool | false |
| `brackets_confirm_minutes` | int 1–1440 | 12 |
| `brackets_check_in_minutes` | int 5–1440 | 30 |
| `brackets_swiss_rounds_default` | int 1–20 | blank = ceil(log2 n) |
| `brackets_entrant_cap_default` | int 2–1024 | blank = no cap |
| `brackets_panel_minutes` | int 1–14 | 10 |

~~Plus **69 word keys** (`BRACKETS_WORDS`): every success line (`brackets_<move>_said`), every refusal
(`brackets_<code>_said`), the state words (`brackets_state_<state>`), `brackets_forfeit_words`,
`brackets_no_role_words`.~~ *(Superseded by the owner's decision "bb", 2026-10-07: only player-facing words are
settings keys.)* Plus **38 word keys** (`BRACKETS_WORDS`), the words a player can see: the three posted in the thread
(`set_called`, `set_final`, `forfeit_words`) and every line or refusal a member who is not an organiser can receive —
`joined`, `left`, `checked_in`, `checked_out`, `dropped`, `set_reported`, `set_disputed`, `off`, `not_organiser`,
`no_role_words`, `no_tournament`, `wrong_state` and the seven `state_*`, `not_yours`, `full`, `already_in`,
`removed_by_to`, `no_set`, `not_in_set`, `not_ready`, `not_playable`, `already_complete`, `disputed`, `bad_score`,
`reported_differently`, `not_reported`, `own_report`, `not_in_bracket`, `already_out`. The 30 organiser-only lines
are constants in `brackets_moves.TO_WORDS`, like other features' refusals. A staff edit that cannot be filled — any
exception — falls back to the shipped wording (checklist 17). Labels in `site/public/assets/labels.js`; mock rows
in `site/mock/server.mjs` (the mock's `BK_TO_WORDS` mirrors `TO_WORDS`).

**Layer 2 adds ~~64~~ 65 keys (1000 → ~~1064~~ 1065, all under `core`):** `brackets_ping_role_id` (role, blank — a role
@-mentioned in the thread at the start) and **~~63~~ 64 word keys** (`BRACKETS_CARD_WORDS`, merged into `BRACKETS_WORDS`, so each has
named fields checked on a staff edit): the four format words, the starter card's lines and option words, the three
starter buttons and `brackets_card_link_label`, `brackets_not_entered_said`, the set card's players line, six round
words, title, best-of, rematch mark and five state lines, the three player buttons, the report and dispute forms'
titles and labels, `brackets_score_not_number_said`, the panel's title, line, empty line, two placeholders, Back,
*Your sets*, Drop out and its question, footer, the six DM texts, the start ping and *(review fix 2)*
`brackets_moved_line` — the line a rehearsal thread keeps once staff move its tournament. Organiser-only words (the panel's
moves, the organiser buttons on a card, the organiser forms) are constants in `brackets_panel.py`,
`brackets_cards.TO_LABELS` and `brackets_buttons.py` (the owner's "bb"). Labels in `labels.js`, rows in the mock
(`BRACKETS_KEYS` regenerated from the registry), `contract.json` `core_keys` 171 → ~~235~~ 236. The `/settings` panel-minutes
select stays at 25: layer 2 adds no `*_panel_minutes` key.

## E. Layer 2 — Discord (as built, branch `brackets-discord`)

*Rewritten 2026-10-07 from the spec to what runs. Where the build brief differed from the old spec the brief won; each
difference is a §G decision. ~~The old spec's **Move to #knuck-up** button and the **Complete** tie-order select are not
built (§H).~~ (Amended by the layer-2 review fixes, 2026-10-07: **Move to #knuck-up** is built — below; the
**Complete** tie-order select is still not built, §H.)*

| Module | Does |
|---|---|
| `black_bloc/cogs/community/brackets.py` | The cog (registered in `bot.py:COGS`): `/bracket`, the persistent card buttons (`add_dynamic_items` in `cog_load`), the one-minute `_sweep` loop (`@loop.error` restarts it, `last_ok_at`/`last_error` for the health tab), the boot reconcile on `on_ready` — both under one `loops.Reconciler`. |
| `black_bloc/brackets_thread.py` | The thread and every card in it: where a thread goes, making it, the starter card, one card per set, `follow` (after any move, from either door), `reconcile`, `sweep`, the start ping, `tell` (the DMs). |
| `black_bloc/brackets_cards.py` | What the thread shows, as plain functions: the starter embed and view, a set's embed, players line and view, which buttons are legal (`starter_moves`, `set_moves`), the persistent `StarterButton` / `SetButton` (`SafeDynamicItem`). |
| `black_bloc/brackets_buttons.py` | What a press does: `starter_pressed`, `set_pressed` / `set_move`, the forms (`ReportModal`, `DisputeModal`, `DecideModal`, `ResetModal`, `ForfeitModal`), and where an answer lands (`CardLanding`; the panel's `PanelLanding`). |
| `black_bloc/brackets_panel.py` | The `/bracket` panel. |

**Where the thread goes.** `brackets_mode = on` → a public thread under `brackets_channel_id` (#knuck-up); `shadow` →
under `shadow.channel_id(bot, guild, feature="brackets")` (`brackets_shadow_channel_id`, then `shadow_channel_id`, then
the guard's channel, then the log channel); `off` → none, and nothing posts. It is made when the tournament is
**created** (the brief: *on create*), or by the first follow or tick that finds none. The row records `channel_id`,
`thread_id`, `shadow` (1 in the rehearsal home) and `message_id` (the starter card). A mode flip never moves a thread;
staff do, with **Move to #knuck-up** (below).
A forum parent takes the starter card with the thread (supported, not exercised — §H).

**The starter card** (pinned; the rehearsal note naming `#knuck-up` above it in shadow): the name; the game; the format
line with its options (`grand-final reset`, `third-place set`, Swiss rounds, the late best-of, the finals best-of); the
state; the entrant count (with the cap when there is one); the start time before the start; when check-in closes while
it is open; the organiser; the top 8 placings once complete. Buttons: ~~**Sign up** and **Leave** during sign-ups,
**Check in** and **Leave** during check-in, nothing else~~ *(review fix 11)* **Sign up** during sign-ups, **Check in**
during check-in, and **Leave** wherever it is legal — draft, sign-ups, check-in and seeding — while anyone is in — plus
**Open the bracket** (`/brackets.html#<id>`, layer 3) when the site has an origin. It is EDITED in place by every follow;
it is posted again only by a reconcile, and only when its stored id no longer resolves — *(review fix 4)* the minute
tick checks that too (`fetch_message` on the stored id). A starter with no stored id (a restart between the send and the
store) is adopted only from the bot's own ordinary message carrying this tournament's starter buttons or its title —
never a set card, never the *pinned a message* notice (review fix 1).

**A set card** — one per set, posted when the set is open (`ready`, `called`, `reported`, `disputed`) and has no card:
the players line `{a} v {b}` (an @-mention for a member, the plain name for a guest), the title `{set} · {round}`
(Winners round 2, Losers round 3, Grand final, Grand final reset, Third place, Round 4), `Best of 3` (`· Rematch` when
the set carries `rematch`), and the state line: *Ready to play* · *Called — play now* · *Ada reported 2–1 — waiting on
Bea, stands in 12 minutes* · *Disputed by Bea — an organiser decides* (and the note) · the final line (*W1-1 is final:
Ada wins 2–1* / *by forfeit*) · *W1-1 was cleared*. Buttons by the set's state, only while the tournament runs:

| Set | Row 0 (players) | Row 1 (organisers — constants, refused in words to anyone else) |
|---|---|---|
| ready | Report | Call · Decide… |
| called | Report | Decide… · Reset… |
| reported | Confirm · Dispute | Decide… · Reset… |
| disputed | — | Decide… · Reset… |
| complete | — | Decide… · Reset… |

Who presses is checked on the press: a stranger's Report or Dispute is refused in words and opens no form; the
reporter's Confirm answers *own report*; Decide, Reset and Call re-ask `may_run` every press. A TO's Report on a set
they are not in is final at once (layer 1). Mentions: `AllowedMentions(users=[the two])` when ~~the THREAD is not a
rehearsal (`shadow` 0)~~ *(review fix 2)* `brackets_thread.live` holds — the mode is `on` AND the thread is not a
rehearsal — `AllowedMentions.none()` otherwise; every edit is `none()`. No form opens while the mode is `off` (review
fix 10).

**Card lifecycle.** Idempotent by stored id, under `brackets_thread.card_lock(bot, tournament)` (re-read inside it):
before the send the set gets `card_at` with no `message_id`, after it the id. A follow EDITS the starter card and every
card in `Outcome.changed`, edits the cards in `Outcome.gone` to the cleared line (no buttons, ids dropped), and posts a
card for an open set that has none. A card whose set falls back to `waiting`/`bye`/`void` is cleared and its id dropped
*(review fix 8: only once the clear landed or 404'd; a failed clear keeps the id and is tried again next tick)*, so a
fresh card (and ping) comes when it is ready again. Complete, Reopen, Cancel, Restore *and Move* re-render every card (the
buttons depend on the tournament's state); an entrant's Restore is `restore_entrant` and edits only what it changed
(review fix 5). An edit that finds the message gone (a 404, nothing else) marks it; the next tick posts it again. An
edit or clear that fails any other way (429, 5xx, a timeout) keeps the card, is `card_failed` once, and is tried again
next tick (review fix 16). A set that fills already forfeited — a DQ'd player's later set — gets one card in its final
state, mentioning the walkover winner (review fix 9).
A set holding a stamp and no id ("may have been posted": a restart between the send and the store) is looked for by its
buttons' custom-id prefix in the thread's last 100 messages and adopted before anything is posted.

**The sweep** — every minute, per available guild, skipped while `off`: `brackets_sets.confirm_due` and
`brackets_people.close_due_check_ins`, then the cards for what they changed (the confirmed set's card, the starter card
of a closed check-in), then a reconcile pass. At most **5 new set cards per pass**; the rest come next tick.

**Reconcile** — on boot ~~(`on_ready`, `skip_if_recent`)~~ *(review fix 4: the loop's FIRST tick after a boot, and the
first after a reconnect's `on_ready`)* every live tournament (draft … running) gets a FULL pass: the
thread (re-made after two NotFounds running), the starter card and every stored card edited (a NotFound posts it
again, `brackets.card_reposted`), a card for each open set without one. The minute tick runs the cheap pass: missing
threads, starter cards and cards, the starter's stored id checked (review fix 4), anything a follow marked gone, and
anything whose last write failed. "Missing" is decided by the stored id; the only searches are the two adoptions above.
A thread the bot cannot read is `brackets.thread_failed` once a run, worded as a permission (`Forbidden`) or as
"could not be reached" (anything else) — never every tick (review fix 3).

**Pings and DMs.** The set card's mention is the only ping by default. `brackets_ping_role_id` (blank) is @-mentioned
in the thread at the start (`brackets_start_ping`); in a rehearsal it is named, pings nobody, and `brackets.would_ping`
is logged. A member is DM'd (`brackets_thread.tell`) — never the organiser who made the move (review fix 12) — when an
organiser removes them (`brackets_dm_removed`), DQs them
(`_dq`), drops them (`_dropped`), decides or corrects their set — Decide, a forfeit, an organiser's report
(`_decided`, both players) — or resets it (`_reset`, both players); the organiser's optional reason follows as
`brackets_dm_reason`. Sent only when the mode is `on` AND the tournament's thread is not a rehearsal (`live`); otherwise
`brackets.would_dm` is logged and nothing is sent; a DM that cannot land is `brackets.dm_failed`. Both rows carry
`text` (the DM as rendered) and `reason` (the organiser's); `dm_failed` also `why` (review fix 6).

**Move to #knuck-up** (review fix 2, the conductor's decision following the reviewer) — for a tournament whose thread was
made in shadow. **Staff only** (`access.is_staff`, not the TO role: it writes to a real channel); on the panel for staff
while `shadow` is 1 and the mode is `on` (asks first), and `POST /api/brackets/{id}/move`. It makes a new thread under
`brackets_channel_id` FIRST (nothing changes if that fails — 502, in words), then drops every stored card id, edits the
old starter to `brackets_moved_line` (*This tournament moved to {thread}.* — no embed, no buttons; a 404 posts the line
instead; nothing is deleted), logs `brackets.thread_moved` (IMPORTANT; actor, `via`, `from_thread`, `to_thread`) and sets
`shadow` 0; the follow posts the pinned starter and every open set card in the new thread (5 a pass, the rest next tick),
pinging as `live` now allows. Refused in words: not staff (403), the mode not `on` (409, naming the mode), already in
#knuck-up (409). Staff-only words are `brackets_thread.MOVE_WORDS` constants (the owner's "bb").

**The panel** — `/bracket` (one command, ephemeral, `brackets_panel_minutes`, hidden while `brackets_mode` is `off`,
every view with `render_again`):

| View | A member sees | An organiser (staff or `brackets_to_role_id`) also sees |
|---|---|---|
| Home | the tournaments in sign-ups, check-in, seeding or running (one line each, a picker) | every tournament; **Create…** (form: name, game, format, best of, entrant cap) |
| A tournament | the starter card; *Your sets* (the players line is `brackets_set_card_players`, review fix 15); **Sign up** (sign-ups, not in) · **Leave** (in, before the start — draft and seeding too, review fix 11) · **Check in** (check-in, not yet) · **Drop out** (running, asks first); a picker of their sets | *Open sets*; the moves legal now — draft: Open sign-ups, Add entrant…, Cancel · sign-ups: Close sign-ups, Open check-in, Add entrant…, Cancel · check-in: Close check-in, Add entrant…, Cancel · seeding: Open sign-ups, Open check-in, Seed…, Shuffle, Start, Add entrant…, Cancel · running: Call ready sets (when one is ready), Complete (when finished), Back to seeding, Cancel · complete: Reopen, Cancel · cancelled: Restore; **staff only**, while the thread is a rehearsal and the mode is `on`: Move to #knuck-up; an entrant picker; a picker of every set |
| An entrant | — | before the start: Remove… or Restore (check-in: Check in / Check out first) · running: DQ… and Drop…, or Restore |
| A set | Report (ready/called) · Confirm and Dispute (reported, and not the reporter) | Report (not playing) · Call (ready) · Let it stand (reported/disputed) · Decide… · *{a} by forfeit…* · *{b} by forfeit…* · Reset… |
| Add entrant | — | a member picker, **Add a guest…** (form: name) |

Cancel, Back to seeding and Drop out ask first (Keep it / yes). Remove, DQ, Drop, Decide, Reset and a forfeit open a
form with an optional reason, which is what the member is DM'd — the form is the confirmation. Seed… is a form listing
`Name #id` one per line, top seed first (lines are read by the tag, then by a unique name). Every move goes through
the layer-1 move with `via=VIA_DISCORD`, the panel re-renders with the move's own words, then the cards catch up.

**The website's writes** (`api/tools/brackets.py` `answered`) ~~await `brackets_thread.follow` after every successful
move~~ *(review fix 7)* start `brackets_thread.follow_later` after every successful move — a tracked task, its failure
logged, never raised into the request — and wait for it at most `FOLLOW_GRACE_SECONDS` (1.5) before answering, so a
change made on the site reaches the thread too and a 64-entrant Complete (~127 card edits) can never hold a request past
Cloudflare's 100 s.

**Log kinds** added (head `brackets`, under `core`): `thread_made`, `card_reposted` (ROUTINE); `thread_lost`,
`thread_moved` and its `web.` twin (IMPORTANT; review fix 2); `thread_failed`, `card_failed`, `dm_failed` (IMPORTANT by
suffix; written once per tournament, card and reason a run); `would_dm`, `would_ping` (shadow, ROUTINE by rule).

## F. Layer 3 — the site page (as built, branch `brackets-site`)

*Rewritten 2026-10-07 from the spec to what runs. Differences from the old spec are §G 56–72; the layer-3 review fixes amended it in place the same day (§G 73–82, "Review fixes (layer 3)" below).*

| File | Does |
|---|---|
| `site/public/brackets.html` | The page shell (nav entry **Brackets** under *Runs the cookout*, icon `navBrackets`; a member who is not staff gets it too — `shell.MEMBER_TABS`). |
| `site/public/assets/page-brackets.js` | The list, a tournament, the set drawer, create/edit, Logs and Settings; live polling. |
| `site/public/assets/bracket-layout.js` | Pure: layout maths, the results grid, standings order, best-of scores, the seeding reorder, which moves a viewer may press. |
| `site/public/assets/brackets.css` | The page's styles, theme tokens only. |
| `site/mock/brackets.mjs` | The mock's engine stand-in (builds, byes, drops, the reset set, round robin, Swiss, resets, standings). |

**The list** (`/brackets.html`): one *Tournaments* section, full width — live ones first (running, check-in, sign-ups, seeding, draft), then **Complete** and **Cancelled** folded; search and chips (All / Live / Complete / Cancelled) through `listFilter`, which opens the folds when a search or chip is active. Each row: name; game · format · entrants (`n/cap` when capped) · start time before the start (viewer's zone, AM/PM) · the organiser's name; the state pill. A member sees no drafts and no cancelled ones. **New tournament** (organisers, while the mode is not `off`) opens the drawer.

**A tournament** (`/brackets.html#<id>` — the starter card's link): the head card — name, state pill (and *rehearsal* to organisers while the thread is a rehearsal), the meta line (game · format · Bo · ~~late/finals best-of · reset or third place or Swiss rounds~~ the starter card's option words — `brackets_card_reset_words` / `_third_words` / `_rounds_words` (the rounds the engine will play, `rounds_to_play`) / `_late_words` / `_finals_words` (only when it differs from the Bo) · entrants · organiser), the time line, **your line** (the viewer's `waiting_on` row in its word key; pressing it opens that set when there is a move), the member moves (`brackets_sign_up_label` / `_check_in_label` / `_leave_label` / `_drop_label`, legality = `memberMoves`, as the panel), the organiser moves (constants: Open/Close sign-ups, Open/Close check-in, Start, Edit…, Call ready sets, Complete, Back to seeding, Cancel, Reopen, Restore, and **Move to #knuck-up** for staff while the thread is a rehearsal and the mode is `on`; Cancel, Back to seeding, Move and Drop out ask first), Rules folded, and *updated N s ago*. Sections: **Bracket** (once started, full width), **Standings** (round robin and Swiss while running, every format once complete), **Entrants**, then **Logs** and **Settings** for staff.

- **Bracket**: elimination as an absolutely placed tree with SVG elbow lines along `winner_to` — winners on top, losers below, the grand final (and the reset while it may be played) after the longer side; round robin as a results grid (row player's score first, wins green, a disputed or reported pair marked `?`); Swiss as one column per round (a Swiss bye is a plain `name · bye` line, not a card). *(Review fix 2:)* a set nobody will play — a bye, a void set, or a waiting set whose feeders can only ever bring it one player or none (`unplayedSets`) — is not drawn: the player who goes through is already named in the next round's slot, nothing is pressable, and a round left empty gives up its column. Every set card: key · Bo · rematch mark, the state word (called / reported / disputed), both names and scores, the winner bold, the viewer's own sets outlined, a dot where the viewer has something to do. The tree scrolls sideways inside its section; the page does not. *(Review fix 8:)* the cards squeeze to fit the section (188 px, down to 140 px with a 20 px gap — `treeSize`), so an 8-player double elimination fits at 1280 px; a tree still wider (a phone, a big field) scrolls with the edge that has more faded, and redraws when the window is resized.
- **The set drawer** (press a set): the card, round · best-of · rematch, the state line in the set-card word keys, the dispute note, *In Discord* (`brackets_discord_label`) when the set has a card, then the moves `setMoves` allows: a score picker offering only scores that finish the best-of; **Report** (a player in a ready/called set, or the reporter again); **Confirm** / **Dispute** (with a note) for the opponent; and for organisers Call, Let it stand (only when not playing in it), Decide (the picker), *{name} by forfeit*, Reset, with one **Reason** field sent as `reason`.
- **Entrants**: before the start, organisers get the seeding list — a drag handle per row (pointer events; ArrowUp/ArrowDown on the handle), **Randomise** (client-side), and **Save seeding** / **Discard** once the order differs (*review fix 1:* an unsaved order keeps its moves when the poll lands, drops whoever left and puts a newcomer last, visible and draggable — `seedOrderWith`); Remove… (an inline reason field, sent as `reason`), Check in / Check out during check-in; **Add entrant** folded (a member picker for staff — `/api/ref/members` is staff-only — and a guest name for anyone who runs). Out entrants fold under **Out** (organisers only) with Restore. Once started: everyone in the bracket by seed (by place once complete — *review fix 6:* then the left column is the place and the seed is in the note), marks for DQ / dropped, placings, and for organisers each entrant's `waiting_on` line and DQ… / Drop… / Restore.
- **Standings**: elimination — place (ordinal) and player once placed; round robin — place/rank, sets W–L, games W–L; Swiss adds opponents' win % and byes. *(Review fix 7:)* under 700 px one compact row per player — place · name · sets W–L, with games, opp. win % and byes in the note.
- **Phones** *(review fixes 3 and 5)*: under 700 px every move a player or organiser presses (the head moves, score picks, Report, Confirm, Dispute, Decide, forfeits, Reset, Close, DQ… / Drop… / Remove… / Restore, Keep, the seeding tools, the drag handle, a results-grid cell, *your line*) is at least 40 px; an entrant row keeps seed · name on one line (the name ellipsised, only the note wraps) and puts its actions on their own line.
- **Logs** (staff): `GET /api/actions?feature=core&q=brackets&details=1`, kept to `brackets.`/`web.brackets.` rows (of this tournament in a tournament view).
- **Settings** (staff), folded: the mode switch first (`modeSwitch`, the ON · SHADOW · OFF control every page uses), the other `brackets_*` keys through `settingsPanel` (channel pickers read `#name · Category` through the shared helper), the word keys under a folded **Wording**.
- **Live**: the open view re-reads every 15 s while the tab is visible (and on returning to it); each part redraws only when its data changed and nobody is typing in it (*review fix 12:* an entrant move repaints Entrants when it lands whatever has focus); a read that fails says so in the status line and tries again; a refused move is shown in words in the page's notice (or inside the drawer).

**API glue (this layer):** `GET /api/brackets` adds `words` (the player-facing templates the page draws, `brackets_view.PAGE_WORDS`), `defaults` (*review fix 4:* a new tournament's options from the registry, `brackets_moves.option_defaults` — what `create` applies — so the form shows a TO who is not staff the same defaults) and per row `entrant_cap` and `to_name`; `GET /api/brackets/{id}` adds `shadow`, `to_name` and `rounds_to_play` (*review fix 9:* Swiss only — the stored rounds, else `swiss.rounds_for` of the field). Every answer and refusal of a bracket write goes through `api/names.site_words` (*review fix 11:* `<#id>` reads `#name`, a thread too). The DQ / drop / remove / override / reset routes take an optional `reason` (whitespace folded, 300 characters) and, on success, call `brackets_thread.tell` — `brackets_dm_dq` / `_dropped` / `_removed` for the entrant, `brackets_dm_decided` (`set`, `result` = the move's words) and `brackets_dm_reset` (`set`) for both players, read before the move — always with `actor=` so an organiser is never told about their own move. `POST /api/brackets/{id}/move` is in `contract.json` (a contract entry may now carry `settings`, written before the request: mode `on`, `brackets_channel_id` = a forum the fixture has).

**Keys:** *(review fixes: no key added; `PAGE_WORDS` gained the five existing `brackets_card_*_words` keys the head meta now reads.)* 10 new player-facing word keys (`BRACKETS_PAGE_WORDS`): `brackets_waiting_play`, `_called`, `_confirm`, `_opponent_confirms`, `_to_decides`, `_waits`, `_next_round`, `_done`, `_out` (each takes `{set}` and `{opponent}`) and `brackets_discord_label`. Every other player-facing word on the page is an existing layer-1/2 key (states, formats, the button labels, round words, set-card lines, the report and dispute words), so Discord and the site share one wording.

## G. Decisions beyond the brief

1. **`brackets_best_of_late`** is a key (and a `best_of_late` column) the brief did not list: "from a chosen round
   onward → 5" needs the 5 somewhere, and `best_of_finals` is the grand final's.
2. **`brackets_best_of_from_round` means "top N"** — the entrants still alive when the set is played (A4) — not a
   round number, because round numbers differ between the two sides of a double elimination; it applies to
   elimination only. ~~(alive computed from the bracket size)~~ *Amended by review fix 2:* alive is who is still
   unplaced when the set's round is played, from n and the sets that eliminate someone, not from the bracket size.
3. **The finals best-of covers single elimination's final too**, not only a grand final.
4. **`brackets_format_default`** is a key: every default is a key, and a create without a format needs one.
5. **Best-of keys are enums of odd numbers** ("1"…"15"), so an even best-of cannot be stored.
6. **`confirmed` is not a resting state** (A7); the opponent reporting the same score is their confirm, a different
   score is refused with the reported one. A reporter's re-report restarts the confirm clock (review fix 12).
7. **`accept`**: a TO who is not playing confirms a reported or disputed score as it stands (`confirmed_how = to`).
8. **Disputes only from `reported`**, by the opponent, never by the TO (who decides instead).
9. **No auto-complete:** when the last set is final the tournament stays `running` until a TO presses Complete
   (round robin and Swiss ties need the TO's order first). `finished` in the view says it is ready.
10. **Every decision has a reverse** (staff final say): open/close sign-ups, check-in in and out, remove ↔ restore,
    drop/DQ ↔ restore, start ↔ unstart (back to seeding, sets cleared — start.gg's phase reset), complete ↔ reopen,
    cancel ↔ restore, a result ↔ reset or override.
11. **Lifting a DQ leaves the forfeits** until the TO resets those sets — reinstating cannot know which result the TO
    wants replayed.
12. **A TO may add entrants past the cap**; the cap stops sign-ups only.
13. **Guests are checked in automatically** when check-in opens (or when added during it).
14. **A member removed by a TO cannot sign themselves back up**; one who left, or was a no-show, can.
15. **Options are editable in every state before the start** (draft, signups, check_in, seeding), not only draft and
    signups — closing sign-ups should not freeze the best-of.
16. **The site's write bucket for brackets is the staff one** (60/min) for every signed-in member, not the member
    bucket (10/min), so a TO with the role but no staff role can run a round.
17. **Log head `brackets` files under `core`** (like `pbfeed`): a feature of its own would need a 26th settings group
    for its log level.
18. **Moves live in three modules** (tournament / entrants / sets) beside the pure package, so the package stays free
    of the database and Discord; `may_run` lives in the package (`brackets/access.py`) because it only reads a
    store and a member.
19. **The drop pattern is the pair flip** (A3), chosen for its proved property rather than copied.
20. **`brackets_panel_minutes` fills the `/settings` panel-minutes select to Discord's 25** (`tests/test_settings_panel.py` now asserts 25). ⚠️ The NEXT feature with a panel needs that select split or paged.
21. **The engine's confirm is `play.confirm_report` and the move `brackets_sets.confirm_report`** — `confirm` is a reserved library-helper name (`tests/test_panels.py::test_no_cog_writes_its_own_copy_of_a_library_helper`).
22. **Only player-facing words are settings keys** (owner, 2026-10-07, verbatim "bb"); organiser lines are
    `TO_WORDS` constants. Three of the reviewer's 33 "TO-only" strings were kept as keys because a plain member can
    receive them: `checked_out` (a member may check themselves out), `no_set` (a member reporting, confirming or
    disputing a set key that does not exist, through the site), `not_in_bracket` (a member dropping or checking in an
    entrant id that does not exist, through the site).
23. **`Outcome` gained `changed` and `gone`** (`panels.Outcome`, defaulted, so no other feature changes) rather than a
    brackets-only subclass — one answer type both doors read.
24. **A correction that keeps the winner keeps what it fed in elimination too**, not only Swiss (review fix 4 named
    Swiss and round robin): the same bug shape — a corrected W1 score wiped an already-played W2 — and the same fix.
25. **The Swiss round limit is n − 1 for odd fields too**, as the review asked, though an odd field with byes could
    in principle carry n rounds; the simpler, stricter rule refuses fewer real cases than it would complicate.
26. **An unreadable stamp is logged once by acting on it at once**: the sweep that finds it closes the check-in or
    lets the report stand in the same tick, so the warning cannot repeat.

**Layer 2 (branch `brackets-discord`, 2026-10-07):**

27. **The thread is made when the tournament is created** (the brief), not at the first Open sign-ups (the old §E): the
    draft's starter card is where its options can be read before anyone signs up. In shadow that is the rehearsal home.
28. **A card's buttons depend on state only** — a posted message is the same for every viewer — and who may press is
    decided on the press, in words. The organiser buttons on a card (Call, Decide…, Reset…) therefore show to
    everyone and refuse a player; the panel, which IS per viewer, hides what the viewer cannot do (Confirm from the
    reporter, every organiser move from a member).
29. **Only player-facing words are keys** (decision 22 carried into layer 2): 63 word keys; organiser words are
    constants.
30. **The website's writes follow too** (`api/tools/brackets.py` `answered` ~~awaits `brackets_thread.follow`~~ *starts
    `follow_later` and waits at most 1.5 s — review fix 7, decision 50*), so the thread never lags the site; layer 1's
    routes and refusals are unchanged.
31. **The starter card carries the game, the option words and the top 8 placings when complete**, and not the old
    §E's "bracket as text" — the set cards are the bracket in the thread, and the page is the drawing.
32. **A follow edits, a reconcile re-posts** (the brief): a follow that finds a card gone marks it, the next tick posts
    it again.
33. **A half-posted card is adopted, not doubled.** `card_at` is written with no id before the send; a restart in that
    gap leaves "may have been posted", and the card is looked for by its custom-id prefix before posting. This is the
    one search of the thread; the old §E's "never by searching" holds for everything else.
34. **The boot reconcile is full, the minute tick is cheap.** Boot edits every live starter card and stored card (that
    edit IS the check that the id resolves); the tick only acts on what is missing or marked~~, so a running bracket costs
    no Discord call a minute when nothing changed~~. *(Amended by review fix 4, 2026-10-07: the boot pass is the loop's
    first tick, not `on_ready`; and the tick reads each live tournament's starter once (`fetch_message`), so a running
    bracket costs ONE Discord read a minute — the price of finding a starter a moderator deleted.)*
35. **Two NotFounds re-make a thread; one NotFound re-posts a message.** A message 404 in a channel the bot can read is
    definitive; a thread that cannot be found might be a cache or permission blip, and re-making it is the visible,
    expensive act (checklist 32).
36. **At most 5 new set cards a pass** (`brackets_thread.POSTS_PER_PASS`, a constant — it is a rate-limit detail, not
    an owner decision): Discord allows about 5 messages per 5 seconds in a channel, so a 64-entrant start posts its 32
    first-round cards over about seven minutes. Edits are not budgeted.
37. **Rehearsal is a property of the thread, not of the mode now** (checklist 3): a tournament whose thread was made in
    shadow never pings or DMs anyone, even after `brackets_mode` goes `on`. A DM is sent only when the mode is `on`
    AND the thread is not a rehearsal. *(Amended by review fix 2: the same rule — `live` — now governs the set cards'
    mentions and the start ping too; before, a card pinged in an `on`-made thread after the mode went `shadow`.)*
38. **What is DM'd:** remove, DQ, an organiser's drop, Decide / a forfeit / an organiser's report on someone else's
    set (both players), and Reset (both players), each with the organiser's optional reason. Not DM'd: a check-in
    no-show (the starter card says check-in closed), *Let it stand* (the score the player saw stands), Call (the card
    says it).
39. **Leave is refused while a tournament runs** — `brackets_people.drop` on a running bracket forfeits the rest, and a
    stale Leave button must never do that; a player leaves a running bracket with **Drop out** on the panel, which asks
    first. *(Review fix 11: before the start Leave is OFFERED wherever layer 1 allows it — draft and seeding too — on the
    card while anyone is in, on the panel to an entrant.)*
40. **Complete, Reopen, Cancel and Restore re-render every card**, so a finished or cancelled tournament's cards lose
    their buttons and a restored one gets them back.
41. **A carded set that falls back to waiting loses its card id**, so when it is ready again a new card pings the two
    players again (the old card says it was cleared). *(Review fix 8: only once the clear landed or 404'd.)*
42. **Failure rows are written once per tournament, card and reason a run**; ~~the log line is every time~~ *(review
    fixes 3 and 13: the warning is once too; repeats are DEBUG)*. Shadow with no rehearsal home and no log channel
    writes no row (nowhere to rehearse, nowhere to post the row) and warns once per tournament a run.
43. **`/bracket` hides while `brackets_mode` is `off`** (`HIDDEN_WHEN_OFF`); the `/settings` mode block reads
    *Tournament brackets*. `test_settings_panel`'s counts (24 modes, 20 hideable) and `test_command_visibility`'s table
    moved with it.
44. **Seeding from Discord is a form**: every active entrant on a line as `Name #id`, top seed first; the move refuses
    an order that is not everyone exactly once. Shuffle is a button.
45. **Call ready sets calls every ready set** (one `set_called` row each), the way a TO calls a round.
46. **The forms double as the confirmation** for Remove, DQ, Drop, Decide, Reset and a forfeit (dismissing the form is
    *Keep it*); Cancel, Back to seeding and Drop out — no form to hang it on — ask first.
47. **The card buttons' custom ids** are `brackets:<id>:<action>` and `brackets:<id>:<set>:<action>` (fullmatched
    templates, at most 100 characters).
48. **The chat model's command block names `/bracket`** (`personas.py`), as `test_personas` requires of every member
    command.

**Layer 2 review fixes (2026-10-07):**

49. **Move to #knuck-up asks first** (Keep it / Move to #knuck-up) on the panel — it is public and it pings, and there is
    no form to hang a confirmation on. The panel shows it to staff only while the mode is `on`; the move itself refuses
    in words otherwise (the API, a stale panel).
50. **The website's write waits up to 1.5 s for its follow, then answers** — not zero. A small move answers with its cards
    already caught up; a long one answers at 1.5 s and the follow carries on (Cloudflare's cut-off is 100 s). It also
    keeps a test client, whose event loop lives one request, from closing under a follow mid-write — measured: with no
    wait at all, the follows the TestClient abandoned left the shared test database answering later requests wrongly
    (three `tests/api/tools/test_brackets.py` tests failed).
51. **One Discord read a minute per live tournament** for the starter check (decision 34 amended): finding a deleted
    starter within a minute was the finding; set cards are still only checked by the full pass.
52. **A forfeit-filled set's card mentions the walkover winner only** — it is the one who has something to do; the DQ'd
    player is already told by the DQ's DM.
53. **Failed edits and clears are remembered in memory** (`stale`, `clears`), not in the database: a restart's first
    tick is the full pass, which edits every stored card anyway, so nothing is lost but one retry.
54. **Leave on the card shows only while someone is in** — a draft with no entrants does not grow a Leave button nobody
    can use.
55. **`POST /api/brackets/{id}/move` is not in `contract.json` yet**: the contract test answers every listed route 200
    against `seed_brackets`, and a 200 here needs the mode `on`, a rehearsal row and a channel that can hold a thread in
    the API fixture. Layer 3 adds it when the page reads it; the mock already answers it.

**Layer 3 (branch `brackets-site`, 2026-10-07):**

56. **The page's player words reach a member through `GET /api/brackets` `words`**, not `/api/settings` (staff-only): the
    templates, unfilled, for the keys in `brackets_view.PAGE_WORDS`. Organiser words on the page are constants (the
    owner's "bb").
57. **Ten new word keys only**: the nine `waiting_on` words and *In Discord*. Every other player-facing word reuses a
    layer-1/2 key (Sign up, Leave, Check in, Drop out, Report, Confirm, Dispute, states, formats, rounds, set-card
    lines), so a staff edit changes Discord and the site together.
58. **The list and the view carry `to_name`** (the organiser's display name from the guild), and the list `entrant_cap`:
    a member cannot call `/api/ref/names`.
59. **The view carries `shadow`**, so the page can offer Move to #knuck-up exactly when the panel does.
60. **Members see no drafts and no cancelled tournaments in the list** (the panel's member view shows only live ones);
    a draft's link still opens for anyone.
61. **Randomise is client-side and saved with Save seeding**, so a shuffle can be looked at and dragged further before it
    lands (Discord's Shuffle saves at once).
62. **Seeding is drag-and-drop by a handle, plus ArrowUp/ArrowDown on the handle** — the keyboard path costs nothing and a
    drag-only control is not reachable without a pointer.
63. **Add a member by picker is staff-only**: `/api/ref/members` is a staff route; a TO with the role but no staff role
    adds guests by name (or members sign themselves up).
64. **The reason routes read the set's players BEFORE the move** and tell after success; a refused move tells nobody.
    An organiser's plain Report on someone else's set from the site is NOT DM'd (the brief named DQ / drop / remove /
    override / reset; Discord's Report form does DM `_decided`) — §H.
65. **Let it stand only when the organiser is not playing in the set**: playing, their confirm is the opponent's.
66. **The drop line is not drawn**: lines follow `winner_to` only; who drops where is in the set cards and Discord.
67. **A void grand-final reset is not drawn**; the reset set shows while it may still be played. *(Widened by review fix 2: no set nobody will play is drawn — decision 73.)*
68. **The bracket, the head card and the list are full width** (`data-span="full"`); the two-column layout would squeeze
    the tree. The tree scrolls inside its section so the page never scrolls sideways.
69. **Poll every 15 s while visible**, redraw a part only when its data changed and nobody types in it, ~~and skip the
    Entrants part while a seeding order is unsaved~~ *(never what ran — it redrew; review fix 1: the unsaved order is
    reconciled on every redraw, decision 74)*; a change of shape (state, sets appearing) reloads the view.
70. **A contract entry may carry `settings`**, written before its request in both halves (`test_contract.py`,
    `check.mjs`); the per-test rewind puts them back. Used only by the move route (decision 55 resolved).
71. **The mock plays brackets for real** (`site/mock/brackets.mjs`): builds with byes and the pair-flip drops, the reset
    set, round robin, Swiss pairing, resets that take back what they fed, withdrawals and standings; the report route
    honours who reports. Seed ids 1–8 are unchanged for the contract; 9–14 add a running double elimination of 8 with a
    reported and a disputed set, a round robin, a Swiss, a rehearsal (12), a finished double elimination and a seeding
    field of 6.
72. **The mock's `brackets_channel_id` default and its fixture ids are strings** — as numbers they lost precision
    (1076005097617760296 read as …300), which made the Settings row look changed on load.

**Layer 3 review fixes (2026-10-07):**

73. **A set is drawn only if someone will play it.** Byes and void sets are never cards, and neither is a waiting set
    whose feeders can only bring it one player or none — predicted at the start, so a 5-player double elimination's
    L1-1 (fed by W1-1's bye and W1-2) is never drawn as a card that later vanishes. Measured: against the Python engine
    at 3, 5, 6, 7, 9, 12, 13 and 17 entrants in both formats, the prediction equals what ends `bye`/`void`.
74. **An unsaved seeding order meets a fresh read by `seedOrderWith`**: its order kept, leavers dropped, joiners last.
    The poll still redraws Entrants (a member's sign-up must show), except while a row is mid-drag.
75. **The tree squeezes before it scrolls, and fades when it must scroll** (both of the review's options): squeezing to
    140 px fits 6 columns at 1280; a phone cannot fit a tree at all, so the fade is what tells it more is there. The round
    labels sit at the top of the tree and scroll with their column.
76. **40 px on phones, not 44**: the brief's floor; the shared buttons are lifted by `brackets.css` for this page only
    (`#dash .btn`, `.drawer .btn`, `.ask .btn` under 700 px), so no other page changes.
77. **The create form's defaults ride on `GET /api/brackets`** rather than a new route, beside `words`; a blank
    check-in box is not sent, so the server's own default applies (no code constant anywhere — checklist 33).
78. **The head meta uses the starter card's option words**, so a staff edit of `brackets_card_*_words` changes Discord
    and the site together; the finals best-of shows only when it differs from the Bo, as on the card.
79. **`site_words` moved to `api/names.py`** (shared by sticky and brackets) and looks threads up with
    `get_channel_or_thread`; a channel the guild does not have reads *a channel Discord no longer has (id)*. The mock
    names a moved tournament's new thread after the tournament (its threads are not in the mock's channel list).
80. **Compact standings are a second drawing of the same rows**, swapped by CSS at 700 px, not a second source.
81. **Once complete, the place leads an entrant row** and the placement badge is not drawn beside it.
82. **`check.mjs` restores a contract entry's settings in a `finally`**, read back from `GET /api/settings` first.


## H. What is NOT built (and is not in L2/L3 either unless the owner asks)

Pools into a bracket (phases, progressions), teams and crews, stations and streams, entry fees and payouts, series
or circuit points, ladders and matchmaking, the start.gg mirror (only the `source` column exists), DE's optional
5th-place set, per-game reporting (characters, stages), the DQ timer (auto-DQ when a player does not check in to a
called set), conflicts and waves, printing.

**Not built in layer 2** (the old §E or the brief named them; each is a small follow-up): ~~the staff **Move to
#knuck-up** button for a thread made in shadow~~ *(built by the layer-2 review fixes, §E)*; the **Complete** tie-order select for a round robin or Swiss tie
(Complete places a tie as shared); editing a tournament's options from Discord (the site's `PATCH` does it); archiving
or locking the thread when a tournament completes or is cancelled; a per-tournament ping role (one global
`brackets_ping_role_id`); a DM to a check-in no-show; the reason field on the website's DQ / drop / remove / override /
reset ~~(layer 3 — §F)~~ *(built by layer 3)*. A forum channel as the parent is coded but no test exercises it.

**Not built in layer 3:** the **Complete** tie-order picker on the site (Complete places a round robin or Swiss tie as
shared, as on Discord); changing the organiser (`to_user_id`) from the page; editing a set's best-of; a DM when an
organiser's plain Report decides someone else's set from the site (decision 64); a time-zone picker on the page (times
are the viewer's device zone, as the tracker reads by default); ~~rendering `<#id>` mentions inside a move's sentence
(the Move answer shows the raw `<#…>`)~~ *(built by the layer-3 review fixes, decision 79)*; the `/settings` and Settings
pages showing the ten new keys were not opened in a browser.

## Review fixes 2026-10-07

An independent review of layer 1 found no blocker. Each finding, what changed, and the test that pins it ("seen
failing" = run against the code before the fix and watched fail).

| # | Finding | What changed | Pinned by (seen failing first?) |
|---|---|---|---|
| 1 | Swiss silently pairs rematches when `swiss_rounds` > n − 1 | `play.build` refuses `too_many_rounds` in words; `swiss.pair_round` sets `rematch` on a forced repeat; `rematch` column, view field, every `set_*` log row | `tests/brackets/test_swiss.py::test_more_rounds_than_the_field_can_carry_without_a_rematch_is_refused`, `::test_a_forced_rematch_is_flagged_on_the_set`, `tests/test_brackets_moves.py::test_a_swiss_start_with_more_rounds_than_the_field_can_carry_is_refused`, `tests/test_brackets_sets.py::test_a_forced_swiss_rematch_shows_in_the_view_and_on_every_set_row` (all yes) |
| 2 | "Top N" was structural; W2's alive disagreed with L2's | `alive` = who is still unplaced when the round is played (`play.pace` over a rehearsal); `winners_alive`/`losers_alive` removed; the losers side of a full bracket unchanged | `tests/brackets/test_elimination.py::test_alive_is_who_is_still_unplaced_when_the_round_is_played` (n = 2…33, 48, 64, single and double; yes), `::test_top_six_of_eight_plays_winners_round_two_long_like_the_losers_round_beside_it` (b; yes), `::test_a_full_bracket_keeps_the_losers_side_numbers_of_the_design_tables` (passes before and after), `::test_top_eight_of_nine_starts_once_nine_are_down_to_eight` (a; **passed before** — see note), the locked-in `W2-1 == 16` assertion changed to 12 |
| 3 | No idempotent id for the per-set card | `tournament_sets.message_id`, `card_at` (schema-90 hunk); `brackets_store.cards`/`set_card`; view fields; `Outcome.changed`/`gone` on every move; §E rewritten | `tests/test_brackets_store.py::test_a_set_card_is_kept_across_saves_until_the_set_is_removed`, `tests/test_brackets_view.py::test_each_set_shows_its_card_and_whether_it_is_a_rematch`, `tests/test_brackets_moves.py::test_start_and_back_to_seeding_say_which_sets_changed` (yes) |
| 4 | A Swiss score correction that kept the winner wiped every later round | `play.kept_winner`: same winner → only that set changes (every format); a flip still re-pairs | `tests/brackets/test_swiss.py::test_correcting_a_score_without_changing_the_winner_keeps_the_later_rounds` (yes), `::test_flipping_the_winner_still_re_pairs_every_later_round` (passes before and after), `tests/brackets/test_play.py::test_correcting_an_elimination_score_without_changing_the_winner_keeps_what_it_fed` (yes), `::test_a_round_robin_correction_touches_that_set_either_way` |
| 5 | `restore_entrant` while running made a ghost | refused in words (`not_in_bracket`) unless the entrant is in the bracket | `tests/test_brackets_people.py::test_someone_out_before_the_start_cannot_be_put_back_into_a_running_bracket` (yes) |
| 6 | Dead `brackets_not_entrant_said`, `brackets_store.in_bracket` | both removed | the key count (registry, contract, labels, mock) |
| 7 | A Discord `<t:…>` token reached the site | `clock_words`: Discord gets `<t:…:t>`, the site a plain time in `default_timezone` (the mock too) | `tests/test_brackets_people.py::test_check_in_opening_tells_the_website_a_plain_time_and_discord_a_timestamp` (yes) |
| 8 | `started` over-counted (void G2-1, waiting sets) | `play.sets_to_play`: the sets certain to be played, *up to* N with a reset | `tests/brackets/test_play.py::test_the_sets_to_play_counts_only_sets_that_are_played`, `tests/test_brackets_moves.py::test_started_counts_only_the_sets_that_will_be_played` (yes) |
| 9 | After Complete, Reset/Override gave the generic wrong-state line | `brackets_sets.correctable`: *is complete. Reopen it first, then change {set}.* (organiser checked first) | `tests/test_brackets_sets.py::test_after_complete_a_correction_says_to_reopen_first` (yes) |
| 10 | Unparseable `reported_at` / `check_in_closes_at` never came due (checklist 5) | due now, logged (once, because it is acted on in the same tick); a naive stamp reads as UTC | `tests/brackets/test_play.py::test_a_report_with_an_unreadable_time_stands_at_the_next_sweep`, `tests/test_brackets_people.py::test_a_check_in_with_an_unreadable_closing_time_closes_at_the_next_sweep` (yes) |
| 11 | `said()` caught three exception types (checklist 17) | catches `Exception`, logs, falls back | `tests/test_brackets_moves.py::test_a_staff_wording_that_breaks_in_any_way_falls_back` (yes) |
| 12 | Re-report and the confirm clock (doc); stale seeds after Back to seeding | §A7 and decision 6 say re-reporting restarts the clock; `start` writes seeds for the players then everyone else, so no two rows share a seed | `tests/test_brackets_moves.py::test_back_to_seeding_leaves_every_entrant_a_seed_of_their_own` (yes) |
| 13 | Wording fold (owner: "bb") | 31 keys out of the registry, mock rows, `labels.js`, `contract.json` (30 folded into `TO_WORDS` + the dead one); 3 reclassified as player-facing (decision 22) | `site/mock/check.mjs` (*171 core settings, all keys present*), `tests/api/test_contract.py`, the moves tests that read the folded lines |
| 14 | Missing tests: simultaneous different reports; a differing second report through the moves and the API | added (they pass on the existing lock and decision 6 — no code change) | `tests/test_brackets_sets.py::test_two_different_reports_at_once_leave_one_and_refuse_the_other`, `::test_a_second_report_that_differs_is_refused_and_the_same_one_confirms`, `tests/api/tools/test_brackets.py::test_a_differing_second_report_is_refused_with_the_score_already_reported` |

⚠️ **Finding 2(a) did not reproduce as stated.** The review said 9 entrants are down to 8 after W1 and L1; measured
by playing it out, they are still 9 — the one W1 loser meets a bye in L1 and is first eliminated in L2. So W2 and L2
playing Bo3 under "top 8" was correct, and L3/W3 on Bo5 is what the old and the new rule both give. The pin asserts
that, and the property test (`…_is_who_is_still_unplaced…`) is what catches the real defect, 2(b), at every size.

## Review fixes (layer 3) 2026-10-07

An independent review of layer 3 used the page in headless Chrome at 375×812 and found no blocker. Each finding, what
changed, and what pins it ("seen failing" = the pin run against `498f44ee`, the code before the fix, in a throwaway
worktree, and watched fail; "harness" = measured in headless Chrome against the branch's mock, not committed).

| # | Finding | What changed | Pinned by |
|---|---|---|---|
| 1 | An unsaved seeding order hid a newcomer; Save refused with no visible cause | `seedOrderWith` on every redraw, drop, key move, Randomise and Save; §G 69 struck, decision 74 | `site/mock/brackets.test.mjs` (*an unsaved order keeps its moves and puts a new entrant last*, *…drops whoever left*, *…names everyone in exactly once*); harness: on #14 a drag, a guest added behind the page, the poll → 7 rows with Newcomer last, Save → *Seeding for Third Strike Open is saved.* and the saved order matches |
| 2 | A bye was a card that opened an empty drawer; void sets drawn | `unplayedSets`; `eliminationLayout` draws none of them, compacts empty rounds and lifts each side to its first row; a Swiss bye is a plain line; `setCard` treats `bye` as quiet | `brackets.test.mjs`: 5, 6, 7, 12 entrants × single/double × start / part played / played out (no bye or void drawn, every played set drawn, no empty column, no shared spot, lines between drawn sets only), the 5-player single and double cases by key, and *what the start leaves out is exactly what turns out a bye or void* at 3, 5, 6, 7, 9, 12, 13 (measured on `498f44ee`'s `eliminationLayout`: 3, 2, 1, 4 bye/void cards for single at 5, 6, 7, 12 and 4, 2, 1, 4 for double). Harness: a 5-player double elimination made on the mock draws W1-2, W2-1/2, W3-1, L2-1, L3-1, L4-1, G1-1, G2-1 — no W1 bye, no L1 |
| 3 | Phone taps under 32 px | `brackets.css` under 700 px: every move 40 px | harness at 375 (all measured W×H): head moves 40 tall; score picks 56×40; Report 75×40; Confirm 84×40; Dispute 81×40; Decide 62×40; Let it stand 85×40; Call 44×40; forfeits 99–130×40; Reset 54×40; Close 55×40; DQ… 50×40; Drop… 61×40; DQ 40×40; Keep 51×40; Remove… 79×40; Randomise / Save seeding / Discard 86 / 99 / 66 ×40; drag handle 40×40; results-grid cell 40×40; *your line* 112×40 |
| 4 | A TO who is not staff got code constants in New tournament | `GET /api/brackets` `defaults` (`brackets_moves.option_defaults`, shared with `create`); the form reads only that; a blank check-in is not sent | `tests/api/tools/test_brackets.py::test_the_list_carries_the_registry_defaults_a_new_tournament_starts_with` (read as the TO, not staff; seen failing) |
| 5 | Entrant rows wrapped raggedly at 375 | under 700 px: seed · name on one line (ellipsised), the note wraps, actions on their own line | harness: every #14 and #9 row is one 20 px name line with its actions on the line below (rows 108–126 px; 126 where the note wraps) |
| 6 | Complete tournaments printed the seed beside a place order | `entrantLine({ placed })`: the place leads, `seed n` in the note, no duplicate badge | harness: #13 reads 1st Casey *seed 1* · 2nd Juno *seed 8 · guest* · 3rd Nick *seed 2* … |
| 7 | Standings stacked 2–4 lines per player on a phone | `compactStandings` under 700 px | harness: #10 rows *1st Moth / games 2–1 / 1–0*, 60–61 px each; #13 41 px; the table still shows at 1280 |
| 8 | 8-player DE clipped at 1280 with a thin scrollbar as the only hint | squeeze to fit (`treeSize`) AND a fade when it still overflows (decision 75); redraw on resize | `brackets.test.mjs` (*fits keeps full size*, *943 px squeezes to fit*, *a phone never squeezes under the floor*); harness: #9 at 1280 → 943 px of room, 140 px cards, scrollWidth = clientWidth (no clip); at 1600 → 188 px cards; resized 1600→1280 → redrawn at 140; at 375 → 140 px cards, scrolls, `data-more="right"` |
| 9 | Swiss meta read "auto rounds" from a split string | `rounds_to_play` on the view, `brackets_card_rounds_words` | `tests/api/tools/test_brackets.py::test_a_swiss_says_the_rounds_the_engine_will_play` (5 entrants → 3; stored 2 → 2 after the start; single → null; seen failing); harness: #11 reads *Swiss · Bo3 · 3 rounds* |
| 10 | `check.mjs` never restored an entry's settings | read first, PUT back in a `finally` | `node site/mock/check.mjs` ok (345 routes); not a failing-first pin — the move entry is still last |
| 11 | `<#id>` showed raw on the site | `site_words` moved to `api/names.py`, threads too, every bracket answer and refusal; the mock the same | `tests/api/tools/test_brackets.py::test_a_channel_in_a_bracket_sentence_reads_as_its_name_on_the_site`, `tests/api/test_names.py::test_site_words_names_a_channel_or_a_thread_and_says_when_one_is_gone` (both seen failing); §H item struck |
| 12 | The inline reason row stayed stale after a DQ when focus stayed in it (Safari) | `entrantMove` repaints Entrants with `force` after any entrant move lands | harness: on #9 focus held in Dax's reason box, DQ pressed by `click()` (focus does not move) → the row reads out with only Restore |

**Deltas:** registry keys 1075 → **1075** (none added; `PAGE_WORDS` +5 existing keys); routes 345 → **345**; `GET
/api/brackets` + `defaults`; `GET /api/brackets/{id}` + `rounds_to_play`; `contract.json` reads `defaults`,
`rounds_to_play` and the sets' `loser_to` (the page reads it now).

## Review fixes (layer 2) 2026-10-07

An independent review of layer 2 found no path from a thread made in shadow to a real channel; its findings were about
identity, agreement between paths and operational honesty. Each finding, what changed, and the test that pins it ("seen
failing" = run against the code before the fix and watched fail; "mutation" = the fix reverted on purpose and the pin
watched fail).

| # | Finding | What changed | Pinned by (seen failing first?) |
|---|---|---|---|
| 1 | A deleted starter was "re-posted" by adopting the oldest bot message — a set card, or on real Discord the uneditable `pins_add` notice | `is_starter` / `adopt_starter`: only the bot's own `MessageType.default` message carrying this tournament's starter custom id or its title, never one with a set custom id; else a fresh starter, pinned. The fakes gained `MessageType`, a pin notice and Discord's 50021 refusal to edit it | `tests/test_brackets_thread.py::test_a_deleted_starter_is_posted_fresh_and_never_adopts_a_set_card`, `::test_a_pin_notice_is_never_taken_for_the_starter` (both yes); `::test_a_starter_the_restart_lost_is_adopted_by_its_own_buttons` (passes before and after — adoption still works) |
| 2 | Three "live" predicates disagreed: a thread made `on`, mode flipped to `shadow`, start → the card pinged real members while DMs logged `would_dm` | ONE `live(bot, guild, row)` (mode `on` AND not made in shadow) for cards, the start ping and DMs. **Move to #knuck-up** built (staff; panel and `POST /api/brackets/{id}/move`), §E; removed from §H. New key `brackets_moved_line`, new kind `brackets.thread_moved` | `tests/test_brackets_thread.py::test_a_thread_made_on_pings_and_dms_nobody_once_the_mode_is_not_on`, `::test_staff_move_a_rehearsal_to_knuck_up_with_its_starter_and_open_cards`, `::test_the_move_is_refused_in_words_unless_staff_on_and_a_rehearsal`, `::test_a_move_whose_thread_cannot_be_made_moves_nothing`, `tests/test_brackets_panel.py::test_only_staff_see_the_move_and_it_moves_the_rehearsal_into_knuck_up`, `tests/api/tools/test_brackets.py::test_the_move_into_knuck_up_is_staff_only_and_refused_in_words_while_shadow` (all yes) |
| 3 | A thread the bot cannot read was invisible to staff and logged every tick | `find_thread` words a `Forbidden` as a permission and anything else as "could not be reached"; `ensured` writes it through `failed` — row and warning once per tournament and reason a run | `tests/test_brackets_thread.py::test_a_thread_the_bot_may_not_read_is_written_down_once_as_a_permission`, `::test_a_thread_discord_could_not_return_is_never_called_a_permission` (yes) |
| 4 | The boot reconcile was skipped (the loop's first cheap tick took the lock before `on_ready`); the cheap tick never checked the starter | The cog's first tick after a boot, and the first after a reconnect's `on_ready`, is the full pass (`full_due`); `on_ready` no longer reconciles. The cheap pass checks the stored starter id (`resolves`, `fetch_message`) and reposts on a 404 | `tests/cogs/community/test_brackets.py::test_the_first_tick_after_boot_is_the_full_pass`, `::test_a_reconnect_makes_the_next_tick_a_full_pass_again`, `tests/test_brackets_thread.py::test_the_minute_tick_finds_a_starter_card_deleted_while_nobody_looked` (yes) |
| 5 | An entrant's Restore from the panel re-edited every card | The panel passes `restore_entrant` (as the API door already did) | `tests/test_brackets_panel.py::test_restoring_one_entrant_from_the_panel_edits_no_set_card` (yes) |
| 6 | `would_dm` carried no text or reason; `dm_failed` dropped the reason | both carry `text` and `reason`; `dm_failed` also `why` | `tests/test_brackets_thread.py::test_a_would_dm_and_a_failed_dm_carry_the_words_and_the_reason` (yes) |
| 7 | A website write awaited the whole follow inside the request | `follow_later` (a tracked task, failure logged); the request waits at most 1.5 s for it (decision 50) | `tests/api/tools/test_brackets.py::test_a_website_write_answers_before_the_thread_catches_up` (yes — timed out at 5 s), `::test_a_follow_that_fails_never_reaches_the_request` (passes before and after) |
| 8 | A non-404 failed clear dropped the id; the card kept live buttons and a second card came later | the id is dropped only when the clear landed or 404'd; otherwise `stale`, cleared again next tick; a removed set's failed clear is kept in `clears` | `tests/test_brackets_thread.py::test_a_clear_that_fails_for_any_reason_but_404_keeps_the_card_it_could_not_clear`, `::test_a_clear_that_failed_is_tried_again_by_the_next_tick` (yes) |
| 9 | A set that filled already forfeited never got a card | `owed`: one card in its final state, mentioning the walkover winner | `tests/test_brackets_thread.py::test_a_set_that_fills_already_forfeited_gets_its_final_card_once` (yes) |
| 10 | Report/Dispute/Decide/Reset forms opened while `off` | `off_now` before every form (the cards' and the panel's) | `tests/test_brackets_buttons.py::test_no_set_form_opens_while_the_mode_is_off`, `tests/test_brackets_panel.py::test_a_form_never_opens_while_the_mode_is_off` (yes) |
| 11 | Leave was legal in draft/seeding but never offered | offered wherever legal (before the start) — on the card while anyone is in, on the panel to an entrant | `tests/test_brackets_panel.py::test_leave_is_offered_and_works_wherever_it_is_legal[draft]`, `[seeding]` (yes); `tests/test_brackets_cards.py::test_the_starter_card_offers_only_the_member_moves_legal_now` (table changed), `::test_leave_is_offered_wherever_it_is_legal_and_only_while_someone_is_in`, `tests/test_brackets_buttons.py::test_leave_from_the_starter_card_works_while_seeding` (written after the card change) |
| 12 | A TO deciding their own set DM'd themselves | `tell(..., actor=)` skips the actor | `tests/test_brackets_buttons.py::test_an_organiser_deciding_their_own_set_is_not_told_about_it` (yes) |
| 13 | The empty rehearsal home warned on every follow and tick | warned once per tournament a run (`told_once`) | `tests/test_brackets_thread.py::test_the_empty_rehearsal_home_is_warned_about_once` (mutation) |
| 14 | `ON`/`SHADOW` re-declared in the thread module | `brackets_moves`: `OFF, SHADOW, ON = BRACKETS_MODES`, imported | `tests/test_brackets_thread.py::test_the_modes_have_one_home` (yes) |
| 15 | The panel's set lines hard-coded `{a} v {b}` | `brackets_set_card_players` with plain names | `tests/test_brackets_panel.py::test_the_panels_set_lines_use_the_players_line_staff_can_edit` (yes) |
| 16 | No test noticed "any exception is gone" | only a 404 is gone; anything else is `card_failed` once, kept, and retried next tick (`stale`) — for set cards and the starter | `tests/test_brackets_thread.py::test_a_card_edit_refused_for_any_reason_but_404_is_kept_and_tried_again` (yes on the retry; **mutation**: `except Exception` → gone fails it), `::test_a_starter_edit_refused_for_any_reason_but_404_is_kept_and_tried_again` (yes) |

**Deltas:** registry keys 1064 → **1065** (`brackets_moved_line`; `contract.json` `core_keys` 235 → 236, the mock row,
`BRACKETS_KEYS`, `labels.js`); routes +1 (`POST /api/brackets/{id}/move`, real and mock; not in `contract.json`,
decision 55); log kinds +2 (`brackets.thread_moved`, `web.brackets.thread_moved`, IMPORTANT); `would_dm`/`dm_failed`
gained `text`, `reason` (and `why`); `thread_failed` can carry `error`.

## Gate — layer 3 review fixes (2026-10-07, branch `brackets-site`, code at `ac950d33`)

- `python -m pytest tests -q -p no:cacheprovider -n 8`: **12556 passed, 1 skipped** (+4 on the layer-3 gate's 12552).
- `python -m ruff check .`: all checks passed.
- `MOCK_PORT=8818 node site/mock/check.mjs` against the branch's own mock: *ok - 26 pages, 345 routes, 246 core settings,
  all keys present*.
- Every `site/mock/*.test.mjs` (14): exit 0.
- `scripts/ci-local.ps1`: **CI MIRROR GREEN: 16 step(s) passed in 203s** (code at `ac950d33`).
- Browser: headless Chrome (CDP, device emulation), the mock on 8818 — 375×812 for #14, #9 (staff, and the member Moth
  through `?as=member`), #10, #11, #13 and a 5-player double elimination made on the page's API; 1280 and 1600 wide for
  #9 and #13. Page width 375 = scrollWidth on every page at 375 (no sideways scroll). Measured figures are in the table
  above. No console errors or exceptions.

## Gate — layer 3 (2026-10-07, branch `brackets-site`)

- `python -m pytest tests -q -p no:cacheprovider -n 8`: **12552 passed, 1 skipped** (main at `7850359b`: ~12536).
- `python -m ruff check .`: all checks passed.
- `MOCK_PORT=8816 node site/mock/check.mjs` against the branch's own mock: *ok - 26 pages, 345 routes, 246 core settings,
  all keys present*.
- Every `site/mock/*.test.mjs` (14, the new `brackets.test.mjs` included): exit 0.
- `scripts/ci-local.ps1`: **CI MIRROR GREEN: 16 step(s) passed in 150s** (the new *Brackets drawing* step included).
- Browser (Chrome, the mock on 8816, desktop width only): list as staff and member; a double elimination of 8 drawn with
  its lines, a reported and a disputed set; staff reported W2-1 2–1 from the drawer; the member (Moth) confirmed W2-2
  and dropped into L2-1; the member signed up to Knuck Up 13; staff dragged Remy to seed 1 and saved; the New
  tournament drawer created a Swiss; Move to #knuck-up with the mode on; round robin grid and Swiss rounds drawn; no
  console errors. ⚠️ **Phone width NOT checked**: the browser window could not be resized (it stayed 2498 CSS px) and the
  page refuses to be framed.

## Gate — layer 2 review fixes (2026-10-07, branch `brackets-discord`, code at `eba050d1`)

- `python -m pytest tests -q -p no:cacheprovider -n 8`: **12536 passed, 1 skipped** (the layer-2 build: 12502).
- `python -m ruff check .`: all checks passed.
- `MOCK_PORT=8815 node site/mock/check.mjs` against the branch's own mock: *ok - 25 pages, 344 routes, 236 core
  settings, all keys present*.
- Every `site/mock/*.test.mjs` (13): exit 0 (with the mock up on 8815).
- `scripts/ci-local.ps1`: **CI MIRROR GREEN: 15 step(s) passed in 146s**.
- Not verified by these fixes: the real Discord's `pins_add` notice, its 50021 edit refusal, `fetch_message`'s cost and a
  `Forbidden` from `fetch_channel` are modelled on the library and API docs in the fakes, not observed; the 1.5 s
  grace was not measured against a real 64-entrant Complete; the Move was exercised only against fakes (no real thread
  made under #knuck-up, no real pin); the move route is not in `contract.json` (decision 55).

## Gate — layer 2 (2026-10-07, branch `brackets-discord`, measured on the final code)

- `python -m pytest tests -q -p no:cacheprovider -n 8`: **12502 passed, 1 skipped** (main at `aba3b1ee`: 12326 passed).
  New: `tests/test_brackets_thread.py`, `tests/test_brackets_cards.py`, `tests/test_brackets_buttons.py`,
  `tests/test_brackets_panel.py`, `tests/cogs/community/test_brackets.py`, one test in
  `tests/api/tools/test_brackets.py`; counts moved in `test_settings_store`, `test_settings_panel`,
  `test_command_visibility`, `test_bot`, and `test_logkinds` enumerates the thread module's kinds.
- `python -m ruff check .`: all checks passed.
- `MOCK_PORT=8813 node site/mock/check.mjs` against the branch's own mock: *ok - 25 pages, 344 routes, 235 core
  settings, all keys present*.
- Every `site/mock/*.test.mjs` (13): exit 0 (`schedule.test.mjs` with the mock up on 8813).
- `scripts/ci-local.ps1` (the Docker CI mirror): **CI MIRROR GREEN: 15 step(s) passed in 134s**.

## Gate (2026-10-07, branch `brackets-engine`, measured on the final code)

**Review-fix pass (2026-10-07, on `7d95ccb7` code):** `pytest tests -q -p no:cacheprovider -n 8`: **12315 passed** (no
skips reported this run; the build's run had 3 skipped); `ruff check .`: all checks passed; `MOCK_PORT=8812 node
site/mock/check.mjs`: *ok - 25 pages, 344 routes, 171 core settings, all keys present*; every `site/mock/*.test.mjs`
(13): exit 0. The figures below are the build's, kept for history.


- `python -m pytest tests -q -p no:cacheprovider -n 8`: **12235 passed, 3 skipped** (main before the branch: 11896 passed, 3 skipped; +339 tests).
- `python -m ruff check .`: all checks passed.
- `MOCK_PORT=8809 node site/mock/check.mjs` against the branch's own mock: *ok - 25 pages, 344 routes, 202 core settings, all keys present*.
- Every `site/mock/*.test.mjs` (13): exit 0.

## What was NOT verified

**Layer 3 review fixes:**

- Phone checks are Chrome's device emulation, not a phone: Safari (the focus case of fix 12 is simulated with
  `click()`, which does not move focus), real touch drags and iOS's own tap handling were not tried.
- The drag in the seeding check was the keyboard path; a pointer drag at 375 was not repeated.
- A Swiss bye line was not seen in a browser: the mock's Swiss is 6 players, so it has no bye.
- The `/settings` and Settings pages were still not opened to look at the brackets keys.
- The resize redraw was measured on an emulated window resize, not by dragging a real window edge.

**Layer 2:**

- Nothing met the real Discord. Threads, messages, pins, history, interactions and forms are fakes
  (`tests/test_brackets_thread.py`, `tests/test_brackets_buttons.py`); the real library's behaviour for an edit in an
  archived thread, a pin in a thread, `history(oldest_first=True)` and a 429 during a start's burst of cards is assumed
  from the library source and docs, not observed.
- No restart was performed: "a restart between the post and the store" is simulated by clearing the stored id and the
  in-memory state.
- A forum channel as the thread's parent is coded, not tested.
- The `/settings` page and the dashboard Settings page were not opened in a browser to see the 64 new keys render.
- Layer 1's caveats below still stand.

- Nothing met Discord — layer 1 has no Discord code; the thread, cards and panel above are a specification.
- No browser rendered anything — there is no page; the mock answers the shapes only and its player paths are
  simplified.
- The schema change has not run on the live database (only on fixtures: a fresh file and an 89 file).
- start.gg's own drop order and placement numbers are not confirmed from a source (research §3); the engine's are
  derived and tested by hand-worked brackets and by simulation.
- Concurrency is tested for two simultaneous sign-ups and two simultaneous different reports on one set, both
  through `asyncio.gather` in one process — not across two processes (there is only one bot process).
- The card id columns (`message_id`, `card_at`) have no writer yet — layer 2 writes them; only the store round-trip
  is tested.
