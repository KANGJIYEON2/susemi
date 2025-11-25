# app/routers/pdf_parse.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.pdf_schema import PdfParseResponse
from app.services.pdf_parser import parse_year_end_pdf

router = APIRouter(tags=["pdf"])


@router.post("/pdf-parse", response_model=PdfParseResponse)
async def pdf_parse(file: UploadFile = File(...)):
    """
    연말정산 간소화 PDF 업로드 → LLM이 항목/누락 추천까지 판단해서 내려주는 엔드포인트
    """
    try:
        file_bytes = await file.read()
        parsed_pdf, missing_fields = await parse_year_end_pdf(file_bytes)
        return PdfParseResponse(parsed_pdf=parsed_pdf, missing_fields=missing_fields)
    except Exception as e:
        # 디버깅 필요하면 여기서만 print 찍고, 응답은 깔끔하게
        print("PDF parse error:", repr(e))
        raise HTTPException(
            status_code=500,
            detail="PDF를 분석하는 중 오류가 발생했습니다.",
        )
