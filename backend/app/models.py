"""SQLAlchemy models.

`PunchItem` and `Rfi` carry no mutable status column. Status is always
derived by folding `PunchItemEvent` / `RfiEvent`, which are append-only:
nothing in this codebase ever runs an UPDATE or DELETE against either
table, only INSERT (see `closeout.py`, `rfi.py`, and `tests/test_append_only.py`,
which asserts this by inspecting the tables directly, not by trusting the
code).
"""
from __future__ import annotations

import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PunchItem(Base):
    __tablename__ = "punch_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(16))
    room: Mapped[str] = mapped_column(String(32))
    drawing_sheet: Mapped[str] = mapped_column(String(32))
    discipline: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)
    opened_at: Mapped[datetime.datetime] = mapped_column(DateTime)

    events: Mapped[list["PunchItemEvent"]] = relationship(
        back_populates="punch_item", order_by="PunchItemEvent.id"
    )


class InspectionEvidence(Base):
    """An immutable inspection record. A close event may only reference a
    piece of evidence that names the exact punch item it inspected."""

    __tablename__ = "inspection_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    punch_item_id: Mapped[int] = mapped_column(ForeignKey("punch_items.id"))
    inspector: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime)


class PunchItemEvent(Base):
    """Append-only. `event_type` is 'opened' or 'closed'. A closed event's
    `evidence_id` is always set and always points at evidence for the same
    punch item; enforced in `closeout.py`, not by a database constraint."""

    __tablename__ = "punch_item_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    punch_item_id: Mapped[int] = mapped_column(ForeignKey("punch_items.id"))
    event_type: Mapped[str] = mapped_column(String(16))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("inspection_evidence.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime)

    punch_item: Mapped[PunchItem] = relationship(back_populates="events")


class Rfi(Base):
    __tablename__ = "rfis"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(16))
    room: Mapped[str] = mapped_column(String(32))
    drawing_sheet: Mapped[str] = mapped_column(String(32))
    discipline: Mapped[str] = mapped_column(String(32))
    question: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime.datetime] = mapped_column(DateTime)

    events: Mapped[list["RfiEvent"]] = relationship(back_populates="rfi", order_by="RfiEvent.id")


class RfiEvent(Base):
    """Append-only. `event_type` is 'submitted' or 'answered'."""

    __tablename__ = "rfi_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    rfi_id: Mapped[int] = mapped_column(ForeignKey("rfis.id"))
    event_type: Mapped[str] = mapped_column(String(16))
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime)

    rfi: Mapped[Rfi] = relationship(back_populates="events")
