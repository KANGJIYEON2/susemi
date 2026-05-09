"""
중앙 logging 설정.

- LOG_LEVEL 환경변수로 레벨 조정 (기본 INFO)
- stdout 으로만 출력 (도커/EC2 에서 docker logs 로 수집)
- 포맷: 시각 + 레벨 + 모듈 + request_id (있으면) + 메시지
"""

from __future__ import annotations

import logging
import logging.config
import os
import sys


def configure_logging() -> None:
    """앱 시작 시 1회 호출."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": sys.stdout,
                },
            },
            "root": {
                "handlers": ["console"],
                "level": level,
            },
            "loggers": {
                # uvicorn 자체 로그 형식 통일
                "uvicorn": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.error": {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["console"],
                    "level": "INFO",
                    "propagate": False,
                },
                # httpx (LLM/법령 API 호출) — DEBUG 면 매우 시끄러움 → INFO 까지만
                "httpx": {"level": "WARNING"},
                # openai SDK 도 INFO 까지만
                "openai": {"level": "WARNING"},
            },
        }
    )
