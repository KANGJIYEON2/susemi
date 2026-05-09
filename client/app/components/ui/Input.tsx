import type { InputHTMLAttributes, ReactNode } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  /** 우측 단위 표시 (예: "원", "개월") */
  suffix?: ReactNode;
  /** 숫자/금액 입력일 때 tabular-nums 적용 */
  numeric?: boolean;
  /** 에러 상태 */
  invalid?: boolean;
}

export default function Input({
  suffix,
  numeric = false,
  invalid = false,
  className = "",
  ...props
}: Props) {
  return (
    <div className="relative">
      <input
        {...props}
        className={`
          w-full h-11 rounded-xl border bg-white text-sm text-slate-900
          ${suffix ? "pl-3.5 pr-10" : "px-3.5"}
          placeholder:text-slate-400
          transition-colors
          focus:outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10
          disabled:bg-slate-50 disabled:text-slate-400
          ${numeric ? "tabular text-right" : ""}
          ${
            invalid
              ? "border-red-300 focus:border-red-500 focus:ring-red-500/15"
              : "border-slate-200 hover:border-slate-300"
          }
          ${className}
        `}
      />
      {suffix ? (
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-400">
          {suffix}
        </span>
      ) : null}
    </div>
  );
}
