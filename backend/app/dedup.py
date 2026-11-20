"""Collapses near-identical field reports (punch items and RFIs opened
against the same room) into one group. The mechanism is domain-neutral,
the same shape as `routing.py`: a fixed similarity rule over text, not a
classifier and not an embedding. It genuinely does not understand a true
paraphrase with no shared words; see the README "Honest framing" for what
that costs.

`same_room_only=False` reproduces this extension's first, broken design
(see README "What broke"): comparing every report in the dataset against
every other report, regardless of location, instead of restricting
comparison to reports already known to be in the same room.
"""
from __future__ import annotations

from dataclasses import dataclass

SIMILARITY_THRESHOLD = 0.5


@dataclass(frozen=True)
class ReportRecord:
    """One field report (a punch item or an RFI) in the shape dedup needs.
    Built from `PunchItem`/`Rfi` rows by `requirements.py`; this module
    never touches the database."""

    report_id: str  # "punch:<id>" or "rfi:<id>", unique across both tables
    level: str
    room: str
    discipline: str
    text: str


def _tokens(text: str) -> set[str]:
    return set(text.lower().replace("/", " ").replace("-", " ").split())


def similarity(a: str, b: str) -> float:
    """Jaccard similarity over whitespace-tokenized, lowercased text."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def find_duplicate_groups(
    reports: list[ReportRecord],
    same_room_only: bool = True,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[list[ReportRecord]]:
    """Union-find clustering: two reports merge when their text's Jaccard
    similarity is at or above `threshold`, and (when `same_room_only`,
    the default) they also share a (level, room). Restricting to the same
    room first is a prefilter exactly like `autolabel`'s grid prefilter in
    the sibling tracking project: it is what makes an exact O(n^2) text
    comparison cheap enough to run on the full dataset, not an
    approximation.
    """
    if same_room_only:
        buckets: dict[tuple[str, str], list[ReportRecord]] = {}
        for r in reports:
            buckets.setdefault((r.level, r.room), []).append(r)
        groups: list[list[ReportRecord]] = []
        for bucket in buckets.values():
            groups.extend(_cluster(bucket, threshold))
        return groups
    return _cluster(reports, threshold)


def _cluster(reports: list[ReportRecord], threshold: float) -> list[list[ReportRecord]]:
    parent = {r.report_id: r.report_id for r in reports}

    def find(x: str) -> str:
        while parent[x] != x:
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(len(reports)):
        for j in range(i + 1, len(reports)):
            a, b = reports[i], reports[j]
            if similarity(a.text, b.text) >= threshold:
                union(a.report_id, b.report_id)

    grouped: dict[str, list[ReportRecord]] = {}
    for r in reports:
        grouped.setdefault(find(r.report_id), []).append(r)
    return list(grouped.values())
