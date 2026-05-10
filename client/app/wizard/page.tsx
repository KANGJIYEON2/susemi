"use client";

import {
  ChangeEvent,
  Dispatch,
  FormEvent,
  SetStateAction,
  useEffect,
  useMemo,
  useState,
} from "react";

import AppHeader from "@/app/components/AppHeader";
import ReportLayout from "@/app/components/report/ReportLayout";

import { analyzeTax, parsePdf } from "@/app/lib/api";
import {
  loadAnalysis,
  saveAnalysis,
  type StoredAnalysis,
} from "@/app/lib/storage";

const RESUME_SLOT_KEY = "susemi.resume";
import type {
  AnalyzeResponse,
  Conditions,
  Dependents,
  Income,
  ManualInput,
  ParsedPdfData,
} from "@/app/lib/types";

import IncomeStep from "./IncomeStep";
import IntroStep from "./IntroStep";
import ManualStep from "./ManualStep";
import PdfStep from "./PdfStep";
import ResultStep from "./ResultStep";

const TOTAL_STEPS = 4;
export type Setter<T> = Dispatch<SetStateAction<T>>;

const defaultIncome: Income = { total_salary: 0, non_taxable: 0, bonus: 0 };
const defaultDependents: Dependents = {
  has_spouse: false,
  dependents_count: 0,
  disabled_count: 0,
  senior_count: 0,
  single_parent: false,
  female_householder: false,
};
const defaultConditions: Conditions = {
  householder: true,
  no_house: true,
  lease_contract: false,
  has_loan: false,
  child_education: false,
  self_education: false,
  mid_small_company_worker: false,
};
const defaultParsedPdf: ParsedPdfData = {
  credit_card: 0,
  debit_card: 0,
  cash_receipt: 0,
  medical_expense: 0,
  severe_medical_for_disabled: 0,
  insurance: 0,
  pension_saving: 0,
  retirement_pension: 0,
  donation_total: 0,
  housing_loan_interest: 0,
  rent_in_pdf: 0,
  tax_credit_type: "unknown",
};
const defaultManualInput: ManualInput = {
  donation_extra: 0,
  rent: { has_rent: false, monthly_rent: 0, months_paid: 0 },
  housing_loan: { has_loan: false, interest_paid: 0 },
  family_medical_expenses: [],
  glasses_contacts_expense: 0,
  assistive_devices_expense: 0,
  infertility_treatment_expense: 0,
  preschool_education_expense: 0,
  school_uniform_and_books_expense: 0,
  foreign_education_expense: 0,
  childbirth_care_expense: 0,
  mid_small_company_reduction_applied: false,
};

