"""
Admin 토큰 인증 테스트.

require_admin_token dependency 의 3가지 분기:
- ADMIN_TOKEN env 미설정 → 503
- 헤더 없음 → 401
- 헤더 있는데 불일치 → 403
- 일치 → True 반환

라우터 단위 적용 검증은 FastAPI TestClient 로 1건만 (비용 낮음).
"""

import os

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.security import require_admin_token


def test_no_env_returns_503(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_admin_token(x_admin_token="anything")
    assert exc.value.status_code == 503


def test_no_header_returns_401(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret_value")
    with pytest.raises(HTTPException) as exc:
        require_admin_token(x_admin_token=None)
    assert exc.value.status_code == 401


def test_wrong_header_returns_403(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret_value")
    with pytest.raises(HTTPException) as exc:
        require_admin_token(x_admin_token="wrong")
    assert exc.value.status_code == 403


def test_correct_header_returns_true(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret_value")
    assert require_admin_token(x_admin_token="secret_value") is True


# -------------------- 라우터 통합 (TestClient) --------------------


def _build_test_app() -> FastAPI:
    """admin_rules + rag 라우터만 마운트한 최소 앱 — 401/403/503 검증용."""
    from app.routers import admin_rules, rag

    app = FastAPI()
    app.include_router(admin_rules.router, prefix="/api/v1")
    app.include_router(rag.router, prefix="/api/v1")
    return app


def test_admin_route_blocks_without_env(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    client = TestClient(_build_test_app())
    res = client.get("/api/v1/admin/rules/drafts")
    assert res.status_code == 503


def test_admin_route_blocks_without_header(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "x")
    client = TestClient(_build_test_app())
    res = client.get("/api/v1/admin/rules/drafts")
    assert res.status_code == 401


def test_admin_route_blocks_wrong_header(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "x")
    client = TestClient(_build_test_app())
    res = client.get(
        "/api/v1/admin/rules/drafts",
        headers={"X-Admin-Token": "wrong"},
    )
    assert res.status_code == 403


def test_admin_route_allows_correct_header(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "x")
    client = TestClient(_build_test_app())
    res = client.get(
        "/api/v1/admin/rules/drafts",
        headers={"X-Admin-Token": "x"},
    )
    assert res.status_code == 200


def test_rag_route_also_guarded(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "x")
    client = TestClient(_build_test_app())
    res = client.get("/api/v1/rag/stats")
    assert res.status_code == 401  # 헤더 없음
    res = client.get("/api/v1/rag/stats", headers={"X-Admin-Token": "x"})
    assert res.status_code == 200
