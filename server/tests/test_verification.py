"""
verification (Phase 3-3) 테스트.

- 자체 산식 결과를 그대로 회사 신고에 넣으면 모든 단계 'match'
- 결정세액에만 큰 차이 → 'major'
- 1,000원 미만 차이 → 'minor'
- 일부 필드 None → 'missing'
- final_delta / refund_delta 부호 검증
- summary 문구가 단정적이지 않은지 (오류 단어 사용 X)
"""

from app.schemas.analysis_schema import AnalyzeRequest
from app.schemas.manual_input_schema import (
    HousingLoanInfo,
    ManualInputRequest,
    RentInfo,
)
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.user_input_schema import Conditions, Dependents, Income
from app.schemas.verification_schema import CompanyFiling
from app.services.verification import _classify, verify


def _basic_request(gross: int = 30_000_000) -> AnalyzeRequest:
    return AnalyzeRequest(
        income=Income(total_salary=gross, non_taxable=0, bonus=0),
        dependents=Dependents(has_spouse=False),
        conditions=Conditions(
            householder=True,
            no_house=True,
            lease_contract=False,
            has_loan=False,
        ),
        parsed_pdf=ParsedPdfData(),
        manual_input=ManualInputRequest(
            rent=RentInfo(has_rent=False),
            housing_loan=HousingLoanInfo(has_loan=False),
        ),
    )


# -------------------- 단위 --------------------


def test_classify_thresholds():
    assert _classify(0) == "match"
    assert _classify(500) == "minor"
    assert _classify(-500) == "minor"
    assert _classify(1000) == "major"
    assert _classify(-1000) == "major"


# -------------------- 통합: 자가 일치 --------------------


def test_self_consistent_no_diff():
    """
    자체 산식 결과를 그대로 회사 신고에 넣으면 모든 비교 단계 'match'.
    이는 '회사가 우리 산식과 똑같이 신고했을 때' 케이스.
    """
    req = _basic_request(30_000_000)
    # 30M / 단신 / 표준세액공제 → test_golden_single_30M 의 기댓값과 동일
    filing = CompanyFiling(
        determined_tax=682_500,
        prepaid_tax=1_000_000,
        earned_income_deduction=9_750_000,
        earned_income_amount=20_250_000,
        personal_deduction=1_500_000,
        taxable_income=18_750_000,
        calculated_tax=1_552_500,
        earned_income_tax_credit=740_000,
        local_income_tax=68_250,
    )

    report = verify(req, filing)
    severities = {s.severity for s in report.steps}
    assert severities == {"match"}
    assert report.has_major_diff is False
    assert report.final_delta == 0
    assert "일치" in report.summary
    # 단정적 표현 금지
    assert "오류" not in report.summary
    assert "잘못" not in report.summary


# -------------------- 결정세액 큰 차이 --------------------


def test_major_diff_in_determined_tax():
    req = _basic_request(30_000_000)
    filing = CompanyFiling(
        determined_tax=900_000,  # 자체 산식 682,500 보다 큼
        prepaid_tax=1_000_000,
        earned_income_deduction=9_750_000,
        earned_income_amount=20_250_000,
        personal_deduction=1_500_000,
        taxable_income=18_750_000,
        calculated_tax=1_552_500,
        earned_income_tax_credit=740_000,
        local_income_tax=90_000,
    )

    report = verify(req, filing)
    by_name = {s.name: s for s in report.steps}
    assert by_name["determined_tax"].severity == "major"
    assert by_name["determined_tax"].delta == 682_500 - 900_000  # negative
    assert by_name["earned_income_deduction"].severity == "match"
    assert report.has_major_diff is True

    # final_delta < 0 → 자체 산식 < 회사 → 환급 더 받을 수 있음(refund_delta > 0)
    assert report.final_delta is not None and report.final_delta < 0
    assert report.refund_delta is not None and report.refund_delta > 0
    assert "수정 신고" in report.summary or "확인" in report.summary


# -------------------- 반올림 오차 --------------------


def test_minor_rounding_diff():
    req = _basic_request(30_000_000)
    filing = CompanyFiling(
        determined_tax=682_500 + 100,  # 100원 차이
        prepaid_tax=1_000_000,
        local_income_tax=68_250,
    )
    report = verify(req, filing)
    determined = next(s for s in report.steps if s.name == "determined_tax")
    assert determined.severity == "minor"
    assert report.has_major_diff is False
    assert "반올림" in report.summary or "차이만" in report.summary


# -------------------- 일부 필드 누락 --------------------


def test_missing_fields_skip_comparison():
    req = _basic_request(30_000_000)
    filing = CompanyFiling(
        determined_tax=682_500,
        prepaid_tax=1_000_000,
        # 다른 모든 단계 None — 회사가 결정세액만 알려줬을 때
        local_income_tax=68_250,
    )
    report = verify(req, filing)
    missing_steps = [s for s in report.steps if s.severity == "missing"]
    assert len(missing_steps) >= 5  # 다수 누락
    assert "비교를 건너뛰" in report.summary


# -------------------- local_tax 자동 추정 --------------------


def test_local_tax_inferred_from_determined():
    """회사가 local_income_tax 만 안 알려줬으면 결정세액 × 10% 로 추정해 비교."""
    req = _basic_request(30_000_000)
    filing = CompanyFiling(
        determined_tax=682_500,
        prepaid_tax=1_000_000,
        local_income_tax=None,  # 추정 사용
    )
    report = verify(req, filing)
    # company_total = 682,500 + round(682,500 * 0.10) = 682,500 + 68,250 = 750,750
    # our.total_tax = 750,750 → final_delta = 0
    assert report.final_delta == 0


# -------------------- 환급 추가 가능 케이스 --------------------


def test_refund_delta_sign_when_we_say_smaller_tax():
    """우리 산식이 회사보다 결정세액을 작게 본다 → 환급액 차이는 양수."""
    req = _basic_request(30_000_000)
    filing = CompanyFiling(
        determined_tax=682_500 + 50_000,  # 회사 더 큼
        prepaid_tax=1_000_000,
        local_income_tax=int(round((682_500 + 50_000) * 0.10)),
    )
    report = verify(req, filing)
    assert report.refund_delta is not None and report.refund_delta > 0


# -------------------- step anchor 가 함께 실리는지 --------------------


def test_steps_carry_legal_anchors():
    req = _basic_request(30_000_000)
    filing = CompanyFiling(determined_tax=682_500, prepaid_tax=1_000_000)
    report = verify(req, filing)
    eid = next(s for s in report.steps if s.name == "earned_income_deduction")
    assert eid.legal_anchor and "소득세법" in eid.legal_anchor
    calc = next(s for s in report.steps if s.name == "calculated_tax")
    assert calc.legal_anchor and "§55" in calc.legal_anchor
