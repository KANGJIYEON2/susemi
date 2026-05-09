# susemi 로드맵 (Plan)

> 본 문서는 작업 우선순위와 결정사항 워킹 문서. 상세 코드 패턴은 [CLAUDE.md](./CLAUDE.md), 사용자용 README 는 [README.md](./README.md) 참조.

```
Status: Phase 1~4 ✅ Complete · Phase 5 보류 (트리거 조건 시)
Tests:  145 passed · 보안 패스 통과 (path traversal 차단 검증)
```

---

## 0. 비전 한 줄

**2025년 귀속** 연말정산을 "왜 이 금액?"까지 **법령 API 기반 조항 trace**로 설명하고, 회사 신고 결과를 **자체 산식으로 cross-check** 하는 서비스. UI 는 노랑 브랜드 + 딥슬레이트 신뢰 톤.

---

## 1. 진행 요약

| Phase | 내용 | 상태 | 핵심 산출물 |
|:---:|---|:---:|---|
| 1 | UI 리디자인 | ✅ | slate-900 + yellow-400 토큰, AppHeader 글자 로고(scrubbing motif), 위저드 5단계 + 4 펼침 섹션 |
| 2-1 | 환급액 산식 + 골든셋 | ✅ | `tax_calculator.py` 정수 기반, `tax_tables/2025.json`, 골든셋 5+단위 27 |
| 2-2 | 룰 JSON 외부화 | ✅ | `rules/2025.json`, `ValueExpr`/`Evaluator` discriminated union, **`eval()` 사용 0줄**, RuleEvaluation 구조화 |
| 2-3 | IndexedDB 클라 영속 | ✅ | `lib/storage.ts` CRUD + IntroStep "이어서 보기" 카드 |
| 2-4 | 법령 API 클라이언트 | ✅ | `legal_api.py` open.law.go.kr 클라이언트, 디스크 캐시, sha256 변경 감지. 실제 OC 키로 e2e 검증(소득세법 1511 청크) |
| 3-1 | Provenance trace | ✅ | `analysis_schema.Section.provenance: list[RuleEvaluation]` + `analyze.py SECTION_TO_RULE_IDS` 매핑 + LLM 프롬프트 `[rule_id]` 강제 |
| 3-2 | LLM 룰 컴파일 + 검수 | ✅ | `rule_compiler.py` + `rule_drafts_store.py` + `/admin/rules` 페이지 |
| 3-3 | 회사 신고 cross-check | ✅ | `verification.py` + `/verify` + ResultStep VerifySection (단정 표현 금지 톤) |
| 4-1 | 다년도 What-if 시뮬 | ✅ | `simulate.py` carry-forward + ResultStep SimulateSection |
| 4-2 | 단순 RAG | ✅ | `rag.py` per-law + cosine + `/admin/rag` |
| 4-3 | Greedy 추천 | ✅ | `recommend.py` 4 lever + ResultStep RecommendSection |
| 4-4 | 의존성 그래프 (ripple) | ✅ | `dependencies.py` 정적 DAG + BFS + `/admin/ripple` |

---

## 2. 결정사항 (확정)

| 항목 | 결정 | 근거 |
|---|---|---|
| 기준 연도 | **2025** | 2025년 귀속분 → 2026 초 정산 |
| 법령 데이터 소스 | **국가법령정보센터 OPEN API** | 단일 출처 + 변경 감지 가능. e2e 검증 통과 |
| UI primary CTA | **slate-900 검정** (`#0F172A`) | 노랑 highlight 대비 가장 강함 |
| 노랑 사용 영역 | CTA primary 1곳 + 숫자 highlight + tip 박스만 | 브랜드 보존 + 신뢰감 균형 |
| 마스코트 노출 | 헤더 글자 로고만 (scrubbing motif SVG) + 결과 페이지 작은 일러스트 | 친근함 + 전문성 균형 |
| 골든셋 출처 | 국세청 모의계산기 + 공식 예제 | 다양성 |
| 아이콘 라이브러리 | `lucide-react` | 트리셰이크, 톤 통일 |
| 다크모드 | v2 보류 | v1 작업량 2배 |
| 서버 사용자 데이터 영속화 | **하지 않음** | 프라이버시 default off |
| 법령 캐시 저장소 | 디스크 (`legal_cache/`) 시작 | 트래픽 늘면 Redis 검토 |
| RAG 임베딩 모델 | `text-embedding-3-small` | 다국어 + 1536 dim + 저렴 |
| RAG 벡터 저장 | 디스크 per-law JSON | 수백 법령까지 OK, 이후 vector DB |
| LLM 모델 | `gpt-4o-mini` | 비용 효율, 한국어 OK |
| 룰 평가기 | Pydantic discriminated union (`eval()` X) | 보안 |

---

## 3. 보안 결정 (Phase 4 후 무자비 테스트로 발굴/적용)

PoC 로 직접 검증한 위협 + 차단 조치:

