"use client";

import { ReactNode, useCallback, useEffect, useState } from "react";
import { AlertTriangle, KeyRound, Loader2, LogOut, ShieldCheck } from "lucide-react";

import Button from "@/app/components/ui/Button";
import Card from "@/app/components/ui/Card";
import Input from "@/app/components/ui/Input";
import {
  clearAdminToken,
  getAdminToken,
  setAdminToken,
} from "@/app/lib/admin-token";
import { AdminAuthError } from "@/app/lib/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Status = "loading" | "ok" | "needs_token" | "wrong_token" | "disabled";

interface Props {
  children: ReactNode;
}

/**
 * /admin/* 페이지 wrapper.
 * - localStorage 의 X-Admin-Token 으로 한 번 호출(/rag/stats) 해서 인증 검증
 * - 401/없음 → 입력 폼
 * - 403 → 잘못된 토큰
 * - 503 → 서버에 ADMIN_TOKEN 미설정
 * - 200 → children 렌더
 */
export default function AdminGate({ children }: Props) {
  const [status, setStatus] = useState<Status>("loading");
  const [tokenInput, setTokenInput] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const probe = useCallback(async (): Promise<Status> => {
    const token = getAdminToken();
    if (!token) return "needs_token";
    try {
      const res = await fetch(`${API_BASE}/rag/stats`, {
        headers: { "X-Admin-Token": token },
      });
      if (res.status === 200) return "ok";
      if (res.status === 503) return "disabled";
      if (res.status === 401) return "needs_token";
      if (res.status === 403) return "wrong_token";
      return "wrong_token";
    } catch {
      return "needs_token";
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    probe().then((s) => {
      if (!cancelled) setStatus(s);
    });
    return () => {
      cancelled = true;
    };
  }, [probe]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    setSubmitting(true);
    setAdminToken(tokenInput.trim());
    const next = await probe();
    setStatus(next);
    setSubmitting(false);
    setTokenInput("");
  };

  const logout = () => {
    clearAdminToken();
    setStatus("needs_token");
  };

  if (status === "loading") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-[13px] text-slate-500">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        admin 인증 확인 중…
      </div>
    );
  }

  if (status === "disabled") {
    return (
      <div className="mx-auto max-w-[480px] px-5 py-16">
        <Card pad="lg" className="text-center">
          <AlertTriangle className="mx-auto h-6 w-6 text-amber-500" />
          <h2 className="mt-3 text-[16px] font-semibold text-slate-900">
            admin 기능 비활성
          </h2>
          <p className="mt-2 text-[12px] leading-relaxed text-slate-500">
            서버에 <code className="rounded bg-slate-100 px-1 py-px font-mono text-[11px]">ADMIN_TOKEN</code>{" "}
            환경변수가 설정되지 않았어요. 운영자에게 문의하세요.
          </p>
        </Card>
      </div>
    );
  }

  if (status === "needs_token" || status === "wrong_token") {
    return (
      <div className="mx-auto max-w-[440px] px-5 py-16">
        <Card pad="lg" className="space-y-4">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-slate-700" />
            <h2 className="text-[15px] font-semibold text-slate-900">
              Admin 인증 필요
            </h2>
          </div>
          <p className="text-[12px] leading-relaxed text-slate-500">
            <code className="rounded bg-slate-100 px-1 py-px font-mono text-[11px]">
              X-Admin-Token
            </code>{" "}
            을 입력해 주세요. 토큰은 이 기기 localStorage 에만 저장됩니다.
          </p>
          <form onSubmit={submit} className="space-y-3">
            <Input
              type="password"
              autoFocus
              autoComplete="off"
              placeholder="admin 토큰"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
            />
            {status === "wrong_token" ? (
              <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
                <AlertTriangle className="h-3.5 w-3.5" />
                토큰이 일치하지 않아요. 다시 시도해 주세요.
              </div>
            ) : null}
            <Button
              type="submit"
              variant="primary"
              size="md"
              full
              disabled={submitting || !tokenInput.trim()}
              leftIcon={
                submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="h-4 w-4" />
                )
              }
            >
              {submitting ? "확인 중…" : "토큰으로 인증"}
            </Button>
          </form>
        </Card>
      </div>
    );
  }

  // status === "ok"
  return (
    <div className="relative">
      <div className="sticky top-14 z-10 flex justify-end border-b border-slate-100 bg-white/85 px-5 py-1.5 backdrop-blur">
        <button
          type="button"
          onClick={logout}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-slate-900"
        >
          <LogOut className="h-3 w-3" />
          admin 로그아웃
        </button>
      </div>
      {children}
    </div>
  );
}

// AdminAuthError 가 사용되지 않는 경우에도 import 유지 (다른 컴포넌트가 catch 시)
export { AdminAuthError };
