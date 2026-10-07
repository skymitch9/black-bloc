# Tournament brackets — the engine, the storage and the API (layer 1), and what layers 2 and 3 build

> **Audience:** the conductor, reviewers, and the agents that build layers 2 and 3 from this page alone.
> **Status:** TRACKED · 🔨 **LAYER 1 BUILT on branch `brackets-engine`** (off `main` `ecd43324`), **NOT merged, NOT
> deployed**; schema **89 → 90**; registry keys **946 → 1031**. **Last verified: 2026-10-07** — by the hermetic test
> suite, `ruff`, `site/mock/check.mjs` against the branch's own mock on port 8809 and every `site/mock/*.test.mjs`
> (figures under *Gate*). ⚠️ **NOT checked:** nothing here has met Discord (layer 1 has no Discord code), no browser has
> rendered anything (there is no page), and the schema change has not run on the live database. Secret NAMES only (none
> here).

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
| **L1** | Pure engine `black_bloc/brackets/`, storage (schema 90), the moves both doors call, the API `/api/brackets`, settings keys, log kinds, contract + mock | 🔨 this branch |
| **L2** | Discord: the tournament thread under `#knuck-up` (or the shadow home), the players' buttons, the TO panel, the two sweeps | not built — spec below |
| **L3** | The site page `brackets.html`: the bracket drawn, the TO's moves, the player's moves | not built — spec below |

## A. The engine (`black_bloc/brackets/`, pure — no database, no Discord)

Every function takes plain data (`Bracket`, `Match`, `Options` in `model.py`) and returns plain data. A move works on a
deep copy and returns `Moved(bracket, changed, removed)`; the caller persists `changed` and deletes `removed`. A refused
move raises `BracketError(code, **fields)`; the caller turns the code into words (`brackets_<code>_said`).

| Module | Does |
|---|---|
| `model.py` | Constants (formats, sides, states, slots), `Options`, `Match` (a set: structure + result), `Bracket`, `BracketError`, `order_key` (play order), `key_of` (`W2-3`, `L1-1`, `G1-1`, `T1-1`, `R3-2`, `S1-4`) |
| `seeding.py` | `bracket_size`, `standard_order` (1 v N, then the halves split), `first_round` (byes to the top seeds), `randomised`, `reordered` (the TO's order) |
| `bestof.py` | `wins_needed`, `fits` (a score finishes the best-of), `checked`, `valid_length` (odd, 1–15), `length_for` (default / late / finals) |
| `elimination.py` | `single`, `double`: every set and its explicit links (`winner_to`/`winner_slot`, `loser_to`/`loser_slot`, `reset_of`), `alive`, structural places, the drop pattern (`drop_target`, `flipped`) |
| `roundrobin.py` | `schedule` (circle method, rounds), `match_count`, `build` |
| `swiss.py` | `rounds_for` (default ceil(log2 n)), `pairings` (score groups, no rematch, backtracking), `pair_round` (bye to the lowest-ranked without one), `next_round_due`, `add_round`, `build` |
| `tally.py` | `records` (sets, games, byes, opponents, who beat whom), `met` (every pair ever paired) |
| `play.py` | `build`, `settle` (byes, voids, forfeits, deliveries, the next Swiss round), the moves `call` / `report` / `confirm` / `accept` / `confirm_due` / `dispute` / `override` / `reset` / `withdraw` / `reinstate`, `downstream`, `finished`, `confirms_at` |
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
its loser finishes):

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
entrants still **alive** plays `best_of_late`; everything else `best_of`. *Alive* (stored per set): winners round 1
= the bracket size; winners round r ≥ 2 = 4 × its sets; an odd losers round = 4 × its sets; a drop round = 3 × its
sets; the grand final = 2; a single-elimination round = 2 × its sets; the third-place set = 4. So "8" means top 8:
in a 16 bracket, W3, L3 and later. Round robin and Swiss play `best_of` throughout. A score fits only when one side
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
backtracks; if no rematch-free pairing exists within a search budget the order is paired top-down. An odd field
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
result answers *nothing to reset*. An override of a `complete` set is a reset plus the new result.

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
  `confirmed_how`, `disputed_by`/`disputed_at`/`dispute_note`, `completed_at`, `placement_winner`/`placement_loser`.
  UNIQUE `(tournament_id, key)`; a save is an upsert on it.

