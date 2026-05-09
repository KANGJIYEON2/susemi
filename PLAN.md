# susemi 로드맵 (Plan)

> 본 문서는 작업 우선순위와 결정사항 워킹 문서. 상세 코드 패턴은 [CLAUDE.md](./CLAUDE.md), 사용자용 README 는 [README.md](./README.md) 참조.

```
Status: Phase 1~4 ✅ · v2-1~v2-4 ✅ · Tier 1(운영 배포) ✅ · Phase 5 보류
Tests:  206 passed · 보안 패스 통과 (path traversal 차단 + admin 토큰 + rate limit + 로깅)
```

---

## 0. 비전 한 줄

**2025년 귀속** 연말정산을 "왜 이 금액?"까지 **법령 API 기반 조항 trace**로 설명하고, 회사 신고 결과를 **자체 산식으로 cross-check** 하는 서비스. UI 는 노랑 브랜드 + 딥슬레이트 신뢰 톤. **Docker + Caddy on EC2 운영 배포 가능 상태.**

---

## 1. 진행 요약

### Phase 1~4 (코어 기능)

| Phase | 내용 | 상태 | 핵심 산출물 |
|:---:|---|:---:|---|
| 1 | UI 리디자인 | ✅ | slate-900 + yellow-400 토큰, AppHeader 글자 로고(scrubbing motif), 위저드 5단계 + 4 펼침 섹션 |
| 2-1 | 환급액 산식 + 골든셋 | ✅ | `tax_calculator.py` 정수 기반, `tax_tables/2025.json`, 골든셋 10건(원본 5 + 추가 5) + 단위 27 |
| 2-2 | 룰 JSON 외부화 | ✅ | `rules/2025.json`, `ValueExpr`/`Evaluator` discriminated union, **`eval()` 사용 0줄** |
| 2-3 | IndexedDB 클라 영속 | ✅ | `lib/storage.ts` CRUD + IntroStep "이어서 보기" 카드 |
| 2-4 | 법령 API 클라이언트 | ✅ | `legal_api.py`, 디스크 캐시, sha256 변경 감지. 실 OC 키 e2e 검증(소득세법 1511 청크) |
| 3-1 | Provenance trace | ✅ | `Section.provenance: list[RuleEvaluation]` + LLM `[rule_id]` 강제 |
| 3-2 | LLM 룰 컴파일 + 검수 | ✅ | `rule_compiler.py` + `rule_drafts_store.py` + `/admin/rules` |
| 3-3 | 회사 신고 cross-check | ✅ | `verification.py` + `/verify` + ResultStep VerifySection |
| 4-1 | 다년도 What-if 시뮬 | ✅ | `simulate.py` carry-forward + ResultStep SimulateSection |
| 4-2 | 단순 RAG | ✅ | `rag.py` per-law + cosine + `/admin/rag` |
| 4-3 | Greedy 추천 | ✅ | `recommend.py` 4 lever + ResultStep RecommendSection |
| 4-4 | 의존성 그래프 (ripple) | ✅ | `dependencies.py` + `/admin/ripple` |

### v2 (정확도 / 신뢰성 보강)

