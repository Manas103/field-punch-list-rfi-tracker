"""Reproduces the dedup/prioritization numbers quoted in the README.
Prints, does not assert; `pytest tests/test_dedup.py` is what actually
verifies the ground-truth accuracy claim."""
import datetime
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import make_engine, make_session
from app.dedup import ReportRecord, find_duplicate_groups
from app.generator import build_dedup_ground_truth_corpus, build_synthetic_dataset
from app.models import PunchItem, Rfi
from app.requirements import build_ranked_requirements
from sqlalchemy import select


def _records_from_db(session):
    return [
        ReportRecord(f"punch:{item.id}", item.level, item.room, item.discipline, item.description)
        for item in session.scalars(select(PunchItem)).all()
    ] + [
        ReportRecord(f"rfi:{rfi.id}", rfi.level, rfi.room, rfi.discipline, rfi.question)
        for rfi in session.scalars(select(Rfi)).all()
    ]


def main():
    engine = make_engine("sqlite:///:memory:")
    session = make_session(engine)
    rng = random.Random(5)
    truth = build_dedup_ground_truth_corpus(session, rng, num_rooms=100)
    records = _records_from_db(session)
    print(f"ground truth corpus: {len(records)} reports across 100 rooms")

    predicted_groups = find_duplicate_groups(records, same_room_only=True)
    predicted_group_of = {}
    for g in predicted_groups:
        key = frozenset(r.report_id for r in g)
        for r in g:
            predicted_group_of[r.report_id] = key

    pairs_total, pairs_caught, false_merges = 0, 0, 0
    for root_id, true_group in truth["true_groups"].items():
        if len(true_group) > 1:
            pairs_total += len(true_group) - 1
            root_pred = predicted_group_of[root_id]
            pairs_caught += sum(1 for m in true_group if m != root_id and m in root_pred)
        root_pred = predicted_group_of[root_id]
        false_merges += sum(1 for m in root_pred if m not in true_group)

    print(f"same_room_only=True (fixed design): true duplicate pairs caught {pairs_caught}/{pairs_total}, "
          f"false merges {false_merges}")

    # The first, broken design: compare every report regardless of room.
    naive_groups = find_duplicate_groups(records, same_room_only=False)
    naive_group_of = {}
    for g in naive_groups:
        key = frozenset(r.report_id for r in g)
        for r in g:
            naive_group_of[r.report_id] = key
    naive_false_merges = 0
    for root_id, true_group in truth["true_groups"].items():
        root_pred = naive_group_of[root_id]
        naive_false_merges += sum(1 for m in root_pred if m not in true_group)
    print(f"same_room_only=False (the first, broken design): false merges {naive_false_merges} "
          f"(out of {len(records)} reports compared pairwise with no room restriction)")

    engine2 = make_engine("sqlite:///:memory:")
    session2 = make_session(engine2)
    rng2 = random.Random(11)
    scale = build_synthetic_dataset(session2, rng2, target_punch_items=2600, target_rfis=420)
    print(f"production dataset: {scale['punch_item_count']} punch items, {scale['rfi_count']} RFIs")
    reqs = build_ranked_requirements(session2, datetime.datetime(2026, 5, 15))
    print(f"ranked requirements produced: {len(reqs)} (from {scale['punch_item_count'] + scale['rfi_count']} reports)")
    print("top 5 by priority score:")
    for r in reqs[:5]:
        print(f"  {r.requirement_id} score={r.priority_score:.2f} discipline={r.discipline} "
              f"fan_in={len(r.source_report_ids)} unanswered_rfi={r.contains_unanswered_rfi} "
              f"text={r.representative_text!r}")


if __name__ == "__main__":
    main()
