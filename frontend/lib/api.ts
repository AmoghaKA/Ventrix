import { supabase } from "./supabase";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

let analysesCache: { data: AnalysisRecord[]; fetchedAt: number } | null = null;
let analysesPromise: Promise<AnalysisRecord[]> | null = null;
const ANALYSES_CACHE_TTL = 5_000;

export function invalidateAnalysesCache() {
  analysesCache = null;
  analysesPromise = null;
}

let cachedToken: string | null = null;
let tokenExpiresAt = 0;
let tokenPromise: Promise<string | null> | null = null;

supabase.auth.onAuthStateChange(() => {
  cachedToken = null;
  tokenExpiresAt = 0;
  tokenPromise = null;
});

async function getAccessToken(): Promise<string | null> {
  const now = Date.now();
  if (cachedToken && now < tokenExpiresAt) return cachedToken;
  if (tokenPromise) return tokenPromise;

  tokenPromise = (async () => {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token ?? null;
      const expiresAt = (data.session?.expires_at ?? 0) * 1000;
      cachedToken = token;
      tokenExpiresAt = expiresAt
        ? Math.min(expiresAt - 60_000, Date.now() + 5 * 60_000)
        : Date.now() + 60_000;
      return token;
    } catch {
      cachedToken = null;
      tokenExpiresAt = 0;
      return null;
    } finally {
      tokenPromise = null;
    }
  })();

  return tokenPromise;
}

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

  const token = await getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
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

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function createAnalysis(
  input: AnalysisSubmission
): Promise<AnalysisRecord> {
  return apiRequest<AnalysisRecord>("/analyses", {
    method: "POST",
    body: JSON.stringify(input),
  }).then((result) => {
    invalidateAnalysesCache();
    return result;
  });
}

export function deleteAnalysis(analysisId: string | number): Promise<void> {
  return apiRequest<void>(`/analyses/${analysisId}`, { method: "DELETE" });
}

export function getAnalysis(
  analysisId: string | number
): Promise<AnalysisRecord> {
  return apiRequest<AnalysisRecord>(`/analyses/${analysisId}`);
}

export function listAnalyses(force = false): Promise<AnalysisRecord[]> {
  const now = Date.now();
  if (
    !force &&
    analysesCache &&
    now - analysesCache.fetchedAt < ANALYSES_CACHE_TTL
  ) {
    return Promise.resolve(analysesCache.data);
  }
  if (analysesPromise) return analysesPromise;
  analysesPromise = apiRequest<AnalysisRecord[]>("/analyses")
    .then((data) => {
      analysesCache = { data, fetchedAt: Date.now() };
      return data;
    })
    .finally(() => {
      analysesPromise = null;
    });
  return analysesPromise;
}


export interface WorkflowStatusRecord {
  id: number;
  analysis_id: number;
  startup_id: number | null;
  status: string;
  current_step: string | null;
  retry_limit: number;
  error_details: string | null;
  report: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface WorkflowAgentStatusRecord {
  id: number;
  workflow_id: number;
  analysis_id: number;
  agent_key: string;
  agent_name: string;
  sequence: number;
  status: string;
  attempt_count: number;
  output: Record<string, unknown> | null;
  error_details: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface WorkflowLogRecord {
  id: number;
  workflow_id: number;
  analysis_id: number;
  timestamp: string;
  level: string;
  event: string;
  agent_key: string | null;
  message: string;
  meta: Record<string, unknown>;
}

export interface AgentInfo {
  key: string;
  name: string;
  description: string;
}

export interface AgentRunResponse {
  analysis_id: number;
  startup_id: number;
  outputs: Array<Record<string, unknown>>;
}

export interface EvidenceRecord {
  id: number;
  startup_id: number;
  analysis_id: number;
  source_url: string;
  source_title: string;
  source_category: string;
  extracted_information: string;
  raw_text: string | null;
  publication_date: string | null;
  retrieval_date: string;
  verification_status: string;
  related_agent: string;
  findings: Array<Record<string, unknown>>;
  source_metadata: Record<string, unknown>;
  content_hash: string;
  created_at: string;
  updated_at: string | null;
}

export interface EvidenceSearchResponse {
  total: number;
  limit: number;
  offset: number;
  items: EvidenceRecord[];
}

export interface SystemStatus {
  api_status: string;
  database: string;
  analysis_count: number;
  max_analyses: number;
  providers: Array<{ name: string; configured: boolean; active: boolean }>;
  active_provider: string;
  fallback_history: string[];
  version: string;
}

export function listAgents(): Promise<AgentInfo[]> {
  return apiRequest<AgentInfo[]>("/agents");
}

export function startAnalysisWorkflow(
  analysisId: string | number,
  retryLimit = 2,
  maxPages = 5
): Promise<WorkflowStatusRecord> {
  return apiRequest<WorkflowStatusRecord>(
    `/analyses/${analysisId}/start?retry_limit=${retryLimit}&max_pages=${maxPages}`,
    { method: "POST" }
  );
}

export function getWorkflow(
  analysisId: string | number
): Promise<WorkflowStatusRecord> {
  return apiRequest<WorkflowStatusRecord>(`/analyses/${analysisId}/workflow`);
}

export function getWorkflowAgents(
  analysisId: string | number
): Promise<WorkflowAgentStatusRecord[]> {
  return apiRequest<WorkflowAgentStatusRecord[]>(
    `/analyses/${analysisId}/workflow/agents`
  );
}

export function getWorkflowLogs(
  analysisId: string | number,
  limit = 100,
  offset = 0
): Promise<WorkflowLogRecord[]> {
  return apiRequest<WorkflowLogRecord[]>(
    `/analyses/${analysisId}/workflow/logs?limit=${limit}&offset=${offset}`
  );
}

export function runAgent(
  analysisId: string | number,
  agentKey: string
): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>(
    `/analyses/${analysisId}/agents/${agentKey}/run`,
    { method: "POST" }
  );
}

export function runAgents(
  analysisId: string | number,
  agents?: string[]
): Promise<AgentRunResponse> {
  const query = agents?.length
    ? `?${agents.map((agent) => `agents=${encodeURIComponent(agent)}`).join("&")}`
    : "";
  return apiRequest<AgentRunResponse>(`/analyses/${analysisId}/agents/run${query}`, {
    method: "POST",
  });
}

export function verifyAnalysis(
  analysisId: string | number
): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>(`/analyses/${analysisId}/verify`, {
    method: "POST",
  });
}

