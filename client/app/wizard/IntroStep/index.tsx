"use client";

import Button from "@/app/components/ui/Button";

type Props = { onStart: () => void };

export default function IntroStep({ onStart }: Props) {
  return (
    <div className="flex flex-col items-center text-center px-6 py-14 w-full">
      {/* 캐릭터 */}
      <div className="w-24 h-24 mb-2 relative">
        <img
          src="/susemi.png"
          alt="수세미"
          className="w-full h-full object-contain drop-shadow-[0_6px_15px_rgba(0,0,0,0.10)]"
        />
      </div>

      {/* 타이틀 */}
      <h1 className="text-lg md:text-xl font-semibold text-slate-800 mb-2">
        수세미랑 같이 연말정산 뜯어보기
      </h1>

      {/* 설명 */}
      <p className="text-xs md:text-sm text-slate-600 leading-relaxed mb-6">
        간소화 PDF, 소득, 가족, 누락 비용까지.
        <br />
        사람이 설명하듯 Why 중심으로 풀어줘요.
      </p>

      {/* 버튼 */}
      <div className="w-full max-w-xs">
        <Button
          full
          onClick={onStart}
          className="py-3 text-sm font-medium bg-[#FFD84C] hover:bg-[#ffcd2c] text-slate-800 transition-all"
        >
          시작하기 →
        </Button>
      </div>

      {/* 하단 설명 */}
      <p className="text-[10px] text-slate-400 mt-4">
        * 실제 세액계산이 아니라 공제 구조 설명용입니다.
      </p>
    </div>
  );
}
