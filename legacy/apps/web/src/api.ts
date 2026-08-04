import type {
  BusinessBrief,
  Calibration,
  Cohort,
  CohortBody,
  CoverageResponse,
  CreateProjectBody,
  CreateSourceBody,
  CreateTokenBody,
  EvaluationBody,
  EvaluationsResponse,
  Gap,
  GapDetail,
  JourneyStage,
  OfferBody,
  Project,
  Run,
  ShadowCandidate,
  Source,
  SourcesResponse,
  TokenResult,
  UploadSourceBody,
  UploadSourceResult,
} from "./types";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://localhost:3001";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  if (options.body !== undefined && !("Content-Type" in headers)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  const text = await res.text();
  let parsed: unknown = undefined;
  if (text.length > 0) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!res.ok) {
    const message =
      parsed !== null &&
      typeof parsed === "object" &&
      "message" in parsed &&
      typeof (parsed as Record<string, unknown>).message === "string"
        ? ((parsed as Record<string, unknown>).message as string)
        : `Request failed with status ${res.status}`;
    throw new ApiError(res.status, message, parsed);
  }

  return parsed as T;
}

function jsonBody(data: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(data) };
}

export const api = {
  // Health
  health: () => request<{ status?: string; [k: string]: unknown }>("/api/v1/health"),

  // Projects
  createProject: (body: CreateProjectBody) =>
    request<Project>("/api/v1/projects", jsonBody(body)),
  getProject: (projectId: string) =>
    request<Project>(`/api/v1/projects/${projectId}`),

  // Business brief
  putBusinessBrief: (projectId: string, body: BusinessBrief) =>
    request<BusinessBrief>(
      `/api/v1/projects/${projectId}/business-brief`,
      jsonBody(body),
    ),
  getBusinessBrief: (projectId: string) =>
    request<BusinessBrief>(`/api/v1/projects/${projectId}/business-brief`),

  // Offers
  createOffer: (projectId: string, body: OfferBody) =>
    request<{ id: string }>(
      `/api/v1/projects/${projectId}/offers`,
      jsonBody(body),
    ),

  // Cohorts
  createCohort: (projectId: string, body: CohortBody) =>
    request<Cohort>(`/api/v1/projects/${projectId}/cohorts`, jsonBody(body)),
  getCohorts: (projectId: string) =>
    request<Cohort[]>(`/api/v1/projects/${projectId}/cohorts`),

  // Sources
  createSource: (projectId: string, body: CreateSourceBody) =>
    request<Source>(`/api/v1/projects/${projectId}/sources`, jsonBody(body)),
  uploadSource: (projectId: string, body: UploadSourceBody) =>
    request<UploadSourceResult>(
      `/api/v1/projects/${projectId}/sources/upload`,
      jsonBody(body),
    ),
  getSources: (projectId: string) =>
    request<SourcesResponse>(`/api/v1/projects/${projectId}/sources`),

  // Runs
  getRuns: (projectId: string) =>
    request<Run[]>(`/api/v1/projects/${projectId}/runs`),

  // Gaps
  getGaps: (
    projectId: string,
    filters?: { cohortId?: string; journeyStage?: JourneyStage },
  ) => {
    const params = new URLSearchParams();
    if (filters?.cohortId) params.set("cohortId", filters.cohortId);
    if (filters?.journeyStage) params.set("journeyStage", filters.journeyStage);
    const qs = params.toString();
    return request<Gap[]>(
      `/api/v1/projects/${projectId}/gaps${qs ? `?${qs}` : ""}`,
    );
  },
  getGap: (gapId: string) => request<GapDetail>(`/api/v1/gaps/${gapId}`),

  // Coverage
  getCoverage: (projectId: string) =>
    request<CoverageResponse>(`/api/v1/projects/${projectId}/coverage`),

  // Evaluations
  createGapEvaluation: (gapId: string, body: EvaluationBody) =>
    request<unknown>(`/api/v1/gaps/${gapId}/evaluations`, jsonBody(body)),
  createCandidateEvaluation: (candidateId: string, body: EvaluationBody) =>
    request<unknown>(
      `/api/v1/candidates/${candidateId}/evaluations`,
      jsonBody(body),
    ),
  getEvaluations: (projectId: string) =>
    request<EvaluationsResponse>(`/api/v1/projects/${projectId}/evaluations`),

  // Shadow sample
  getShadowSample: (projectId: string) =>
    request<ShadowCandidate[]>(`/api/v1/projects/${projectId}/shadow-sample`),

  // Tokens
  createToken: (body: CreateTokenBody) =>
    request<TokenResult>("/api/v1/tokens", jsonBody(body)),
};

export type { Calibration };
