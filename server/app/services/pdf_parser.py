"""
연말정산 간소화 PDF Hybrid Parsing.

== 흐름 ==
PDF 바이트 → PyMuPDF 텍스트 추출 → LLM(JSON 구조화) → 검증/정규화 → ParsedPdfData

== 안전장치 ==
- LLM 응답을 그대로 신뢰하지 않고 _validate_and_normalize 가:
  * 음수 → 0 + warning
  * 비현실적으로 큰 값(50억 초과) → 0 + warning
  * 문자열 숫자("1,234,567") → 정수 파싱
  * tax_credit_type 화이트리스트 매칭
- 텍스트 잘림(15,000자 컷) 시 missing_fields 에 'pdf_truncated' 추가
- LLM 호출은 llm_call 인자로 주입 가능 (테스트용)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Awaitable, Callable, List, Tuple

import pymupdf
from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.schemas.pdf_schema import ParsedPdfData


load_dotenv()

# Lazy init — 테스트 환경에서 모듈 로드 시점 OPENAI_API_KEY 미설정 회피.
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# 테스트에서 monkeypatch / 인자 주입 가능
LlmCall = Callable[[str, str], Awaitable[str]]


# 비현실적 상한 — 이보다 크면 LLM 환각으로 판단
MAX_REALISTIC_AMOUNT = 5_000_000_000  # 50억 원
MAX_PDF_TEXT_CHARS = 15_000

VALID_TAX_CREDIT_TYPES = {"standard", "special", "unknown"}


# -------------------- 텍스트 추출 --------------------


async def _extract_pdf_text(file_bytes: bytes) -> tuple[str, bool]:
    """
    PDF 바이트 → 전체 텍스트.
    반환: (text, truncated). truncated=True 면 15,000자 컷 발생.
    """
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    texts: list[str] = []
    try:
        for page in doc:
            texts.append(page.get_text("text"))
    finally:
        doc.close()

    full = "\n\n".join(texts)
    if len(full) > MAX_PDF_TEXT_CHARS:
        return full[:MAX_PDF_TEXT_CHARS], True
    return full, False


# -------------------- 정규화 helper --------------------


_NUM_RE = re.compile(r"-?\d+")


def _normalize_int(value: Any, max_value: int = MAX_REALISTIC_AMOUNT) -> tuple[int, str | None]:
    """
    LLM 이 보낸 임의 타입 → 안전한 정수.
    return (값, warning|None)

    - None / 빈 문자열 → 0
    - bool → 0 (True 가 1로 잡히는 거 방지)
    - int / float → int 변환
    - str → 숫자만 파싱 (예: '1,234,567원' → 1234567)
    - 음수 → 0 + warning
    - max_value 초과 → 0 + warning
    """
    if value is None or value == "":
        return 0, None
    if isinstance(value, bool):
        # bool 은 int 의 서브타입 — 명시적 거부
        return 0, "boolean given for numeric field"

    parsed: int | None = None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        parsed = int(value)
    elif isinstance(value, str):
        # 콤마/공백/원 표시 제거 후 숫자만
        cleaned = value.strip()
        match = _NUM_RE.search(cleaned.replace(",", ""))
        if match:
            try:
                parsed = int(match.group(0))
            except ValueError:
                parsed = None
    if parsed is None:
        return 0, f"unparseable numeric: {value!r}"

    if parsed < 0:
        return 0, f"negative value clamped to 0: {parsed}"
    if parsed > max_value:
        return 0, f"unrealistic large value rejected: {parsed}"
    return parsed, None


def _normalize_tax_credit_type(value: Any) -> str:
    if isinstance(value, str) and value in VALID_TAX_CREDIT_TYPES:
        return value
    return "unknown"


def _validate_and_normalize(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """
    LLM JSON → ParsedPdfData 에 넣을 dict + warnings.
    warnings 는 missing_fields 에 합쳐 사용자/검수자에게 노출.
    """
    warnings: list[str] = []

    int_fields = [
        "credit_card",
        "debit_card",
        "cash_receipt",
        "medical_expense",
        "severe_medical_for_disabled",
        "insurance",
        "pension_saving",
        "retirement_pension",
        "donation_total",
        "housing_loan_interest",
        "rent_in_pdf",
    ]

    out: dict[str, Any] = {}
    for f in int_fields:
        v, warn = _normalize_int(raw.get(f))
        out[f] = v
        if warn:
            warnings.append(f"{f}: {warn}")

    out["tax_credit_type"] = _normalize_tax_credit_type(raw.get("tax_credit_type"))
    if raw.get("tax_credit_type") not in VALID_TAX_CREDIT_TYPES:
        if raw.get("tax_credit_type") is not None:
            warnings.append(
                f"tax_credit_type: '{raw.get('tax_credit_type')!r}' → 'unknown' 으로 정규화"
            )

    return out, warnings


def _normalize_missing_fields(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["invalid_missing_fields_from_llm"]
    return [str(x) for x in value if isinstance(x, (str, int))]


# -------------------- LLM 호출 --------------------


SYSTEM_PROMPT = """
너는 2025년 기준 대한민국 근로소득 연말정산 전문가이자 세무사다.
너의 역할은 '연말정산 간소화 서비스 PDF 내용'을 읽고,
세법 기준에 맞게 공제 항목을 구조화하고, 누락되기 쉬운 항목을 추천하는 것이다.

