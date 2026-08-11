import type { ReactNode } from "react";

import { Badge } from "../../shared/ui/Badge";
import { GlassCard } from "../../shared/ui/GlassCard";

type LandingIconName =
  | "clipboard-check"
  | "download"
  | "file"
  | "files"
  | "history"
  | "link"
  | "list-checks"
  | "scan";

interface ModuleEntry {
  id: string;
  badge: string;
  title: string;
  input: string;
  scope: string;
  output: string;
  href: string;
  action: string;
  icon: LandingIconName;
}

const modules: ModuleEntry[] = [
  {
    id: "report-check",
    badge: "REPORT CHECK",
    title: "报告自身核对",
    input: "单份检验报告 PDF",
    scope: "C01-C11",
    output: "核对结果、Finding、定位证据与导出",
    href: "#/report-check",
    action: "开启核对任务",
    icon: "file",
  },
  {
    id: "ptr-compare",
    badge: "PTR COMPARE",
    title: "PTR 条款核对",
    input: "PTR PDF + 检验报告 PDF",
    scope: "第 2 章条款与表格参数",
    output: "条款/表格参数差异、Finding 与定位证据",
    href: "#/ptr-compare",
    action: "开启比对任务",
    icon: "files",
  },
];

const workflow = [
  {
    title: "PDF 解析 / OCR",
    description: "提取文本、表格和页面证据",
    icon: "scan" as const,
    tone: "default",
  },
  {
    title: "规则核对",
    description: "执行 C01-C11 与 PTR 条款、参数核对",
    icon: "list-checks" as const,
    tone: "rules",
  },
  {
    title: "自动结果复核",
    description: "结合文档证据消除误报，形成最终结论",
    icon: "clipboard-check" as const,
    tone: "codex",
  },
  {
    title: "证据与导出",
    description: "展示定位与证据，支持 JSON / PDF / XLSX",
    icon: "download" as const,
    tone: "default",
  },
];

const capabilities = [
  { label: "报告自身核对", value: "C01-C11" },
  { label: "PTR 覆盖", value: "第 2 章" },
  { label: "导出格式", value: "JSON / PDF / XLSX" },
  { label: "Backend", value: "FastAPI Contract" },
];

const auditChain = [
  { label: "定位", value: "来源页 · 字段 / 表格行 / caption" },
  { label: "规则核对", value: "字段、条款与参数逐项检查" },
  { label: "自动复核", value: "确认最终问题或转入人工复核" },
  { label: "最终结果", value: "通过 / 不通过 / 需人工复核" },
];

