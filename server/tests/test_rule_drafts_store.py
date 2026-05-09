"""
rule_drafts_store 테스트 — tmp_path 로 격리.
"""

from datetime import datetime, timezone
from pathlib import Path

import json

import pytest

from app.schemas.rule_draft_schema import RuleDraft
from app.schemas.rule_schema import (
    AllOfFlagsEvaluator,
    AllOfFlagsOutputs,
    Rule,
    RulePack,
    ThresholdEvaluator,
    ThresholdOutputs,
    RatioOfField,
    SumOfFields,
)
from app.services import rule_drafts_store
from app.services.rules_engine import load_rules


def _make_card_rule(rule_id: str = "card_25_threshold") -> Rule:
    return Rule(
        rule_id=rule_id,
        title="카드 25%",
        year=2025,
        legal_anchor="조세특례제한법 §126의2 ①",
        evaluator=ThresholdEvaluator(
            threshold=RatioOfField(field="total_salary", ratio=0.25),
            value=SumOfFields(fields=["credit_card", "debit_card", "cash_receipt"]),
            comparison="gte",
            outputs=ThresholdOutputs(
                threshold_key="card_threshold_25",
                value_key="card_total_usage",
                result_key="card_meets_threshold",
            ),
        ),
    )


def _make_flags_rule(rule_id: str = "rent_eligibility") -> Rule:
    return Rule(
        rule_id=rule_id,
        title="월세",
        year=2025,
        legal_anchor="조세특례제한법 §95의2 ①",
        evaluator=AllOfFlagsEvaluator(
            flags=["householder", "no_house", "lease_contract"],
            outputs=AllOfFlagsOutputs(result_key="rent_conditions_met"),
        ),
    )


def _make_draft(
    rule: Rule, source_law_excerpt: str = "법령 발췌…", **kw
) -> RuleDraft:
    return RuleDraft(
        rule=rule,
        source_law_excerpt=source_law_excerpt,
        saved_at=datetime.now(timezone.utc),
        **kw,
    )


# -------------------- save / load / list --------------------


def test_save_and_load(tmp_path: Path):
    draft = _make_draft(_make_card_rule())
    rule_drafts_store.save_draft(draft, data_dir=tmp_path)
    loaded = rule_drafts_store.load_draft(2025, "card_25_threshold", data_dir=tmp_path)
    assert loaded is not None
    assert loaded.rule.rule_id == "card_25_threshold"
    assert loaded.source_law_excerpt == "법령 발췌…"


def test_load_missing_returns_none(tmp_path: Path):
    assert rule_drafts_store.load_draft(2025, "nope", data_dir=tmp_path) is None


def test_list_drafts_empty_when_no_dir(tmp_path: Path):
    assert rule_drafts_store.list_drafts(data_dir=tmp_path) == []


def test_list_drafts_filter_by_year(tmp_path: Path):
    rule_drafts_store.save_draft(_make_draft(_make_card_rule()), data_dir=tmp_path)
    rule_drafts_store.save_draft(_make_draft(_make_flags_rule()), data_dir=tmp_path)

    all_2025 = rule_drafts_store.list_drafts(year=2025, data_dir=tmp_path)
    assert len(all_2025) == 2
    assert {d.rule.rule_id for d in all_2025} == {"card_25_threshold", "rent_eligibility"}

    other_year = rule_drafts_store.list_drafts(year=2099, data_dir=tmp_path)
    assert other_year == []


def test_save_overwrites_same_id(tmp_path: Path):
    rule_drafts_store.save_draft(
        _make_draft(_make_card_rule(), source_law_excerpt="v1"),
        data_dir=tmp_path,
    )
    rule_drafts_store.save_draft(
        _make_draft(_make_card_rule(), source_law_excerpt="v2"),
        data_dir=tmp_path,
    )
    loaded = rule_drafts_store.load_draft(
        2025, "card_25_threshold", data_dir=tmp_path
    )
    assert loaded is not None
    assert loaded.source_law_excerpt == "v2"
    # 디스크에 1개만 남음
    drafts = rule_drafts_store.list_drafts(year=2025, data_dir=tmp_path)
    assert len(drafts) == 1


# -------------------- delete --------------------


def test_delete_draft(tmp_path: Path):
    rule_drafts_store.save_draft(_make_draft(_make_card_rule()), data_dir=tmp_path)
    assert rule_drafts_store.delete_draft(
        2025, "card_25_threshold", data_dir=tmp_path
    )
    assert (
        rule_drafts_store.load_draft(2025, "card_25_threshold", data_dir=tmp_path)
        is None
    )


