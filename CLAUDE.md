# susemi (수세미)

> **연말정산 Why 분석 + 자체 산식 + 법령 trace + 회사 신고 cross-check.**
> 사용자용 README: [README.md](./README.md) · 단계별 작업 로그/결정: [PLAN.md](./PLAN.md)

```
Status: Phase 1~4 완료 · 237 tests passing · 보안 패스 통과
2025년 귀속 기준
```

---

## 한 줄 아키텍처

```
[Next.js 16 위저드/Admin]  →  POST /api/v1/*  →  [FastAPI · Pydantic v2]
   /wizard 4단계                                      ├─ analyze       (rules + LLM Why)
   /admin/rules · /rag · /ripple                      ├─ verify        (자체 산식 vs 회사 신고)
   IndexedDB (분석 영속)                              ├─ simulate      (5년 What-if)
                                                      ├─ recommend     (greedy levers)
                                                      ├─ ripple        (의존 그래프 BFS)
                                                      ├─ admin/rules   (LLM 룰 컴파일 + 검수)
                                                      └─ rag           (법령 임베딩 검색)
                                                       │
                                                       ├→ tax_calculator (정수 한국 소득세 풀 산식)
                                                       ├→ rules_engine   (JSON 룰, eval() 0줄)
                                                       ├→ legal_api      (open.law.go.kr + 디스크 캐시)
                                                       ├→ rule_compiler  (법령 → LLM → Rule JSON)
                                                       ├→ rag            (text-embedding-3-small + cosine)
                                                       └→ dependencies   (룰·step DAG 정적 분석)
```

---

## 디렉터리 구조

