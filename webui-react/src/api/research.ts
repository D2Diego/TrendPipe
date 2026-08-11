import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export type ResearchDepth = "quick" | "deep";
export type ResearchStatus = "pending" | "running" | "completed" | "failed";

export interface ReportCandidate {
  title?: string;
  url?: string;
  source?: string;
  snippet?: string;
  [key: string]: unknown;
}

export interface ReportCluster {
  cluster_id: string;
  title?: string;
  score?: number;
  fun_score?: number;
  explanation?: string;
  why_ranked?: string;
  sources?: string[];
  links?: string[];
  candidates?: ReportCandidate[];
  items?: ReportCandidate[];
  [key: string]: unknown;
}

export interface ResearchReport {
  entities: Array<{
    entity: string;
    report: { clusters?: ReportCluster[]; [key: string]: unknown };
  }>;
}

export const ARTIFACT_FIELDS = [
  "video_subject",
  "video_script_prompt",
  "custom_system_prompt",
  "video_script",
  "video_terms",
] as const;
export type ArtifactField = (typeof ARTIFACT_FIELDS)[number];

export interface ArtifactChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ResearchArtifact {
  id: string;
  research_id: string;
  entity: string;
  cluster_id: string;
  video_subject: string;
  video_script: string | null;
  video_script_prompt: string | null;
  custom_system_prompt: string | null;
  video_terms: string[] | null;
  generated_fields: ArtifactField[];
  created_at: string;
  updated_at: string;
}

export type ArtifactChatTurn =
  | { type: "question"; message: string }
  | { type: "final"; message: string; artifact: ResearchArtifact };

export interface Research {
  id: string;
  topic: string;
  depth: ResearchDepth;
  sources: string[];
  status: ResearchStatus;
  error_message: string | null;
  report_json: ResearchReport | null;
  artifacts?: ResearchArtifact[];
  created_at: string;
  updated_at: string;
}

export interface CreateResearchInput {
  topic: string;
  depth: ResearchDepth;
  sources: string[];
}

export interface CredentialStatus {
  present: boolean;
  label: string;
}

export interface ResearchSettings {
  available_sources: string[];
  permission_preflight?: {
    credentials?: Record<string, CredentialStatus>;
  };
  credential_keys?: Record<string, boolean>;
}

export const listResearches = () =>
  apiGet<{ researches: Research[] }>("/researches");
export const createResearch = (input: CreateResearchInput) =>
  apiPost<Research>("/researches", input);
export const getResearch = (researchId: string) =>
  apiGet<Research>(`/researches/${encodeURIComponent(researchId)}`);
export const deleteResearch = (researchId: string) =>
  apiDelete<{ deleted: boolean }>(`/researches/${encodeURIComponent(researchId)}`);
export const getResearchSettings = () =>
  apiGet<ResearchSettings>("/research-settings");
export const updateResearchSettings = (values: Record<string, string>) =>
  apiPut<{ saved: boolean }>("/research-settings", { values });
export const deleteResearchCredential = (key: string) =>
  apiDelete<{ deleted: boolean }>(`/research-settings/${encodeURIComponent(key)}`);

function clusterArtifactPath(researchId: string, entity: string, clusterId: string) {
  return `/researches/${encodeURIComponent(researchId)}/entities/${encodeURIComponent(entity)}/clusters/${encodeURIComponent(clusterId)}`;
}

export const postArtifactChat = (
  researchId: string,
  entity: string,
  clusterId: string,
  selectedFields: ArtifactField[],
  messages: ArtifactChatMessage[],
) =>
  apiPost<ArtifactChatTurn>(`${clusterArtifactPath(researchId, entity, clusterId)}/artifact-chat`, {
    selected_fields: selectedFields,
    messages,
  });

export const getArtifactRestoreParams = (researchId: string, entity: string, clusterId: string) =>
  apiGet<{ params: Record<string, unknown> }>(`${clusterArtifactPath(researchId, entity, clusterId)}/restore-params`);

export const deleteArtifact = (researchId: string, entity: string, clusterId: string) =>
  apiDelete<{ deleted: boolean }>(`${clusterArtifactPath(researchId, entity, clusterId)}/artifacts`);
