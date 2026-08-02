"""Input fact models for wage-and-hour determinations.

Unlike leave (which reasons about a discrete `LeaveEvent`), wage-and-hour reasons
about ongoing employment and, optionally, a separation. These are pydantic models,
so they double as the validated API surface.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class PayBasis(str, Enum):
    HOURLY = "hourly"
    SALARY = "salary"


class SeparationType(str, Enum):
    FIRED = "fired"
    LAID_OFF = "laid_off"
    QUIT_WITH_NOTICE = "quit_with_notice"  # at least 72 hours' notice (matters in CA)
    QUIT_WITHOUT_NOTICE = "quit_without_notice"


class Separation(BaseModel):
    type: SeparationType
    last_day: date = Field(description="Last day of employment")
    final_pay_date: date | None = Field(
        default=None, description="When the employer actually paid final wages, to check compliance"
    )
    accrued_vacation_hours: float | None = Field(
        default=None, ge=0, description="Unused accrued vacation/PTO at separation (hours)"
    )


class WageFacts(BaseModel):
    work_state: str = Field(description="Two-letter state code where the employee works, e.g. CA")
    work_locality: str | None = Field(
        default=None,
        description="City/county slug if known, e.g. 'seattle'. Localities may set higher minimums.",
    )
    employer_total_employees: int = Field(default=1, ge=1)
    pay_basis: PayBasis = PayBasis.HOURLY
    hourly_rate: float | None = Field(
        default=None, ge=0, description="Effective hourly cash wage, for the minimum-wage check"
    )
    is_tipped: bool = Field(default=False, description="Employee regularly receives tips")
    weekly_hours: float | None = Field(default=None, ge=0)
    separation: Separation | None = Field(
        default=None, description="Present when assessing final-pay-on-separation rules"
    )
