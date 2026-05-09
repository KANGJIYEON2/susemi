"""
Phase 4-3 추천 테스트.
"""

from app.schemas.analysis_schema import AnalyzeRequest
from app.schemas.manual_input_schema import (
    HousingLoanInfo,
    ManualInputRequest,
    RentInfo,
)
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.recommend_schema import RecommendRequest
from app.schemas.user_input_schema import Conditions, Dependents, Income
from app.services.recommend import recommend


def _request(
    *,
    gross: int = 30_000_000,
    householder: bool = True,
    no_house: bool = True,
    lease: bool = True,
) -> AnalyzeRequest:
    return AnalyzeRequest(
        income=Income(total_salary=gross, non_taxable=0, bonus=0),
        dependents=Dependents(has_spouse=False),
        conditions=Conditions(
            householder=householder,
            no_house=no_house,
            lease_contract=lease,
            has_loan=False,
        ),
        parsed_pdf=ParsedPdfData(),
        manual_input=ManualInputRequest(
            rent=RentInfo(has_rent=False),
            housing_loan=HousingLoanInfo(has_loan=False),
        ),
    )


# -------------------- 기본 --------------------


def test_recommend_returns_all_levers():
    req = RecommendRequest(
        request=_request(), baseline_prepaid_tax=1_000_000
    )
    res = recommend(req)
    ids = [r.lever.lever_id for r in res.recommendations]
    assert set(ids) == {"pension_400", "pension_irp_700", "donation_100k", "rent_credit"}


def test_recommend_sorted_by_delta_desc():
    """자격 충족 항목들은 delta 큰 순으로 앞에 옴."""
    req = RecommendRequest(
        request=_request(gross=30_000_000), baseline_prepaid_tax=1_000_000
    )
    res = recommend(req)
    eligible = [r for r in res.recommendations if r.eligible]
    deltas = [r.refund_delta for r in eligible]
    assert deltas == sorted(deltas, reverse=True)


# -------------------- 자격 검사 --------------------


def test_rent_credit_eligible_when_conditions_met():
    req = RecommendRequest(
        request=_request(householder=True, no_house=True, lease=True),
        baseline_prepaid_tax=1_000_000,
    )
    res = recommend(req)
    rent = next(r for r in res.recommendations if r.lever.lever_id == "rent_credit")
    assert rent.eligible is True
    assert rent.refund_delta > 0


def test_rent_credit_inel_when_not_householder():
    req = RecommendRequest(
        request=_request(householder=False, no_house=True, lease=True),
        baseline_prepaid_tax=1_000_000,
    )
    res = recommend(req)
    rent = next(r for r in res.recommendations if r.lever.lever_id == "rent_credit")
    assert rent.eligible is False
    assert rent.refund_delta == 0
    assert rent.note and "세대주" in rent.note


def test_rent_credit_inel_when_owns_house():
    req = RecommendRequest(
        request=_request(householder=True, no_house=False, lease=True),
        baseline_prepaid_tax=1_000_000,
    )
    res = recommend(req)
    rent = next(r for r in res.recommendations if r.lever.lever_id == "rent_credit")
    assert rent.eligible is False
    assert rent.note and "무주택" in rent.note


# -------------------- 미적격은 뒤로 --------------------


def test_ineligible_pushed_to_back():
    req = RecommendRequest(
        request=_request(householder=False),
        baseline_prepaid_tax=1_000_000,
    )
    res = recommend(req)
    last = res.recommendations[-1]
    # 자격 미충족인 lever 가 마지막
    assert last.eligible is False


# -------------------- 세율 차등 --------------------


def test_pension_credit_rate_high_income_lower_delta():
    """총급여 5500만 초과 시 세율 12% — delta 가 더 작음."""
    low_req = RecommendRequest(
        request=_request(gross=40_000_000), baseline_prepaid_tax=1_000_000
    )
    high_req = RecommendRequest(
        request=_request(gross=80_000_000), baseline_prepaid_tax=10_000_000
    )
    low_res = recommend(low_req)
    high_res = recommend(high_req)

    low_p = next(
        r for r in low_res.recommendations if r.lever.lever_id == "pension_400"
    )
    high_p = next(
        r for r in high_res.recommendations if r.lever.lever_id == "pension_400"
    )
    # baseline 의 결정세액이 충분히 크다면 delta 는 거의 credit 액수와 같음
    # 4,000,000 × 0.132 = 528,000 / 4,000,000 × 0.12 = 480,000
    assert low_p.refund_delta > high_p.refund_delta


# -------------------- delta = projected - baseline --------------------


def test_delta_equals_projected_minus_baseline():
    req = RecommendRequest(
        request=_request(gross=50_000_000), baseline_prepaid_tax=2_000_000
    )
    res = recommend(req)
    for r in res.recommendations:
        assert r.refund_delta == r.projected_refund - r.baseline_refund


# -------------------- 결정세액이 작으면 delta 가 cap 됨 --------------------


def test_delta_capped_when_determined_tax_small():
    """
    매우 낮은 소득 → 결정세액이 작음 → 추가 세액공제는 결정세액을 0 으로 만들면 끝.
    delta 가 lever 의 명목 credit 보다 작아짐.
    """
    req = RecommendRequest(
        request=_request(gross=20_000_000),
        baseline_prepaid_tax=200_000,
    )
    res = recommend(req)
    pension = next(
        r for r in res.recommendations if r.lever.lever_id == "pension_400"
    )
    # 명목: 2000만은 5500 이하 → 13.2% × 400만 = 528,000
    # 실 baseline 결정세액이 작으면 delta 가 528,000 미만일 수 있음
    nominal_credit = int(round(4_000_000 * 0.132))
    assert pension.refund_delta <= nominal_credit
    assert pension.refund_delta >= 0
