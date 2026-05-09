"""
Phase 4-1: 다년도 시뮬레이션 엔진.

== 흐름 ==
baseline AnalyzeRequest → CalcInputs 변환 → calculate() (베이스라인)
                                          ↘ 각 YearOverride: 직전 연도 inputs 에 override 덮어씀
                                            → calculate() 재실행

== 한계 ==
- 현재는 모든 연도가 동일한 세율표 (data/tax_tables/2025.json) 사용.
  실제 세법 변경 반영은 v2 (per-year 세율표).
- 비과세/상여 같은 부가 항목은 베이스라인 값 고정.
"""

from __future__ import annotations

from app.schemas.analysis_schema import AnalyzeRequest
from app.schemas.simulate_schema import (
    SimulateRequest,
    SimulateResponse,
    YearOverride,
    YearProjection,
)
from app.schemas.tax_calculator_schema import CalcInputs, DependentsInput
from app.services.tax_calculator import calculate


def _to_calc_inputs(
    req: AnalyzeRequest,
    *,
    prepaid_tax: int = 0,
    extra_income_deductions: int = 0,
    extra_tax_credits: int = 0,
    use_standard_tax_credit: bool = True,
) -> CalcInputs:
    deps = DependentsInput(
        self_eligible=True,
        spouse=bool(req.dependents.has_spouse),
        dependents_count=req.dependents.dependents_count or 0,
        senior_count=req.dependents.senior_count or 0,
        disabled_count=req.dependents.disabled_count or 0,
        female_householder=bool(req.dependents.female_householder),
        single_parent=bool(req.dependents.single_parent),
    )
    return CalcInputs(
        gross_salary=req.income.total_salary or 0,
        non_taxable=req.income.non_taxable or 0,
        dependents=deps,
        extra_income_deductions=extra_income_deductions,
        extra_tax_credits=extra_tax_credits,
        use_standard_tax_credit=use_standard_tax_credit,
        prepaid_tax=prepaid_tax,
    )


def _apply_override(prev: CalcInputs, ov: YearOverride) -> CalcInputs:
    """직전 연도 inputs 에 override 를 덮어써 새 연도 inputs 생성."""
    deps = prev.dependents.model_copy()
    if ov.spouse is not None:
        deps.spouse = ov.spouse
    if ov.dependents_count is not None:
        deps.dependents_count = ov.dependents_count
    if ov.senior_count is not None:
        deps.senior_count = ov.senior_count
    if ov.disabled_count is not None:
        deps.disabled_count = ov.disabled_count
    if ov.female_householder is not None:
        deps.female_householder = ov.female_householder
    if ov.single_parent is not None:
        deps.single_parent = ov.single_parent

    return CalcInputs(
        gross_salary=ov.gross_salary if ov.gross_salary is not None else prev.gross_salary,
        non_taxable=prev.non_taxable,
        dependents=deps,
        extra_income_deductions=(
            ov.extra_income_deductions
            if ov.extra_income_deductions is not None
            else prev.extra_income_deductions
        ),
        extra_tax_credits=(
            ov.extra_tax_credits
            if ov.extra_tax_credits is not None
            else prev.extra_tax_credits
        ),
        use_standard_tax_credit=prev.use_standard_tax_credit,
        prepaid_tax=ov.prepaid_tax if ov.prepaid_tax is not None else prev.prepaid_tax,
    )


def simulate(req: SimulateRequest) -> SimulateResponse:
    baseline_inputs = _to_calc_inputs(
        req.baseline_request,
        prepaid_tax=req.baseline_prepaid_tax,
        extra_income_deductions=req.extra_income_deductions,
        extra_tax_credits=req.extra_tax_credits,
        use_standard_tax_credit=req.use_standard_tax_credit,
    )
    baseline_result = calculate(baseline_inputs, year=req.baseline_year)
    baseline_proj = YearProjection(
        year=req.baseline_year,
        note="현재(베이스라인)",
        inputs_used=baseline_inputs,
        result=baseline_result,
    )

    projections: list[YearProjection] = []
    prev = baseline_inputs
    for ov in req.years:
        new_inputs = _apply_override(prev, ov)
        result = calculate(new_inputs, year=req.baseline_year)
        projections.append(
            YearProjection(
                year=ov.year,
                note=ov.note,
                inputs_used=new_inputs,
                result=result,
            )
        )
        prev = new_inputs

    cumulative_refund = baseline_result.refund_or_owed + sum(
        p.result.refund_or_owed for p in projections
    )
    cumulative_total_tax = baseline_result.total_tax + sum(
        p.result.total_tax for p in projections
    )

    return SimulateResponse(
        baseline_year=req.baseline_year,
        baseline=baseline_proj,
        projections=projections,
        cumulative_refund=cumulative_refund,
        cumulative_total_tax=cumulative_total_tax,
    )
