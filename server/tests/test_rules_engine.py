"""
rules_engine 테스트.

- 룰 JSON 로드 + Pydantic 검증
- ValueExpr 4종 (field/ratio/sum/constant) 평가
- threshold / all_of_flags evaluator
- build_rule_context: legacy field 호환 + evaluations 구조화 출력
- 데이터 부족 시 None 처리
"""

import pytest

from app.schemas.manual_input_schema import (
    FamilyMedicalItem,
    HousingLoanInfo,
    ManualInputRequest,
    RentInfo,
)
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.rule_schema import (
    AllOfFlagsEvaluator,
    AllOfFlagsOutputs,
    Constant,
    FieldRef,
    RatioOfField,
    Rule,
    SumOfFields,
    ThresholdEvaluator,
    ThresholdOutputs,
)
from app.schemas.user_input_schema import Conditions, Dependents, Income
from app.services.rules_engine import (
    _resolve_value,
    build_eval_context,
    build_rule_context,
    evaluate_rule,
    load_rules,
)


# ---------------- 룰 팩 로드 ----------------


def test_load_rules_2025_has_three_rules():
    pack = load_rules(year=2025)
    assert pack.year == 2025
    assert len(pack.rules) == 3
    ids = {r.rule_id for r in pack.rules}
    assert ids == {"card_25_threshold", "medical_3_threshold", "rent_eligibility"}


def test_each_rule_has_legal_anchor():
    pack = load_rules(year=2025)
    for r in pack.rules:
        assert r.legal_anchor, f"룰 {r.rule_id} 에 legal_anchor 누락"


# ---------------- ValueExpr ----------------


def test_resolve_field_ref():
    ctx = {"x": 1000, "y": 2000}
    assert _resolve_value(FieldRef(name="x"), ctx) == 1000
    assert _resolve_value(FieldRef(name="missing"), ctx) == 0


def test_resolve_ratio_of_field():
    ctx = {"salary": 50_000_000}
    assert _resolve_value(
        RatioOfField(field="salary", ratio=0.25), ctx
    ) == 12_500_000
    # 0 또는 음수면 0
    assert _resolve_value(
        RatioOfField(field="salary", ratio=0.25), {"salary": 0}
    ) == 0


def test_resolve_sum_of_fields():
    ctx = {"a": 100, "b": 200, "c": 300}
    assert _resolve_value(SumOfFields(fields=["a", "b", "c"]), ctx) == 600
    # 일부 누락 → 누락분은 0 처리
    assert _resolve_value(SumOfFields(fields=["a", "missing"]), ctx) == 100


def test_resolve_constant():
    assert _resolve_value(Constant(value=130000), {}) == 130000


# ---------------- threshold evaluator ----------------


def _make_threshold_rule(comparison: str = "gte") -> Rule:
    return Rule(
        rule_id="t",
        title="t",
        year=2025,
        legal_anchor="X §1",
        evaluator=ThresholdEvaluator(
            threshold=RatioOfField(field="salary", ratio=0.25),
            value=SumOfFields(fields=["a", "b"]),
            comparison=comparison,
            outputs=ThresholdOutputs(
                threshold_key="thr",
                value_key="val",
                result_key="ok",
            ),
        ),
    )


def test_threshold_passes():
    rule = _make_threshold_rule("gte")
    ctx = {"salary": 40_000_000, "a": 8_000_000, "b": 3_000_000}
    ev = evaluate_rule(rule, ctx)
    # threshold = 1000만, value = 1100만 → True
    assert ev.computed["thr"] == 10_000_000
    assert ev.computed["val"] == 11_000_000
    assert ev.computed["ok"] is True
    assert ev.result is True
    assert ev.legal_anchor == "X §1"


def test_threshold_fails():
    rule = _make_threshold_rule("gte")
    ctx = {"salary": 40_000_000, "a": 5_000_000, "b": 3_000_000}
    ev = evaluate_rule(rule, ctx)
    assert ev.result is False


def test_threshold_data_missing_returns_none():
    rule = _make_threshold_rule("gte")
    ctx = {"salary": 0, "a": 0, "b": 0}
    ev = evaluate_rule(rule, ctx)
    # threshold 0 → 판단불가
    assert ev.result is None
    assert ev.computed["thr"] is None


# ---------------- all_of_flags evaluator ----------------


def _make_flags_rule() -> Rule:
    return Rule(
        rule_id="f",
        title="f",
        year=2025,
        legal_anchor="X §2",
        evaluator=AllOfFlagsEvaluator(
            flags=["a", "b", "c"],
            outputs=AllOfFlagsOutputs(result_key="ok"),
        ),
    )


def test_flags_all_true():
    rule = _make_flags_rule()
    ev = evaluate_rule(rule, {"a": True, "b": True, "c": True})
    assert ev.result is True
    assert ev.computed["ok"] is True


def test_flags_one_false():
    rule = _make_flags_rule()
    ev = evaluate_rule(rule, {"a": True, "b": False, "c": True})
    assert ev.result is False


