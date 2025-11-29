"use client";

import { ReactNode } from "react";

export default function UploadArea({
  children,
  className = "",
  ...props
}: {
  children: ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      {...props}
      className={`
        flex flex-col items-center justify-center gap-2
        border-2 border-dashed border-[#AAC4F5]
        rounded-2xl bg-white px-5 py-6 text-sm text-slate-500 cursor-pointer
        hover:border-[#8CA9FF] transition
        ${className}
      `}
    >
      {children}
    </label>
  );
}
