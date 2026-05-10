"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  Clock,
  Equal,
  FileText,
  GitCompareArrows,
  Loader2,
  RotateCcw,
  Sparkles,
  Trash2,
  TrendingUp,
  X,
} from "lucide-react";

import Button from "@/app/components/ui/Button";
import Card from "@/app/components/ui/Card";
import {
  clearAnalyses,
  isStorageAvailable,
  listAnalyses,
  removeAnalysis,
  type StoredAnalysis,
} from "@/app/lib/storage";

const RESUME_SLOT_KEY = "susemi.resume";

export default function HistoryPage() {
  const router = useRouter();
  // 스토리지 가용성은 동기 체크 — useState lazy initializer 로 결정 (effect 안에서 setState 회피)
  const [storageOk] = useState(() => isStorageAvailable());
  const [items, setItems] = useState<StoredAnalysis[]>([]);
  const [loading, setLoading] = useState(storageOk);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    if (!storageOk) return;
    setLoading(true);
    const list = await listAnalyses();
    setItems(list);
    setLoading(false);
  }, [storageOk]);

  useEffect(() => {
    if (!storageOk) return;
    let cancelled = false;
    listAnalyses().then((list) => {
      if (!cancelled) {
        setItems(list);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [storageOk]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < 2) {
        next.add(id);
      } else {
        // 이미 2개 선택 — 가장 오래된 거 빼고 새 거 추가
        const oldest = next.values().next().value as string;
        next.delete(oldest);
        next.add(id);
      }
      return next;
    });
  };

  const clearSelection = () => setSelected(new Set());

  const compared = useMemo<[StoredAnalysis, StoredAnalysis] | null>(() => {
    if (selected.size !== 2) return null;
    const ids = [...selected];
    const a = items.find((i) => i.id === ids[0]);
    const b = items.find((i) => i.id === ids[1]);
    if (!a || !b) return null;
    // 시간순 정렬 — 왼쪽이 더 오래된 것
    return a.saved_at <= b.saved_at ? [a, b] : [b, a];
  }, [items, selected]);

  const stats = useMemo(() => deriveStats(items), [items]);
  const maxSalary = useMemo(
    () => Math.max(0, ...items.map((i) => i.inputs.income.total_salary || 0)),
    [items]
  );

  const onResume = (id: string) => {
    if (typeof window === "undefined") return;
    try {
      window.sessionStorage.setItem(RESUME_SLOT_KEY, id);
    } catch {
      /* ignore */
    }
    router.push("/wizard");
  };

  const onRemove = async (id: string) => {
    if (!window.confirm("이 분석 기록을 삭제할까요?")) return;
    await removeAnalysis(id);
    refresh();
  };

  const onClearAll = async () => {
    if (!window.confirm(`전체 ${items.length}건을 삭제할까요? 되돌릴 수 없습니다.`))
      return;
    await clearAnalyses();
    refresh();
  };

  if (!storageOk) {
    return (
      <div className="mx-auto max-w-[640px] px-5 py-16">
        <Card pad="lg" className="text-center">
          <AlertTriangle className="mx-auto h-6 w-6 text-amber-500" />
          <h2 className="mt-3 text-[16px] font-semibold text-slate-900">
            기록 저장소 사용 불가
          </h2>
          <p className="mt-2 text-[12px] leading-relaxed text-slate-500">
            이 브라우저는 IndexedDB 를 지원하지 않거나 시크릿 모드입니다.
          </p>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-[13px] text-slate-500">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        기록 불러오는 중…
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-[560px] px-5 py-16">
        <Card pad="lg" className="text-center">
          <Sparkles className="mx-auto h-6 w-6 text-slate-400" />
          <h2 className="mt-3 text-[16px] font-semibold text-slate-900">
            아직 저장된 분석이 없어요
          </h2>
          <p className="mt-2 text-[12px] leading-relaxed text-slate-500">
            위저드를 끝까지 진행하면 결과가 자동으로 이 기기에 저장됩니다.
          </p>
          <div className="mt-5">
            <Button
              variant="cta"
              onClick={() => router.push("/wizard")}
              rightIcon={<ArrowRight className="h-4 w-4" />}
            >
              분석 시작하기
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[920px] px-5 py-8 md:py-12">
      <header className="mb-6">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          History
        </div>
        <h1 className="mt-1 flex items-baseline gap-2 text-[24px] font-bold tracking-tight text-slate-900">
          분석 기록
          <span className="tabular text-[18px] font-semibold text-slate-500">
            ({items.length})
          </span>
        </h1>
        <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
          이 기기에만 저장된 기록입니다. 클릭하면 위저드로 이동해 그 시점의 결과를
          다시 봅니다.
        </p>
      </header>

      <StatsRow stats={stats} />

      <SalaryBars items={items} maxSalary={maxSalary} />

      {compared ? (
        <ComparePanel pair={compared} onClose={clearSelection} />
      ) : selected.size > 0 ? (
        <SelectionHint count={selected.size} onClear={clearSelection} />
      ) : null}

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[15px] font-semibold text-slate-900">
            시계열 ({items.length}건)
            {items.length >= 2 ? (
              <span className="ml-2 text-[11px] font-normal text-slate-500">
                · 체크 2개 선택 시 비교
              </span>
            ) : null}
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/wizard")}
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
          >
            새 분석
          </Button>
        </div>

        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id}>
              <HistoryRow
                item={item}
                isSelected={selected.has(item.id)}
                onToggleSelect={() => toggleSelect(item.id)}
                onResume={() => onResume(item.id)}
                onRemove={() => onRemove(item.id)}
              />
            </li>
          ))}
        </ul>
      </section>

      {items.length > 0 ? (
        <section className="mt-10">
          <Button
            variant="danger"
            size="sm"
            onClick={onClearAll}
            leftIcon={<Trash2 className="h-3.5 w-3.5" />}
          >
            전체 삭제
          </Button>
        </section>
      ) : null}
    </div>
  );
}

