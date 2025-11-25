import os
import json
from typing import List, Tuple

import pymupdf
from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.schemas.pdf_schema import ParsedPdfData


load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


async def _extract_pdf_text(file_bytes: bytes) -> str:
    """
    PDF 바이트에서 전체 텍스트만 싹 뽑는 함수.
    (이미지까지 OCR 하진 않고, 간소화 PDF 기준으로 텍스트만 사용)
    """
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    texts = []
    for page in doc:
        # 텍스트 모드
        texts.append(page.get_text("text"))
    doc.close()

    full_text = "\n\n".join(texts)

    # 혹시 너무 길면 LLM 토큰 보호용으로 적당히 자르기 (필요시 조정)
    max_chars = 15000
    if len(full_text) > max_chars:
        return full_text[:max_chars]
    return full_text


async def _call_llm_for_pdf(pdf_text: str) -> dict:
    """
    PDF 텍스트를 LLM에 던져서
    ParsedPdfData + missing_fields 구조에 맞는 JSON을 받아오는 함수.
    """
    system_prompt = """
너는 2024년 기준 대한민국 근로소득 연말정산 전문가이자 세무사다.
너의 역할은 '연말정산 간소화 서비스 PDF 내용'을 읽고,
세법 기준에 맞게 공제 항목을 구조화하고, 누락되기 쉬운 항목을 추천하는 것이다.

규칙:
- 한국 2024년 소득·세액공제 규정을 기준으로 판단한다.
- PDF 텍스트에 금액이 명시되지 않았으면 해당 항목은 0 으로 둔다.
- 애매하면 0 또는 "unknown" 으로 처리하고, missing_fields 에 이유를 반영한다.
- 금액 단위는 모두 "원" 기준 정수(int)로 맞춘다.
- 출력은 반드시 JSON 하나만, 주석/설명 없이 반환한다.
"""

    user_prompt = f"""
다음은 근로소득자의 연말정산 간소화 PDF 전체 텍스트다.

[PDF_TEXT_START]
{pdf_text}
[PDF_TEXT_END]

이 텍스트를 읽고 아래 스키마에 맞는 JSON 을 만들어라.

스키마(키 이름 고정):
{{
  "credit_card": int,                 // 신용카드 사용액 합계 (없으면 0)
  "debit_card": int,                  // 체크/직불카드 사용액 합계 (없으면 0)
  "cash_receipt": int,                // 현금영수증 사용액 합계 (없으면 0)
  "medical_expense": int,             // 전체 의료비 합계 (없으면 0)
  "severe_medical_for_disabled": int, // 장애인 의료비 (없으면 0)
  "insurance": int,                   // 보장성 보험료 합계 (없으면 0)
  "pension_saving": int,              // 연금저축 납입액 (없으면 0)
  "retirement_pension": int,          // 퇴직연금(DC/IRP 등) 납입액 (없으면 0)
  "donation_total": int,              // 전체 기부금 합계 (없으면 0)
  "housing_loan_interest": int,       // 주택자금대출 이자상환액 (없으면 0)
  "rent_in_pdf": int,                 // PDF에 잡힌 월세 금액 (없으면 0)
  "tax_credit_type": "standard" | "special" | "unknown",
                                      // 특별세액공제를 쓰는지, 표준세액공제인지, 알 수 없으면 "unknown"
  "missing_fields": [
      // 사용자가 간소화 PDF 외에 따로 챙기면 좋은 항목의 키워드 목록
      // 예시: "donation", "housing_loan", "rent", "disabled_medical", "private_education", ...
  ]
}}

주의:
- 반드시 위 JSON 형태만 출력하고, 한국어 설명은 넣지 마라.
- 숫자는 정수만 사용하라. None 이나 문자열 "0" 은 쓰지 마라.
"""

    resp = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=0.1,
    )

    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # 혹시 LLM이 이상하게 답하면 안전하게 기본값 리턴
        return {
            "credit_card": 0,
            "debit_card": 0,
            "cash_receipt": 0,
            "medical_expense": 0,
            "severe_medical_for_disabled": 0,
            "insurance": 0,
            "pension_saving": 0,
            "retirement_pension": 0,
            "donation_total": 0,
            "housing_loan_interest": 0,
            "rent_in_pdf": 0,
            "tax_credit_type": "unknown",
            "missing_fields": ["llm_parse_error"],
        }

    return data


async def parse_year_end_pdf(file_bytes: bytes) -> Tuple[ParsedPdfData, List[str]]:
    """
    라우터에서 업로드된 PDF 바이트를 받아서:
    1) 텍스트 추출
    2) LLM 호출
    3) ParsedPdfData + missing_fields 로 변환해서 반환
    """
    # 1. 텍스트 추출
    pdf_text = await _extract_pdf_text(file_bytes)

    # 2. LLM 호출해서 구조화 JSON 받기
    data = await _call_llm_for_pdf(pdf_text)

    # 3. ParsedPdfData 로 매핑
    parsed_pdf = ParsedPdfData(
        credit_card=int(data.get("credit_card", 0) or 0),
        debit_card=int(data.get("debit_card", 0) or 0),
        cash_receipt=int(data.get("cash_receipt", 0) or 0),
        medical_expense=int(data.get("medical_expense", 0) or 0),
        severe_medical_for_disabled=int(data.get("severe_medical_for_disabled", 0) or 0),
        insurance=int(data.get("insurance", 0) or 0),
        pension_saving=int(data.get("pension_saving", 0) or 0),
        retirement_pension=int(data.get("retirement_pension", 0) or 0),
        donation_total=int(data.get("donation_total", 0) or 0),
        housing_loan_interest=int(data.get("housing_loan_interest", 0) or 0),
        rent_in_pdf=int(data.get("rent_in_pdf", 0) or 0),
        tax_credit_type=data.get("tax_credit_type", "unknown"),
    )

    missing_fields = data.get("missing_fields", []) or []
    # 타입 방어
    if not isinstance(missing_fields, list):
        missing_fields = ["invalid_missing_fields_from_llm"]

    return parsed_pdf, missing_fields