```
susemi/
├── client/                              # Next.js 16 + React 19 + Tailwind v4
│   ├── package.json (lucide-react 포함)
│   └── app/
│       ├── components/
│       │   ├── AppHeader.tsx           # 글자 로고 (수세미 scrubbing motif SVG)
│       │   ├── ui/                     # Button/Input/Card/Spinner/UploadArea
│       │   └── report/ReportLayout/    # Why 리포트 + provenance 트리 + [rule_id] anchor
│       ├── wizard/                     # 4단계 위저드 + 결과 페이지
│       │   ├── page.tsx                # state 컨트롤러 + 모바일/데스크 분기
│       │   ├── IntroStep/              # step 0 (이어서 보기 카드 포함)
│       │   ├── IncomeStep/             # step 1
│       │   ├── PdfStep/                # step 2
│       │   ├── ManualStep/             # step 3
│       │   └── ResultStep/             # step 4
│       │       ├── index.tsx
│       │       ├── VerifySection.tsx   # 회사 신고 cross-check
│       │       ├── SimulateSection.tsx # 5년 시뮬
│       │       └── RecommendSection.tsx# What-if 추천
│       ├── admin/                      # 검수자 UI
│       │   ├── rules/                  # LLM 컴파일 + 검수 큐
│       │   ├── rag/                    # 법령 인덱싱·검색
│       │   └── ripple/                 # 의존 그래프 뷰어
│       ├── lib/
│       │   ├── api.ts                  # 백엔드 fetch 래퍼 (verify/simulate/recommend/admin/rag/ripple)
│       │   ├── storage.ts              # IndexedDB CRUD + SSR 안전
│       │   └── types.ts                # 백엔드 스키마 미러
│       └── globals.css                 # @import "tailwindcss" + @theme inline 토큰
└── server/                              # FastAPI 0.121 + Pydantic v2
    ├── main.py                          # CORS + 라우터 등록
    ├── pytest.ini                       # asyncio_mode=auto, pythonpath=.
    └── app/
        ├── routers/
        │   ├── analyze.py              # POST /analyze (rules + LLM Why + provenance 부착)
        │   ├── verify.py               # POST /verify
        │   ├── simulate.py             # POST /simulate
        │   ├── recommend.py            # POST /recommend
        │   ├── dependencies.py         # GET /ripple/{field}, /ripple/graph, /ripple/fields
        │   ├── admin_rules.py          # POST compile, GET drafts, POST approve/reject
        │   ├── rag.py                  # POST /rag/index, /rag/search, GET /rag/stats
        │   ├── pdf_parse.py            # POST /pdf-parse (Hybrid: PyMuPDF + LLM)
        │   ├── manual_input.py         # POST /manual-input (validation only)
        │   └── user_input.py           # POST /user-input (validation only)
        ├── schemas/                    # Pydantic 모델
        │   ├── analysis_schema.py      # AnalyzeRequest/Response, Section.provenance
        │   ├── tax_calculator_schema.py# CalcInputs / CalcStep / CalcResult
        │   ├── rule_schema.py          # Rule + ValueExpr/Evaluator discriminated union + RuleEvaluation
        │   ├── rule_draft_schema.py    # RuleDraft + Compile/Decide req·res
        │   ├── verification_schema.py  # CompanyFiling / StepDiff / VerificationReport
        │   ├── simulate_schema.py      # YearOverride / SimulateRequest/Response
        │   ├── recommend_schema.py     # Lever / Recommendation / Recommend* req·res
        │   ├── dependencies_schema.py  # RippleNode / GraphNode / GraphEdge
        │   ├── rag_schema.py           # IndexedChunk / Search* / Index* req·res
        │   ├── legal_schema.py         # Law / LawArticle / LawChunk
        │   ├── pdf_schema.py
        │   ├── manual_input_schema.py
        │   └── user_input_schema.py
        ├── services/                   # 도메인 로직
        │   ├── tax_calculator.py       # 정수 산식 + CalcStep trail
        │   ├── rules_engine.py         # JSON 로드 + 평가 + EVAL_CONTEXT_FIELDS 화이트리스트
        │   ├── rule_compiler.py        # LLM 컴파일 + 메타 강제 + 검증
        │   ├── rule_drafts_store.py    # 디스크 CRUD + UnsafeIdError 차단
        │   ├── verification.py         # 단계별 diff + 단정 표현 금지 톤
        │   ├── simulate.py             # YearOverride carry-forward
        │   ├── recommend.py            # 4 lever greedy
        │   ├── dependencies.py         # 정적 DAG + BFS
        │   ├── rag.py                  # 임베딩 + cosine + 빈 인덱스 skip 최적화
        │   ├── legal_api.py            # open.law.go.kr 클라이언트
        │   ├── llm_client.py           # /analyze 용 Why 생성 (lazy init)
        │   └── pdf_parser.py           # PyMuPDF + LLM Hybrid (lazy init)
        ├── data/
        │   ├── rules/2025.json         # 룰 정의 (3건: 카드/의료/월세)
        │   ├── rules/drafts/{year}/    # LLM 컴파일 드래프트
        │   ├── tax_tables/2025.json    # 세율·공제표
        │   ├── legal_cache/            # 법령 API 캐시 (gitignored)
        │   └── rag_index/              # RAG 임베딩 (gitignored)
        └── tests/                      # 237 케이스 (3.4초)
            ├── test_legal_api.py       (11)
            ├── test_tax_calculator.py  (27)
            ├── test_rules_engine.py    (19)
            ├── test_provenance.py      (5)
            ├── test_rule_compiler.py   (12)
            ├── test_rule_drafts_store.py (16)
            ├── test_verification.py    (8)
            ├── test_simulate.py        (9)
            ├── test_rag.py             (14)
            ├── test_recommend.py       (9)
            ├── test_dependencies.py    (14)
            └── fixtures/legal_api/, fixtures/.../
```

---

## 핵심 모듈 — 어디서 무엇이 일어나나

### `tax_calculator.py` — 한국 소득세 산식
- 흐름: 총급여 → 근로소득공제 → 인적공제 → 과세표준 → 누진세율 → 산출세액 → 세액공제 → 결정세액 → 지방소득세 → 환급/추징
- **정수(원 단위)** — 부동소수점 누적 오차 회피
- 모든 단계가 `CalcStep(name, label, legal_anchor, formula, inputs, output)` 으로 trail
- 세율표/한도/공제율은 **외부 JSON** (`data/tax_tables/2025.json`)
- 골든셋 5건 + 단위 27건. 산식 변경 시 골든셋 expected 값 재계산 필요