Every write runs under `brackets_moves.lock_for(bot, tournament_id)` (one `asyncio.Lock` per tournament, kept on the
bot) with the unique indexes behind it (checklist 6; `test_two_sign_ups_at_once_leave_one_entrant`).

## C. The moves and the API

The moves are the ONE implementation both doors call (layer 2's buttons and the site's routes); each takes
`via` (default `VIA_DISCORD`), logs ONE row and returns an `Outcome` whose message is a settings key's words.

| Module | Moves |
|---|---|
| `brackets_moves.py` | the shared helpers (`lock_for`, `mode_of`, `said`, `note`, `require_*`, `engine`); `create`, `edit`, `open_signups`, `close_signups`, `seed`, `start`, `unstart`, `complete`, `reopen`, `cancel`, `restore` |
| `brackets_people.py` | `join`, `add_entrant`, `remove_entrant`, `restore_entrant`, `drop`, `dq`, `open_check_in`, `close_check_in`, `set_check_in`, `close_due_check_ins` (sweep) |
| `brackets_sets.py` | `call`, `report`, `confirm`, `dispute`, `override`, `reset`, `confirm_due` (sweep) |
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

## D. Settings (85 keys, all under `core` — `brackets_` would be a 26th `/settings` group)

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

Plus **69 word keys** (`BRACKETS_WORDS`): every success line (`brackets_<move>_said`), every refusal
(`brackets_<code>_said`), the state words (`brackets_state_<state>`), `brackets_forfeit_words`,
`brackets_no_role_words`. Each is checked for its `{fields}` (`TEXT_CHECKS`) and falls back to the shipped wording if a
staff edit cannot be filled. Labels in `site/public/assets/labels.js`; mock rows in `site/mock/server.mjs`.

## E. Layer 2 — Discord (build from this)

