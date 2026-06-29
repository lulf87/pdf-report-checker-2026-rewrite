export type Confidence = "high" | "medium" | "low";
export type SourceType = "report" | "ptr" | "system";
export type EvidenceMethod = "pdf_text" | "pdf_layout" | "ocr" | "vlm" | "llm" | "manual" | "system";
export type FindingSeverity = "error" | "warn" | "info";
export type UserFacingFindingStatus = "confirmed_error" | "needs_review" | "candidate_issue" | "refuted" | "passed";
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
  if (severity === "error") return "候选错误";
  if (severity === "warn") return "需复核";
  return "信息";
}

export function severityTone(severity?: FindingSeverity | null): "danger" | "warn" | "info" {
  if (severity === "error") return "danger";
  if (severity === "warn") return "warn";
  return "info";
}

export function findingUserFacingStatus(
  finding: Finding,
  codexFinalStatus?: string | null,
): UserFacingFindingStatus {
  const metadataStatus = metadataString(finding.metadata, "user_facing_status");
  if (isUserFacingFindingStatus(metadataStatus)) return metadataStatus;

  if (codexFinalStatus === "confirmed") return finding.severity === "error" ? "confirmed_error" : "needs_review";
  if (codexFinalStatus === "refuted") return "refuted";
  if (codexFinalStatus === "manual_review_required") return "needs_review";

  if (finding.severity === "error") return "candidate_issue";
  if (finding.severity === "warn") return "needs_review";
  return "passed";
}

export function findingUserFacingStatusLabel(status: UserFacingFindingStatus, finding?: Finding): string {
  if (status === "confirmed_error") return "确认错误";
  if (status === "refuted") return "已反驳";
  if (status === "candidate_issue") return "候选问题";
  if (status === "passed") return "通过";
  if (finding?.code === "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN") return "表格抽取不确定/需视觉复核";
  if (finding?.code === "CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX") return "复杂矩阵需复核";
  if (finding?.code === "OCR_EVIDENCE_INSUFFICIENT" || finding?.code === "NEEDS_VISUAL_REVIEW") {
    return "OCR 证据不足/需视觉复核";
  }
  return "需人工复核";
}

export function findingUserFacingStatusTone(
  status: UserFacingFindingStatus,
): "success" | "danger" | "warn" | "info" {
  if (status === "confirmed_error") return "danger";
  if (status === "needs_review" || status === "candidate_issue") return "warn";
  if (status === "passed") return "success";
  return "info";
}

function metadataString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function isUserFacingFindingStatus(value: string | null): value is UserFacingFindingStatus {
  return (
    value === "confirmed_error" ||
    value === "needs_review" ||
    value === "candidate_issue" ||
    value === "refuted" ||
    value === "passed"
  );
}
