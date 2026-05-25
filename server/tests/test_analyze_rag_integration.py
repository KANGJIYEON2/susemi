"""
analyze.py 의 RAG 통합 테스트.

LLM 호출은 하지 않고 (실제 prompt 검증은 별도)
- _build_rag_query
- _fetch_rag_context (rag.search monkeypatch)
- _format_rag_for_prompt (llm_client)
"""

import pytest

from app.routers.analyze import _build_rag_query, _fetch_rag_context
from app.schemas.rag_schema import IndexedChunk, SearchHit
from app.schemas.rule_schema import RuleEvaluation
from app.services import rules_engine


# -------------------- _build_rag_query --------------------


def test_build_rag_query_empty_evaluations():
    rc = rules_engine.RuleContext()
    rc.evaluations = []
    assert _build_rag_query(rc) is None


def test_build_rag_query_combines_titles_and_anchors():
    rc = rules_engine.RuleContext()
    rc.evaluations = [
        RuleEvaluation(
            rule_id="r1",
            title="신용카드 공제",
            legal_anchor="조세특례제한법 §126의2",
            computed={},
            result=True,
            formula="x + y",
        ),
        RuleEvaluation(
            rule_id="r2",
            title="의료비 공제",
            legal_anchor="소득세법 §59의4",
            computed={},
            result=False,
            formula="m gt n",
        ),
    ]
    q = _build_rag_query(rc)
    assert q is not None
    assert "신용카드 공제" in q
    assert "조세특례제한법" in q
    assert "의료비 공제" in q


# -------------------- _fetch_rag_context --------------------


def _ev(rule_id: str = "r") -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        title="t",
        legal_anchor="X §1",
        computed={},
        result=True,
        formula="f",
    )


def _make_hit(text: str = "법령 본문") -> SearchHit:
    return SearchHit(
        chunk=IndexedChunk(
            chunk_id="X-§1",
            law_id="L1",
            law_name="X법",
            article_no="1",
            paragraph_no=None,
            item_no=None,
            text=text,
            text_hash="h",
            embedding=[0.0],
            embedding_model="test",
            indexed_at="2025-01-01T00:00:00Z",
        ),
        score=0.9,
    )


async def test_fetch_rag_context_empty_evaluations_returns_empty():
    rc = rules_engine.RuleContext()
    rc.evaluations = []
    hits = await _fetch_rag_context(rc)
    assert hits == []


async def test_fetch_rag_context_calls_search_and_returns_hits(monkeypatch):
    captured = {}

    async def fake_search(query, **kwargs):
        captured["query"] = query
        captured["top_k"] = kwargs.get("top_k")
        return [_make_hit("매칭 본문 1"), _make_hit("매칭 본문 2")], 5

    from app.services import rag as rag_module

    monkeypatch.setattr(rag_module, "search", fake_search)

    rc = rules_engine.RuleContext()
    rc.evaluations = [_ev()]
    hits = await _fetch_rag_context(rc, top_k=3)
    assert len(hits) == 2
    assert captured["top_k"] == 3
    assert "X §1" in captured["query"]


async def test_fetch_rag_context_silent_fallback_on_error(monkeypatch):
    async def raising_search(query, **kwargs):
        raise RuntimeError("openai down")

    from app.services import rag as rag_module

    monkeypatch.setattr(rag_module, "search", raising_search)

    rc = rules_engine.RuleContext()
    rc.evaluations = [_ev()]
    hits = await _fetch_rag_context(rc)
    assert hits == []


# -------------------- _format_rag_for_prompt --------------------


def test_format_rag_for_prompt_empty():
    from app.services.llm_client import _format_rag_for_prompt

    out = _format_rag_for_prompt([])
    assert "인덱싱된 법령 없음" in out


def test_format_rag_for_prompt_truncates_long_text():
    from app.services.llm_client import _format_rag_for_prompt

    long_text = "긴 법령 본문 " * 100  # 약 700자 — 500자 컷 초과
    hit = _make_hit(long_text)
    out = _format_rag_for_prompt([hit])
    # 500자 + ellipsis
    assert "…" in out
    assert "X법 §1" in out


def test_format_rag_for_prompt_numbers_hits():
    from app.services.llm_client import _format_rag_for_prompt

    out = _format_rag_for_prompt([_make_hit("a"), _make_hit("b")])
    assert "[1]" in out
    assert "[2]" in out


# -------------------- prompt 통합 — RAG 블록 포함 --------------------


def test_build_prompt_includes_rag_block():
    from app.schemas.user_input_schema import Conditions, Dependents, Income
    from app.schemas.pdf_schema import ParsedPdfData
    from app.schemas.manual_input_schema import (
        HousingLoanInfo,
        ManualInputRequest,
        RentInfo,
    )
    from app.services.llm_client import build_prompt

    rc = rules_engine.RuleContext()
    rc.evaluations = [_ev()]

    prompt = build_prompt(
        income=Income(total_salary=30_000_000),
        dependents=Dependents(has_spouse=False),
        conditions=Conditions(
            householder=True, no_house=True, lease_contract=False, has_loan=False
        ),
        parsed_pdf=ParsedPdfData(),
        manual_input=ManualInputRequest(
            rent=RentInfo(has_rent=False),
            housing_loan=HousingLoanInfo(has_loan=False),
        ),
        rule_context=rc,
        rag_hits=[_make_hit("신용카드 사용액 공제 본문 발췌")],
    )
    assert "참고 법령 본문" in prompt
    assert "신용카드 사용액 공제 본문 발췌" in prompt
    assert "X법 §1" in prompt


def test_build_prompt_handles_no_rag_hits():
    from app.schemas.user_input_schema import Conditions, Dependents, Income
    from app.schemas.pdf_schema import ParsedPdfData
    from app.schemas.manual_input_schema import (
        HousingLoanInfo,
        ManualInputRequest,
        RentInfo,
    )
    from app.services.llm_client import build_prompt

    rc = rules_engine.RuleContext()

    prompt = build_prompt(
        income=Income(total_salary=30_000_000),
        dependents=Dependents(has_spouse=False),
        conditions=Conditions(
            householder=True, no_house=True, lease_contract=False, has_loan=False
        ),
        parsed_pdf=ParsedPdfData(),
        manual_input=ManualInputRequest(
            rent=RentInfo(has_rent=False),
            housing_loan=HousingLoanInfo(has_loan=False),
        ),
        rule_context=rc,
        # rag_hits 미지정 — None
    )
    # "인덱싱된 법령 없음" fallback 메시지 포함
    assert "인덱싱된 법령 없음" in prompt
