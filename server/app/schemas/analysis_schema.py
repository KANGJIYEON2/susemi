from typing import List, Dict, Any, Union
from pydantic import BaseModel

from app.schemas.user_input_schema import Income, Dependents, Conditions
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.manual_input_schema import ManualInputRequest


# ----- 요청 스키마 -----
class AnalyzeRequest(BaseModel):
    income: Income
    dependents: Dependents
    conditions: Conditions
    parsed_pdf: ParsedPdfData
    manual_input: ManualInputRequest


# ----- 응답 스키마 -----
class Summary(BaseModel):
    headline: str
    key_points: List[str]


class Section(BaseModel):
    id: str
    title: str
    highlight: str
    detail: str
    evidence: Union[str, Dict[str, Any], None] = None
    tips: List[str] | None = None


class AnalyzeResponse(BaseModel):
    summary: Summary
    sections: List[Section]
    tax_tips: List[str]
