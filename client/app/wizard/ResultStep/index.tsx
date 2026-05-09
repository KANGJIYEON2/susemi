"use client";

import Image from "next/image";
import { CheckCircle2, RotateCcw } from "lucide-react";
import Button from "@/app/components/ui/Button";

export default function ResultStep({ restart }: { restart: () => void }) {
  return (
    <div className="flex flex-col gap-6 px-2 py-8">
      <div className="flex items-start gap-3">
        <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-[#FFFBEA] ring-1 ring-[#FDE68A]">
          <Image
            src="/susemi.png"
            alt="susemi"
            fill
            sizes="48px"
            className="object-contain p-1.5"
          />
        </div>
        <div className="min-w-0">
          <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            Step 04
          </div>
          <h2 className="mt-0.5 text-[20px] font-semibold text-slate-900">
            분석 완료
          </h2>
          <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
            오른쪽 패널에서 항목별 Why 리포트를 확인해 주세요.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 text-[13px] font-semibold text-slate-900">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          이번 분석에서 본 것
        </div>
        <ul className="mt-3 space-y-2 text-[13px] leading-relaxed text-slate-700">
          <li className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-slate-400" />
            신용카드·의료비·기부금·월세 등 주요 공제 항목의 기준 충족 여부
          </li>
          <li className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-slate-400" />
            왜 그 결과가 나왔는지 — 공제 구조와 함께 설명
          </li>
          <li className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-slate-400" />
            내년에 챙기면 좋을 행동 제안
          </li>
        </ul>
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-[12px] leading-relaxed text-slate-600">
        모바일에서는 아래 리포트 영역을 위로 스크롤해 보세요.
        데스크톱은 우측 패널의 인덱스를 클릭하면 해당 섹션으로 이동합니다.
      </div>

      <div>
        <Button
          variant="outline"
          size="md"
          onClick={restart}
          leftIcon={<RotateCcw className="h-4 w-4" />}
        >
          처음부터 다시 입력
        </Button>
      </div>
    </div>
  );
}
