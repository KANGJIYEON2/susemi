"""
골든셋 calibration 테스트.

`tests/golden/*.json` 의 모든 파일을 자동 로드해 parametrize.
사용자가 국세청 모의계산기로 검증한 케이스를 추가/수정할 때:
  - 새 .json 파일 떨구거나 기존 파일의 expected 값 조정
  - source / calibrated_at 메타 갱신
  - pytest 재실행

스키마: tests/golden/README.md 참조.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.tax_calculator_schema import CalcInputs
from app.services.tax_calculator import CalcResult, calculate


GOLDEN_DIR = Path(__file__).parent / "golden"


def _list_cases() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    return sorted(GOLDEN_DIR.glob("*.json"))


_CASES = _list_cases()


def _id(case_path: Path) -> str:
    return case_path.stem


@pytest.mark.parametrize("case_path", _CASES, ids=[_id(c) for c in _CASES])
def test_golden_case_matches_expected(case_path: Path):
    data = json.loads(case_path.read_text(encoding="utf-8"))

    name = data.get("name", case_path.stem)
    source = data.get("source", "unknown")
    calibrated = data.get("calibrated_at")

    inputs = CalcInputs.model_validate(data["inputs"])
    expected: dict = data["expected"]

    result: CalcResult = calculate(inputs)

    diffs: list[str] = []
    for field, exp_val in expected.items():
        if not hasattr(result, field):
            diffs.append(f"  · 알 수 없는 필드: {field}")
            continue
        actual = getattr(result, field)
        if actual != exp_val:
            diffs.append(
                f"  · {field}: expected {exp_val:,}, got {actual:,} (Δ {actual - exp_val:+,})"
            )

    assert not diffs, (
        f"\n[{name}] (source={source}, calibrated={calibrated})\n"
        + "\n".join(diffs)
        + f"\n\n→ tests/golden/{case_path.name} 의 expected 값을 조정하거나 "
        "tax_calculator/tax_tables 산식을 수정하세요."
    )


def test_at_least_one_golden_case_exists():
    """디렉터리 자체가 있고 케이스가 1개 이상 있어야 함 (회귀 방지)."""
    assert len(_CASES) >= 1, (
        "tests/golden/ 에 .json 케이스가 없습니다. README.md 참조해 추가하세요."
    )
