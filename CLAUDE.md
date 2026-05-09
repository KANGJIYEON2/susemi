# susemi (수세미)

> AI Tax Explainability Agent — 근로소득자 연말정산 결과를 단순히 보여주는 게 아니라 **"왜 이 금액이 나왔는지"** 를 설명하는 도구.

---

## 한 줄 아키텍처

```
[Next.js 위저드 4단계]  →  POST /api/v1/*  →  [FastAPI]
   Income → PDF → Manual → Result                 ├─ pdf_parser  (PyMuPDF + LLM JSON 변환)
                                                  ├─ rules_engine (한도/요건 충족 여부 계산)
                                                  └─ llm_client   (rules_engine 결과를 근거로 'Why' 설명)
```

**핵심 데이터 흐름:** 사용자 입력 + PDF 파싱 결과 → `RuleContext` 생성 → 그 컨텍스트를 프롬프트에 박아 LLM이 섹션별 해설 생성 → JSON 파싱해 응답.

DB/영속화 없음. 전부 in-memory + 클라이언트 state. 위저드 끝나면 데이터 휘발.

---

## 디렉터리 구조

```
susemi/
├── client/                          # Next.js 16 + React 19 + Tailwind v4
│   └── app/
│       ├── page.tsx                 # /wizard 로 redirect
│       ├── wizard/
│       │   ├── page.tsx             # 위저드 컨트롤러 (state 보관, 단계 전환)
│       │   ├── IntroStep/           # step 0
│       │   ├── IncomeStep/          # step 1: 소득 + 인적공제 + 조건 설문
│       │   ├── PdfStep/             # step 2: PDF 업로드 → /pdf-parse
│       │   ├── ManualStep/          # step 3: 간소화에 안 잡히는 항목 수기 입력
│       │   └── ResultStep/          # step 4: 분석 결과
│       ├── components/
│       │   ├── ui/                  # Button, Card, Input, Spinner, UploadArea
│       │   ├── ProgressHeader.tsx
│       │   └── report/ReportLayout/ # 우측 리포트 패널 렌더러
│       └── lib/
│           ├── api.ts               # parsePdf / analyzeTax / postManualInput fetch 래퍼
│           └── types.ts             # 백엔드 스키마 미러
│
└── server/                          # FastAPI 0.121 + Uvicorn
    ├── main.py                      # CORS + 라우터 등록
    └── app/
        ├── routers/
        │   ├── user_input.py        # POST /api/v1/user-input  (validation only)
        │   ├── pdf_parse.py         # POST /api/v1/pdf-parse   (multipart upload)
        │   ├── manual_input.py      # POST /api/v1/manual-input (validation only)
        │   └── analyze.py           # POST /api/v1/analyze     (rules → LLM)
        ├── schemas/                 # Pydantic 모델 (요청/응답)
        │   ├── user_input_schema.py # Income / Dependents / Conditions
        │   ├── pdf_schema.py        # ParsedPdfData / PdfParseResponse
        │   ├── manual_input_schema.py
        │   └── analysis_schema.py   # AnalyzeRequest / Summary / Section / AnalyzeResponse
        └── services/
            ├── pdf_parser.py        # PyMuPDF로 텍스트 → LLM(gpt-4.1-mini)으로 JSON 추출
            ├── rules_engine.py      # 룰 평가 → RuleContext 빌드
            └── llm_client.py        # gpt-4o-mini로 Why 분석 JSON 생성
```

---

## 현재 구현된 룰 (rules_engine.py)

**3개**. 모두 `RuleContext` dataclass 필드로 평가 결과만 표현.

| 룰 | 입력 | 출력 |
|---|---|---|
| 카드 25% 기준 | `total_salary`, `credit_card + debit_card + cash_receipt` | `card_threshold_25`, `card_total_usage`, `card_meets_threshold` |
| 의료비 3% 기준 | `total_salary`, `medical_expense + 수기 의료비 합계` | `medical_threshold_3`, `medical_total`, `medical_meets_threshold` |
| 월세 요건 | `householder ∧ no_house ∧ lease_contract` | `rent_conditions_met` |

**이 룰들은 하드코딩.** 법령 조항 ID, 한도, 공제율은 코드 안에 흩어져 있고 외부 데이터로 분리되어 있지 않음.

---

## LLM 호출 패턴 (llm_client.py)

- 모델: `gpt-4o-mini`, `temperature=0.3`, `max_tokens=2000`
- 시스템 프롬프트: 계산 금지, 룰 엔진 결과만 사용, JSON만 반환
- 유저 프롬프트: 사용자 데이터 + 룰 엔진 결과를 한국어 라벨로 박아 넣고, 5개 고정 섹션(`card / medical / donation / rent_loan / other`)을 채우라고 지시
- 응답 파싱: `json.loads` 1차 → 실패 시 `extract_json` 정규식 정리 후 재시도. 두 번 다 실패하면 `ValueError`.

