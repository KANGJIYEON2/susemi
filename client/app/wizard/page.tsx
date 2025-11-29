"use client";

import {
  useState,
  useMemo,
  ChangeEvent,
  FormEvent,
  Dispatch,
  SetStateAction,
} from "react";

import Button from "@/app/components/ui/Button";
import Spinner from "@/app/components/ui/Spinner";
import ProgressHeader from "@/app/components/ProgressHeader";
import ReportLayout from "@/app/components/report/ReportLayout";

import { analyzeTax, parsePdf } from "@/app/lib/api";
import type {
  Income,
  Dependents,
  Conditions,
  ParsedPdfData,
  ManualInput,
  AnalyzeResponse,
} from "@/app/lib/types";

import IntroStep from "./IntroStep";
import IncomeStep from "./IncomeStep";
import PdfStep from "./PdfStep";
import ManualStep from "./ManualStep";
import ResultStep from "./ResultStep";

const TOTAL_STEPS = 4;
export type Setter<T> = Dispatch<SetStateAction<T>>;

// -------- 기본 값들 --------
const defaultIncome: Income = {
  total_salary: 0,
  non_taxable: 0,
  bonus: 0,
};

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
  rent: {
    has_rent: false,
    monthly_rent: 0,
    months_paid: 0,
  },
  housing_loan: {
    has_loan: false,
    interest_paid: 0,
  },
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

  // PDF 업로드
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
    } catch (err: any) {
      alert(err.message ?? "PDF 분석 중 오류가 발생했어요.");
    } finally {
      setLoadingPdf(false);
    }
  };

  // 분석 요청
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
    } catch (err: any) {
      setAnalyzeError(err.message ?? "분석 중 오류가 발생했어요.");
    } finally {
      setLoadingAnalyze(false);
    }
  };

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

  return (
    <div className="flex flex-col md:flex-row max-w-[1400px] mx-auto w-full min-h-screen">
      {/* 👈 왼쪽: 위저드 패널 */}
      <div className="w-full md:w-[45%] max-w-[600px] mx-auto flex flex-col border-r border-[#FFEEC2] bg-[#FFFDF5]">
        <ProgressHeader step={step} totalSteps={TOTAL_STEPS} />

        <div className="flex-1 px-6 py-5 overflow-y-auto">
          {step === 0 && <IntroStep onStart={() => goStep(1)} />}

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

          {step === 4 && <ResultStep restart={restart} />}
        </div>
      </div>

      {/* 👉 오른쪽: 리포트 패널 (PC 전용) */}
      <div className="hidden md:flex w-[55%] bg-[#FFFCF0] flex-col">
        <div className="flex items-center gap-3 px-6 pt-5 pb-3 border-b border-[#FFEEC2] bg-[#FFF9E6]">
          <div className="relative w-9 h-9">
            <img
              src="/susemi.png"
              alt="수세미"
              className="w-full h-full object-contain"
            />
          </div>

          <div className="flex flex-col">
            <span className="text-xs font-semibold text-slate-800">
              수세미 리포트
            </span>
            <span className="text-[10px] text-slate-500">
              연말정산 Why 분석 요약
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="bg-white/90 border border-[#EFE7C8] rounded-2xl shadow-sm px-5 py-4">
            <ReportLayout
              data={result}
              loading={loadingAnalyze}
              error={analyzeError}
            />
          </div>
        </div>
      </div>

      {/* 📱 모바일 리포트 */}
      <div className="md:hidden w-full border-t border-[#FFF2C6] bg-[#FFFCF0] px-4 py-3">
        <div className="bg-white/90 border border-[#EFE7C8] rounded-2xl shadow-sm px-4 py-3">
          <ReportLayout
            data={result}
            loading={loadingAnalyze}
            error={analyzeError}
          />
        </div>
      </div>
    </div>
  );
}
