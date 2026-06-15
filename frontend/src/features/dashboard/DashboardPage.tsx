import { Badge } from "../../shared/ui/Badge";
import { Button } from "../../shared/ui/Button";
import { GlassCard } from "../../shared/ui/GlassCard";

const modules = [
  {
    id: "report-check",
    title: "报告自身核对",
    description: "上传单份检验报告 PDF，展示后端 C01-C11 规则结果、证据和导出入口。",
    path: "/report-check",
    badge: "C01-C11",
  },
  {
    id: "ptr-compare",
    title: "PTR 条款核对",
    description: "上传 PTR PDF 和检验报告 PDF，展示后端条款、表格参数和 Finding 差异。",
    path: "/ptr-compare",
    badge: "PTR",
  },
];

export function DashboardPage() {
  return (
    <main className="page-shell">
      <div className="dashboard-grid">
        <aside className="dashboard-sidebar glass-card" aria-label="项目导航">
          <p className="brand">Report Checker Pro</p>
          <p className="muted">医疗器械检验报告核对工作台</p>
          <ul className="nav-list">
            <li className="nav-item">
              <span>Dashboard</span>
              <Badge variant="success">READY</Badge>
            </li>
            <li className="nav-item">
              <span>Report</span>
              <Badge variant="accent">API</Badge>
            </li>
            <li className="nav-item">
              <span>PTR</span>
              <Badge variant="accent">API</Badge>
            </li>
          </ul>
        </aside>

        <section className="panel-stack">
          <header className="page-header">
            <div>
              <p className="eyebrow">NEW FRONTEND STRUCTURE</p>
              <h1>报告核对工具</h1>
              <p className="muted">前端只负责上传、轮询、展示和导出，不在浏览器里实现核对规则。</p>
            </div>
            <Badge variant="success">FastAPI Contract</Badge>
          </header>

          <section className="module-grid" aria-label="模块入口">
            {modules.map((module) => (
              <GlassCard className="module-card" hover key={module.id}>
                <div className="row-head">
                  <div>
                    <Badge variant="accent">{module.badge}</Badge>
                    <h2>{module.title}</h2>
                    <p className="muted">{module.description}</p>
                  </div>
                </div>
                <Button onClick={() => (window.location.hash = module.path)} variant="primary">
                  进入
                </Button>
              </GlassCard>
            ))}
          </section>

          <section className="metric-grid three" aria-label="迁移状态">
            <GlassCard className="metric-card">
              <p className="muted">API</p>
              <p className="metric-value">/api/tasks</p>
            </GlassCard>
            <GlassCard className="metric-card">
              <p className="muted">Result</p>
              <p className="metric-value">Finding</p>
            </GlassCard>
            <GlassCard className="metric-card">
              <p className="muted">Export</p>
              <p className="metric-value">3</p>
            </GlassCard>
          </section>
        </section>
      </div>
    </main>
  );
}
