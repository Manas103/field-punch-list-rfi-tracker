"""End-to-end demo: open punch items and RFIs in a room, close some with
evidence, leave one open, check turnover (refused), close the last one,
check turnover again (allowed).
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import make_engine, make_session
from app.punch_items import close_punch_item, open_punch_item, record_inspection_evidence
from app.rfi import answer_rfi, open_rfi
from app.turnover import attempt_room_turnover

OPENED = datetime.datetime(2026, 6, 1)
CLOSED = datetime.datetime(2026, 6, 8)


def main():
    engine = make_engine("sqlite:///:memory:")
    session = make_session(engine)

    level, room = "L04", "R412"
    items = [
        open_punch_item(session, level, room, "M-201", "duct hanger missing insulation clamp", OPENED),
        open_punch_item(session, level, room, "A-101", "door hardware missing closer arm", OPENED),
        open_punch_item(session, level, room, "S-301", "footing rebar cover under minimum", OPENED),
    ]
    for item in items:
        print(f"opened punch item {item.id}: [{item.discipline}] {item.description}")

    rfi = open_rfi(session, level, room, "M-201", "duct routing conflicts with beam, confirm reroute", OPENED)
    print(f"opened RFI {rfi.id}: [{rfi.discipline}] {rfi.question}")

    print("\nclosing 2 of 3 punch items, answering the RFI, leaving 1 item open...")
    for item in items[:2]:
        evidence = record_inspection_evidence(session, item.id, "J. Ruiz", "verified in field", CLOSED)
        close_punch_item(session, item.id, evidence_id=evidence.id, closed_at=CLOSED)
    answer_rfi(session, rfi.id, "reroute approved per RFI-114", OPENED + datetime.timedelta(days=2))

    result = attempt_room_turnover(session, level, room, CLOSED)
    print(f"\nturnover check: {result.refusal_message()}")
    assert result.allowed is False

    print("\nclosing the remaining item...")
    remaining = items[2]
    evidence = record_inspection_evidence(session, remaining.id, "J. Ruiz", "rebar cover corrected and reinspected", CLOSED)
    close_punch_item(session, remaining.id, evidence_id=evidence.id, closed_at=CLOSED)

    result = attempt_room_turnover(session, level, room, CLOSED)
    print(f"turnover check: {result.refusal_message()}")
    assert result.allowed is True


if __name__ == "__main__":
    main()
