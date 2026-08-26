import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.db import make_engine, make_session


@pytest.fixture()
def session():
    engine = make_engine("sqlite:///:memory:")
    return make_session(engine)
