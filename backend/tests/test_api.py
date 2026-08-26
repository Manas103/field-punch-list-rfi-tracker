from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_open_close_and_turnover_over_http():
    created = client.post(
        "/punch-items",
        json={"level": "L09", "room": "R901", "drawing_sheet": "A-101", "description": "wall paint touch-up needed"},
    ).json()
    assert created["status"] == "open"
    assert created["discipline"] == "architectural"

    refused = client.post("/rooms/L09/R901/turnover")
    # GET is the real route; confirm it via GET below, this call 404s and
    # is here only to document the route is not accidentally a POST.
    assert refused.status_code == 405

    blocked = client.get("/rooms/L09/R901/turnover").json()
    assert blocked["allowed"] is False
    assert blocked["blocking_punch_items"][0]["id"] == created["id"]

    evidence = client.post(
        "/inspection-evidence",
        json={"punch_item_id": created["id"], "inspector": "J. Ruiz", "note": "verified"},
    ).json()
    closed = client.post(
        "/punch-items/close", json={"punch_item_id": created["id"], "evidence_id": evidence["id"]}
    ).json()
    assert closed["status"] == "closed"

    allowed = client.get("/rooms/L09/R901/turnover").json()
    assert allowed["allowed"] is True


def test_close_without_evidence_returns_409():
    created = client.post(
        "/punch-items",
        json={"level": "L09", "room": "R902", "drawing_sheet": "A-101", "description": "door hardware missing closer arm"},
    ).json()
    response = client.post("/punch-items/close", json={"punch_item_id": created["id"], "evidence_id": 999999})
    assert response.status_code == 409
    assert str(created["id"]) in response.json()["detail"]


def test_rfi_open_and_answer_over_http():
    created = client.post(
        "/rfis",
        json={
            "level": "L09",
            "room": "R903",
            "drawing_sheet": "M-201",
            "question": "duct routing conflicts with beam, confirm reroute",
        },
    ).json()
    assert created["status"] == "open"
    assert created["discipline"] == "mep"

    answered = client.post("/rfis/answer", json={"rfi_id": created["id"], "answer_text": "reroute approved"}).json()
    assert answered["status"] == "answered"