export default function WizardPage() {
  const [step, setStep] = useState(0);

  const [income, setIncome] = useState<Income>(defaultIncome);
  const [dependents, setDependents] = useState<Dependents>(defaultDependents);
  const [conditions, setConditions] = useState<Conditions>(defaultConditions);
  const [parsedPdf, setParsedPdf] = useState<ParsedPdfData | null>(null);
  const [manualInput, setManualInput] =
    useState<ManualInput>(defaultManualInput);

  const [pdfMissingFields, setPdfMissingFields] = useState<string[]>([]);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const goStep = (n: number) => setStep(n);

  const canNextFromIncome = useMemo(
    () => income.total_salary > 0,
    [income.total_salary]
  );
  const canAnalyze = useMemo(
    () => income.total_salary > 0,
    [income.total_salary]
  );

  const handlePdfUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoadingPdf(true);
    setParsedPdf(null);
    setPdfMissingFields([]);
    try {
      const res = await parsePdf(file);
      setParsedPdf(res.parsed_pdf);
      setPdfMissingFields(res.missing_fields ?? []);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "PDF 분석 중 오류가 발생했어요.";
      alert(msg);
    } finally {
      setLoadingPdf(false);
    }
  };

  const handleAnalyze = async (e?: FormEvent<HTMLFormElement>) => {
    e?.preventDefault();
    if (!canAnalyze) return;
    setLoadingAnalyze(true);
    setAnalyzeError(null);
    setResult(null);
    try {
      const payload = {
        income,
        dependents,
        conditions,
        parsed_pdf: parsedPdf ?? defaultParsedPdf,
        manual_input: manualInput,
      };
      const res = await analyzeTax(payload);
      setResult(res);
      goStep(4);

      // 클라이언트 IndexedDB 에 자동 저장 (fire-and-forget — 실패해도 분석 흐름 영향 X)
      saveAnalysis({
        year: 2025,
        inputs: payload,
        result: res,
      }).catch(() => {
        /* 저장 실패는 무시 (private browsing / quota / SSR 등) */
      });
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "분석 중 오류가 발생했어요.";
      setAnalyzeError(msg);
    } finally {
      setLoadingAnalyze(false);
    }
  };

  // 저장된 과거 분석을 불러와 결과 페이지로 이동
  const handleResume = (loaded: StoredAnalysis) => {
    setIncome(loaded.inputs.income);
    setDependents(loaded.inputs.dependents);
    setConditions(loaded.inputs.conditions);
    setParsedPdf(loaded.inputs.parsed_pdf);
    setManualInput(loaded.inputs.manual_input);
    setResult(loaded.result);
    setAnalyzeError(null);
    setPdfMissingFields([]);
    goStep(4);
  };

  // /history 에서 "보기" 클릭 시 sessionStorage 로 id 전달 → 마운트 시 resume
  useEffect(() => {
    if (typeof window === "undefined") return;
    let cancelled = false;
    const id = window.sessionStorage.getItem(RESUME_SLOT_KEY);
    if (!id) return;
    window.sessionStorage.removeItem(RESUME_SLOT_KEY);
    loadAnalysis(id).then((loaded) => {
      if (!cancelled && loaded) handleResume(loaded);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const restart = () => {
    setIncome(defaultIncome);
    setDependents(defaultDependents);
    setConditions(defaultConditions);
    setParsedPdf(null);
    setManualInput(defaultManualInput);
    setResult(null);
    setAnalyzeError(null);
    setPdfMissingFields([]);
    setStep(0);
  };

  // 모바일: step 4 미만이면 위저드만, step 4 면 결과 패널 + 리포트
  const showReportMobile = step === 4;

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader step={step} totalSteps={TOTAL_STEPS} />

      <main className="mx-auto flex w-full max-w-[1400px] flex-col md:flex-row md:items-stretch">
        {/* 좌측: 위저드 */}
        <section
          className={`w-full bg-white md:w-[45%] md:border-r md:border-slate-200 ${
            showReportMobile ? "hidden md:block" : "block"
          }`}
        >
          <div className="mx-auto w-full max-w-[560px] px-5">
            {step === 0 && (
            <IntroStep onStart={() => goStep(1)} onResume={handleResume} />
          )}

            {step === 1 && (
              <IncomeStep
                income={income}
                setIncome={setIncome}
                dependents={dependents}
                setDependents={setDependents}
                conditions={conditions}
                setConditions={setConditions}
                canNext={canNextFromIncome}
                next={() => goStep(2)}
                prev={() => goStep(0)}
              />
            )}

            {step === 2 && (
              <PdfStep
                parsedPdf={parsedPdf}
                missingFields={pdfMissingFields}
                loadingPdf={loadingPdf}
                onUpload={handlePdfUpload}
                next={() => goStep(3)}
                prev={() => goStep(1)}
              />
            )}

            {step === 3 && (
              <ManualStep
                manualInput={manualInput}
                setManualInput={setManualInput}
                canAnalyze={canAnalyze}
                loadingAnalyze={loadingAnalyze}
                analyze={handleAnalyze}
                prev={() => goStep(2)}
              />
            )}

            {step === 4 && (
              <ResultStep
                restart={restart}
                inputs={{
                  income,
                  dependents,
                  conditions,
                  parsed_pdf: parsedPdf ?? defaultParsedPdf,
                  manual_input: manualInput,
                }}
              />
            )}
          </div>
        </section>

        {/* 우측(데스크톱) / 결과 단계(모바일): 리포트 패널.
            report-print 클래스: @media print 시 이 영역만 출력 (globals.css 참조) */}
        <section
          className={`w-full bg-slate-50 md:w-[55%] ${
            showReportMobile ? "block" : "hidden md:block"
          }`}
        >
          <div className="report-print sticky top-14 mx-auto w-full max-w-[640px] px-5 py-6 md:py-8">
            <ReportLayout
              data={result}
              loading={loadingAnalyze}
              error={analyzeError}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
