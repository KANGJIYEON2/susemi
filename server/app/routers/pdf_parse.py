# app/routers/pdf_parse.py
import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.rate_limit import LIMIT_LLM_USER, limiter
from app.schemas.pdf_schema import PdfParseResponse
from app.services.pdf_parser import parse_year_end_pdf

router = APIRouter(tags=["pdf"])
logger = logging.getLogger(__name__)


@router.post("/pdf-parse", response_model=PdfParseResponse)
@limiter.limit(LIMIT_LLM_USER)
async def pdf_parse(request: Request, file: UploadFile = File(...)):
    """
    연말정산 간소화 PDF 업로드 → LLM이 항목/누락 추천까지 판단해서 내려주는 엔드포인트
    """
    try:
        file_bytes = await file.read()
        parsed_pdf, missing_fields = await parse_year_end_pdf(file_bytes)
        return PdfParseResponse(parsed_pdf=parsed_pdf, missing_fields=missing_fields)
    except Exception as e:
        logger.exception("PDF 파싱 실패")
        raise HTTPException(
            status_code=500,
            detail="PDF를 분석하는 중 오류가 발생했습니다.",
        ) from e
