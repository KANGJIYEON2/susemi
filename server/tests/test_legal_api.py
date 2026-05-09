"""
LegalAPIClient 의 단위 테스트.

- 실제 OPEN.LAW API 는 호출하지 않음
- httpx.MockTransport 로 응답 주입
- 캐시 hit/miss, 변경 감지, fallback, to_chunks 검증
"""

import json
from pathlib import Path

import httpx
import pytest

from app.services.legal_api import LegalAPIClient, LegalAPIError, _sha256

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "legal_api"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def transport_returning(payload: dict) -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def transport_status(status_code: int) -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    return httpx.MockTransport(handler)


# ---------- 기본 동작 ----------


async def test_get_law_cache_miss_fetches_and_caches(tmp_path):
    payload = load_fixture("income_tax_law.json")

    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(payload)
    ) as client:
        law = await client.get_law("001234", "20250101")

    assert law.law_name == "소득세법"
    assert law.data_source == "api"
    assert law.is_stale is False
    assert law.text_hash  # non-empty
    # 캐시 파일이 생성됐는지
    assert (tmp_path / "001234" / "20250101.json").exists()


async def test_get_law_cache_hit_returns_without_network(tmp_path):
    payload = load_fixture("income_tax_law.json")

    # 1차: cache miss → fetch
    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(payload)
    ) as client:
        first = await client.get_law("001234", "20250101")

    # 2차: 항상 500 반환하는 transport 로 새 클라이언트 — 캐시 hit 이라면 네트워크 안 탐
    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_status(500)
    ) as client:
        second = await client.get_law("001234", "20250101")

    assert second.law_name == first.law_name
    assert second.text_hash == first.text_hash
    assert second.data_source == "api"  # 캐시에서 그대로 복원


async def test_get_article_locates_by_no(tmp_path):
    payload = load_fixture("income_tax_law.json")

    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(payload)
    ) as client:
        article = await client.get_article("001234", "52", "20250101")

    assert article.article_no == "52"
    assert article.title == "특별소득공제"
    # 항/호가 paragraphs 로 펼쳐짐
    assert len(article.paragraphs) > 0


async def test_get_article_raises_when_not_found(tmp_path):
    payload = load_fixture("income_tax_law.json")

    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(payload)
    ) as client:
        with pytest.raises(LegalAPIError):
            await client.get_article("001234", "9999", "20250101")


# ---------- to_chunks ----------


async def test_to_chunks_decomposes_paragraphs_and_items(tmp_path):
    payload = load_fixture("income_tax_law.json")

    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(payload)
    ) as client:
        law = await client.get_law("001234", "20250101")
        chunks = client.to_chunks(law)

    assert len(chunks) >= 3  # §52 ① 1호, §52 ① 2호, §52 ②, §59의2 ①
    for c in chunks:
        assert c.chunk_id.startswith("소득세법-§")
        assert c.text_hash == _sha256(c.text)
        assert c.law_id == "001234"


async def test_chunk_anchor_format(tmp_path):
    payload = load_fixture("income_tax_law.json")

    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(payload)
    ) as client:
        law = await client.get_law("001234", "20250101")
        chunks = client.to_chunks(law)

    ids = {c.chunk_id for c in chunks}
    assert "소득세법-§52-①-1" in ids
    assert "소득세법-§52-②" in ids


# ---------- 변경 감지 ----------


async def test_validate_freshness_detects_modified_text(tmp_path):
    original = load_fixture("income_tax_law.json")

    # 1) 초기 캐시
    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(original)
    ) as client:
        await client.get_law("001234", "20250101")

    # 2) 본문이 바뀐 응답
    modified = json.loads(json.dumps(original, ensure_ascii=False))
    modified["법령"]["조문"]["조문단위"][0]["조문내용"] = "변경된 본문입니다."

    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(modified)
    ) as client:
        result = await client.validate_freshness("001234", "20250101")

    assert result.is_stale is True
    assert result.text_hash != _sha256("")


async def test_validate_freshness_marks_unchanged(tmp_path):
    payload = load_fixture("income_tax_law.json")

    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(payload)
    ) as client:
        await client.get_law("001234", "20250101")
        result = await client.validate_freshness("001234", "20250101")

    assert result.is_stale is False


# ---------- API 실패 시 fallback ----------


async def test_fallback_to_cache_when_api_errors(tmp_path):
    payload = load_fixture("income_tax_law.json")

    # 캐시 시드
    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_returning(payload)
    ) as client:
        await client.get_law("001234", "20250101")

    # force_refresh=True 로 다시 호출하지만 API 가 500 → cache_fallback 으로 복원
    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_status(500)
    ) as client:
        result = await client.get_law(
            "001234", "20250101", force_refresh=True
        )

    assert result.data_source == "cache_fallback"
    assert result.law_name == "소득세법"


async def test_no_cache_no_api_raises(tmp_path):
    async with LegalAPIClient(
        oc="test", cache_root=tmp_path, transport=transport_status(500)
    ) as client:
        with pytest.raises(LegalAPIError):
            await client.get_law("999999", "20250101")


# ---------- 인증 ----------


def test_missing_oc_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("OPEN_LAW_API_KEY", raising=False)
    with pytest.raises(LegalAPIError):
        LegalAPIClient(cache_root=tmp_path)