규칙:
- 한국 2025년 소득·세액공제 규정을 기준으로 판단한다.
- PDF 텍스트에 금액이 명시되지 않았으면 해당 항목은 0 으로 둔다.
- 애매하면 0 또는 "unknown" 으로 처리하고, missing_fields 에 이유를 반영한다.
- 금액 단위는 모두 "원" 기준 정수(int)로 맞춘다.
- 출력은 반드시 JSON 하나만, 주석/설명 없이 반환한다.
""".strip()


def _build_user_prompt(pdf_text: str) -> str:
    return f"""
다음은 근로소득자의 연말정산 간소화 PDF 전체 텍스트다.

[PDF_TEXT_START]
{pdf_text}
[PDF_TEXT_END]

이 텍스트를 읽고 아래 스키마에 맞는 JSON 을 만들어라.

스키마(키 이름 고정):
{{
  "credit_card": int,
  "debit_card": int,
  "cash_receipt": int,
  "medical_expense": int,
  "severe_medical_for_disabled": int,
  "insurance": int,
  "pension_saving": int,
  "retirement_pension": int,
  "donation_total": int,
  "housing_loan_interest": int,
  "rent_in_pdf": int,
  "tax_credit_type": "standard" | "special" | "unknown",
  "missing_fields": ["donation", "housing_loan", ...]
}}

주의:
- 반드시 위 JSON 형태만 출력하고, 한국어 설명은 넣지 마라.
- 숫자는 정수만 사용하라. None 이나 문자열 "0" 은 쓰지 마라.
""".strip()


async def _default_llm_call(system: str, user: str) -> str:
    resp = await _get_client().chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""


async def _call_llm_for_pdf(
    pdf_text: str,
    llm_call: LlmCall | None = None,
) -> dict[str, Any]:
    """LLM 응답을 dict 로 반환. 파싱 실패시 모든-0 fallback + missing_fields 마크."""
    call = llm_call or _default_llm_call
    user = _build_user_prompt(pdf_text)
    try:
        content = await call(SYSTEM_PROMPT, user)
    except Exception as e:  # 네트워크/LLM 오류 광범위
        return _empty_result(reason=f"llm_call_error: {type(e).__name__}")

    if not content:
        return _empty_result(reason="llm_empty_response")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return _empty_result(reason="llm_parse_error")


def _empty_result(reason: str) -> dict[str, Any]:
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
        "missing_fields": [reason],
    }


# -------------------- orchestrator --------------------


async def parse_year_end_pdf(
    file_bytes: bytes,
    llm_call: LlmCall | None = None,
) -> Tuple[ParsedPdfData, List[str]]:
    """
    PDF 바이트 → (ParsedPdfData, missing_fields).
    llm_call 인자로 LLM 주입 가능 (테스트).
    """
    pdf_text, truncated = await _extract_pdf_text(file_bytes)
    raw = await _call_llm_for_pdf(pdf_text, llm_call=llm_call)

    normalized, warnings = _validate_and_normalize(raw)
    parsed_pdf = ParsedPdfData(**normalized)

    missing = _normalize_missing_fields(raw.get("missing_fields"))
    if truncated:
        missing.append("pdf_truncated_15k_chars")
    missing.extend(warnings)

    # 중복 제거하면서 순서 보존
    seen: set[str] = set()
    deduped: list[str] = []
    for m in missing:
        if m not in seen:
            seen.add(m)
            deduped.append(m)

    return parsed_pdf, deduped
