from typing import List, Optional
from pydantic import BaseModel


class ParsedPdfData(BaseModel):
    """
    연말정산 간소화 PDF에서 뽑아낼 주요 항목들.
    LLM이 이 스키마에 맞춰 값을 채우는 구조.
    금액은 없으면 0 또는 None 으로.
    """

    # 카드/현금영수증
    credit_card: Optional[int] = 0          # 신용카드 사용액
    debit_card: Optional[int] = 0           # 직불/체크카드 사용액
    cash_receipt: Optional[int] = 0         # 현금영수증

    # 의료비
    medical_expense: Optional[int] = 0      # 전체 의료비 합계
    severe_medical_for_disabled: Optional[int] = 0  # 장애인 의료비(있으면)

    # 보험/연금
    insurance: Optional[int] = 0            # 보장성 보험료
    pension_saving: Optional[int] = 0       # 연금저축
    retirement_pension: Optional[int] = 0   # 퇴직연금(DC/IRP 등)

    # 기부금
    donation_total: Optional[int] = 0       # 전체 기부금 합계

    # 주택 관련
    housing_loan_interest: Optional[int] = 0  # 주택자금대출 이자
    rent_in_pdf: Optional[int] = 0            # 간소화에 잡힌 월세(있으면)

    # 세액공제 유형 (표준/특별/판단불가)
    # "standard" | "special" | "unknown"
    tax_credit_type: Optional[str] = "unknown"


class PdfParseResponse(BaseModel):
    """
    /pdf-parse 응답 스키마
    """
    parsed_pdf: ParsedPdfData
    # LLM이 “추가로 사용자가 수동 입력하면 좋은 항목”을 추천
    # 예: ["donation", "housing_loan", "rent", "disabled_medical"]
    missing_fields: List[str]