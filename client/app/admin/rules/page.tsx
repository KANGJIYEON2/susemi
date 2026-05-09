"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Loader2,
  Plus,
  RefreshCw,
  Sparkles,
  XCircle,
} from "lucide-react";

import Button from "@/app/components/ui/Button";
import Card from "@/app/components/ui/Card";
import Input from "@/app/components/ui/Input";
import {
  approveDraft,
  compileRule,
  listDrafts,
  rejectDraft,
  type CompileRequest,
  type RuleDraftDTO,
} from "@/app/lib/api";

const DEFAULT_YEAR = 2025;

export default function AdminRulesPage() {
  const [drafts, setDrafts] = useState<RuleDraftDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listDrafts(DEFAULT_YEAR);
      setDrafts(res.drafts);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "드래프트 로드 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="mx-auto max-w-[920px] px-5 py-8 md:py-12">
      <header className="mb-7">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Admin
        </div>
        <h1 className="mt-1 text-[24px] font-bold tracking-tight text-slate-900">
          룰 컴파일러 · 검수 큐
        </h1>
        <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
          법령 본문을 LLM 으로 컴파일해 룰 JSON 드래프트를 생성하고, 검수 후 production
          (rules/{DEFAULT_YEAR}.json) 으로 승격합니다. 드래프트는 자동 검증 결과(신뢰도·경고)와
          함께 저장돼요.
        </p>
      </header>

      <CompileForm onCompiled={refresh} />

      <section className="mt-10">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[15px] font-semibold text-slate-900">
            대기 중인 드래프트 ({drafts.length})
          </h2>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={refresh}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            새로고침
          </Button>
        </div>

        {error ? (
          <div className="mb-3 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            {error}
          </div>
        ) : null}

        {loading && drafts.length === 0 ? (
          <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-5 text-[13px] text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            불러오는 중…
          </div>
        ) : drafts.length === 0 ? (
          <Card pad="lg" className="text-center">
            <p className="text-[13px] text-slate-500">
              대기 중인 드래프트가 없어요. 위 폼으로 새로 컴파일해 보세요.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {drafts.map((d) => (
              <DraftCard key={d.rule.rule_id as string} draft={d} onChanged={refresh} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

/* ============================================================
   컴파일 폼
============================================================ */

function CompileForm({ onCompiled }: { onCompiled: () => void }) {
  const [rule_id, setRuleId] = useState("");
  const [title, setTitle] = useState("");
  const [anchor, setAnchor] = useState("");
  const [law_id, setLawId] = useState("");
  const [law_mst, setLawMst] = useState("");
  const [article_no, setArticleNo] = useState("");
  const [effective_date, setEffectiveDate] = useState("");
  const [law_text_override, setLawTextOverride] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setErrMsg(null);

    if (!rule_id.trim() || !title.trim() || !anchor.trim()) {
      setErrMsg("rule_id / title / anchor 는 필수입니다.");
      return;
    }
    if (!law_id && !law_mst && !law_text_override.trim()) {
      setErrMsg("law_id / law_mst 중 하나를 채우거나, 법령 본문을 직접 붙여 넣으세요.");
      return;
    }

    const body: CompileRequest = {
      target_rule_id: rule_id.trim(),
      target_title: title.trim(),
      target_anchor: anchor.trim(),
      target_year: DEFAULT_YEAR,
      law_id: law_id.trim() || null,
      law_mst: law_mst.trim() || null,
      article_no: article_no.trim() || null,
      effective_date: effective_date.trim() || null,
      law_text_override: law_text_override.trim() || null,
    };

    setBusy(true);
    try {
      const res = await compileRule(body);
      setMsg(
        `컴파일 완료: ${res.draft.rule.rule_id as string} ` +
          `(신뢰도 ${(res.draft.rule.confidence as number).toFixed(2)})`
      );
      // 폼 초기화는 일부만 — 같은 anchor 로 재컴파일 자주 함
      setLawTextOverride("");
      onCompiled();
    } catch (err: unknown) {
      setErrMsg(err instanceof Error ? err.message : "컴파일 실패");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card pad="lg" className="space-y-4">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-[#CA8A04]" />
        <h2 className="text-[15px] font-semibold text-slate-900">새 룰 컴파일</h2>
      </div>

      <form onSubmit={onSubmit} className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="rule_id (소문자/언더바)" required>
            <Input
              placeholder="card_25_threshold"
              value={rule_id}
              onChange={(e) => setRuleId(e.target.value)}
            />
          </Field>
          <Field label="title (사람이 읽는 이름)" required>
            <Input
              placeholder="신용카드 등 사용액 공제 최저사용액 요건"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>
          <Field label="legal_anchor" required>
            <Input
              placeholder="조세특례제한법 §126의2 ①"
              value={anchor}
              onChange={(e) => setAnchor(e.target.value)}
            />
          </Field>
          <Field label="effective_date (YYYYMMDD, 선택)">
            <Input
              placeholder="20250101"
              value={effective_date}
              onChange={(e) => setEffectiveDate(e.target.value)}
            />
          </Field>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-3">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            법령 본문 출처 (셋 중 하나)
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Field label="law_id (6자리)" small>
              <Input
                placeholder="001565"
                value={law_id}
                onChange={(e) => setLawId(e.target.value)}
              />
            </Field>
            <Field label="law_mst (법령일련번호)" small>
              <Input
                placeholder="285523"
                value={law_mst}
                onChange={(e) => setLawMst(e.target.value)}
              />
            </Field>
            <Field label="article_no (조 번호, 선택)" small>
              <Input
                placeholder="52"
                value={article_no}
                onChange={(e) => setArticleNo(e.target.value)}
              />
            </Field>
          </div>
          <div className="mt-3">
            <Field label="또는 법령 본문 직접 붙여넣기" small>
              <textarea
                className="min-h-[120px] w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-[13px] text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/10"
                placeholder="법령 본문을 그대로 붙여넣으면 API 호출 없이 컴파일합니다."
                value={law_text_override}
                onChange={(e) => setLawTextOverride(e.target.value)}
              />
            </Field>
          </div>
        </div>

        {msg ? (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12px] text-emerald-700">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {msg}
          </div>
        ) : null}
        {errMsg ? (
          <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            {errMsg}
          </div>
        ) : null}

        <div className="pt-1">
          <Button
            type="submit"
            variant="cta"
            disabled={busy}
            leftIcon={
              busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )
            }
          >
            {busy ? "컴파일 중…" : "컴파일"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

/* ============================================================
   드래프트 카드
============================================================ */

function DraftCard({
  draft,
  onChanged,
}: {
  draft: RuleDraftDTO;
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const rule = draft.rule;
  const ruleId = rule.rule_id as string;
  const confidence = rule.confidence as number;
  const title = rule.title as string;
  const anchor = rule.legal_anchor as string;

  const decide = async (kind: "approve" | "reject") => {
    const action = kind === "approve" ? approveDraft : rejectDraft;
    const verb = kind === "approve" ? "승인" : "거부";
    if (!window.confirm(`${ruleId} 를 ${verb}할까요?`)) return;
    setBusy(true);
    try {
      await action(ruleId);
      onChanged();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : `${verb} 실패`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[11px] font-semibold text-slate-700">
              {ruleId}
            </span>
            <ConfidenceBadge confidence={confidence} />
            {draft.validation_warnings.length > 0 ? (
              <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-1.5 py-px text-[10px] font-semibold text-amber-700 ring-1 ring-amber-200">
                <AlertTriangle className="h-3 w-3" />
                경고 {draft.validation_warnings.length}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-[13px] font-semibold text-slate-900 line-clamp-1">
            {title}
          </p>
          <p className="text-[11px] text-slate-500">
            {anchor} · 저장 {formatDate(draft.saved_at)}
          </p>
        </div>
        {open ? (
          <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-slate-500" />
        ) : (
          <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-slate-500" />
        )}
      </button>

      {open ? (
        <div className="space-y-3 border-t border-slate-100 px-4 py-3">
          {draft.validation_warnings.length > 0 ? (
            <ul className="space-y-1">
              {draft.validation_warnings.map((w, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-800"
                >
                  <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                  {w}
                </li>
              ))}
            </ul>
          ) : null}

          <details className="rounded-xl border border-slate-200 bg-slate-50/60">
            <summary className="cursor-pointer px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Rule JSON
            </summary>
            <pre className="overflow-x-auto px-3 pb-3 pt-1 text-[11px] leading-relaxed text-slate-700">
              {JSON.stringify(rule, null, 2)}
            </pre>
          </details>

          <details className="rounded-xl border border-slate-200 bg-slate-50/60">
            <summary className="cursor-pointer px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              법령 본문 발췌 ({draft.source_law_excerpt.length} chars)
            </summary>
            <pre className="overflow-x-auto whitespace-pre-wrap px-3 pb-3 pt-1 text-[11px] leading-relaxed text-slate-700">
              {draft.source_law_excerpt}
            </pre>
          </details>

          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={busy}
              onClick={() => decide("approve")}
              leftIcon={<CheckCircle2 className="h-3.5 w-3.5" />}
            >
              승인 → published 로 병합
            </Button>
            <Button
              type="button"
              variant="danger"
              size="sm"
              disabled={busy}
              onClick={() => decide("reject")}
              leftIcon={<XCircle className="h-3.5 w-3.5" />}
            >
              거부
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const tone =
    confidence >= 0.9
      ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
      : confidence >= 0.5
      ? "bg-amber-50 text-amber-700 ring-amber-200"
      : "bg-red-50 text-red-700 ring-red-200";
  return (
    <span
      className={`inline-flex items-center rounded-md px-1.5 py-px text-[10px] font-semibold tabular ring-1 ${tone}`}
    >
      conf {confidence.toFixed(2)}
    </span>
  );
}

function Field({
  label,
  small,
  required,
  children,
}: {
  label: string;
  small?: boolean;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span
        className={`${
          small ? "text-[12px]" : "text-[13px]"
        } font-medium text-slate-700`}
      >
        {label}
        {required ? <span className="ml-0.5 text-[#EAB308]">*</span> : null}
      </span>
      {children}
    </label>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("ko-KR", {
      year: "2-digit",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
