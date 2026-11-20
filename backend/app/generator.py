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

# Near-duplicate rewordings of the lists above, one per entry, at the same
# index: a different reporter describing the same issue in slightly
# different words (reordered clauses, an added "please"/"the"/"is"), not a
# true paraphrase with no shared vocabulary. Measured Jaccard token
# similarity against the original is 0.64-1.0 for every entry (see
# docs/dedup_benchmark_output.txt), comfortably above dedup.py's 0.5
# threshold; this is the honest limit of a keyword-overlap dedup rule, not
# an accident of these specific sentences (see README "Honest framing").
_PUNCH_NEAR_DUPLICATES = [
    "insulation clamp missing from duct hanger",
    "hvac diffuser off center from the ceiling grid, installed incorrectly",
    "sprinkler head clearance is below the code minimum",
    "conduit run is not secured to the unistrut",
    "outlet cover plate is missing in the corridor",
    "panelboard door does not fully close",
    "beam camber at the gridline exceeds tolerance",
    "column base plate grout is incomplete",
    "slab control joint saw cut was missed",
    "footing rebar cover is under the minimum",
    "door hardware is missing a closer arm",
    "ceiling tile was damaged during mep rough-in",
    "wall paint touch up is needed at the patch",
    "baseboard gap exceeds 1/8 of an inch",
    "casework drawer is misaligned",
]

_RFI_NEAR_DUPLICATES = [
    "duct routing conflicts with the structural beam at this gridline, please confirm reroute",
    "hvac unit weight exceeds the roof structural capacity shown on the drawing, please confirm",
    "plumbing riser location is not shown on this sheet, confirm the routing",
    "electrical panel clearance conflicts with the door swing, confirm the relocation",
    "beam connection detail is not shown for this condition, please confirm detail",
    "column schedule conflicts with the foundation plan at this gridline",
    "slab depression dimension is unclear at this location, confirm the depth",
    "wall type at this partition does not match the legend, please confirm type",
    "ceiling height conflicts with the duct depth shown, confirm the clearance",
    "door swing conflicts with the adjacent casework, confirm the orientation",
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


def build_dedup_ground_truth_corpus(
    session: Session,
    rng: random.Random,
    num_rooms: int = 100,
    opened_on: datetime.datetime = datetime.datetime(2026, 9, 1),
) -> dict:
    """A dedicated corpus for measuring dedup accuracy against a known
    truth, separate from the 2,600/420 production dataset above. Each of
    `num_rooms` rooms gets exactly one "root" report (a punch item or an
    RFI, alternating), a seeded 0-3 near-duplicate rewordings of it (from
    `_PUNCH_NEAR_DUPLICATES` / `_RFI_NEAR_DUPLICATES`), and exactly one
    "distractor" report describing a genuinely different issue in the same
    room, so the measurement exercises both "must merge" and "must not
    merge" within the one room a dedup rule actually has to decide between.

    Returns `{"true_groups": {root_report_id: frozenset(all_ids_in_truth)},
    "distractor_ids": set(...)}`; a caller runs `find_duplicate_groups` on
    the full corpus and compares its predicted groups against this truth.
    """
    true_groups: dict[str, frozenset] = {}
    distractor_ids: set[str] = set()

    for i in range(num_rooms):
        level, room = f"D{i // 20:02d}", f"T{i % 20:03d}"
        sheet = f"A-{(i % 40) + 100}"
        vocab_index = i % len(_PUNCH_DESCRIPTIONS)
        num_duplicates = rng.randint(0, 3)

        if i % 2 == 0:
            root = open_punch_item(session, level, room, sheet, _PUNCH_DESCRIPTIONS[vocab_index], opened_on)
            root_id = f"punch:{root.id}"
            group_ids = {root_id}
            for _ in range(num_duplicates):
                dup = open_punch_item(session, level, room, sheet, _PUNCH_NEAR_DUPLICATES[vocab_index], opened_on)
                group_ids.add(f"punch:{dup.id}")
            distractor_text = _PUNCH_DESCRIPTIONS[(vocab_index + 1) % len(_PUNCH_DESCRIPTIONS)]
            distractor = open_punch_item(session, level, room, sheet, distractor_text, opened_on)
            distractor_ids.add(f"punch:{distractor.id}")
        else:
            root = open_rfi(session, level, room, sheet, _RFI_QUESTIONS[vocab_index % len(_RFI_QUESTIONS)], opened_on)
            root_id = f"rfi:{root.id}"
            group_ids = {root_id}
            rfi_vocab_index = vocab_index % len(_RFI_QUESTIONS)
            for _ in range(num_duplicates):
                dup = open_rfi(session, level, room, sheet, _RFI_NEAR_DUPLICATES[rfi_vocab_index], opened_on)
                group_ids.add(f"rfi:{dup.id}")
            distractor_text = _RFI_QUESTIONS[(rfi_vocab_index + 1) % len(_RFI_QUESTIONS)]
            distractor = open_rfi(session, level, room, sheet, distractor_text, opened_on)
            distractor_ids.add(f"rfi:{distractor.id}")

        true_groups[root_id] = frozenset(group_ids)

    return {"true_groups": true_groups, "distractor_ids": distractor_ids}
