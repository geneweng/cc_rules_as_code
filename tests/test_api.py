from fastapi.testclient import TestClient

from openleave.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_checker_page_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "OpenLeave" in r.text


def test_determination_endpoint():
    body = {
        "facts": {
            "employee": {
                "work_state": "MN",
                "hire_date": "2025-03-01",
                "hours_last_12mo": 1400,
                "average_weekly_wage": 1100,
            },
            "employer": {"total_employees": 85},
            "event": {"type": "bonding", "start": "2026-09-01"},
        }
    }
    r = client.post("/determinations", json=body)
    assert r.status_code == 200
    data = r.json()
    mn = next(x for x in data["regimes"] if x["regime"] == "mn_paid_leave")
    assert mn["eligible"] is True
    assert data["disclaimer"]
    assert all(f["citation"]["ref"] for reg in data["regimes"] for f in reg["findings"])


def test_validation_rejects_bad_input():
    r = client.post("/determinations", json={"facts": {"employee": {"work_state": "CA"}}})
    assert r.status_code == 422
