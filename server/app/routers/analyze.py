from fastapi import APIRouter
from app.schemas.analysis_schema import AnalyzeRequest, AnalyzeResponse

from app.services.rules_engine import build_rule_context
from app.services.llm_client import generate_analysis

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_tax(data: AnalyzeRequest):
    """
    PAGE 7: 전체 데이터 기반 Why 분석
    - 프론트에서 user-input / pdf-parse / manual-input 결과를 모두 전달
    - 규칙엔진 → LLM 분석으로 흐름 구성
    """

    # 1) 규칙 엔진: 기준 충족 여부 & 계산
    rule_context = build_rule_context(
        income=data.income,
        dependents=data.dependents,
        conditions=data.conditions,
        parsed_pdf=data.parsed_pdf,
        manual_input=data.manual_input,
    )

    # 2) LLM Why 분석
    summary, sections, tax_tips = await generate_analysis(
        income=data.income,
        dependents=data.dependents,
        conditions=data.conditions,
        parsed_pdf=data.parsed_pdf,
        manual_input=data.manual_input,
        rule_context=rule_context,
    )

    return AnalyzeResponse(
        summary=summary,
        sections=sections,
        tax_tips=tax_tips,
    )
