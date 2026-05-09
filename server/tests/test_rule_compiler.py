"""
rule_compiler 테스트.
- LLM 호출은 인자로 주입한 fake 함수로 대체
- JSON 파싱, Pydantic 검증, 알려진/알려지지 않은 필드 케이스
- 코드가 강제하는 메타(rule_id/title/anchor/year/compiled_by 등) 덮어쓰기 검증
"""

import json

import pytest

from app.services.rule_compiler import (
    _collect_field_refs,
    _parse_rule_json,
    _validate_rule,
    compile_rule,
)
from app.schemas.rule_schema import (
    AllOfFlagsEvaluator,
    Rule,
    SumOfFields,
    ThresholdEvaluator,
)


def make_fake_llm(response_text: str, capture: list | None = None):
    async def _fake(system: str, user: str) -> str:
        if capture is not None:
            capture.append({"system": system, "user": user})
        return response_text

    return _fake


VALID_THRESHOLD_JSON = json.dumps(
    {
        "rule_id": "_will_be_overwritten",
        "title": "_will_be_overwritten",
        "year": 1900,
        "legal_anchor": "_will_be_overwritten",
        "legal_text_hash": None,
        "source_api_id": None,
        "human_reviewed": True,
        "confidence": 1.0,
        "compiled_at": "2020-01-01",
        "compiled_by": "manual",
        "evaluator": {
            "kind": "threshold",
            "threshold": {
                "type": "ratio_of_field",
                "field": "total_salary",
                "ratio": 0.25,
            },
            "value": {
                "type": "sum_of_fields",
                "fields": ["credit_card", "debit_card", "cash_receipt"],
            },
            "comparison": "gte",
            "outputs": {
                "threshold_key": "card_threshold_25",
                "value_key": "card_total_usage",
                "result_key": "card_meets_threshold",
            },
        },
    },
    ensure_ascii=False,
)


VALID_FLAGS_JSON = json.dumps(
    {
        "rule_id": "x",
        "title": "x",
        "year": 2025,
        "legal_anchor": "X §1",
        "evaluator": {
            "kind": "all_of_flags",
            "flags": ["householder", "no_house", "lease_contract"],
            "outputs": {"result_key": "rent_conditions_met"},
        },
    },
    ensure_ascii=False,
)


# -------------------- 기본 컴파일 --------------------


async def test_compile_threshold_rule_overwrites_meta():
    capture: list = []
    fake = make_fake_llm(VALID_THRESHOLD_JSON, capture)

    draft = await compile_rule(
        law_text="법령 본문 텍스트 — 충분히 길게 채워둠 " * 10,
        target_rule_id="card_25_threshold",
        target_title="신용카드 등 사용액 공제 최저사용액 요건",
        target_anchor="조세특례제한법 §126의2 ①",
        target_year=2025,
        legal_text_hash="abc123",
        source_api_id="src1",
        llm_call=fake,
    )

    rule = draft.rule
    # 메타 강제 덮어쓰기
    assert rule.rule_id == "card_25_threshold"
    assert rule.title == "신용카드 등 사용액 공제 최저사용액 요건"
    assert rule.year == 2025
    assert rule.legal_anchor == "조세특례제한법 §126의2 ①"
    assert rule.legal_text_hash == "abc123"
    assert rule.source_api_id == "src1"
    assert rule.compiled_by == "llm:gpt-4o-mini"
    assert rule.human_reviewed is False
    # evaluator 보존
    assert isinstance(rule.evaluator, ThresholdEvaluator)
    assert rule.evaluator.comparison == "gte"
    assert isinstance(rule.evaluator.value, SumOfFields)

    # 자동 검증 통과
    assert rule.confidence == 1.0
    assert draft.validation_warnings == []
    assert draft.status == "draft"
    assert capture and "법령 본문 텍스트" in capture[0]["user"]


async def test_compile_flags_rule_basic():
    fake = make_fake_llm(VALID_FLAGS_JSON)
    draft = await compile_rule(
        law_text="요건: 세대주이고 무주택이며 임대차계약을 체결한 거주자에 한해…",
        target_rule_id="rent_eligibility",
        target_title="월세액 세액공제 요건",
        target_anchor="조세특례제한법 §95의2 ①",
        llm_call=fake,
    )
    assert isinstance(draft.rule.evaluator, AllOfFlagsEvaluator)
    assert "householder" in draft.rule.evaluator.flags
    assert draft.rule.confidence == 1.0


