"use client";

import { FormEvent, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Loader2,
  Sparkles,
  Target,
  XCircle,
} from "lucide-react";

import Button from "@/app/components/ui/Button";
import Input from "@/app/components/ui/Input";
import { recommendLevers } from "@/app/lib/api";
import type {
  AnalyzeRequest,
  RecommendationDTO,
  RecommendResponse,
} from "@/app/lib/types";

interface Props {
  inputs: AnalyzeRequest;
}

const formatNumber = (n: number) =>
  n ? n.toLocaleString("ko-KR", { maximumFractionDigits: 0 }) : "";

const parseNumber = (raw: string) => {
  const cleaned = raw.replace(/,/g, "").trim();
  if (cleaned === "") return 0;
  const v = Number(cleaned);
  return Number.isFinite(v) ? v : 0;
};

export default function RecommendSection({ inputs }: Props) {
  const [open, setOpen] = useState(false);
  const [prepaidStr, setPrepaidStr] = useState(
    formatNumber(Math.round((inputs.income.total_salary || 0) * 0.04))
  );
  const [extraDed, setExtraDed] = useState("");
  const [extraCred, setExtraCred] = useState("");
  const [report, setReport] = useState<RecommendResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setReport(null);
    setLoading(true);
    try {
      const res = await recommendLevers({
        request: inputs,
        baseline_prepaid_tax: parseNumber(prepaidStr),
        baseline_extra_income_deductions: parseNumber(extraDed),
        baseline_extra_tax_credits: parseNumber(extraCred),
        use_standard_tax_credit: true,
      });
      setReport(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "추천 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-slate-700" />
          <span className="text-[14px] font-semibold text-slate-900">
            공제 What-if 추천
          </span>
          <span className="rounded-md bg-slate-100 px-1.5 py-px text-[10px] font-medium uppercase tracking-wider text-slate-500">
            beta
          </span>
        </div>
        {open ? (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-500" />
        )}
      </button>

      {open ? (
        <div className="space-y-4 border-t border-slate-100 p-4">
          <p className="text-[12px] leading-relaxed text-slate-500">
            연금저축·IRP·월세 등 변경 가능한 변수를 한 개씩 적용했을 때 환급액이 얼마나
            늘어나는지 ranking 으로 보여드려요. 자격 미충족 항목은 사유와 함께 뒤에
            표시됩니다.
          </p>

          <form onSubmit={onSubmit} className="space-y-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field label="현재 기납부세액 (원)" small>
                <Input
                  type="text"
                  inputMode="numeric"
                  numeric
                  suffix="원"
                  value={prepaidStr}
                  onChange={(e) =>
                    setPrepaidStr(formatNumber(parseNumber(e.target.value)))
                  }
                />
              </Field>
              <Field label="베이스라인 추가 소득공제 (선택)" small>
                <Input
                  type="text"
                  inputMode="numeric"
                  numeric
                  suffix="원"
                  value={extraDed}
                  onChange={(e) => setExtraDed(e.target.value)}
                />
              </Field>
              <Field label="베이스라인 추가 세액공제 (선택)" small>
                <Input
                  type="text"
                  inputMode="numeric"
                  numeric
                  suffix="원"
                  value={extraCred}
                  onChange={(e) => setExtraCred(e.target.value)}
                />
              </Field>
            </div>

            {error ? (
              <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
                <AlertTriangle className="h-3.5 w-3.5" />
                {error}
              </div>
            ) : null}

            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={loading}
              leftIcon={
                loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )
              }
            >
              {loading ? "계산 중…" : "추천 받기"}
            </Button>
          </form>

          {report ? <Report report={report} /> : null}
        </div>
      ) : null}
    </div>
  );
}

/* ---------- 결과 ---------- */

function Report({ report }: { report: RecommendResponse }) {
  return (
    <div className="space-y-3 border-t border-slate-200 pt-4">
      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          현재 환급/추징
        </span>
        <span
          className={`tabular text-[14px] font-bold ${
            report.baseline_refund > 0
              ? "text-emerald-700"
              : report.baseline_refund < 0
              ? "text-red-700"
              : "text-slate-700"
          }`}
        >
          {report.baseline_refund > 0 ? "+" : ""}
          {report.baseline_refund.toLocaleString("ko-KR")}원
        </span>
      </div>

      <ol className="space-y-2">
        {report.recommendations.map((r, i) => (
          <RecCard key={r.lever.lever_id} rec={r} rank={i + 1} />
        ))}
      </ol>
    </div>
  );
}

function RecCard({ rec, rank }: { rec: RecommendationDTO; rank: number }) {
  const lev = rec.lever;
  const isElig = rec.eligible;
  const deltaTone =
    rec.refund_delta > 0
      ? "text-emerald-700"
      : rec.refund_delta < 0
      ? "text-red-700"
      : "text-slate-500";

  return (
    <li
      className={`rounded-xl border bg-white px-3.5 py-3 ${
        isElig ? "border-slate-200" : "border-slate-200 bg-slate-50/40"
      }`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-baseline gap-1.5">
          <span className="tabular text-[10px] font-semibold text-slate-400">
            #{rank}
          </span>
          <span
            className={`text-[13px] font-semibold ${
              isElig ? "text-slate-900" : "text-slate-500"
            }`}
          >
            {lev.label}
          </span>
        </div>
        {isElig ? (
          <span className={`tabular text-[14px] font-bold ${deltaTone}`}>
            {rec.refund_delta > 0 ? "+" : ""}
            {rec.refund_delta.toLocaleString("ko-KR")}원
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-1.5 py-px text-[10px] font-semibold text-slate-500 ring-1 ring-slate-200">
            <XCircle className="h-3 w-3" />
            미적격
          </span>
        )}
      </div>

      <p
        className={`mt-1 text-[12px] leading-relaxed ${
          isElig ? "text-slate-600" : "text-slate-500"
        }`}
      >
        {lev.description}
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
        <span className="rounded-md bg-slate-50 px-1.5 py-px text-slate-600 ring-1 ring-slate-200">
          {lev.cost_label}
        </span>
        <span className="text-slate-400">근거: {lev.legal_anchor}</span>
        {!isElig && rec.note ? (
          <span className="text-amber-700">사유: {rec.note}</span>
        ) : null}
      </div>
    </li>
  );
}

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
