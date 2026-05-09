"use client";

import { ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
  /** 강조 카드(노랑 1px 좌측 보더). tip / 핵심 highlight 용. */
  accent?: boolean;
  /** 패딩 사이즈 */
  pad?: "sm" | "md" | "lg";
}

const padClass: Record<NonNullable<Props["pad"]>, string> = {
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export default function Card({
  children,
  className = "",
  accent = false,
  pad = "md",
}: Props) {
  return (
    <div
      className={`
        bg-white rounded-2xl border border-slate-200
        ${padClass[pad]}
        ${accent ? "border-l-[3px] border-l-[#FACC15]" : ""}
        ${className}
      `}
    >
      {children}
    </div>
  );
}