### `rules_engine.py` — JSON 룰 평가기
- `EVAL_CONTEXT_FIELDS` — 룰이 참조 가능한 필드 화이트리스트 + 한국어 라벨
- `build_eval_context(...)` — 사용자 입력을 flat dict 로 평탄화
- `Rule.evaluator` 는 **discriminated union** (`ThresholdEvaluator` / `AllOfFlagsEvaluator`)
- `ValueExpr` 는 `FieldRef` / `RatioOfField` / `SumOfFields` / `Constant`
- **`eval()` 사용 0줄** — 보안성 확보
- legacy `RuleContext` (dataclass) 호환 + 새 `RuleEvaluation` (Pydantic) 둘 다 반환
- 새 룰 추가: `data/rules/{year}.json` 에 1건 추가. 새 evaluator 종류 추가 시 schema + dispatcher 동기 갱신.

### `rule_compiler.py` — 법령 → Rule JSON
- 입력: 법령 본문 + 타깃 메타(rule_id/title/anchor)
- LLM 호출은 `_call_llm` 함수 또는 `llm_call` 인자 주입 (테스트는 mock)
- **메타 강제 덮어쓰기** — LLM 응답 후 코드가 `rule_id/title/year/anchor/compiled_by` 강제 세팅
- 화이트리스트 검증 — `EVAL_CONTEXT_FIELDS` 외 필드 참조 시 confidence 디스카운트 + warning
- JSON 파싱 1차 + 1회 재시도

### `rule_drafts_store.py` — 드래프트 디스크 CRUD
- 위치: `data/rules/drafts/{year}/{rule_id}.json`
- **`_validate_rule_id`** — `^[A-Za-z0-9_\-]+$` 화이트리스트, `UnsafeIdError` raise
- approve = `rules/{year}.json` 에 병합 (동일 id 교체) + `load_rules.cache_clear()` + 드래프트 삭제

### `legal_api.py` — open.law.go.kr 클라이언트
- 본문 조회: `lawService.do?OC=...&type=JSON&ID=...` (또는 MST=)
- 검색: `lawSearch.do?OC=...&query=...`
- 디스크 캐시: `legal_cache/{law_id}/{efYd}.json`
- **`validate_freshness(...)`** — 명시적 재호출, sha256 비교, `is_stale` 채움
- API 실패 + 캐시 있음 → `data_source="cache_fallback"`
- **`_safe_path_component`** — path traversal 방어
- 응답 키 매핑은 `_parse_law_response` 에 격리 (실 API 응답 다르면 여기만 수정)
- 실 OC 키 검증 완료 (소득세법 1511 청크)

### `rag.py` — 단순 RAG
- 임베딩 모델: `text-embedding-3-small` (1536 dim, 다국어)
- 저장: `rag_index/{law_id}/{efYd}.json` 단위 `IndexedLawPack`
- 검색: 메모리 풀스캔 + cosine 유사도 + top-K
- **빈 인덱스 / 필터 후 후보 0개 → 임베딩 호출 자동 skip** (비용·안정성 최적화)
- `embed_fn` 인자 주입 가능 (테스트는 deterministic 매핑)
- `_safe_component` — path traversal 방어
- 한계: 메모리 풀스캔(수백 법령까지 OK), 임베딩 dedup 미구현

### `verification.py` — 회사 신고 cross-check
- 자체 `tax_calculator.calculate(...)` 결과 vs 사용자 제공 `CompanyFiling` 단계별 비교
- severity: `match` / `minor` (<1,000원 반올림) / `major` / `missing`
- **단정 표현 금지** — 테스트로 `"오류"`, `"잘못"` 단어 차단
- `local_income_tax` 누락 시 결정세액 × 10% 자동 추정

### `simulate.py` — 5년 What-if
- baseline + `YearOverride` 리스트 (max 10년)
- **carry-forward** — `None` 필드는 직전 연도 값 자동 상속
- 모든 연도가 동일 세율표 (현재 2025 단년만). per-year 세율표는 v2.

### `recommend.py` — Greedy 5 lever
- 연금저축 600 / IRP 합산 900 / 정치자금 10만 / 고향사랑 10만 / 월세 세액공제
- 각 lever: `eligibility(inputs, request)` → `(bool, note)` + `apply(inputs, request)` → 새 CalcInputs
- 자격 미충족 = 미적격 (delta=0, 마지막 정렬)
- `cost_label` 로 사용자 부담 명시 (delta 만으로 오해 방지)

