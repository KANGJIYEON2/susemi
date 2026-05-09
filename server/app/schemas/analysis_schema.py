from typing import List

from pydantic import BaseModel, Field

from app.schemas.manual_input_schema import ManualInputRequest
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.rule_schema import RuleEvaluation
from app.schemas.user_input_schema import Conditions, Dependents, Income


# ----- 요청 -----


class AnalyzeRequest(BaseModel):
    income: Income
    dependents: Dependents
    conditions: Conditions
    parsed_pdf: ParsedPdfData
    manual_input: ManualInputRequest


# ----- 응답 -----


class Summary(BaseModel):
    headline: str
    key_points: List[str]


class Section(BaseModel):
    """
    LLM 이 생성하는 항목별 해설 + 백엔드가 붙이는 구조화 근거(provenance).

    - id/title/highlight/detail/tips: LLM 생성
    - provenance: 백엔드가 룰 평가 결과를 매핑해 부착 (Phase 3-1)
    - LLM 의 detail 텍스트 안에 [rule_id] 마커가 있으면 UI 가 anchor 로 렌더링
    """

    id: str
    title: str
    highlight: str
    detail: str
    tips: List[str] | None = None
    provenance: List[RuleEvaluation] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    summary: Summary
    sections: List[Section]
    tax_tips: List[str]
    # 전체 룰 평가 결과 (UI 가 모든 anchor 를 참조해야 할 때)
    evaluations: List[RuleEvaluation] = Field(default_factory=list)
