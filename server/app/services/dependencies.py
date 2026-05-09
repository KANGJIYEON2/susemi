"""
Phase 4-4: ripple-effect simulator.

== 정적 분석 ==
- 룰 evaluator 로부터 (field → rule_id) 매핑 추출 (런타임 lru_cache)
- tax_calculator step DAG 는 본 모듈에 하드코딩 (코드와 동기 유지 필요)

== ripple BFS ==
changed_field 에서 시작 → 1-hop: 영향받는 rule/step → 2-hop+: step DAG 전파.
rule 은 다른 rule 의 출력을 읽지 않으므로 rule 노드는 leaf.
"""

from __future__ import annotations

from collections import deque
from functools import lru_cache
from typing import Iterable

from app.schemas.dependencies_schema import (
    GraphEdge,
    GraphNode,
    GraphResponse,
    RippleNode,
    RippleResponse,
)
from app.schemas.rule_schema import (
    AllOfFlagsEvaluator,
    Constant,
    FieldRef,
    RatioOfField,
    Rule,
    SumOfFields,
    ThresholdEvaluator,
)
from app.services.rules_engine import EVAL_CONTEXT_FIELDS, load_rules


# -------------------- 정적 step DAG --------------------

# step → 그 step 이 입력으로 읽는 (field 또는 다른 step) 집합
TAX_STEP_DEPS: dict[str, set[str]] = {
    "earned_income_deduction": {"gross_salary"},
    "earned_income_amount": {"earned_income_deduction"},
    "personal_deduction": {
        "has_spouse",
        "dependents_count",
        "senior_count",
        "disabled_count",
        "single_parent",
        "female_householder",
    },
    "taxable_income": {
        "earned_income_amount",
        "personal_deduction",
        # extra_income_deductions 는 baseline 외부 입력 — 시뮬에서 변경 가능 → field 로 취급
        "extra_income_deductions",
    },
    "calculated_tax": {"taxable_income"},
    "earned_income_tax_credit": {"calculated_tax", "gross_salary"},
    "standard_tax_credit": set(),  # 상수 (use_standard_tax_credit 플래그 외 의존 없음)
    "determined_tax": {
        "calculated_tax",
        "earned_income_tax_credit",
        "standard_tax_credit",
        "extra_tax_credits",
    },
    "local_income_tax": {"determined_tax"},
    "refund_or_owed": {"determined_tax", "local_income_tax", "prepaid_tax"},
}

TAX_STEP_META: dict[str, dict[str, str | None]] = {
    "earned_income_deduction": {"label": "근로소득공제", "anchor": "소득세법 §47"},
    "earned_income_amount": {"label": "근로소득금액", "anchor": "소득세법 §47"},
    "personal_deduction": {
        "label": "인적공제 (기본+추가)",
        "anchor": "소득세법 §50",
    },
    "taxable_income": {"label": "과세표준", "anchor": None},
    "calculated_tax": {"label": "산출세액", "anchor": "소득세법 §55"},
    "earned_income_tax_credit": {
        "label": "근로소득세액공제",
        "anchor": "소득세법 §59",
    },
    "standard_tax_credit": {
        "label": "표준세액공제",
        "anchor": "소득세법 §59의4 ⑤",
    },
    "determined_tax": {"label": "결정세액 (국세)", "anchor": None},
    "local_income_tax": {"label": "지방소득세", "anchor": "지방세법 §103의3"},
    "refund_or_owed": {"label": "환급/추징", "anchor": None},
}


# 외부 입력 (extra_*, prepaid_tax) — EVAL_CONTEXT_FIELDS 에 없는 tax_calculator 입력
EXTRA_TAX_FIELDS: dict[str, str] = {
    "extra_income_deductions": "추가 소득공제 합산 (원)",
    "extra_tax_credits": "추가 세액공제 합산 (원)",
    "prepaid_tax": "기납부세액 (원)",
}


# -------------------- 룰 의존성 추출 --------------------


def _rule_input_fields(rule: Rule) -> set[str]:
    fields: set[str] = set()
    ev = rule.evaluator
    if isinstance(ev, ThresholdEvaluator):
        for expr in (ev.threshold, ev.value):
            if isinstance(expr, FieldRef):
                fields.add(expr.name)
            elif isinstance(expr, RatioOfField):
                fields.add(expr.field)
            elif isinstance(expr, SumOfFields):
                fields.update(expr.fields)
            elif isinstance(expr, Constant):
                pass
    elif isinstance(ev, AllOfFlagsEvaluator):
        fields.update(ev.flags)
    return fields


@lru_cache(maxsize=4)
def _build_indices(year: int = 2025) -> tuple[
    dict[str, list[str]],  # field → rule_ids
    dict[str, set[str]],  # rule_id → input fields
    dict[str, Rule],  # rule_id → Rule
]:
    pack = load_rules(year=year)
    field_to_rules: dict[str, list[str]] = {}
    rule_to_fields: dict[str, set[str]] = {}
    rule_by_id: dict[str, Rule] = {}
    for rule in pack.rules:
        rule_by_id[rule.rule_id] = rule
        fields = _rule_input_fields(rule)
        rule_to_fields[rule.rule_id] = fields
        for f in fields:
            field_to_rules.setdefault(f, []).append(rule.rule_id)
    return field_to_rules, rule_to_fields, rule_by_id


