"""
Admin 토큰 인증.

== 사용 ==
환경변수 ADMIN_TOKEN 에 임의 문자열 저장. 클라이언트는 X-Admin-Token 헤더로 전송.
미설정 환경(운영 X) 에서는 503으로 거부 — admin 기능 사용 불가가 default.

== 라우터 단위 적용 ==
    router = APIRouter(dependencies=[Depends(require_admin_token)])

또는 엔드포인트 단위 — Depends(require_admin_token).

== 한계 ==
- 단일 토큰. 다중 사용자/롤은 v3.
- 평문 비교 — env 가 노출되면 끝. rate limit + audit log 는 v3.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


ADMIN_TOKEN_ENV = "ADMIN_TOKEN"
ADMIN_TOKEN_HEADER = "X-Admin-Token"


def require_admin_token(
    x_admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER),
) -> bool:
    expected = os.getenv(ADMIN_TOKEN_ENV)
    if not expected:
        # 운영자가 토큰을 설정하지 않았으면 admin 자체가 disabled
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"{ADMIN_TOKEN_ENV} 환경변수가 설정되지 않아 admin 기능이 비활성 상태입니다."
            ),
        )
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{ADMIN_TOKEN_HEADER} 헤더가 필요합니다.",
        )
    # 타이밍 공격 방어 — hmac.compare_digest
    if not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 admin 토큰입니다.",
        )
    return True
