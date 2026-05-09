import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ParsedPdfData,
  RecommendRequest,
  RecommendResponse,
  SimulateRequest,
  SimulateResponse,
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

/* ---------------- Phase 4-3: 추천 ---------------- */

export async function recommendLevers(
  payload: RecommendRequest
): Promise<RecommendResponse> {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`추천 실패: ${res.status} ${text}`);
  }
  return res.json();
}

/* ---------------- Phase 4-1: 시뮬레이션 ---------------- */

export async function simulateScenario(
  payload: SimulateRequest
): Promise<SimulateResponse> {
  const res = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`시뮬레이션 실패: ${res.status} ${text}`);
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

/* ---------------- Phase 4-4: 의존성 그래프 (ripple) ---------------- */

export type RippleNodeDTO = {
  kind: "field" | "rule" | "step";
  id: string;
  label: string;
  legal_anchor: string | null;
  depth: number;
};

export type RippleResponseDTO = {
  changed_field: string;
  field_label: string | null;
  nodes: RippleNodeDTO[];
  total_count: number;
};

export type FieldNodeDTO = {
  kind: "field" | "rule" | "step";
  id: string;
  label: string;
  legal_anchor?: string | null;
};

export type FieldsResponseDTO = {
  fields: FieldNodeDTO[];
};

export async function rippleFields(): Promise<FieldsResponseDTO> {
  return adminFetch("/ripple/fields");
}

export async function rippleFor(field: string): Promise<RippleResponseDTO> {
  return adminFetch(`/ripple/${encodeURIComponent(field)}`);
}

/* ---------------- Phase 4-2: RAG ---------------- */

export type IndexLawRequest = {
  law_id?: string | null;
  law_mst?: string | null;
  effective_date?: string | null;
  use_mst?: boolean;
  article_no?: string | null;
};

export type IndexLawResponse = {
  law_id: string;
  law_name: string;
  effective_date: string | null;
  chunks_indexed: number;
  embedding_model: string;
};

export type RagSearchRequest = {
  query: string;
  top_k?: number;
  law_id_filter?: string | null;
  article_no_filter?: string | null;
};

export type RagHit = {
  chunk: {
    chunk_id: string;
    law_id: string;
    law_name: string;
    article_no: string;
    paragraph_no: string | null;
    item_no: string | null;
    text: string;
    text_hash: string;
    effective_date: string | null;
    embedding_model: string;
  };
  score: number;
};

export type RagSearchResponse = {
  query: string;
  hits: RagHit[];
  total_indexed: number;
};

export type RagStatsEntry = {
  law_id: string;
  law_name: string;
  effective_date: string | null;
  chunks: number;
  indexed_at: string;
  embedding_model: string;
};

export type RagStatsResponse = {
  laws: RagStatsEntry[];
  total_chunks: number;
};

export async function ragIndexLaw(body: IndexLawRequest): Promise<IndexLawResponse> {
  return adminFetch("/rag/index", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function ragSearch(body: RagSearchRequest): Promise<RagSearchResponse> {
  return adminFetch("/rag/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function ragStats(): Promise<RagStatsResponse> {
  return adminFetch("/rag/stats");
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
