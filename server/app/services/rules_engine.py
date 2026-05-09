"""
룰 엔진.

== 흐름 ==
1) 사용자 입력(소득/인적공제/조건/PDF/수기) → 평가 컨텍스트(flat dict)
2) `data/rules/{year}.json` 로드 → Rule 객체들
3) 각 Rule 의 evaluator 실행 → RuleEvaluation
4) legacy RuleContext(@dataclass) 의 named field 도 동시에 채워서 반환
   (analyze.py / llm_client.py 가 기존 필드명에 의존하므로 호환 유지)

== 보안 ==
- eval() 안 씀. evaluator 는 전부 discriminated union 으로 분기.

== 확장 ==
- 새 룰 추가: rules/{year}.json 에 1건 추가 + (필요 시) evaluation context 에 새 필드.
- 새 evaluator 종류 추가: rule_schema.py 에 BaseModel + Literal kind 추가, 본 파일 _evaluate_* dispatcher 추가.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.manual_input_schema import ManualInputRequest
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.rule_schema import (
    AllOfFlagsEvaluator,
    Constant,
    FieldRef,
    RatioOfField,
    Rule,
    RuleEvaluation,
    RulePack,
    SumOfFields,
    ThresholdEvaluator,
    ValueExpr,
)
from app.schemas.user_input_schema import Conditions, Dependents, Income


DEFAULT_RULES_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "rules"
)


# ---------------- legacy RuleContext (호환 유지) ----------------


@dataclass
class RuleContext:
    """
    기존 코드(analyze.py / llm_client.py) 와의 호환을 위해 named field 유지.
    추가로 evaluations(구조화 출력) 와 raw(디버그) 보유.
    """

    # 카드
    card_threshold_25: int | None = None
    card_total_usage: int | None = None
    card_meets_threshold: bool | None = None

    # 의료비
    medical_threshold_3: int | None = None
    medical_total: int | None = None
    medical_meets_threshold: bool | None = None

    # 월세
    rent_conditions_met: bool | None = None

    # PDF 메타
    tax_credit_type: str | None = None

    # 디버그용 raw flat context
    raw: dict[str, Any] = field(default_factory=dict)

    # Phase 2-2: 구조화 평가 결과 (Provenance·LLM 모두 이 쪽 사용 권장)
    evaluations: list[RuleEvaluation] = field(default_factory=list)


# ---------------- 룰 로드 ----------------


@lru_cache(maxsize=4)
def load_rules(year: int = 2025, path: str | None = None) -> RulePack:
    file_path = Path(path) if path else DEFAULT_RULES_DIR / f"{year}.json"
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    pack = RulePack.model_validate(data)
    if pack.year != year and path is None:
        raise ValueError(f"룰 팩 연도 mismatch: 요청 {year}, 파일 {pack.year}")
    return pack


# ---------------- 평가 컨텍스트 ----------------


def build_eval_context(
    income: Income,
    dependents: Dependents,
    conditions: Conditions,
    parsed_pdf: ParsedPdfData,
    manual_input: ManualInputRequest,
) -> dict[str, Any]:
    """모든 입력을 룰이 참조할 수 있는 flat dict 로 평탄화."""

    family_medical_total = 0
    if manual_input.family_medical_expenses:
        family_medical_total = sum(
            item.amount for item in manual_input.family_medical_expenses
        )

    ctx: dict[str, Any] = {
        # 소득
        "total_salary": income.total_salary or 0,
        "non_taxable": income.non_taxable or 0,
        "bonus": income.bonus or 0,
        # 카드
        "credit_card": parsed_pdf.credit_card or 0,
        "debit_card": parsed_pdf.debit_card or 0,
        "cash_receipt": parsed_pdf.cash_receipt or 0,
        # 의료비
        "medical_expense": parsed_pdf.medical_expense or 0,
        "severe_medical_for_disabled": parsed_pdf.severe_medical_for_disabled
        or 0,
        "infertility_treatment_expense": manual_input.infertility_treatment_expense
        or 0,
        "assistive_devices_expense": manual_input.assistive_devices_expense
        or 0,
        "childbirth_care_expense": manual_input.childbirth_care_expense or 0,
        "glasses_contacts_expense": manual_input.glasses_contacts_expense or 0,
        "family_medical_total": family_medical_total,
        # 기부금
        "donation_total": parsed_pdf.donation_total or 0,
        "donation_extra": manual_input.donation_extra or 0,
        # 주택
        "rent_in_pdf": parsed_pdf.rent_in_pdf or 0,
        "housing_loan_interest": parsed_pdf.housing_loan_interest or 0,
        # 보험·연금
        "insurance": parsed_pdf.insurance or 0,
        "pension_saving": parsed_pdf.pension_saving or 0,
        "retirement_pension": parsed_pdf.retirement_pension or 0,
        # PDF 메타
        "tax_credit_type": parsed_pdf.tax_credit_type or "unknown",
        # 인적공제
        "has_spouse": bool(dependents.has_spouse),
        "dependents_count": dependents.dependents_count or 0,
        "disabled_count": dependents.disabled_count or 0,
        "senior_count": dependents.senior_count or 0,
        "single_parent": bool(dependents.single_parent),
        "female_householder": bool(dependents.female_householder),
        # 조건 플래그
        "householder": bool(conditions.householder),
        "no_house": bool(conditions.no_house),
        "lease_contract": bool(conditions.lease_contract),
        "has_loan": bool(conditions.has_loan),
        "child_education": bool(conditions.child_education),
        "self_education": bool(conditions.self_education),
        "mid_small_company_worker": bool(
            conditions.mid_small_company_worker
        ),
    }
    return ctx


# ---------------- 값 표현 평가 ----------------


def _resolve_value(expr: ValueExpr, ctx: dict[str, Any]) -> int:
    """ValueExpr 을 정수값으로 변환."""

    if isinstance(expr, FieldRef):
        v = ctx.get(expr.name, 0)
        return int(v) if isinstance(v, (int, float)) else 0

    if isinstance(expr, RatioOfField):
        base = ctx.get(expr.field, 0)
        if not isinstance(base, (int, float)) or base <= 0:
            return 0
        return int(base * expr.ratio)

    if isinstance(expr, SumOfFields):
        total = 0
        for fld in expr.fields:
            v = ctx.get(fld, 0)
            if isinstance(v, (int, float)):
                total += int(v)
        return total

    if isinstance(expr, Constant):
        return int(expr.value)

    raise ValueError(f"Unknown value expression: {type(expr).__name__}")


# ---------------- evaluator dispatcher ----------------


_COMPARISONS = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
}


def _formula_str(expr: ValueExpr) -> str:
    if isinstance(expr, FieldRef):
        return expr.name
    if isinstance(expr, RatioOfField):
        return f"{expr.field} × {expr.ratio}"
    if isinstance(expr, SumOfFields):
        return " + ".join(expr.fields)
    if isinstance(expr, Constant):
        return str(expr.value)
    return "?"


def evaluate_rule(rule: Rule, ctx: dict[str, Any]) -> RuleEvaluation:
    """단일 룰 평가 → RuleEvaluation."""

    ev = rule.evaluator
    computed: dict[str, Any] = {}
    result: bool | None = None
    formula: str | None = None

    if isinstance(ev, ThresholdEvaluator):
        threshold_val = _resolve_value(ev.threshold, ctx)
        actual_val = _resolve_value(ev.value, ctx)
        op = _COMPARISONS[ev.comparison]

        # 데이터가 사실상 모두 0 이면 None (판단불가) 처리: total_salary 가 0 인 경우만 보수적 판단불가
        # 단순화: threshold 가 0 이면 None
        if threshold_val == 0:
            result = None
        else:
            result = bool(op(actual_val, threshold_val))

        computed[ev.outputs.threshold_key] = threshold_val if threshold_val else None
        computed[ev.outputs.value_key] = actual_val
        computed[ev.outputs.result_key] = result

        formula = (
            f"{_formula_str(ev.value)} {ev.comparison} "
            f"{_formula_str(ev.threshold)}"
        )

    elif isinstance(ev, AllOfFlagsEvaluator):
        flags = [bool(ctx.get(f)) for f in ev.flags]
        result = all(flags) if flags else None
        computed[ev.outputs.result_key] = result
        formula = " ∧ ".join(ev.flags)

    else:
        raise ValueError(f"Unknown evaluator kind: {type(ev).__name__}")

    return RuleEvaluation(
        rule_id=rule.rule_id,
        title=rule.title,
        legal_anchor=rule.legal_anchor,
        legal_text_hash=rule.legal_text_hash,
        computed=computed,
        result=result,
        formula=formula,
    )


# ---------------- 통합: build_rule_context ----------------


# legacy RuleContext field <-> rule output key 매핑
_LEGACY_FIELD_KEYS = {
    "card_threshold_25",
    "card_total_usage",
    "card_meets_threshold",
    "medical_threshold_3",
    "medical_total",
    "medical_meets_threshold",
    "rent_conditions_met",
}


def build_rule_context(
    income: Income,
    dependents: Dependents,
    conditions: Conditions,
    parsed_pdf: ParsedPdfData,
    manual_input: ManualInputRequest,
    year: int = 2025,
) -> RuleContext:
    """
    공개 API. 기존 코드와 동일 시그니처(year 만 추가, 기본 2025).
    내부적으로는 JSON 룰 팩을 로드해서 evaluator 로 평가.
    """
    ctx_data = build_eval_context(
        income, dependents, conditions, parsed_pdf, manual_input
    )
    pack = load_rules(year=year)
    evaluations = [evaluate_rule(rule, ctx_data) for rule in pack.rules]

    # legacy named field 채우기
    flat: dict[str, Any] = {}
    for ev in evaluations:
        flat.update(ev.computed)

    raw = dict(ctx_data)
    raw["_evaluations"] = [ev.model_dump() for ev in evaluations]

    return RuleContext(
        card_threshold_25=flat.get("card_threshold_25"),
        card_total_usage=flat.get("card_total_usage"),
        card_meets_threshold=flat.get("card_meets_threshold"),
        medical_threshold_3=flat.get("medical_threshold_3"),
        medical_total=flat.get("medical_total"),
        medical_meets_threshold=flat.get("medical_meets_threshold"),
        rent_conditions_met=flat.get("rent_conditions_met"),
        tax_credit_type=parsed_pdf.tax_credit_type,
        raw=raw,
        evaluations=evaluations,
    )
