# susemi 로드맵 (Plan)

> 본 문서는 작업 우선순위와 결정사항을 담는 **워킹 문서**. 합의/완료된 항목만 CLAUDE.md로 승격.

---

## 0. 비전 한 줄

**2025년 귀속** 연말정산을 "왜 이 금액?"까지 **법령 API 기반 조항 trace**로 설명하고, 회사 신고 결과를 **자체 산식으로 cross-check** 하는 서비스. UI는 노랑 브랜드 + 딥슬레이트 신뢰 톤으로 재설계.

---

## 1. 현재 상태 진단 (요약)

- 룰 3개 하드코딩: 카드 25% / 의료비 3% / 월세 요건. 법령 조항 출처 없음.
- 환급액 자체 산식 0줄. LLM이 룰 결과 보고 "글만" 씀.
- LLM 프롬프트가 "5줄 이상 사례까지 써라" → hallucination 트리거.
- 영속화 없음. 위저드 끝나면 휘발.
- UI: 베이지+노랑 단일 톤, 이모지 과다, 위계 없음, 컴포넌트 불일치(`input-box` 미정의 클래스 등).

---

## 2. 단계별 로드맵

### Phase 1 — UI 리디자인 (선행, 시각 임팩트 큼)
*독립 작업. 백엔드 작업과 병렬 가능.*

목표: 신뢰감 있는 핀테크 톤. 노랑은 브랜드 accent로 유지, 메인 위계는 딥네이비/슬레이트로.

→ 자세한 내용 §3.

### Phase 2 — 산식 & 데이터 기반 (Tier 0)
*백엔드 핵심. 다른 모든 차별화의 전제. 기준 연도 **2025**.*

- **2-1. 환급액 자체 산식 구현** — 소득공제 → 과세표준 → 산출세액(누진세율) → 세액공제 → 결정세액 → 기납부세액 비교 → 환급/추징.
  - `server/app/services/tax_calculator.py` 신설
  - 정수(원 단위) 기반. 부동소수점 회피.
  - 누진세율표/근로소득공제표 등 상수는 `server/app/data/tax_tables/2025.json`에 분리
  - 골든셋 테스트 (`server/tests/test_tax_calculator.py`) 동시 작성 — 국세청 모의계산기 결과와 대조
- **2-2. 룰을 JSON으로 외부화 (법령 API 연동)**
  - `server/app/data/rules/2025.json` (조항/한도/공제율을 데이터로)
  - **법령 본문은 국가법령정보센터 OPEN API에서 fetch** (§4-4 참조)
  - `rules_engine.py`는 데이터 로더 + 평가기로 단순화
  - 각 룰에 `legal_anchor` + `legal_text_hash` 필드 — 법령 변경 감지용
- **2-3. 결과 영속화 (클라이언트)**
  - IndexedDB 래퍼 (`client/app/lib/storage.ts`)
  - 분석 결과 + 입력값 자동 저장, 다년도 누적용 base
  - 서버 영속은 도입하지 않음 (프라이버시 default)
- **2-4. 법령 API 클라이언트** — §4-4 별도 상세. Phase 2-2/3-2의 전제.

### Phase 3 — 진짜 차별화 (Tier 1)
*Phase 2 완료 후.*

- **3-1. Provenance trace** — 모든 룰 결과 + LLM 답변에 `legal_anchor` 강제, UI에서 anchor 클릭 시 트리뷰 expand.
  - 응답 스키마 `evidence` 구조화: `{ rule_id, statute_ref, computed_value, formula }`
  - 프롬프트에 "각 highlight 끝 `[rule_id]` 표시 강제"
  - LLM 출력 검증기: anchor 없는 detail은 reject 후 재생성
- **3-2. LLM 룰 컴파일 (법령 API → rule JSON)**
  - 파이프라인: **법령 API fetch (§4-4) → 본문 추출 → LLM compile → 룰 JSON + 신뢰도 스코어**
  - human-in-the-loop 검수 큐 (간단한 admin 페이지)
  - 컴파일된 룰은 골든셋 통과 + 검수자 approve 전엔 production으로 안 감
  - 법령 API 응답의 `시행일자` 변경 감지 시 해당 룰 자동 재컴파일 트리거 (diff 표시)
