"""
tax_calculator 의 단위 + 골든셋 테스트.

== 검증 방식 ==
- 단위 테스트: 각 함수(근로소득공제, 누진세율, 인적공제, 근로세액공제)별 구간/엣지 케이스.
- 골든셋: 5개 종합 시나리오. 기대값은 본 모듈의 공식을 손으로 step-by-step 계산한 값.
- 향후 사용자가 국세청 모의계산기로 케이스를 받아 fixture 화하면 더 강건해짐.
"""

import pytest

from app.schemas.tax_calculator_schema import CalcInputs, DependentsInput
from app.services.tax_calculator import (
    calculate,
    earned_income_deduction,
    earned_income_tax_credit,
    load_tax_table,
    personal_deduction,
    progressive_tax,
)


@pytest.fixture(scope="module")
def table() -> dict:
    return load_tax_table(year=2025)


# ============================================================
# 단위 테스트: earned_income_deduction
# ============================================================


@pytest.mark.parametrize(
    "gross,expected,desc",
    [
        # 0~500만 구간: 70%
        (4_000_000, int(4_000_000 * 0.70), "500만 이하 70%"),
        # 500~1500만: 350만 + (gross-500만)*40%
        (10_000_000, 3_500_000 + int((10_000_000 - 5_000_000) * 0.40), "1000만"),
        # 1500~4500만: 750만 + (gross-1500만)*15%
        (
            30_000_000,
            7_500_000 + int((30_000_000 - 15_000_000) * 0.15),
            "3000만",
        ),
        # 4500~1억: 1200만 + (gross-4500만)*5%
        (
            80_000_000,
            12_000_000 + int((80_000_000 - 45_000_000) * 0.05),
            "8000만",
        ),
        # 1억 초과: 1475만 + (gross-1억)*2%
        (
            150_000_000,
            14_750_000 + int((150_000_000 - 100_000_000) * 0.02),
            "1.5억",
        ),
        # 한도(2,000만) 적용 — 매우 고소득
        (3_000_000_000, 20_000_000, "한도 2,000만"),
    ],
)
def test_earned_income_deduction(table, gross, expected, desc):
    assert earned_income_deduction(gross, table) == expected, desc


def test_earned_income_deduction_zero(table):
    assert earned_income_deduction(0, table) == 0
    assert earned_income_deduction(-1000, table) == 0


# ============================================================
# 단위 테스트: progressive_tax
# ============================================================


@pytest.mark.parametrize(
    "taxable,expected,desc",
    [
        (0, 0, "0원"),
        (10_000_000, int(10_000_000 * 0.06), "1400만 이하 6%"),
        (
            30_000_000,
            840_000 + int((30_000_000 - 14_000_000) * 0.15),
            "3000만 (1400~5000 구간)",
        ),
        (
            80_000_000,
            6_240_000 + int((80_000_000 - 50_000_000) * 0.24),
            "8000만 (5000~8800 구간)",
        ),
        (
            120_000_000,
            15_360_000 + int((120_000_000 - 88_000_000) * 0.35),
            "1.2억 (8800~1.5억 구간)",
        ),
        (
            200_000_000,
            37_060_000 + int((200_000_000 - 150_000_000) * 0.38),
            "2억 (1.5~3억 구간)",
        ),
    ],
)
def test_progressive_tax(table, taxable, expected, desc):
    assert progressive_tax(taxable, table) == expected, desc


# ============================================================
# 단위 테스트: personal_deduction
# ============================================================


def test_personal_deduction_single(table):
    deps = DependentsInput()
    total, breakdown = personal_deduction(deps, table)
    assert total == 1_500_000
    assert breakdown == {"basic_self": 1_500_000}


def test_personal_deduction_with_family(table):
    deps = DependentsInput(
        spouse=True,
        dependents_count=2,  # 자녀 둘
        senior_count=1,
        disabled_count=1,
    )
    total, _ = personal_deduction(deps, table)
    # 본인 150 + 배우자 150 + 부양가족 150*2 + 경로 100 + 장애 200 = 900만
    assert total == 1_500_000 * 4 + 1_000_000 + 2_000_000


