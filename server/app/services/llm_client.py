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
from app.schemas.tax_calculator_schema import CalcResult
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


def _format_calc_for_prompt(calc: CalcResult | None) -> str:
    """세금 산식 결과를 LLM 이 참조할 수 있는 블록으로 직렬화."""
    if calc is None:
        return "(세금 산식 실행 불가 — 소득 데이터 부족)"
    lines = [
        f"근로소득공제: {calc.earned_income_deduction:,}원",
        f"근로소득금액: {calc.earned_income_amount:,}원",
        f"인적공제: {calc.personal_deduction:,}원",
        f"과세표준: {calc.taxable_income:,}원",
        f"산출세액: {calc.calculated_tax:,}원",
        f"근로소득세액공제: {calc.earned_income_tax_credit:,}원",
        f"표준세액공제: {calc.standard_tax_credit:,}원",
        f"기타 세액공제: {calc.extra_tax_credits:,}원",
        f"결정세액(국세): {calc.determined_tax:,}원",
        f"지방소득세: {calc.local_income_tax:,}원",
        f"총 부담세액: {calc.total_tax:,}원",
        f"기납부세액: {calc.prepaid_tax:,}원",
        f"환급/추징: {calc.refund_or_owed:,}원 ({'환급' if calc.refund_or_owed > 0 else '추징' if calc.refund_or_owed < 0 else '정산 완료'})",
    ]
    if calc.itemized_breakdown:
        lines.append("── 항목별 세액공제 ──")
        label_map = {
            "child_tax_credit": "자녀세액공제",
            "medical_credit": "의료비 세액공제",
            "donation_credit": "기부금 세액공제",
        }
        for k, v in calc.itemized_breakdown.items():
            lines.append(f"  {label_map.get(k, k)}: {v:,}원")
    return "\n".join(lines)


def build_prompt(
    income: Income,
    dependents: Dependents,
    conditions: Conditions,
    parsed_pdf: ParsedPdfData,
    manual_input: ManualInputRequest,
    rule_context: RuleContext,
    rag_hits: List[SearchHit] | None = None,
    calc_result: CalcResult | None = None,
) -> str:

    rules_block = _format_rules_for_prompt(rule_context)
    rag_block = _format_rag_for_prompt(rag_hits or [])
    calc_block = _format_calc_for_prompt(calc_result)

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

**④ 세금 산식 기반 절세 시뮬레이션** — 【자체 세금 산식 결과】의 실제 세액을 인용.
  - 반드시 결정세액, 환급/추징 금액을 명시
  - 충족 시: "현재 결정세액 X원에서 이 공제로 Y원이 줄어 Z원을 추가 환급받을 수 있습니다"
  - 미충족 시: "현재 결정세액 X원이며, 의료비를 Y원 더 지출하면 초과분의 15%인 Z원을 절세할 수 있습니다"
  - 환급/추징 상태도 언급: "현재 기납부세액 대비 A원 환급/추징 예상입니다"

**⑤ 실행 가능한 전략** — 내년에 이 공제를 받기 위한 구체적 행동 + 예상 절세 금액.

━━━ Provenance (출처) ━━━

- 시스템이 제공한 [rule_id] 마커만 인용 가능. 임의 법령 인용 금지.
- 【참고 법령 본문】의 조문은 "소득세법 §XX조" 형식으로 인용하되, 시스템이 준 범위만.
- 룰이 없는 섹션(donation, other)은 마커 없이 법령 본문만 참조.

━━━ 데이터가 부족한 항목 ━━━

"데이터 없음" 으로 끝내지 마세요. 반드시:
- 해당 공제의 법적 요건 + 공제율/한도를 법령 본문 기반으로 설명
- 이 사용자의 소득 구간에서 공제받으면 얼마나 절세되는지 예시 제시
- 내년에 공제받기 위한 구체적 조건과 준비사항

━━━ 공제 항목별 세부 구조 (2025년 귀속) ━━━

각 section 작성 시 반드시 아래 세부율과 한도를 반영하세요.

【1. 신용카드 등 소득공제 — 조세특례제한법 §126의2】
결제수단별 공제율 (총급여 25% 초과분에 적용):
- 신용카드: 15% / 체크카드·현금영수증: 30% / 전통시장: 40% / 대중교통: 40%
- 도서·공연·영화·박물관 등 문화비: 30% (총급여 7천만원 이하만)
기본한도: 7천만 이하 300만원, 초과 250만원
추가한도 (전통시장+대중교통+문화비): 7천만 이하 300만원, 초과 200만원
공제 순서: 신용카드(15%) → 체크카드(30%) → 문화비(30%) → 전통시장·대중교통(40%)
→ card tips에 반드시: 체크카드 전환(30% vs 15%), 전통시장 40%, 문화비 30% 전략 포함

