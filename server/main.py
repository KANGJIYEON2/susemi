import logging
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import configure_logging
from app.rate_limit import limiter
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


# 로깅 설정 — import 시점 로그도 잡힘
configure_logging()
logger = logging.getLogger("susemi")



app = FastAPI(
    title="Susemi Backend",
    description="근로소득자 연말정산 Why 설명용 수세미 백엔드",
    version="1.0.0",
)

# Rate limit — 데코레이터로 명시한 엔드포인트만 적용 (app/rate_limit.py)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Request ID 미들웨어 — 모든 요청에 X-Request-ID 부여 + 응답 헤더 + 액세스 로그
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed method=%s path=%s rid=%s",
                request.method,
                request.url.path,
                request_id,
            )
            raise
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s %s rid=%s",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
        )
        return response


app.add_middleware(RequestIdMiddleware)


# CORS — 환경변수 CORS_ORIGINS (쉼표 구분) 로 주입.
# 운영(Caddy 뒤)에서는 동일 호스트라 거의 무관, 그래도 명시적 허용 목록 유지.
# 개발: dev 서버 (3000) 와 uvicorn (8000) 분리 → CORS 필요.
def _parse_origins(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
cors_origins = _parse_origins(os.getenv("CORS_ORIGINS", _default_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
