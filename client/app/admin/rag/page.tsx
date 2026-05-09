"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";

import Button from "@/app/components/ui/Button";
import Card from "@/app/components/ui/Card";
import Input from "@/app/components/ui/Input";
import {
  ragIndexLaw,
  ragSearch,
  ragStats,
  type RagHit,
  type RagStatsEntry,
} from "@/app/lib/api";

export default function AdminRagPage() {
  return (
    <div className="mx-auto max-w-[920px] px-5 py-8 md:py-12">
      <header className="mb-7">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Admin
        </div>
        <h1 className="mt-1 text-[24px] font-bold tracking-tight text-slate-900">
          RAG · 법령 임베딩 검색
        </h1>
        <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
          법령을 청크 단위로 임베딩해 디스크에 저장하고, 자연어 질의로 top-K 매칭 청크를
          가져옵니다. 룰 컴파일·LLM 응답 보강에 사용해요.
        </p>
      </header>

      <IndexerCard />

      <div className="mt-8">
        <SearcherCard />
      </div>

      <div className="mt-8">
        <StatsCard />
      </div>
    </div>
  );
}

/* ============================================================
   인덱서
============================================================ */

function IndexerCard() {
  const [law_id, setLawId] = useState("");
  const [law_mst, setLawMst] = useState("");
  const [effective_date, setEffectiveDate] = useState("");
  const [article_no, setArticleNo] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setErrMsg(null);
    if (!law_id.trim() && !law_mst.trim()) {
      setErrMsg("law_id 또는 law_mst 둘 중 하나는 필수입니다.");
      return;
    }
    setBusy(true);
    try {
      const res = await ragIndexLaw({
        law_id: law_id.trim() || null,
        law_mst: law_mst.trim() || null,
        use_mst: !!law_mst.trim(),
        effective_date: effective_date.trim() || null,
        article_no: article_no.trim() || null,
      });
      setMsg(
        `${res.law_name} (${res.effective_date ?? "latest"}) ` +
          `— ${res.chunks_indexed}개 청크 인덱싱 (${res.embedding_model})`
      );
    } catch (err: unknown) {
      setErrMsg(err instanceof Error ? err.message : "인덱싱 실패");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card pad="lg" className="space-y-4">
      <div className="flex items-center gap-2">
        <Database className="h-4 w-4 text-slate-700" />
        <h2 className="text-[15px] font-semibold text-slate-900">법령 인덱싱</h2>
      </div>
      <form onSubmit={onSubmit} className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="law_id (6자리)">
            <Input
              placeholder="001565"
              value={law_id}
              onChange={(e) => setLawId(e.target.value)}
            />
          </Field>
          <Field label="law_mst (법령일련번호)">
            <Input
              placeholder="285523"
              value={law_mst}
              onChange={(e) => setLawMst(e.target.value)}
            />
          </Field>
          <Field label="effective_date (YYYYMMDD, 선택)">
            <Input
              placeholder="20250101"
              value={effective_date}
              onChange={(e) => setEffectiveDate(e.target.value)}
            />
          </Field>
          <Field label="article_no (조 번호, 선택 — 일부만 인덱싱)">
            <Input
              placeholder="52"
              value={article_no}
              onChange={(e) => setArticleNo(e.target.value)}
            />
          </Field>
        </div>

        {msg ? (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12px] text-emerald-700">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {msg}
          </div>
        ) : null}
        {errMsg ? (
          <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            {errMsg}
          </div>
        ) : null}

        <Button
          type="submit"
          variant="primary"
          size="md"
          disabled={busy}
          leftIcon={
            busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Database className="h-4 w-4" />
            )
          }
        >
          {busy ? "인덱싱 중…" : "인덱싱 실행"}
        </Button>
      </form>
    </Card>
  );
}

/* ============================================================
   검색
============================================================ */

