"use client";

import { useEffect, useState } from "react";
import {
  ArrowRight,
  Clock,
  FileText,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import Button from "@/app/components/ui/Button";
import {
  isStorageAvailable,
  listAnalyses,
  removeAnalysis,
  type StoredAnalysis,
} from "@/app/lib/storage";

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
    title: "민감정보는 서버 미저장",
    desc: "분석은 일회성이고, 기록은 이 기기에만 남아요.",
  },
];

interface Props {
  onStart: () => void;
  onResume: (loaded: StoredAnalysis) => void;
}

export default function IntroStep({ onStart, onResume }: Props) {
  const [recent, setRecent] = useState<StoredAnalysis | null>(null);

  useEffect(() => {
    if (!isStorageAvailable()) return;
    let cancelled = false;
    listAnalyses({ limit: 1 }).then((items) => {
      if (!cancelled && items.length > 0) setRecent(items[0]);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleRemove = async () => {
    if (!recent) return;
    const ok = window.confirm("이 기기에 저장된 마지막 분석을 삭제할까요?");
    if (!ok) return;
    await removeAnalysis(recent.id);
    setRecent(null);
  };

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

      {recent ? <ResumeCard recent={recent} onResume={onResume} onRemove={handleRemove} /> : null}

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
          {recent ? "새로 시작하기" : "시작하기"}
        </Button>
        <p className="mt-3 text-center text-[11px] text-slate-400">
          정확한 세액 계산이 아니라 공제 구조 설명용 도구예요.
        </p>
      </div>
    </div>
  );
}

/* ---------- 이어서 보기 카드 ---------- */

function ResumeCard({
  recent,
  onResume,
  onRemove,
}: {
  recent: StoredAnalysis;
  onResume: (loaded: StoredAnalysis) => void;
  onRemove: () => void;
}) {
  const date = new Date(recent.saved_at);
  const dateLabel = date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const headline = recent.result?.summary?.headline ?? "분석 결과";

  return (
    <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/60 px-4 py-2">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <Clock className="h-3 w-3" />
          마지막 분석
        </div>
        <span className="text-[11px] tabular text-slate-500">{dateLabel}</span>
      </div>
      <div className="px-4 py-3">
        <p className="text-[13px] font-semibold text-slate-900 line-clamp-2">
          {headline}
        </p>
        <p className="mt-0.5 text-[11px] text-slate-500">
          이 기기에만 저장돼 있어요. 새 분석을 시작하면 덮어쓰지 않고 누적됩니다.
        </p>
        <div className="mt-3 flex gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => onResume(recent)}
            rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
          >
            이어서 보기
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRemove}
            leftIcon={<Trash2 className="h-3.5 w-3.5" />}
          >
            삭제
          </Button>
        </div>
      </div>
    </div>
  );
}
