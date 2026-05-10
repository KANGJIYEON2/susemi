"""
회귀 테스트 — `from __future__ import annotations` + slowapi + Pydantic body 충돌.

사고 이력:
  POST /admin/rules/compile, /rag/search, /rag/index 가
  422 "Field required: req (in query)" 반환 — body 가 query 로 오인됨.

원인:
  - 라우터 파일에 `from __future__ import annotations` 가 있으면
    `req: CompileRequest` 같은 어노테이션이 ForwardRef 로 평가됨.
  - slowapi @limiter.limit 와 결합 시 FastAPI 가 본문 타입을 추론 못함.

Fix:
  - 두 라우터에서 `from __future__ import annotations` 제거
  - 본문 파라미터에 명시적 `Body(...)` default 추가

본 테스트는 TestClient 로 실제 body parsing 동작 확인 — 회귀 시 즉시 fail.
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_app(monkeypatch):
    """admin/rag 라우터만 마운트. ADMIN_TOKEN 셋업."""
    monkeypatch.setenv("ADMIN_TOKEN", "test-token")
    # 캐시된 import 무효화 — env 가 바뀌었을 수 있음
    from fastapi import FastAPI

    from app.routers import admin_rules, rag

    app = FastAPI()
    app.include_router(admin_rules.router, prefix="/api/v1")
    app.include_router(rag.router, prefix="/api/v1")
    return TestClient(app)


HEADERS = {"X-Admin-Token": "test-token"}


def test_compile_endpoint_parses_body_not_query(admin_app):
    """짧은 본문 검증으로 진입했다는 건 body 파싱이 정상 동작한다는 신호."""
    res = admin_app.post(
        "/api/v1/admin/rules/compile",
        json={
            "target_rule_id": "regression_test",
            "target_title": "회귀",
            "target_anchor": "X §1",
            "law_text_override": "짧",  # 20자 미만 → 라우터에서 400 반환
        },
        headers=HEADERS,
    )
    # 422 (body 못 파싱) 가 아니라 400 (라우터 검증)이 떠야 정상
    assert res.status_code == 400, res.text
    assert "짧" in res.text or "본문" in res.text


def test_compile_endpoint_with_real_body_passes_pydantic(admin_app):
    """Pydantic 검증이 정상적으로 본문에 적용되는지."""
    res = admin_app.post(
        "/api/v1/admin/rules/compile",
        json={
            "target_rule_id": "../escape",  # path traversal — pattern 위반
            "target_title": "x",
            "target_anchor": "X §1",
            "law_text_override": "충분히 긴 법령 본문 텍스트입니다 충분히 긴 본문",
        },
        headers=HEADERS,
    )
    # 422 — Pydantic pattern 위반 (body 는 정상 파싱됨)
    assert res.status_code == 422
    detail = res.json().get("detail", [])
    # loc 가 query 가 아니라 body 여야 함
    if isinstance(detail, list) and detail:
        loc = detail[0].get("loc", [])
        assert loc and loc[0] == "body", f"loc 가 body 가 아님: {loc}"


def test_rag_search_endpoint_parses_body_not_query(admin_app):
    """rag/search 도 같은 패턴 — 빈 인덱스 시 200 [] 떠야 정상."""
    res = admin_app.post(
        "/api/v1/rag/search",
        json={"query": "테스트", "top_k": 5},
        headers=HEADERS,
    )
    # 인덱스가 비어있으면 200 + hits=[] (OpenAI 호출 skip 덕분)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "hits" in data
    assert "total_indexed" in data


def test_rag_search_validates_body(admin_app):
    """빈 query 는 422 (Pydantic min_length=1)."""
    res = admin_app.post(
        "/api/v1/rag/search",
        json={"query": "", "top_k": 5},
        headers=HEADERS,
    )
    assert res.status_code == 422
    detail = res.json().get("detail", [])
    if isinstance(detail, list) and detail:
        loc = detail[0].get("loc", [])
        # body 단계 검증이지 query 단계 아님
        assert loc and loc[0] == "body"
