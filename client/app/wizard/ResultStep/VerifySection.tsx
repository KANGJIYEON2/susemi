"use client";

import { FormEvent, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  GitCompareArrows,
  Loader2,
  ScanSearch,
} from "lucide-react";

import Button from "@/app/components/ui/Button";
import Input from "@/app/components/ui/Input";
import { verifyFiling } from "@/app/lib/api";
import type {
  AnalyzeRequest,
  CompanyFiling,
  Severity,
  StepDiff,
  VerificationReport,
} from "@/app/lib/types";

interface Props {
  inputs: AnalyzeRequest;
}

const formatNumber = (n: number) =>
  n ? n.toLocaleString("ko-KR", { maximumFractionDigits: 0 }) : "";

const parseNumber = (raw: string) => {
  const cleaned = raw.replace(/,/g, "").trim();
  if (cleaned === "" || cleaned === "-") return null;
  const v = Number(cleaned);
  return Number.isFinite(v) ? v : null;
};

type FilingForm = {
  determined_tax: string;
  prepaid_tax: string;
  earned_income_deduction: string;
  earned_income_amount: string;
  personal_deduction: string;
  taxable_income: string;
  calculated_tax: string;
  earned_income_tax_credit: string;
  local_income_tax: string;
};

const emptyFiling: FilingForm = {
  determined_tax: "",
  prepaid_tax: "",
  earned_income_deduction: "",
  earned_income_amount: "",
  personal_deduction: "",
  taxable_income: "",
  calculated_tax: "",
  earned_income_tax_credit: "",
  local_income_tax: "",
};

export default function VerifySection({ inputs }: Props) {
  const [open, setOpen] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [form, setForm] = useState<FilingForm>(emptyFiling);
  const [extraDed, setExtraDed] = useState("");
  const [extraCred, setExtraCred] = useState("");
  const [report, setReport] = useState<VerificationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setField = (key: keyof FilingForm) => (raw: string) =>
    setForm((p) => ({ ...p, [key]: raw }));

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setReport(null);

    const det = parseNumber(form.determined_tax);
    const pre = parseNumber(form.prepaid_tax);
    if (det === null || pre === null) {
      setError("결정세액과 기납부세액은 필수입니다.");
      return;
    }

    const filing: CompanyFiling = {
      determined_tax: det,
      prepaid_tax: pre,
      earned_income_deduction: parseNumber(form.earned_income_deduction),
      earned_income_amount: parseNumber(form.earned_income_amount),
      personal_deduction: parseNumber(form.personal_deduction),
      taxable_income: parseNumber(form.taxable_income),
      calculated_tax: parseNumber(form.calculated_tax),
      earned_income_tax_credit: parseNumber(form.earned_income_tax_credit),
      local_income_tax: parseNumber(form.local_income_tax),
    };

    setLoading(true);
    try {
      const res = await verifyFiling({
        request: inputs,
        filing,
        extra_income_deductions: parseNumber(extraDed) ?? 0,
        extra_tax_credits: parseNumber(extraCred) ?? 0,
      });
      setReport(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "검증 실패");
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
          <GitCompareArrows className="h-4 w-4 text-slate-700" />
          <span className="text-[14px] font-semibold text-slate-900">
            회사 신고와 비교
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
            원천징수영수증의 숫자를 넣으면 자체 산식 결과와 단계별로 비교해 드려요.
            결정세액·기납부세액만 채워도 충분합니다. 단정적 표현은 쓰지 않고 차이가
            발생한 단계만 짚어줘요.
          </p>

          <form onSubmit={onSubmit} className="space-y-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <NumField
                label="결정세액 (국세, 원)"
                required
                value={form.determined_tax}
                onChange={setField("determined_tax")}
              />
              <NumField
                label="기납부세액 (원)"
                required
                value={form.prepaid_tax}
                onChange={setField("prepaid_tax")}
              />
            </div>

            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="text-[12px] font-medium text-slate-600 hover:text-slate-900"
            >
              {showAdvanced ? "▾ 다른 단계도 비교 (펼침)" : "▸ 다른 단계도 비교"}
            </button>

            {showAdvanced ? (
              <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/40 p-3">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <NumField
                    label="근로소득공제 (원, 선택)"
                    small
                    value={form.earned_income_deduction}
                    onChange={setField("earned_income_deduction")}
                  />
                  <NumField
                    label="근로소득금액 (원, 선택)"
                    small
                    value={form.earned_income_amount}
                    onChange={setField("earned_income_amount")}
                  />
                  <NumField
                    label="인적공제 합계 (원, 선택)"
                    small
                    value={form.personal_deduction}
                    onChange={setField("personal_deduction")}
                  />
                  <NumField
                    label="과세표준 (원, 선택)"
                    small
                    value={form.taxable_income}
                    onChange={setField("taxable_income")}
                  />
                  <NumField
                    label="산출세액 (원, 선택)"
                    small
                    value={form.calculated_tax}
                    onChange={setField("calculated_tax")}
                  />
                  <NumField
                    label="근로소득세액공제 (원, 선택)"
                    small
                    value={form.earned_income_tax_credit}
                    onChange={setField("earned_income_tax_credit")}
                  />
                  <NumField
                    label="지방소득세 (원, 선택)"
                    small
                    value={form.local_income_tax}
                    onChange={setField("local_income_tax")}
                  />
                </div>
                <div className="grid grid-cols-1 gap-3 border-t border-slate-200 pt-3 sm:grid-cols-2">
                  <NumField
                    label="추가 소득공제 합산 (원, 선택)"
                    small
                    value={extraDed}
                    onChange={setExtraDed}
                  />
                  <NumField
                    label="추가 세액공제 합산 (원, 선택)"
                    small
                    value={extraCred}
                    onChange={setExtraCred}
                  />
                </div>
              </div>
            ) : null}

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
                  <ScanSearch className="h-4 w-4" />
                )
              }
            >
              {loading ? "비교 중…" : "비교 실행"}
            </Button>
          </form>

          {report ? <ReportView report={report} /> : null}
        </div>
      ) : null}
    </div>
  );
}

