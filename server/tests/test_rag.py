"""
Phase 4-2 RAG 테스트.

embed_fn 을 주입해 OpenAI 호출 없이 동작 검증.
"""

import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.schemas.legal_schema import Law, LawArticle, LawChunk
from app.services import rag


# -------------------- helpers --------------------


def _chunk(
    chunk_id: str,
    text: str,
    *,
    article_no: str = "1",
    paragraph_no: str | None = None,
    item_no: str | None = None,
    law_id: str = "L1",
    law_name: str = "테스트법",
) -> LawChunk:
    return LawChunk(
        chunk_id=chunk_id,
        law_id=law_id,
        law_name=law_name,
        article_no=article_no,
        paragraph_no=paragraph_no,
        item_no=item_no,
        text=text,
        text_hash=f"h:{chunk_id}",
    )


def _law(*, law_id: str = "L1", law_name: str = "테스트법") -> Law:
    art1 = LawArticle(
        law_id=law_id,
        law_name=law_name,
        article_no="52",
        title="특별소득공제",
        text="조문 본문",
        paragraphs=[
            _chunk(
                f"{law_name}-§52-①",
                "신용카드 사용액이 총급여의 25%를 초과한 분에 대해 공제한다.",
                article_no="52",
                paragraph_no="①",
                law_id=law_id,
                law_name=law_name,
            ),
            _chunk(
                f"{law_name}-§52-②",
                "의료비가 총급여의 3%를 초과한 분에 대해 세액공제한다.",
                article_no="52",
                paragraph_no="②",
                law_id=law_id,
                law_name=law_name,
            ),
        ],
    )
    art2 = LawArticle(
        law_id=law_id,
        law_name=law_name,
        article_no="59",
        title="월세액 세액공제",
        text="",
        paragraphs=[
            _chunk(
                f"{law_name}-§59-①",
                "무주택 세대주이고 임대차계약을 체결한 경우 월세액의 일정률을 공제한다.",
                article_no="59",
                paragraph_no="①",
                law_id=law_id,
                law_name=law_name,
            ),
        ],
    )
    return Law(
        law_id=law_id,
        law_name=law_name,
        articles=[art1, art2],
        raw_text="full text",
        text_hash="lawhash",
        fetched_at=datetime.now(timezone.utc),
    )


