export interface BackendCandidate {
  name: string;
  reason?: string;
  confidence?: number;
  strategy?: string;
}

export interface BackendLogEntry {
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  ts?: number;
  extra?: unknown;
}

export interface BackendPreviewItem {
  index: number;
  src: string;
  display_name?: string;
  block_index: number;
  image_index: number;
  normalized_title?: string;
  suggested_name?: string;
  best?: string;
  candidates?: BackendCandidate[];
  above_text?: string;
  below_text?: string;
  between_text?: string;
  explicit_refs?: string[];
  alt?: string;
  title_attr?: string;
  ai_error?: string | null;
  ai_raw?: string | null;
  request_mode?: string | null;
}

export interface BackendPreviewResponse {
  document: string;
  title: string;
  count: number;
  items: BackendPreviewItem[];
  logs?: BackendLogEntry[];
}

export interface BackendCandidateResponse {
  normalized_title?: string;
  best?: string;
  candidates: BackendCandidate[];
}

export interface BackendApplyResponse {
  document: string;
  updated: boolean;
  skip_indexes: number[];
  applied: number[];
  logs?: BackendLogEntry[];
}
