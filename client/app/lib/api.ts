import type { ParsedPdfData, AnalyzeRequest, AnalyzeResponse } from "./types";

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

export async function postManualInput(payload: any): Promise<any> {
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
