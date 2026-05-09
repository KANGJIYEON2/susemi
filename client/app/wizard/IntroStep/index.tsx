"use client";

import { ArrowRight, FileText, ShieldCheck, Sparkles } from "lucide-react";
import Button from "@/app/components/ui/Button";

const FEATURES = [
  {
    icon: <FileText className="h-4 w-4 text-slate-700" />,
    title: "간소화 PDF 그대로",
    desc: "국세청에서 받은 PDF를 올리면 항목별로 정리해 드려요.",
  },
  {
    icon: <Sparkles className="h-4 w-4 text-slate-700" />,
    title: "Why 중심 해설",
    desc: "공제 기준 충족 여부와 그 이유를 사람 말투로 설명합니다.",
  },
  {
    icon: <ShieldCheck className="h-4 w-4 text-slate-700" />,
    title: "민감정보는 저장 안 함",
    desc: "분석은 전부 일회성이고, 데이터는 서버에 남기지 않아요.",
  },
];

export default function IntroStep({ onStart }: { onStart: () => void }) {
  return (
    <div className="flex w-full flex-col px-2 py-8 md:py-10">
      <div className="mb-1 inline-flex w-fit items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600">
        <span className="h-1.5 w-1.5 rounded-full bg-[#FACC15]" />
        2025년 귀속분 연말정산
      </div>

      <h1 className="mt-4 text-[26px] font-bold leading-[1.25] tracking-tight text-slate-900 md:text-[28px]">
        왜 이 금액이 나왔는지
        <br />
        <span className="bg-[linear-gradient(180deg,transparent_60%,#FEF08A_60%)] px-0.5">
          하나하나 풀어드릴게요
        </span>
        .
      </h1>

      <p className="mt-3 text-[14px] leading-relaxed text-slate-600">
        소득·부양가족·간소화 자료를 차례로 입력하면, 항목별 공제 기준과 충족 여부를
        근거와 함께 보여드려요.
      </p>

      <div className="mt-7 grid gap-2.5">
        {FEATURES.map((f) => (
          <div
            key={f.title}
            className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-3.5 py-3"
          >
            <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-50">
              {f.icon}
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-slate-900">
                {f.title}
              </div>
              <div className="mt-0.5 text-[12px] leading-relaxed text-slate-500">
                {f.desc}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <Button
          onClick={onStart}
          variant="cta"
          size="lg"
          full
          rightIcon={<ArrowRight className="h-4 w-4" />}
        >
          시작하기
        </Button>
        <p className="mt-3 text-center text-[11px] text-slate-400">
          정확한 세액 계산이 아니라 공제 구조 설명용 도구예요.
        </p>
      </div>
    </div>
  );
}
