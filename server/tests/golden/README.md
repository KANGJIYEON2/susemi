# 골든셋 (calibration cases)

본 디렉터리의 `*.json` 파일은 `tax_calculator.calculate(...)` 의 동치성 검증용
케이스입니다. `test_golden_calibration.py` 가 자동으로 로드해 parametrize 합니다.

## JSON 스키마

```json
{
  "name": "케이스 이름",
  "source": "hand_calculated | official_calculator_YYYY-MM-DD | nts_simulator",
  "calibrated_at": "2026-05-10",
  "notes": "메모, 어떤 가정으로 검증했는지 등",
  "inputs": {
    "gross_salary": 30000000,
    "non_taxable": 0,
    "dependents": {
      "self_eligible": true,
      "spouse": false,
      "dependents_count": 0,
      "senior_count": 0,
      "disabled_count": 0,
      "female_householder": false,
      "single_parent": false
    },
    "extra_income_deductions": 0,
    "extra_tax_credits": 0,
    "itemized": null,
    "use_standard_tax_credit": true,
    "prepaid_tax": 1000000
  },
  "expected": {
    "earned_income_deduction": 9750000,
    "calculated_tax": 1552500,
    "determined_tax": 682500,
    "local_income_tax": 68250,
    "refund_or_owed": 249250
  }
}
```

`expected` 의 필드는 `CalcResult` 의 어떤 필드든 부분집합으로 가능. 일치 검증만.

## 검증 워크플로 (사용자 직접)

1. **국세청 모의계산기 접속**
   - 홈택스 → 세금모의계산 → 근로소득자 연말정산 자동계산
   - https://www.hometax.go.kr (귀속 연도별 모의계산기)

2. **케이스 입력 → 결과 캡처**
   - 본 디렉터리의 `*.json` 의 `inputs` 와 동일한 입력을 모의계산기에 넣고
     결과(결정세액, 환급액 등) 받아옴

3. **차이 발견 시 JSON 수정**
   ```jsonc
   {
     "source": "official_calculator_2026-05-10",  // ← 갱신
     "calibrated_at": "2026-05-10",                // ← 갱신
     "expected": {
       "determined_tax": 682500   // 모의계산기 결과로 갱신
     },
     "notes": "모의계산기와 일치 확인. ..."
   }
   ```

4. **`pytest tests/test_golden_calibration.py -v` 로 동치성 재확인**
   - 차이 발생 시 `tax_calculator` 산식 또는 `tax_tables/2025.json` 상수를 디버깅

## 케이스 추가

새 `*.json` 파일을 본 디렉터리에 떨궈 두기만 하면 자동으로 테스트에 합류.
파일명은 자유 (예: `case_180M_high_income.json`).

## 현재 케이스 출처

| 파일 | source | 메모 |
|---|---|---|
| `case_30M_single.json` | hand_calculated | 본 모듈의 산식 손계산 결과 |
| `case_50M_family.json` | hand_calculated | 동상 |
| `case_high_income_180M.json` | hand_calculated | 38% 구간 — 손계산 |

⚠️ **모든 케이스가 현재 `hand_calculated` 상태.** 운영 신뢰성을 위해 사용자가
국세청 모의계산기로 한 번씩 검증한 뒤 `source` 를 `official_calculator_YYYY-MM-DD`
로 갱신해 주세요.
