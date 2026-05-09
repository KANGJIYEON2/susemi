"use client";

interface Props {
  size?: number;
  className?: string;
}

export default function Spinner({ size = 16, className = "" }: Props) {
  const dimension = `${size}px`;
  return (
    <span
      role="status"
      aria-label="loading"
      className={`inline-block ${className}`}
      style={{ width: dimension, height: dimension }}
    >
      <span
        className="block w-full h-full rounded-full border-2 border-slate-200 border-t-slate-900 animate-spin"
      />
    </span>
  );
}
