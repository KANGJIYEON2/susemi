from typing import Tuple, List
from openai import AsyncOpenAI
import os
import json
import re

from app.schemas.user_input_schema import Income, Dependents, Conditions
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.manual_input_schema import ManualInputRequest
from app.schemas.analysis_schema import Summary, Section
from app.schemas.rag_schema import SearchHit
from app.services.rules_engine import RuleContext

# OpenAI 클라이언트는 lazy init — 테스트 환경에서 모듈 로드 시점 OPENAI_API_KEY 미설정 회피.
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# -------------------------------
# 0) 포맷 도우미
# -------------------------------

def fmt_money(v) -> str:
    if v is None:
        return "데이터 없음"
    try:
        return f"{int(v):,}원"
    except Exception:
        return str(v)

def fmt_bool(b) -> str:
    if b is None:
        return "판단 불가(데이터 없음)"
    return "예" if b else "아니오"


def extract_json(text: str) -> str:
    """LLM이 출력한 문자열에서 JSON 한 덩어리만 추출"""
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(f"JSON 시작/끝을 찾지 못했습니다: {text}")

    json_str = text[start:end+1]

    # 자동 정리
    json_str = re.sub(r"\n\s*\n", "\n", json_str)
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*\]", "]", json_str)

    return json_str


# -------------------------------
# 1) SYSTEM 프롬프트
# -------------------------------

SYSTEM_PROMPT = """
당신은 대한민국 2025년 기준 연말정산 Why 분석 전문가입니다.
항상 JSON만 출력해야 하며, 계산은 하지 않고 규칙엔진 결과만 사용합니다.
법령 조항을 인용할 때는 반드시 시스템이 제공한 [rule_id] 마커만 사용하고,
시스템이 주지 않은 법령은 인용하지 마세요.
"""


# -------------------------------
# 2) build_prompt
# -------------------------------

def _format_rules_for_prompt(rule_context: RuleContext) -> str:
    """평가된 룰들을 LLM 이 anchor 로 인용할 수 있게 라벨/근거 형태로 직렬화."""
    if not rule_context.evaluations:
        return "(평가된 룰 없음)"

    lines: List[str] = []
    for ev in rule_context.evaluations:
        result_label = (
            "충족" if ev.result is True
            else ("미충족" if ev.result is False else "판단불가")
        )
        computed_str = ", ".join(
            f"{k}={fmt_money(v) if isinstance(v, int) else v}"
            for k, v in ev.computed.items()
        )
        lines.append(
            f"- [{ev.rule_id}] {ev.title} | 근거: {ev.legal_anchor}\n"
            f"    공식: {ev.formula or '-'}\n"
            f"    결과: {result_label} | {computed_str}"
        )
    return "\n".join(lines)


def _format_rag_for_prompt(rag_hits: List[SearchHit]) -> str:
    """RAG top-K 법령 청크를 LLM 컨텍스트 블록으로 직렬화."""
    if not rag_hits:
        return "(인덱싱된 법령 없음 — admin 에서 /rag/index 후 다시 시도하세요)"
    lines: List[str] = []
    for i, hit in enumerate(rag_hits, start=1):
        c = hit.chunk
        # 본문이 너무 길면 자름 (LLM 토큰 보호)
        text = c.text.strip().replace("\n", " ")
        if len(text) > 280:
            text = text[:280] + "…"
        lines.append(f"[{i}] {c.law_name} §{c.article_no}{c.paragraph_no or ''} — {text}")
    return "\n".join(lines)


