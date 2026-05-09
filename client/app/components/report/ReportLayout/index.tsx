"use client";

import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileText,
  Lightbulb,
  Loader2,
  ScrollText,
  Sparkles,
  XCircle,
} from "lucide-react";
import type { AnalyzeResponse, RuleEvaluation, Section } from "@/app/lib/types";

interface Props {
  data?: AnalyzeResponse | null;
  loading?: boolean;
  error?: string | null;
}

export default function ReportLayout({ data, loading, error }: Props) {
  if (loading) {
    return (
      <div className="flex min-h-[280px] flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white px-6 py-10 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        <p className="text-[13px] font-medium text-slate-700">
          항목별 Why 리포트를 작성 중입니다…
        </p>
        <p className="text-[11px] text-slate-400">잠시만 기다려주세요.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-2xl border border-red-200 bg-red-50/40 px-6 py-8 text-center">
        <AlertCircle className="h-5 w-5 text-red-500" />
        <p className="text-[13px] font-medium text-red-600">{error}</p>
        <p className="text-[11px] text-slate-500">
          잠시 후 다시 시도하거나 입력값을 확인해 주세요.
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-200 bg-white/60 px-6 py-8 text-center">
        <FileText className="h-5 w-5 text-slate-400" />
        <p className="text-[13px] font-medium text-slate-600">
          아직 분석 결과가 없어요
        </p>
        <p className="text-[11px] text-slate-400">
          왼쪽 위저드를 끝까지 진행하면 여기에 리포트가 표시됩니다.
        </p>
      </div>
    );
  }

  // [rule_id] 마커 lookup 용
  const allRuleIds = new Set(data.evaluations.map((e) => e.rule_id));

  return (
    <div className="space-y-7">
      {/* Summary */}
      <section>
        <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#CA8A04]">
          <Sparkles className="h-3 w-3" />
          Summary
        </div>
        <h1 className="mt-2 text-[22px] font-bold leading-snug text-slate-900">
          {data.summary.headline}
        </h1>

        {data.summary.key_points.length > 0 ? (
          <ul className="mt-4 space-y-2 rounded-2xl border border-slate-200 bg-white p-4">
            {data.summary.key_points.map((p, i) => (
              <li
                key={i}
                className="flex items-start gap-2.5 text-[13px] leading-relaxed text-slate-700"
              >
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      {/* Sections */}
      <div className="space-y-5">
        {data.sections.map((s, idx) => (
          <SectionCard
            key={s.id}
            index={idx + 1}
            section={s}
            knownRuleIds={allRuleIds}
          />
        ))}
      </div>

      {/* Final tips */}
      {data.tax_tips.length > 0 ? (
        <section className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <h2 className="flex items-center gap-1.5 text-[14px] font-semibold text-slate-900">
            <Lightbulb className="h-3.5 w-3.5 text-[#CA8A04]" />
            내년을 위한 총정리
          </h2>
          <ol className="mt-3 space-y-2.5">
            {data.tax_tips.map((t, i) => (
              <li
                key={i}
                className="flex gap-2.5 text-[13px] leading-relaxed text-slate-700"
              >
                <span className="tabular flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white text-[10px] font-bold text-slate-500 ring-1 ring-slate-200">
                  {i + 1}
                </span>
                <span>{t}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </div>
  );
}

/* ---------- 섹션 카드 ---------- */

function SectionCard({
  index,
  section,
  knownRuleIds,
}: {
  index: number;
  section: Section;
  knownRuleIds: Set<string>;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-baseline gap-2">
        <span className="tabular text-[11px] font-semibold text-slate-400">
          {String(index).padStart(2, "0")}
        </span>
        <h2 className="text-[15px] font-semibold text-slate-900">
          {section.title}
        </h2>
      </div>

      {section.highlight ? (
        <p className="mt-2 text-[13px] font-medium leading-relaxed text-slate-800">
          <DetailWithAnchors text={section.highlight} known={knownRuleIds} />
        </p>
      ) : null}

      {section.detail ? (
        <p className="mt-2 whitespace-pre-line text-[13px] leading-7 text-slate-600">
          <DetailWithAnchors text={section.detail} known={knownRuleIds} />
        </p>
      ) : null}

      {section.tips && section.tips.length > 0 ? (
        <div className="mt-4 rounded-xl border border-[#FDE68A] bg-[#FFFBEA] p-3.5">
          <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold text-[#854D0E]">
            <Lightbulb className="h-3 w-3" />
            TIP
          </div>
          <ul className="space-y-1">
            {section.tips.map((t, i) => (
              <li
                key={i}
                className="flex gap-1.5 text-[12px] leading-relaxed text-slate-700"
              >
                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-[#CA8A04]" />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {section.provenance && section.provenance.length > 0 ? (
        <ProvenanceBlock evaluations={section.provenance} />
      ) : null}
    </section>
  );
}

/* ---------- [rule_id] 마커 → 인라인 anchor 칩 ---------- */

function DetailWithAnchors({
  text,
  known,
}: {
  text: string;
  known: Set<string>;
}) {
  const parts = text.split(/(\[[a-z0-9_]+\])/g);
  return (
    <>
      {parts.map((p, i) => {
        const m = p.match(/^\[([a-z0-9_]+)\]$/);
        if (m && known.has(m[1])) {
          return (
            <a
              key={i}
              href={`#prov-${m[1]}`}
              className="ml-0.5 inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-1.5 py-px text-[10px] font-semibold tabular text-slate-600 align-middle hover:border-[#FACC15] hover:text-slate-900"
              title="근거 보기"
            >
              {m[1]}
            </a>
          );
        }
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

/* ---------- Provenance 펼침 블록 ---------- */

function ProvenanceBlock({ evaluations }: { evaluations: RuleEvaluation[] }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/60">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-[12px] font-semibold text-slate-700 hover:text-slate-900"
      >
        <span className="inline-flex items-center gap-1.5">
          <ScrollText className="h-3.5 w-3.5 text-slate-500" />
          근거 ({evaluations.length})
        </span>
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
        )}
      </button>

      {open ? (
        <div className="space-y-3 border-t border-slate-200 px-3.5 py-3">
          {evaluations.map((ev) => (
            <ProvenanceItem key={ev.rule_id} ev={ev} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ProvenanceItem({ ev }: { ev: RuleEvaluation }) {
  return (
    <div id={`prov-${ev.rule_id}`} className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="rounded-md border border-slate-200 bg-white px-1.5 py-px text-[10px] font-mono text-slate-600">
          {ev.rule_id}
        </span>
        <ResultBadge result={ev.result} />
      </div>
      <p className="text-[12px] font-semibold text-slate-900">{ev.title}</p>
      <div className="text-[11px] text-slate-500">
        근거: <span className="font-medium text-slate-700">{ev.legal_anchor}</span>
      </div>
      {ev.formula ? (
        <div className="text-[11px] text-slate-500">
          공식: <code className="rounded bg-white px-1 py-px font-mono text-[10.5px] text-slate-700">{ev.formula}</code>
        </div>
      ) : null}
      {Object.keys(ev.computed).length > 0 ? (
        <ul className="mt-1 space-y-0.5">
          {Object.entries(ev.computed).map(([k, v]) => (
            <li
              key={k}
              className="flex justify-between gap-3 text-[11px] text-slate-600"
            >
              <span className="font-mono text-slate-500">{k}</span>
              <span className="tabular font-medium text-slate-800">
                {formatComputedValue(v)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function ResultBadge({ result }: { result: boolean | null }) {
  if (result === true) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-1.5 py-px text-[10px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
        <CheckCircle2 className="h-3 w-3" />
        충족
      </span>
    );
  }
  if (result === false) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-red-50 px-1.5 py-px text-[10px] font-semibold text-red-700 ring-1 ring-red-200">
        <XCircle className="h-3 w-3" />
        미충족
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-1.5 py-px text-[10px] font-semibold text-slate-600 ring-1 ring-slate-200">
      판단불가
    </span>
  );
}

function formatComputedValue(v: number | boolean | string | null): string {
  if (v === null) return "데이터 없음";
  if (typeof v === "boolean") return v ? "예" : "아니오";
  if (typeof v === "number") {
    // 100 만원 이상이면 ',' 구분 + 원 단위 추정
    if (v >= 10000) return `${v.toLocaleString("ko-KR")}원`;
    return v.toLocaleString("ko-KR");
  }
  return String(v);
}
