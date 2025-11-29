"use client";

import { ChangeEvent } from "react";
import UploadArea from "@/app/components/ui/UploadArea";
import Button from "@/app/components/ui/Button";

interface Props {
  parsedPdf: any;
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
    <div className="flex flex-col items-center w-full">
      <div className="w-full max-w-xl px-4 flex flex-col gap-6 pb-20">
        {/* 제목 */}
        <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-800">
          ② 간소화 PDF 업로드
        </h2>

        {/* 설명 */}
        <p className="text-[15px] leading-relaxed text-slate-600">
          국세청 연말정산 간소화 서비스에서 내려받은
          <span className="bg-[#FFF2B2] px-1 py-0.5 rounded mx-1">
            PDF 한 개
          </span>
          파일을 업로드해주세요.
          <br />
          신용카드 · 의료비 · 기부금 등 주요 항목을 자동으로 불러올게요.
        </p>

        {/* 업로드 박스 */}
        <UploadArea className="mt-1 max-w-xl h-40">
          <span className="text-base text-[#7B9FFF] font-medium">
            {loadingPdf
              ? "PDF 분석 중…"
              : isUploaded
              ? "PDF 업로드 완료 ✔"
              : "PDF 파일 선택하기"}
          </span>

          <span className="text-xs text-slate-400">
            개인정보는 저장되지 않아요.
          </span>

          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={onUpload}
          />
        </UploadArea>

        {/* PDF 분석 결과 박스 */}
        {isUploaded && (
          <div className="bg-[#FFF8DE] border border-[#F2E7A5] rounded-xl px-4 py-3 text-sm text-slate-700">
            <p className="font-semibold mb-1">PDF 분석 결과</p>

            {missingFields.length === 0 ? (
              <p>📌 필요한 항목 모두 확인됐어요!</p>
            ) : (
              <ul className="list-disc pl-4 space-y-1">
                <li>누락된 정보: {missingFields.join(", ")}</li>
                <li className="text-[12px] text-slate-500">
                  누락 항목은 다음 단계에서 입력하면 돼요.
                </li>
              </ul>
            )}
          </div>
        )}

        {/* 버튼 영역 */}
        <div className="flex gap-3 pt-4">
          <Button type="button" variant="ghost" onClick={prev}>
            ← 이전
          </Button>

          <Button
            full
            type="button"
            disabled={!isUploaded || loadingPdf}
            onClick={next}
          >
            다음으로 (추가 입력) →
          </Button>
        </div>
      </div>
    </div>
  );
}
