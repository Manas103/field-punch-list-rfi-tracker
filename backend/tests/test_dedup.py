import random

from app.dedup import ReportRecord, find_duplicate_groups, similarity
from app.generator import build_dedup_ground_truth_corpus


def _group_sizes(groups):
    return sorted(len(g) for g in groups)


def test_near_duplicate_reports_in_the_same_room_merge():
    a = ReportRecord("punch:1", "L01", "R001", "mep", "duct hanger missing insulation clamp")
    b = ReportRecord("punch:2", "L01", "R001", "mep", "insulation clamp missing from duct hanger")
    groups = find_duplicate_groups([a, b])
    assert _group_sizes(groups) == [2]


def test_dissimilar_reports_in_the_same_room_do_not_merge():
    a = ReportRecord("punch:1", "L01", "R001", "mep", "duct hanger missing insulation clamp")
    b = ReportRecord("punch:2", "L01", "R001", "structural", "column base plate grout incomplete")
    groups = find_duplicate_groups([a, b])
    assert _group_sizes(groups) == [1, 1]


def test_same_room_only_true_does_not_merge_across_rooms_even_if_text_is_identical():
    a = ReportRecord("punch:1", "L01", "R001", "mep", "outlet cover plate missing in corridor")
    b = ReportRecord("punch:2", "L02", "R099", "mep", "outlet cover plate missing in corridor")
    groups = find_duplicate_groups([a, b], same_room_only=True)
    assert _group_sizes(groups) == [1, 1]


def test_same_room_only_false_reproduces_the_broken_naive_design():
    """The first version of this extension compared every report in the
    dataset regardless of room; reproduced here to document, not to
    recommend (see README "What broke")."""
    a = ReportRecord("punch:1", "L01", "R001", "mep", "outlet cover plate missing in corridor")
    b = ReportRecord("punch:2", "L02", "R099", "mep", "outlet cover plate missing in corridor")
    groups = find_duplicate_groups([a, b], same_room_only=False)
    assert _group_sizes(groups) == [2]


def test_union_find_transitively_groups_a_chain_of_three():
    a = ReportRecord("punch:1", "L01", "R001", "mep", "panelboard door does not close fully")
    b = ReportRecord("punch:2", "L01", "R001", "mep", "panelboard door does not fully close")
    c = ReportRecord("punch:3", "L01", "R001", "mep", "panelboard door does not close fully at all")
    groups = find_duplicate_groups([a, b, c])
    assert _group_sizes(groups) == [3]


def test_similarity_is_symmetric():
    a, b = "duct hanger missing insulation clamp", "insulation clamp missing from duct hanger"
    assert similarity(a, b) == similarity(b, a)


def test_dedup_against_a_seeded_ground_truth_corpus(session):
    """The accuracy claim: every true duplicate pair should merge, and no
    distractor should merge into a root's group. Measured pairwise over a
    dedicated 100-room corpus with a known truth, not the 2,600/420
    production dataset (see generator.build_dedup_ground_truth_corpus)."""
    from app.dedup import ReportRecord as RR
    from app.models import PunchItem, Rfi
    from sqlalchemy import select

    rng = random.Random(5)
    truth = build_dedup_ground_truth_corpus(session, rng, num_rooms=100)

    records = [
        RR(f"punch:{item.id}", item.level, item.room, item.discipline, item.description)
        for item in session.scalars(select(PunchItem)).all()
    ] + [
        RR(f"rfi:{rfi.id}", rfi.level, rfi.room, rfi.discipline, rfi.question)
        for rfi in session.scalars(select(Rfi)).all()
    ]
    predicted_groups = find_duplicate_groups(records)
    predicted_group_of = {}
    for g in predicted_groups:
        key = frozenset(r.report_id for r in g)
        for r in g:
            predicted_group_of[r.report_id] = key

    true_positive_pairs_caught = 0
    true_positive_pairs_total = 0
    false_merges = 0

    for root_id, true_group in truth["true_groups"].items():
        if len(true_group) > 1:
            true_positive_pairs_total += len(true_group) - 1
            root_predicted_group = predicted_group_of[root_id]
            for member in true_group:
                if member != root_id and member in root_predicted_group:
                    true_positive_pairs_caught += 1

    for root_id, true_group in truth["true_groups"].items():
        root_predicted_group = predicted_group_of[root_id]
        for member_of_group in root_predicted_group:
            if member_of_group not in true_group:
                false_merges += 1

    assert true_positive_pairs_total > 0
    assert true_positive_pairs_caught == true_positive_pairs_total
    assert false_merges == 0