- **3-3. 검증 레이어 (회사 신고 cross-check)**
  - 입력: 원천징수영수증 PDF 또는 수기 입력
  - 자체 산식 결과 vs 회사 신고 → diff + 어느 단계에서 어긋났는지 리포트
  - "회사 신고에 X% 확률로 오류" 같은 강한 표현은 보류 (오해 소지)

### Phase 4 — 확장 (Tier 2)
*도입 시점은 Phase 3 안정화 후 결정.*

- **4-1. 다년도 시뮬레이션** — IndexedDB 누적 데이터 기반 트렌드 + What-if 5년치
- **4-2. 단순 RAG** — 법령/유권해석 청크 임베딩 + Top-K 검색. KG는 v2로 후순위.
- **4-3. What-if greedy 추천** — 변경 가능 변수 ranking. ILP는 폭발 발견 시에만.
- **4-4. 의존성 그래프** ("Causal" 대신 "ripple-effect simulator"로 명명) — 룰 간 의존 추적, 변경 시 재계산 후보 표시.

### Phase 5 — 보류 (Tier 3)
*가성비 안 맞음. 트리거 조건 만족 시에만.*

- WASM Rust BigDecimal — `decimal.js`/정수 산식이 부족할 때만
- 클라이언트 사이드 학습 — 데이터량 충분(수천 피드백) 쌓이면 검토
- KG + GraphRAG — 단순 RAG로 한계 명확해질 때
- ILP 최적화 — greedy로 안 잡히는 다변수 폭발 발생할 때

---

## 3. UI 리디자인 상세

### 3-1. 컬러 시스템

**브랜드/페르소나 keep**: 수세미 노랑은 정체성. 단, 면적/비중을 줄이고 **CTA·highlight·강조**에만.

| Role | Hex | Tailwind | 용도 |
|---|---|---|---|
| **Brand Yellow** | `#FACC15` | `yellow-400` | CTA 버튼, key 숫자 highlight |
| **Brand Yellow Soft** | `#FEF9C3` | `yellow-100` | tip 박스 배경, mascot 아우라 |
| **Trust Navy** | `#0F172A` | `slate-900` | 본문 텍스트, primary 헤딩, 보조 CTA |
| **Trust Navy Soft** | `#1E293B` | `slate-800` | 헤더 dark band (선택) |
| **Surface** | `#FFFFFF` / `#F8FAFC` | `white` / `slate-50` | 카드 / 페이지 배경 |
| **Border** | `#E2E8F0` | `slate-200` | 카드/입력 테두리 |
| **Text Sub** | `#475569` | `slate-600` | 부연 |
| **Text Caption** | `#94A3B8` | `slate-400` | 메타/플레이스홀더 |
| **Success** | `#10B981` | `emerald-500` | 기준 충족 뱃지 |
| **Warning** | `#F59E0B` | `amber-500` | 누락/주의 |
| **Error** | `#EF4444` | `red-500` | 미충족/오류 |

원칙: **노랑은 점·선·1차 CTA**, **네이비는 면·문장·구조**, **흰색이 메인 배경**. 베이지 톤(`#FFFCF0`, `#FFFDF5` 등) 전면 제거.

### 3-2. 타이포 위계

```
Display  text-3xl  / font-bold     — 페이지 메인 헤딩 (28~32px)
H1       text-xl   / font-semibold — 섹션 제목       (20px)
H2       text-base / font-semibold — 카드 제목       (16px)
Body     text-sm                   — 본문            (14px)
Caption  text-xs   / text-slate-500 — 메타·보조       (12px)
Number   tabular-nums             — 금액·숫자 강제 (모노)
```