【2. 의료비 세액공제 — 소득세법 §59의4 ②】
최저한: 총급여의 3% 초과분부터 공제
공제율: 일반 15% / 난임시술 30% / 미숙아·선천이상 20%
한도: 본인·65세이상·장애인·6세이하 = 한도 없음 / 일반 부양가족 = 연 700만원
특수: 안경·콘택트렌즈 1인 50만원 한도 / 산후조리원 출산 1회 200만원 (소득제한 폐지)
→ tips에: 3% 넘기기 전략, 가족 의료비 몰아주기, 라식·라섹·보청기도 대상, 영수증 수집

【3. 교육비 세액공제 — 소득세법 §59의4 ③】
공제율: 15%
한도: 본인 한도없음 / 취학전 아동 300만원 / 초중고 300만원 / 대학생 900만원 / 장애인특수교육 한도없음
특수: 교복·체육복 1인 50만원 (간소화 미반영, 영수증 직접 제출) / 취학전 학원비 (주1회이상)
→ tips에: 교복 영수증 챙기기, 취학전 학원비(태권도 등) 공제 가능

【4. 보험료 세액공제 — 소득세법 §59의4 ①】
일반 보장성 보험: 12%, 한도 100만원 / 장애인전용 보장성 보험: 15%, 한도 100만원 (별도)
최대 세액공제: 일반 12만원 + 장애인전용 15만원 = 27만원

【5. 연금저축·IRP 세액공제 — 소득세법 §59의3】
연금저축 단독: 600만원 / 연금저축+IRP 합산: 900만원
공제율: 총급여 5,500만 이하 16.5%, 초과 13.2% (지방세 포함)
최대 환급: 900만 × 16.5% = 148.5만원
→ tips에: 12월 중순까지 납입, IRP 300만 추가로 한도 확대, ISA 전환 추가공제

【6. 월세 세액공제 — 조세특례제한법 §95의2】
공제율: 총급여 5,500만 이하 17%, 5,500~8,000만 15%, 8,000만 초과 불가
한도: 연 1,000만원 (2024년~ 상향)
요건: 무주택 세대주(원), 85㎡ 이하 또는 기준시가 4억 이하
→ tips에: 확정일자·임대차계약서·주민등록등본 준비, 현금영수증 발급 신청 가능

【7. 기부금 세액공제 — 소득세법 §59의4 ④】
정치자금: 10만 이하 100/110(≈90.9%), 10만~3천만 15%, 3천만 초과 25%
고향사랑: 10만 이하 100%, 10만 초과 15%. 한도 2,000만. + 답례품 3만원
법정·지정: 1천만 이하 15%, 초과 30%. 종교단체 소득 10% 한도, 그 외 30% 한도

【8. 놓치기 쉬운 항목 — other 섹션에서 반드시 언급】
- 중소기업 청년 소득세 90% 감면 (5년간, 연 200만 한도) — 조세특례제한법 §30
- 주택청약저축 소득공제: 연 300만원 한도, 40% (총급여 7천만 이하 무주택 세대주)
- 결혼세액공제: 혼인신고 시 부부 각 50만원 (2024~2026, 생애 1회)

━━━ tips ━━━

- 각 section 3~5개, **구체적 금액 또는 행동** 포함.
- 나쁜 예: "의료비를 늘리세요" → 좋은 예: "연간 의료비가 990,000원을 넘으면 초과분의 15%를 돌려받습니다. 정기검진·치과·한의원 지출도 포함되니 영수증을 모아두세요."
- card tips에서는 반드시: 체크카드 전환 권유(30% vs 15%), 전통시장/대중교통 활용(40%), 문화비 활용(30%) 등 결제수단별 전략 포함.

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

【자체 세금 산식 결과 — 실제 계산된 세액. 이 숫자를 반드시 detail에서 인용】
{calc_block}

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
    calc_result: CalcResult | None = None,
) -> Tuple[Summary, List[Section], List[str]]:

    prompt = build_prompt(
        income,
        dependents,
        conditions,
        parsed_pdf,
        manual_input,
        rule_context,
        rag_hits=rag_hits,
        calc_result=calc_result,
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
