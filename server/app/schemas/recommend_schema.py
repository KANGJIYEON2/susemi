"""
Phase 4-3: What-if greedy 추천 스키마.

원칙:
- delta(환급 증가분)만으로 정렬하되, '비용 라벨'로 사용자가 실제 부담을 볼 수 있게.
  예) "월세 신청": 추가 비용 없음. "연금저축 +400만": 추가 납입 400만 필요.
- 정확도/신뢰도 향상은 v2 (한도·소득별 세율 차등 등 정밀화).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis_schema import AnalyzeRequest


LeverKind = Literal["tax_credit", "income_deduction"]


class Lever(BaseModel):
    """추천 1개의 메타데이터 (실행 함수는 코드에서 별도 매핑)."""

    lever_id: str
    label: str = Field(..., description="사용자에게 보여줄 짧은 한국어 제목")
    description: str = Field(..., description="동작 한 줄 설명")
    legal_anchor: str
    cost_label: str = Field(
        ...,
        description="사용자가 추가로 부담해야 하는 것 (예: '추가 납입 400만원' / '기존 지출, 신청만')",
    )
    kind: LeverKind


class Recommendation(BaseModel):
    lever: Lever
    eligible: bool
    note: str | None = None
    baseline_refund: int
    projected_refund: int
    refund_delta: int = Field(
        ..., description="projected_refund - baseline_refund (양수=환급 더 받음)"
    )


class RecommendRequest(BaseModel):
    request: AnalyzeRequest
    baseline_prepaid_tax: int = 0
    baseline_extra_income_deductions: int = 0
    baseline_extra_tax_credits: int = 0
    use_standard_tax_credit: bool = True


class RecommendResponse(BaseModel):
    baseline_refund: int
    baseline_total_tax: int
    recommendations: list[Recommendation]
