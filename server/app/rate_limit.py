"""
Rate limiting (slowapi).

== 정책 ==
값비싼 LLM/embedding 엔드포인트만 보호. 순수 compute 엔드포인트(verify/simulate/
recommend/ripple) 는 제한 없음 — 의도적으로 가볍게.

키: 클라이언트 IP (Caddy 뒤에 있을 때는 X-Forwarded-For 헤더 활용 — slowapi 가 자동 처리).

== 사용 ==
    from fastapi import Request
    from app.rate_limit import limiter

    @router.post("/...")
    @limiter.limit("5/minute")
    async def endpoint(request: Request, ...):
        ...

데코레이터 적용 시 첫 인자가 반드시 `request: Request` 여야 함 (slowapi 내부 규약).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


limiter = Limiter(
    key_func=get_remote_address,
    # 기본 limit 없음 — 데코레이터로 명시한 엔드포인트만 보호
)


# 자주 쓰는 임계값 상수 — 명시적 가독성
LIMIT_LLM_USER = "5/minute"        # /analyze, /pdf-parse — 사용자 facing LLM
LIMIT_LLM_ADMIN = "10/minute"      # /admin/rules/compile — 검수자 LLM
LIMIT_EMBEDDING = "30/minute"      # /admin/rag/search 등 임베딩 호출
LIMIT_INDEX = "10/hour"            # /admin/rag/index — 비용 큰 1회성 작업
