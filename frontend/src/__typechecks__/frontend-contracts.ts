import { ApiError, apiClient } from "../shared/api/client";
import type { CodexReviewResult } from "../entities/codexReview/types";
import { groupCodexReviewsByFinding, normalizeCodexReviews, summarizeCodexReviews } from "../entities/codexReview/types";
import type { Finding } from "../entities/finding/types";
import type { PTRClauseViewModel } from "../entities/ptr/types";
import type { ReportCheckResultView } from "../entities/report/types";
import type { CheckResult, TaskResult, TaskStatus } from "../entities/task/types";
import { uploadPTRCompareFiles } from "../features/ptr-compare/api";
import { PTRComparePage } from "../features/ptr-compare/pages/PTRComparePage";
import { uploadReportCheckFile } from "../features/report-check/api";
import { ReportCheckPage } from "../features/report-check/pages/ReportCheckPage";
import { AnimatedCounter } from "../shared/ui/AnimatedCounter";
import { Badge } from "../shared/ui/Badge";
import { Button } from "../shared/ui/Button";
import { ExportButton } from "../shared/ui/ExportButton";
import { FileUpload } from "../shared/ui/FileUpload";
import { GlassCard } from "../shared/ui/GlassCard";
import { ProgressOverlay } from "../shared/ui/ProgressOverlay";

const task: TaskStatus = {
  task_id: "task-1",
  task_type: "report_check",
  status: "completed",
  progress: 100,
  current_step: "completed",
  input_files: [],
  result_ref: "task-1",
  error_message: null,
  logs: [],
  created_at: "2026-06-14T00:00:00Z",
  updated_at: "2026-06-14T00:00:01Z",
};

const finding: Finding = {
  id: "finding-1",
  task_id: task.task_id,
  check_id: "C01",
  severity: "error",
  code: "C01_FIELD_MISMATCH",
  message: "字段不一致",
  confidence: "high",
  evidence: [],
  missing_evidence: [],
  diff_fragments: [],
  metadata: {},
};

const result: TaskResult = {
  task_id: task.task_id,
  task_type: "report_check",
  summary: {
    total_checks: 1,
    pass_count: 0,
    fail_count: 1,
    review_count: 0,
    skip_count: 0,
    system_error_count: 0,
    error_count: 1,
    warn_count: 0,
    info_count: 0,
  },
  check_results: [
    {
      task_id: task.task_id,
      check_id: "C01",
      check_name: "首页与第三页字段一致性",
      status: "fail",
      severity: "error",
      summary: "字段不一致",
      findings: [finding],
      evidence: [],
      metrics: {},
      metadata: {},
    },
  ],
  findings: [finding],
  input_files: [],
  diagnostics: [],
  metadata: {},
};

const codexReview: CodexReviewResult = {
  review_id: "codex-review-1",
  request_id: "codex-request-1",
  task_id: task.task_id,
  target: {
    target_id: "target-1",
    target_type: "label_ocr",
    check_id: finding.check_id,
    finding_id: finding.id,
    finding_code: finding.code,
    title: "标签字段复核",
    summary: "标签字段复核",
    evidence_refs: [
      {
        ref_id: "finding:finding-1",
        source_type: "finding",
        path: null,
        page_number: 3,
        section: "C02",
        description: "规则初判 finding",
        metadata: {},
      },
    ],
    metadata: {},
  },
  status: "succeeded",
  verdict: "confirm",
  confidence: "high",
  reasoning_summary: "Codex 确认规则初判成立。",
  suggested_severity: null,
  suggested_finding: null,
  evidence_refs: ["finding:finding-1"],
  raw_output_path: null,
  error: null,
  created_at: "2026-06-14T00:00:02Z",
  completed_at: "2026-06-14T00:00:03Z",
  metadata: {},
};

const checkResultWithCodex: CheckResult = {
  ...result.check_results[0],
  codex_reviews: [codexReview],
};

const legacyCheckResultWithoutCodexReviews: CheckResult = {
  ...result.check_results[0],
};

const groupedCodexReviews = groupCodexReviewsByFinding([finding], checkResultWithCodex.codex_reviews);
const codexReviewSummary = summarizeCodexReviews(checkResultWithCodex.codex_reviews);
const legacyCodexReviews = normalizeCodexReviews(legacyCheckResultWithoutCodexReviews.codex_reviews);

const ptrClause: PTRClauseViewModel = {
  id: "PTR_CLAUSE-0",
  checkId: "PTR_CLAUSE",
  title: "PTR 条款正文一致性",
  status: "fail",
  severity: "error",
  summary: "条款不一致",
  findings: [finding],
  diffs: finding.diff_fragments,
  codexReviews: [codexReview],
};

const reportView: ReportCheckResultView = {
  task: task,
  result,
  visibleFindings: [finding],
};

void apiClient;
void ApiError;
void uploadPTRCompareFiles;
void uploadReportCheckFile;
void PTRComparePage;
void ReportCheckPage;
void AnimatedCounter;
void Badge;
void Button;
void ExportButton;
void FileUpload;
void GlassCard;
void ProgressOverlay;
void ptrClause;
void reportView;
void groupedCodexReviews;
void codexReviewSummary;
void legacyCodexReviews;