# -------------------- 알려지지 않은 필드 → confidence 디스카운트 --------------------


async def test_unknown_field_warning_lowers_confidence():
    bad = json.loads(VALID_THRESHOLD_JSON)
    bad["evaluator"]["value"]["fields"] = ["credit_card", "made_up_field"]
    fake = make_fake_llm(json.dumps(bad, ensure_ascii=False))

    draft = await compile_rule(
        law_text="긴 법령 본문 " * 5,
        target_rule_id="r",
        target_title="t",
        target_anchor="X §1",
        llm_call=fake,
    )
    assert draft.rule.confidence < 1.0
    assert any("made_up_field" in w for w in draft.validation_warnings)


# -------------------- JSON 잡음·재시도 --------------------


async def test_compile_recovers_from_messy_json():
    """LLM 이 앞뒤 텍스트 + JSON 을 섞어 보내도 추출 가능."""
    messy = (
        "다음과 같이 컴파일했습니다:\n\n"
        + VALID_THRESHOLD_JSON
        + "\n\n위 결과를 사용하세요."
    )
    fake = make_fake_llm(messy)
    draft = await compile_rule(
        law_text="긴 법령 본문 " * 5,
        target_rule_id="r",
        target_title="t",
        target_anchor="X §1",
        llm_call=fake,
    )
    assert draft.rule.evaluator is not None


async def test_compile_retry_on_invalid_then_success():
    bad_then_good = ["완전히 잘못된 응답", VALID_THRESHOLD_JSON]
    idx = {"i": 0}

    async def fake(system, user):
        out = bad_then_good[idx["i"]]
        idx["i"] += 1
        return out

    draft = await compile_rule(
        law_text="긴 법령 본문 " * 5,
        target_rule_id="r",
        target_title="t",
        target_anchor="X §1",
        llm_call=fake,
    )
    assert idx["i"] == 2  # 1차 실패 + 1회 재시도
    assert isinstance(draft.rule.evaluator, ThresholdEvaluator)


async def test_compile_double_failure_raises():
    fake = make_fake_llm("그냥 자유 텍스트")
    with pytest.raises(Exception):
        await compile_rule(
            law_text="긴 법령 본문 " * 5,
            target_rule_id="r",
            target_title="t",
            target_anchor="X §1",
            llm_call=fake,
        )


# -------------------- 헬퍼 함수 --------------------


def test_collect_field_refs_threshold():
    rule = Rule.model_validate(json.loads(VALID_THRESHOLD_JSON))
    refs = _collect_field_refs(rule)
    assert "total_salary" in refs
    assert "credit_card" in refs
    assert "cash_receipt" in refs


def test_collect_field_refs_flags():
    rule = Rule.model_validate(json.loads(VALID_FLAGS_JSON))
    refs = _collect_field_refs(rule)
    assert refs == ["householder", "no_house", "lease_contract"]


def test_validate_rule_clean():
    rule = Rule.model_validate(json.loads(VALID_THRESHOLD_JSON))
    confidence, warnings = _validate_rule(rule)
    assert confidence == 1.0
    assert warnings == []


def test_validate_rule_with_unknown():
    bad = json.loads(VALID_THRESHOLD_JSON)
    bad["evaluator"]["value"]["fields"] = ["zzz_unknown"]
    rule = Rule.model_validate(bad)
    confidence, warnings = _validate_rule(rule)
    assert confidence < 1.0
    assert warnings


def test_parse_rule_json_strict():
    rule = _parse_rule_json(VALID_THRESHOLD_JSON)
    assert isinstance(rule, Rule)


def test_parse_rule_json_with_trailing_comma():
    s = (
        '{ "rule_id":"x","title":"x","year":2025,"legal_anchor":"X","'
        'evaluator":{"kind":"all_of_flags","flags":["a"],"outputs":{"result_key":"r"},}}'
    )
    rule = _parse_rule_json(s)
    assert rule.rule_id == "x"