def test_personal_deduction_single_parent_overrides_female(table):
    deps = DependentsInput(single_parent=True, female_householder=True)
    total, breakdown = personal_deduction(deps, table)
    assert "additional_single_parent" in breakdown
    assert "additional_female_householder" not in breakdown
    # 본인 150 + 한부모 100 = 250
    assert total == 2_500_000


# ============================================================
# 단위 테스트: earned_income_tax_credit
# ============================================================


def test_eitc_low_calculated_tax(table):
    # 산출세액 100만 → 55% = 55만, 한도(총급여 3000만) 74만 → 55만
    assert earned_income_tax_credit(1_000_000, 30_000_000, table) == 550_000


def test_eitc_high_calculated_tax_capped(table):
    # 산출세액 500만 → 71.5 + (500-130)*30% = 71.5 + 111 = 182.5만
    # 한도(총급여 3000만) 74만 → 74만으로 cap
    assert earned_income_tax_credit(5_000_000, 30_000_000, table) == 740_000


def test_eitc_cap_high_gross(table):
    # 총급여 1.5억 → 한도 = 500,000 - (1.5억-1.2억)*0.005 = 500,000 - 150,000 = 350,000
    # 산출세액 충분히 큼
    assert earned_income_tax_credit(20_000_000, 150_000_000, table) == 350_000


# ============================================================
# 골든셋: 종합 시나리오
# ============================================================


def test_golden_single_30M():
    """
    총급여 30,000,000 / 단신 / 인적공제 본인만 / 표준세액공제 / 기납부 1,000,000

    근로소득공제 = 750만 + (3000-1500)×15% = 975만
    근로소득금액 = 3000-975 = 2025만
    인적공제 = 본인 150만
    과세표준 = 2025-150 = 1875만
    산출세액 = 84만 + (1875-1400)×15% = 84만 + 71.25만 = 1,552,500
    근로세액공제 raw = 71.5만 + (155.25-130)×30% = 79.075만
       한도(3000만) = 74만 → 740,000
    표준세액공제 = 130,000
    결정세액 = 1,552,500 - 740,000 - 130,000 = 682,500
    지방소득세 = 68,250
    총 부담 = 750,750
    환급 = 1,000,000 - 750,750 = 249,250
    """
    inputs = CalcInputs(
        gross_salary=30_000_000,
        prepaid_tax=1_000_000,
    )
    r = calculate(inputs)
    assert r.earned_income_deduction == 9_750_000
    assert r.earned_income_amount == 20_250_000
    assert r.personal_deduction == 1_500_000
    assert r.taxable_income == 18_750_000
    assert r.calculated_tax == 1_552_500
    assert r.earned_income_tax_credit == 740_000
    assert r.standard_tax_credit == 130_000
    assert r.determined_tax == 682_500
    assert r.local_income_tax == 68_250
    assert r.total_tax == 750_750
    assert r.refund_or_owed == 249_250


def test_golden_family_50M():
    """
    총급여 50,000,000 / 배우자 1, 부양가족 1 / 표준세액공제 / 기납부 2,000,000

    근로소득공제 (5000만은 4500~1억 구간, 5%):
      = 1,200만 + (5000-4500)×5% = 1,225만 = 12,250,000
    근로소득금액 = 5000-1225 = 3,775만 = 37,750,000
    인적공제 = 본인 150 + 배우자 150 + 부양가족 150 = 450만
    과세표준 = 3775-450 = 3,325만 = 33,250,000
    산출세액 = 84만 + (3325-1400)×15% = 84 + 288.75 = 372.75만 = 3,727,500
    근로세액공제 raw = 71.5 + (372.75-130)×30% = 144.325만
       한도(5000만, 33M~70M): 740,000 - (50M-33M)×0.008 = 604,000 → min 660,000 적용 → 660,000
    표준세액공제 = 130,000
    결정세액 = 3,727,500 - 660,000 - 130,000 = 2,937,500
    지방 = 293,750
    총 = 3,231,250
    환급 = 2,000,000 - 3,231,250 = -1,231,250 (추징)
    """
    inputs = CalcInputs(
        gross_salary=50_000_000,
        dependents=DependentsInput(spouse=True, dependents_count=1),
        prepaid_tax=2_000_000,
    )
    r = calculate(inputs)
    assert r.earned_income_deduction == 12_250_000
    assert r.earned_income_amount == 37_750_000
    assert r.personal_deduction == 4_500_000
    assert r.taxable_income == 33_250_000
    assert r.calculated_tax == 3_727_500
    assert r.earned_income_tax_credit == 660_000
    assert r.determined_tax == 2_937_500
    assert r.local_income_tax == 293_750
    assert r.total_tax == 3_231_250
    assert r.refund_or_owed == -1_231_250


