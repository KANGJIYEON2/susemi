# syntax=docker/dockerfile:1.7
# FastAPI · Python 3.13 slim

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 시스템 의존성 — PyMuPDF 같은 wheel 없는 패키지 빌드 대비
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 의존성 layer 분리 (코드 변경 시 캐시 활용)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드
COPY . .

# 비루트 사용자
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# 운영용: workers 1 (단일 EC2). 필요 시 docker-compose 에서 override.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
