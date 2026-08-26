import datetime
import os

import pytest
from sqlalchemy.exc import OperationalError

from app.db import make_engine, make_session
from app.punch_items import close_punch_item, open_punch_item, punch_item_status, record_inspection_evidence


def test_postgresql_backend_skips_cleanly_when_not_running():
    """PostgreSQL is not installed as a service on the build machine (see
    playbooks/BUILDER.md section 3). This exercises the real PostgreSQL
    path when TRACKER_DATABASE_URL points at a live server, and skips
    cleanly otherwise."""
    url = os.environ.get("TRACKER_DATABASE_URL")
    if not url:
        pytest.skip("TRACKER_DATABASE_URL not set; no PostgreSQL instance configured")
    try:
        engine = make_engine(url)
        session = make_session(engine)
    except OperationalError:
        pytest.skip("PostgreSQL not reachable")

    opened = datetime.datetime(2026, 5, 1)
    item = open_punch_item(session, "L01", "R001", "A-101", "wall paint touch-up needed", opened)
    evidence = record_inspection_evidence(session, item.id, "J. Ruiz", "verified", opened)
    close_punch_item(session, item.id, evidence_id=evidence.id, closed_at=opened)
    assert punch_item_status(session, item.id) == "closed"
