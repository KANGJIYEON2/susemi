<div align="center">

# 🌟 SUSEMI — AI 기반 연말정산 WHY 리포트

### **기획 → 디자인 → 프론트 → 백엔드 → AI 분석 → 배포까지 4일 만에 단독 개발**

<img width="120" src="./client/public/susemi.png" alt="SUSEMI Logo"/>

<br/>

<img src="https://img.shields.io/badge/Next.js_16-black?style=flat&logo=nextdotjs"/>
<img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white"/>
<img src="https://img.shields.io/badge/TailwindCSS-0EA5E9?style=flat&logo=tailwindcss&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/Python_3.10-blue?style=flat&logo=python"/>
<img src="https://img.shields.io/badge/OpenAI_API-black?style=flat&logo=openai"/>
<img src="https://img.shields.io/badge/PDF_Parsing-orange?style=flat"/>
<img src="https://img.shields.io/badge/Rule_Engine-blueviolet?style=flat"/>

<br/><br/>

✨ **사용자 맞춤형 연말정산 "WHY" 리포트 서비스**  
✨ **신용카드·의료비·기부금·월세 등 공제 항목별 ‘왜?’를 AI가 설명**  
✨ **PDF 파싱 → 세법 Rule Engine → AI 분석까지 자동 처리**

</div>

---

# 📌 프로젝트 요약

> **“왜 내 연말정산 환급액이 이렇게 나왔는지 알고 싶다.”**  
> 기존 간소화 서비스는 합계만 보여주고  
> **‘왜 이런 결과가 나왔는지’는 설명해주지 않습니다.**

**SUSEMI**는 PDF + 입력데이터 + 세법 규칙을 활용해  
AI가 **각 항목의 원인·비교·근거까지 설명한 WHY 리포트**를 생성합니다.

---

# 🚀 주요 기능

## ✔ AI Why 분석 엔진

- 단순 요약이 아닌 **원인 기반 Reasoning (Explainable AI)**
- 기준 대비 부족/초과 자동 판정
- PDF 데이터 + Rule Engine 조합 후 GPT가 설명 생성
- “수세미” 말투 적용 (친근 + 정확)

---

## ✔ 국세청 PDF 자동 파싱

### **PyMuPDF + GPT Hybrid Parsing 방식**

한국 연말정산 간소화 PDF는 구조가 일정하지 않아  
정규식 기반 파싱만으로는 정확도가 낮음.

그래서 SUSEMI는 **Hybrid Parsing Pipeline**을 사용함:

PDF Binary
→ PyMuPDF 텍스트 추출
→ LLM(GPT) 기반 텍스트 분석 및 JSON 구조화
→ Pydantic 후처리 및 타입 정제
→ ParsedPdfData + missing_fields 반환

### 장점

- 포맷이 조금 달라도 LLM이 문맥으로 파싱 가능
- 누락 항목을 `"missing_fields"` 로 자동 추천
- 정제된 스키마(JSON)로 API 안정성 확보
- 의료비/장애인/기부금 등 항목 분리 정확도 상승

---

## ✔ 카카오페이톤 감성 UI

- 브랜드 컬러 `#FFD84D` 적용
- **4단계 Wizard UX**
- PC: 오른쪽 고정 리포트 패널
- 모바일: 자동 스크롤
- 모든 Input/Checkbox/Card **직접 커스텀 제작**

---

## ✔ 단 4일 만에 단독 개발

기획 → 디자인 → 프론트 → 백엔드 → AI 분석 → 배포까지  
**100% 혼자 개발한 풀사이클 프로젝트**

---

# 🔧 시스템 아키텍처

Next.js 16 (Frontend)
│ - Wizard Forms
│ - 누락 항목 표시
│ - WHY 리포트 UI
│ - TypeScript
│
▼ JSON
FastAPI (Backend)
│ - PDF Parsing (PyMuPDF) + GPT Hybrid
│ - 세법 Rule Engine
│ - GPT WHY Reasoning
│ - Pydantic Validation
│
▼
OpenAI GPT (Why Analysis)

---

# 🧠 기능 상세

## 1️⃣ Wizard Step 흐름

| 단계              | 설명                         |
| ----------------- | ---------------------------- |
| 1. 소득/가족 입력 | 인적공제 + 세법요건 체크     |
| 2. PDF 업로드     | 자동 파싱 + 누락 항목 감지   |
| 3. 수동입력       | 월세·난임·안경·조리원·기부금 |
| 4. WHY 리포트     | 이유 + 근거 + 비교 수치      |

---

# 2️⃣ 세법 Rule Engine

세무/회계 실무 기반 규칙 모델링

- 총급여 5,000만원 이하 → 소득요건 충족
- 소득금액 100만원 초과 시 기본공제 불가
- 20세 이하 / 60세 이상만 인적공제
- 장애인은 나이 제한 없음
- 자녀세액공제와 기본공제 중복 불가
- 의료비: 본인/장애인/부양가족별 공제율 차등
- 신용카드 공제: 급여의 25% 초과분만 공제

---

# 3️⃣ PDF Parsing 전체 흐름

PDF Raw
→ Line Normalize
→ GPT Prompt 생성
→ GPT 텍스트 분석 & JSON 매핑
→ Pydantic 후처리
→ 최종 ParsedPdfData 반환

---

# 🛠 기술 스택

## Frontend

- Next.js 16 (App Router)
- TypeScript
- TailwindCSS
- Axios
- Custom UI Components
- 반응형 Wizard UI

## Backend

- FastAPI
- PyMuPDF / pdfminer
- **OpenAI GPT Hybrid Parsing**
- Pydantic v2
- AWS EC2 배포
- 세법 Rule Engine

---

# 📦 실행 방법

## Frontend

npm install
npm run dev

## Backend

pip install -r requirements.txt
uvicorn main:app --reload

---

# 📡 API 요약

### ▶ POST /parse-pdf

- PDF 업로드
- Hybrid parsing
- 누락 항목 반환

### ▶ POST /analyze-tax

- 전체 데이터 + Rule Engine 결과 결합
- WHY 리포트 생성

---

# 🏆 Technical Highlights (핵심 요약)

- **한국 간소화 PDF → GPT 기반 Hybrid Parsing 직접 구현**
- PDF 파싱 + Rule Engine + AI WHY 분석 **모두 직접 구축**
- Explainable AI 적용 (항목별 WHY 기반 설명)
- GPT Prompt Builder 설계 → 답변 품질 안정화
- Wizard 기반 UX · PC/모바일 최적화 UI
- TypeScript 기반 안정적인 SPA 구조
- **4일 만에 모든 기능을 가진 MVP 완성**

---

# 👩‍💻 Developer — 강지연

**Full-stack & AI Developer**

“아이디어를 빠르게 제품으로 만드는 개발자”

- 기획 → 설계 → 개발 → 배포 단독 수행
- 프론트/백엔드/AI 모두 구현 가능한 멀티스택
- 세무/회계 실무 경험 → Rule Engine 정확도 강화
- UI/UX 감각 우수
- 극강의 집중력 & 문제 해결능력

---

# License
