"""
Provenance 부착 로직 테스트 (analyze.py 의 _attach_provenance).

LLM 호출은 mock 하지 않고 — 순수 후처리 함수만 검증.
"""

from app.routers.analyze import _attach_provenance, SECTION_TO_RULE_IDS
from app.schemas.analysis_schema import Section
from app.schemas.rule_schema import RuleEvaluation


def _ev(rule_id: str, anchor: str = "X §1") -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        title=rule_id,
        legal_anchor=anchor,
        computed={"k": 1},
        result=True,
        formula="a + b",
    )


def _sec(id: str) -> Section:
    return Section(
        id=id,
        title=id,
        highlight="",
        detail="",
        tips=[],
    )


def test_attach_card_evaluation():
    sections = [_sec("card"), _sec("donation")]
    evals = [
        _ev("card_25_threshold", "조세특례제한법 §126의2 ①"),
        _ev("rent_eligibility", "조세특례제한법 §95의2 ①"),
    ]
    out = _attach_provenance(sections, evals)

    card = next(s for s in out if s.id == "card")
    donation = next(s for s in out if s.id == "donation")

    assert len(card.provenance) == 1
    assert card.provenance[0].rule_id == "card_25_threshold"
    assert "조세특례제한법" in card.provenance[0].legal_anchor
    assert donation.provenance == []


def test_attach_unknown_section_id_no_provenance():
    sections = [_sec("unknown_section_xyz")]
    evals = [_ev("card_25_threshold")]
    out = _attach_provenance(sections, evals)
    assert out[0].provenance == []


def test_attach_missing_rule_silently_skipped():
    """섹션 매핑에 등록된 룰이 평가 결과에 없으면 빠진 채로 통과."""
    sections = [_sec("card")]
    evals: list[RuleEvaluation] = []  # 평가 결과 없음
    out = _attach_provenance(sections, evals)
    assert out[0].provenance == []


def test_section_to_rule_ids_covers_all_default_sections():
    """analyze.py 가 LLM 한테 요청하는 5개 섹션은 모두 매핑이 등록돼 있어야 함."""
    expected_section_ids = {"card", "medical", "donation", "rent_loan", "other"}
    assert expected_section_ids.issubset(SECTION_TO_RULE_IDS.keys())


def test_original_sections_not_mutated():
    """_attach_provenance 는 새 객체를 반환하고 입력 sections 는 건드리지 않음."""
    sections = [_sec("card")]
    evals = [_ev("card_25_threshold")]
    out = _attach_provenance(sections, evals)

    assert sections[0].provenance == []  # 원본 보존
    assert out[0].provenance != []
    assert out[0] is not sections[0]
