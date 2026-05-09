"""
Phase 4-3: What-if greedy 추천.

== 알고리즘 ==
baseline tax_calculator 결과 vs 각 lever 적용 후 결과 → refund_delta → 정렬.

== 현재 levers (4개) ==
1. pension_400        : 연금저축 한도(400만) 채우기 (세액공제 13.2 / 12%)
2. pension_irp_700    : 연금저축+IRP 합산 700만 (추가 300만 × 13.2 / 12%)
3. donation_100k      : 기부금 10만원 정치자금/특례 (100% 세액공제)
4. rent_credit        : 월세 세액공제 (자격 충족 시) — 가정: 월 60만 × 12개월

== 가정/한계 (v0) ==
- 추천은 baseline 의 extra_tax_credits 에 더해서 측정 (income_deduction 류 lever 는 v1)
- 한도/소득별 세율 차등은 단순화 — 정확 산식은 룰 데이터화 + 검수 필요
- 가족공제·소득별 cap 같은 부가 조건 미반영
"""

from __future__ import annotations

from typing import Callable

from app.schemas.analysis_schema import AnalyzeRequest
from app.schemas.recommend_schema import (
    Lever,
    Recommendation,
    RecommendRequest,
    RecommendResponse,
)
from app.schemas.tax_calculator_schema import CalcInputs, DependentsInput
from app.services.tax_calculator import calculate


# -------------------- baseline 변환 --------------------


