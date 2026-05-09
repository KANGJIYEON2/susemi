"""
Phase 4-1: 다년도 시뮬레이션 스키마.

- 베이스라인 inputs (현재 상태) + 연도별 override 리스트 → 연도별 tax_calculator 결과
- override 는 'inherit from previous year' 디폴트. None 인 필드는 직전 연도 값을 그대로 가져감.
- 모든 연도가 동일한 세율표를 사용 (현재는 2025 단년만 지원). 미래 세법 변경은 v2.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.analysis_schema import AnalyzeRequest
from app.schemas.tax_calculator_schema import CalcInputs, CalcResult


class YearOverride(BaseModel):
    """1개 연도에 적용할 변경. None 이면 이전 연도 값을 그대로 사용."""

    year: int = Field(..., description="대상 연도 (예: 2026)")
    gross_salary: int | None = None
    spouse: bool | None = None
    dependents_count: int | None = None
    senior_count: int | None = None
    disabled_count: int | None = None
    female_householder: bool | None = None
    single_parent: bool | None = None
    extra_income_deductions: int | None = None
    extra_tax_credits: int | None = None
    prepaid_tax: int | None = None
    note: str | None = Field(default=None, description="연도 라벨 (예: '결혼 + 자녀 출생')")


class SimulateRequest(BaseModel):
    baseline_request: AnalyzeRequest = Field(
        ..., description="현재 입력 (위저드 결과)"
    )
    baseline_year: int = 2025
    baseline_prepaid_tax: int = Field(default=0, ge=0)
    use_standard_tax_credit: bool = True
    extra_income_deductions: int = Field(default=0, ge=0)
    extra_tax_credits: int = Field(default=0, ge=0)
    years: list[YearOverride] = Field(default_factory=list, max_length=10)


class YearProjection(BaseModel):
    year: int
    note: str | None = None
    inputs_used: CalcInputs
    result: CalcResult


class SimulateResponse(BaseModel):
    baseline_year: int
    baseline: YearProjection
    projections: list[YearProjection]
    cumulative_refund: int = Field(
        ..., description="베이스라인 + 모든 연도의 refund_or_owed 합 (양수=환급 누적)"
    )
    cumulative_total_tax: int
