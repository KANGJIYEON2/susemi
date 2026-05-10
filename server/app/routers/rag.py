"""
Phase 4-2 RAG 엔드포인트.

- POST /rag/index        : 법령 인덱싱 (legal_api 통해 fetch + embed + 저장)
- POST /rag/search       : 자연어 → top-K 청크
- GET  /rag/stats        : 인덱스 통계 (법령별 청크 수)

주의: 1차는 admin 인증 없음. 운영 배포 전 가드 필수.
"""

import os

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from app.rate_limit import LIMIT_EMBEDDING, LIMIT_INDEX, limiter
from app.schemas.rag_schema import (
    IndexLawRequest,
    IndexLawResponse,
    IndexStatsResponse,
    SearchRequest,
    SearchResponse,
)
from app.security import require_admin_token
from app.services import rag
from app.services.legal_api import LegalAPIClient, LegalAPIError


# RAG 는 OpenAI 호출 비용/데이터 노출 우려 → admin 전용
router = APIRouter(dependencies=[Depends(require_admin_token)])


@router.post("/rag/index", response_model=IndexLawResponse)
@limiter.limit(LIMIT_INDEX)
async def index_endpoint(
    request: Request,
    payload: IndexLawRequest = Body(...),
):
    # 명시적 Body(...) — slowapi 데코레이터 + FastAPI 본문 추론 충돌 회피
    req = payload
    if not (req.law_id or req.law_mst):
        raise HTTPException(
            status_code=400,
            detail="law_id 또는 law_mst 중 하나는 필수입니다.",
        )
    if not os.getenv("OPEN_LAW_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPEN_LAW_API_KEY 미설정 — 법령 fetch 불가.",
        )

    use_mst = req.use_mst or (req.law_mst is not None)
    law_id = req.law_mst if use_mst else req.law_id
    if law_id is None:
        raise HTTPException(status_code=400, detail="법령 식별자 누락")

    try:
        async with LegalAPIClient() as client:
            law = await client.get_law(
                law_id, effective_date=req.effective_date, use_mst=use_mst
            )
    except LegalAPIError as e:
        raise HTTPException(
            status_code=502, detail=f"법령 fetch 실패: {e}"
        ) from e

    try:
        pack = await rag.index_law(
            law, article_no_filter=req.article_no
        )
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"인덱싱 실패: {e}"
        ) from e

    return IndexLawResponse(
        law_id=pack.law_id,
        law_name=pack.law_name,
        effective_date=pack.effective_date,
        chunks_indexed=len(pack.chunks),
        embedding_model=pack.embedding_model,
    )


@router.post("/rag/search", response_model=SearchResponse)
@limiter.limit(LIMIT_EMBEDDING)
async def search_endpoint(
    request: Request,
    payload: SearchRequest = Body(...),
):
    req = payload
    try:
        hits, total = await rag.search(
            req.query,
            top_k=req.top_k,
            law_id_filter=req.law_id_filter,
            article_no_filter=req.article_no_filter,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"검색 실패: {e}"
        ) from e
    return SearchResponse(query=req.query, hits=hits, total_indexed=total)


@router.get("/rag/stats", response_model=IndexStatsResponse)
def stats_endpoint():
    laws, total = rag.get_stats()
    return IndexStatsResponse(laws=laws, total_chunks=total)
