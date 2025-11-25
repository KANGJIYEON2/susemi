from typing import Tuple, List
from openai import AsyncOpenAI
import os
import json
import re

from app.schemas.user_input_schema import Income, Dependents, Conditions
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.manual_input_schema import ManualInputRequest
from app.schemas.analysis_schema import Summary, Section
from app.services.rules_engine import RuleContext

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
당신은 대한민국 2024년 기준 연말정산 Why 분석 전문가입니다.
항상 JSON만 출력해야 하며, 계산은 하지 않고 규칙엔진 결과만 사용합니다.
"""


# -------------------------------
# 2) build_prompt
# -------------------------------

def build_prompt(
    income: Income,
    dependents: Dependents,
    conditions: Conditions,
    parsed_pdf: ParsedPdfData,
    manual_input: ManualInputRequest,
    rule_context: RuleContext,
) -> str:

    return f"""
당신은 2024년 한국 근로소득 연말정산 전문가입니다.
사용자의 모든 입력을 바탕으로 공제 항목별 'Why 분석'을 JSON으로 설명하세요.

아래 규칙을 **절대 어기지 마세요**:
- 반드시 JSON만 출력하세요.
- highlight 문장은 1~2줄 핵심 요약
- detail 문장은 **반드시 최소 5줄 이상** 작성하세요.
- detail에는 기본 설명 외에도 아래 내용을 반드시 포함하세요:
    1) 해당 공제 제도의 구조 및 법적 근거 요약
    2) 사용자가 왜 기준을 충족하지 못했는지 단계별 분석
    3) 데이터가 없더라도 사례 기반 설명 (예: “일반적으로 OO 공제를 받으려면…”)
    4) 기준 충족 시 어떤 혜택이 발생하는지 시뮬레이션 설명
    5) 사용자가 향후 같은 항목에서 공제를 받기 위해 해야 할 행동 제안

- 데이터가 부족한 경우:
    → “데이터 없음”이라 끝내지 말고 반드시 공제 제도의 원리 + 실제 사례를 덧붙여 설명하세요.

- evidence 필드는 간단한 문자열 또는 근거 요약 객체로 작성하세요.
  (예: "의료비 총합이 기준금액보다 낮아 공제 요건 미충족")

- tips 항목은 반드시 2~4개 작성하며,
  구체적인 행동을 제시해야 함:
    예: "내년에는 의료비 지출 영수증을 잘 보관하세요."
        "현금영수증도 신용카드 공제 항목에 포함됩니다."
        "기부금은 공제율이 높으니 20만원 이하라도 효과적입니다."

- 절대로 내부 변수명(rule_context.xxx, parsed_pdf.xxx 등)을 그대로 노출하지 마세요.
- 숫자는 주어진 값을 그대로 사용하고 직접 계산하지 마세요.
- JSON 외 텍스트 금지.

--- 사용자 데이터 ---

【소득 정보】
총급여: {income.total_salary:,}원
비과세: {income.non_taxable:,}원
상여금: {income.bonus:,}원

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
신용카드: {parsed_pdf.credit_card:,}원
체크카드: {parsed_pdf.debit_card:,}원
현금영수증: {parsed_pdf.cash_receipt:,}원
의료비: {parsed_pdf.medical_expense:,}원
기부금: {parsed_pdf.donation_total:,}원
PDF 월세: {parsed_pdf.rent_in_pdf:,}원
간편 공제 타입: {parsed_pdf.tax_credit_type}

【수기 입력】
추가 기부금: {manual_input.donation_extra:,}원
수기 월세: {manual_input.rent}
가족 의료비: {manual_input.family_medical_expenses}
안경/콘택트렌즈: {manual_input.glasses_contacts_expense:,}원
산후조리원: {manual_input.childbirth_care_expense:,}원

【규칙 엔진 결과】
카드 총 사용액: {fmt_money(rule_context.card_total_usage)}
카드 25% 기준: {fmt_money(rule_context.card_threshold_25)}
카드 기준 충족: {fmt_bool(rule_context.card_meets_threshold)}

의료비 총합: {fmt_money(rule_context.medical_total)}
의료비 3% 기준: {fmt_money(rule_context.medical_threshold_3)}
의료비 기준 충족: {fmt_bool(rule_context.medical_meets_threshold)}

월세 요건 충족: {fmt_bool(rule_context.rent_conditions_met)}
PDF 월세 금액: {fmt_money(parsed_pdf.rent_in_pdf)}

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
      "evidence": null,
      "tips": []
    }},
    {{
      "id": "medical",
      "title": "의료비",
      "highlight": "",
      "detail": "",
      "evidence": null,
      "tips": []
    }},
    {{
      "id": "donation",
      "title": "기부금",
      "highlight": "",
      "detail": "",
      "evidence": null,
      "tips": []
    }},
    {{
      "id": "rent_loan",
      "title": "월세 / 주택자금대출",
      "highlight": "",
      "detail": "",
      "evidence": null,
      "tips": []
    }},
    {{
      "id": "other",
      "title": "기타 교육비 / 보험 / 연금",
      "highlight": "",
      "detail": "",
      "evidence": null,
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
) -> Tuple[Summary, List[Section], List[str]]:

    prompt = build_prompt(
        income, dependents, conditions, parsed_pdf, manual_input, rule_context
    )

    response = await client.chat.completions.create(
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
    except:
        # JSON만 추출
        cleaned = extract_json(content)
        try:
            raw = json.loads(cleaned)
        except:
            raise ValueError(f"LLM JSON 파싱 실패(자동수정도 실패): {content}")

    summary = Summary(**raw["summary"])
    sections = [Section(**sec) for sec in raw["sections"]]
    tax_tips = raw.get("tax_tips", [])

    return summary, sections, tax_tips
