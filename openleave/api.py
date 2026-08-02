"""OpenLeave determinations API.

Run with: .venv/bin/uvicorn openleave.api:app --reload
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import DISCLAIMER, __version__, determine
from .facts import Facts
from .wagehour import WageFacts, assess_wage_hour

app = FastAPI(title="OpenLeave", version=__version__, description=DISCLAIMER)

_CHECKER = Path(__file__).parent / "checker.html"
_WAGE_CHECKER = Path(__file__).parent / "wage_checker.html"


class DeterminationRequest(BaseModel):
    facts: Facts
    as_of: date | None = None


class WageHourRequest(BaseModel):
    facts: WageFacts
    as_of: date | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "engine_version": __version__}


@app.post("/determinations")
def determinations(request: DeterminationRequest) -> dict:
    return determine(request.facts, as_of=request.as_of)


@app.post("/wage-hour/determinations")
def wage_hour_determinations(request: WageHourRequest) -> dict:
    return assess_wage_hour(request.facts, as_of=request.as_of)


@app.get("/", response_class=HTMLResponse)
def checker() -> str:
    return _CHECKER.read_text()


@app.get("/wage-hour", response_class=HTMLResponse)
def wage_checker() -> str:
    return _WAGE_CHECKER.read_text()
