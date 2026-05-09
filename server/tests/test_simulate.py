"""
Phase 4-1 시뮬레이션 테스트.
"""

from app.schemas.analysis_schema import AnalyzeRequest
from app.schemas.manual_input_schema import (
    HousingLoanInfo,
    ManualInputRequest,
    RentInfo,
)
from app.schemas.pdf_schema import ParsedPdfData
from app.schemas.simulate_schema import SimulateRequest, YearOverride
from app.schemas.user_input_schema import Conditions, Dependents, Income
from app.services.simulate import simulate


def _baseline_request(gross: int = 30_000_000) -> AnalyzeRequest:
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


# -------------------- 빈 시나리오 --------------------


def test_empty_years_runs_baseline_only():
    req = SimulateRequest(
        baseline_request=_baseline_request(30_000_000),
        baseline_prepaid_tax=1_000_000,
        years=[],
    )
    res = simulate(req)
    assert res.baseline_year == 2025
    assert res.baseline.year == 2025
    assert res.baseline.note == "현재(베이스라인)"
    assert res.projections == []
    # 골든셋(test_golden_single_30M)과 동일
    assert res.baseline.result.refund_or_owed == 249_250
    assert res.cumulative_refund == 249_250


# -------------------- 단일 연도 override (연봉 인상) --------------------


def test_salary_increase_one_year():
    req = SimulateRequest(
        baseline_request=_baseline_request(30_000_000),
        baseline_prepaid_tax=1_000_000,
        years=[
            YearOverride(year=2026, gross_salary=33_000_000, prepaid_tax=1_100_000),
        ],
    )
    res = simulate(req)
    assert len(res.projections) == 1
    p = res.projections[0]
    assert p.year == 2026
    assert p.inputs_used.gross_salary == 33_000_000
    assert p.inputs_used.prepaid_tax == 1_100_000
    # baseline 보다 산출세액 더 큼
    assert p.result.calculated_tax > res.baseline.result.calculated_tax


# -------------------- 5년 시나리오 (carry-forward) --------------------


def test_five_year_carry_forward():
    """첫 해에만 연봉 override → 이후 4년은 같은 연봉 자동 상속."""
    req = SimulateRequest(
        baseline_request=_baseline_request(30_000_000),
        baseline_prepaid_tax=1_000_000,
        years=[
            YearOverride(year=2026, gross_salary=33_000_000),
            YearOverride(year=2027),  # carry-forward
            YearOverride(year=2028),
            YearOverride(year=2029),
            YearOverride(year=2030),
        ],
    )
    res = simulate(req)
    assert len(res.projections) == 5
    # 모두 33M
    salaries = {p.inputs_used.gross_salary for p in res.projections}
    assert salaries == {33_000_000}


# -------------------- 부양가족 추가 (life event) --------------------


def test_add_dependent_in_year_2():
    req = SimulateRequest(
        baseline_request=_baseline_request(50_000_000),
        baseline_prepaid_tax=2_500_000,
        years=[
            YearOverride(year=2026, note="유지"),
            YearOverride(
                year=2027,
                spouse=True,
                dependents_count=1,
                note="결혼 + 자녀",
            ),
        ],
    )
    res = simulate(req)
    p2026 = res.projections[0]
    p2027 = res.projections[1]

    # 2026 은 baseline 과 동일한 인적공제
    assert p2026.inputs_used.dependents.spouse is False
    assert p2026.inputs_used.dependents.dependents_count == 0
    # 2027 은 부양가족 +1, 배우자 추가
    assert p2027.inputs_used.dependents.spouse is True
    assert p2027.inputs_used.dependents.dependents_count == 1
    # 인적공제 늘어 → 결정세액 줄어
    assert p2027.result.determined_tax < p2026.result.determined_tax


# -------------------- 누적 합계 --------------------


def test_cumulative_aggregates():
    req = SimulateRequest(
        baseline_request=_baseline_request(30_000_000),
        baseline_prepaid_tax=1_000_000,
        years=[
            YearOverride(year=2026),
            YearOverride(year=2027),
        ],
    )
    res = simulate(req)
    expected = res.baseline.result.refund_or_owed + sum(
        p.result.refund_or_owed for p in res.projections
    )
    assert res.cumulative_refund == expected


# -------------------- override 가 직전 연도 기준이지 베이스라인이 아님 --------------------


def test_override_chains_from_previous_year():
    """y1: 33M, y2: spouse=True, y3: dependents=1 → y3 도 spouse=True 유지."""
    req = SimulateRequest(
        baseline_request=_baseline_request(30_000_000),
        baseline_prepaid_tax=1_000_000,
        years=[
            YearOverride(year=2026, gross_salary=33_000_000),
            YearOverride(year=2027, spouse=True),
            YearOverride(year=2028, dependents_count=1),
        ],
    )
    res = simulate(req)
    y3 = res.projections[2]
    assert y3.inputs_used.gross_salary == 33_000_000
    assert y3.inputs_used.dependents.spouse is True
    assert y3.inputs_used.dependents.dependents_count == 1


# -------------------- 베이스라인 prepaid_tax 적용 --------------------


def test_baseline_prepaid_tax_used():
    req = SimulateRequest(
        baseline_request=_baseline_request(30_000_000),
        baseline_prepaid_tax=1_000_000,
        years=[],
    )
    res = simulate(req)
    assert res.baseline.inputs_used.prepaid_tax == 1_000_000


# -------------------- 외부 공제 합산 적용 --------------------


def test_extra_deductions_applied_to_baseline():
    req = SimulateRequest(
        baseline_request=_baseline_request(50_000_000),
        baseline_prepaid_tax=2_000_000,
        extra_income_deductions=2_000_000,
        extra_tax_credits=300_000,
        years=[],
    )
    res = simulate(req)
    # test_golden_with_extra_deductions 와 동일 기댓값 (배우자 1, 자녀 1 가정 제외)
    # 여기선 단신이라 다름. 그래도 extra 가 들어간 건 결정세액에 반영
    base = res.baseline
    assert base.inputs_used.extra_income_deductions == 2_000_000
    assert base.inputs_used.extra_tax_credits == 300_000
