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
당신은 대한민국 2025년 기준 연말정산 Why 분석 전문가이자, 세무 법령 해설가입니다.
항상 JSON만 출력해야 하며, 계산은 하지 않고 규칙엔진 결과만 사용합니다.

핵심 원칙:
1. 법령 조항을 인용할 때는 반드시 시스템이 제공한 [rule_id] 마커만 사용하세요.
2. 【참고 법령 본문】이 주어지면 반드시 해당 조문 번호(§)와 핵심 문구를 detail에 직접 인용하세요.
3. 단순 요약이 아닌, "왜 이 결과가 나왔는지" 법적 근거 → 수치 대입 → 판정 흐름으로 설명하세요.
4. 시스템이 주지 않은 법령은 인용하지 마세요.
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
        if len(text) > 500:
            text = text[:500] + "…"
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
당신은 2025년 한국 근로소득 연말정산 WHY 분석 전문가입니다.
사용자의 데이터 + 규칙엔진 평가 + 법령 본문을 결합해, **왜 이 결과가 나왔는지** 법적 근거까지 포함한 심층 분석을 JSON으로 작성하세요.

━━━ 절대 규칙 ━━━

1. **JSON만 출력.** JSON 외 텍스트 금지.
2. **숫자는 주어진 값 그대로 사용.** 직접 계산하지 마세요.
3. **내부 변수명 노출 금지** (rule_context.xxx, parsed_pdf.xxx 등).

━━━ detail 작성 가이드 (핵심) ━━━

각 section의 detail은 **반드시 아래 구조를 따르세요** (최소 8줄 이상):

**① 법적 근거** — 【참고 법령 본문】에서 해당 조문을 인용.
  - 조문 번호(§)와 핵심 문구를 직접 따옴표로 인용
  - 예: 소득세법 §52조 제1항에 따르면 "근로소득이 있는 거주자가 ... 기본공제대상자를 위하여 지급한 의료비"가 공제 대상입니다.
  - 법령 본문이 없으면 규칙엔진의 legal_anchor 를 명시

**② 사용자 수치 대입** — 실제 수치를 법적 기준에 대입해 판정 과정을 보여줌.
  - 예: 총급여 33,000,000원의 3%인 990,000원이 의료비 공제 최저한이며, 실제 지출 717,400원은 이에 272,600원 미달합니다.

**③ 판정 결과 + [rule_id]** — 충족/미충족 판정과 그 의미.
  - 관련 룰이 있으면 문장 끝에 [rule_id] 마커 부착
  - 예: "따라서 의료비 세액공제 요건을 충족하지 못했습니다 [medical_3_threshold]."

**④ 공제 혜택 시뮬레이션** — 충족 시 예상 절세 효과, 미충족 시 얼마나 더 필요한지.
  - 예: 272,600원만 추가 지출하면 초과분부터 15% 세액공제를 받을 수 있습니다.

**⑤ 실행 가능한 전략** — 내년에 이 공제를 받기 위한 구체적 행동.

━━━ Provenance (출처) ━━━

- 시스템이 제공한 [rule_id] 마커만 인용 가능. 임의 법령 인용 금지.
- 【참고 법령 본문】의 조문은 "소득세법 §XX조" 형식으로 인용하되, 시스템이 준 범위만.
- 룰이 없는 섹션(donation, other)은 마커 없이 법령 본문만 참조.

━━━ 데이터가 부족한 항목 ━━━

"데이터 없음" 으로 끝내지 마세요. 반드시:
- 해당 공제의 법적 요건 + 공제율/한도를 법령 본문 기반으로 설명
- 이 사용자의 소득 구간에서 공제받으면 얼마나 절세되는지 예시 제시
- 내년에 공제받기 위한 구체적 조건과 준비사항

━━━ tips ━━━

- 각 section 2~4개, **구체적 금액 또는 행동** 포함.
- 나쁜 예: "의료비를 늘리세요" → 좋은 예: "연간 의료비가 990,000원을 넘으면 초과분의 15%를 돌려받습니다. 정기검진·치과·한의원 지출도 포함되니 영수증을 모아두세요."

━━━ highlight ━━━

1~2문장 핵심 판정. 금액과 충족/미충족을 명시.

━━━ summary ━━━

- headline: 이 사용자의 연말정산을 한 문장으로 (예: "신용카드 공제는 충족, 의료비·월세는 기준 미달로 추가 절세 여지가 있습니다")
- key_points: 3~5개. 각각 핵심 숫자 + 판정 + 한 줄 조언 포함.

━━━ 사용자 데이터 ━━━

【소득 정보】
총급여: {fmt_money(income.total_salary)}
비과세: {fmt_money(income.non_taxable)}
상여금: {fmt_money(income.bonus)}

【인적공제】
배우자: {fmt_bool(dependents.has_spouse)}
부양가족 수: {dependents.dependents_count}명
장애인: {dependents.disabled_count}명
경로우대: {dependents.senior_count}명
한부모: {fmt_bool(dependents.single_parent)}
부녀자: {fmt_bool(dependents.female_householder)}

【조건】
세대주: {fmt_bool(conditions.householder)}
무주택: {fmt_bool(conditions.no_house)}
임대차계약: {fmt_bool(conditions.lease_contract)}
대출 여부: {fmt_bool(conditions.has_loan)}
자녀 교육비: {fmt_bool(conditions.child_education)}
본인 교육비: {fmt_bool(conditions.self_education)}
중소기업 재직: {fmt_bool(conditions.mid_small_company_worker)}

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

【참고 법령 본문 (RAG 검색 결과) — 조문 인용 가능, 임의 법령 추가 금지】
{rag_block}

---

### JSON OUTPUT FORMAT

{{
  "summary": {{
    "headline": "",
    "key_points": ["핵심 숫자 + 판정 + 조언 형태로 3~5개"]
  }},
  "sections": [
    {{
      "id": "card",
      "title": "신용카드 등 사용액 공제",
      "highlight": "",
      "detail": "",
      "tips": []
    }},
    {{
      "id": "medical",
      "title": "의료비 세액공제",
      "highlight": "",
      "detail": "",
      "tips": []
    }},
    {{
      "id": "donation",
      "title": "기부금 세액공제",
      "highlight": "",
      "detail": "",
      "tips": []
    }},
    {{
      "id": "rent_loan",
      "title": "월세 · 주택자금대출 공제",
      "highlight": "",
      "detail": "",
      "tips": []
    }},
    {{
      "id": "other",
      "title": "교육비 · 보험료 · 연금 공제",
      "highlight": "",
      "detail": "",
      "tips": []
    }}
  ],
  "tax_tips": ["내년 절세를 위한 종합 행동 제안 3~5개"]
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
        max_tokens=4000,
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