- **Shadow routing.** On the first move that opens sign-ups (or a TO's **Post it** on a draft), the cog makes ONE
  thread per tournament: `brackets_mode = on` → a public thread under `brackets_channel_id`; `shadow` →
  `shadow.channel_id(bot, guild, feature="brackets")` (so `brackets_shadow_channel_id`, then `shadow_channel_id`,
  then the log channel), with `rehearsal_note` naming `#knuck-up`; record `channel_id`, `thread_id`, `message_id`
  (the thread's starter card) and `shadow` (1 when made in the rehearsal home). A mode flip does not move an existing
  thread; staff get a **Move to #knuck-up** button. ⚠️ Anything that posts runs under a `Reconciler` lock and re-reads
  `thread_id` inside it (checklist 37); every send carries `allowed_mentions` (11).
- **The starter card** (edited in place on every move that changes the tournament): name, game, format and options,
  state, entrants (count and names), the bracket as text (current round's sets with names and scores), and the
  player buttons that are legal now: **Sign up** / **Leave** (signups), **Check in** (check-in), and nothing else.
- **A set card** per set when it becomes `ready` (or `called`), posted in the thread, pinging only its two players
  (members; guests are named): **Report** (a modal with two score fields, the set's best-of in the title) for the two
  players; **Confirm** / **Dispute** (a modal with the note) for the opponent once reported, with the
  `confirms_at` time as `<t:…:R>`; the card is edited to the final line on completion. TO-only buttons on the same
  card render only for `may_run`: **Decide** (scores or forfeit), **Reset**, **Call**.
- **The TO panel** (`/bracket`, one command, ephemeral, `brackets_panel_minutes`): pick a tournament → its moves as
  buttons that render only when legal (Open/Close sign-ups, Open/Close check-in, Seed (select order / Shuffle),
  Start, Back to seeding, Complete (with a tie order select for RR/Swiss when `standings` has a shared place),
  Reopen, Cancel, Restore), plus Add entrant (modal: member picker or guest name), Remove / Restore / DQ (entrant
  select), and per-set Decide / Reset. Every refusal answers the move's own words; `render_again` on every panel
  (checklist 36).
- **The sweeps** (one `tasks.loop`, a tick a minute, with `@loop.error` and `last_ok_at`, checklist 28):
  `brackets_sets.confirm_due(bot, guild)` and `brackets_people.close_due_check_ins(bot, guild)`; post the results in
  the thread. Both are no-ops while the mode is off.
- **Reconcile on boot and on the loop** (4, 25): a tournament whose thread is gone is re-made; a set card missing
  for a `ready` set is posted.

## F. Layer 3 — the site page (build from this)

`site/public/brackets.html` + `assets/page-brackets.js`, reading only the routes above. A list (`GET /api/brackets`)
with Create (only when `may_run`); a tournament view drawing the bracket by `side`/`round`/`position` (winners above
losers, grand final at the end; round robin as a table; Swiss as rounds plus the standings table), each set showing
`a_name`/`b_name`, scores, `state` and `confirms_at`; the entrants list with seeds (drag to reorder + Shuffle while
seeding, check-in ticks during check-in), and the moves as buttons that render only when legal for this viewer
(`may_run`, `mine`, and the set's slots). The words the page draws for `waiting_on.what` (`play`, `called`,
`confirm`, `opponent_confirms`, `to_decides`, `waits`, `next_round`, `done`, `out`) and every button label become
settings keys in L3 (the every-word-editable rule). No explaining blurbs. The settings drawer on the page holds the
85 keys. Add `brackets.html` to `contract.json` `pages` and extend the mock's player paths (the L1 mock answers a
report from any session as a TO's).

## G. Decisions beyond the brief

1. **`brackets_best_of_late`** is a key (and a `best_of_late` column) the brief did not list: "from a chosen round
   onward → 5" needs the 5 somewhere, and `best_of_finals` is the grand final's.
2. **`brackets_best_of_from_round` means "top N"** — the entrants still alive when the set is played (A4) — not a
   round number, because round numbers differ between the two sides of a double elimination; it applies to
   elimination only.
3. **The finals best-of covers single elimination's final too**, not only a grand final.
4. **`brackets_format_default`** is a key: every default is a key, and a create without a format needs one.
5. **Best-of keys are enums of odd numbers** ("1"…"15"), so an even best-of cannot be stored.
6. **`confirmed` is not a resting state** (A7); the opponent reporting the same score is their confirm, a different
   score is refused with the reported one.
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

## H. What is NOT built (and is not in L2/L3 either unless the owner asks)

Pools into a bracket (phases, progressions), teams and crews, stations and streams, entry fees and payouts, series
or circuit points, ladders and matchmaking, the start.gg mirror (only the `source` column exists), DE's optional
5th-place set, per-game reporting (characters, stages), the DQ timer (auto-DQ when a player does not check in to a
called set), conflicts and waves, printing.

## Gate (2026-10-07, branch `brackets-engine`)

See the build report for the exact figures at the final commit; recorded here at the docs commit:
full suite `python -m pytest tests -q -p no:cacheprovider -n 8`, `python -m ruff check .`,
`MOCK_PORT=8809 node site/mock/check.mjs` (*25 pages, 344 routes, 202 core settings, all keys present*), and every
`site/mock/*.test.mjs` — results in *Deviations / gate* below once the last run is in.

## What was NOT verified

- Nothing met Discord — layer 1 has no Discord code; the thread, cards and panel above are a specification.
- No browser rendered anything — there is no page; the mock answers the shapes only and its player paths are
  simplified.
- The schema change has not run on the live database (only on fixtures: a fresh file and an 89 file).
- start.gg's own drop order and placement numbers are not confirmed from a source (research §3); the engine's are
  derived and tested by hand-worked brackets and by simulation.
- Concurrency was tested for two simultaneous sign-ups only; two simultaneous reports on one set rely on the same
  per-tournament lock, not a separate test.
