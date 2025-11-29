"use client";

type Props = {
  step: number;
  totalSteps: number;
};

const STEP_LABELS = [
  "시작하기",
  "소득 · 가족 정보",
  "PDF 간소화 자료",
  "추가 입력",
  "AI 분석 결과",
];

export default function ProgressHeader({ step, totalSteps }: Props) {
  const progress = Math.round((step / totalSteps) * 100);

  return (
    <div className="w-full px-5 py-4 border-b border-[#FFEEC2] bg-white/80 flex items-center justify-between gap-4 backdrop-blur-sm">
      <div className="flex flex-col">
        <span className="text-[11px] uppercase tracking-wide text-slate-400">
          수세미 진행률
        </span>
        <div className="flex items-baseline gap-2">
          <span className="text-lg font-semibold text-slate-800">
            {progress}%
          </span>
          <span className="text-xs text-slate-500">
            지금은{" "}
            <span className="font-medium text-[#8CA9FF]">
              {STEP_LABELS[step]}
            </span>{" "}
            단계예요
          </span>
        </div>
      </div>
      <div className="flex-1 max-w-[220px]">
        <div className="w-full h-2 rounded-full bg-[#FFF2C6] overflow-hidden">
          <div
            className="h-full bg-[#FFD860] transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}
