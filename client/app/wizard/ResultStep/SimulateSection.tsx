"use client";

import { FormEvent, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Loader2,
  TrendingUp,
} from "lucide-react";

import Button from "@/app/components/ui/Button";
import Input from "@/app/components/ui/Input";
import { simulateScenario } from "@/app/lib/api";
import type {
  AnalyzeRequest,
  SimulateResponse,
  YearOverride,
  YearProjection,
} from "@/app/lib/types";

const BASELINE_YEAR = 2025;

interface Props {
  inputs: AnalyzeRequest;
}

const formatNumber = (n: number) =>
  n ? n.toLocaleString("ko-KR", { maximumFractionDigits: 0 }) : "";

const parseNumber = (raw: string): number => {
  const cleaned = raw.replace(/,/g, "").trim();
  if (cleaned === "") return 0;
  const v = Number(cleaned);
  return Number.isFinite(v) ? v : 0;
};

export default function SimulateSection({ inputs }: Props) {
  const [open, setOpen] = useState(false);
  const [growthPct, setGrowthPct] = useState("3");
  const [years, setYears] = useState("5");
  const [prepaidStr, setPrepaidStr] = useState(
    formatNumber(Math.round((inputs.income.total_salary || 0) * 0.04))
  );
  const [marriageY, setMarriageY] = useState(""); // n년 후 결혼 (빈값 = 없음)
  const [childY, setChildY] = useState("");
  const [extraDed, setExtraDed] = useState("");
  const [extraCred, setExtraCred] = useState("");

  const [report, setReport] = useState<SimulateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baselineSalary = inputs.income.total_salary || 0;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setReport(null);

    const r = parseNumber(growthPct) / 100;
    const horizon = Math.max(1, Math.min(10, parseNumber(years) || 5));
    const prepaid = parseNumber(prepaidStr);
    const marriageOffset = marriageY.trim() === "" ? null : parseNumber(marriageY);
    const childOffset = childY.trim() === "" ? null : parseNumber(childY);

    if (baselineSalary <= 0) {
      setError("총급여가 비어 있어요. 베이스라인을 다시 입력해 주세요.");
      return;
    }

    // 베이스라인 가족 상태
    let spouseFlag = inputs.dependents.has_spouse;
    let depCount = inputs.dependents.dependents_count || 0;

    const yearOverrides: YearOverride[] = [];
    for (let n = 1; n <= horizon; n++) {
      const projectedSalary = Math.round(baselineSalary * Math.pow(1 + r, n));
      const projectedPrepaid =
        prepaid > 0 ? Math.round(prepaid * Math.pow(1 + r, n)) : 0;

      const notes: string[] = [];
      let setSpouse: boolean | null = null;
      let setDepCount: number | null = null;

      if (marriageOffset !== null && n === marriageOffset && !spouseFlag) {
        spouseFlag = true;
        setSpouse = true;
        notes.push("결혼");
      }
      if (childOffset !== null && n === childOffset) {
        depCount = depCount + 1;
        setDepCount = depCount;
        notes.push("자녀 출생");
      }

      yearOverrides.push({
        year: BASELINE_YEAR + n,
        gross_salary: projectedSalary,
        prepaid_tax: projectedPrepaid > 0 ? projectedPrepaid : null,
        spouse: setSpouse,
        dependents_count: setDepCount,
        note: notes.length > 0 ? notes.join(" + ") : null,
      });
    }

    setLoading(true);
    try {
      const res = await simulateScenario({
        baseline_request: inputs,
        baseline_year: BASELINE_YEAR,
        baseline_prepaid_tax: prepaid,
        use_standard_tax_credit: true,
        extra_income_deductions: parseNumber(extraDed),
        extra_tax_credits: parseNumber(extraCred),
        years: yearOverrides,
      });
      setReport(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "시뮬레이션 실패");
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
          <TrendingUp className="h-4 w-4 text-slate-700" />
          <span className="text-[14px] font-semibold text-slate-900">
            5년 What-if 시뮬레이션
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
            연봉 인상률과 인생 이벤트(결혼·자녀)를 가정해 향후 N년의 연도별 결정세액·환급액을
            추산합니다. 모든 연도는 현재 세율표(2025)를 사용해요 — 미래 세법 변경은 반영되지
            않습니다.
          </p>

          <form onSubmit={onSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Field label="연봉 인상률 (%)" small>
                <Input
                  type="text"
                  inputMode="decimal"
                  value={growthPct}
                  onChange={(e) => setGrowthPct(e.target.value)}
                />
              </Field>
              <Field label="기간 (1~10년)" small>
                <Input
                  type="text"
                  inputMode="numeric"
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
                />
              </Field>
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
              <Field label="베이스라인 연봉" small>
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-right text-[13px] tabular text-slate-700">
                  {formatNumber(baselineSalary) || "—"} 원
                </div>
              </Field>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-3">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                인생 이벤트 (선택)
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="결혼 시점 (n년 후, 비우면 없음)" small>
                  <Input
                    type="text"
                    inputMode="numeric"
                    placeholder="2"
                    value={marriageY}
                    onChange={(e) => setMarriageY(e.target.value)}
                  />
                </Field>
                <Field label="자녀 출생 시점 (n년 후)" small>
                  <Input
                    type="text"
                    inputMode="numeric"
                    placeholder="3"
                    value={childY}
                    onChange={(e) => setChildY(e.target.value)}
                  />
                </Field>
              </div>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="추가 소득공제 (원, 매년 동일 가정)" small>
                  <Input
                    type="text"
                    inputMode="numeric"
                    numeric
                    suffix="원"
                    value={extraDed}
                    onChange={(e) => setExtraDed(e.target.value)}
                  />
                </Field>
                <Field label="추가 세액공제 (원)" small>
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
                  <TrendingUp className="h-4 w-4" />
                )
              }
            >
              {loading ? "계산 중…" : "시뮬레이션 실행"}
            </Button>
          </form>

          {report ? <ReportView report={report} /> : null}
        </div>
      ) : null}
    </div>
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

