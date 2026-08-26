"""FastAPI surface over the tracker. Every write goes through the same
guarded functions the tests exercise directly (`punch_items.py`, `rfi.py`,
`turnover.py`); the API layer adds no business logic of its own.
"""
from __future__ import annotations

import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import punch_items as punch_items_module
from . import rfi as rfi_module
from .db import make_engine, make_session
from .models import PunchItem, Rfi
from .turnover import attempt_room_turnover

app = FastAPI(title="Field Punch List and RFI Tracker")

_engine = make_engine()


def get_session() -> Session:
    return make_session(_engine)


class OpenPunchItemRequest(BaseModel):
    level: str
    room: str
    drawing_sheet: str
    description: str


class RecordEvidenceRequest(BaseModel):
    punch_item_id: int
    inspector: str
    note: str


class ClosePunchItemRequest(BaseModel):
    punch_item_id: int
    evidence_id: int


class OpenRfiRequest(BaseModel):
    level: str
    room: str
    drawing_sheet: str
    question: str


class AnswerRfiRequest(BaseModel):
    rfi_id: int
    answer_text: str


def _punch_item_dict(session: Session, item: PunchItem) -> dict:
    return {
        "id": item.id,
        "level": item.level,
        "room": item.room,
        "drawing_sheet": item.drawing_sheet,
        "discipline": item.discipline,
        "description": item.description,
        "status": punch_items_module.punch_item_status(session, item.id),
    }


def _rfi_dict(session: Session, rfi: Rfi, as_of: datetime.datetime) -> dict:
    return {
        "id": rfi.id,
        "level": rfi.level,
        "room": rfi.room,
        "drawing_sheet": rfi.drawing_sheet,
        "discipline": rfi.discipline,
        "question": rfi.question,
        "status": rfi_module.rfi_status(session, rfi.id, as_of),
    }


@app.post("/punch-items")
def create_punch_item(request: OpenPunchItemRequest):
    session = get_session()
    item = punch_items_module.open_punch_item(
        session, request.level, request.room, request.drawing_sheet, request.description, datetime.datetime.utcnow()
    )
    return _punch_item_dict(session, item)


@app.post("/inspection-evidence")
def record_evidence(request: RecordEvidenceRequest):
    session = get_session()
    evidence = punch_items_module.record_inspection_evidence(
        session, request.punch_item_id, request.inspector, request.note, datetime.datetime.utcnow()
    )
    return {"id": evidence.id, "punch_item_id": evidence.punch_item_id}


@app.post("/punch-items/close")
def close_punch_item(request: ClosePunchItemRequest):
    session = get_session()
    try:
        punch_items_module.close_punch_item(
            session, request.punch_item_id, request.evidence_id, datetime.datetime.utcnow()
        )
    except punch_items_module.CloseoutRefused as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    item = session.get(PunchItem, request.punch_item_id)
    return _punch_item_dict(session, item)


@app.post("/rfis")
def create_rfi(request: OpenRfiRequest):
    session = get_session()
    rfi = rfi_module.open_rfi(
        session, request.level, request.room, request.drawing_sheet, request.question, datetime.datetime.utcnow()
    )
    return _rfi_dict(session, rfi, datetime.datetime.utcnow())


@app.post("/rfis/answer")
def answer_rfi(request: AnswerRfiRequest):
    session = get_session()
    rfi_module.answer_rfi(session, request.rfi_id, request.answer_text, datetime.datetime.utcnow())
    rfi = session.get(Rfi, request.rfi_id)
    return _rfi_dict(session, rfi, datetime.datetime.utcnow())


@app.get("/rooms/{level}/{room}/turnover")
def room_turnover(level: str, room: str):
    session = get_session()
    result = attempt_room_turnover(session, level, room, datetime.datetime.utcnow())
    return {
        "level": result.level,
        "room": result.room,
        "allowed": result.allowed,
        "blocking_punch_items": [
            {"id": i.id, "description": i.description} for i in result.blocking_punch_items
        ],
        "blocking_rfis": [{"id": r.id, "question": r.question} for r in result.blocking_rfis],
        "message": result.refusal_message(),
    }
