"use client";

import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Lightbulb,
  Loader2,
  Sparkles,
} from "lucide-react";
import { AnalyzeResponse } from "@/app/lib/types";

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
          <section
            key={s.id}
            className="rounded-2xl border border-slate-200 bg-white p-5"
          >
            <div className="flex items-baseline gap-2">
              <span className="tabular text-[11px] font-semibold text-slate-400">
                {String(idx + 1).padStart(2, "0")}
              </span>
              <h2 className="text-[15px] font-semibold text-slate-900">
                {s.title}
              </h2>
            </div>

            {s.highlight ? (
              <p className="mt-2 text-[13px] font-medium leading-relaxed text-slate-800">
                {s.highlight}
              </p>
            ) : null}

            {s.detail ? (
              <p className="mt-2 whitespace-pre-line text-[13px] leading-7 text-slate-600">
                {s.detail}
              </p>
            ) : null}

            {s.tips && s.tips.length > 0 ? (
              <div className="mt-4 rounded-xl border border-[#FDE68A] bg-[#FFFBEA] p-3.5">
                <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold text-[#854D0E]">
                  <Lightbulb className="h-3 w-3" />
                  TIP
                </div>
                <ul className="space-y-1">
                  {s.tips.map((t, i) => (
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
          </section>
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