def test_golden_high_income_80M():
    """
    총급여 80,000,000 / 단신 / 표준세액공제 / 기납부 5,000,000

    근로소득공제 = 1,200만 + (8000-4500)×5% = 1,375만
    근로소득금액 = 8000-1375 = 6625만
    인적공제 = 본인 150
    과세표준 = 6625-150 = 6475만
    산출세액 = 624만 + (6475-5000)×24% = 624만 + 354만 = 9,780,000
    근로세액공제 raw = 71.5 + (978-130)×30% = 71.5 + 254.4 = 325.9만
       한도(8000만): 70M~120M 구간
       cap = 660,000 - (80M-70M)×0.005 = 660,000 - 50,000 = 610,000
    표준세액공제 = 130,000
    결정세액 = 9,780,000 - 610,000 - 130,000 = 9,040,000
    지방 = 904,000
    총 = 9,944,000
    환급 = 5,000,000 - 9,944,000 = -4,944,000 (추징)
    """
    inputs = CalcInputs(gross_salary=80_000_000, prepaid_tax=5_000_000)
    r = calculate(inputs)
    assert r.earned_income_deduction == 13_750_000
    assert r.earned_income_amount == 66_250_000
    assert r.taxable_income == 64_750_000
    assert r.calculated_tax == 9_780_000
    assert r.earned_income_tax_credit == 610_000
    assert r.determined_tax == 9_040_000
    assert r.local_income_tax == 904_000
    assert r.refund_or_owed == -4_944_000


def test_golden_low_income_25M_likely_refund():
    """
    총급여 25,000,000 / 단신 / 기납부 800,000 (회사가 좀 많이 떼었다고 가정)

    근로소득공제 = 750 + (2500-1500)*15% = 900만
    근로소득금액 = 2500-900 = 1600만
    인적공제 150
    과세표준 = 1600-150 = 1450만
    산출세액 = 84 + (1450-1400)*15% = 84 + 7.5 = 91.5만 = 915,000
    근로세액공제 raw = 91.5만 × 55% = 503,250
       한도(2500만 < 3300만) = 740,000 → 503,250
    표준세액공제 130,000
    결정세액 = 915,000 - 503,250 - 130,000 = 281,750
    지방 = 28,175
    총 = 309,925
    환급 = 800,000 - 309,925 = 490,075
    """
    inputs = CalcInputs(gross_salary=25_000_000, prepaid_tax=800_000)
    r = calculate(inputs)
    assert r.earned_income_deduction == 9_000_000
    assert r.taxable_income == 14_500_000
    assert r.calculated_tax == 915_000
    assert r.earned_income_tax_credit == 503_250
    assert r.determined_tax == 281_750
    assert r.local_income_tax == 28_175
    assert r.refund_or_owed == 490_075


