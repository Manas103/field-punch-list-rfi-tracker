import datetime

from app.punch_items import close_punch_item, open_punch_item, record_inspection_evidence
from app.rfi import answer_rfi, open_rfi
from app.turnover import attempt_room_turnover

OPENED = datetime.datetime(2026, 5, 1)
CLOSED = datetime.datetime(2026, 5, 10)
DESCRIPTIONS = [
    "wall paint touch-up needed at patch",
    "door hardware missing closer arm",
    "baseboard gap exceeds 1/8 inch",
]


def _build_room(session, level, room, items_left_open=0):
    """Opens 3 punch items and 1 RFI in a room, closes all but
    `items_left_open` of the punch items with real evidence, and answers
    the RFI. Returns the still-open punch items, in the order opened."""
    items = [
        open_punch_item(session, level, room, "A-101", desc, OPENED) for desc in DESCRIPTIONS
    ]
    rfi = open_rfi(session, level, room, "A-101", "wall type at this partition unclear, confirm type", OPENED)
    answer_rfi(session, rfi.id, "wall type confirmed per addendum 2", OPENED + datetime.timedelta(days=1))

    to_close = items[: len(items) - items_left_open]
    for item in to_close:
        evidence = record_inspection_evidence(session, item.id, "J. Ruiz", "verified", CLOSED)
        close_punch_item(session, item.id, evidence_id=evidence.id, closed_at=CLOSED)

    return items[len(items) - items_left_open :]


def test_30_of_30_seeded_premature_closeouts_refused_naming_the_item_still_open(session):
    refused_correctly = 0
    for i in range(30):
        level, room = "L01", f"R{i:03d}"
        [still_open_item] = _build_room(session, level, room, items_left_open=1)
        result = attempt_room_turnover(session, level, room, CLOSED)

        assert result.allowed is False
        assert len(result.blocking_punch_items) == 1
        assert result.blocking_punch_items[0].id == still_open_item.id
        assert str(still_open_item.id) in result.refusal_message()
        assert still_open_item.description in result.refusal_message()
        refused_correctly += 1

    assert refused_correctly == 30


def test_0_false_holds_across_40_clean_rooms(session):
    false_holds = 0
    for i in range(40):
        level, room = "L02", f"R{i:03d}"
        still_open = _build_room(session, level, room, items_left_open=0)
        assert still_open == []
        result = attempt_room_turnover(session, level, room, CLOSED)
        if not result.allowed:
            false_holds += 1

    assert false_holds == 0


def test_an_unanswered_rfi_alone_blocks_turnover_even_with_no_open_punch_items(session):
    level, room = "L03", "R001"
    item = open_punch_item(session, level, room, "A-101", "wall paint touch-up needed", OPENED)
    evidence = record_inspection_evidence(session, item.id, "J. Ruiz", "verified", CLOSED)
    close_punch_item(session, item.id, evidence_id=evidence.id, closed_at=CLOSED)

    rfi = open_rfi(session, level, room, "A-101", "wall type at this partition unclear, confirm type", OPENED)
    result = attempt_room_turnover(session, level, room, CLOSED)

    assert result.allowed is False
    assert len(result.blocking_rfis) == 1
    assert result.blocking_rfis[0].id == rfi.id
