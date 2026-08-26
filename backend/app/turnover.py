"""Room turnover gate. A room is not allowed to turn over while any punch
item or RFI opened against it is still unresolved; the refusal names the
exact item still open rather than saying a room "isn't ready".
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .punch_items import open_punch_items_in_room
from .rfi import unresolved_rfis_in_room


@dataclass(frozen=True)
class TurnoverResult:
    level: str
    room: str
    allowed: bool
    blocking_punch_items: tuple = field(default_factory=tuple)
    blocking_rfis: tuple = field(default_factory=tuple)

    def refusal_message(self) -> str:
        if self.allowed:
            return f"level {self.level} room {self.room}: turnover allowed"
        names = [f"punch item {i.id} ({i.description})" for i in self.blocking_punch_items] + [
            f"RFI {r.id} ({r.question})" for r in self.blocking_rfis
        ]
        return f"level {self.level} room {self.room}: turnover refused, still open: " + "; ".join(names)


def attempt_room_turnover(session: Session, level: str, room: str, as_of: datetime.datetime) -> TurnoverResult:
    open_items = open_punch_items_in_room(session, level, room)
    unresolved = unresolved_rfis_in_room(session, level, room, as_of)
    allowed = not open_items and not unresolved
    return TurnoverResult(
        level=level,
        room=room,
        allowed=allowed,
        blocking_punch_items=tuple(open_items),
        blocking_rfis=tuple(unresolved),
    )