/* ============================================================
   Stats
============================================================ */

type Stats = {
  count: number;
  firstAt: string | null;
  lastAt: string | null;
  avgSalary: number;
  yearsCovered: number;
};

function deriveStats(items: StoredAnalysis[]): Stats {
  if (items.length === 0) {
    return { count: 0, firstAt: null, lastAt: null, avgSalary: 0, yearsCovered: 0 };
  }
  const sortedByDate = [...items].sort((a, b) =>
    a.saved_at < b.saved_at ? -1 : 1
  );
  const total = items.reduce(
    (acc, i) => acc + (i.inputs.income.total_salary || 0),
    0
  );
  const years = new Set(items.map((i) => i.year));
  return {
    count: items.length,
    firstAt: sortedByDate[0].saved_at,
    lastAt: sortedByDate[sortedByDate.length - 1].saved_at,
    avgSalary: Math.round(total / items.length),
    yearsCovered: years.size,
  };
}

function StatsRow({ stats }: { stats: Stats }) {
  const items: Array<{ label: string; value: string }> = [
    {
      label: "분석 횟수",
      value: `${stats.count.toLocaleString("ko-KR")}건`,
    },
    {
      label: "평균 총급여",
      value: stats.avgSalary
        ? `${stats.avgSalary.toLocaleString("ko-KR")}원`
        : "—",
    },
    {
      label: "커버 연도",
      value: `${stats.yearsCovered}개`,
    },
    {
      label: "최근 분석",
      value: stats.lastAt ? formatDate(stats.lastAt, true) : "—",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
      {items.map((s) => (
        <div
          key={s.label}
          className="rounded-xl border border-slate-200 bg-white px-3.5 py-3"
        >
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            {s.label}
          </div>
          <div className="mt-0.5 tabular text-[15px] font-bold text-slate-900">
            {s.value}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ============================================================
   Salary bars (간단 시각화)
============================================================ */

function SalaryBars({
  items,
  maxSalary,
}: {
  items: StoredAnalysis[];
  maxSalary: number;
}) {
  if (items.length === 0 || maxSalary <= 0) return null;
  // 최근 12건만 표시 (역순으로)
  const top = [...items].slice(0, 12).reverse();

  return (
    <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        <TrendingUp className="h-3 w-3" />
        총급여 추이 (최근 {top.length}건)
      </div>
      <div className="flex items-end justify-between gap-1.5 px-1 pt-2 pb-1">
        {top.map((item) => {
          const sal = item.inputs.income.total_salary || 0;
          const heightPct = maxSalary > 0 ? (sal / maxSalary) * 100 : 0;
          return (
            <div
              key={item.id}
              className="flex flex-1 flex-col items-center gap-1.5"
            >
              <div className="relative flex h-24 w-full items-end overflow-hidden rounded-md bg-slate-50">
                <div
                  className="w-full rounded-md bg-gradient-to-t from-[#FACC15] to-[#FDE68A] transition-all"
                  style={{ height: `${Math.max(2, heightPct)}%` }}
                  title={`${sal.toLocaleString("ko-KR")}원`}
                />
              </div>
              <div className="text-[9px] tabular text-slate-400">
                {shortDate(item.saved_at)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ============================================================
   Row
============================================================ */

function HistoryRow({
  item,
  isSelected,
  onToggleSelect,
  onResume,
  onRemove,
}: {
  item: StoredAnalysis;
  isSelected: boolean;
  onToggleSelect: () => void;
  onResume: () => void;
  onRemove: () => void;
}) {
  const headline =
    item.result?.summary?.headline?.trim() || "분석 결과 (요약 없음)";
  const sal = item.inputs.income.total_salary || 0;

  return (
    <div
      className={`flex items-start gap-3 rounded-xl border bg-white px-4 py-3 transition-colors ${
        isSelected ? "border-slate-900 ring-1 ring-slate-900/10" : "border-slate-200"
      }`}
    >
      <label className="mt-1 flex shrink-0 cursor-pointer items-center">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
          className="h-4 w-4 cursor-pointer accent-slate-900"
          aria-label="비교용 선택"
        />
      </label>
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-50">
        <FileText className="h-4 w-4 text-slate-500" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="tabular text-[11px] font-semibold text-slate-500">
            <Clock className="mr-1 inline h-3 w-3 text-slate-400" />
            {formatDate(item.saved_at)}
          </span>
          <span className="rounded-md bg-slate-100 px-1.5 py-px text-[10px] font-semibold tabular text-slate-700">
            {item.year} 귀속
          </span>
          <span className="tabular text-[11px] text-slate-500">
            {sal ? `${sal.toLocaleString("ko-KR")}원` : "급여 미입력"}
          </span>
        </div>
        <p className="mt-1 text-[13px] font-semibold text-slate-900 line-clamp-2">
          {headline}
        </p>
      </div>
      <div className="flex shrink-0 flex-col gap-1.5">
        <Button
          variant="primary"
          size="sm"
          onClick={onResume}
          rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
        >
          보기
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onRemove}
          leftIcon={<Trash2 className="h-3.5 w-3.5" />}
        >
          삭제
        </Button>
      </div>
    </div>
  );
}

/* ============================================================
   Compare panel
============================================================ */

function SelectionHint({
  count,
  onClear,
}: {
  count: number;
  onClear: () => void;
}) {
  return (
    <div className="mt-5 flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-2.5 text-[12px]">
      <span className="text-slate-600">
        선택됨 <span className="tabular font-semibold">{count}/2</span> — 하나 더
        체크하면 비교 패널이 나타나요.
      </span>
      <button
        type="button"
        onClick={onClear}
        className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-slate-900"
      >
        <X className="h-3 w-3" />
        해제
      </button>
    </div>
  );
}

function ComparePanel({
  pair,
  onClose,
}: {
  pair: [StoredAnalysis, StoredAnalysis];
  onClose: () => void;
}) {
  const [a, b] = pair;
  const rows: Array<{ label: string; va: string; vb: string; same: boolean }> = [];

  const push = (label: string, va: string, vb: string) => {
    rows.push({ label, va, vb, same: va === vb });
  };

  push("저장 시각", formatDate(a.saved_at), formatDate(b.saved_at));
  push("귀속 연도", String(a.year), String(b.year));
  push(
    "총급여",
    a.inputs.income.total_salary
      ? `${a.inputs.income.total_salary.toLocaleString("ko-KR")}원`
      : "—",
    b.inputs.income.total_salary
      ? `${b.inputs.income.total_salary.toLocaleString("ko-KR")}원`
      : "—"
  );
  push("배우자", a.inputs.dependents.has_spouse ? "있음" : "없음", b.inputs.dependents.has_spouse ? "있음" : "없음");
  push(
    "부양가족 수",
    String(a.inputs.dependents.dependents_count || 0),
    String(b.inputs.dependents.dependents_count || 0)
  );
  push(
    "장애인",
    String(a.inputs.dependents.disabled_count || 0),
    String(b.inputs.dependents.disabled_count || 0)
  );
  push("세대주", a.inputs.conditions.householder ? "Y" : "N", b.inputs.conditions.householder ? "Y" : "N");
  push("무주택", a.inputs.conditions.no_house ? "Y" : "N", b.inputs.conditions.no_house ? "Y" : "N");
  push("임대차계약", a.inputs.conditions.lease_contract ? "Y" : "N", b.inputs.conditions.lease_contract ? "Y" : "N");
  push("주택대출", a.inputs.conditions.has_loan ? "Y" : "N", b.inputs.conditions.has_loan ? "Y" : "N");

  return (
    <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/60 px-4 py-2.5">
        <div className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-700">
          <GitCompareArrows className="h-3.5 w-3.5 text-slate-500" />
          분석 비교
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-slate-900"
        >
          <X className="h-3 w-3" />
          닫기
        </button>
      </div>
      <div className="px-4 py-3">
        <div className="mb-3 grid grid-cols-2 gap-3">
          <CompareHeader item={a} label="이전" />
          <CompareHeader item={b} label="이후" />
        </div>
        <div className="overflow-hidden rounded-xl border border-slate-200">
          <table className="w-full text-[12px]">
            <tbody className="divide-y divide-slate-100">
              {rows.map((r) => (
                <tr key={r.label} className={r.same ? "bg-white" : "bg-amber-50/40"}>
                  <td className="w-24 px-3 py-2 text-[11px] font-semibold text-slate-500">
                    {r.label}
                  </td>
                  <td className="px-3 py-2 tabular text-slate-800">{r.va}</td>
                  <td className="w-6 px-1 text-center text-slate-300">
                    {r.same ? <Equal className="inline h-3 w-3" /> : "→"}
                  </td>
                  <td className="px-3 py-2 tabular text-slate-800">{r.vb}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-slate-400">
          ※ 입력 스냅샷 비교만 표시합니다. 결정세액·환급액 같은 산식 결과 비교는 다음 버전에 — 그때 두 분석을 같은 세율표로 동시 재계산해 보여드릴게요.
        </p>
      </div>
    </div>
  );
}

function CompareHeader({
  item,
  label,
}: {
  item: StoredAnalysis;
  label: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="mt-0.5 text-[11px] tabular text-slate-700">
        {formatDate(item.saved_at, true)}
      </div>
      <div className="line-clamp-2 mt-1 text-[12px] font-semibold text-slate-900">
        {item.result?.summary?.headline ?? "분석 결과"}
      </div>
    </div>
  );
}

/* ============================================================
   format
============================================================ */

function formatDate(iso: string, short = false): string {
  try {
    const d = new Date(iso);
    if (short) {
      return d.toLocaleDateString("ko-KR", {
        year: "2-digit",
        month: "2-digit",
        day: "2-digit",
      });
    }
    return d.toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function shortDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return "";
  }
}
