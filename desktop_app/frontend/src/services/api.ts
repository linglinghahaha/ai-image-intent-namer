import type {
  BackendApplyResponse,
  BackendCandidateResponse,
  BackendLogEntry,
  BackendPreviewResponse,
} from "@desktop/types/backend";

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

const API_BASE =
  (import.meta.env.VITE_BACKEND_URL as string | undefined)?.replace(/\/+$/, "") ||
  DEFAULT_BASE_URL;

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Backend request failed (${response.status}): ${text || response.statusText}`,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface PreviewRequestPayload {
  md_path: string;
  ai: Record<string, unknown>;
  naming: Record<string, unknown>;
  runtime: Record<string, unknown>;
}

export interface ApplyRequestPayload extends PreviewRequestPayload {
  chosen_map: Record<number, string>;
  skip_indexes: number[];
}

export const apiClient = {
  baseUrl(): string {
    return API_BASE;
  },

  async listProfiles(): Promise<Record<string, unknown>> {
    return request("/api/v1/profiles");
  },

  async saveProfile(name: string, payload: Record<string, unknown>): Promise<void> {
    await request(`/api/v1/profiles/${encodeURIComponent(name)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async deleteProfile(name: string): Promise<void> {
    await request(`/api/v1/profiles/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
  },

  async listTemplates(): Promise<Record<string, unknown>> {
    return request("/api/v1/templates");
  },

  async saveTemplate(name: string, payload: Record<string, unknown>): Promise<void> {
    await request(`/api/v1/templates/${encodeURIComponent(name)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async deleteTemplate(name: string): Promise<void> {
    await request(`/api/v1/templates/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
  },

  async previewDocument(payload: PreviewRequestPayload): Promise<BackendPreviewResponse> {
    return request<BackendPreviewResponse>("/api/v1/documents/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async generateCandidates(payload: Record<string, unknown>): Promise<BackendCandidateResponse> {
    return request<BackendCandidateResponse>("/api/v1/candidates", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async applyDocument(payload: ApplyRequestPayload): Promise<BackendApplyResponse> {
    return request<BackendApplyResponse>("/api/v1/documents/apply", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async processText(payload: Record<string, unknown>): Promise<{ result: string; logs?: BackendLogEntry[] }> {
    return request<{ result: string; logs?: BackendLogEntry[] }>("/api/v1/text/process", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};

export type ApiClient = typeof apiClient;