def _to_calc_inputs(
    req: AnalyzeRequest,
    *,
    prepaid_tax: int,
    extra_income_deductions: int,
    extra_tax_credits: int,
    use_standard_tax_credit: bool,
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


# -------------------- lever 정의 --------------------


def _pension_credit_rate(gross_salary: int) -> float:
    """연금저축 세액공제율 추정. 총급여 5500만 이하 13.2%, 초과 12%."""
    return 0.132 if gross_salary <= 55_000_000 else 0.12


# 각 lever 의 (메타, eligibility, apply) 튜플
LeverEligibility = Callable[[CalcInputs, AnalyzeRequest], tuple[bool, str | None]]
LeverApply = Callable[[CalcInputs, AnalyzeRequest], CalcInputs]


def _always_eligible(_i: CalcInputs, _r: AnalyzeRequest) -> tuple[bool, str | None]:
    return True, None


def _rent_eligibility(
    _i: CalcInputs, r: AnalyzeRequest
) -> tuple[bool, str | None]:
    cond = r.conditions
    ok = bool(cond.householder and cond.no_house and cond.lease_contract)
    if ok:
        return True, None
    missing = []
    if not cond.householder:
        missing.append("세대주")
    if not cond.no_house:
        missing.append("무주택")
    if not cond.lease_contract:
        missing.append("임대차계약")
    return False, f"요건 미충족 ({' / '.join(missing)})"


def _apply_pension_400(inputs: CalcInputs, _r: AnalyzeRequest) -> CalcInputs:
    rate = _pension_credit_rate(inputs.gross_salary)
    credit = int(round(4_000_000 * rate))
    return inputs.model_copy(
        update={"extra_tax_credits": inputs.extra_tax_credits + credit}
    )


def _apply_pension_irp_700(inputs: CalcInputs, _r: AnalyzeRequest) -> CalcInputs:
    rate = _pension_credit_rate(inputs.gross_salary)
    # 연금저축 400 + IRP 300 = 700, 합산 한도. 추가 300 × rate.
    credit = int(round(3_000_000 * rate))
    return inputs.model_copy(
        update={"extra_tax_credits": inputs.extra_tax_credits + credit}
    )


def _apply_donation_100k(inputs: CalcInputs, _r: AnalyzeRequest) -> CalcInputs:
    # 정치자금/특례기부금 10만원: 100% 세액공제
    return inputs.model_copy(
        update={"extra_tax_credits": inputs.extra_tax_credits + 100_000}
    )


def _apply_rent_credit(inputs: CalcInputs, _r: AnalyzeRequest) -> CalcInputs:
    # 가정: 월 60만 × 12 × 17% (총급여 5500 이하) or 15%
    monthly_rent = 600_000
    rate = 0.17 if inputs.gross_salary <= 55_000_000 else 0.15
    credit = int(round(monthly_rent * 12 * rate))
    return inputs.model_copy(
        update={"extra_tax_credits": inputs.extra_tax_credits + credit}
    )


LEVERS: list[tuple[Lever, LeverEligibility, LeverApply]] = [
    (
        Lever(
            lever_id="pension_400",
            label="연금저축 한도(400만원) 채우기",
            description="연 400만원까지 납입 시 13.2% 세액공제 (총급여 5,500만원 초과는 12%).",
            legal_anchor="소득세법 §59의3",
            cost_label="추가 납입 400만원 (노후자금으로 보존)",
            kind="tax_credit",
        ),
        _always_eligible,
        _apply_pension_400,
    ),
    (
        Lever(
            lever_id="pension_irp_700",
            label="IRP 추가 (연금저축과 합산 700만원)",
            description="연금저축 400만 채운 뒤 IRP 300만 추가 납입.",
            legal_anchor="소득세법 §59의3, 조세특례제한법 §86의2",
            cost_label="추가 납입 300만원 (퇴직 시까지 보존)",
            kind="tax_credit",
        ),
        _always_eligible,
        _apply_pension_irp_700,
    ),
    (
        Lever(
            lever_id="donation_100k",
            label="정치자금 기부금 10만원",
            description="10만원 이하 정치자금 기부금은 100% 세액공제. 사실상 환급 100% 회수.",
            legal_anchor="조세특례제한법 §76",
            cost_label="기부 10만원 (사회 기여, 환급으로 100% 회수)",
            kind="tax_credit",
        ),
        _always_eligible,
        _apply_donation_100k,
    ),
    (
        Lever(
            lever_id="rent_credit",
            label="월세 세액공제 신청",
            description="세대주·무주택·임대차 계약 요건 충족 시 월세액의 17% (총급여 5,500만 초과는 15%).",
            legal_anchor="조세특례제한법 §95의2",
            cost_label="기존 지출 — 신청만 하면 됨",
            kind="tax_credit",
        ),
        _rent_eligibility,
        _apply_rent_credit,
    ),
]


# -------------------- 엔진 --------------------


def recommend(req: RecommendRequest) -> RecommendResponse:
    baseline_inputs = _to_calc_inputs(
        req.request,
        prepaid_tax=req.baseline_prepaid_tax,
        extra_income_deductions=req.baseline_extra_income_deductions,
        extra_tax_credits=req.baseline_extra_tax_credits,
        use_standard_tax_credit=req.use_standard_tax_credit,
    )
    baseline_result = calculate(baseline_inputs)

    recs: list[Recommendation] = []
    for lever, eligibility, apply_fn in LEVERS:
        eligible, note = eligibility(baseline_inputs, req.request)
        if not eligible:
            recs.append(
                Recommendation(
                    lever=lever,
                    eligible=False,
                    note=note,
                    baseline_refund=baseline_result.refund_or_owed,
                    projected_refund=baseline_result.refund_or_owed,
                    refund_delta=0,
                )
            )
            continue

        new_inputs = apply_fn(baseline_inputs, req.request)
        new_result = calculate(new_inputs)
        delta = new_result.refund_or_owed - baseline_result.refund_or_owed
        recs.append(
            Recommendation(
                lever=lever,
                eligible=True,
                note=None,
                baseline_refund=baseline_result.refund_or_owed,
                projected_refund=new_result.refund_or_owed,
                refund_delta=delta,
            )
        )

    # 정렬: 자격 충족 + delta 큰 순. 미적격은 뒤로.
    recs.sort(key=lambda r: (not r.eligible, -r.refund_delta))

    return RecommendResponse(
        baseline_refund=baseline_result.refund_or_owed,
        baseline_total_tax=baseline_result.total_tax,
        recommendations=recs,
    )
