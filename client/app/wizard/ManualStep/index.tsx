"use client";

import { Dispatch, SetStateAction, FormEvent } from "react";
import Button from "@/app/components/ui/Button";
import type { ManualInput, FamilyMedicalExpense } from "@/app/lib/types";

// 숫자 → 콤마
const format = (v: number | null | undefined) =>
  v ? v.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "";

// 콤마 제거 후 숫자로 변환
const parse = (value: string) => Number(value.replace(/,/g, "")) || 0;

export default function ManualStep({
  manualInput,
  setManualInput,
  canAnalyze,
  loadingAnalyze,
  analyze,
  prev,
}: {
  manualInput: ManualInput;
  setManualInput: Dispatch<SetStateAction<ManualInput>>;
  canAnalyze: boolean;
  loadingAnalyze: boolean;
  analyze: (e?: FormEvent<HTMLFormElement>) => Promise<void>;
  prev: () => void;
}) {
  // 공통 업데이트 함수

  const update = (path: string, value: any) => {
    setManualInput((prev) => {
      const copy: any = structuredClone(prev);

      if (path.includes(".")) {
        const [obj, key] = path.split(".");
        copy[obj][key] = value;
      } else {
        copy[path] = value;
      }
      return copy;
    });
  };

  // 가족 의료비 배열

  const addFamilyMedical = () => {
    setManualInput((prev) => ({
      ...prev,
      family_medical_expenses: [
        ...prev.family_medical_expenses,
        { name: "", amount: 0 },
      ],
    }));
  };

  const updateFamilyMedical = (
    index: number,
    field: keyof FamilyMedicalExpense,
    value: any
  ) => {
    setManualInput((prev) => {
      const list = [...prev.family_medical_expenses];
      list[index] = { ...list[index], [field]: value };
      return { ...prev, family_medical_expenses: list };
    });
  };

  const removeFamilyMedical = (index: number) => {
    setManualInput((prev) => ({
      ...prev,
      family_medical_expenses: prev.family_medical_expenses.filter(
        (_, i) => i !== index
      ),
    }));
  };

  // UI

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        analyze();
      }}
      className="w-full flex justify-center"
    >
      <div className="flex flex-col w-full max-w-xl px-4 gap-6 pb-24">
        {/* 제목 */}
        <h2 className="text-lg font-semibold text-slate-800">
          ③ 간소화에 안 잡힌 비용 입력
        </h2>

        <p className="text-[14px] text-slate-600 leading-relaxed">
          조리원·난임·안경·월세처럼 국세청 PDF에 없는 항목들을 입력해주세요.
          <br />
          최소 입력만 해도 분석은 가능합니다.
        </p>

        {/* 추가 기부금 */}
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">추가 기부금 (간소화 외)</span>
          <input
            type="text"
            className="input-box"
            placeholder="없으면 비워두세요"
            value={format(manualInput.donation_extra)}
            onChange={(e) => update("donation_extra", parse(e.target.value))}
          />
        </label>

        {/* 월세 */}
        <div className="p-4 border border-[#FFEEC2] bg-[#FFFCF0] rounded-xl space-y-3">
          <div className="flex justify-between text-sm">
            <span className="font-medium">월세를 납부했나요?</span>

            <label className="inline-flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={manualInput.rent.has_rent}
                onChange={(e) => update("rent.has_rent", e.target.checked)}
              />
              월세 있음
            </label>
          </div>

          {manualInput.rent.has_rent && (
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col text-xs">
                월세 금액(월)
                <input
                  type="text"
                  className="input-box"
                  value={format(manualInput.rent.monthly_rent)}
                  onChange={(e) =>
                    update("rent.monthly_rent", parse(e.target.value))
                  }
                />
              </label>

              <label className="flex flex-col text-xs">
                납부 개월 수
                <input
                  type="text"
                  className="input-box"
                  value={format(manualInput.rent.months_paid)}
                  onChange={(e) =>
                    update("rent.months_paid", parse(e.target.value))
                  }
                />
              </label>
            </div>
          )}
        </div>

        {/* 주택자금 대출 */}
        <div className="p-4 border border-[#FFEEC2] bg-[#FFFCF0] rounded-xl space-y-3">
          <div className="flex justify-between text-sm">
            <span className="font-medium">주택자금대출 상환액이 있나요?</span>

            <label className="inline-flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={manualInput.housing_loan.has_loan}
                onChange={(e) =>
                  update("housing_loan.has_loan", e.target.checked)
                }
              />
              대출 있음
            </label>
          </div>

          {manualInput.housing_loan.has_loan && (
            <label className="flex flex-col text-xs">
              이자 상환액
              <input
                type="text"
                className="input-box"
                value={format(manualInput.housing_loan.interest_paid)}
                onChange={(e) =>
                  update("housing_loan.interest_paid", parse(e.target.value))
                }
              />
            </label>
          )}
        </div>

        {/* 가족 의료비 */}
        <div className="space-y-2">
          <p className="font-medium text-sm">가족 의료비 (간소화 누락분)</p>

          {manualInput.family_medical_expenses.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-2 p-2 bg-white border rounded-lg"
            >
              <input
                className="input-box text-xs flex-1"
                value={item.name}
                placeholder="이름 / 관계"
                onChange={(e) => updateFamilyMedical(i, "name", e.target.value)}
              />

              <input
                className="input-box text-xs w-28"
                value={format(item.amount)}
                placeholder="금액"
                onChange={(e) =>
                  updateFamilyMedical(i, "amount", parse(e.target.value))
                }
              />

              <button
                type="button"
                className="text-red-400 text-xs"
                onClick={() => removeFamilyMedical(i)}
              >
                삭제
              </button>
            </div>
          ))}

          <Button
            type="button"
            variant="ghost"
            className="text-xs"
            onClick={addFamilyMedical}
          >
            + 가족 의료비 추가
          </Button>
        </div>

        {/* 기타 항목들 */}
        {[
          ["glasses_contacts_expense", "안경·렌즈 비용"],
          ["assistive_devices_expense", "보청기/보장구/의료기기"],
          ["infertility_treatment_expense", "난임 시술 의료비"],
          ["preschool_education_expense", "취학 전 아동 교육비"],
          ["school_uniform_and_books_expense", "교복·도서비"],
          ["foreign_education_expense", "국외 교육비"],
          ["childbirth_care_expense", "산후조리원·추가 의료성 비용"],
        ].map(([key, label]) => (
          <label key={key} className="flex flex-col text-sm gap-1">
            <span>{label}</span>
            <input
              type="text"
              className="input-box"
              value={format((manualInput as any)[key])}
              onChange={(e) => update(key, parse(e.target.value))}
              placeholder="없으면 비워두세요"
            />
          </label>
        ))}

        {/* 중소기업 감면 */}
        <label className="inline-flex items-center gap-2 text-sm pt-2">
          <input
            type="checkbox"
            checked={manualInput.mid_small_company_reduction_applied}
            onChange={(e) =>
              update("mid_small_company_reduction_applied", e.target.checked)
            }
          />
          중소기업 취업자 감면 신청했어요
        </label>

        {/* 버튼 */}
        <div className="flex gap-3 pt-4">
          <Button type="button" variant="ghost" onClick={prev}>
            ← 이전
          </Button>

          <Button type="submit" full disabled={!canAnalyze || loadingAnalyze}>
            {loadingAnalyze ? "AI 분석 중…" : "AI 분석 보기 →"}
          </Button>
        </div>
      </div>
    </form>
  );
}
