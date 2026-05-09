"""
LLM 컴파일된 룰의 드래프트 + 검수 워크플로 스키마.

상태 흐름:
  draft → approved (rules/{year}.json 으로 승격)
  draft → rejected (드래프트 파일 삭제 또는 보관)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rule_schema import Rule


DraftStatus = Literal["draft", "approved", "rejected"]


class RuleDraft(BaseModel):
    """
    rule_compiler 가 생성한 1건의 드래프트.

    - rule.confidence 는 자동 검증 결과 (Pydantic 통과 + 알려진 필드 사용 여부)
    - status 는 검수자가 수동으로 변경
    - review_notes 는 검수 시 입력
    """

    model_config = ConfigDict(populate_by_name=True)

    rule: Rule
    status: DraftStatus = "draft"
    review_notes: str | None = None

    # 출처 추적
    source_law_excerpt: str = Field(
        ...,
        description="컴파일에 사용한 법령 본문 발췌 (앞 1000자 정도)",
    )
    source_chunk_id: str | None = Field(
        default=None,
        description="법령 API to_chunks 결과의 chunk_id (예: '소득세법-§52-①-1')",
    )
    parent_rule_id: str | None = Field(
        default=None,
        description="기존 룰을 재컴파일한 경우 원본 rule_id",
    )

    # 검증 경고 — 자동 검증 단계의 비치명적 문제
    validation_warnings: list[str] = Field(default_factory=list)

    saved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CompileRequest(BaseModel):
    """admin 엔드포인트용 입력."""

    # 법령 출처 — 둘 중 하나로 본문 fetch
    law_id: str | None = None
    law_mst: str | None = None
    article_no: str | None = None
    effective_date: str | None = None
    # 또는 사용자가 직접 본문 텍스트 제공
    law_text_override: str | None = None

    # 컴파일 타깃 메타
    target_rule_id: str = Field(..., min_length=1)
    target_title: str = Field(..., min_length=1)
    target_anchor: str = Field(..., min_length=1)
    target_year: int = 2025
    parent_rule_id: str | None = None


class CompileResponse(BaseModel):
    draft: RuleDraft


class DraftsListResponse(BaseModel):
    drafts: list[RuleDraft]


class DecideRequest(BaseModel):
    review_notes: str | None = None


class DecideResponse(BaseModel):
    status: DraftStatus
    rule_id: str
    message: str