### `dependencies.py` — Ripple-Effect Simulator
- 룰 evaluator 자동 분석 → `(field → rule_ids)` 매핑
- tax_calculator step DAG 는 `TAX_STEP_DEPS` 상수에 **하드코딩** — 코드와 동기 유지 필요
- `ripple(field)` = BFS 최단경로 (사이클 없는 DAG 가정)
- 노드 3종: `field` / `rule` / `step`. `rule` 은 leaf.
- 의도적으로 "causal" 명명 회피 — 결정론적 정적 분석임을 명시

### `analyze.py` — Why 분석 라우터
- 흐름: rules_engine → LLM (Why 해설) → `_attach_provenance(sections, evaluations)` 후처리
- `SECTION_TO_RULE_IDS` 매핑 — section ID → 관련 rule_id 리스트
- LLM 응답은 변경하지 않고 새 Section 객체로 복제 (immutable 패턴)

### `llm_client.py` — Why LLM 호출
- 모델: `gpt-4o-mini` · `temperature=0.3`
- **시스템 제공 `[rule_id]` anchor 만 인용 허용** — 시스템 미제공 법령 인용 금지
- `_get_client()` lazy init — 테스트 환경에서 OPENAI_API_KEY 없어도 import 가능
- JSON 1차 파싱 + `extract_json` regex 정리 후 재시도

### `pdf_parser.py` — Hybrid PDF
- PyMuPDF 텍스트 추출 → 15,000자 컷 → LLM (`gpt-4.1-mini`) 으로 JSON 구조화
- 응답 실패 시 안전한 기본값 + `missing_fields=["llm_parse_error"]` 반환 (예외 안 던짐)
- `_get_client()` lazy init

---

## 보안 결정 (직접 PoC 로 검증 후 차단)

| 위협 | 차단 |
|---|---|
| Path traversal in `rule_drafts_store` / `rag` / `legal_api` | 화이트리스트 `^[A-Za-z0-9_\-]+$`, `UnsafeIdError`, Pydantic pattern |
| `eval()` 사용 | 룰 evaluator 는 Pydantic discriminated union |
| 시크릿 누출 | `.env*` gitignore + `.env.example` 화이트리스트 |
| LLM hallucination | 시스템 제공 `[rule_id]` 만 인용. 룰 컴파일러 메타 강제 덮어쓰기 |
| 음수/잘못된 입력 | Pydantic `ge=0` 검증 (simulate, verify, recommend) |
| RAG 빈 인덱스 OpenAI 호출 | 후보 0이면 임베딩 호출 자동 skip |

⚠️ **Admin 인증 미구현** — 운영 배포 전 토큰 가드 필수.

---

## 기술 스택

### Client
- Next.js **16.0.3** (App Router), React **19.2**
- Tailwind CSS **v4** (`@tailwindcss/postcss` + `@theme inline` in CSS)
- TypeScript 5 strict, ESLint 9
- 경로 alias: `@/*` → `./*`
- 의존성: `lucide-react` (아이콘만)
- API base: `process.env.NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000/api/v1`)

### Server
- FastAPI **0.121.3** + Uvicorn, Pydantic v2
- `httpx` 0.28 async (legal_api, rag_test)
- `openai` 2.x (chat + embeddings)
- `PyMuPDF` (PDF 추출)
- `python-multipart` (파일 업로드)
- `python-dotenv`
- 환경변수: `OPENAI_API_KEY`, `OPEN_LAW_API_KEY` (open.law.go.kr OC)
- 테스트: `pytest` 8.3 + `pytest-asyncio` 0.25 (asyncio_mode=auto)

---

## 개발 명령어

```bash
# Backend
cd server
source venv/bin/activate
uvicorn main:app --reload     # http://localhost:8000
pytest tests/ -q              # 237 passed

# Frontend
cd client
npm run dev                   # http://localhost:3000 → /wizard
npm run build
npm run lint
```

---

## 작업할 때 의식해야 할 것

### 정확성·출처
- **세무 계산은 틀리면 안 됨.** 정확도가 UX 보다 우선. 산식 변경시 `tests/golden/*.json` expected 값 재확인.
- **출처 없는 법령 인용 금지.** `RuleEvaluation.legal_anchor` 와 `CalcStep.legal_anchor` 가 truth source. LLM 은 `[rule_id]` 마커로 참조만 가능.
- **민감 데이터 서버 영속화 안 함** (default off). 추가시 명시적 동의 + 암호화 흐름 설계.

