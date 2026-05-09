"""
Phase 4-2: 단순 RAG 스키마.

- IndexedChunk: 법령 청크 + OpenAI embedding 벡터
- IndexLawRequest/Response: 법령 단위 인덱싱
- SearchRequest/Response: 자연어 → top-K 청크
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IndexedChunk(BaseModel):
    """디스크에 저장되는 한 청크."""

    model_config = ConfigDict(populate_by_name=True)

    chunk_id: str
    law_id: str
    law_name: str
    article_no: str
    paragraph_no: str | None = None
    item_no: str | None = None
    text: str
    text_hash: str
    effective_date: str | None = None
    embedding: list[float]
    embedding_model: str
    indexed_at: datetime


class IndexedLawPack(BaseModel):
    """rag_index/{law_id}/{date}.json 의 최상위 컨테이너."""

    law_id: str
    law_name: str
    effective_date: str | None = None
    embedding_model: str
    chunks: list[IndexedChunk]
    indexed_at: datetime


class IndexLawRequest(BaseModel):
    """
    /rag/index 입력.
    셋 중 하나로 본문/청크 결정:
    - law_id (+ optional effective_date)
    - law_mst (+ optional effective_date) with use_mst=True
    - chunks_override (외부 텍스트 사용 시)
    """

    law_id: str | None = None
    law_mst: str | None = None
    effective_date: str | None = None
    use_mst: bool = False
    article_no: str | None = None  # 일부 조만 인덱싱하고 싶을 때


class IndexLawResponse(BaseModel):
    law_id: str
    law_name: str
    effective_date: str | None
    chunks_indexed: int
    embedding_model: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    law_id_filter: str | None = None
    article_no_filter: str | None = None


class SearchHit(BaseModel):
    chunk: IndexedChunk
    score: float


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
    total_indexed: int


class IndexStatsEntry(BaseModel):
    law_id: str
    law_name: str
    effective_date: str | None
    chunks: int
    indexed_at: datetime
    embedding_model: str


class IndexStatsResponse(BaseModel):
    laws: list[IndexStatsEntry]
    total_chunks: int


SimilarityKind = Literal["cosine"]
