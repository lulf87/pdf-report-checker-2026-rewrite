import type { Finding, FindingSeverity } from "../finding/types";
import type { CheckResult, TaskResult, TaskStatus } from "../task/types";

export type ReportRuleId =
  | "C01"
  | "C02"
  | "C03"
  | "C04"
  | "C05"
  | "C06"
  | "C07"
  | "C08"
  | "C09"
  | "C10"
  | "C11";

export type ReportSeverityFilter = "all" | FindingSeverity;

export interface ReportCheckResultView {
  task: TaskStatus;
  result: TaskResult;
  visibleFindings: Finding[];
}

export interface ReportRuleGroup {
  title: string;
  description: string;
  checkIds: ReportRuleId[];
}

export const REPORT_RULE_GROUPS: ReportRuleGroup[] = [
  {
    title: "字段核对",
    description: "首页、第三页、标签 OCR 相关字段。",
    checkIds: ["C01", "C02", "C03"],
  },
  {
    title: "样品与标签",
    description: "样品描述、照片覆盖和中文标签覆盖。",
    checkIds: ["C04", "C05", "C06"],
  },
  {
    title: "检验项目表",
    description: "单项结论、非空字段、序号和续表。",
    checkIds: ["C07", "C08", "C09", "C10"],
  },
  {
    title: "页码",
    description: "报告页码连续性。",
    checkIds: ["C11"],
  },
];

export function checkResultSeverity(result: CheckResult): FindingSeverity {
  if (result.severity) return result.severity;
  if (result.status === "fail") return "error";
  if (result.status === "review" || result.status === "system_error") return "warn";
  return "info";
}
