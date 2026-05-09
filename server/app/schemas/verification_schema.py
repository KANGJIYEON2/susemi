"""
검증 레이어 (Phase 3-3) 스키마.

== 의도 ==
- 사용자 입력 + 자체 산식 결과 vs 회사가 신고한(원천징수영수증 상의) 결과 비교.
- 차이가 있는 단계를 가시화. **단정적 표현 금지** ('회사가 틀렸다' 류 X).
- 의미 있는 차이는 '확인 필요' 정도의 톤으로.

== 흐름 ==
VerifyRequest → tax_calculator.calculate(...) → 회사 입력값과 단계별 비교 → VerificationReport
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis_schema import AnalyzeRequest


Severity = Literal["match", "minor", "major", "missing"]


class CompanyFiling(BaseModel):
    """
    회사 신고 결과 — 원천징수영수증의 핵심 숫자.
    필수: 결정세액 + 기납부세액. 나머지는 있으면 사용, 없으면 'missing' 처리.
    """

    determined_tax: int = Field(..., description="결정세액 (국세분, 원)")
    prepaid_tax: int = Field(..., description="기납부세액 (회사 원천징수, 원)")

    earned_income_deduction: int | None = None
    earned_income_amount: int | None = None
    personal_deduction: int | None = None
    taxable_income: int | None = None
    calculated_tax: int | None = None
    earned_income_tax_credit: int | None = None
    local_income_tax: int | None = None

    notes: str | None = None


class StepDiff(BaseModel):
    """단계별 비교."""

    name: str
    label: str
    legal_anchor: str | None = None
    our_value: int
    company_value: int | None
    delta: int | None = Field(
        default=None, description="our - company (양수 = 회사 값이 더 작음)"
    )
    severity: Severity
    note: str | None = None


class VerificationReport(BaseModel):
    year: int
    our_total: int = Field(..., description="자체 산식 총 부담세액 (결정세액 + 지방소득세)")
    company_total: int | None = Field(
        default=None, description="회사 신고 총 부담세액"
    )
    final_delta: int | None = Field(
        default=None, description="our_total - company_total"
    )
    refund_delta: int | None = Field(
        default=None,
        description=(
            "양수면 자체 산식이 환급액이 더 크다고 본다는 뜻 — "
            "검토 후 수정 신고 검토 가능."
        ),
    )
    steps: list[StepDiff]
    summary: str
    has_major_diff: bool = False


class VerifyRequest(BaseModel):
    """
    /verify 의 입력. AnalyzeRequest 와 CompanyFiling 모두 필수.
    extra_income_deductions / extra_tax_credits 는 사용자가 별도 합산해 넘김.
    """

    request: AnalyzeRequest
    filing: CompanyFiling
    extra_income_deductions: int = Field(default=0, ge=0)
    extra_tax_credits: int = Field(default=0, ge=0)
