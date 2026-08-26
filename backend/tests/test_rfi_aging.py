import datetime

from app.rfi import ESCALATION_SLA_DAYS, answer_rfi, open_rfi, rfi_status

SUBMITTED = datetime.datetime(2026, 6, 1)


def test_rfi_is_open_within_the_sla(session):
    rfi = open_rfi(session, "L01", "R001", "M-201", "duct routing conflicts with beam, confirm reroute", SUBMITTED)
    as_of = SUBMITTED + datetime.timedelta(days=ESCALATION_SLA_DAYS - 1)
    assert rfi_status(session, rfi.id, as_of) == "open"


def test_rfi_escalates_after_the_sla_if_unanswered(session):
    rfi = open_rfi(session, "L01", "R001", "M-201", "duct routing conflicts with beam, confirm reroute", SUBMITTED)
    as_of = SUBMITTED + datetime.timedelta(days=ESCALATION_SLA_DAYS + 1)
    assert rfi_status(session, rfi.id, as_of) == "escalated"


def test_answered_rfi_never_escalates_even_long_after_the_sla(session):
    rfi = open_rfi(session, "L01", "R001", "M-201", "duct routing conflicts with beam, confirm reroute", SUBMITTED)
    answer_rfi(session, rfi.id, "reroute approved per RFI-114", SUBMITTED + datetime.timedelta(days=3))
    as_of = SUBMITTED + datetime.timedelta(days=90)
    assert rfi_status(session, rfi.id, as_of) == "answered"


def test_rfi_is_routed_to_the_discipline_its_question_names():
    from app.routing import route_discipline

    assert route_discipline("duct routing conflicts with beam, confirm reroute") == "mep"
    assert route_discipline("beam connection detail not shown, confirm detail") == "structural"