**주의해야 할 점:**
- 프롬프트가 "데이터 없어도 사례 기반으로 5줄 이상 써라"고 강제 → **hallucination 발생하기 쉬운 구조**. 출처 anchor 없음.
- 섹션이 5개로 고정되어 있어서 새 공제 항목을 추가할 때 프롬프트와 응답 스키마를 같이 수정해야 함.
- JSON 파싱 fallback의 `except:` (bare)는 향후 좁히는 게 좋음.

---

## PDF 파서 (pdf_parser.py)

- `pymupdf.open(stream=..., filetype="pdf")` → `page.get_text("text")` 페이지별 텍스트 추출 → 전체를 `\n\n`로 join
- 15,000자 컷 (LLM 토큰 보호) — 길이 큰 PDF는 뒷부분 손실 가능
- 텍스트를 `gpt-4.1-mini`에 넣고 `ParsedPdfData` 스키마 키에 맞춰 JSON 반환받음
- LLM JSON 파싱 실패 시 모든 필드 0인 기본값 + `missing_fields=["llm_parse_error"]` 반환 (예외 안 던짐)

OCR 없음. 이미지 기반 PDF는 텍스트가 안 뽑힘 (현재 한계).

---

## API 엔드포인트 요약

| Method | Path | 역할 | 영속화 |
|---|---|---|---|
| GET | `/` | 헬스체크 | - |
| POST | `/api/v1/user-input` | 소득/인적공제/조건 validation | 없음 (사실상 echo) |
| POST | `/api/v1/pdf-parse` | PDF 업로드 → 구조화 JSON + missing_fields | 없음 |
| POST | `/api/v1/manual-input` | 수기 입력 validation | 없음 |
| POST | `/api/v1/analyze` | 룰 엔진 + LLM Why 분석 | 없음 |

`user-input`/`manual-input`은 현재 사실상 noop validator. 실제 분석은 클라이언트가 모은 state를 한 번에 `/analyze`로 보내서 처리.

---

## 기술 스택

### Client
- Next.js **16.0.3** (App Router), React **19.2**
- Tailwind CSS **v4** (`@tailwindcss/postcss`) + `tailwind.config.ts`
- TypeScript 5 strict, ESLint 9 (`eslint-config-next`)
- 경로 alias: `@/*` → `./*`
- API base: `process.env.NEXT_PUBLIC_API_BASE_URL` (없으면 `http://localhost:8000/api/v1`)

### Server
- Python venv (`server/venv/`)
- FastAPI **0.121.3** + Uvicorn, Pydantic v2
- `openai` 2.x (`AsyncOpenAI`), `PyMuPDF` (PDF), `python-multipart`, `python-dotenv`
- 환경변수: `OPENAI_API_KEY` (필수)

### CI/CD
- `.github/workflows/deploy.yml` 존재. 배포 환경은 EC2 + Vercel (CORS allow-list로 추정).

---

## 개발 명령어

### Client
```bash
cd client
npm run dev      # http://localhost:3000 → /wizard 자동 redirect
npm run build
npm run lint
```

### Server
```bash
cd server
source venv/bin/activate
uvicorn main:app --reload    # http://localhost:8000
# 환경변수: .env 에 OPENAI_API_KEY=...
```

---

## 작업할 때 의식해야 할 것

- **세무 계산은 틀리면 안 됨.** 정확도가 UX보다 우선. 현재는 환급액 자체 산식이 코드에 없고, LLM이 룰 엔진 결과만 보고 "설명"하는 구조. 산식을 직접 구현하는 작업이 들어오면 부동소수점 누적 오차에 주의 (`Decimal` 또는 정수 원 단위).
- **출처 없는 법령 인용 금지.** LLM이 "○○법 △△조에 따라"라고 자신 있게 쓰지만 출처가 코드에 없음. Provenance 추가 작업이 들어오면 `RuleContext`에 룰 ID + 법령 조항 ID를 같이 싣고 LLM이 anchor를 달도록 프롬프트 수정.
- **사용자 PDF는 민감정보.** 서버 영속화 default off. 추가시 명시적 동의 + 암호화 흐름부터 설계.
- **새 룰을 추가할 때**: `rules_engine.py`의 `RuleContext` 필드 추가 → `build_rule_context` 평가 로직 추가 → `llm_client.build_prompt`에 새 라벨 추가 → 응답 섹션 추가 (4단 동기화 필요). 이 동기화 비용이 크기 때문에 룰 데이터 외부화가 향후 큰 리팩터 포인트.
- **프롬프트의 "5줄 이상 써라"는 hallucination 트리거.** 데이터 없을 때 LLM이 사례를 만들어내기 쉬움. 정확성 우선이라면 이 강제 길이를 풀고 anchor 기반으로 쓰게 하는 것이 안전.
- **Vision 항목**(법령→룰 자동 컴파일, ILP 최적화, KG+RAG, 다년도 시뮬레이션, 검증 레이어, WASM 정밀 계산 등)은 별도 대화에서 논의 중. CLAUDE.md에 옮기지 말고 합의된 것만 옮길 것.
