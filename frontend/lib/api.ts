export type RepositoryInfo = {
  owner: string;
  name: string;
  full_name: string;
  html_url: string;
  description: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  primary_language: string | null;
  license: string | null;
  default_branch: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type HealthCheck = {
  key: string;
  label: string;
  passed: boolean;
  detail: string;
};

export type Language = {
  name: string;
  bytes: number;
  percentage: number;
};

export type Commit = {
  sha: string;
  message: string;
  author: string;
  date: string | null;
  url: string | null;
};

export type Contributor = {
  login: string;
  avatar_url: string | null;
  contributions: number;
  url: string | null;
};

export type RepositoryAnalysis = {
  repository: RepositoryInfo;
  health_score: number;
  health_checks: HealthCheck[];
  languages: Language[];
  recent_commits: Commit[];
  contributors: Contributor[];
  generated_at: string;
  score_note: string;
};

export type HistoryItem = {
  id: number;
  repository: string;
  github_url: string;
  health_score: number;
  created_at: string | null;
};

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal, cache: "no-store" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  return data as T;
}

export function analyzeRepository(owner: string, repo: string, signal?: AbortSignal) {
  return request<RepositoryAnalysis>(
    `/api/analyze/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`,
    signal,
  );
}

export function getHistory(signal?: AbortSignal) {
  return request<HistoryItem[]>("/api/history?limit=8", signal);
}
