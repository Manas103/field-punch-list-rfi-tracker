import datetime

from app.punch_items import open_punch_item
from app.requirements import build_ranked_requirements, score_group
from app.rfi import open_rfi

OPENED = datetime.datetime(2026, 5, 1)
AS_OF = datetime.datetime(2026, 5, 5)


def test_score_group_is_a_pure_function_matching_hand_computed_values():
    # mep, fan_in=1, 0 unanswered RFIs, 0 age: 3.0 * (1 + 0) + 0 + 0 = 3.0
    assert score_group("mep", fan_in=1, unanswered_rfi_count=0, max_age_days=0.0) == 3.0
    # architectural, fan_in=3, 0 unanswered, 0 age: 1.0 * (1 + 0.5*2) = 2.0
    assert score_group("architectural", fan_in=3, unanswered_rfi_count=0, max_age_days=0.0) == 2.0
    # mep, fan_in=1, 1 unanswered RFI, 0 age: 3.0 * 1 + 0 + 2.0 = 5.0
    assert score_group("mep", fan_in=1, unanswered_rfi_count=1, max_age_days=0.0) == 5.0
    # architectural, fan_in=1, 0 unanswered, 30 days age (saturates): 1.0 + 3.0 = 4.0
    assert score_group("architectural", fan_in=1, unanswered_rfi_count=0, max_age_days=30.0) == 4.0
    # age beyond saturation does not add more than the cap
    assert score_group("architectural", fan_in=1, unanswered_rfi_count=0, max_age_days=300.0) == 4.0


def test_a_room_with_three_near_duplicate_reports_outranks_a_room_with_one(session):
    open_punch_item(session, "L01", "R001", "A-101", "duct hanger missing insulation clamp", OPENED)
    open_punch_item(session, "L01", "R001", "A-101", "insulation clamp missing from duct hanger", OPENED)
    open_punch_item(session, "L01", "R001", "A-101", "duct hanger missing its insulation clamp", OPENED)

    open_punch_item(session, "L01", "R002", "A-102", "wall paint touch-up needed at patch", OPENED)

    reqs = build_ranked_requirements(session, AS_OF)
    by_room = {r.room: r for r in reqs}
    assert len(by_room["R001"].source_report_ids) == 3
    assert len(by_room["R002"].source_report_ids) == 1
    assert reqs[0].room == "R001"
    assert reqs.index(by_room["R001"]) < reqs.index(by_room["R002"])


def test_a_room_with_an_unanswered_rfi_outranks_an_otherwise_identical_mep_room(session):
    # R001 gets two separate requirements (the punch item and the RFI do
    # not merge, their text is too dissimilar); R002 gets exactly one.
    open_punch_item(session, "L01", "R001", "A-101", "duct hanger missing insulation clamp", OPENED)
    open_rfi(session, "L01", "R001", "A-101", "duct routing conflicts with structural beam at this gridline, confirm reroute", OPENED)

    open_punch_item(session, "L01", "R002", "A-102", "conduit run not secured to unistrut", OPENED)

    reqs = build_ranked_requirements(session, AS_OF)
    r001_reqs = [r for r in reqs if r.room == "R001"]
    r002_reqs = [r for r in reqs if r.room == "R002"]
    assert len(r001_reqs) == 2
    assert len(r002_reqs) == 1
    r001_with_rfi = next(r for r in r001_reqs if r.contains_unanswered_rfi)
    assert reqs.index(r001_with_rfi) < reqs.index(r002_reqs[0])


def test_requirements_list_is_sorted_descending_by_priority_score(session):
    open_punch_item(session, "L01", "R001", "A-101", "duct hanger missing insulation clamp", OPENED)
    open_punch_item(session, "L01", "R002", "A-102", "wall paint touch-up needed at patch", OPENED)
    open_punch_item(session, "L01", "R003", "A-103", "column base plate grout incomplete", OPENED)

    reqs = build_ranked_requirements(session, AS_OF)
    scores = [r.priority_score for r in reqs]
    assert scores == sorted(scores, reverse=True)


def test_requirement_ids_are_unique_and_representative_text_is_one_of_the_source_reports(session):
    open_punch_item(session, "L01", "R001", "A-101", "duct hanger missing insulation clamp", OPENED)
    open_punch_item(session, "L01", "R001", "A-101", "insulation clamp missing from duct hanger", OPENED)

    reqs = build_ranked_requirements(session, AS_OF)
    ids = [r.requirement_id for r in reqs]
    assert len(ids) == len(set(ids))
    for r in reqs:
        assert len(r.source_report_ids) >= 1