def _build_field_to_steps() -> dict[str, list[str]]:
    """field/step 이름 → 그것을 입력으로 읽는 step 들."""
    out: dict[str, list[str]] = {}
    for step, deps in TAX_STEP_DEPS.items():
        for d in deps:
            out.setdefault(d, []).append(step)
    return out


# -------------------- 메타 lookup --------------------


def _all_known_fields() -> dict[str, str]:
    """EVAL_CONTEXT_FIELDS + tax_calculator 외부 입력."""
    out = dict(EVAL_CONTEXT_FIELDS)
    out.update(EXTRA_TAX_FIELDS)
    return out


def _label_for_field(name: str) -> str | None:
    return _all_known_fields().get(name)


def _label_for_rule(rule_id: str, year: int) -> tuple[str | None, str | None]:
    _, _, rule_by_id = _build_indices(year)
    r = rule_by_id.get(rule_id)
    if r is None:
        return None, None
    return r.title, r.legal_anchor


def _label_for_step(name: str) -> tuple[str | None, str | None]:
    meta = TAX_STEP_META.get(name)
    if meta is None:
        return None, None
    return meta.get("label"), meta.get("anchor")


# -------------------- ripple BFS --------------------


def ripple(changed_field: str, year: int = 2025) -> RippleResponse:
    field_to_rules, _, _ = _build_indices(year)
    field_to_steps = _build_field_to_steps()

    visited: set[tuple[str, str]] = set()
    queue: deque[tuple[str, str, int]] = deque()  # (kind, id, depth)
    queue.append(("field", changed_field, 0))
    visited.add(("field", changed_field))

    nodes: list[RippleNode] = []

    while queue:
        kind, name, depth = queue.popleft()

        # depth>0 인 rule/step 만 결과에 누적 (시작 field 자체는 제외)
        if depth >= 1 and kind != "field":
            if kind == "rule":
                label, anchor = _label_for_rule(name, year)
            elif kind == "step":
                label, anchor = _label_for_step(name)
            else:
                label, anchor = None, None
            nodes.append(
                RippleNode(
                    kind=kind,
                    id=name,
                    label=label or name,
                    legal_anchor=anchor,
                    depth=depth,
                )
            )

        # 확장
        next_kind_id_pairs: Iterable[tuple[str, str]] = []
        if kind == "field":
            next_kind_id_pairs = list(
                ("rule", rid) for rid in field_to_rules.get(name, [])
            ) + list(("step", st) for st in field_to_steps.get(name, []))
        elif kind == "step":
            # step 의 출력 이름은 step 이름과 동일 (e.g., calculated_tax) → 이를 읽는 step 들
            next_kind_id_pairs = (
                ("step", st) for st in field_to_steps.get(name, [])
            )
        # rule 은 leaf (다른 rule/step 이 rule 출력을 읽지 않음)

        for next_kind, next_id in next_kind_id_pairs:
            key = (next_kind, next_id)
            if key in visited:
                continue
            visited.add(key)
            queue.append((next_kind, next_id, depth + 1))

    return RippleResponse(
        changed_field=changed_field,
        field_label=_label_for_field(changed_field),
        nodes=nodes,
        total_count=len(nodes),
    )


# -------------------- 전체 그래프 --------------------


def build_graph(year: int = 2025) -> GraphResponse:
    field_to_rules, rule_to_fields, rule_by_id = _build_indices(year)
    fields_meta = _all_known_fields()

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    # 필드 노드
    for fname, label in fields_meta.items():
        nodes.append(GraphNode(kind="field", id=fname, label=label))

    # 룰 노드 + 엣지
    for rid, rule in rule_by_id.items():
        nodes.append(
            GraphNode(
                kind="rule",
                id=rid,
                label=rule.title,
                legal_anchor=rule.legal_anchor,
            )
        )
        for f in rule_to_fields.get(rid, set()):
            edges.append(
                GraphEdge(
                    source_kind="field",
                    source=f,
                    target_kind="rule",
                    target=rid,
                )
            )

    # 스텝 노드 + 엣지
    for step, meta in TAX_STEP_META.items():
        nodes.append(
            GraphNode(
                kind="step",
                id=step,
                label=str(meta.get("label") or step),
                legal_anchor=str(meta.get("anchor")) if meta.get("anchor") else None,
            )
        )

    for step, deps in TAX_STEP_DEPS.items():
        for d in deps:
            # d 가 step 인지 field 인지 판별
            if d in TAX_STEP_DEPS:
                edges.append(
                    GraphEdge(
                        source_kind="step",
                        source=d,
                        target_kind="step",
                        target=step,
                    )
                )
            else:
                edges.append(
                    GraphEdge(
                        source_kind="field",
                        source=d,
                        target_kind="step",
                        target=step,
                    )
                )

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        field_count=len(fields_meta),
        rule_count=len(rule_by_id),
        step_count=len(TAX_STEP_META),
    )


def list_fields() -> list[GraphNode]:
    return [
        GraphNode(kind="field", id=fname, label=label)
        for fname, label in _all_known_fields().items()
    ]
