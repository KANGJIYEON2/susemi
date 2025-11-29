"use client";

import Button from "@/app/components/ui/Button";

type Props = {
  restart: () => void;
};

export default function ResultStep({ restart }: Props) {
  return (
    <div className="flex flex-col gap-6 w-full max-w-xl mx-auto px-3">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-full bg-[#FFF3C8] border border-[#FCE6A4] flex items-center justify-center shadow-sm">
          <span className="text-[20px]">✨</span>
        </div>

        <div className="flex flex-col">
          <h2 className="text-base font-semibold text-slate-800">
            ④ 분석 완료!
          </h2>
          <p className="text-[12px] text-slate-500 mt-[1px]">
            이제 오른쪽에서 Why 리포트를 확인해 보세요.
          </p>
        </div>
      </div>

      {/* 설명 카드 */}
      <div className="bg-[#FFFDF3] border border-[#F3E6C0] rounded-xl p-5 shadow-sm">
        <p className="text-sm text-slate-700 leading-relaxed">
          수세미가 입력하신 정보를 기반으로{" "}
          <span className="font-semibold">항목별 Why 분석 결과</span>를
          생성했어요.
        </p>

        <p className="text-[12px] text-slate-500 leading-relaxed mt-2">
          신용카드·의료비·기부금·월세 등 주요 공제 항목들을 자동으로 비교하고,
          기준 충족 여부까지 정리해 드립니다.
        </p>
      </div>

      {/* TIP 안내 */}
      <div className="px-4 py-3 bg-[#FFFCF0] border border-[#FFEEC2] rounded-xl shadow-sm">
        <p className="text-[12px] text-slate-700 leading-relaxed">
          🔎 <span className="font-semibold">TIP.</span> 오른쪽의 인덱스를
          클릭하면 해당 분석 섹션으로 바로 이동할 수 있어요!
          <br />
          모바일은 아래쪽 리포트 영역까지 스크롤해 주세요.
        </p>
      </div>

      {/* 다시하기 버튼 */}
      <div className="flex mt-2">
        <Button
          type="button"
          variant="primary"
          onClick={restart}
          className="text-sm px-4 py-2"
        >
          ← 다시 처음부터 입력하기
        </Button>
      </div>
    </div>
  );
}
