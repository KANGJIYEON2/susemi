"""
Phase 4-4: ripple-effect simulator 스키마.

(이름은 의도적으로 "causal" 대신 "ripple"/"의존성 그래프" — 결정론적 정적 분석.)

== 노드 ==
- field: build_eval_context 가 채우는 사용자 입력 키 (e.g., total_salary)
- rule:  rules/{year}.json 의 1건 (e.g., card_25_threshold)
- step:  tax_calculator 의 단계 (e.g., calculated_tax)

== 엣지 ==
- field → rule  : 룰의 evaluator 가 그 field 를 읽음
- field → step  : tax_calculator step 이 그 field 를 직접 읽음 (e.g., gross_salary → earned_income_deduction)
- step  → step  : step 의 출력이 다른 step 의 입력
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


NodeKind = Literal["field", "rule", "step"]


class RippleNode(BaseModel):
    kind: NodeKind
    id: str
    label: str
    legal_anchor: str | None = None
    depth: int = Field(..., ge=1, description="changed_field 로부터의 hop 거리 (1 이상)")


class RippleResponse(BaseModel):
    changed_field: str
    field_label: str | None = None
    nodes: list[RippleNode]
    total_count: int


class GraphNode(BaseModel):
    kind: NodeKind
    id: str
    label: str
    legal_anchor: str | None = None


class GraphEdge(BaseModel):
    source_kind: NodeKind
    source: str
    target_kind: NodeKind
    target: str


class GraphResponse(BaseModel):
    """전체 의존성 그래프 — 시각화/디버깅용."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    field_count: int
    rule_count: int
    step_count: int


class FieldsResponse(BaseModel):
    """알려진 필드 목록 (UI 가 드롭다운으로 채울 때)."""

    fields: list[GraphNode]