| 항목 | 상태 | 핵심 산출물 |
|---|:---:|---|
| v2-1 Admin 인증 | ✅ | `app/security.py` + `X-Admin-Token` 헤더 + AdminGate 컴포넌트. /admin/* + /rag/* 가드 |
| v2-2 PDF 파서 보강 | ✅ | 사후 검증/정규화, 음수·이상치·문자열 흡수, +37 단위 테스트 |
| v2-3 analyze 에 RAG 통합 | ✅ | `_fetch_rag_context` → LLM 프롬프트에 법령 본문 자동 주입, silent fallback |
| v2-4 골든셋 5건 추가 | ✅ | 38%·40% 구간 + 한부모/장애인/저소득/임원급 |

### Tier 1 (운영 배포 묶음 — Docker on EC2)

| 항목 | 상태 | 핵심 산출물 |
|---|:---:|---|
| Tier 1-1 Docker + Caddy | ✅ | `client/Dockerfile`(Next standalone) + `server/Dockerfile`(slim) + `docker-compose.yml` + `Caddyfile`(자동 SSL) |
| Tier 1-2 CORS env-driven | ✅ | `CORS_ORIGINS` 환경변수, `<EC2_IP>` 자리표시자 제거 |
| Tier 1-3 CI (GitHub Actions) | ✅ | `.github/workflows/test.yml` — pytest + lint + build + docker buildx |
| Tier 1-4 Rate limit (slowapi) | ✅ | `/analyze`·`/pdf-parse` 5/min, `/admin/rules/compile` 10/min, `/admin/rag/search` 30/min, `/admin/rag/index` 10/hour |
| Tier 1-5 구조화된 로깅 | ✅ | `logging_config.py` + Request ID 미들웨어 + LOG_LEVEL env |

---

## 2. 결정사항 (확정)

| 항목 | 결정 | 근거 |
|---|---|---|
| 기준 연도 | **2025** | 2025년 귀속분 → 2026 초 정산 |
| 법령 데이터 소스 | **국가법령정보센터 OPEN API** | 단일 출처 + 변경 감지. e2e 검증 통과 |
| UI primary CTA | **slate-900 검정** (`#0F172A`) | 노랑 highlight 대비 가장 강함 |
| 노랑 사용 영역 | CTA primary 1곳 + 숫자 highlight + tip 박스만 | 브랜드 보존 + 신뢰감 균형 |
| 마스코트 노출 | 헤더 글자 로고 (scrubbing motif SVG) + 결과 페이지 작은 일러스트 | 친근함 + 전문성 균형 |
| 골든셋 출처 | 국세청 모의계산기 + 공식 예제 | 다양성 |
| 아이콘 라이브러리 | `lucide-react` | 트리셰이크, 톤 통일 |
| 다크모드 | v2 보류 | v1 작업량 2배 |
| 서버 사용자 데이터 영속화 | **하지 않음** | 프라이버시 default off |
| 법령 캐시 저장소 | 디스크 (`legal_cache/`) 시작 | 트래픽 늘면 Redis |
| RAG 임베딩 모델 | `text-embedding-3-small` | 다국어 + 1536 dim + 저렴 |
| RAG 벡터 저장 | 디스크 per-law JSON | 수백 법령까지 OK, 이후 vector DB |
| LLM 모델 | `gpt-4o-mini` | 비용 효율, 한국어 OK |
| 룰 평가기 | Pydantic discriminated union (`eval()` X) | 보안 |
| **운영 배포** | **Docker + docker-compose + Caddy on EC2** (Vercel X) | 단일 EC2 통합 운영, Caddy 자동 SSL |
| **Admin 인증** | **`X-Admin-Token` 단일 토큰** (env `ADMIN_TOKEN`) | 단일 운영자, OAuth/세션은 v3 |
| **시크릿** | `.env` 파일 EC2 직접 (chmod 600) | 1인 운영, AWS SSM 은 v3 |
| **로깅 출력처** | **stdout** (docker logs 로 수집) | 단순 + 표준 12-factor |

---

## 3. 보안 결정

PoC 직접 검증 → 차단 조치 → 회귀 테스트.

| 위협 | 발견 | 차단 조치 |
|---|---|---|
| **Path traversal** in `rule_drafts_store` | `rule_id="../../../../tmp/PWN"` 으로 base 디렉터리 탈출 PoC 성공 | `_SAFE_ID_RE = ^[A-Za-z0-9_\-]+$`, `UnsafeIdError`, Pydantic pattern, 라우터 400 매핑 |
| Same in `rag._pack_path` & `legal_api._cache_path` | 동일 패턴 | `_safe_path_component` / `_safe_component` |
| RAG 빈 인덱스에서 OpenAI 호출 | 401 + 비용 | 필터 후 후보 0이면 임베딩 호출 skip |
| `simulate` 음수 입력 | 잘못된 결과로 사용자 혼란 | `YearOverride` 의 number 필드 모두 `ge=0` |
| LLM hallucination (없는 법령 인용) | 프롬프트 회귀 | 시스템 제공 `[rule_id]` 만 인용 허용 + 룰 컴파일러 메타 강제 덮어씀 |
| `/admin/*` 와 `/rag/*` 무인증 | (기획상) | `X-Admin-Token` + `hmac.compare_digest` 타이밍 공격 방어. ADMIN_TOKEN 미설정 시 503 |
| LLM/embedding 비용 폭주 | (기획상) | `slowapi` rate limit (4 임계값) |
| `print()` 디버그 / 로그 누락 | 운영 가시성 0 | `logging` dictConfig + Request ID 미들웨어 |

---

## 4. 운영 배포 가이드

### EC2 초기 셋업
```bash
# Ubuntu 22.04+
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER && newgrp docker

git clone https://github.com/KANGJIYEON2/susemi.git
cd susemi

cp .env.example .env
nano .env
# OPENAI_API_KEY=sk-...
# OPEN_LAW_API_KEY=hihello516 (예시)
# ADMIN_TOKEN=긴_랜덤_문자열
# SITE_ADDRESS=:80   ← IP 로 시작. 도메인 붙일 때 susemi.kr 식으로 변경.

docker compose up -d --build
docker compose logs -f caddy   # 헬스체크
```

### 도메인 붙일 때
```bash
# DNS A 레코드: susemi.kr → EC2 public IP
nano .env
# SITE_ADDRESS=susemi.kr   ← 변경
docker compose up -d   # caddy 자동 Let's Encrypt 발급
```

### 업데이트
```bash
git pull
docker compose up -d --build
```

### 로그 / 모니터링
```bash
docker compose logs -f server      # FastAPI + uvicorn
docker compose logs -f client      # Next.js
docker compose logs -f caddy       # access + SSL 발급
docker compose ps                  # 컨테이너 상태
```

---

## 5. v2 백로그 (Tier 별 우선순위)

### Tier 2 — 사용자 가치 / 데모 임팩트 (다음 후보)

| 항목 | 작업량 | 임팩트 | 비고 |
|---|:-:|:-:|---|
| **다년도 트렌드 뷰** | 1일 | ★★★ | IndexedDB 누적 기반 차트. 데이터는 이미 쌓이고 있음 |
| **분석 결과 PDF/이미지 export** | 1일 | ★★ | `html2canvas` + `jsPDF` 또는 print stylesheet |
| **한국어 폰트(Pretendard) 직접 호스팅** | 0.3일 | ★ | 작아서 끼워넣기 좋음. 한글 가독성 즉시 ↑ |
| **분석 결과 비교** (이전 vs 현재) | 0.5일 | ★★ | IndexedDB 기록 활용 |

### Tier 3 — 세무 정확도 심화

| 항목 | 작업량 | 임팩트 | 비고 |
|---|:-:|:-:|---|
| **국세청 모의계산기 동치성 실측 검증** | 사용자 액션 | ★★★ | 골든셋 10케이스를 실 모의계산기로 돌려 expected 값 보정. 현재는 손계산. |
| **원천징수영수증 PDF 파서** | 1.5일 | ★★ | `/verify` 입력 수동 9개 → PDF 한 장으로 자동 채움 |
| **항목별 정밀 산식** | 2~3일 | ★★ | 자녀세액공제 / 의료비 한도별 / 기부금 종류별. 현재 `extra_*` 합산값으로 단순화 |
| **연도별 세율표** (`tax_tables/2026.json`...) | 0.5일/연도 | ★ | 시뮬 정밀도 |

### Tier 4 — 장기 / 트리거 조건

| 항목 | 트리거 |
|---|---|
| Vector DB (pgvector / Qdrant) | RAG 100+ 법령, 검색 latency 이슈 |
| Background job (법령 변경 감지 + 자동 재컴파일) | 법령 자주 바뀌는 게 운영 부담 될 때 |
| Sentry / 에러 트래킹 | 사용자 발견 버그 잦아질 때 |
| Admin 페이지 합본 layout | 검수자 multi-task 빈번해질 때 |
| i18n / 영문 병기 | 해외 사용자 요청 시 |
| **WASM Rust BigDecimal** | 정수 산식 한계 (분수 비율 정확도) |
| **ILP 최적화** | greedy 4 lever 로 안 잡히는 다변수 폭발 |
| **KG + GraphRAG** | 단순 RAG 정확도 한계 명확해질 때 |
| **Federated Learning** | 데이터량 충분(수천 사용자 피드백) |

---

## 6. 잔여 정리 (small chores)

| 항목 | 상태 | 메모 |
|---|---|---|
| `.github/workflows/deploy.yml` 갱신 | ⚠️ TODO | 현재 옛 gunicorn 방식(`pkill gunicorn` + `pip install`)으로 작성됨. Docker 전환 후 obsolete. **수정안**: ssh로 `cd ~/susemi && git pull && docker compose up -d --build` 호출하게 |
| 골든셋 모의계산기 동치성 검증 | ⚠️ TODO | 사용자 액션 필요 (Tier 3-1 참조) |
| `legal_api.list_changes_since` 실 응답 검증 | ⚠️ assumed | 현재 미검증, 호출 시 502 가능 |
| Admin 페이지 noindex meta | ✅ done | `app/admin/layout.tsx` 의 metadata `robots: noindex` |

---

## 7. 안 할 것 (명시)

- 서버에 사용자 PDF/입력 영속화 (프라이버시 default)
- 출처 없는 법령 인용 (LLM hallucination 차단)
- "회사 신고가 X% 틀렸다" 같은 단정 표현 (오해 소지 → "차이 발생, 확인 필요" 톤)
- "Causal Reasoning" / "Federated Learning" 같은 학술 용어 마케팅 — 실제 구현은 단순 결정론/로컬 학습. 이름과 기술 일치 ("ripple-effect simulator").
- 룰 evaluator 에 `eval()` 사용 (Pydantic discriminated union 으로 안전성 확보)
- Vercel 배포 (Docker on EC2 단일 운영으로 통합)

---

## 8. 핵심 데이터/스키마 위치

- 룰: `server/app/data/rules/{year}.json` ([rule_schema.py](./server/app/schemas/rule_schema.py))
- 룰 드래프트: `server/app/data/rules/drafts/{year}/{rule_id}.json`
- 세율표: `server/app/data/tax_tables/{year}.json`
- 법령 캐시: `server/app/data/legal_cache/{law_id}/{date}.json` (gitignored)
- RAG 인덱스: `server/app/data/rag_index/{law_id}/{date}.json` (gitignored)
- 클라 영속: 브라우저 IndexedDB `susemi.analyses` store

### 환경변수 (.env)

| 키 | 필수 | 설명 |
|---|:---:|---|
| `OPENAI_API_KEY` | ✅ | OpenAI (chat + embedding) |
| `OPEN_LAW_API_KEY` | ✅ | 국가법령정보센터 OC |
| `ADMIN_TOKEN` | ✅ | `/admin/*` + `/rag/*` 가드 |
| `CORS_ORIGINS` | 선택 | 쉼표 구분, 기본 `localhost:3000` |
| `SITE_ADDRESS` | 선택 | Caddy 사이트 주소 (`:80` 또는 도메인) |
| `LOG_LEVEL` | 선택 | 기본 `INFO` |

---

## 9. 다음 결정 필요한 사항

추가 작업 시 사용자에게 확인 필요한 항목:

- [ ] **Tier 2 우선 항목 선택** — 다년도 트렌드 뷰 / PDF export / Pretendard 폰트 / 분석 결과 비교 중 어디부터?
- [ ] **deploy.yml 갱신 타이밍** — 지금? 첫 EC2 배포 검증 후?
- [ ] **모의계산기 골든셋 검증** — 사용자가 직접 한 번 돌려서 차이 찾기
- [ ] PDF export 디자인 — A4 인쇄용? 이미지?
- [ ] 다국어 — 한국어 only 유지 vs 영문 병기
- [ ] 라이선스 — MIT? Proprietary? 비공개?
