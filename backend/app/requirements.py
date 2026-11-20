"""Deduplicated field reports in one room collapse into one ranked
requirement. Priority rewards three things a Project Engineer actually
cares about: more independent reports naming the same issue (fan-in), a
gating discipline (mep/structural over architectural, since those more
often block other trades), and an unanswered RFI sitting underneath it
(a question nobody has answered yet blocks a design decision, not just a
punch item).
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .dedup import ReportRecord, find_duplicate_groups
from .models import PunchItem, Rfi
from .rfi import rfi_status

# Deliberately coarse: MEP and structural issues more often block other
# trades' work than a finish item does, so they outrank architectural by
# construction, not by measurement.
_DISCIPLINE_WEIGHT = {"mep": 3.0, "structural": 3.0, "architectural": 1.0}

# An unresolved RFI underneath a requirement blocks a design decision, not
# just a punch item; each one adds this many points.
_UNANSWERED_RFI_BONUS = 2.0

# Age contributes at most this many points, reached at 3x the RFI
# escalation SLA (30 days); an issue does not get infinitely more urgent
# the older it gets, it is capped the same way a real triage board caps
# "ancient" severity.
_MAX_AGE_BONUS = 3.0
_AGE_BONUS_SATURATION_DAYS = 30.0


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    level: str
    room: str
    discipline: str
    representative_text: str
    source_report_ids: tuple[str, ...]
    contains_unanswered_rfi: bool
    priority_score: float


def score_group(discipline: str, fan_in: int, unanswered_rfi_count: int, max_age_days: float) -> float:
    """Pure function of the already-known group facts; unit-tested
    directly (`test_requirements.py`) against hand-computed expected
    scores, the same pure/live split `ReleaseGate.evaluate` uses in the
    sibling telemetry project."""
    discipline_weight = _DISCIPLINE_WEIGHT.get(discipline, 1.0)
    fan_in_bonus = 0.5 * (fan_in - 1)
    age_bonus = min(max_age_days / _AGE_BONUS_SATURATION_DAYS * _MAX_AGE_BONUS, _MAX_AGE_BONUS)
    rfi_bonus = _UNANSWERED_RFI_BONUS * unanswered_rfi_count
    return discipline_weight * (1.0 + fan_in_bonus) + age_bonus + rfi_bonus


def _report_records(session: Session) -> list[ReportRecord]:
    records = [
        ReportRecord(f"punch:{item.id}", item.level, item.room, item.discipline, item.description)
        for item in session.scalars(select(PunchItem)).all()
    ]
    records += [
        ReportRecord(f"rfi:{rfi.id}", rfi.level, rfi.room, rfi.discipline, rfi.question)
        for rfi in session.scalars(select(Rfi)).all()
    ]
    return records


def build_ranked_requirements(session: Session, as_of: datetime.datetime) -> list[Requirement]:
    reports = _report_records(session)
    groups = find_duplicate_groups(reports)

    rfi_rows = {f"rfi:{rfi.id}": rfi for rfi in session.scalars(select(Rfi)).all()}
    punch_rows = {f"punch:{item.id}": item for item in session.scalars(select(PunchItem)).all()}

    requirements = []
    for idx, group in enumerate(groups):
        unanswered = 0
        max_age = 0.0
        for r in group:
            if r.report_id in rfi_rows:
                rfi = rfi_rows[r.report_id]
                if rfi_status(session, rfi.id, as_of) != "answered":
                    unanswered += 1
                max_age = max(max_age, (as_of - rfi.submitted_at).days)
            else:
                item = punch_rows[r.report_id]
                max_age = max(max_age, (as_of - item.opened_at).days)

        score = score_group(group[0].discipline, len(group), unanswered, max_age)
        representative = max(group, key=lambda r: len(r.text))
        requirements.append(
            Requirement(
                requirement_id=f"REQ-{group[0].level}-{group[0].room}-{idx}",
                level=group[0].level,
                room=group[0].room,
                discipline=group[0].discipline,
                representative_text=representative.text,
                source_report_ids=tuple(sorted(r.report_id for r in group)),
                contains_unanswered_rfi=unanswered > 0,
                priority_score=score,
            )
        )

    requirements.sort(key=lambda req: req.priority_score, reverse=True)
    return requirements
