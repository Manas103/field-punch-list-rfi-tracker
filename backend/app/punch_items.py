"""Punch item lifecycle: open against a level/room/sheet, routed to a
discipline, closed only against inspection evidence, over an append-only
event log.
"""
from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import InspectionEvidence, PunchItem, PunchItemEvent
from .routing import route_discipline


class CloseoutRefused(Exception):
    """Raised when a close attempt does not carry evidence for the exact
    item being closed. Always names the item."""


def open_punch_item(
    session: Session, level: str, room: str, drawing_sheet: str, description: str, opened_at: datetime.datetime
) -> PunchItem:
    item = PunchItem(
        level=level,
        room=room,
        drawing_sheet=drawing_sheet,
        discipline=route_discipline(description),
        description=description,
        opened_at=opened_at,
    )
    session.add(item)
    session.flush()
    session.add(PunchItemEvent(punch_item_id=item.id, event_type="opened", created_at=opened_at))
    session.commit()
    return item


def record_inspection_evidence(
    session: Session, punch_item_id: int, inspector: str, note: str, recorded_at: datetime.datetime
) -> InspectionEvidence:
    evidence = InspectionEvidence(
        punch_item_id=punch_item_id, inspector=inspector, note=note, recorded_at=recorded_at
    )
    session.add(evidence)
    session.commit()
    return evidence


def close_punch_item(
    session: Session, punch_item_id: int, evidence_id: int, closed_at: datetime.datetime
) -> PunchItemEvent:
    """Refuses the close, naming the item, unless `evidence_id` names real
    inspection evidence recorded against this exact punch item. Never
    updates or deletes a row; a close is one more row in the event log."""
    item = session.get(PunchItem, punch_item_id)
    if item is None:
        raise CloseoutRefused(f"punch item {punch_item_id} does not exist")

    if punch_item_status(session, punch_item_id) == "closed":
        raise CloseoutRefused(f"punch item {punch_item_id} ({item.description}) is already closed")

    evidence = session.get(InspectionEvidence, evidence_id)
    if evidence is None or evidence.punch_item_id != punch_item_id:
        raise CloseoutRefused(
            f"punch item {punch_item_id} ({item.description}) has no inspection evidence "
            f"covering it; closeout refused, item remains open"
        )

    event = PunchItemEvent(
        punch_item_id=punch_item_id, event_type="closed", evidence_id=evidence_id, created_at=closed_at
    )
    session.add(event)
    session.commit()
    return event


def punch_item_status(session: Session, punch_item_id: int) -> str:
    """Derived from the event log: the most recent event decides. Never
    read from a mutable status column, because there isn't one."""
    latest = session.scalars(
        select(PunchItemEvent)
        .where(PunchItemEvent.punch_item_id == punch_item_id)
        .order_by(PunchItemEvent.id.desc())
        .limit(1)
    ).first()
    if latest is None:
        raise ValueError(f"punch item {punch_item_id} has no events")
    return "closed" if latest.event_type == "closed" else "open"


def open_punch_items_in_room(session: Session, level: str, room: str) -> list[PunchItem]:
    items = session.scalars(
        select(PunchItem).where(PunchItem.level == level, PunchItem.room == room)
    ).all()
    return [item for item in items if punch_item_status(session, item.id) == "open"]
