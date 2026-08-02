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


def test_wage_checker_page_served():
    r = client.get("/wage-hour")
    assert r.status_code == 200
    assert "Wage" in r.text


def test_wage_hour_endpoint_minimum_wage():
    r = client.post(
        "/wage-hour/determinations",
        json={"facts": {"work_state": "CA", "hourly_rate": 15.0}, "as_of": "2026-02-01"},
    )
    assert r.status_code == 200
    data = r.json()
    mw = next(t for t in data["topics"] if t["topic"] == "minimum_wage")
    assert mw["data"]["applicable_minimum"] == 16.90
    assert mw["data"]["rate_compliant"] is False  # $15 is below the 2026 floor
    assert data["disclaimer"]
    assert all(f["citation"]["ref"] for t in data["topics"] for f in t["findings"])


def test_wage_hour_endpoint_final_pay():
    r = client.post(
        "/wage-hour/determinations",
        json={
            "facts": {
                "work_state": "CA",
                "hourly_rate": 30.0,
                "separation": {"type": "fired", "last_day": "2026-03-02",
                               "final_pay_date": "2026-03-07", "accrued_vacation_hours": 40},
            },
            "as_of": "2026-03-02",
        },
    )
    assert r.status_code == 200
    fp = next(t for t in r.json()["topics"] if t["topic"] == "final_pay")
    assert fp["data"]["deadline"] == "2026-03-02"  # due immediately on firing
    assert fp["data"]["vacation_payout_owed"] == 1200.0


def test_wage_hour_locality_coverage_warning():
    r = client.post(
        "/wage-hour/determinations",
        json={"facts": {"work_state": "WA", "hourly_rate": 17.13, "work_locality": "Seattle"},
              "as_of": "2026-02-01"},
    )
    assert r.json()["coverage"]["complete"] is False
