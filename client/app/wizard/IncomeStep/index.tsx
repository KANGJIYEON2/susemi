"use client";

import { ChangeEvent, Dispatch, SetStateAction } from "react";
import { ArrowLeft, ArrowRight, Home, Lightbulb, Users, Wallet } from "lucide-react";
import Button from "@/app/components/ui/Button";
import Input from "@/app/components/ui/Input";
import Card from "@/app/components/ui/Card";
import type { Conditions, Dependents, Income } from "@/app/lib/types";

const formatNumber = (n: number) =>
  n ? n.toLocaleString("ko-KR", { maximumFractionDigits: 0 }) : "";

const parseNumber = (raw: string) => {
  const cleaned = raw.replace(/,/g, "").trim();
  return cleaned === "" ? 0 : Number(cleaned) || 0;
};

interface Props {
  income: Income;
  setIncome: Dispatch<SetStateAction<Income>>;
  dependents: Dependents;
  setDependents: Dispatch<SetStateAction<Dependents>>;
  conditions: Conditions;
  setConditions: Dispatch<SetStateAction<Conditions>>;
  canNext: boolean;
  next: () => void;
  prev: () => void;
}

export default function IncomeStep({
  income,
  setIncome,
  dependents,
  setDependents,
  conditions,
  setConditions,
  canNext,
  next,
  prev,
}: Props) {
  const onNum =
    <T extends object>(setter: Dispatch<SetStateAction<T>>, key: keyof T) =>
    (e: ChangeEvent<HTMLInputElement>) => {
      const num = parseNumber(e.target.value);
      setter((prev) => ({ ...prev, [key]: num }) as T);
    };

  const onBool =
    <T extends object>(setter: Dispatch<SetStateAction<T>>, key: keyof T) =>
    (e: ChangeEvent<HTMLInputElement>) =>
      setter((prev) => ({ ...prev, [key]: e.target.checked }) as T);

  return (
    <form
      className="flex flex-col gap-8 px-2 py-6 pb-24"
      onSubmit={(e) => {
        e.preventDefault();
        if (canNext) next();
      }}
    >
      <SectionHeader
        icon={<Wallet className="h-4 w-4 text-slate-700" />}
        title="소득 정보"
        sub="회사에서 받은 연봉(세전)을 기준으로 입력해주세요."
      />
      <div className="space-y-3">
        <Field label="총급여 (연봉, 세전)" required>
          <Input
            type="text"
            inputMode="numeric"
            numeric
            placeholder="0"
            suffix="원"
            value={formatNumber(income.total_salary)}
            onChange={onNum(setIncome, "total_salary")}
          />
        </Field>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="비과세 급여 (선택)">
            <Input
              type="text"
              inputMode="numeric"
              numeric
              placeholder="0"
              suffix="원"
              value={formatNumber(income.non_taxable ?? 0)}
              onChange={onNum(setIncome, "non_taxable")}
            />
          </Field>
          <Field label="상여금 (선택)">
            <Input
              type="text"
              inputMode="numeric"
              numeric
              placeholder="0"
              suffix="원"
              value={formatNumber(income.bonus ?? 0)}
              onChange={onNum(setIncome, "bonus")}
            />
          </Field>
        </div>
      </div>

      <Divider />

      <SectionHeader
        icon={<Users className="h-4 w-4 text-slate-700" />}
        title="가족 · 인적공제"
        sub="해당 없으면 비워두셔도 돼요."
      />

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        <CheckRow
          checked={dependents.has_spouse}
          label="배우자 있음"
          onChange={onBool(setDependents, "has_spouse")}
        />
        <CheckRow
          checked={dependents.single_parent}
          label="한부모"
          onChange={onBool(setDependents, "single_parent")}
        />
        <CheckRow
          checked={dependents.female_householder}
          label="부녀자 공제"
          onChange={onBool(setDependents, "female_householder")}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Field label="부양가족 수" small>
          <Input
            type="text"
            inputMode="numeric"
            numeric
            placeholder="0"
            suffix="명"
            value={formatNumber(dependents.dependents_count)}
            onChange={onNum(setDependents, "dependents_count")}
          />
        </Field>
        <Field label="장애인 가족 수" small>
          <Input
            type="text"
            inputMode="numeric"
            numeric
            placeholder="0"
            suffix="명"
            value={formatNumber(dependents.disabled_count)}
            onChange={onNum(setDependents, "disabled_count")}
          />
        </Field>
        <Field label="경로우대 (만 70세 ↑)" small>
          <Input
            type="text"
            inputMode="numeric"
            numeric
            placeholder="0"
            suffix="명"
            value={formatNumber(dependents.senior_count)}
            onChange={onNum(setDependents, "senior_count")}
          />
        </Field>
      </div>

      <Card accent pad="sm" className="bg-[#FFFBEA]">
        <div className="mb-2 flex items-center gap-1.5 text-[12px] font-semibold text-slate-900">
          <Lightbulb className="h-3.5 w-3.5 text-[#CA8A04]" />
          인적공제 한 줄 정리
        </div>
        <ul className="space-y-1 text-[12px] leading-relaxed text-slate-600">
          <li>· 부양가족 소득금액 100만원 이하(근로 총급여 500만원 이하 동일 인정).</li>
          <li>· 나이요건: 20세 이하 · 60세 이상. 장애인은 나이 제한 없음.</li>
          <li>· 자녀세액공제 받는 자녀와 인적공제 중복 불가.</li>
        </ul>
      </Card>

      <Divider />

      <SectionHeader
        icon={<Home className="h-4 w-4 text-slate-700" />}
        title="세법 요건 체크"
        sub="해당하는 항목만 체크해주세요."
      />
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {(
          [
            ["householder", "세대주"],
            ["no_house", "무주택"],
            ["lease_contract", "임대차 계약 있음"],
            ["has_loan", "주택자금 대출 있음"],
            ["child_education", "자녀 교육비 있음"],
            ["self_education", "본인 교육비 있음"],
            ["mid_small_company_worker", "중소기업 취업자 감면 대상"],
          ] as const
        ).map(([key, label]) => (
          <CheckRow
            key={key}
            checked={Boolean(conditions[key])}
            label={label}
            onChange={onBool(setConditions, key)}
          />
        ))}
      </div>

      <div className="sticky bottom-0 -mx-2 mt-4 flex gap-2 border-t border-slate-200 bg-white/95 px-2 py-3 backdrop-blur">
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
          variant="primary"
          full
          disabled={!canNext}
          rightIcon={<ArrowRight className="h-4 w-4" />}
        >
          다음 단계로
        </Button>
      </div>
    </form>
  );
}

/* ---------- 내부 헬퍼 컴포넌트 ---------- */

function SectionHeader({
  icon,
  title,
  sub,
}: {
  icon: React.ReactNode;
  title: string;
  sub?: string;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-lg bg-slate-50">
        {icon}
      </div>
      <div className="min-w-0">
        <h3 className="text-[15px] font-semibold text-slate-900">{title}</h3>
        {sub ? (
          <p className="mt-0.5 text-[12px] text-slate-500">{sub}</p>
        ) : null}
      </div>
    </div>
  );
}

function Field({
  label,
  required,
  small,
  children,
}: {
  label: string;
  required?: boolean;
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
        {required ? <span className="ml-0.5 text-[#EAB308]">*</span> : null}
      </span>
      {children}
    </label>
  );
}

function CheckRow({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label
      className={`flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-[13px] cursor-pointer transition-colors ${
        checked
          ? "border-slate-900 bg-slate-900 text-white"
          : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="h-4 w-4 cursor-pointer accent-[#FACC15]"
      />
      <span className="select-none">{label}</span>
    </label>
  );
}

function Divider() {
  return <div className="h-px w-full bg-slate-100" />;
}
