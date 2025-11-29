"use client";

import { AnalyzeResponse } from "@/app/lib/types";
import Spinner from "@/app/components/ui/Spinner";

/* 공통 카드 스타일 */
const cardClass =
  "bg-[#FFFDF5] border border-[#F3E6C0] rounded-xl p-6 shadow-sm";

/* 섹션 헤더 */
const sectionTitle =
  "text-lg font-bold text-slate-900 mb-3 flex items-center gap-2";

export default function ReportLayout({
  data,
  loading,
  error,
}: {
  data?: AnalyzeResponse | null;
  loading?: boolean;
  error?: string | null;
}) {
  /* 로딩 */
  if (loading)
    return (
      <div className="flex flex-col items-center justify-center h-72 gap-4 text-center">
        <div className="scale-110">
          <p className="text-slate-600 text-sm animate-pulse">
            🤓 수세미가 연말정산 Why 리포트를 작성 중입니다…
          </p>
        </div>
      </div>
    );

  /* 에러시 */
  if (error)
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center px-6">
        <div className="text-4xl mb-2">🥲</div>
        <p className="text-red-500 text-sm font-medium">{error}</p>
      </div>
    );

  /* 빈 값일 경우 */
  if (!data)
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center opacity-60">
        <div className="text-4xl">✨</div>
        <p className="text-slate-500 text-sm mt-2">
          아직 분석 결과가 없습니다.
        </p>
      </div>
    );

  /* 메인 section*/
  return (
    <div className="w-full flex justify-center">
      <div className="w-full max-w-3xl px-4 py-10 space-y-12">
        {/* SUMMARY */}
        <section className="space-y-3">
          <span className="text-xs uppercase font-semibold text-[#F5A623] tracking-wide">
            Summary
          </span>

          <h1 className="text-2xl font-bold text-slate-900 leading-snug">
            {data.summary.headline}
          </h1>

          <div className={cardClass}>
            <ul className="space-y-3">
              {data.summary.key_points.map((p, i) => (
                <li
                  key={i}
                  className="flex gap-3 text-sm text-slate-700 leading-relaxed"
                >
                  <span className="w-5 h-5 rounded-full bg-[#FFD860] text-white text-[10px] flex items-center justify-center font-bold">
                    ✓
                  </span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* SECTIONS */}
        <div className="space-y-10">
          {data.sections.map((s) => (
            <section key={s.id} className="space-y-3">
              <h2 className={sectionTitle}>{s.title}</h2>

              <p className="text-[15px] text-slate-700 leading-7 whitespace-pre-line">
                {s.detail}
              </p>

              {/* TIP BOX */}
              {s.tips.length > 0 && (
                <div className="bg-[#FFF8DA] border border-[#F2E7A5] rounded-xl p-4 shadow-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">💡</span>
                    <span className="text-xs font-semibold text-amber-700">
                      수세미의 TIP
                    </span>
                  </div>

                  <ul className="space-y-1.5">
                    {s.tips.map((t, i) => (
                      <li
                        key={i}
                        className="text-sm text-slate-800 leading-relaxed flex gap-2"
                      >
                        <span className="text-amber-400">•</span>
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          ))}
        </div>

        {/* FINAL TIPS */}
        {data.tax_tips.length > 0 && (
          <section className="bg-slate-50 border border-slate-200 rounded-2xl p-6 shadow-inner space-y-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-2">
              <span className="text-xl">🎓</span>
              내년을 위한 총정리
            </h2>

            <ul className="space-y-3">
              {data.tax_tips.map((t, i) => (
                <li
                  key={i}
                  className="flex gap-3 text-sm text-slate-700 leading-relaxed"
                >
                  <span className="w-6 h-6 flex items-center justify-center bg-slate-200 text-slate-600 rounded-full text-[11px] font-bold">
                    {i + 1}
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
