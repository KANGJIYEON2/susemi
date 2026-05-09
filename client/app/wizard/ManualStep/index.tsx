"use client";

import { Dispatch, FormEvent, SetStateAction } from "react";
import {
  ArrowLeft,
  Heart,
  Home,
  Info,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import Button from "@/app/components/ui/Button";
import Input from "@/app/components/ui/Input";
import Card from "@/app/components/ui/Card";
import Spinner from "@/app/components/ui/Spinner";
import type { FamilyMedicalExpense, ManualInput } from "@/app/lib/types";

const formatNumber = (v: number | null | undefined) =>
  v ? v.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "";

const parseNumber = (raw: string) => Number(raw.replace(/,/g, "")) || 0;

interface Props {
  manualInput: ManualInput;
  setManualInput: Dispatch<SetStateAction<ManualInput>>;
  canAnalyze: boolean;
  loadingAnalyze: boolean;
  analyze: (e?: FormEvent<HTMLFormElement>) => Promise<void>;
  prev: () => void;
}

export default function ManualStep({
  manualInput,
  setManualInput,
  canAnalyze,
  loadingAnalyze,
  analyze,
  prev,
}: Props) {
  const update = (path: string, value: unknown) => {
    setManualInput((prev) => {
      const copy = structuredClone(prev) as Record<string, unknown> & ManualInput;
      if (path.includes(".")) {
        const [obj, key] = path.split(".");
        const target = copy[obj] as Record<string, unknown>;
        target[key] = value;
      } else {
        (copy as Record<string, unknown>)[path] = value;
      }
      return copy;
    });
  };

  const addFamilyMedical = () =>
    setManualInput((prev) => ({
      ...prev,
      family_medical_expenses: [
        ...prev.family_medical_expenses,
        { name: "", amount: 0 },
      ],
    }));

  const updateFamilyMedical = (
    index: number,
    field: keyof FamilyMedicalExpense,
    value: string | number
  ) =>
    setManualInput((prev) => {
      const list = [...prev.family_medical_expenses];
      list[index] = { ...list[index], [field]: value };
      return { ...prev, family_medical_expenses: list };
    });

  const removeFamilyMedical = (index: number) =>
    setManualInput((prev) => ({
      ...prev,
      family_medical_expenses: prev.family_medical_expenses.filter(
        (_, i) => i !== index
      ),
    }));

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        analyze();
      }}
      className="flex flex-col gap-6 px-2 py-6 pb-28"
    >
      <header>
        <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
          Step 03
        </div>
        <h2 className="mt-1 text-[20px] font-semibold text-slate-900">
          간소화에 안 잡힌 비용
        </h2>
        <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
          산후조리·난임·안경·월세처럼 PDF에 없는 항목을 입력하면 분석에 반영합니다.
          <br />
          해당 없으면 비워두셔도 됩니다.
        </p>
      </header>

      <Field label="추가 기부금 (간소화 외)">
        <Input
          type="text"
          inputMode="numeric"
          numeric
          placeholder="0"
          suffix="원"
          value={formatNumber(manualInput.donation_extra)}
          onChange={(e) =>
            update("donation_extra", parseNumber(e.target.value))
          }
        />
      </Field>

      <ToggleCard
        icon={<Home className="h-4 w-4 text-slate-700" />}
        title="월세"
        active={manualInput.rent.has_rent}
        onToggle={(v) => update("rent.has_rent", v)}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="월세 금액 (월)" small>
            <Input
              type="text"
              inputMode="numeric"
              numeric
              suffix="원"
              value={formatNumber(manualInput.rent.monthly_rent)}
              onChange={(e) =>
                update("rent.monthly_rent", parseNumber(e.target.value))
              }
            />
          </Field>
          <Field label="납부 개월 수" small>
            <Input
              type="text"
              inputMode="numeric"
              numeric
              suffix="개월"
              value={formatNumber(manualInput.rent.months_paid)}
              onChange={(e) =>
                update("rent.months_paid", parseNumber(e.target.value))
              }
            />
          </Field>
        </div>
      </ToggleCard>

      <ToggleCard
        icon={<Home className="h-4 w-4 text-slate-700" />}
        title="주택자금대출 상환"
        active={manualInput.housing_loan.has_loan}
        onToggle={(v) => update("housing_loan.has_loan", v)}
      >
        <Field label="이자 상환액" small>
          <Input
            type="text"
            inputMode="numeric"
            numeric
            suffix="원"
            value={formatNumber(manualInput.housing_loan.interest_paid)}
            onChange={(e) =>
              update(
                "housing_loan.interest_paid",
                parseNumber(e.target.value)
              )
            }
          />
        </Field>
      </ToggleCard>

      <Card pad="md" className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Heart className="h-4 w-4 text-slate-700" />
            <span className="text-[14px] font-semibold text-slate-900">
              가족 의료비
            </span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            leftIcon={<Plus className="h-3.5 w-3.5" />}
            onClick={addFamilyMedical}
          >
            추가
          </Button>
        </div>
        {manualInput.family_medical_expenses.length === 0 ? (
          <p className="text-[12px] text-slate-400">
            간소화에 빠진 가족 의료비가 있다면 추가해주세요.
          </p>
        ) : (
          <div className="space-y-2">
            {manualInput.family_medical_expenses.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-2.5 py-2"
              >
                <input
                  className="flex-1 bg-transparent px-1 text-[13px] outline-none placeholder:text-slate-400"
                  placeholder="이름·관계 (예: 어머니)"
                  value={item.name}
                  onChange={(e) =>
                    updateFamilyMedical(i, "name", e.target.value)
                  }
                />
                <input
                  className="w-28 bg-transparent px-1 text-right text-[13px] tabular outline-none placeholder:text-slate-400"
                  placeholder="0"
                  value={formatNumber(item.amount)}
                  onChange={(e) =>
                    updateFamilyMedical(i, "amount", parseNumber(e.target.value))
                  }
                />
                <span className="text-[11px] text-slate-400">원</span>
                <button
                  type="button"
                  className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-red-500"
                  onClick={() => removeFamilyMedical(i)}
                  aria-label="삭제"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="space-y-3">
        <div className="text-[12px] font-medium uppercase tracking-wide text-slate-400">
          기타 추가 항목
        </div>
        {(
          [
            ["glasses_contacts_expense", "안경·렌즈 비용"],
            ["assistive_devices_expense", "보청기·보장구·의료기기"],
            ["infertility_treatment_expense", "난임 시술 의료비"],
            ["preschool_education_expense", "취학 전 아동 교육비"],
            ["school_uniform_and_books_expense", "교복·도서비"],
            ["foreign_education_expense", "국외 교육비"],
            ["childbirth_care_expense", "산후조리원·기타 의료성"],
          ] as const
        ).map(([key, label]) => (
          <Field key={key} label={label} small>
            <Input
              type="text"
              inputMode="numeric"
              numeric
              placeholder="0"
              suffix="원"
              value={formatNumber(manualInput[key] as number | null | undefined)}
              onChange={(e) => update(key, parseNumber(e.target.value))}
            />
          </Field>
        ))}
      </div>

      <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-[13px] text-slate-700">
        <input
          type="checkbox"
          className="h-4 w-4 accent-[#FACC15]"
          checked={manualInput.mid_small_company_reduction_applied}
          onChange={(e) =>
            update("mid_small_company_reduction_applied", e.target.checked)
          }
        />
        중소기업 취업자 감면 신청했어요
      </label>

      <div className="flex items-start gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-[12px] leading-relaxed text-slate-600">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
        입력값은 모두 일회성이고, 분석이 끝나면 서버에 저장되지 않아요.
      </div>

      <div className="sticky bottom-0 -mx-2 mt-2 flex gap-2 border-t border-slate-200 bg-white/95 px-2 py-3 backdrop-blur">
        <Button
          type="button"
          variant="ghost"
          onClick={prev}
          leftIcon={<ArrowLeft className="h-4 w-4" />}
        >
          이전
        </Button>
        <Button
          type="submit"
          variant="cta"
          full
          disabled={!canAnalyze || loadingAnalyze}
          leftIcon={
            loadingAnalyze ? (
              <Spinner size={14} />
            ) : (
              <Sparkles className="h-4 w-4" />
            )
          }
        >
          {loadingAnalyze ? "분석 중…" : "AI 분석 시작"}
        </Button>
      </div>
    </form>
  );
}

/* ---------- 헬퍼 ---------- */

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

function ToggleCard({
  icon,
  title,
  active,
  onToggle,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  active: boolean;
  onToggle: (v: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <Card pad="md" className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-[14px] font-semibold text-slate-900">
            {title}
          </span>
        </div>
        <label className="inline-flex cursor-pointer items-center gap-2 text-[12px] text-slate-600">
          <input
            type="checkbox"
            className="h-4 w-4 accent-[#FACC15]"
            checked={active}
            onChange={(e) => onToggle(e.target.checked)}
          />
          있음
        </label>
      </div>
      {active ? children : null}
    </Card>
  );
}