### 확장 시 동기화 포인트
- **새 룰 추가**: `data/rules/{year}.json` 에 정의 추가만. evaluator 화이트리스트(`EVAL_CONTEXT_FIELDS`) 외 필드 참조 시 confidence 디스카운트.
- **새 evaluator 종류 추가**: `rule_schema.py` 에 새 `Literal kind` BaseModel + `rules_engine.py` 의 `evaluate_rule` 분기 + `rule_compiler.py` 프롬프트의 `kind` 옵션 + `dependencies.py` 의 `_rule_input_fields` 분기 (**4곳 동기화 필요**).
- **새 tax_calculator 단계 추가**: `tax_calculator.calculate(...)` 에 단계 추가 + `tax_calculator_schema.CalcResult` 필드 + **`dependencies.TAX_STEP_DEPS` 와 `TAX_STEP_META` 동기 갱신** (ripple 정확성 의존).
- **새 itemized 산식 추가** (Tier 3-3): `ItemizedDeductions` 필드 + `tax_calculator._{name}_credit` helper + `tax_tables/{year}.json itemized` 섹션 + `compute_itemized` 호출.

### 라우터 작성 — 사고 방지
- **새 POST 엔드포인트에 Pydantic body + slowapi `@limiter.limit` 같이 쓸 때**:
  1. 라우터 파일에 `from __future__ import annotations` **쓰지 말 것** (어노테이션이 ForwardRef 가 되면 FastAPI body 추론 실패)
  2. 본문 파라미터에 명시적 `Body(...)` default 추가:
     ```python
     async def endpoint(request: Request, payload: MyModel = Body(...)):
     ```
  3. **회귀 테스트는 TestClient 로 라우터 통과해서 검증** — `test_body_parsing.py` 패턴 참조. 단위 테스트만 짜면 422 사고 못 잡음.
- **path 컴포넌트로 받는 user input 은 화이트리스트 통과 필수** — `rule_id`, `law_id`, `effective_date` 등.

### 인프라
- **`load_rules` 캐시**: `lru_cache` 사용 중. 룰 파일 직접 수정 시 `load_rules.cache_clear()` 필요 (rule_drafts_store.approve_draft 가 자동).
- **OpenAI 클라이언트는 lazy init** (`_get_client()`). 직접 import 시점에 API key 없어도 됨.
- **로깅**: `print()` 쓰지 말 것. `logger = logging.getLogger(__name__)` + `logger.info/exception`.
- **rate limit 추가**: `app/rate_limit.py` 의 임계값 상수 사용. 새 LLM/embedding 엔드포인트에 `@limiter.limit(LIMIT_*)` 데코레이터.

### 검증 안전망 4단
1. 단위 테스트 (서비스 함수)
2. **TestClient 통합** (라우터·미들웨어·body 파싱)
3. 유저 e2e 시뮬 (배포 직전)
4. CI 자동 (`.github/workflows/test.yml`)

→ 단위만 보면 라우터 레벨 버그 못 잡음. 새 라우터 추가 시 **TestClient 회귀 테스트 동시 추가**.

---

## 알려진 한계 (PLAN.md §4 v2 백로그 참조)

- 모든 시뮬 연도가 2025 세율표 사용 — per-year 세율표는 v2
- `legal_api.list_changes_since` 파라미터/응답 키 미검증 (⚠️ assumed)
- PDF 파서: 텍스트 PDF 만 지원, 이미지 OCR 없음
- RAG: 메모리 풀스캔 (수백 법령까지 OK), vector DB 미적용
- 항목별 정밀 산식 (Tier 3-3): 자녀세액공제 / 의료비 / 기부금 정치·일반 정도. **난임 30% / 미숙아 20% 차등은 v1, 보험료/교육비/연금저축은 v1**
- 골든셋 calibration: `tests/golden/*.json` 의 모든 source 가 `hand_calculated`. 사용자가 모의계산기로 검증해 `official_calculator_YYYY-MM-DD` 로 갱신 필요