기존 곳곳의 14~15px 통일 → 위 위계로. 한글 가독성 위해 `leading-relaxed` 유지.

### 3-3. 컴포넌트 변경 매트릭스

| 컴포넌트 | Before | After |
|---|---|---|
| `Button` (primary) | 노랑 배경 + 노랑 그림자 | **slate-900 배경 + 흰 글자** (primary) / 노랑은 `cta`(분석 시작 류) variant 신설 |
| `Button` (variant) | primary/ghost/outline | + `cta`(노랑) 추가, ghost는 hover 톤 슬레이트로 |
| `Input` | 노랑 포커스링 (`#FFE37A`) | slate-900 1px ring, 라벨은 위에 별도 |
| `Card` | 베이지 위 베이지 | white + slate-200 border, shadow는 hover에만 |
| `UploadArea` | 파랑 점선 (`#AAC4F5`) | slate-300 점선, 호버 시 yellow-400 |
| `Spinner` | 노랑 단색 회전 | slate-200 트랙 + slate-900 progress + 작게 |
| `ProgressHeader` | 노랑 progress bar 위 베이지 | white bar + slate-900 progress, 단계명 좌측, % 우측. 베이지 배경 제거 |
| `ReportLayout` | 베이지 카드 | white 카드 + slate-200, 섹션 헤딩에 인덱스 번호(01, 02), key 숫자만 노랑 highlight |
| Tip 박스 | 노랑 일색 | yellow-50 + yellow-300 border + 라인 아이콘(전구) |
| 마스코트 | Intro 96px 메인 | 헤더 24~32px 로고 자리만, IntroStep은 subtle 일러스트로 |

### 3-4. 레이아웃

- **데스크탑**: 현재 45/55 분할 유지하되 **borderline 강화 + 우측 리포트 배경 차이로 zone 분리** (좌: white, 우: slate-50)
- **모바일**: 위저드 진행 중엔 리포트 영역 숨김 → 분석 완료 후 리포트 단독 페이지로 fade-in (현재 위/아래 두 번 스크롤하는 구조 폐기)
- **상단 글로벌 헤더 신설**: `app/components/AppHeader.tsx` — 좌측 수세미 작은 로고 + 우측 진행률 (현 ProgressHeader 흡수)

### 3-5. 이모지 정책

- **본문/제목 이모지 전면 제거** (💰 👨‍👩‍👧 🏠 🤓 🥲 ✨ 💡 🎓 🔎 📌 →)
- 대체: Lucide 아이콘(`lucide-react`) — 라인 스타일, 16~20px, slate-700
- 예외: TIP 박스에 작은 전구 아이콘 1개만 허용

### 3-6. 작업 순서

토큰부터 만들고 컴포넌트 → 단계별 위저드 → 리포트 → 페이지 흐름 순. 시각 회귀 막기 위해 한 단계씩.

```
1. tailwind.config.ts 토큰 갱신 + globals.css 정리 (input-box 미정의 클래스 정리 포함)
2. components/ui/* 5개 갱신 (Button/Input/Card/Spinner/UploadArea)
3. AppHeader 신설 + ProgressHeader 흡수/철거
4. IntroStep → IncomeStep → PdfStep → ManualStep → ResultStep 순차
5. ReportLayout (number anchor 노랑 highlight, 카드 슬레이트화)
6. wizard/page.tsx 레이아웃 보정 (모바일 분기 변경 포함)
7. lucide-react 의존성 추가 + 이모지 일괄 치환
8. 다크모드는 v2로 보류 (지금 추가하면 작업량 2배)
```

`lucide-react` 추가 시 `package.json` dependency 1줄, 다른 의존성 영향 없음.

---

## 4. 백엔드 작업 상세 (Tier 0~1만)

### 4-1. tax_calculator.py 스켈레톤