def test_golden_with_extra_deductions():
    """
    50M 케이스에 신용카드 등 소득공제 200만, 자녀세액공제 30만 추가

    family_50M 의 과세표준 33,250,000 에서 - 2,000,000 → 31,250,000
    - 산출세액 = 84만 + (3125-1400)×15% = 84 + 258.75 = 342.75만 = 3,427,500
    - 근로세액공제 raw = 71.5 + (342.75-130)×30% = 135.325만 → 한도 660,000
    - extra_tax_credits = 300,000
    - 결정세액 = 3,427,500 - 660,000 - 130,000 - 300,000 = 2,337,500
    - 지방 = 233,750
    - 총 = 2,571,250
    - 환급(prepaid 2M) = 2,000,000 - 2,571,250 = -571,250
    """
    inputs = CalcInputs(
        gross_salary=50_000_000,
        dependents=DependentsInput(spouse=True, dependents_count=1),
        extra_income_deductions=2_000_000,
        extra_tax_credits=300_000,
        prepaid_tax=2_000_000,
    )
    r = calculate(inputs)
    assert r.taxable_income == 31_250_000
    assert r.calculated_tax == 3_427_500
    assert r.earned_income_tax_credit == 660_000
    assert r.extra_tax_credits == 300_000
    assert r.determined_tax == 2_337_500
    assert r.local_income_tax == 233_750
    assert r.refund_or_owed == -571_250


# ============================================================
# 골든셋 v2 — 추가 5케이스 (다양한 구간 + 인적공제 조합)
#   ※ 현재 expected 는 본 모듈의 산식을 손계산한 값.
#     국세청 모의계산기로 검증되면 메모 추가하고 실값과 매칭 확인.
# ============================================================


def test_golden_high_income_180M_family_38pct_bracket():
    """
    총급여 180,000,000 / 배우자 + 자녀 2 / 표준세액공제 / 기납부 30M
    소득세법 38% 구간 (1.5억~3억) 진입 케이스.

    근로소득공제 (1억 초과 2%, 한도 2000만):
      = 1,475만 + (180M-100M)×2% = 1,475만 + 160만 = 1,635만 = 16,350,000
    근로소득금액 = 180M - 1,635만 = 163,650,000
    인적공제 = 본인 150 + 배우자 150 + 부양가족 150×2 = 600만 = 6,000,000
    과표 = 163,650,000 - 6,000,000 = 157,650,000
    산출세액 (1.5억~3억 38%):
      = 37,060,000 + (157,650,000 - 150,000,000) × 38%
      = 37,060,000 + 7,650,000 × 0.38
      = 37,060,000 + 2,907,000
      = 39,967,000
    근로세액공제 raw = 71.5만 + (3,996.7만 - 130만)×30% = 12,310,100… (계산 무관 — 한도 cap 적용)
      한도(180M > 1.2억, 4번째 구간): 500,000 - (180M-120M)×0.005 = 200,000
      → 200,000 (min 200,000 도 함께)
    표준세액공제 = 130,000
    결정세액 = 39,967,000 - 200,000 - 130,000 = 39,637,000
    지방 = 3,963,700
    총 부담 = 43,600,700
    환급(prepaid 30M) = 30,000,000 - 43,600,700 = -13,600,700 (추징)
    """
    inputs = CalcInputs(
        gross_salary=180_000_000,
        dependents=DependentsInput(spouse=True, dependents_count=2),
        prepaid_tax=30_000_000,
    )
    r = calculate(inputs)
    assert r.earned_income_deduction == 16_350_000
    assert r.earned_income_amount == 163_650_000
    assert r.personal_deduction == 6_000_000
    assert r.taxable_income == 157_650_000
    assert r.calculated_tax == 39_967_000
    assert r.earned_income_tax_credit == 200_000
    assert r.determined_tax == 39_637_000
    assert r.local_income_tax == 3_963_700
    assert r.refund_or_owed == -13_600_700


