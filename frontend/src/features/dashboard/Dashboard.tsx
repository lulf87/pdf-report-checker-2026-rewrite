import type { TaskModule } from "../../entities/task";
import { StatusPill } from "../../shared/ui/StatusPill";

const modules: TaskModule[] = [
  {
    id: "report-check",
    title: "报告自检",
    description: "C01-C11 规则位置已预留，具体判断后续逐条迁移。",
    state: "pending",
  },
  {
    id: "ptr-compare",
    title: "PTR 核对",
    description: "条款、表格和参数比对入口已预留，复杂逻辑暂不迁入。",
    state: "pending",
  },
  {
    id: "health",
    title: "服务健康",
    description: "GET /api/health 已作为后端启动和测试的最小验收点。",
    state: "ready",
  },
];

export function Dashboard() {
  return (
    <main className="shell">
      <div className="workspace">
        <aside className="sidebar" aria-label="项目导航">
          <p className="brand">Report Checker Pro</p>
          <p className="sidebar-note">医疗器械检验报告核对工作台</p>
          <ul className="nav-list">
            <li className="nav-item">
              <span>Dashboard</span>
              <StatusPill state="ready" label="READY" />
            </li>
            <li className="nav-item">
              <span>Report</span>
              <StatusPill state="pending" label="NEXT" />
            </li>
            <li className="nav-item">
              <span>PTR</span>
              <StatusPill state="pending" label="NEXT" />
            </li>
          </ul>
        </aside>

        <section className="content">
          <header className="page-head">
            <div>
              <p className="eyebrow">NEW ARCHITECTURE</p>
              <h1>报告核对工具</h1>
            </div>
            <StatusPill state="ready" label="SKELETON" />
          </header>

          <section className="metric-grid" aria-label="骨架状态">
            <div className="metric">
              <div className="metric-label">Backend</div>
              <div className="metric-value">FastAPI</div>
            </div>
            <div className="metric">
              <div className="metric-label">Frontend</div>
              <div className="metric-value">Vite</div>
            </div>
            <div className="metric">
              <div className="metric-label">Rules</div>
              <div className="metric-value">0/11</div>
            </div>
          </section>

          <section className="panel" aria-labelledby="module-title">
            <h2 id="module-title">模块入口</h2>
            <div className="module-list">
              {modules.map((module) => (
                <article className="module-row" key={module.id}>
                  <p className="module-title">{module.title}</p>
                  <p className="module-desc">{module.description}</p>
                  <StatusPill
                    state={module.state}
                    label={module.state === "ready" ? "READY" : "PENDING"}
                  />
                </article>
              ))}
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}
