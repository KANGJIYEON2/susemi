"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  full?: boolean;
  variant?: "primary" | "ghost" | "outline"; //3가지 st 버튼
}

export default function Button({
  children,
  full,
  variant = "primary",
  className = "",
  ...props
}: Props) {
  const base =
    "inline-flex items-center justify-center px-5 py-3 rounded-xl text-sm font-bold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95";

  const variants = {
    primary:
      "bg-[#FFD860] hover:bg-[#FFC840] text-slate-900 shadow-[0_2px_10px_rgba(255,216,96,0.3)] border border-transparent",
    ghost:
      "bg-transparent text-slate-500 hover:bg-slate-100 hover:text-slate-700",
    outline:
      "bg-white border-2 border-slate-100 text-slate-600 hover:border-slate-300 hover:text-slate-800",
  };

  return (
    <button
      {...props}
      className={`
        ${base} 
        ${variants[variant]} 
        ${full ? "w-full" : ""} 
        ${className}
      `}
    >
      {children}
    </button>
  );
}