function SearcherCard() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState("5");
  const [lawIdFilter, setLawIdFilter] = useState("");
  const [hits, setHits] = useState<RagHit[] | null>(null);
  const [totalIndexed, setTotalIndexed] = useState(0);
  const [busy, setBusy] = useState(false);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrMsg(null);
    setHits(null);
    if (!query.trim()) {
      setErrMsg("질의를 입력하세요.");
      return;
    }
    setBusy(true);
    try {
      const res = await ragSearch({
        query: query.trim(),
        top_k: Math.max(1, Math.min(50, Number(topK) || 5)),
        law_id_filter: lawIdFilter.trim() || null,
      });
      setHits(res.hits);
      setTotalIndexed(res.total_indexed);
    } catch (err: unknown) {
      setErrMsg(err instanceof Error ? err.message : "검색 실패");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card pad="lg" className="space-y-4">
      <div className="flex items-center gap-2">
        <Search className="h-4 w-4 text-slate-700" />
        <h2 className="text-[15px] font-semibold text-slate-900">검색</h2>
      </div>

      <form onSubmit={onSubmit} className="space-y-3">
        <Field label="자연어 질의">
          <Input
            placeholder="예: 신용카드 사용액이 25% 미만일 때 어떻게 되나요?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="top_k (1~50)" small>
            <Input
              type="text"
              inputMode="numeric"
              value={topK}
              onChange={(e) => setTopK(e.target.value)}
            />
          </Field>
          <Field label="law_id 필터 (선택)" small>
            <Input
              placeholder="A 또는 001565"
              value={lawIdFilter}
              onChange={(e) => setLawIdFilter(e.target.value)}
            />
          </Field>
        </div>

        {errMsg ? (
          <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            {errMsg}
          </div>
        ) : null}

        <Button
          type="submit"
          variant="primary"
          size="md"
          disabled={busy}
          leftIcon={
            busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )
          }
        >
          {busy ? "검색 중…" : "검색"}
        </Button>
      </form>

      {hits !== null ? (
        <div className="space-y-2 border-t border-slate-100 pt-3">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>
              {hits.length}개 hit · 전체 인덱스 {totalIndexed.toLocaleString("ko-KR")} 청크
            </span>
          </div>
          {hits.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50/40 px-3 py-3 text-center text-[12px] text-slate-500">
              매칭되는 청크가 없어요.
            </p>
          ) : (
            <ul className="space-y-2">
              {hits.map((h, i) => (
                <HitRow key={`${h.chunk.chunk_id}-${i}`} hit={h} rank={i + 1} />
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </Card>
  );
}

function HitRow({ hit, rank }: { hit: RagHit; rank: number }) {
  const c = hit.chunk;
  return (
    <li className="rounded-xl border border-slate-200 bg-white px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="tabular text-[10px] font-semibold text-slate-400">
          #{rank}
        </span>
        <span className="font-mono text-[10px] font-medium text-slate-600">
          {c.chunk_id}
        </span>
        <span className="rounded-md bg-slate-100 px-1.5 py-px text-[10px] font-semibold tabular text-slate-700">
          score {hit.score.toFixed(4)}
        </span>
        {c.effective_date ? (
          <span className="text-[10px] text-slate-400">
            efYd {c.effective_date}
          </span>
        ) : null}
      </div>
      <p className="mt-1.5 text-[12px] leading-relaxed text-slate-700">
        {c.text}
      </p>
    </li>
  );
}

/* ============================================================
   통계
============================================================ */

function StatsCard() {
  const [entries, setEntries] = useState<RagStatsEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const res = await ragStats();
      setEntries(res.laws);
      setTotal(res.total_chunks);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "통계 로드 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <Card pad="lg" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-semibold text-slate-900">
          인덱스 통계 ({total.toLocaleString("ko-KR")} 청크)
        </h2>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={refresh}
          leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
        >
          새로고침
        </Button>
      </div>

      {err ? (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
          <AlertTriangle className="h-3.5 w-3.5" />
          {err}
        </div>
      ) : null}

      {loading && entries.length === 0 ? (
        <div className="text-[12px] text-slate-500">불러오는 중…</div>
      ) : entries.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50/40 px-3 py-3 text-center text-[12px] text-slate-500">
          인덱싱된 법령이 없어요. 위에서 인덱싱해 주세요.
        </p>
      ) : (
        <ul className="space-y-1">
          {entries.map((e) => (
            <li
              key={`${e.law_id}-${e.effective_date ?? "latest"}`}
              className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2"
            >
              <div className="min-w-0">
                <div className="text-[12px] font-semibold text-slate-900">
                  {e.law_name}
                </div>
                <div className="text-[10px] text-slate-500">
                  law_id={e.law_id} · efYd={e.effective_date ?? "latest"} ·{" "}
                  {e.embedding_model}
                </div>
              </div>
              <span className="tabular text-[12px] font-semibold text-slate-700">
                {e.chunks.toLocaleString("ko-KR")} 청크
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/* ============================================================
   shared
============================================================ */

function Field({
  label,
  small,
  children,
}: {
  label: string;
  small?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span
        className={`${
          small ? "text-[12px]" : "text-[13px]"
        } font-medium text-slate-700`}
      >
        {label}
      </span>
      {children}
    </label>
  );
}
