# LegalAPIClient — 국가법령정보센터 OPEN API 클라이언트

## 사용법

```python
from app.services.legal_api import LegalAPIClient

async with LegalAPIClient() as client:                      # OC 키는 OPEN_LAW_API_KEY env 에서
    law = await client.get_law("001234", "20250101")        # 법령ID + 시행일자
    chunks = client.to_chunks(law)                          # 조/항/호 단위 청크
    # 룰 컴파일러로 청크 흘려보내기 ...

    # 변경 감지 — API 호출 1회 수반
    fresh = await client.validate_freshness("001234", "20250101")
    if fresh.is_stale:
        ...  # 룰 재컴파일 트리거
```

## 환경변수

| Key | 필수 | 설명 |
|---|---|---|
| `OPEN_LAW_API_KEY` | ✅ | 국가법령정보센터 OPEN API 의 OC(이메일 ID 형식) 코드 |

키 발급: <https://open.law.go.kr> 회원가입 후 OC 발급 신청. 이메일 ID(예: `your_id`) 가 곧 OC.

## 캐시 정책

- 위치: `server/app/data/legal_cache/{law_id}/{effective_date or 'latest'}.json`
- `get_law` 는 cache hit 시 네트워크 호출 없이 캐시 반환 (rate limit 회피)
- 강제 갱신: `get_law(..., force_refresh=True)` 또는 `validate_freshness(...)`
- API 실패 + 캐시 존재 → `data_source="cache_fallback"` 로 표시 후 캐시 반환
- 디스크 캐시는 `server/.gitignore` 에 의해 git 추적 제외 (`.gitkeep` 만 추적)

## verified vs assumed

실제 OC 키로 e2e 호출하여 검증한 결과 (소득세법 MST=285523, 시행 20260421 응답 기준):

| 항목 | 상태 | 비고 |
|---|---|---|
| Base URL `http://www.law.go.kr/DRF` | ✅ verified | https 도 동작하지만 본 코드는 http 로 호출 |
| `lawSearch.do?OC=...&target=law&query=...&type=JSON` | ✅ verified | 검색 응답 = `{ "LawSearch": { "law": [...] } }` |
| `lawService.do?OC=...&target=law&type=JSON&ID=...` | ✅ verified | 본문 조회. `MST=...` 도 동작 (`use_mst=True`) |
| 응답 루트 `법령.기본정보 / 법령.조문.조문단위` | ✅ verified | 정확히 일치 |
| `기본정보.법령명_한글 / 시행일자 / 공포일자 / 법령ID` | ✅ verified | 밑줄 포함 키 사용 |
| `조문단위[].조문번호 / 조문제목 / 조문내용 / 항` | ✅ verified | 추가로 `조문시행일자 / 조문키 / 조문여부` 도 있음 (현재 미사용) |
| `항.항번호 / 항내용 / 호` | ✅ verified | 항번호는 `①②③...` 포맷 |
| `호.호번호 / 호내용` | ✅ verified | 호번호는 `1.` 처럼 점이 붙어 옴 → `_build_chunk_id` 에서 trailing `.` 제거 |
| 호내용이 list/dict 로도 올 수 있음 | ✅ verified + 흡수 | `_norm_text` 로 string/list/dict 모두 정규화 |
| `lawSearch.do?regDtFrom=...` 로 개정 검색 | ⚠️ assumed | `list_changes_since` 의 파라미터/응답 키 미검증 |
| 시행일자 포맷 `YYYYMMDD` | ✅ verified | |

**소득세법 fetch 결과 샘플 (정상)**: 조문 393개 → 청크 1511개. data_source=`api`. text_hash=64자 sha256.

검증된 내부 동작:
- httpx 0.28 async + MockTransport 테스트 (11/11 pass)
- 디스크 캐시 read/write idempotency
- sha256 기반 변경 감지 (`validate_freshness`)
- 캐시 fallback (API 5xx 시 cache_fallback 마크)
- chunk_id 한글 anchor 포맷 (`소득세법-§1-①-1`)

## 한계 / TODO

- **별표 / 별지 / 부칙 / 한자 병기**: 1차 구현은 본문(조/항/호) 만 추출. 별표 등은 추후.
- **시행일자 미지정 시**: API 가 최신본을 주는지 미검증. `effective_date=None` 호출 시 응답에서 시행일자를 받아 채움.
- **list_changes_since**: 파라미터/응답 모두 추정. 실제 API 검증 후 재작성 필요.
- **Rate limit**: OPEN.LAW 는 조회 한도가 있음. 캐시에 의존하고, `validate_freshness` 는 신중히 호출할 것.
- **XML 응답**: 현재 JSON 만. XML 필요 시 `_fetch_law_raw` 에서 `type=XML` + `xmltodict` 또는 `lxml` 추가.

## 다음 단계 (Phase 3-2 와의 연결)

1. 사용자가 OC 키 발급 → `.env` 에 `OPEN_LAW_API_KEY` 등록
2. 실제 응답 확인 (예: 소득세법 = 법령ID `011357` 또는 `001934` 등)
3. 응답 구조 다르면 `_parse_law_response` 키 매핑 갱신 + 본 README 의 verified 표 업데이트
4. 룰 컴파일러(Phase 3-2)가 `to_chunks(law)` 출력을 입력으로 받아 LLM 으로 룰 JSON 생성

## 테스트

```bash
cd server
source venv/bin/activate
pip install -r requirements.txt   # pytest, pytest-asyncio 포함
pytest tests/test_legal_api.py -v
```
