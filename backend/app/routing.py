"""Routes a punch item or RFI description to a responsible discipline.

A fixed, ordered keyword table, checked top to bottom; the first match
wins, and anything that matches nothing routes to architectural, the
catch-all discipline for finish, layout and general-construction items.
This is a disclosed simplification: a real routing step would let a
superintendent override a bad guess, this one only proposes one.
"""
from __future__ import annotations

_RULES: list[tuple[str, str]] = [
    # MEP first: mechanical, electrical and plumbing vocabulary is the most
    # specific and least likely to collide with a general-construction word.
    ("duct", "mep"),
    ("hvac", "mep"),
    ("diffuser", "mep"),
    ("chiller", "mep"),
    ("sprinkler", "mep"),
    ("plumbing", "mep"),
    ("pipe", "mep"),
    ("valve", "mep"),
    ("conduit", "mep"),
    ("panelboard", "mep"),
    ("breaker", "mep"),
    ("outlet", "mep"),
    ("switchgear", "mep"),
    ("fire alarm", "mep"),
    # Structural next.
    ("beam", "structural"),
    ("column", "structural"),
    ("footing", "structural"),
    ("foundation", "structural"),
    ("slab", "structural"),
    ("rebar", "structural"),
    ("shear wall", "structural"),
    ("steel connection", "structural"),
    # Everything else is architectural: finishes, doors, walls, ceilings,
    # layout, paint, casework.
]

_DEFAULT_DISCIPLINE = "architectural"


def route_discipline(description: str) -> str:
    text = description.lower()
    for keyword, discipline in _RULES:
        if keyword in text:
            return discipline
    return _DEFAULT_DISCIPLINE
