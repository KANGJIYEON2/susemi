import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import user_input, pdf_parse, manual_input, analyze



app = FastAPI(
    title="Susemi Backend",
    description="근로소득자 연말정산 Why 설명용 수세미 백엔드",
    version="1.0.0",
)

# CORS (로컬 Next.js랑 붙일 거 생각해서 널널하게)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 나중에 배포 시 도메인 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(user_input.router, prefix="/api/v1", tags=["user-input"])
app.include_router(pdf_parse.router, prefix="/api/v1", tags=["pdf"])
app.include_router(manual_input.router, prefix="/api/v1", tags=["manual-input"])
app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])


@app.get("/")
def health_check():
    return {"status": "ok", "service": "susemi-backend"}