def test_golden_single_parent_with_child():
    """
    총급여 35M / 단독 + 자녀 1 + 한부모 / 기납부 1.2M

    근로소득공제 (1500~4500 15%):
      = 750만 + (35M-15M)×15% = 1,050만 = 10,500,000
    근로소득금액 = 35M - 1,050만 = 24,500,000
    인적공제 = 본인 150 + 부양가족 150 + 한부모 100 = 400만 = 4,000,000
      ※ 부녀자 미적용 (한부모 우선 — 단, single_parent=True 시 female 자동 무효)
    과표 = 24.5M - 400만 = 20,500,000
    산출세액 (1400~5000 15%):
      = 840,000 + (20,500,000 - 14,000,000)×15% = 840,000 + 975,000 = 1,815,000
    근로세액공제 raw = 71.5만 + (181.5만 - 130만)×30% = 869,500
      한도 (35M = 33M~70M 구간): 740,000 - (35M-33M)×0.008 = 724,000 → min 660,000 OK → 724,000
      raw 869,500 > cap 724,000 → 724,000
    표준세액공제 = 130,000
    결정세액 = 1,815,000 - 724,000 - 130,000 = 961,000
    지방 = 96,100
    총 = 1,057,100
    환급(prepaid 1.2M) = 1,200,000 - 1,057,100 = 142,900
    """
    inputs = CalcInputs(
        gross_salary=35_000_000,
        dependents=DependentsInput(
            spouse=False, dependents_count=1, single_parent=True
        ),
        prepaid_tax=1_200_000,
    )
    r = calculate(inputs)
    assert r.earned_income_deduction == 10_500_000
    assert r.personal_deduction == 4_000_000
    assert r.taxable_income == 20_500_000
    assert r.calculated_tax == 1_815_000
    assert r.earned_income_tax_credit == 724_000
    assert r.determined_tax == 961_000
    assert r.refund_or_owed == 142_900


def test_golden_disabled_family():
    """
    총급여 60M / 배우자 + 부양가족 1 + 장애인 1 / 기납부 3M
    장애인 추가공제 200만 적용.

    근로소득공제 (4500~1억 5%):
      = 1,200만 + (60M-45M)×5% = 1,275만 = 12,750,000
    근로소득금액 = 60M - 1,275만 = 47,250,000
    인적공제 = 본인 150 + 배우자 150 + 부양가족 150 + 장애인 200 = 650만 = 6,500,000
    과표 = 47.25M - 650만 = 40,750,000
    산출세액 (1400~5000 15%):
      = 840,000 + (40,750,000 - 14,000,000)×15% = 840,000 + 4,012,500 = 4,852,500
    근로세액공제 raw = 71.5만 + (485.25만 - 130만)×30% = 1,780,750
      한도 (60M, 33M~70M): 740,000 - (60M-33M)×0.008 = 524,000 → min 660,000 → 660,000
    표준세액공제 = 130,000
    결정세액 = 4,852,500 - 660,000 - 130,000 = 4,062,500
    지방 = 406,250
    총 = 4,468,750
    환급(prepaid 3M) = 3,000,000 - 4,468,750 = -1,468,750
    """
    inputs = CalcInputs(
        gross_salary=60_000_000,
        dependents=DependentsInput(
            spouse=True, dependents_count=1, disabled_count=1
        ),
        prepaid_tax=3_000_000,
    )
    r = calculate(inputs)
    assert r.earned_income_deduction == 12_750_000
    assert r.personal_deduction == 6_500_000
    assert r.taxable_income == 40_750_000
    assert r.calculated_tax == 4_852_500
    assert r.earned_income_tax_credit == 660_000
    assert r.determined_tax == 4_062_500
    assert r.local_income_tax == 406_250
    assert r.refund_or_owed == -1_468_750


def test_golden_very_low_income_15M():
    """
    총급여 15M / 단신 / 기납부 100,000
    가장 낮은 누진세율(6%) 구간.

    근로소득공제 (500~1500 40%): 1500만 경계 = 350만 + 1000만×40% = 750만 = 7,500,000
      또는 1500~4500 시작점(750만 fixed) — 두 구간 접점에서 동일.
    근로소득금액 = 1,500만 - 750만 = 7,500,000
    인적공제 (본인) = 150만
    과표 = 750만 - 150만 = 6,000,000
    산출세액 (1400만 이하 6%) = 6,000,000 × 0.06 = 360,000
    근로세액공제 raw (산출세액 ≤ 130만 → 55%) = 360,000 × 0.55 = 198,000
      한도 (15M ≤ 33M): 740,000 → 198,000 그대로
    표준세액공제 = 130,000
    결정세액 = 360,000 - 198,000 - 130,000 = 32,000
    지방 = 3,200
    총 = 35,200
    환급(prepaid 100,000) = 100,000 - 35,200 = 64,800
    """
    inputs = CalcInputs(gross_salary=15_000_000, prepaid_tax=100_000)
    r = calculate(inputs)
    assert r.earned_income_deduction == 7_500_000
    assert r.taxable_income == 6_000_000
    assert r.calculated_tax == 360_000
    assert r.earned_income_tax_credit == 198_000
    assert r.determined_tax == 32_000
    assert r.local_income_tax == 3_200
    assert r.refund_or_owed == 64_800


