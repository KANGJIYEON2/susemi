"use client";

import { ReactNode } from "react";

export default function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`
        bg-white rounded-2xl p-5
        border border-stone-200
        shadow-[0_1px_4px_rgba(0,0,0,0.04)]
        hover:shadow-[0_3px_12px_rgba(0,0,0,0.08)]
        transition-shadow
        ${className}
      `}
    >
      {children}
    </div>
  );
}
