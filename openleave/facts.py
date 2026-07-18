"""Input fact models. These are the API surface — pydantic validates them."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from .engine import LeaveReason


class Employee(BaseModel):
    work_state: str = Field(description="Two-letter state code where the employee works, e.g. CA")
    hire_date: date
    hours_last_12mo: float = Field(ge=0)
    hours_per_week: float | None = Field(default=None, ge=0)
    average_weekly_wage: float | None = Field(default=None, ge=0)
    annual_wages: float | None = Field(
        default=None, ge=0, description="Base-period wages; derived from average_weekly_wage if omitted"
    )


class Employer(BaseModel):
    total_employees: int = Field(ge=1)
    employees_within_75_miles: int | None = Field(
        default=None, ge=0, description="Defaults to total_employees if omitted"
    )


class LeaveEvent(BaseModel):
    type: LeaveReason
    start: date


class Facts(BaseModel):
    employee: Employee
    employer: Employer
    event: LeaveEvent

    @property
    def tenure_months(self) -> float:
        return (self.event.start - self.employee.hire_date).days / 30.44

    @property
    def tenure_weeks(self) -> float:
        return (self.event.start - self.employee.hire_date).days / 7

    @property
    def worksite_headcount(self) -> int:
        emp = self.employer
        return emp.employees_within_75_miles if emp.employees_within_75_miles is not None else emp.total_employees

    @property
    def base_period_wages(self) -> float | None:
        if self.employee.annual_wages is not None:
            return self.employee.annual_wages
        if self.employee.average_weekly_wage is not None:
            return self.employee.average_weekly_wage * 52
        return None
