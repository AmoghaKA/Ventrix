export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface AnalysisSubmission {
  startup_name: string;
  website: string;
  country?: string;
  industry?: string;
  additional_information?: string;
}

export interface AnalysisRecord {
  id: number;
  startup_name: string;
  website: string;
  country: string | null;
  industry: string | null;
  additional_information: string | null;
  status: string;
  overall_assessment: string | null;
  created_at: string;
  updated_at: string | null;
}

function extractErrorDetail(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;

  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return typeof item === "string" ? item : null;
      })
      .filter(Boolean);

    if (messages.length > 0) return messages.join("; ");
  }

  return null;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}/api/v1${endpoint}`;
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      message = extractErrorDetail(data) ?? message;
    } catch {
      // Keep the status-based fallback when the response has no JSON body.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function createAnalysis(
  input: AnalysisSubmission
): Promise<AnalysisRecord> {
  return apiRequest<AnalysisRecord>("/analyses", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getAnalysis(
  analysisId: string | number
): Promise<AnalysisRecord> {
  return apiRequest<AnalysisRecord>(`/analyses/${analysisId}`);
}

export function listAnalyses(): Promise<AnalysisRecord[]> {
  return apiRequest<AnalysisRecord[]>("/analyses");
}
