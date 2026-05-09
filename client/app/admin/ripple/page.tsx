"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  GitBranch,
  Loader2,
  Search,
  Settings2,
  Sparkles,
} from "lucide-react";

import Card from "@/app/components/ui/Card";
import Input from "@/app/components/ui/Input";
import {
  rippleFields,
  rippleFor,
  type FieldNodeDTO,
  type RippleNodeDTO,
  type RippleResponseDTO,
} from "@/app/lib/api";

export default function AdminRipplePage() {
  const [fields, setFields] = useState<FieldNodeDTO[]>([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [report, setReport] = useState<RippleResponseDTO | null>(null);
  const [loadingFields, setLoadingFields] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFields = useCallback(async () => {
    setLoadingFields(true);
    try {
      const res = await rippleFields();
      setFields(res.fields);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "필드 로드 실패");
    } finally {
      setLoadingFields(false);
    }
  }, []);

  useEffect(() => {
    loadFields();
  }, [loadFields]);

  const select = useCallback(async (fieldId: string) => {
    setSelected(fieldId);
    setReport(null);
    setError(null);
    setLoadingReport(true);
    try {
      const res = await rippleFor(fieldId);
      setReport(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "ripple 조회 실패");
    } finally {
      setLoadingReport(false);
    }
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return fields;
    return fields.filter(
      (f) => f.id.toLowerCase().includes(q) || f.label.toLowerCase().includes(q)
    );
  }, [fields, filter]);

  return (
    <div className="mx-auto max-w-[1100px] px-5 py-8 md:py-12">
      <header className="mb-7">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Admin
        </div>
        <h1 className="mt-1 text-[24px] font-bold tracking-tight text-slate-900">
          Ripple-Effect Simulator
        </h1>
        <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
          입력 필드를 선택하면 영향받는 룰과 tax_calculator 단계를 의존성 그래프 BFS 로
          보여드려요. 룰 변경/리팩터 시 어디가 흔들리는지 한눈에 확인.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[300px_1fr]">
        {/* 좌측: 필드 목록 */}
        <Card pad="md" className="space-y-3 lg:sticky lg:top-20 lg:self-start">
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-slate-700" />
            <h2 className="text-[14px] font-semibold text-slate-900">
              필드 ({fields.length})
            </h2>
          </div>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="필드 검색..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="pl-9"
            />
          </div>
          {loadingFields ? (
            <div className="flex items-center gap-2 text-[12px] text-slate-500">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              불러오는 중…
            </div>
          ) : (
            <ul className="max-h-[60vh] space-y-1 overflow-y-auto">
              {filtered.map((f) => (
                <li key={f.id}>
                  <button
                    type="button"
                    onClick={() => select(f.id)}
                    className={`flex w-full flex-col items-start gap-0.5 rounded-lg border px-2.5 py-1.5 text-left transition-colors ${
                      selected === f.id
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <span className="font-mono text-[10px] font-semibold opacity-75">
                      {f.id}
                    </span>
                    <span className="text-[12px] font-medium">{f.label}</span>
                  </button>
                </li>
              ))}
              {filtered.length === 0 ? (
                <li className="text-center text-[12px] text-slate-400">
                  매칭되는 필드 없음
                </li>
              ) : null}
            </ul>
          )}
        </Card>

        {/* 우측: ripple 결과 */}
        <div className="space-y-4">
          {error ? (
            <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
              <AlertTriangle className="h-3.5 w-3.5" />
              {error}
            </div>
          ) : null}

          {!selected ? (
            <Card pad="lg" className="text-center">
              <Sparkles className="mx-auto h-5 w-5 text-slate-400" />
              <p className="mt-2 text-[13px] text-slate-500">
                좌측에서 필드를 선택하면 영향받는 룰·단계를 보여드려요.
              </p>
            </Card>
          ) : loadingReport ? (
            <Card pad="lg">
              <div className="flex items-center gap-2 text-[13px] text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                계산 중…
              </div>
            </Card>
          ) : report ? (
            <ReportView report={report} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

function ReportView({ report }: { report: RippleResponseDTO }) {
  // depth 별 그룹화
  const byDepth = new Map<number, RippleNodeDTO[]>();
  for (const n of report.nodes) {
    const arr = byDepth.get(n.depth) || [];
    arr.push(n);
    byDepth.set(n.depth, arr);
  }
  const depths = [...byDepth.keys()].sort((a, b) => a - b);

  if (report.nodes.length === 0) {
    return (
      <Card pad="lg" className="text-center">
        <p className="text-[13px] text-slate-500">
          이 필드를 직접 읽는 룰·단계가 없어요. (시작 필드 자체는 결과에 포함되지 않습니다.)
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <Card pad="md" className="space-y-1">
        <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          <GitBranch className="h-3 w-3" />
          시작 필드
        </div>
        <div>
          <div className="font-mono text-[11px] text-slate-600">
            {report.changed_field}
          </div>
          <div className="text-[14px] font-semibold text-slate-900">
            {report.field_label ?? report.changed_field}
          </div>
        </div>
        <div className="text-[11px] text-slate-500">
          영향받는 노드 {report.total_count}개 · 최대 depth {depths.at(-1) ?? 0}
        </div>
      </Card>

      {depths.map((depth) => (
        <DepthBlock key={depth} depth={depth} nodes={byDepth.get(depth) || []} />
      ))}
    </div>
  );
}

function DepthBlock({ depth, nodes }: { depth: number; nodes: RippleNodeDTO[] }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        <span className="rounded-md bg-slate-900 px-1.5 py-px text-white">
          depth {depth}
        </span>
        <span>
          {nodes.length}개 영향받음
        </span>
      </div>
      <ul className="space-y-1.5">
        {nodes.map((n) => (
          <li
            key={`${n.kind}-${n.id}`}
            className="flex items-start gap-2.5 rounded-xl border border-slate-200 bg-white px-3 py-2"
          >
            <KindBadge kind={n.kind} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-1.5">
                <span className="font-mono text-[10px] font-medium text-slate-500">
                  {n.id}
                </span>
              </div>
              <div className="text-[13px] font-semibold text-slate-900">
                {n.label}
              </div>
              {n.legal_anchor ? (
                <div className="mt-0.5 text-[11px] text-slate-500">
                  근거: {n.legal_anchor}
                </div>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function KindBadge({ kind }: { kind: "field" | "rule" | "step" }) {
  const map = {
    field: { tone: "bg-slate-50 text-slate-700 ring-slate-200", label: "field" },
    rule: { tone: "bg-yellow-50 text-yellow-800 ring-yellow-200", label: "rule" },
    step: { tone: "bg-emerald-50 text-emerald-700 ring-emerald-200", label: "step" },
  } as const;
  const m = map[kind];
  return (
    <span
      className={`mt-0.5 inline-flex h-5 shrink-0 items-center rounded-md px-1.5 text-[10px] font-semibold uppercase tracking-wider ring-1 ${m.tone}`}
    >
      {m.label}
    </span>
  );
}