| 위협 | 발견 경위 | 차단 조치 |
|---|---|---|
| **Path traversal** in `rule_drafts_store` | rule_id="../../../../tmp/PWN" 으로 base 디렉터리 탈출 PoC 성공 | `_SAFE_ID_RE = ^[A-Za-z0-9_\-]+$` 화이트리스트, `UnsafeIdError` 도입, `CompileRequest.target_rule_id` Pydantic pattern, 라우터 400 매핑 |
| Same in `rag._pack_path` & `legal_api._cache_path` | 동일 패턴 | `_safe_path_component` / `_safe_component` 적용 |
| RAG 빈 인덱스에서 OpenAI 호출 | 401 에러 + 비용 발생 | 필터 적용 후 후보 0이면 임베딩 호출 자체 skip |
| `simulate` 음수 입력 | 잘못된 결과로 사용자 혼란 | `YearOverride` 의 number 필드 모두 `ge=0` |
| LLM hallucination (없는 법령 인용) | 프롬프트 회귀 | 시스템 제공 `[rule_id]` 만 인용 허용. 룰 컴파일러는 메타(rule_id/anchor/year) 코드가 강제 덮어씀 |

회귀 테스트 9개 추가 — `145 passed` 의 일부.

---

## 4. v2 백로그 (Phase 5 + 후속)

### Phase 5 보류 (트리거 조건 충족 시 도입)
| 항목 | 트리거 조건 |
|---|---|
| **WASM Rust BigDecimal** | 정수 산식 한계 발견 (예: 분수 비율 계산 정확도 이슈) |
| **ILP 최적화** | greedy 4 lever 로 안 잡히는 다변수 폭발 발견 시 |
| **KG + GraphRAG** | 단순 RAG 의 정확도 한계 명확해질 때 |
| **Federated Learning** | 데이터량 충분(수천 사용자 피드백) 누적 시. 현재는 IndexedDB 로컬 학습으로 시작 |

### 추가 v2 후보 (구현 중 발견)

**기능**
- 연도별 세율표 (`tax_tables/2026.json`, `2027.json`...) — 시뮬 정밀도
- 원천징수영수증 PDF 파서 — verify 입력 자동화
- 분석 결과 PDF/이미지 export
- 다년도 트렌드 뷰 (IndexedDB 누적 기반 차트)
- Background job — 법령 변경 감지 + 자동 재컴파일 트리거

**룰**
- 룰 JSON 의 LLM 자동 컴파일 신뢰도 증진 (현재 화이트리스트 + confidence)
- 항목별 정밀 산식 (자녀세액공제 / 의료비 한도별 / 기부금 종류별) — 현재 `extra_*` 합산값으로 단순화
- 법령 변경 시 영향받는 룰 자동 재컴파일 + diff 표시

**보안 / 운영**
- **Admin 인증** (운영 배포 전 필수) — 토큰/세션
- Rate limit (특히 LLM/embedding 엔드포인트)
- 법령 API 호출 동시성 제한
- `legal_api.list_changes_since` 실 응답 검증 (현재 ⚠️ assumed)

**테스트**
- E2E 시나리오 (FastAPI TestClient)
- LLM 응답 stub library 표준화
- 골든셋 확장 (국세청 모의계산기로 케이스 5개 추가)

**UI**
- 다크모드 (v2 명시 보류)
- 분석 결과 사이드 ToC (긴 리포트 navigation)
- Admin 페이지 합본 layout (현재 3개 분리)
- 한국어 폰트 최적화 (Pretendard 직접 호스팅)

---

## 5. 안 할 것 (명시)

- 서버에 사용자 PDF/입력 영속화 (프라이버시 default)
- 출처 없는 법령 인용 (LLM hallucination 차단)
- "회사 신고가 X% 틀렸다" 같은 단정 표현 (오해 소지 → "차이 발생, 확인 필요" 톤)
- "Causal Reasoning" / "Federated Learning" 같은 학술 용어 마케팅 — 실제 구현은 단순 결정론/로컬 학습. 이름과 기술을 일치시킴 ("ripple-effect simulator" 로 명명).
- 룰 evaluator 에 `eval()` 사용 (Pydantic discriminated union 으로 안전성 확보)

---

## 6. 핵심 데이터/스키마 위치

- 룰: `server/app/data/rules/{year}.json` ([rule_schema.py](./server/app/schemas/rule_schema.py))
- 룰 드래프트: `server/app/data/rules/drafts/{year}/{rule_id}.json`
- 세율표: `server/app/data/tax_tables/{year}.json`
- 법령 캐시: `server/app/data/legal_cache/{law_id}/{date}.json` (gitignored)
- RAG 인덱스: `server/app/data/rag_index/{law_id}/{date}.json` (gitignored)
- 클라 영속: 브라우저 IndexedDB `susemi.analyses` store

---

## 7. 다음 결정 필요한 사항

추가 작업 시 사용자에게 확인 필요한 항목:

- [ ] Admin 인증 방식 — 토큰? 세션? OAuth (Google)?
- [ ] PDF export 디자인 — A4 인쇄용? 이미지?
- [ ] 다국어 — 일단 한국어 only 유지 vs 영문 병기
- [ ] 라이선스 — MIT? Proprietary? 비공개?
