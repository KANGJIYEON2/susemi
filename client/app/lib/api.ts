import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ParsedPdfData,
  VerificationReport,
  VerifyRequest,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"; // 배포주소와 현재주소 모두 핸들링

export async function parsePdf(file: File): Promise<{
  parsed_pdf: ParsedPdfData;
  missing_fields: string[];
}> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/pdf-parse`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`PDF 분석 실패: ${res.status} ${text}`);
  }

  return res.json();
}

export async function analyzeTax(
  payload: AnalyzeRequest
): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`분석 API 실패: ${res.status} ${text}`);
  }

  return res.json();
}

export async function postManualInput(
  payload: unknown
): Promise<{ status: string; message?: string | null }> {
  const res = await fetch(`${API_BASE}/manual-input`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`수기 입력 검증 실패: ${res.status} ${text}`);
  }

  return res.json();
}

/* ---------------- Phase 3-3: 검증 ---------------- */

export async function verifyFiling(
  payload: VerifyRequest
): Promise<VerificationReport> {
  const res = await fetch(`${API_BASE}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`검증 실패: ${res.status} ${text}`);
  }
  return res.json();
}

/* ---------------- Admin: 룰 컴파일러 ---------------- */

export type CompileRequest = {
  law_id?: string | null;
  law_mst?: string | null;
  article_no?: string | null;
  effective_date?: string | null;
  law_text_override?: string | null;
  target_rule_id: string;
  target_title: string;
  target_anchor: string;
  target_year?: number;
  parent_rule_id?: string | null;
};

export type RuleDraftDTO = {
  rule: Record<string, unknown>;
  status: "draft" | "approved" | "rejected";
  review_notes: string | null;
  source_law_excerpt: string;
  source_chunk_id: string | null;
  parent_rule_id: string | null;
  validation_warnings: string[];
  saved_at: string;
};

async function adminFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function compileRule(
  body: CompileRequest
): Promise<{ draft: RuleDraftDTO }> {
  return adminFetch("/admin/rules/compile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function listDrafts(
  year?: number
): Promise<{ drafts: RuleDraftDTO[] }> {
  const qs = year != null ? `?year=${year}` : "";
  return adminFetch(`/admin/rules/drafts${qs}`);
}

export async function approveDraft(
  rule_id: string,
  notes?: string,
  year: number = 2025
): Promise<{ status: string; rule_id: string; message: string }> {
  return adminFetch(
    `/admin/rules/drafts/${encodeURIComponent(rule_id)}/approve?year=${year}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ review_notes: notes ?? null }),
    }
  );
}

export async function rejectDraft(
  rule_id: string,
  notes?: string,
  year: number = 2025
): Promise<{ status: string; rule_id: string; message: string }> {
  return adminFetch(
    `/admin/rules/drafts/${encodeURIComponent(rule_id)}/reject?year=${year}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ review_notes: notes ?? null }),
    }
  );
}