def test_golden_executive_500M_40pct_bracket():
    """
    총급여 500M / 단신 / 기납부 100M
    임원급 — 3억~5억 구간 40% 진입 + 근로소득공제 한도 cap.

    근로소득공제 (1억 초과 2%):
      raw = 1,475만 + (500M-100M)×2% = 1,475만 + 800만 = 2,275만
      → 한도 2,000만 적용 = 20,000,000
    근로소득금액 = 500M - 2,000만 = 480,000,000
    인적공제 (본인) = 150만 = 1,500,000
    과표 = 480M - 150만 = 478,500,000
    산출세액 (3억~5억 40%):
      = 94,060,000 + (478,500,000 - 300,000,000) × 40%
      = 94,060,000 + 178,500,000 × 0.40
      = 94,060,000 + 71,400,000
      = 165,460,000
    근로세액공제: 산출세액 거대하지만 한도(500M, 1.2억 초과 4번째 구간)
      = 500,000 - (500M-120M)×0.005 = 500,000 - 1,900,000 = -1,400,000
      → min 200,000 → 200,000
    표준세액공제 = 130,000
    결정세액 = 165,460,000 - 200,000 - 130,000 = 165,130,000
    지방 = 16,513,000
    총 = 181,643,000
    환급(prepaid 100M) = 100,000,000 - 181,643,000 = -81,643,000 (큰 추징)
    """
    inputs = CalcInputs(gross_salary=500_000_000, prepaid_tax=100_000_000)
    r = calculate(inputs)
    assert r.earned_income_deduction == 20_000_000  # 한도 cap
    assert r.earned_income_amount == 480_000_000
    assert r.personal_deduction == 1_500_000
    assert r.taxable_income == 478_500_000
    assert r.calculated_tax == 165_460_000
    assert r.earned_income_tax_credit == 200_000  # min cap
    assert r.determined_tax == 165_130_000
    assert r.local_income_tax == 16_513_000
    assert r.refund_or_owed == -81_643_000


# ============================================================
# Provenance: 단계 trail 정확성
# ============================================================


def test_steps_contain_all_phases():
    inputs = CalcInputs(gross_salary=30_000_000, prepaid_tax=1_000_000)
    r = calculate(inputs)
    names = [s.name for s in r.steps]
    expected = [
        "earned_income_deduction",
        "earned_income_amount",
        "personal_deduction",
        "taxable_income",
        "calculated_tax",
        "earned_income_tax_credit",
        "standard_tax_credit",
        "determined_tax",
        "local_income_tax",
        "refund_or_owed",
    ]
    for n in expected:
        assert n in names, f"단계 {n} 누락"


def test_step_outputs_match_summary_fields():
    inputs = CalcInputs(gross_salary=30_000_000, prepaid_tax=1_000_000)
    r = calculate(inputs)
    by_name = {s.name: s.output for s in r.steps}
    assert by_name["earned_income_deduction"] == r.earned_income_deduction
    assert by_name["calculated_tax"] == r.calculated_tax
    assert by_name["determined_tax"] == r.determined_tax
    assert by_name["local_income_tax"] == r.local_income_tax
    assert by_name["refund_or_owed"] == r.refund_or_owed


def test_legal_anchors_present():
    inputs = CalcInputs(gross_salary=30_000_000, prepaid_tax=1_000_000)
    r = calculate(inputs)
    by_name = {s.name: s for s in r.steps}
    # 핵심 단계들에는 anchor 가 박혀 있어야 함 (Phase 3-1 Provenance 와 직접 연결)
    assert by_name["earned_income_deduction"].legal_anchor is not None
    assert by_name["calculated_tax"].legal_anchor is not None
    assert by_name["earned_income_tax_credit"].legal_anchor is not None
    assert by_name["local_income_tax"].legal_anchor is not None
