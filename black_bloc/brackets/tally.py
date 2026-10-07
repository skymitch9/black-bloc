"""Each entrant's record from the finished sets: sets, games, byes, who they met and beat."""

from __future__ import annotations

from dataclasses import dataclass, field

from .model import BYE, COMPLETE, Bracket


@dataclass
class Record:
    entrant: int
    played: int = 0
    set_wins: int = 0
    set_losses: int = 0
    game_wins: int = 0
    game_losses: int = 0
    byes: int = 0
    opponents: list[int] = field(default_factory=list)
    beat: list[int] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.set_wins / self.played if self.played else 0.0


def records(bracket: Bracket) -> dict[int, Record]:
    found = {entrant: Record(entrant) for entrant in bracket.entrants}
    for match in bracket.ordered():
        if match.state == BYE and match.winner is not None:
            mine = found.setdefault(match.winner, Record(match.winner))
            mine.played += 1
            mine.set_wins += 1
            mine.byes += 1
            continue
        if match.state != COMPLETE or match.winner is None or match.loser is None:
            continue
        winner = found.setdefault(match.winner, Record(match.winner))
        loser = found.setdefault(match.loser, Record(match.loser))
        winner.played += 1
        loser.played += 1
        winner.set_wins += 1
        loser.set_losses += 1
        winner.opponents.append(match.loser)
        loser.opponents.append(match.winner)
        winner.beat.append(match.loser)
        if match.score_a is not None and match.score_b is not None:
            won, lost = (
                (match.score_a, match.score_b)
                if match.winner == match.slot_a
                else (match.score_b, match.score_a)
            )
            winner.game_wins += won
            winner.game_losses += lost
            loser.game_wins += lost
            loser.game_losses += won
    return found


def met(bracket: Bracket) -> set[frozenset[int]]:
    """Every pair that has been paired, finished or not."""
    return {
        frozenset((match.slot_a, match.slot_b))
        for match in bracket.matches.values()
        if match.slot_a is not None and match.slot_b is not None
    }
