"use client";

import { ChangeEvent } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  CloudUpload,
  FileText,
  Loader2,
} from "lucide-react";
import Button from "@/app/components/ui/Button";
import UploadArea from "@/app/components/ui/UploadArea";
import Card from "@/app/components/ui/Card";

import type { ParsedPdfData } from "@/app/lib/types";

interface Props {
  parsedPdf: ParsedPdfData | null;
  missingFields: string[];
  loadingPdf: boolean;
  onUpload: (e: ChangeEvent<HTMLInputElement>) => void;
  next: () => void;
  prev: () => void;
}

export default function PdfStep({
  parsedPdf,
  missingFields,
  loadingPdf,
  onUpload,
  next,
  prev,
}: Props) {
  const isUploaded = Boolean(parsedPdf);

  return (
    <div className="flex flex-col gap-6 px-2 py-6 pb-24">
      <header>
        <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
          Step 02
        </div>
        <h2 className="mt-1 text-[20px] font-semibold text-slate-900">
          간소화 자료 업로드
        </h2>
        <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
          국세청 연말정산 간소화 서비스에서 받은 PDF 한 개를 업로드해 주세요.
          <br />
          신용카드·의료비·기부금 등 주요 항목을 자동으로 정리합니다.
        </p>
      </header>

      <UploadArea done={isUploaded && !loadingPdf}>
        <input
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={onUpload}
        />
        {loadingPdf ? (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
            <span className="text-[13px] font-medium text-slate-700">
              PDF 분석 중…
            </span>
            <span className="text-[11px] text-slate-400">
              파일 용량에 따라 10~20초 정도 걸릴 수 있어요.
            </span>
          </>
        ) : isUploaded ? (
          <>
            <CheckCircle2 className="h-6 w-6 text-emerald-600" />
            <span className="text-[13px] font-semibold text-emerald-700">
              업로드 완료 — 다른 PDF로 교체하려면 다시 클릭
            </span>
          </>
        ) : (
          <>
            <CloudUpload className="h-6 w-6 text-slate-500" />
            <span className="text-[14px] font-semibold text-slate-800">
              PDF 파일 선택하기
            </span>
            <span className="text-[11px] text-slate-400">
              파일은 서버에 저장되지 않아요.
            </span>
          </>
        )}
      </UploadArea>

      {isUploaded && !loadingPdf ? (
        <Card pad="md" className="space-y-2">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-slate-500" />
            <span className="text-[13px] font-semibold text-slate-900">
              PDF 분석 결과
            </span>
          </div>

          {missingFields.length === 0 ? (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-[12px] text-emerald-700">
              <CheckCircle2 className="h-3.5 w-3.5" />
              필요한 주요 항목을 모두 인식했어요.
            </div>
          ) : (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
              <div className="flex items-center gap-1.5 text-[12px] font-semibold text-amber-800">
                <AlertTriangle className="h-3.5 w-3.5" />
                누락된 항목이 있어요
              </div>
              <p className="mt-1 text-[12px] text-amber-800/80">
                {missingFields.join(", ")}
              </p>
              <p className="mt-1 text-[11px] text-amber-700/70">
                다음 단계에서 직접 입력하면 분석에 반영됩니다.
              </p>
            </div>
          )}
        </Card>
      ) : null}

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
          type="button"
          variant="primary"
          full
          disabled={!isUploaded || loadingPdf}
          onClick={next}
          rightIcon={<ArrowRight className="h-4 w-4" />}
        >
          다음 단계로
        </Button>
      </div>
    </div>
  );
}
