"""
tax_calculator 의 입출력 스키마.

핵심 원칙:
- 모든 금액은 정수(원 단위). float 누적 오차 회피.
- 단계별 산출 결과를 CalcStep 으로 trail. Phase 3-1 Provenance 와 직접 연결.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DependentsInput(BaseModel):
    """인적공제 대상 인원수 — 소득/나이 요건은 호출자가 사전에 필터함."""

    self_eligible: bool = Field(
        default=True, description="본인 공제(거의 항상 True, 비거주자 등 예외만 False)"
    )
    spouse: bool = Field(default=False, description="배우자 공제 자격 여부")
    dependents_count: int = Field(default=0, description="기본 부양가족 수 (배우자 제외)")
    senior_count: int = Field(default=0, description="경로우대(만 70세 이상) 인원수")
    disabled_count: int = Field(default=0, description="장애인 인원수")
    female_householder: bool = Field(default=False, description="부녀자 공제 자격")
    single_parent: bool = Field(default=False, description="한부모 (single_parent True 시 female_householder 자동 무효)")


class CalcInputs(BaseModel):
    """tax_calculator 입력."""

    gross_salary: int = Field(..., description="총급여 (세전, 비과세 제외 후)")
    non_taxable: int = Field(default=0, description="비과세 급여 (현재는 정보 보관용, 산식에 미사용)")
    dependents: DependentsInput = Field(default_factory=DependentsInput)

    # Phase 2-1 단계에서는 항목별 정밀 산식 미구현.
    # 외부에서 합산값을 계산해 넘기는 단순 구조.
    extra_income_deductions: int = Field(
        default=0, description="기본 인적공제 외 소득공제 합 (예: 신용카드, 주택임차차입금 등)"
    )
    extra_tax_credits: int = Field(
        default=0, description="근로소득세액공제·표준세액공제 외 세액공제 합 (예: 자녀, 의료비, 기부금)"
    )
    use_standard_tax_credit: bool = Field(
        default=True,
        description="True 면 표준세액공제 13만 적용. extra_tax_credits 와는 별개로 합산.",
    )

    prepaid_tax: int = Field(default=0, description="기납부세액 (회사가 원천징수한 국세분)")


class CalcStep(BaseModel):
    """단계별 계산 trail. Provenance 의 building block."""

    name: str = Field(..., description="단계 ID (예: 'earned_income_deduction')")
    label: str = Field(..., description="사람이 읽는 라벨")
    legal_anchor: str | None = None
    formula: str | None = Field(
        default=None, description="적용 공식 요약 (예: '750만 + (총급여-1500만)×15%')"
    )
    inputs: dict[str, Any] = Field(default_factory=dict)
    output: int = Field(..., description="이 단계 산출값 (정수, 원)")


class CalcResult(BaseModel):
    """tax_calculator 출력."""

    # 핵심 산출
    earned_income_deduction: int
    earned_income_amount: int  # 근로소득금액
    personal_deduction: int  # 기본+추가 인적공제 합
    taxable_income: int  # 과세표준
    calculated_tax: int  # 산출세액
    earned_income_tax_credit: int
    standard_tax_credit: int
    extra_tax_credits: int
    determined_tax: int  # 결정세액 (국세분)
    local_income_tax: int  # 지방소득세
    total_tax: int  # 총 부담세액 (국세 + 지방)

    # 비교
    prepaid_tax: int
    refund_or_owed: int = Field(
        ...,
        description="prepaid_tax - total_tax. 양수=환급, 음수=추징.",
    )

    # provenance
    steps: list[CalcStep]
    year: int = 2025