/* ---------- 폼 헬퍼 ---------- */

function NumField({
  label,
  required,
  small,
  value,
  onChange,
}: {
  label: string;
  required?: boolean;
  small?: boolean;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span
        className={`${
          small ? "text-[12px]" : "text-[13px]"
        } font-medium text-slate-700`}
      >
        {label}
        {required ? <span className="ml-0.5 text-[#EAB308]">*</span> : null}
      </span>
      <Input
        inputMode="numeric"
        numeric
        suffix="원"
        placeholder="0"
        value={formatNumber(parseNumber(value) ?? 0)}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

/* ---------- 결과 ---------- */

function ReportView({ report }: { report: VerificationReport }) {
  const banner = report.has_major_diff
    ? "border-amber-200 bg-amber-50 text-amber-800"
    : "border-emerald-200 bg-emerald-50 text-emerald-800";

  return (
    <div className="space-y-3 border-t border-slate-200 pt-4">
      <div className={`rounded-xl border px-3.5 py-3 text-[12px] leading-relaxed ${banner}`}>
        <div className="mb-1 flex items-center gap-1.5 font-semibold">
          {report.has_major_diff ? (
            <AlertTriangle className="h-3.5 w-3.5" />
          ) : (
            <CheckCircle2 className="h-3.5 w-3.5" />
          )}
          비교 결과
        </div>
        <p>{report.summary}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-3 text-[12px]">
        <Stat label="자체 산식 총 부담" value={report.our_total} />
        <Stat label="회사 신고 총 부담" value={report.company_total} />
        {report.refund_delta !== null ? (
          <div className="col-span-2 mt-1 flex items-baseline justify-between border-t border-slate-200 pt-2 text-[13px]">
            <span className="font-semibold text-slate-700">환급액 차이 (자체 산식 기준)</span>
            <span
              className={`tabular font-bold ${
                report.refund_delta > 0
                  ? "text-emerald-700"
                  : report.refund_delta < 0
                  ? "text-red-700"
                  : "text-slate-700"
              }`}
            >
              {report.refund_delta > 0 ? "+" : ""}
              {report.refund_delta.toLocaleString("ko-KR")}원
            </span>
          </div>
        ) : null}
      </div>

      <div className="space-y-1.5">
        {report.steps.map((s) => (
          <StepRow key={s.name} step={s} />
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </span>
      <span className="mt-0.5 tabular text-[14px] font-bold text-slate-900">
        {value !== null ? `${value.toLocaleString("ko-KR")}원` : "—"}
      </span>
    </div>
  );
}

function StepRow({ step }: { step: StepDiff }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2">
      <SeverityDot severity={step.severity} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[12px] font-semibold text-slate-900">{step.label}</span>
          <DeltaBadge step={step} />
        </div>
        <div className="mt-0.5 flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-[11px] text-slate-500">
          <span>
            우리: <span className="tabular font-medium text-slate-700">{formatMoney(step.our_value)}</span>
          </span>
          <span>
            회사: <span className="tabular font-medium text-slate-700">{formatMoney(step.company_value)}</span>
          </span>
          {step.legal_anchor ? (
            <span className="text-slate-400">· {step.legal_anchor}</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function SeverityDot({ severity }: { severity: Severity }) {
  const tone = {
    match: "bg-emerald-500",
    minor: "bg-amber-400",
    major: "bg-red-500",
    missing: "bg-slate-300",
  }[severity];
  return <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${tone}`} />;
}

function DeltaBadge({ step }: { step: StepDiff }) {
  if (step.severity === "missing") {
    return (
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        skip
      </span>
    );
  }
  if (step.severity === "match") {
    return (
      <span className="inline-flex items-center rounded-md bg-emerald-50 px-1.5 py-px text-[10px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
        일치
      </span>
    );
  }
  const sign = step.delta && step.delta > 0 ? "+" : "";
  const tone =
    step.severity === "major"
      ? "bg-red-50 text-red-700 ring-red-200"
      : "bg-amber-50 text-amber-700 ring-amber-200";
  return (
    <span
      className={`inline-flex items-center rounded-md px-1.5 py-px text-[10px] font-semibold tabular ring-1 ${tone}`}
    >
      Δ {sign}
      {step.delta?.toLocaleString("ko-KR")}원
    </span>
  );
}

function formatMoney(v: number | null): string {
  if (v === null) return "—";
  return `${v.toLocaleString("ko-KR")}원`;
}
