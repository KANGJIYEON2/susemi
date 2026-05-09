"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "cta" | "outline" | "ghost" | "danger";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  full?: boolean;
  variant?: Variant;
  size?: "sm" | "md" | "lg";
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const sizeClass: Record<NonNullable<Props["size"]>, string> = {
  sm: "h-9 px-3 text-[13px]",
  md: "h-11 px-4 text-sm",
  lg: "h-12 px-5 text-[15px]",
};

const variantClass: Record<Variant, string> = {
  // 기본 액션 — 신뢰 톤. 가장 많이 쓰임.
  primary:
    "bg-slate-900 text-white border border-slate-900 hover:bg-slate-800 active:bg-slate-950 disabled:bg-slate-300 disabled:border-slate-300",
  // 결정적 순간(분석 시작/리포트 보기)에만. 노랑은 여기서만 면적을 가져감.
  cta:
    "bg-[#FACC15] text-slate-900 border border-[#FACC15] hover:bg-[#EAB308] active:bg-[#CA8A04] disabled:bg-slate-200 disabled:text-slate-400 disabled:border-slate-200 shadow-[0_1px_2px_rgba(15,23,42,0.08)]",
  outline:
    "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-slate-300 active:bg-slate-100",
  ghost:
    "bg-transparent text-slate-600 border border-transparent hover:bg-slate-100 hover:text-slate-900",
  danger:
    "bg-white text-red-600 border border-red-200 hover:bg-red-50 active:bg-red-100",
};

export default function Button({
  children,
  full,
  variant = "primary",
  size = "md",
  leftIcon,
  rightIcon,
  className = "",
  ...props
}: Props) {
  return (
    <button
      {...props}
      className={`
        inline-flex items-center justify-center gap-2 rounded-xl font-semibold
        transition-colors duration-150
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2
        disabled:cursor-not-allowed
        ${sizeClass[size]} ${variantClass[variant]}
        ${full ? "w-full" : ""}
        ${className}
      `}
    >
      {leftIcon ? <span className="shrink-0">{leftIcon}</span> : null}
      <span className="truncate">{children}</span>
      {rightIcon ? <span className="shrink-0">{rightIcon}</span> : null}
    </button>
  );
}
