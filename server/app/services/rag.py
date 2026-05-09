"""
Phase 4-2: 단순 RAG.

== 구조 ==
법령 chunks → OpenAI embedding → 디스크 저장 (per-law) → 메모리 로드 → cosine top-K

== 위치 ==
server/app/data/rag_index/{law_id}/{effective_date or 'latest'}.json

== 안전장치 ==
- embed_fn 인자로 OpenAI 호출 주입 가능 (테스트용)
- chunks_override 로 법령 API 우회 가능
- 동일 (law_id, effective_date) 재인덱싱 = 덮어쓰기

== 한계 (v0) ==
- 모든 인덱스를 매 검색마다 메모리 로드 — 수백 법령까지는 OK, 그 이상이면 vector DB.
- 임베딩 재사용 dedup 미구현 (text_hash 동일이면 skip 같은 최적화는 v1).
- 한국어 토큰화 별도 안 함 — OpenAI embedding 모델이 다국어 지원.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from openai import AsyncOpenAI

from app.schemas.legal_schema import Law
from app.schemas.rag_schema import (
    IndexedChunk,
    IndexedLawPack,
    IndexStatsEntry,
    SearchHit,
)


DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAG_SUBDIR = ("rag_index",)
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


# OpenAI 클라이언트 lazy init
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# 테스트에서 monkeypatch / 인자 주입 가능
EmbedFn = Callable[[list[str]], Awaitable[list[list[float]]]]


async def _default_embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    resp = await _get_client().embeddings.create(
        model=DEFAULT_EMBEDDING_MODEL,
        input=texts,
    )
    return [d.embedding for d in resp.data]


# -------------------- 디스크 경로 --------------------


def _rag_dir(data_dir: Path) -> Path:
    return data_dir.joinpath(*RAG_SUBDIR)


def _pack_path(
    data_dir: Path, law_id: str, effective_date: str | None
) -> Path:
    key = effective_date or "latest"
    return _rag_dir(data_dir) / law_id / f"{key}.json"


# -------------------- cosine --------------------


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


# -------------------- 인덱싱 --------------------


async def index_law(
    law: Law,
    *,
    embed_fn: EmbedFn | None = None,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    data_dir: Path | None = None,
    article_no_filter: str | None = None,
) -> IndexedLawPack:
    """
    Law → 청크 평탄화 → 임베딩 → 디스크 저장 → IndexedLawPack 반환.

    article_no_filter 가 주어지면 해당 조만 인덱싱.
    """
    base = data_dir or DEFAULT_DATA_DIR
    embed = embed_fn or _default_embed

    # 1) 청크 평탄화 (조/항/호 단위)
    flat: list[IndexedChunk] = []
    raw_texts: list[str] = []
    raw_meta: list[dict[str, Any]] = []

    for article in law.articles:
        if article_no_filter and article.article_no != article_no_filter:
            continue
        for chunk in article.paragraphs:
            if not chunk.text or not chunk.text.strip():
                continue
            raw_texts.append(chunk.text)
            raw_meta.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "law_id": chunk.law_id,
                    "law_name": chunk.law_name,
                    "article_no": chunk.article_no,
                    "paragraph_no": chunk.paragraph_no,
                    "item_no": chunk.item_no,
                    "text": chunk.text,
                    "text_hash": chunk.text_hash,
                    "effective_date": chunk.effective_date,
                }
            )

    # 2) 임베딩 (배치)
    vectors = await embed(raw_texts)
    if len(vectors) != len(raw_texts):
        raise RuntimeError(
            f"임베딩 개수 불일치: 입력 {len(raw_texts)} / 출력 {len(vectors)}"
        )

    now = datetime.now(timezone.utc)
    for meta, vec in zip(raw_meta, vectors):
        flat.append(
            IndexedChunk(
                **meta,
                embedding=vec,
                embedding_model=embedding_model,
                indexed_at=now,
            )
        )

    pack = IndexedLawPack(
        law_id=law.law_id,
        law_name=law.law_name,
        effective_date=law.effective_date,
        embedding_model=embedding_model,
        chunks=flat,
        indexed_at=now,
    )

    # 3) 저장
    path = _pack_path(base, law.law_id, law.effective_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(pack.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return pack


# -------------------- 로드 / stats --------------------


def _load_pack(path: Path) -> IndexedLawPack | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return IndexedLawPack.model_validate(data)
    except (OSError, json.JSONDecodeError):
        return None


def list_packs(data_dir: Path | None = None) -> list[IndexedLawPack]:
    base = data_dir or DEFAULT_DATA_DIR
    root = _rag_dir(base)
    if not root.exists():
        return []
    out: list[IndexedLawPack] = []
    for law_dir in sorted(root.iterdir()):
        if not law_dir.is_dir():
            continue
        for f in sorted(law_dir.glob("*.json")):
            pack = _load_pack(f)
            if pack is not None:
                out.append(pack)
    return out


def get_stats(data_dir: Path | None = None) -> tuple[list[IndexStatsEntry], int]:
    packs = list_packs(data_dir)
    entries = [
        IndexStatsEntry(
            law_id=p.law_id,
            law_name=p.law_name,
            effective_date=p.effective_date,
            chunks=len(p.chunks),
            indexed_at=p.indexed_at,
            embedding_model=p.embedding_model,
        )
        for p in packs
    ]
    total = sum(len(p.chunks) for p in packs)
    return entries, total


# -------------------- 검색 --------------------


async def search(
    query: str,
    *,
    top_k: int = 5,
    law_id_filter: str | None = None,
    article_no_filter: str | None = None,
    embed_fn: EmbedFn | None = None,
    data_dir: Path | None = None,
) -> tuple[list[SearchHit], int]:
    """
    자연어 query → top-K 매칭 청크 + 전체 인덱스 청크 수.
    """
    embed = embed_fn or _default_embed
    qvecs = await embed([query])
    if not qvecs:
        return [], 0
    qvec = qvecs[0]

    packs = list_packs(data_dir)
    total = sum(len(p.chunks) for p in packs)

    candidates: list[tuple[float, IndexedChunk]] = []
    for pack in packs:
        if law_id_filter and pack.law_id != law_id_filter:
            continue
        for ch in pack.chunks:
            if article_no_filter and ch.article_no != article_no_filter:
                continue
            score = cosine(qvec, ch.embedding)
            candidates.append((score, ch))

    candidates.sort(key=lambda x: x[0], reverse=True)
    hits = [
        SearchHit(chunk=ch, score=s) for s, ch in candidates[: max(0, top_k)]
    ]
    return hits, total
