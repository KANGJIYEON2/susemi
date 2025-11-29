"use client";

import { ChangeEvent, Dispatch, SetStateAction } from "react";
import Button from "@/app/components/ui/Button";
import type { Income, Dependents, Conditions } from "@/app/lib/types";

// 숫자 포맷 + UI 클래스
const format = (n: number) =>
  n.toLocaleString("ko-KR", { maximumFractionDigits: 0 });

const inputClass =
  "w-full px-4 py-3.5 rounded-xl bg-[#FFFDF5] border border-[#E8DDBF] text-sm focus:outline-none focus:ring-2 focus:ring-[#FFD84D] transition";

const checkClass =
  "w-4 h-4 rounded border-[#E4D7B0] text-[#FFD84D] focus:ring-[#FFD84D]";

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
}: {
  income: Income;
  setIncome: Dispatch<SetStateAction<Income>>;
  dependents: Dependents;
  setDependents: Dispatch<SetStateAction<Dependents>>;
  conditions: Conditions;
  setConditions: Dispatch<SetStateAction<Conditions>>;
  canNext: boolean;
  next: () => void;
  prev: () => void;
}) {
  // 숫자 핸들러
  const onNum =
    <T,>(setter: Dispatch<SetStateAction<T>>, key: keyof T) =>
    (e: ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value.replace(/,/g, "");
      const num = raw === "" ? 0 : Number(raw);
      setter((prev: any) => ({ ...prev, [key]: num }));
    };

  // boolean 핸들러
  const onBool =
    <T,>(setter: Dispatch<SetStateAction<T>>, key: keyof T) =>
    (e: ChangeEvent<HTMLInputElement>) =>
      setter((prev: any) => ({ ...prev, [key]: e.target.checked }));

  return (
    <form
      className="flex flex-col gap-8 pb-20"
      onSubmit={(e) => {
        e.preventDefault();
        if (canNext) next();
      }}
    >
      {/* 소득 정보 */}
      <section>
        <h3 className="text-base font-semibold text-slate-800 mb-3">
          💰 소득 정보
        </h3>

        <div className="space-y-4 text-sm">
          {/* 총급여 */}
          <div>
            <label className="font-medium">총급여 (연봉, 세전)</label>
            <input
              type="text"
              className={inputClass}
              placeholder="예: 45,000,000"
              value={income.total_salary ? format(income.total_salary) : ""}
              onChange={onNum(setIncome, "total_salary")}
            />
          </div>

          {/* 비과세 */}
          <div>
            <label className="text-slate-600">비과세 급여 (선택)</label>
            <input
              type="text"
              className={inputClass}
              placeholder="없으면 0"
              value={income.non_taxable ? format(income.non_taxable) : ""}
              onChange={onNum(setIncome, "non_taxable")}
            />
          </div>

          {/* 상여금 */}
          <div>
            <label className="text-slate-600">상여금 (선택)</label>
            <input
              type="text"
              className={inputClass}
              placeholder="없으면 0"
              value={income.bonus ? format(income.bonus) : ""}
              onChange={onNum(setIncome, "bonus")}
            />
          </div>
        </div>
      </section>

      {/* 인적공제 */}

      <section>
        <h3 className="text-base font-semibold text-slate-800 mb-3">
          👨‍👩‍👧 가족 & 인적공제
        </h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className={checkClass}
              checked={dependents.has_spouse}
              onChange={onBool(setDependents, "has_spouse")}
            />
            배우자 있음
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className={checkClass}
              checked={dependents.single_parent}
              onChange={onBool(setDependents, "single_parent")}
            />
            한부모
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className={checkClass}
              checked={dependents.female_householder}
              onChange={onBool(setDependents, "female_householder")}
            />
            부녀자 공제
          </label>
        </div>

        {/* 숫자 입력 */}
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div>
            <label className="text-sm text-slate-600">부양가족 수</label>
            <input
              type="text"
              className={inputClass}
              value={
                dependents.dependents_count
                  ? format(dependents.dependents_count)
                  : ""
              }
              onChange={onNum(setDependents, "dependents_count")}
            />
          </div>

          <div>
            <label className="text-sm text-slate-600">장애인 가족 수</label>
            <input
              type="text"
              className={inputClass}
              value={
                dependents.disabled_count
                  ? format(dependents.disabled_count)
                  : ""
              }
              onChange={onNum(setDependents, "disabled_count")}
            />
          </div>

          <div>
            <label className="text-sm text-slate-600">경로우대 (70세 ↑)</label>
            <input
              type="text"
              className={inputClass}
              value={
                dependents.senior_count ? format(dependents.senior_count) : ""
              }
              onChange={onNum(setDependents, "senior_count")}
            />
          </div>
        </div>
        <div className="bg-[#FFF7D1] border border-[#F5DE9D] rounded-xl px-4 py-3 text-[13px] text-slate-700 leading-relaxed mt-4">
          <p className="font-semibold mb-2">💡 인적공제 TIP</p>

          <ul className="list-disc pl-4 space-y-1">
            <li>
              인적공제는 <b>연 소득금액 100만원 이하</b>인 경우만 가능합니다.
            </li>
            <li>
              근로자의 경우 <b>총급여 500만원 이하</b>면 소득금액 100만원 이하로
              인정됩니다.
            </li>
            <li>
              부양가족 나이요건: <b>20세 이하 · 60세 이상</b>만 공제 대상입니다.
            </li>
            <li>
              <b>장애인은 나이 제한 없음</b>, 소득요건만 충족하면 가능해요.
            </li>
            <li>
              자녀세액공제 받는 자녀는 <b>인적공제 중복 불가</b>입니다.
            </li>
          </ul>
        </div>
      </section>

      {/* 세법 요건 체크 */}
      <section>
        <h3 className="text-base font-semibold text-slate-800 mb-3">
          🏠 세법 요건 체크
        </h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          {/* boolean 7개 */}
          {[
            ["householder", "세대주"],
            ["no_house", "무주택"],
            ["lease_contract", "임대차 계약 있음"],
            ["has_loan", "주택대출 있음"],
            ["child_education", "자녀 교육비 있음"],
            ["self_education", "본인 교육비 있음"],
            ["mid_small_company_worker", "중소기업 취업자 감면 대상"],
          ].map(([key, label]) => (
            <label key={key} className="flex items-center gap-2">
              <input
                type="checkbox"
                className={checkClass}
                checked={(conditions as any)[key]}
                onChange={onBool(setConditions, key as keyof Conditions)}
              />
              {label}
            </label>
          ))}
        </div>
      </section>

      {/* 버튼 */}
      <div className="flex gap-2 mt-4">
        <Button type="button" variant="ghost" onClick={prev}>
          ← 이전
        </Button>
        <Button type="submit" full disabled={!canNext}>
          다음 단계로 →
        </Button>
      </div>
    </form>
  );
}
