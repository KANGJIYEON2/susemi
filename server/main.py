import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    admin_rules,
    analyze,
    dependencies,
    manual_input,
    pdf_parse,
    rag,
    recommend,
    simulate,
    user_input,
    verify,
)



app = FastAPI(
    title="Susemi Backend",
    description="근로소득자 연말정산 Why 설명용 수세미 백엔드",
    version="1.0.0",
)

# CORS (로컬 Next.js랑 붙일 거 생각해서 널널하게)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://<EC2_IP>",
        "https://susemi.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(user_input.router, prefix="/api/v1", tags=["user-input"])
app.include_router(pdf_parse.router, prefix="/api/v1", tags=["pdf"])
app.include_router(manual_input.router, prefix="/api/v1", tags=["manual-input"])
app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])
app.include_router(admin_rules.router, prefix="/api/v1", tags=["admin-rules"])
app.include_router(verify.router, prefix="/api/v1", tags=["verify"])
app.include_router(simulate.router, prefix="/api/v1", tags=["simulate"])
app.include_router(rag.router, prefix="/api/v1", tags=["rag"])
app.include_router(recommend.router, prefix="/api/v1", tags=["recommend"])
app.include_router(dependencies.router, prefix="/api/v1", tags=["ripple"])


@app.get("/")
def health_check():
    return {"status": "ok", "service": "susemi-backend"}