# ---------------- build_eval_context ----------------


def _basic_inputs():
    income = Income(total_salary=50_000_000, non_taxable=0, bonus=0)
    deps = Dependents(has_spouse=True, dependents_count=1)
    conds = Conditions(
        householder=True,
        no_house=True,
        lease_contract=True,
        has_loan=False,
    )
    pdf = ParsedPdfData(
        credit_card=10_000_000,
        debit_card=2_000_000,
        cash_receipt=500_000,
        medical_expense=1_500_000,
    )
    manual = ManualInputRequest(
        donation_extra=0,
        rent=RentInfo(has_rent=False),
        housing_loan=HousingLoanInfo(has_loan=False),
        family_medical_expenses=[
            FamilyMedicalItem(name="어머니", amount=300_000)
        ],
    )
    return income, deps, conds, pdf, manual


def test_build_eval_context_flattens_inputs():
    income, deps, conds, pdf, manual = _basic_inputs()
    ctx = build_eval_context(income, deps, conds, pdf, manual)
    assert ctx["total_salary"] == 50_000_000
    assert ctx["credit_card"] == 10_000_000
    assert ctx["debit_card"] == 2_000_000
    assert ctx["cash_receipt"] == 500_000
    assert ctx["family_medical_total"] == 300_000
    assert ctx["householder"] is True
    assert ctx["no_house"] is True
    assert ctx["lease_contract"] is True


# ---------------- build_rule_context (통합) ----------------


def test_build_rule_context_card_passes_threshold():
    """총급여 50M 의 25% = 12.5M, 사용액 12.5M → True"""
    income, deps, conds, pdf, manual = _basic_inputs()
    pdf.credit_card = 10_000_000
    pdf.debit_card = 2_000_000
    pdf.cash_receipt = 500_000  # 합 12.5M = threshold

    rc = build_rule_context(income, deps, conds, pdf, manual)
    assert rc.card_threshold_25 == 12_500_000
    assert rc.card_total_usage == 12_500_000
    assert rc.card_meets_threshold is True


def test_build_rule_context_medical_misses_threshold():
    """총급여 50M 의 3% = 1.5M, 의료비 합이 그 이하면 False"""
    income, deps, conds, pdf, manual = _basic_inputs()
    pdf.medical_expense = 500_000
    manual.family_medical_expenses = []
    manual.infertility_treatment_expense = 0
    manual.assistive_devices_expense = 0
    manual.childbirth_care_expense = 0

    rc = build_rule_context(income, deps, conds, pdf, manual)
    assert rc.medical_threshold_3 == 1_500_000
    assert rc.medical_total == 500_000
    assert rc.medical_meets_threshold is False


def test_build_rule_context_rent_eligibility_true():
    income, deps, conds, pdf, manual = _basic_inputs()
    rc = build_rule_context(income, deps, conds, pdf, manual)
    # 기본 입력에서 모든 플래그 True
    assert rc.rent_conditions_met is True


def test_build_rule_context_rent_eligibility_false_when_owns_house():
    income, deps, conds, pdf, manual = _basic_inputs()
    conds.no_house = False  # 주택 보유
    rc = build_rule_context(income, deps, conds, pdf, manual)
    assert rc.rent_conditions_met is False


# ---------------- evaluations 구조화 출력 ----------------


def test_evaluations_have_legal_anchors():
    income, deps, conds, pdf, manual = _basic_inputs()
    rc = build_rule_context(income, deps, conds, pdf, manual)
    assert len(rc.evaluations) == 3
    for ev in rc.evaluations:
        assert ev.legal_anchor, f"룰 {ev.rule_id} 에 anchor 없음"
        assert ev.formula, f"룰 {ev.rule_id} 에 formula 없음"


def test_evaluations_card_rule_has_correct_anchor():
    income, deps, conds, pdf, manual = _basic_inputs()
    rc = build_rule_context(income, deps, conds, pdf, manual)
    card = next(e for e in rc.evaluations if e.rule_id == "card_25_threshold")
    assert "조세특례제한법" in card.legal_anchor
    assert card.computed["card_threshold_25"] == 12_500_000


def test_legacy_fields_match_evaluations():
    """legacy named field 와 evaluations.computed 가 일치해야 함."""
    income, deps, conds, pdf, manual = _basic_inputs()
    rc = build_rule_context(income, deps, conds, pdf, manual)

    by_rule = {e.rule_id: e for e in rc.evaluations}
    card = by_rule["card_25_threshold"]
    medical = by_rule["medical_3_threshold"]
    rent = by_rule["rent_eligibility"]

    assert rc.card_threshold_25 == card.computed["card_threshold_25"]
    assert rc.card_total_usage == card.computed["card_total_usage"]
    assert rc.card_meets_threshold == card.computed["card_meets_threshold"]
    assert rc.medical_total == medical.computed["medical_total"]
    assert rc.rent_conditions_met == rent.computed["rent_conditions_met"]
