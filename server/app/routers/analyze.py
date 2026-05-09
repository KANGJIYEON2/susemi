from fastapi import APIRouter

from app.schemas.analysis_schema import AnalyzeRequest, AnalyzeResponse, Section
from app.schemas.rule_schema import RuleEvaluation
from app.services.llm_client import generate_analysis
from app.services.rules_engine import build_rule_context

router = APIRouter()


# 섹션 → 관련 룰 ID 매핑 (Phase 3-1 Provenance).
# 룰이 추가되면 여기에 등록해야 해당 섹션에 anchor 가 붙음.
SECTION_TO_RULE_IDS: dict[str, list[str]] = {
    "card": ["card_25_threshold"],
    "medical": ["medical_3_threshold"],
    "rent_loan": ["rent_eligibility"],
    "donation": [],
    "other": [],
}


def _attach_provenance(
    sections: list[Section],
    evaluations: list[RuleEvaluation],
) -> list[Section]:
    """섹션 ID 기준으로 룰 평가 결과를 provenance 로 부착."""
    by_id = {ev.rule_id: ev for ev in evaluations}
    out: list[Section] = []
    for sec in sections:
        wanted = SECTION_TO_RULE_IDS.get(sec.id, [])
        prov = [by_id[rid] for rid in wanted if rid in by_id]
        out.append(sec.model_copy(update={"provenance": prov}))
    return out


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_tax(data: AnalyzeRequest):
    """
    PAGE 7: 전체 데이터 기반 Why 분석.
    1) 규칙엔진: JSON 룰 평가 → RuleEvaluation 리스트 (각각 legal_anchor 포함)
    2) LLM: 항목별 Why 해설 (detail 안에 [rule_id] 마커 인용)
    3) 백엔드 후처리: 섹션마다 관련 평가 결과를 provenance 로 부착
    """

    rule_context = build_rule_context(
        income=data.income,
        dependents=data.dependents,
        conditions=data.conditions,
        parsed_pdf=data.parsed_pdf,
        manual_input=data.manual_input,
    )

    summary, sections, tax_tips = await generate_analysis(
        income=data.income,
        dependents=data.dependents,
        conditions=data.conditions,
        parsed_pdf=data.parsed_pdf,
        manual_input=data.manual_input,
        rule_context=rule_context,
    )

    # Provenance 부착 — LLM 결과는 변경하지 않고 새 Section 객체로 복제
    sections_with_prov = _attach_provenance(sections, rule_context.evaluations)

    return AnalyzeResponse(
        summary=summary,
        sections=sections_with_prov,
        tax_tips=tax_tips,
        evaluations=rule_context.evaluations,
    )