/* ---------- 결과 ---------- */

function ReportView({ report }: { report: SimulateResponse }) {
  const allRows: YearProjection[] = [report.baseline, ...report.projections];

  const cumTone =
    report.cumulative_refund > 0
      ? "text-emerald-700"
      : report.cumulative_refund < 0
      ? "text-red-700"
      : "text-slate-700";

  return (
    <div className="space-y-3 border-t border-slate-200 pt-4">
      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-3 text-[12px]">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            누적 환급/추징 ({allRows.length}년치)
          </span>
          <span className={`tabular text-[15px] font-bold ${cumTone}`}>
            {report.cumulative_refund > 0 ? "+" : ""}
            {report.cumulative_refund.toLocaleString("ko-KR")}원
          </span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">총 부담세액 누계</span>
          <span className="tabular text-[12px] font-medium text-slate-700">
            {report.cumulative_total_tax.toLocaleString("ko-KR")}원
          </span>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full min-w-[520px] text-[12px]">
          <thead className="bg-slate-50 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-3 py-2">연도</th>
              <th className="px-3 py-2 text-right">연봉</th>
              <th className="px-3 py-2 text-right">결정세액</th>
              <th className="px-3 py-2 text-right">총 부담</th>
              <th className="px-3 py-2 text-right">환급/추징</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {allRows.map((p, i) => (
              <tr key={p.year} className={i === 0 ? "bg-white" : "bg-white"}>
                <td className="px-3 py-2">
                  <div className="font-semibold text-slate-900">{p.year}</div>
                  {p.note ? (
                    <div className="text-[10px] text-slate-500">{p.note}</div>
                  ) : null}
                </td>
                <td className="px-3 py-2 text-right tabular text-slate-700">
                  {p.inputs_used.gross_salary.toLocaleString("ko-KR")}
                </td>
                <td className="px-3 py-2 text-right tabular text-slate-700">
                  {p.result.determined_tax.toLocaleString("ko-KR")}
                </td>
                <td className="px-3 py-2 text-right tabular text-slate-700">
                  {p.result.total_tax.toLocaleString("ko-KR")}
                </td>
                <td
                  className={`px-3 py-2 text-right tabular font-semibold ${
                    p.result.refund_or_owed > 0
                      ? "text-emerald-700"
                      : p.result.refund_or_owed < 0
                      ? "text-red-700"
                      : "text-slate-700"
                  }`}
                >
                  {p.result.refund_or_owed > 0 ? "+" : ""}
                  {p.result.refund_or_owed.toLocaleString("ko-KR")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] leading-relaxed text-slate-400">
        ※ 모든 연도가 2025년 세율표를 사용합니다. 실제 미래에는 누진구간·공제율 변경 가능.
      </p>
    </div>
  );
}
