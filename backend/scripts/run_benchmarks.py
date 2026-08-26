"""Reproduces the measured numbers quoted in the README. Prints, does not
assert; `pytest` is what actually verifies these claims (see tests/)."""
import datetime
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import make_engine, make_session
from app.generator import build_synthetic_dataset
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


def build_room(session, level, room, items_left_open):
    items = [open_punch_item(session, level, room, "A-101", desc, OPENED) for desc in DESCRIPTIONS]
    rfi = open_rfi(session, level, room, "A-101", "wall type at this partition unclear, confirm type", OPENED)
    answer_rfi(session, rfi.id, "wall type confirmed per addendum 2", OPENED + datetime.timedelta(days=1))
    for item in items[: len(items) - items_left_open]:
        evidence = record_inspection_evidence(session, item.id, "J. Ruiz", "verified", CLOSED)
        close_punch_item(session, item.id, evidence_id=evidence.id, closed_at=CLOSED)
    return items[len(items) - items_left_open :]


def main():
    engine = make_engine("sqlite:///:memory:")
    session = make_session(engine)

    refused = 0
    for i in range(30):
        [still_open] = build_room(session, "L01", f"R{i:03d}", items_left_open=1)
        result = attempt_room_turnover(session, "L01", f"R{i:03d}", CLOSED)
        if not result.allowed and len(result.blocking_punch_items) == 1 and result.blocking_punch_items[0].id == still_open.id:
            refused += 1
    print(f"seeded premature closeouts: 30, refused naming the item still open: {refused}")

    false_holds = 0
    for i in range(40):
        build_room(session, "L02", f"R{i:03d}", items_left_open=0)
        result = attempt_room_turnover(session, "L02", f"R{i:03d}", CLOSED)
        if not result.allowed:
            false_holds += 1
    print(f"false holds across 40 clean rooms: {false_holds}")

    engine2 = make_engine("sqlite:///:memory:")
    session2 = make_session(engine2)
    rng = random.Random(11)
    result = build_synthetic_dataset(session2, rng, target_punch_items=2600, target_rfis=420)
    print(f"synthetic dataset: {result['punch_item_count']} punch items, {result['rfi_count']} RFIs")


if __name__ == "__main__":
    main()
