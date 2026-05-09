"use client";

import Link from "next/link";

const STEP_LABELS = [
  "시작",
  "소득·가족",
  "간소화 자료",
  "추가 입력",
  "분석 결과",
];

interface Props {
  step: number;
  totalSteps: number;
}

export default function AppHeader({ step, totalSteps }: Props) {
  const safeTotal = Math.max(1, totalSteps);
  const progress = Math.min(100, Math.round((step / safeTotal) * 100));
  const label = STEP_LABELS[step] ?? STEP_LABELS[STEP_LABELS.length - 1];

  return (
    <header className="sticky top-0 z-30 w-full border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-4 md:px-6">
        {/* 좌측: 마크 + 워드마크 */}
        <Link
          href="/"
          aria-label="susemi 홈"
          className="group flex items-center gap-2.5 outline-none"
        >
          {/* 마크: slate-900 라운드 사각형 + 노랑 버블 클러스터 (수세미 모티프) */}
          <span
            className="relative inline-flex h-8 w-8 items-center justify-center rounded-[10px] bg-gradient-to-br from-slate-900 to-slate-800 shadow-[0_2px_6px_-2px_rgba(15,23,42,0.35),inset_0_1px_0_rgba(255,255,255,0.06)] ring-1 ring-slate-900/10 transition-transform duration-200 group-hover:-translate-y-0.5"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
              className="h-4 w-4"
            >
              {/* 큰 버블 */}
              <circle cx="13.5" cy="13.5" r="3.6" fill="#FACC15" />
              {/* 중간 버블 */}
              <circle
                cx="8"
                cy="11"
                r="1.9"
                fill="#FACC15"
                opacity="0.92"
              />
              {/* 작은 버블 */}
              <circle
                cx="16.5"
                cy="7.5"
                r="1.3"
                fill="#FACC15"
                opacity="0.75"
              />
              {/* 큰 버블 하이라이트 */}
              <circle
                cx="12.3"
                cy="12.2"
                r="0.9"
                fill="#FFFFFF"
                opacity="0.55"
              />
            </svg>
          </span>

          {/* 워드마크 */}
          <span className="flex items-baseline">
            <span className="text-[18px] font-extrabold leading-none tracking-[-0.03em] text-slate-900">
              susemi
            </span>
            <span className="ml-[1px] text-[18px] font-extrabold leading-none text-[#FACC15]">
              .
            </span>
          </span>
        </Link>

        {/* 우측: 진행률 */}
        <div className="flex items-center gap-3">
          <div className="hidden flex-col items-end leading-tight sm:flex">
            <span className="text-[10px] uppercase tracking-wide text-slate-400">
              Step {Math.min(step + 1, safeTotal + 1)} / {safeTotal + 1}
            </span>
            <span className="text-[12px] font-medium text-slate-700">
              {label}
            </span>
          </div>
          <div className="relative h-1.5 w-24 overflow-hidden rounded-full bg-slate-100 sm:w-40">
            <div
              className="h-full rounded-full bg-slate-900 transition-[width] duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="tabular text-[12px] font-semibold text-slate-900">
            {progress}%
          </span>
        </div>
      </div>
    </header>
  );
}
