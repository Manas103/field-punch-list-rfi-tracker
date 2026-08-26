"""Synthetic data generator: punch items and RFIs across many level/room
combinations, described in language the routing table can actually match,
labeled synthetic everywhere it is reported. Not a record of a real jobsite;
a student did not walk thousands of punch items.
"""
from __future__ import annotations

import datetime
import random

from sqlalchemy.orm import Session

from .punch_items import open_punch_item
from .rfi import open_rfi

_PUNCH_DESCRIPTIONS = [
    "duct hanger missing insulation clamp",
    "hvac diffuser installed off center from ceiling grid",
    "sprinkler head clearance below code minimum",
    "conduit run not secured to unistrut",
    "outlet cover plate missing in corridor",
    "panelboard door does not close fully",
    "beam camber exceeds tolerance at gridline",
    "column base plate grout incomplete",
    "slab control joint saw cut missed",
    "footing rebar cover under minimum",
    "door hardware missing closer arm",
    "ceiling tile damaged during MEP rough-in",
    "wall paint touch-up needed at patch",
    "baseboard gap exceeds 1/8 inch",
    "casework drawer misaligned",
]

_RFI_QUESTIONS = [
    "duct routing conflicts with structural beam at this gridline, confirm reroute",
    "hvac unit weight exceeds roof structural capacity shown on drawing, confirm",
    "plumbing riser location not shown on this sheet, confirm routing",
    "electrical panel clearance conflicts with door swing, confirm relocation",
    "beam connection detail not shown for this condition, confirm detail",
    "column schedule conflicts with foundation plan at this gridline",
    "slab depression dimension unclear at this location, confirm depth",
    "wall type at this partition does not match legend, confirm type",
    "ceiling height conflicts with duct depth shown, confirm clearance",
    "door swing conflicts with adjacent casework, confirm orientation",
]


def build_synthetic_dataset(
    session: Session,
    rng: random.Random,
    num_levels: int = 10,
    rooms_per_level: int = 50,
    target_punch_items: int = 2600,
    target_rfis: int = 420,
    opened_on: datetime.datetime = datetime.datetime(2026, 5, 1),
) -> dict:
    """Opens `target_punch_items` punch items and `target_rfis` RFIs across
    `num_levels * rooms_per_level` rooms, round-robin so every room gets at
    least one punch item and coverage is as even as the totals allow.
    Returns the room list and per-room item/RFI id lists so callers (tests,
    the turnover-gate seeding script) can pick specific rooms to close out
    or leave open.
    """
    rooms = [(f"L{level:02d}", f"R{room:03d}") for level in range(1, num_levels + 1) for room in range(1, rooms_per_level + 1)]
    assert len(rooms) * 1 <= target_punch_items, "not enough punch items to give every room at least one"

    punch_ids_by_room: dict = {room: [] for room in rooms}
    rfi_ids_by_room: dict = {room: [] for room in rooms}

    for i in range(target_punch_items):
        level, room = rooms[i % len(rooms)]
        description = rng.choice(_PUNCH_DESCRIPTIONS)
        sheet = f"A-{(i % 40) + 100}"
        item = open_punch_item(session, level, room, sheet, description, opened_on)
        punch_ids_by_room[(level, room)].append(item.id)

    for i in range(target_rfis):
        level, room = rooms[i % len(rooms)]
        question = rng.choice(_RFI_QUESTIONS)
        sheet = f"A-{(i % 40) + 100}"
        rfi = open_rfi(session, level, room, sheet, question, opened_on)
        rfi_ids_by_room[(level, room)].append(rfi.id)

    return {
        "rooms": rooms,
        "punch_ids_by_room": punch_ids_by_room,
        "rfi_ids_by_room": rfi_ids_by_room,
        "punch_item_count": target_punch_items,
        "rfi_count": target_rfis,
    }