export function DashboardPage() {
  return (
    <div className="landing-page">
      <nav className="landing-nav" aria-label="首页导航">
        <div className="landing-container landing-nav-inner">
          <div className="landing-nav-start">
            <a className="landing-wordmark" href="#/">
              Report Checker Pro
            </a>
            <div className="landing-nav-links">
              <a href="#/">首页</a>
              <a href="#modules">功能</a>
              <a href="#workflow">工作流程</a>
              <a href="#evidence">审核证据</a>
            </div>
          </div>
          <Badge variant="accent">FastAPI Contract</Badge>
        </div>
      </nav>

      <main className="landing-container landing-main">
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="landing-hero-copy">
            <div>
              <p className="eyebrow">医疗器械检验报告核对工作台</p>
              <h1 id="landing-title">
                医疗器械检验报告核对
                <span>规则与证据清晰可追溯</span>
              </h1>
              <p className="landing-hero-description">
                上传检验报告或 PTR PDF，由后端完成 C01-C11、PTR 条款与表格参数核对；前端集中展示
                最终核对结果、定位证据和导出文件。
              </p>
            </div>

            <div className="landing-actions" aria-label="核对任务入口">
              <a className="button button-primary button-lg landing-cta" href="#/report-check">
                <LandingIcon name="file" />
                报告自身核对
              </a>
              <a className="button button-secondary button-lg landing-cta" href="#/ptr-compare">
                <LandingIcon name="files" />
                PTR 条款核对
              </a>
            </div>
          </div>

          <GlassCard className="landing-workflow" id="workflow">
            <p className="eyebrow">工作流程</p>
            <ol className="landing-workflow-list">
              {workflow.map((stage) => (
                <li className={`landing-workflow-step landing-workflow-step-${stage.tone}`} key={stage.title}>
                  <span className="landing-icon-box" aria-hidden="true">
                    <LandingIcon name={stage.icon} />
                  </span>
                  <div>
                    <h2>{stage.title}</h2>
                    <p>{stage.description}</p>
                  </div>
                </li>
              ))}
            </ol>
          </GlassCard>
        </section>

        <GlassCard className="landing-capability-strip" aria-label="产品能力">
          {capabilities.map((capability) => (
            <div className="landing-capability" key={capability.label}>
              <p>{capability.label}</p>
              <strong>{capability.value}</strong>
            </div>
          ))}
        </GlassCard>

        <section className="landing-module-selection" id="modules" aria-label="核对模块">
          {modules.map((module) => (
            <GlassCard className="landing-module-card" hover key={module.id}>
              <div>
                <div className="landing-module-head">
                  <Badge variant="accent">{module.badge}</Badge>
                  <span className="landing-module-icon" aria-hidden="true">
                    <LandingIcon name={module.icon} />
                  </span>
                </div>
                <h2>{module.title}</h2>
                <dl className="landing-module-facts">
                  <div>
                    <dt>输入</dt>
                    <dd>{module.input}</dd>
                  </div>
                  <div>
                    <dt>范围</dt>
                    <dd>{module.scope}</dd>
                  </div>
                  <div>
                    <dt>输出</dt>
                    <dd>{module.output}</dd>
                  </div>
                </dl>
              </div>
              <a className="button button-primary button-lg landing-module-action" href={module.href}>
                {module.action}
              </a>
            </GlassCard>
          ))}
        </section>

        <GlassCard className="landing-evidence-panel" id="evidence">
          <section className="landing-evidence-copy" aria-labelledby="evidence-title">
            <p className="eyebrow">分层审计链路</p>
            <h2 id="evidence-title">最终结果与证据链</h2>
            <p className="landing-evidence-description">
              普通页面只展示最终确认问题、待人工复核项和通过结论；内部核对过程保留在审计记录中，
              不干扰日常使用。
            </p>

            <div className="landing-evidence-notes">
              <EvidenceNote icon="link" title="定位证据">
                核对结果包含来源页、字段、表格行、caption 或缺失证据说明。
              </EvidenceNote>
              <EvidenceNote icon="history" title="审核记录">
                系统内部保留完整审计记录，用户页面以最终核对结论为准。
              </EvidenceNote>
            </div>
          </section>

          <section className="landing-audit-card" aria-labelledby="audit-chain-title">
            <header className="landing-audit-head">
              <h3 id="audit-chain-title">Finding 审计链</h3>
              <span>由后端结果返回</span>
            </header>
            <dl className="landing-audit-list">
              {auditChain.map((item) => (
                <div className="landing-audit-row" key={item.label}>
                  <dt>{item.label}</dt>
                  <dd>{item.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        </GlassCard>
      </main>

      <footer className="landing-footer">
        <div className="landing-container landing-footer-inner">
          <p>Report Checker Pro</p>
          <p>FastAPI · React · TypeScript · Vite</p>
        </div>
      </footer>
    </div>
  );
}

function EvidenceNote({ children, icon, title }: { children: ReactNode; icon: LandingIconName; title: string }) {
  return (
    <div className="landing-evidence-note">
      <span className="landing-note-icon" aria-hidden="true">
        <LandingIcon name={icon} />
      </span>
      <div>
        <h3>{title}</h3>
        <p>{children}</p>
      </div>
    </div>
  );
}

function LandingIcon({ name }: { name: LandingIconName }) {
  return (
    <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24">
      {iconPaths[name]}
    </svg>
  );
}

const iconPaths: Record<LandingIconName, ReactNode> = {
  file: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6M8 13h8M8 17h6" />
    </>
  ),
  files: (
    <>
      <path d="M15 2H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V6Z" />
      <path d="M15 2v4h4M9 10h6M9 14h5M7 22h10a4 4 0 0 0 4-4V8" />
    </>
  ),
  scan: (
    <>
      <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" />
      <path d="M7 12h10M9 8h6M9 16h6" />
    </>
  ),
  "list-checks": (
    <>
      <path d="m3 6 2 2 4-4M3 14l2 2 4-4M13 6h8M13 14h8M13 20h8" />
    </>
  ),
  "clipboard-check": (
    <>
      <rect width="14" height="18" x="5" y="4" rx="2" />
      <path d="M9 4V2h6v2M9 13l2 2 4-4" />
    </>
  ),
  download: (
    <>
      <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
    </>
  ),
  link: (
    <>
      <path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1" />
      <path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1" />
    </>
  ),
  history: (
    <>
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
      <path d="M3 3v5h5M12 7v5l3 2" />
    </>
  ),
};
