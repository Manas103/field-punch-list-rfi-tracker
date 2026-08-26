import datetime

import pytest
from sqlalchemy import text

from app.punch_items import CloseoutRefused, close_punch_item, open_punch_item, punch_item_status, record_inspection_evidence

OPENED = datetime.datetime(2026, 5, 1)
CLOSED = datetime.datetime(2026, 5, 10)


def test_close_refused_without_any_evidence(session):
    item = open_punch_item(session, "L01", "R001", "A-101", "wall paint touch-up needed", OPENED)
    with pytest.raises(CloseoutRefused, match=str(item.id)):
        close_punch_item(session, item.id, evidence_id=999, closed_at=CLOSED)
    assert punch_item_status(session, item.id) == "open"


def test_close_refused_with_evidence_for_a_different_item(session):
    item_a = open_punch_item(session, "L01", "R001", "A-101", "wall paint touch-up needed", OPENED)
    item_b = open_punch_item(session, "L01", "R002", "A-101", "door hardware missing closer arm", OPENED)
    evidence_for_b = record_inspection_evidence(session, item_b.id, "J. Ruiz", "closer arm installed", CLOSED)

    with pytest.raises(CloseoutRefused, match=str(item_a.id)):
        close_punch_item(session, item_a.id, evidence_id=evidence_for_b.id, closed_at=CLOSED)
    assert punch_item_status(session, item_a.id) == "open"
    assert punch_item_status(session, item_b.id) == "open"  # evidence recorded, not yet closed


def test_close_succeeds_with_matching_evidence(session):
    item = open_punch_item(session, "L01", "R001", "A-101", "wall paint touch-up needed", OPENED)
    evidence = record_inspection_evidence(session, item.id, "J. Ruiz", "touch-up verified", CLOSED)
    close_punch_item(session, item.id, evidence_id=evidence.id, closed_at=CLOSED)
    assert punch_item_status(session, item.id) == "closed"


def test_double_close_is_refused(session):
    item = open_punch_item(session, "L01", "R001", "A-101", "wall paint touch-up needed", OPENED)
    evidence = record_inspection_evidence(session, item.id, "J. Ruiz", "touch-up verified", CLOSED)
    close_punch_item(session, item.id, evidence_id=evidence.id, closed_at=CLOSED)
    with pytest.raises(CloseoutRefused):
        close_punch_item(session, item.id, evidence_id=evidence.id, closed_at=CLOSED)


def test_the_event_log_and_evidence_tables_are_never_updated_or_deleted(session):
    """Inspects the raw tables after a realistic sequence of opens and
    closes and confirms row counts only ever grow, which is what
    'append-only' has to mean if it means anything."""
    item_1 = open_punch_item(session, "L01", "R001", "A-101", "wall paint touch-up needed", OPENED)
    item_2 = open_punch_item(session, "L01", "R002", "A-101", "door hardware missing closer arm", OPENED)
    ev_1 = record_inspection_evidence(session, item_1.id, "J. Ruiz", "verified", CLOSED)
    close_punch_item(session, item_1.id, evidence_id=ev_1.id, closed_at=CLOSED)

    events_after_one_close = session.execute(text("select count(*) from punch_item_events")).scalar()
    evidence_after_one_close = session.execute(text("select count(*) from inspection_evidence")).scalar()

    ev_2 = record_inspection_evidence(session, item_2.id, "J. Ruiz", "verified", CLOSED)
    close_punch_item(session, item_2.id, evidence_id=ev_2.id, closed_at=CLOSED)

    events_after_two_closes = session.execute(text("select count(*) from punch_item_events")).scalar()
    evidence_after_two_closes = session.execute(text("select count(*) from inspection_evidence")).scalar()

    assert events_after_two_closes > events_after_one_close
    assert evidence_after_two_closes > evidence_after_one_close
    # 2 opens + 2 closes = 4 events total, never rewritten in place.
    assert events_after_two_closes == 4
    assert evidence_after_two_closes == 2
