"""
POST /verify — 자체 산식 vs 회사 신고 cross-check.
"""

from fastapi import APIRouter

from app.schemas.verification_schema import VerificationReport, VerifyRequest
from app.services.verification import verify as verify_service


router = APIRouter()


@router.post("/verify", response_model=VerificationReport)
def verify_filing(body: VerifyRequest):
    return verify_service(
        request=body.request,
        filing=body.filing,
        extra_income_deductions=body.extra_income_deductions,
        extra_tax_credits=body.extra_tax_credits,
    )
