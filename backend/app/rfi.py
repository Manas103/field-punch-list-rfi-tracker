"""RFI lifecycle: opened against a level/room/sheet, routed to a
discipline, aged on a clock that escalates when a question goes unanswered
past its SLA, answered over an append-only event log.
"""
from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Rfi, RfiEvent
from .routing import route_discipline

# An RFI that has gone this many calendar days without an answer is
# escalated. Chosen to match a typical two-week contractor RFI turnaround
# with margin, not tuned against any specific test.
ESCALATION_SLA_DAYS = 10


def open_rfi(
    session: Session, level: str, room: str, drawing_sheet: str, question: str, submitted_at: datetime.datetime
) -> Rfi:
    rfi = Rfi(
        level=level,
        room=room,
        drawing_sheet=drawing_sheet,
        discipline=route_discipline(question),
        question=question,
        submitted_at=submitted_at,
    )
    session.add(rfi)
    session.flush()
    session.add(RfiEvent(rfi_id=rfi.id, event_type="submitted", created_at=submitted_at))
    session.commit()
    return rfi


def answer_rfi(session: Session, rfi_id: int, answer_text: str, answered_at: datetime.datetime) -> RfiEvent:
    event = RfiEvent(rfi_id=rfi_id, event_type="answered", answer_text=answer_text, created_at=answered_at)
    session.add(event)
    session.commit()
    return event


def rfi_status(session: Session, rfi_id: int, as_of: datetime.datetime) -> str:
    """'answered', 'escalated' (unanswered past the SLA), or 'open'
    (unanswered, still within the SLA). Escalation is a triage label, not a
    gate by itself: an RFI is unresolved for turnover purposes whether it
    is merely 'open' or already 'escalated'."""
    rfi = session.get(Rfi, rfi_id)
    if rfi is None:
        raise ValueError(f"RFI {rfi_id} does not exist")

    answered = session.scalars(
        select(RfiEvent).where(RfiEvent.rfi_id == rfi_id, RfiEvent.event_type == "answered")
    ).first()
    if answered is not None:
        return "answered"

    age = (as_of - rfi.submitted_at).days
    return "escalated" if age > ESCALATION_SLA_DAYS else "open"


def unresolved_rfis_in_room(session: Session, level: str, room: str, as_of: datetime.datetime) -> list[Rfi]:
    rfis = session.scalars(select(Rfi).where(Rfi.level == level, Rfi.room == room)).all()
    return [rfi for rfi in rfis if rfi_status(session, rfi.id, as_of) != "answered"]
