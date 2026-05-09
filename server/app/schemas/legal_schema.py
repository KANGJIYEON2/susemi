"""
법령 API 응답을 정규화한 스키마.

- LawChunk: 조/항/호 단위. 룰 컴파일/RAG 의 기본 단위.
- LawArticle: 조 단위. 내부에 paragraphs(LawChunk 리스트) 보유.
- Law: 법령 전체. 모든 조문 + raw_text + sha256 hash + 메타.
- LawChangeRecord: 개정 이력 한 건.

모든 텍스트의 hash 는 sha256 hex digest.
chunk_id 는 사람이 읽을 수 있는 anchor (예: "소득세법-§52-②-1").
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LawChunk(BaseModel):
    """조/항/호 단위 청크. RAG/룰 컴파일러가 직접 다루는 단위."""

    chunk_id: str = Field(..., description="anchor ID (예: 소득세법-§52-②-1)")
    law_id: str
    law_name: str
    article_no: str = Field(..., description="조 번호 (예: '52')")
    paragraph_no: str | None = Field(None, description="항 번호 (예: '②')")
    item_no: str | None = Field(None, description="호 번호 (예: '1')")
    text: str
    text_hash: str
    effective_date: str | None = Field(None, description="시행일자 YYYYMMDD")


class LawArticle(BaseModel):
    """조 단위."""

    law_id: str
    law_name: str
    article_no: str
    title: str | None = None
    text: str = Field(default="", description="조문 본문 (항/호 합산)")
    paragraphs: list[LawChunk] = Field(default_factory=list)
    effective_date: str | None = None


class Law(BaseModel):
    """법령 전체."""

    model_config = ConfigDict(populate_by_name=True)

    law_id: str
    law_name: str
    effective_date: str | None = None
    promulgation_date: str | None = None
    articles: list[LawArticle] = Field(default_factory=list)
    raw_text: str = ""
    text_hash: str = ""
    fetched_at: datetime
    data_source: Literal["api", "cache_fallback"] = "api"
    is_stale: bool = Field(
        default=False,
        description="캐시본과 비교해 본문이 달라졌는지 (validate_freshness 호출 후에만 의미 있음)",
    )


class LawChangeRecord(BaseModel):
    """개정 이력 1건."""

    law_id: str
    law_name: str
    change_date: str = Field(..., description="개정/시행 일자 YYYYMMDD")
    summary: str | None = None
