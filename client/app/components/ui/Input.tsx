import type { InputHTMLAttributes } from "react";

export default function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`
        w-full rounded-xl border border-stone-200 bg-stone-50/50 px-4 py-3 text-sm text-slate-800
        placeholder:text-slate-400
        transition-all duration-200
        focus:bg-white focus:border-[#FFD860]
        focus:ring-4 focus:ring-[#FFE37A]/40
        focus:shadow-[0_0_0_3px_rgba(255,216,96,0.2)]
        disabled:bg-slate-100 disabled:text-slate-400
        ${props.className ?? ""}
      `}
    />
  );
}
