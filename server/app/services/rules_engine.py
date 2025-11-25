from dataclasses import dataclass
from typing import Any, Dict

from app.schemas.user_input_schema import Income, Dependents, Conditions
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.manual_input_schema import ManualInputRequest


@dataclass
class RuleContext:
    # 카드 관련
    card_threshold_25: int | None
    card_total_usage: int | None
    card_meets_threshold: bool | None

    # 의료비 관련
    medical_threshold_3: int | None
    medical_total: int | None
    medical_meets_threshold: bool | None

    # 월세 요건
    rent_conditions_met: bool | None

    # PDF의 세액공제 유형
    tax_credit_type: str | None

    # 디버깅용 RAW 데이터
    raw: Dict[str, Any]


def build_rule_context(
    income: Income,
    dependents: Dependents,
    conditions: Conditions,
    parsed_pdf: ParsedPdfData,
    manual_input: ManualInputRequest,
) -> RuleContext:

    total_salary = income.total_salary or 0

    # ---------------------------
    # 1) 카드 25% 기준
    # ---------------------------
    card_threshold_25 = int(total_salary * 0.25) if total_salary > 0 else None

    card_total_usage = 0
    for v in [
        parsed_pdf.credit_card,
        parsed_pdf.debit_card,
        parsed_pdf.cash_receipt,
    ]:
        if v:
            card_total_usage += v

    card_meets_threshold = (
        None if card_threshold_25 is None else card_total_usage >= card_threshold_25
    )

    # ---------------------------
    # 2) 의료비 3% 기준
    # ---------------------------
    medical_threshold_3 = int(total_salary * 0.03) if total_salary > 0 else None

    medical_total = 0
    medical_total += parsed_pdf.medical_expense or 0
    medical_total += manual_input.infertility_treatment_expense or 0
    medical_total += manual_input.assistive_devices_expense or 0
    medical_total += manual_input.childbirth_care_expense or 0

    if manual_input.family_medical_expenses:
        medical_total += sum(item.amount for item in manual_input.family_medical_expenses)

    medical_meets_threshold = (
        None if medical_threshold_3 is None else (medical_total > medical_threshold_3)
    )

    # ---------------------------
    # 3) 월세 요건
    # ---------------------------
    rent_conditions_met = bool(
        conditions.householder
        and conditions.no_house
        and conditions.lease_contract
    )

    # ---------------------------
    # 4) RAW 디버그 데이터
    # ---------------------------
    raw: Dict[str, Any] = {
        "total_salary": total_salary,
        "card_threshold_25": card_threshold_25,
        "card_total_usage": card_total_usage,
        "card_meets_threshold": card_meets_threshold,
        "medical_threshold_3": medical_threshold_3,
        "medical_total": medical_total,
        "medical_meets_threshold": medical_meets_threshold,
        "rent_conditions": rent_conditions_met,
        "dependents": dependents.dict(),
        "conditions": conditions.dict(),
    }

    return RuleContext(
        card_threshold_25=card_threshold_25,
        card_total_usage=card_total_usage,
        card_meets_threshold=card_meets_threshold,
        medical_threshold_3=medical_threshold_3,
        medical_total=medical_total,
        medical_meets_threshold=medical_meets_threshold,
        rent_conditions_met=rent_conditions_met,
        tax_credit_type=parsed_pdf.tax_credit_type,
        raw=raw,
    )