export function getVerification(
  analysisId: string | number
): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>(`/analyses/${analysisId}/verification`);
}

export function getReport(
  analysisId: string | number
): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>(`/analyses/${analysisId}/report`);
}

export async function downloadReportPdf(
  analysisId: string | number
): Promise<Blob> {
  const token = await getAccessToken();
  const response = await fetch(
    `${API_BASE_URL}/api/v1/analyses/${analysisId}/report/pdf`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );
  if (!response.ok) throw new Error("Report download failed");
  return response.blob();
}

export function searchEvidence(params: {
  analysisId?: string | number;
  query?: string;
  category?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<EvidenceSearchResponse> {
  const search = new URLSearchParams();
  if (params.analysisId !== undefined)
    search.set("analysis_id", String(params.analysisId));
  if (params.query) search.set("q", params.query);
  if (params.category) search.set("category", params.category);
  if (params.status) search.set("verification_status", params.status);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  return apiRequest<EvidenceSearchResponse>(`/evidence?${search.toString()}`);
}

export function getEvidence(
  evidenceId: string | number
): Promise<EvidenceRecord> {
  return apiRequest<EvidenceRecord>(`/evidence/${evidenceId}`);
}

export function collectEvidence(
  analysisId: string | number,
  maxPages = 5
): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>(
    `/analyses/${analysisId}/collect-evidence?max_pages=${maxPages}`,
    { method: "POST" }
  );
}

export function getSystemStatus(): Promise<SystemStatus> {
  return apiRequest<SystemStatus>("/system/status");
}

export interface StartupSubmission {
  name: string;
  website: string;
  description?: string;
  industry?: string;
  stage?: string;
  location?: string;
}

export interface AnalysisStartResponse {
  analysis_id: number;
  status: string;
}

export interface SystemUsage {
  max_analyses: number;
  completed_analyses: number;
  reserved_analyses: number;
  remaining_analyses: number;
  limit_reached: boolean;
}

export async function createStartup(input: StartupSubmission): Promise<Record<string, unknown>> {
  const token = await getAccessToken();
  const response = await fetch(`${API_BASE_URL}/api/startup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error("Startup creation failed");
  return response.json();
}

export async function startAnalysis(input: AnalysisSubmission): Promise<AnalysisStartResponse> {
  const token = await getAccessToken();
  const response = await fetch(`${API_BASE_URL}/api/analysis/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      message = (data as { detail?: string }).detail ?? message;
    } catch {}
    throw new Error(message);
  }
  const result = (await response.json()) as AnalysisStartResponse;
  invalidateAnalysesCache();
  return result;
}

export async function getSystemUsage(): Promise<SystemUsage> {
  const token = await getAccessToken();
  const response = await fetch(`${API_BASE_URL}/api/system/usage`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error("Failed to load usage");
  return response.json() as Promise<SystemUsage>;
}

export interface UserProfile {
  id: string;
  full_name: string | null;
  email: string | null;
  avatar_url: string | null;
  company: string | null;
  role: string | null;
  bio: string | null;
  timezone: string | null;
  language: string | null;
  preferences: Record<string, unknown> | null;
  notifications: Record<string, unknown> | null;
  security: Record<string, unknown> | null;
}

export function getProfile(): Promise<UserProfile> {
  return apiRequest<UserProfile>("/profile");
}

export function updateProfile(
  data: Partial<Omit<UserProfile, "id">>
): Promise<UserProfile> {
  return apiRequest<UserProfile>("/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
