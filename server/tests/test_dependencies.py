"""
Phase 4-4 의존성 그래프 / ripple 테스트.
"""

from app.services.dependencies import (
    TAX_STEP_DEPS,
    _build_field_to_steps,
    _build_indices,
    build_graph,
    list_fields,
    ripple,
)


# -------------------- 인덱스 --------------------


def test_indices_built_from_rules_2025():
    field_to_rules, rule_to_fields, rule_by_id = _build_indices(2025)
    # rules/2025.json 에 정의된 3개 룰
    assert set(rule_by_id.keys()) == {
        "card_25_threshold",
        "medical_3_threshold",
        "rent_eligibility",
    }
    # 카드 룰은 total_salary, credit_card, debit_card, cash_receipt 를 읽음
    card_fields = rule_to_fields["card_25_threshold"]
    assert "total_salary" in card_fields
    assert "credit_card" in card_fields
    # 월세는 flag 3개
    rent_fields = rule_to_fields["rent_eligibility"]
    assert rent_fields == {"householder", "no_house", "lease_contract"}
    # 역방향 매핑
    assert "card_25_threshold" in field_to_rules["total_salary"]


# -------------------- step DAG --------------------


def test_step_deps_field_to_steps():
    f2s = _build_field_to_steps()
    # gross_salary 는 earned_income_deduction 와 earned_income_tax_credit 둘 다 읽음
    assert "earned_income_deduction" in f2s["gross_salary"]
    assert "earned_income_tax_credit" in f2s["gross_salary"]
    # taxable_income → calculated_tax
    assert "calculated_tax" in f2s["taxable_income"]


def test_no_orphan_step():
    """모든 step 은 한 개 이상 input 을 갖거나 (standard_tax_credit) 명시적 빈 set."""
    for step, deps in TAX_STEP_DEPS.items():
        assert isinstance(deps, set)


# -------------------- ripple --------------------


def test_ripple_total_salary_hits_card_rule_and_calc_chain():
    res = ripple("total_salary")
    ids = {n.id for n in res.nodes}
    # 룰: total_salary 를 읽는 룰
    assert "card_25_threshold" in ids
    assert "medical_3_threshold" in ids
    # tax steps: gross_salary 가 아니라 total_salary 라 직접 매칭은 룰만.
    # gross_salary 는 step 에서 별도로 추적
    assert res.field_label == "총급여 (원)"
    assert res.total_count == len([n for n in res.nodes])


def test_ripple_gross_salary_propagates_through_step_chain():
    res = ripple("gross_salary")
    ids = {n.id for n in res.nodes}
    # earned_income_deduction (depth 1)
    assert "earned_income_deduction" in ids
    # earned_income_tax_credit (depth 1, 직접 의존)
    assert "earned_income_tax_credit" in ids
    # 그 다음 단계들 (depth 2+)
    assert "earned_income_amount" in ids
    assert "taxable_income" in ids
    assert "calculated_tax" in ids
    assert "determined_tax" in ids
    assert "local_income_tax" in ids
    assert "refund_or_owed" in ids


def test_ripple_depth_increases_along_chain():
    """
    BFS 는 최단경로를 채택. gross_salary 는 두 갈래로 직접 진입하므로
    일부 step 은 짧은 경로로 도달함.
    """
    res = ripple("gross_salary")
    by_id = {n.id: n for n in res.nodes}
    # 직접 의존: depth 1
    assert by_id["earned_income_deduction"].depth == 1
    assert by_id["earned_income_tax_credit"].depth == 1
    # 한 단계 더 (eid → eia, eitc → det)
    assert by_id["earned_income_amount"].depth == 2
    assert by_id["determined_tax"].depth == 2
    # 그 이후
    assert by_id["taxable_income"].depth == 3
    assert by_id["local_income_tax"].depth == 3
    assert by_id["refund_or_owed"].depth == 3
    assert by_id["calculated_tax"].depth >= 3


def test_ripple_householder_only_hits_rent_rule():
    res = ripple("householder")
    ids = {n.id for n in res.nodes}
    # 월세 룰만 직접 영향
    assert "rent_eligibility" in ids
    # 다른 룰은 안 읽음
    assert "card_25_threshold" not in ids
    assert "medical_3_threshold" not in ids


def test_ripple_extra_income_deductions_propagates():
    res = ripple("extra_income_deductions")
    ids = {n.id for n in res.nodes}
    # extra_income_deductions 는 taxable_income 의 input
    assert "taxable_income" in ids
    # 그 후 calculated_tax 등
    assert "calculated_tax" in ids
    assert "refund_or_owed" in ids


def test_ripple_unknown_field_returns_empty():
    res = ripple("zzz_unknown_field")
    assert res.nodes == []
    assert res.total_count == 0


def test_ripple_no_self_loop():
    """ripple 결과에 시작 field 자체는 포함되지 않아야 함."""
    res = ripple("gross_salary")
    assert all(n.id != "gross_salary" for n in res.nodes)


# -------------------- 전체 그래프 --------------------


def test_graph_includes_all_kinds():
    g = build_graph(2025)
    kinds = {n.kind for n in g.nodes}
    assert kinds == {"field", "rule", "step"}
    assert g.rule_count == 3
    assert g.step_count == len(TAX_STEP_DEPS)
    assert g.field_count > 0


def test_graph_has_field_to_rule_edges():
    g = build_graph(2025)
    rule_edges = [e for e in g.edges if e.source_kind == "field" and e.target_kind == "rule"]
    # card_25_threshold 는 최소 4개 field 의존 (total_salary + credit/debit/cash)
    card_edges = [e for e in rule_edges if e.target == "card_25_threshold"]
    assert len(card_edges) >= 4


def test_graph_has_step_to_step_edges():
    g = build_graph(2025)
    step_edges = [
        e for e in g.edges if e.source_kind == "step" and e.target_kind == "step"
    ]
    # earned_income_deduction → earned_income_amount 같은 chain 존재
    assert any(
        e.source == "earned_income_deduction" and e.target == "earned_income_amount"
        for e in step_edges
    )


# -------------------- list_fields --------------------


def test_list_fields_includes_extras():
    fields = list_fields()
    ids = {f.id for f in fields}
    assert "total_salary" in ids
    # tax_calculator 외부 입력도 포함
    assert "extra_income_deductions" in ids
    assert "prepaid_tax" in ids