```python
# 정수(원 단위) 기반. 부동소수점 회피.
def calculate_refund(
    gross_salary: int,            # 총급여
    deductions: dict[str, int],   # 소득공제 항목별
    tax_credits: dict[str, int],  # 세액공제 항목별
    prepaid_tax: int,             # 기납부세액 (회사가 원천징수한 것)
) -> RefundResult:
    earned_income_deduction = ...     # 근로소득공제 (구간별)
    income_after_deduction = ...      # 근로소득금액
    taxable_income = ...              # 과세표준 (인적공제 등 차감)
    calculated_tax = apply_progressive_rate(taxable_income)  # 누진세율 (6/15/24/35/38/40/42/45)
    determined_tax = calculated_tax - sum(tax_credits.values())
    return RefundResult(
        determined_tax=determined_tax,
        prepaid_tax=prepaid_tax,
        refund_or_owed=prepaid_tax - determined_tax,
        steps=[...],  # provenance용 단계별 trail
    )
```

골든셋: 국세청 모의계산기 입력 5~10케이스를 `tests/golden/`에 fixture로 두고 `pytest`로 동치성 검사.

### 4-2. rules JSON 스키마 안

```json
{
  "rule_id": "card_25_threshold",
  "title": "신용카드 등 사용액 공제 최저사용액",
  "year": 2025,
  "legal_anchor": "조세특례제한법 §126의2 ①",
  "legal_text_hash": "sha256:...",
  "source_api_id": "법령 API에서의 조항 식별자",
  "trigger": { "type": "ratio_of_field", "field": "total_salary", "ratio": 0.25 },
  "evaluator": "card_total_usage >= threshold",
  "outputs": ["card_threshold", "card_total_usage", "card_meets_threshold"],
  "human_reviewed": true,
  "confidence": 1.0,
  "compiled_at": "2026-05-05T00:00:00Z",
  "compiled_by": "llm:gpt-4o-mini" 
}
```

`rules_engine.py`는 이 데이터를 로드해서 평가만 수행. 결과에 `legal_anchor` 동봉.

### 4-3. Provenance 응답 스키마

```python
class Evidence(BaseModel):
    rule_id: str
    legal_anchor: str          # "소득세법 §52 ②"
    formula: str | None        # "min(card_usage - threshold, 한도)"
    computed: dict[str, Any]   # {"threshold": 10000000, "usage": 12000000}
```

`Section.evidence` 타입을 `Evidence`로 강제. LLM이 anchor 없이 답하면 reject 후 재시도.

### 4-4. 법령 API 클라이언트

**전제**: 사용자가 법령 데이터를 **국가법령정보센터 OPEN API**(`open.law.go.kr`) 또는 동등한 한국 법령 API에서 받기로 결정. 룰 데이터의 single source of truth.

```
[법령 API]
   │  (1) fetch
   ▼
server/app/services/legal_api.py
   │  - 조회 / 캐시 / rate-limit 핸들링
   │  - 응답을 표준 형태로 정규화 (조/항/호 단위 청크)
   ▼
server/app/data/legal_cache/{law_id}/{date}.json   ← 캐시 + 버전 스냅샷
   │
   ▼
[Phase 3-2 LLM 룰 컴파일러]  →  rules/2025.json
```

설계 포인트:
- **인증/키 관리**: `OPEN_LAW_API_KEY` env로 분리. `.env.example`에 키만 등록.
- **캐시 layer 필수**: 법령은 자주 안 바뀌고 API rate limit이 빠듯함. ETag/시행일자/lastmod 기준 캐시 hit/miss 판단. 디스크 캐시(`legal_cache/`)부터 시작 → 트래픽 늘면 Redis 검토.
- **호출 단위**: 법령 ID + 시행일자(또는 버전)로 idempotent. 시행일자 바뀌면 자동 새 스냅샷.
- **변경 감지**: 캐시된 본문 hash와 신규 응답 hash 비교 → 다르면 해당 룰 `is_stale=true` 마크 + 검수 큐로 보냄.
- **에러 처리**: API 다운/5xx → 캐시 fallback 허용, 단 응답에 `data_source: "cache_fallback"` 표시.
- **테스트**: 실제 API 의존 없이 검증되도록 fixture 응답(`tests/fixtures/legal_api/*.json`) 기반 unit test.

