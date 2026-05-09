"""
RuleDraft 디스크 저장소.

== 디렉토리 구조 ==
server/app/data/rules/drafts/{year}/{rule_id}.json

== 워크플로 ==
- save_draft(draft): 동일 (year, rule_id) 면 덮어씀
- list_drafts(year=None): 전체 또는 연도별 리스트
- load_draft(year, rule_id) -> RuleDraft | None
- delete_draft(year, rule_id)
- approve_draft(year, rule_id) -> Rule  : draft 의 rule 을 rules/{year}.json 에 병합 (id 일치 시 교체) 후 draft 파일 삭제
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.rule_draft_schema import RuleDraft
from app.schemas.rule_schema import Rule, RulePack


DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DRAFTS_SUBDIR = ("rules", "drafts")
PUBLISHED_SUBDIR = ("rules",)


def _drafts_dir(data_dir: Path) -> Path:
    return data_dir.joinpath(*DRAFTS_SUBDIR)


def _drafts_year_dir(data_dir: Path, year: int) -> Path:
    return _drafts_dir(data_dir) / str(year)


def _draft_path(data_dir: Path, year: int, rule_id: str) -> Path:
    return _drafts_year_dir(data_dir, year) / f"{rule_id}.json"


def _published_path(data_dir: Path, year: int) -> Path:
    return data_dir.joinpath(*PUBLISHED_SUBDIR) / f"{year}.json"


# -------------------- CRUD --------------------


def save_draft(
    draft: RuleDraft, data_dir: Path | None = None
) -> Path:
    base = data_dir or DEFAULT_DATA_DIR
    year = draft.rule.year
    rule_id = draft.rule.rule_id
    path = _draft_path(base, year, rule_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_draft(
    year: int, rule_id: str, data_dir: Path | None = None
) -> RuleDraft | None:
    base = data_dir or DEFAULT_DATA_DIR
    path = _draft_path(base, year, rule_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RuleDraft.model_validate(data)
    except (OSError, json.JSONDecodeError):
        return None


def list_drafts(
    year: int | None = None, data_dir: Path | None = None
) -> list[RuleDraft]:
    base = data_dir or DEFAULT_DATA_DIR
    root = _drafts_dir(base)
    if not root.exists():
        return []

    out: list[RuleDraft] = []
    if year is not None:
        year_dirs: list[Path] = [_drafts_year_dir(base, year)]
    else:
        year_dirs = [d for d in root.iterdir() if d.is_dir()]

    for ydir in year_dirs:
        if not ydir.exists():
            continue
        for f in sorted(ydir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                out.append(RuleDraft.model_validate(data))
            except (OSError, json.JSONDecodeError):
                continue

    out.sort(key=lambda d: d.saved_at, reverse=True)
    return out


def delete_draft(
    year: int, rule_id: str, data_dir: Path | None = None
) -> bool:
    base = data_dir or DEFAULT_DATA_DIR
    path = _draft_path(base, year, rule_id)
    if not path.exists():
        return False
    path.unlink()
    return True


# -------------------- approve --------------------


def approve_draft(
    year: int,
    rule_id: str,
    review_notes: str | None = None,
    data_dir: Path | None = None,
) -> Rule:
    """
    드래프트의 rule 을 rules/{year}.json 에 병합:
    - 동일 rule_id 가 있으면 교체
    - 없으면 추가
    드래프트 파일은 삭제 (히스토리는 git 으로 관리)
    """
    base = data_dir or DEFAULT_DATA_DIR
    draft = load_draft(year, rule_id, data_dir=base)
    if draft is None:
        raise FileNotFoundError(
            f"드래프트 없음: year={year}, rule_id={rule_id}"
        )

    # 인메모리 캐시(load_rules @lru_cache) 무효화
    from app.services.rules_engine import load_rules

    load_rules.cache_clear()

    rule = draft.rule.model_copy(update={"human_reviewed": True})

    # 기존 팩 로드 (없으면 새로 생성)
    pub_path = _published_path(base, year)
    if pub_path.exists():
        pack_data = json.loads(pub_path.read_text(encoding="utf-8"))
        pack = RulePack.model_validate(pack_data)
    else:
        pack = RulePack(year=year, rules=[])

    # 동일 rule_id 교체 또는 추가
    replaced = False
    for i, existing in enumerate(pack.rules):
        if existing.rule_id == rule.rule_id:
            pack.rules[i] = rule
            replaced = True
            break
    if not replaced:
        pack.rules.append(rule)

    pub_path.parent.mkdir(parents=True, exist_ok=True)
    pub_path.write_text(
        json.dumps(pack.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 드래프트 삭제 (review_notes 가 있으면 마지막 상태를 별도 보관해도 좋지만,
    # 1차 구현은 단순 삭제. 검수 이력은 git history 로.)
    delete_draft(year, rule_id, data_dir=base)

    return rule


def reject_draft(
    year: int,
    rule_id: str,
    review_notes: str | None = None,
    data_dir: Path | None = None,
) -> bool:
    """
    1차 구현: 단순 삭제. 추후 rejected/{year}/{rule_id}.json 으로 보관 옵션 추가 가능.
    """
    return delete_draft(year, rule_id, data_dir=data_dir)
