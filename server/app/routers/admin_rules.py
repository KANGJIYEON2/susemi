"""
admin: 룰 컴파일 + 검수 큐.

엔드포인트:
- POST /admin/rules/compile          : 법령 fetch + LLM 컴파일 → 드래프트 저장
- GET  /admin/rules/drafts            : 드래프트 목록
- GET  /admin/rules/drafts/{rule_id}  : 단일 드래프트 (year=2025 기본)
- POST /admin/rules/drafts/{rule_id}/approve : 드래프트를 published 로 승격
- POST /admin/rules/drafts/{rule_id}/reject  : 드래프트 거부

주의: 1차 구현은 인증 없음. 운영 배포 전 admin 인증 필수.
"""

import os

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from app.rate_limit import LIMIT_LLM_ADMIN, limiter
from app.schemas.rule_draft_schema import (
    CompileRequest,
    CompileResponse,
    DecideRequest,
    DecideResponse,
    DraftsListResponse,
    RuleDraft,
)
from app.security import require_admin_token
from app.services import rule_drafts_store
from app.services.legal_api import LegalAPIClient, LegalAPIError
from app.services.rule_compiler import compile_rule
from app.services.rule_drafts_store import UnsafeIdError


# 라우터 전체에 admin 토큰 가드 적용
router = APIRouter(dependencies=[Depends(require_admin_token)])


async def _fetch_law_text(req: CompileRequest) -> tuple[str, str | None, str | None]:
    """
    CompileRequest 에서 법령 본문/hash/source_api_id 를 결정.
    - law_text_override 우선
    - 아니면 LegalAPIClient 로 fetch
    """
    if req.law_text_override:
        return req.law_text_override, None, None

    if not (req.law_id or req.law_mst):
        raise HTTPException(
            status_code=400,
            detail="law_text_override 또는 (law_id|law_mst) 중 하나는 필수입니다.",
        )

    use_mst = req.law_mst is not None
    law_id = req.law_mst if use_mst else req.law_id
    if law_id is None:
        raise HTTPException(status_code=400, detail="법령 식별자 누락")

    if not os.getenv("OPEN_LAW_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPEN_LAW_API_KEY 환경변수가 설정되지 않아 법령 API 호출 불가. law_text_override 를 사용하세요.",
        )

    try:
        async with LegalAPIClient() as client:
            if req.article_no:
                article = await client.get_article(
                    law_id, req.article_no, effective_date=req.effective_date
                )
                source_api_id = (
                    f"{law_id}#§{req.article_no}@{req.effective_date or 'latest'}"
                )
                # 항/호 본문 합쳐서 전달
                parts = [article.text] + [
                    p.text for p in article.paragraphs if p.text
                ]
                return ("\n".join(p for p in parts if p), None, source_api_id)
            else:
                law = await client.get_law(
                    law_id, effective_date=req.effective_date, use_mst=use_mst
                )
                source_api_id = f"{law_id}@{req.effective_date or 'latest'}"
                return (law.raw_text, law.text_hash, source_api_id)
    except LegalAPIError as e:
        raise HTTPException(
            status_code=502, detail=f"법령 API 호출 실패: {e}"
        ) from e


@router.post("/admin/rules/compile", response_model=CompileResponse)
@limiter.limit(LIMIT_LLM_ADMIN)
async def compile_endpoint(
    request: Request,
    payload: CompileRequest = Body(...),
):
    # 명시적 Body(...) — slowapi 데코레이터 + FastAPI 본문 추론 충돌 회피
    req = payload
    law_text, legal_text_hash, source_api_id = await _fetch_law_text(req)

    if not law_text or len(law_text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="법령 본문이 너무 짧거나 비어있습니다.",
        )

    try:
        draft = await compile_rule(
            law_text=law_text,
            target_rule_id=req.target_rule_id,
            target_title=req.target_title,
            target_anchor=req.target_anchor,
            target_year=req.target_year,
            legal_text_hash=legal_text_hash,
            source_api_id=source_api_id,
            parent_rule_id=req.parent_rule_id,
        )
    except Exception as e:  # 광범위 — 컴파일 실패 시 502
        raise HTTPException(
            status_code=502, detail=f"룰 컴파일 실패: {e}"
        ) from e

    rule_drafts_store.save_draft(draft)
    return CompileResponse(draft=draft)


@router.get("/admin/rules/drafts", response_model=DraftsListResponse)
def list_drafts_endpoint(year: int | None = Query(default=None)):
    drafts = rule_drafts_store.list_drafts(year=year)
    return DraftsListResponse(drafts=drafts)


@router.get(
    "/admin/rules/drafts/{rule_id}",
    response_model=RuleDraft,
)
def load_draft_endpoint(
    rule_id: str, year: int = Query(default=2025)
):
    try:
        draft = rule_drafts_store.load_draft(year, rule_id)
    except UnsafeIdError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if draft is None:
        raise HTTPException(status_code=404, detail="드래프트 없음")
    return draft


@router.post(
    "/admin/rules/drafts/{rule_id}/approve",
    response_model=DecideResponse,
)
def approve_endpoint(
    rule_id: str,
    body: DecideRequest,
    year: int = Query(default=2025),
):
    try:
        rule = rule_drafts_store.approve_draft(
            year, rule_id, review_notes=body.review_notes
        )
    except UnsafeIdError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return DecideResponse(
        status="approved",
        rule_id=rule.rule_id,
        message=f"{rule.rule_id} 가 rules/{year}.json 에 병합되었습니다.",
    )


@router.post(
    "/admin/rules/drafts/{rule_id}/reject",
    response_model=DecideResponse,
)
def reject_endpoint(
    rule_id: str,
    body: DecideRequest,
    year: int = Query(default=2025),
):
    try:
        ok = rule_drafts_store.reject_draft(
            year, rule_id, review_notes=body.review_notes
        )
    except UnsafeIdError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=404, detail="드래프트 없음")
    return DecideResponse(
        status="rejected",
        rule_id=rule_id,
        message=f"{rule_id} 드래프트가 거부되었습니다.",
    )