지원할 최소 기능:
1. `get_law(law_id, effective_date=None)` — 법령 본문 조회
2. `get_article(law_id, article_no, effective_date=None)` — 조 단위 조회
3. `list_changes_since(date)` — 특정 시점 이후 개정된 법령 목록 (있는 경우)
4. `to_chunks(law_text)` — 조/항/호 단위로 분리, 각 청크에 anchor ID 부여 (Phase 3 RAG에도 재사용)

**주의**: 일부 한국 법령 API는 XML/JSON 혼합 + 한자 병기 + 별표/별지 처리 까다로움. 정규화 로직에 시간 들 수 있음 — Phase 2-4 작업량 보수적으로 잡을 것.

---

## 5. 결정사항 (확정)

| 항목 | 결정 | 근거 |
|---|---|---|
| 기준 연도 | **2025** | 사용자 지정. 2025년 귀속분 → 2026 초 정산 |
| 법령 데이터 소스 | **국가법령정보센터 OPEN API** (또는 동등) | 사용자 지정. 단일 출처 + 변경 감지 가능 |
| UI primary CTA | **slate-900 검정** (`#0F172A`) | 노랑 highlight 대비 가장 강함, 한국 핀테크 표준 |
| 노랑 사용 영역 | CTA primary 1곳 + 숫자 highlight + tip 박스만 | 브랜드 보존 + 신뢰감 확보 균형 |
| 마스코트 노출 | 헤더 로고(28px) + 결과 페이지 작은 일러스트 | 브랜드 흔적 유지, 위저드 본문엔 부재 |
| 골든셋 출처 | 국세청 모의계산기 + 공식 예제 PDF 양쪽 | 다양성 확보 |
| 아이콘 라이브러리 | `lucide-react` | 트리셰이크, 라인 톤 통일, 가벼움 |
| 다크모드 | v2로 보류 | v1 작업량 2배 됨, 출시 후 추가 |
| 서버 사용자 데이터 영속화 | **하지 않음** | 프라이버시 default off |
| 법령 캐시 저장소 | 디스크(`legal_cache/`)부터 | 트래픽 늘면 Redis 검토 |

---

## 6. 작업 단위 추정 (러프)

| 작업 | 추정 | 의존 |
|---|---|---|
| Phase 1 UI 리디자인 | 0.5~1일 | - |
| Phase 2-1 산식 + 골든셋 (2025) | 1~2일 | - |
| Phase 2-4 법령 API 클라이언트 + 캐시 | 1~2일 | - |
| Phase 2-2 룰 데이터화 (3개 룰 → 법령 API anchor 부여) | 0.5~1일 | 2-4 |
| Phase 2-3 IndexedDB 영속 | 0.5일 | - |
| Phase 3-1 Provenance | 1일 | 2-1, 2-2 |
| Phase 3-2 룰 컴파일 + 검수 큐 | 2~3일 | 2-2, 2-4, 3-1 |
| Phase 3-3 검증 레이어 | 2~3일 | 2-1, 2-2 |

UI(Phase 1)는 백엔드와 병렬 가능. 법령 API 클라이언트(2-4)는 룰 데이터화·룰 컴파일의 공통 전제라 Phase 2 안에서 가장 먼저.

---

## 7. 안 할 것 (명시)

- 서버에 사용자 PDF/입력 영속화 (프라이버시 default)
- 출처 없는 법령 인용 (LLM hallucination 차단)
- "회사 신고가 X% 틀렸다" 같은 단정 표현 (오해 소지 → "차이 발생, 확인 필요" 톤)
- "Causal Reasoning" / "Federated Learning" 같은 학술 용어 마케팅 — 실제 구현은 단순 결정론/로컬 학습. 이름과 기술을 일치시킴.
- 동시에 여러 Phase 진행 (UI Phase 1만 백엔드와 병렬, 나머지는 순차)
