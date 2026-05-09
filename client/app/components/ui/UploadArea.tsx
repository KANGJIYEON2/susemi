"use client";

import { ReactNode } from "react";

interface Props extends React.HTMLAttributes<HTMLLabelElement> {
  children: ReactNode;
  className?: string;
  /** 업로드 완료 상태 — 보더/배경 톤이 바뀜 */
  done?: boolean;
}

export default function UploadArea({
  children,
  className = "",
  done = false,
  ...props
}: Props) {
  return (
    <label
      {...props}
      className={`
        flex flex-col items-center justify-center gap-2
        border-2 border-dashed rounded-2xl
        px-5 py-10
        text-sm cursor-pointer
        transition-colors
        ${
          done
            ? "border-emerald-300 bg-emerald-50/40 text-emerald-700"
            : "border-slate-200 bg-slate-50/60 text-slate-600 hover:border-[#FACC15] hover:bg-[#FFFBEA]"
        }
        ${className}
      `}
    >
      {children}
    </label>
  );
}
