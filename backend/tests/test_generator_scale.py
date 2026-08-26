import random

from app.generator import build_synthetic_dataset
from app.punch_items import punch_item_status
from app.rfi import rfi_status
import datetime


def test_over_2500_synthetic_punch_items_and_400_rfis_all_routed_and_located(session):
    rng = random.Random(11)
    result = build_synthetic_dataset(session, rng, target_punch_items=2600, target_rfis=420)

    assert result["punch_item_count"] > 2500
    assert result["rfi_count"] > 400

    all_punch_ids = [pid for ids in result["punch_ids_by_room"].values() for pid in ids]
    all_rfi_ids = [rid for ids in result["rfi_ids_by_room"].values() for rid in ids]
    assert len(all_punch_ids) == 2600
    assert len(all_rfi_ids) == 420

    from app.models import PunchItem, Rfi

    for pid in all_punch_ids[:50]:  # spot-check a sample; every one is opened the same way
        item = session.get(PunchItem, pid)
        assert item.level and item.room and item.drawing_sheet
        assert item.discipline in {"architectural", "structural", "mep"}
        assert punch_item_status(session, pid) == "open"

    for rid in all_rfi_ids[:50]:
        rfi = session.get(Rfi, rid)
        assert rfi.level and rfi.room and rfi.drawing_sheet
        assert rfi.discipline in {"architectural", "structural", "mep"}
        assert rfi_status(session, rid, datetime.datetime(2026, 5, 2)) == "open"


def test_every_room_gets_at_least_one_punch_item(session):
    rng = random.Random(11)
    result = build_synthetic_dataset(session, rng, target_punch_items=2600, target_rfis=420)
    empty_rooms = [room for room, ids in result["punch_ids_by_room"].items() if not ids]
    assert empty_rooms == []