def make_deterministic_embedder(vector_map: dict[str, list[float]]):
    """
    텍스트 → 벡터 매핑 사전을 받아, 매칭되는 키워드가 있으면 해당 벡터 반환.
    매칭 없으면 zeros (1차원 단위벡터로 fallback 가능하지만 그냥 zeros).
    """

    async def _embed(texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            chosen = None
            for keyword, vec in vector_map.items():
                if keyword in t:
                    chosen = vec
                    break
            if chosen is None:
                chosen = [0.0] * len(next(iter(vector_map.values())))
            out.append(list(chosen))
        return out

    return _embed


# -------------------- cosine 유틸 --------------------


def test_cosine_orthogonal_zero():
    assert rag.cosine([1, 0], [0, 1]) == 0.0


def test_cosine_identical_one():
    assert math.isclose(rag.cosine([1, 2, 3], [1, 2, 3]), 1.0, abs_tol=1e-9)


def test_cosine_zero_vector_safe():
    assert rag.cosine([0, 0], [1, 1]) == 0.0


# -------------------- 인덱싱 --------------------


async def test_index_law_writes_pack(tmp_path: Path):
    law = _law()
    embed = make_deterministic_embedder(
        {
            "신용카드": [1.0, 0.0, 0.0],
            "의료비": [0.0, 1.0, 0.0],
            "무주택": [0.0, 0.0, 1.0],
        }
    )
    pack = await rag.index_law(law, embed_fn=embed, data_dir=tmp_path)

    assert pack.law_id == "L1"
    assert len(pack.chunks) == 3
    assert all(len(c.embedding) == 3 for c in pack.chunks)

    # 디스크 저장 확인
    f = tmp_path / "rag_index" / "L1" / "latest.json"
    assert f.exists()


async def test_index_filter_by_article(tmp_path: Path):
    law = _law()
    embed = make_deterministic_embedder({"법": [1.0, 0.0]})
    pack = await rag.index_law(
        law, embed_fn=embed, data_dir=tmp_path, article_no_filter="59"
    )
    assert len(pack.chunks) == 1
    assert pack.chunks[0].article_no == "59"


async def test_index_skips_empty_text(tmp_path: Path):
    law = Law(
        law_id="L1",
        law_name="L",
        articles=[
            LawArticle(
                law_id="L1",
                law_name="L",
                article_no="1",
                paragraphs=[
                    _chunk("a", "텍스트 있음", article_no="1"),
                    _chunk("b", "  ", article_no="1"),  # 공백만
                ],
            )
        ],
        raw_text="x",
        text_hash="h",
        fetched_at=datetime.now(timezone.utc),
    )
    embed = make_deterministic_embedder({"있음": [1.0]})
    pack = await rag.index_law(law, embed_fn=embed, data_dir=tmp_path)
    assert len(pack.chunks) == 1


# -------------------- 검색 --------------------


async def test_search_returns_top_k_by_cosine(tmp_path: Path):
    law = _law()
    embed = make_deterministic_embedder(
        {
            "신용카드": [1.0, 0.0, 0.0],
            "의료비": [0.0, 1.0, 0.0],
            "무주택": [0.0, 0.0, 1.0],
        }
    )
    await rag.index_law(law, embed_fn=embed, data_dir=tmp_path)

    # 질의가 '신용카드' 키워드 → 동일 벡터 → §52-① 이 1위
    hits, total = await rag.search(
        "신용카드 공제 한도",
        top_k=2,
        embed_fn=embed,
        data_dir=tmp_path,
    )
    assert total == 3
    assert len(hits) == 2
    assert hits[0].chunk.paragraph_no == "①"
    assert hits[0].chunk.article_no == "52"
    assert hits[0].score >= hits[1].score


async def test_search_law_id_filter(tmp_path: Path):
    law_a = _law(law_id="A", law_name="A법")
    law_b = _law(law_id="B", law_name="B법")
    embed = make_deterministic_embedder({"공제": [1.0, 0.0]})
    await rag.index_law(law_a, embed_fn=embed, data_dir=tmp_path)
    await rag.index_law(law_b, embed_fn=embed, data_dir=tmp_path)

    hits, total = await rag.search(
        "공제",
        top_k=10,
        law_id_filter="A",
        embed_fn=embed,
        data_dir=tmp_path,
    )
    assert total == 6  # 두 법령 합산
    assert all(h.chunk.law_id == "A" for h in hits)


async def test_search_article_filter(tmp_path: Path):
    law = _law()
    embed = make_deterministic_embedder({"공제": [1.0, 0.0]})
    await rag.index_law(law, embed_fn=embed, data_dir=tmp_path)

    hits, _ = await rag.search(
        "공제",
        top_k=10,
        article_no_filter="59",
        embed_fn=embed,
        data_dir=tmp_path,
    )
    assert all(h.chunk.article_no == "59" for h in hits)


async def test_search_empty_index_returns_nothing(tmp_path: Path):
    embed = make_deterministic_embedder({"x": [1.0]})
    hits, total = await rag.search(
        "테스트", top_k=5, embed_fn=embed, data_dir=tmp_path
    )
    assert total == 0
    assert hits == []


# -------------------- stats --------------------


async def test_get_stats(tmp_path: Path):
    law_a = _law(law_id="A", law_name="A법")
    law_b = _law(law_id="B", law_name="B법")
    embed = make_deterministic_embedder({"법": [1.0, 0.0]})
    await rag.index_law(law_a, embed_fn=embed, data_dir=tmp_path)
    await rag.index_law(law_b, embed_fn=embed, data_dir=tmp_path)

    laws, total = rag.get_stats(data_dir=tmp_path)
    assert total == 6
    assert {e.law_id for e in laws} == {"A", "B"}


# -------------------- 임베딩 개수 mismatch --------------------


async def test_index_raises_on_embedding_count_mismatch(tmp_path: Path):
    law = _law()

    async def bad_embed(texts):
        return [[1.0]]  # 항상 1개만 — chunks 수와 mismatch

    with pytest.raises(RuntimeError):
        await rag.index_law(law, embed_fn=bad_embed, data_dir=tmp_path)
