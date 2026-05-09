"""
회사 신고 결과 cross-check.

원칙:
- 단정적 표현 금지. '오류' 대신 '차이 발견' / '확인 필요' 톤.
- 반올림 오차(1,000원 미만)는 자동으로 'minor' 로 분류해 잡음 줄임.
- 단계별 anchor 를 함께 실어 사용자가 어느 법령 단계에서 갈렸는지 추적 가능.
"""

from __future__ import annotations

from app.schemas.analysis_schema import AnalyzeRequest
from app.schemas.tax_calculator_schema import CalcInputs, DependentsInput
from app.schemas.verification_schema import (
    CompanyFiling,
    Severity,
    StepDiff,
    VerificationReport,
)
from app.services.tax_calculator import calculate


# 비교할 필드 (tax_calculator 의 attribute 이름 == CompanyFiling 의 attribute 이름)
_COMPARABLE_FIELDS: list[tuple[str, str]] = [
    ("earned_income_deduction", "근로소득공제"),
    ("earned_income_amount", "근로소득금액"),
    ("personal_deduction", "인적공제"),
    ("taxable_income", "과세표준"),
    ("calculated_tax", "산출세액"),
    ("earned_income_tax_credit", "근로소득세액공제"),
    ("determined_tax", "결정세액"),
    ("local_income_tax", "지방소득세"),
]

MINOR_THRESHOLD = 1000  # 1,000원 미만은 반올림 오차로 분류


def _classify(delta: int) -> Severity:
    if delta == 0:
        return "match"
    if abs(delta) < MINOR_THRESHOLD:
        return "minor"
    return "major"


def _to_calc_inputs(
    req: AnalyzeRequest,
    filing: CompanyFiling,
    extra_income_deductions: int = 0,
    extra_tax_credits: int = 0,
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
        prepaid_tax=filing.prepaid_tax,
    )


def _build_summary(
    has_major: bool, has_minor: bool, missing_count: int, final_delta: int | None
) -> str:
    if has_major:
        if final_delta is not None and final_delta < 0:
            # our_total < company_total → 회사 신고가 더 큼 → 사용자가 환급 더 받을 수 있음
            return (
                "의미 있는 차이가 발견됐어요. 자체 산식보다 회사 신고가 부담이 더 큰 단계가 있어, "
                "검토 후 수정 신고를 고려해볼 수 있습니다. 입력값과 누락 공제 항목부터 다시 확인해보세요."
            )
        if final_delta is not None and final_delta > 0:
            return (
                "의미 있는 차이가 발견됐어요. 자체 산식이 결정세액을 더 크게 보고 있어요. "
                "회사 신고에서 빠진 공제 항목이 있는지, 또는 사용자가 입력한 공제 합산이 정확한지 다시 확인이 필요합니다."
            )
        return "의미 있는 차이가 발견됐어요. 단계별 비교를 살펴보세요."
    if has_minor:
        return "단계별로 1,000원 미만 차이만 있어요. 반올림 오차 범위로 보입니다."
    if missing_count > 0:
        return (
            f"비교 가능한 단계는 모두 일치합니다. 다만 {missing_count}개 단계는 회사 신고 값이 "
            "제공되지 않아 비교를 건너뛰었어요."
        )
    return "모든 비교 단계가 일치합니다. 자체 산식과 회사 신고가 동일한 결과를 가리켜요."


def verify(
    request: AnalyzeRequest,
    filing: CompanyFiling,
    extra_income_deductions: int = 0,
    extra_tax_credits: int = 0,
) -> VerificationReport:
    """자체 산식 vs 회사 신고 비교 리포트."""

    inputs = _to_calc_inputs(
        request, filing, extra_income_deductions, extra_tax_credits
    )
    our = calculate(inputs)

    # CalcStep 에서 anchor 매핑 추출
    anchors_by_name = {s.name: s.legal_anchor for s in our.steps}

    steps: list[StepDiff] = []
    has_major = False
    has_minor = False
    missing_count = 0

    for field, label in _COMPARABLE_FIELDS:
        our_val = getattr(our, field)
        co_val = getattr(filing, field, None)
        anchor = anchors_by_name.get(field)

        if co_val is None:
            missing_count += 1
            steps.append(
                StepDiff(
                    name=field,
                    label=label,
                    legal_anchor=anchor,
                    our_value=our_val,
                    company_value=None,
                    delta=None,
                    severity="missing",
                    note="회사 신고 값이 제공되지 않아 비교 불가",
                )
            )
            continue

        delta = our_val - co_val
        severity = _classify(delta)
        if severity == "major":
            has_major = True
        elif severity == "minor":
            has_minor = True

        steps.append(
            StepDiff(
                name=field,
                label=label,
                legal_anchor=anchor,
                our_value=our_val,
                company_value=co_val,
                delta=delta,
                severity=severity,
            )
        )

    # 회사 총 부담세액 — local_income_tax 가 빠졌으면 결정세액 × 10% 추정
    if filing.local_income_tax is None:
        company_total = filing.determined_tax + int(
            round(filing.determined_tax * 0.10)
        )
    else:
        company_total = filing.determined_tax + filing.local_income_tax

    final_delta = our.total_tax - company_total
    refund_delta = -final_delta  # 양수: 자체 산식 환급이 회사보다 더 크다는 뜻

    summary = _build_summary(has_major, has_minor, missing_count, final_delta)

    return VerificationReport(
        year=our.year,
        our_total=our.total_tax,
        company_total=company_total,
        final_delta=final_delta,
        refund_delta=refund_delta,
        steps=steps,
        summary=summary,
        has_major_diff=has_major,
    )