def build_prompt(
    income: Income,
    dependents: Dependents,
    conditions: Conditions,
    parsed_pdf: ParsedPdfData,
    manual_input: ManualInputRequest,
    rule_context: RuleContext,
    rag_hits: List[SearchHit] | None = None,
) -> str:

    rules_block = _format_rules_for_prompt(rule_context)
    rag_block = _format_rag_for_prompt(rag_hits or [])

    return f"""
당신은 2025년 한국 근로소득 연말정산 전문가입니다.
사용자의 모든 입력을 바탕으로 공제 항목별 'Why 분석'을 JSON으로 설명하세요.

아래 규칙을 **절대 어기지 마세요**:
- 반드시 JSON만 출력하세요.
- highlight 문장은 1~2줄 핵심 요약
- detail 문장은 **반드시 최소 5줄 이상** 작성하세요.
- detail에는 다음을 포함:
    1) 해당 공제 제도의 구조 및 법적 근거 요약
    2) 사용자가 왜 기준을 충족/미충족 했는지 단계별 분석
    3) 데이터가 없더라도 사례 기반 설명 (예: "일반적으로 OO 공제를 받으려면…")
    4) 기준 충족 시 어떤 혜택이 발생하는지 시뮬레이션 설명
    5) 사용자가 향후 같은 항목에서 공제를 받기 위해 해야 할 행동 제안

== Provenance (출처 anchor) ==
- 시스템이 제공한 [rule_id] 마커만 인용 가능. 그 외 임의 법령 인용 금지.
- 특정 룰의 결과/계산을 언급하는 detail 문장 끝에 [rule_id] 를 그대로 넣으세요.
  예: "총급여의 25% 기준에 미달했어요 [card_25_threshold]."
- 룰이 적용되지 않는 섹션(예: donation, other) 은 마커를 비워도 됩니다.
- 절대로 내부 변수명(rule_context.xxx, parsed_pdf.xxx 등)을 그대로 노출하지 마세요.

- 데이터가 부족한 경우:
    → "데이터 없음"이라 끝내지 말고 반드시 공제 제도의 원리 + 실제 사례를 덧붙여 설명하세요.

- tips 항목은 반드시 2~4개 작성하며, 구체적인 행동 제안.

- 숫자는 주어진 값을 그대로 사용하고 직접 계산하지 마세요.
- JSON 외 텍스트 금지.

--- 사용자 데이터 ---

【소득 정보】
총급여: {fmt_money(income.total_salary)}
비과세: {fmt_money(income.non_taxable)}
상여금: {fmt_money(income.bonus)}

【인적공제】
배우자: {dependents.has_spouse}
부양가족 수: {dependents.dependents_count}
장애인: {dependents.disabled_count}
경로우대: {dependents.senior_count}
한부모: {dependents.single_parent}
부녀자: {dependents.female_householder}

【조건】
세대주: {conditions.householder}
무주택: {conditions.no_house}
임대차계약: {conditions.lease_contract}
대출 여부: {conditions.has_loan}
자녀 교육비: {conditions.child_education}
본인 교육비: {conditions.self_education}
중소기업 재직: {conditions.mid_small_company_worker}

【PDF 파싱】
신용카드: {fmt_money(parsed_pdf.credit_card)}
체크카드: {fmt_money(parsed_pdf.debit_card)}
현금영수증: {fmt_money(parsed_pdf.cash_receipt)}
의료비: {fmt_money(parsed_pdf.medical_expense)}
기부금: {fmt_money(parsed_pdf.donation_total)}
PDF 월세: {fmt_money(parsed_pdf.rent_in_pdf)}
간편 공제 타입: {parsed_pdf.tax_credit_type}

【수기 입력】
추가 기부금: {fmt_money(manual_input.donation_extra)}
수기 월세: {manual_input.rent}
가족 의료비: {manual_input.family_medical_expenses}
안경/콘택트렌즈: {fmt_money(manual_input.glasses_contacts_expense)}
산후조리원: {fmt_money(manual_input.childbirth_care_expense)}

【규칙엔진 평가 결과 — 반드시 이것만 사용】
{rules_block}

【참고 법령 본문 (RAG 검색 결과) — 인용 가능, 임의 법령 추가 금지】
{rag_block}

---

### JSON OUTPUT FORMAT

{{
  "summary": {{
    "headline": "",
    "key_points": []
  }},
  "sections": [
    {{
      "id": "card",
      "title": "신용카드 등 사용액",
      "highlight": "",
      "detail": "",
      "tips": []
    }},
    {{
      "id": "medical",
      "title": "의료비",
      "highlight": "",
      "detail": "",
      "tips": []
    }},
    {{
      "id": "donation",
      "title": "기부금",
      "highlight": "",
      "detail": "",
      "tips": []
    }},
    {{
      "id": "rent_loan",
      "title": "월세 / 주택자금대출",
      "highlight": "",
      "detail": "",
      "tips": []
    }},
    {{
      "id": "other",
      "title": "기타 교육비 / 보험 / 연금",
      "highlight": "",
      "detail": "",
      "tips": []
    }}
  ],
  "tax_tips": []
}}
"""


# -------------------------------
# 3) LLM 호출 함수
# -------------------------------

async def generate_analysis(
    income: Income,
    dependents: Dependents,
    conditions: Conditions,
    parsed_pdf: ParsedPdfData,
    manual_input: ManualInputRequest,
    rule_context: RuleContext,
    rag_hits: List[SearchHit] | None = None,
) -> Tuple[Summary, List[Section], List[str]]:

    prompt = build_prompt(
        income,
        dependents,
        conditions,
        parsed_pdf,
        manual_input,
        rule_context,
        rag_hits=rag_hits,
    )

    response = await _get_client().chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content

    # 1차 파싱
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        cleaned = extract_json(content)
        try:
            raw = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM JSON 파싱 실패(자동수정도 실패): {content}"
            ) from e

    summary = Summary(**raw["summary"])
    # provenance 는 백엔드가 채우므로 LLM 출력에서 빠져 있어도 OK
    sections = [Section(**sec) for sec in raw["sections"]]
    tax_tips = raw.get("tax_tips", [])

    return summary, sections, tax_tips