def test_delete_nonexistent(tmp_path: Path):
    assert (
        rule_drafts_store.delete_draft(2025, "nope", data_dir=tmp_path) is False
    )


# -------------------- approve --------------------


def test_approve_creates_published_pack(tmp_path: Path):
    rule_drafts_store.save_draft(_make_draft(_make_card_rule()), data_dir=tmp_path)

    rule = rule_drafts_store.approve_draft(
        2025, "card_25_threshold", data_dir=tmp_path
    )
    assert rule.human_reviewed is True

    # rules/2025.json 생성 확인
    pub_path = tmp_path / "rules" / "2025.json"
    assert pub_path.exists()
    pack = RulePack.model_validate(json.loads(pub_path.read_text(encoding="utf-8")))
    assert pack.year == 2025
    assert any(r.rule_id == "card_25_threshold" for r in pack.rules)
    assert all(r.human_reviewed for r in pack.rules if r.rule_id == "card_25_threshold")

    # 드래프트 삭제됨
    assert (
        rule_drafts_store.load_draft(2025, "card_25_threshold", data_dir=tmp_path)
        is None
    )


def test_approve_replaces_existing_rule_id(tmp_path: Path):
    """동일 rule_id 가 이미 published 에 있으면 교체."""
    pub_dir = tmp_path / "rules"
    pub_dir.mkdir()
    pack = RulePack(
        year=2025,
        rules=[_make_card_rule()],  # 기존 룰 (human_reviewed=True default)
    )
    (pub_dir / "2025.json").write_text(
        json.dumps(pack.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )

    # 새 드래프트로 교체
    new_rule = _make_card_rule()
    new_rule.title = "신버전 카드 25%"
    rule_drafts_store.save_draft(_make_draft(new_rule), data_dir=tmp_path)

    rule_drafts_store.approve_draft(
        2025, "card_25_threshold", data_dir=tmp_path
    )

    pack_after = RulePack.model_validate(
        json.loads((pub_dir / "2025.json").read_text(encoding="utf-8"))
    )
    matching = [r for r in pack_after.rules if r.rule_id == "card_25_threshold"]
    assert len(matching) == 1  # 중복 안 됨
    assert matching[0].title == "신버전 카드 25%"


def test_approve_missing_draft_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        rule_drafts_store.approve_draft(2025, "nope", data_dir=tmp_path)


# -------------------- reject --------------------


def test_path_traversal_blocked_in_save(tmp_path: Path):
    """rule_id 에 ../ 포함 시 저장 단계에서 거부 (path traversal 방어)."""
    from app.services.rule_drafts_store import UnsafeIdError

    rule = _make_card_rule()
    rule.rule_id = "../../../../etc/passwd"
    draft = _make_draft(rule)
    with pytest.raises(UnsafeIdError):
        rule_drafts_store.save_draft(draft, data_dir=tmp_path)


def test_path_traversal_blocked_in_load(tmp_path: Path):
    from app.services.rule_drafts_store import UnsafeIdError

    with pytest.raises(UnsafeIdError):
        rule_drafts_store.load_draft(2025, "../escape", data_dir=tmp_path)


def test_path_traversal_blocked_in_delete(tmp_path: Path):
    from app.services.rule_drafts_store import UnsafeIdError

    with pytest.raises(UnsafeIdError):
        rule_drafts_store.delete_draft(2025, "../escape", data_dir=tmp_path)


def test_path_traversal_blocked_in_approve(tmp_path: Path):
    from app.services.rule_drafts_store import UnsafeIdError

    with pytest.raises(UnsafeIdError):
        rule_drafts_store.approve_draft(2025, "../escape", data_dir=tmp_path)


def test_safe_id_allows_normal_chars(tmp_path: Path):
    """평범한 rule_id 는 통과."""
    rule = _make_card_rule(rule_id="card_25_threshold-v2")
    rule_drafts_store.save_draft(_make_draft(rule), data_dir=tmp_path)
    loaded = rule_drafts_store.load_draft(
        2025, "card_25_threshold-v2", data_dir=tmp_path
    )
    assert loaded is not None


def test_reject_deletes_draft(tmp_path: Path):
    rule_drafts_store.save_draft(_make_draft(_make_card_rule()), data_dir=tmp_path)
    assert rule_drafts_store.reject_draft(
        2025, "card_25_threshold", data_dir=tmp_path
    )
    assert (
        rule_drafts_store.load_draft(2025, "card_25_threshold", data_dir=tmp_path)
        is None
    )
