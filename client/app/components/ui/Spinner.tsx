"use client";

export default function Spinner() {
  return (
    <div className="relative w-5 h-5">
      <div className="absolute inset-0 border-2 border-slate-100 rounded-full h-full w-full"></div>
      <div className="absolute inset-0 border-2 border-[#FFD860] border-t-transparent rounded-full h-full w-full animate-spin"></div>
    </div>
  );
}
