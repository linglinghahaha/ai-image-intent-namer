export interface BackendPreviewItem {
  index: number;
  src: string;
  display_name?: string;
  block_index: number;
  image_index: number;
  normalized_title?: string;
  candidates?: Array<{
    name: string;
    reason?: string;
    confidence?: number;
    strategy?: string;
  }>;
  above_text?: string;
  below_text?: string;
  between_text?: string;
  alt?: string;
  title_attr?: string;
  explicit_refs?: string[];
}

export interface BackendPreviewResponse {
  document: string;
  title: string;
  count: number;
  items: BackendPreviewItem[];
}
