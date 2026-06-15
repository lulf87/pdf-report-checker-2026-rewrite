export type Confidence = "high" | "medium" | "low";
export type SourceType = "report" | "ptr" | "system";
export type EvidenceMethod = "pdf_text" | "pdf_layout" | "ocr" | "vlm" | "llm" | "manual" | "system";
export type FindingSeverity = "error" | "warn" | "info";
export type DiffFragmentKind = "equal" | "insert" | "delete" | "replace";

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface Location {
  source_id?: string | null;
  source_type?: SourceType | null;
  page_number?: number | null;
  bbox?: BoundingBox | null;
  section?: string | null;
  table_id?: string | null;
  row_index?: number | null;
  column_name?: string | null;
  text_span?: [number, number] | null;
  description?: string | null;
}

export interface Evidence {
  id: string;
  source_type: SourceType;
  location?: Location | null;
  raw_text?: string | null;
  normalized_text?: string | null;
  value?: string | null;
  method?: EvidenceMethod | null;
  confidence?: Confidence | null;
  image_ref?: string | null;
  metadata: Record<string, unknown>;
}

export interface MissingEvidence {
  label: string;
  reason: string;
  expected_source?: SourceType | null;
  location?: Location | null;
  metadata: Record<string, unknown>;
}

export interface DiffFragment {
  kind: DiffFragmentKind;
  text: string;
  source?: string | null;
}

export interface Finding {
  id: string;
  task_id: string;
  check_id: string;
  severity: FindingSeverity;
  code: string;
  message: string;
  location?: Location | null;
  expected?: unknown;
  actual?: unknown;
  evidence: Evidence[];
  missing_evidence: MissingEvidence[];
  diff_fragments: DiffFragment[];
  confidence: Confidence;
  metadata: Record<string, unknown>;
}

export function severityLabel(severity: FindingSeverity): string {
  if (severity === "error") return "错误";
  if (severity === "warn") return "需复核";
  return "信息";
}

export function severityTone(severity?: FindingSeverity | null): "danger" | "warn" | "info" {
  if (severity === "error") return "danger";
  if (severity === "warn") return "warn";
  return "info";
}
