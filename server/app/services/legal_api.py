"""
국가법령정보센터 OPEN API 클라이언트.

== 책임 ==
1. 법령 본문 fetch (법령 ID + 시행일자 단위로 idempotent)
2. 디스크 기반 캐시 (rate limit 회피, 오프라인 fallback)
3. 응답 정규화 — 조/항/호 단위 청크 분리, anchor ID 부여
4. sha256 hash 기반 변경 감지 (validate_freshness)

== 엔드포인트(추정) ==
- 법령 본문 조회: GET {base}/lawService.do?OC={oc}&target=law&type=JSON&ID={law_id}&efYd={YYYYMMDD}
- 개정 검색:    GET {base}/lawSearch.do?OC={oc}&target=law&type=JSON&...

응답 구조는 실제 API 검증 후 _parse_law_response 의 키 매핑을 조정해야 함.
README 의 "verified vs assumed" 참조.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx

from app.schemas.legal_schema import (
    Law,
    LawArticle,
    LawChangeRecord,
    LawChunk,
)

DEFAULT_BASE_URL = "http://www.law.go.kr/DRF"
DEFAULT_CACHE_ROOT = (
    Path(__file__).resolve().parent.parent / "data" / "legal_cache"
)


class LegalAPIError(Exception):
    """법령 API 호출/파싱 실패."""


# ----------------- 유틸 -----------------


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _build_chunk_id(
    law_name: str,
    article_no: str,
    paragraph_no: str | None = None,
    item_no: str | None = None,
) -> str:
    parts: list[str] = [law_name, f"§{article_no}"]
    if paragraph_no:
        parts.append(paragraph_no.strip().rstrip("."))
    if item_no:
        parts.append(item_no.strip().rstrip("."))
    return "-".join(parts)


def _coerce_list(value: Any) -> list[Any]:
    """API 응답에서 항/호가 단일 dict 인 경우와 list 인 경우를 통일."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _norm_text(value: Any) -> str:
    """
    응답의 본문 필드(조문내용/항내용/호내용 등) 정규화.
    실제 API 는 동일 키가 string / list / dict 모두로 올 수 있어 방어적으로 처리.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(
            _norm_text(x) for x in value if x is not None
        ).strip()
    if isinstance(value, dict):
        return "\n".join(
            _norm_text(v) for v in value.values() if v is not None
        ).strip()
    return str(value).strip()


# ----------------- 클라이언트 -----------------


class LegalAPIClient:
    """
    사용 예:
        async with LegalAPIClient() as client:
            law = await client.get_law("011357", "20250101")
            chunks = client.to_chunks(law)
    """

    def __init__(
        self,
        oc: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        cache_root: Path | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.oc = oc or os.getenv("OPEN_LAW_API_KEY")
        if not self.oc:
            raise LegalAPIError(
                "OPEN_LAW_API_KEY 환경변수 또는 oc 인자가 필요합니다."
            )
        self.base_url = base_url
        self.cache_root = Path(cache_root) if cache_root else DEFAULT_CACHE_ROOT
        self.cache_root.mkdir(parents=True, exist_ok=True)

        # transport 가 주어지면 base_url 무시되지 않게 그대로 전달
        self._client = httpx.AsyncClient(
            base_url=base_url,
            transport=transport,
            timeout=timeout,
        )

    # context manager
    async def __aenter__(self) -> LegalAPIClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ----- 캐시 -----

    def _cache_path(self, law_id: str, effective_date: str | None) -> Path:
        key = effective_date or "latest"
        return self.cache_root / law_id / f"{key}.json"

    def _read_cache(
        self, law_id: str, effective_date: str | None
    ) -> dict[str, Any] | None:
        path = self._cache_path(law_id, effective_date)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(
        self, law_id: str, effective_date: str | None, data: dict[str, Any]
    ) -> None:
        path = self._cache_path(law_id, effective_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ----- 네트워크 -----

    async def _fetch_law_raw(
        self,
        law_id: str,
        effective_date: str | None,
        use_mst: bool = False,
    ) -> dict[str, Any]:
        """
        use_mst=True 면 law_id 를 MST(법령일련번호) 로 해석.
        그렇지 않으면 법령ID(6자리) 로 해석.
        """
        params: dict[str, str] = {
            "OC": str(self.oc),
            "target": "law",
            "type": "JSON",
            ("MST" if use_mst else "ID"): law_id,
        }
        if effective_date:
            params["efYd"] = effective_date

        try:
            resp = await self._client.get("/lawService.do", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            raise LegalAPIError(
                f"법령 fetch 실패 (id={law_id}, efYd={effective_date}): {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise LegalAPIError(f"법령 응답 JSON 파싱 실패: {e}") from e

    # ----- 파싱 -----

    @staticmethod
    def _parse_law_response(raw: dict[str, Any], law_id: str) -> Law:
        """
        가정한 응답 형태:
            { "법령": {
                "기본정보": {"법령명_한글": ..., "시행일자": ..., "공포일자": ...},
                "조문": {"조문단위": [ {조문번호, 조문제목, 조문내용, 항: [ {항번호, 항내용, 호: [...]}]} ]}
            } }

        실제 응답이 다르면 본 메서드의 키 매핑만 수정하면 됨.
        """
        body = raw.get("법령", raw)
        basic = body.get("기본정보", {}) or {}
        law_name = (
            basic.get("법령명_한글")
            or basic.get("법령명")
            or basic.get("법령명한글")
            or "unknown"
        )
        effective_date = basic.get("시행일자")
        promulgation_date = basic.get("공포일자")

        조문 = body.get("조문", {}) or {}
        articles_raw = _coerce_list(조문.get("조문단위"))

        articles: list[LawArticle] = []
        full_text_parts: list[str] = []

        for art in articles_raw:
            article_no = str(art.get("조문번호", "")).strip()
            if not article_no:
                continue

            title = art.get("조문제목")
            article_text = _norm_text(art.get("조문내용"))

            chunks: list[LawChunk] = []
            paragraphs_raw = _coerce_list(art.get("항"))

            if paragraphs_raw:
                for para in paragraphs_raw:
                    paragraph_no = (
                        str(para.get("항번호", "")).strip() or None
                    )
                    para_text = _norm_text(para.get("항내용"))
                    items_raw = _coerce_list(para.get("호"))

                    if items_raw:
                        for it in items_raw:
                            item_no = (
                                str(it.get("호번호", "")).strip() or None
                            )
                            item_text = _norm_text(it.get("호내용"))
                            chunks.append(
                                LawChunk(
                                    chunk_id=_build_chunk_id(
                                        law_name,
                                        article_no,
                                        paragraph_no,
                                        item_no,
                                    ),
                                    law_id=law_id,
                                    law_name=law_name,
                                    article_no=article_no,
                                    paragraph_no=paragraph_no,
                                    item_no=item_no,
                                    text=item_text,
                                    text_hash=_sha256(item_text),
                                    effective_date=effective_date,
                                )
                            )
                    else:
                        chunks.append(
                            LawChunk(
                                chunk_id=_build_chunk_id(
                                    law_name, article_no, paragraph_no
                                ),
                                law_id=law_id,
                                law_name=law_name,
                                article_no=article_no,
                                paragraph_no=paragraph_no,
                                item_no=None,
                                text=para_text,
                                text_hash=_sha256(para_text),
                                effective_date=effective_date,
                            )
                        )
            elif article_text:
                # 항이 없는 단순 조문
                chunks.append(
                    LawChunk(
                        chunk_id=_build_chunk_id(law_name, article_no),
                        law_id=law_id,
                        law_name=law_name,
                        article_no=article_no,
                        paragraph_no=None,
                        item_no=None,
                        text=article_text,
                        text_hash=_sha256(article_text),
                        effective_date=effective_date,
                    )
                )

            articles.append(
                LawArticle(
                    law_id=law_id,
                    law_name=law_name,
                    article_no=article_no,
                    title=title,
                    text=article_text,
                    paragraphs=chunks,
                    effective_date=effective_date,
                )
            )

            if article_text:
                full_text_parts.append(article_text)

        raw_text = "\n\n".join(full_text_parts)

        return Law(
            law_id=law_id,
            law_name=law_name,
            effective_date=effective_date,
            promulgation_date=promulgation_date,
            articles=articles,
            raw_text=raw_text,
            text_hash=_sha256(raw_text),
            fetched_at=datetime.now(timezone.utc),
            data_source="api",
            is_stale=False,
        )

    # ----- 공개 메서드 -----

    async def get_law(
        self,
        law_id: str,
        effective_date: str | None = None,
        force_refresh: bool = False,
        use_mst: bool = False,
    ) -> Law:
        """
        cache hit → cached 반환 (네트워크 호출 없음)
        cache miss → fetch → 캐시 후 반환
        force_refresh=True → 항상 fetch, 캐시 갱신
        API 실패 + 캐시 있음 → cache_fallback 표시 후 캐시 반환
        use_mst=True → law_id 를 법령일련번호(MST) 로 해석. 시점별 정확.
        """
        if not force_refresh:
            cached = self._read_cache(law_id, effective_date)
            if cached is not None:
                return Law.model_validate(cached)

        try:
            raw = await self._fetch_law_raw(
                law_id, effective_date, use_mst=use_mst
            )
            fresh = self._parse_law_response(raw, law_id)
            self._write_cache(
                law_id,
                effective_date,
                fresh.model_dump(mode="json"),
            )
            return fresh
        except LegalAPIError:
            cached = self._read_cache(law_id, effective_date)
            if cached is not None:
                law = Law.model_validate(cached)
                law.data_source = "cache_fallback"
                return law
            raise

    async def get_article(
        self,
        law_id: str,
        article_no: str,
        effective_date: str | None = None,
    ) -> LawArticle:
        law = await self.get_law(law_id, effective_date=effective_date)
        for article in law.articles:
            if article.article_no == str(article_no):
                return article
        raise LegalAPIError(
            f"§{article_no} 를 {law.law_name}({law_id}) 에서 찾지 못함"
        )

    async def validate_freshness(
        self,
        law_id: str,
        effective_date: str | None = None,
    ) -> Law:
        """
        캐시 vs 신규 응답 hash 비교. is_stale 플래그가 채워진 Law 를 반환.
        결과: is_stale=True 면 호출자가 룰 재컴파일 트리거 등 후속 액션.
        주의: 항상 API 호출 → 자주 부르지 말 것 (rate limit 위험).
        """
        cached_dict = self._read_cache(law_id, effective_date)
        try:
            raw = await self._fetch_law_raw(law_id, effective_date)
            fresh = self._parse_law_response(raw, law_id)
        except LegalAPIError:
            if cached_dict is None:
                raise
            cached_law = Law.model_validate(cached_dict)
            cached_law.data_source = "cache_fallback"
            return cached_law

        if cached_dict is not None:
            cached_law = Law.model_validate(cached_dict)
            fresh.is_stale = fresh.text_hash != cached_law.text_hash

        # 갱신본은 항상 캐시에 덮어씀
        self._write_cache(
            law_id, effective_date, fresh.model_dump(mode="json")
        )
        return fresh

    async def list_changes_since(
        self, since_date: str
    ) -> list[LawChangeRecord]:
        """
        since_date(YYYYMMDD) 이후 개정된 법령 목록.
        주의: 본 엔드포인트의 정확한 파라미터/응답 키는 미검증. README 참조.
        """
        params = {
            "OC": str(self.oc),
            "target": "law",
            "type": "JSON",
            "regDtFrom": since_date,
        }
        try:
            resp = await self._client.get("/lawSearch.do", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            raise LegalAPIError(f"개정 목록 조회 실패: {e}") from e

        items_raw = _coerce_list(data.get("LawSearch", {}).get("law"))
        records: list[LawChangeRecord] = []
        for it in items_raw:
            records.append(
                LawChangeRecord(
                    law_id=str(it.get("법령ID", "")),
                    law_name=str(
                        it.get("법령명한글") or it.get("법령명") or ""
                    ),
                    change_date=str(
                        it.get("개정일자") or it.get("시행일자") or ""
                    ),
                    summary=it.get("개정구분"),
                )
            )
        return records

    @staticmethod
    def to_chunks(law: Law) -> list[LawChunk]:
        """모든 조문의 paragraphs(=청크) 를 평탄화해 반환."""
        chunks: list[LawChunk] = []
        for article in law.articles:
            chunks.extend(article.paragraphs)
        return chunks
