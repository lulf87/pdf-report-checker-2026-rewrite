# Theme and Design Tokens

## Stack and styling approach

- Framework: React 18 with TypeScript and Vite 5.
- Component library: custom React primitives; no third-party UI kit.
- Styling: global vanilla CSS class names and CSS custom properties; no Tailwind configuration is present.
- Font stack: Inter when available, falling back to system sans-serif.
- Direction: dark glassmorphism with teal accent, restrained amber warmth, soft blur, thin borders, and compact radii.
- Primary responsive breakpoint: 760px.
- Active global stylesheet: `frontend/src/index.css`, imported by `frontend/src/main.tsx`.
- Legacy stylesheet: `frontend/src/app/styles.css` is retained in the repository but is not imported by the current entry point.

## `frontend/src/shared/styles/design-tokens.css`

```css
:root {
  --color-bg: #101417;
  --color-bg-elevated: rgba(20, 28, 32, 0.82);
  --color-bg-soft: rgba(255, 255, 255, 0.045);
  --color-border: rgba(205, 229, 226, 0.14);
  --color-border-strong: rgba(205, 229, 226, 0.24);
  --color-text: #edf7f6;
  --color-text-secondary: #b7cbc8;
  --color-text-muted: #8ea5a2;
  --color-accent: #74d7c8;
  --color-accent-strong: #43b9aa;
  --color-success: #8fd0aa;
  --color-danger: #f19a9a;
  --color-warn: #f2c078;
  --color-info: #8fb9f0;
  --radius-sm: 6px;
  --radius-md: 8px;
  --shadow-glass: 0 16px 48px rgba(0, 0, 0, 0.3);
  --transition-fast: 140ms ease;
  --transition-normal: 220ms ease;
}
```

## `frontend/src/index.css`

```css
@import "./shared/styles/design-tokens.css";

* {
  box-sizing: border-box;
}

:root {
  color: var(--color-text);
  background: var(--color-bg);
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  background:
    linear-gradient(135deg, rgba(21, 83, 94, 0.28), transparent 34%),
    linear-gradient(220deg, rgba(112, 72, 38, 0.24), transparent 32%),
    radial-gradient(circle at 70% 8%, rgba(116, 215, 200, 0.13), transparent 28%),
    #101417;
}

button,
input,
textarea,
select {
  font: inherit;
}

button {
  color: inherit;
}

a {
  color: inherit;
}

h1,
h2,
h3,
p {
  margin-top: 0;
}

.app-shell {
  min-height: 100vh;
}

.page-shell {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 28px 0 40px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.page-header h1 {
  margin-bottom: 8px;
  font-size: clamp(2rem, 5vw, 3.5rem);
  line-height: 1.05;
}

.page-header.compact h1 {
  font-size: clamp(1.7rem, 4vw, 2.5rem);
}

.eyebrow {
  margin-bottom: 8px;
  color: var(--color-accent);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.muted {
  color: var(--color-text-muted);
}

.glass-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-glass);
  backdrop-filter: blur(18px) saturate(1.18);
}

.glass-card-hover {
  transition:
    transform var(--transition-normal),
    border-color var(--transition-normal),
    background var(--transition-normal);
}

.glass-card-hover:hover {
  transform: translateY(-2px);
  border-color: var(--color-border-strong);
  background: rgba(26, 36, 40, 0.88);
}

.glass-card-glow {
  box-shadow:
    var(--shadow-glass),
    0 0 32px rgba(116, 215, 200, 0.08);
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  transition:
    transform var(--transition-fast),
    opacity var(--transition-fast),
    background var(--transition-fast),
    border-color var(--transition-fast);
}

.button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.52;
}

.button-sm {
  min-height: 32px;
  padding: 6px 10px;
  font-size: 0.84rem;
}

.button-md {
  min-height: 40px;
  padding: 9px 14px;
}

.button-lg {
  min-height: 48px;
  padding: 12px 18px;
  font-size: 1.05rem;
}

.button-primary {
  color: #06100f;
  background: var(--color-accent);
}

.button-secondary {
  border-color: var(--color-border);
  color: var(--color-text);
  background: rgba(255, 255, 255, 0.06);
}

.button-ghost {
  border-color: transparent;
  color: var(--color-text-secondary);
  background: transparent;
}

.button-danger {
  color: #1e0b0b;
  background: var(--color-danger);
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  padding: 4px 10px;
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}

.badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
}

.badge-success {
  color: var(--color-success);
  background: rgba(143, 208, 170, 0.12);
}

.badge-danger {
  color: var(--color-danger);
  background: rgba(241, 154, 154, 0.12);
}

.badge-info {
  color: var(--color-info);
  background: rgba(143, 185, 240, 0.12);
}

.badge-warn {
  color: var(--color-warn);
  background: rgba(242, 192, 120, 0.12);
}

.badge-accent {
  color: var(--color-accent);
  background: rgba(116, 215, 200, 0.12);
}

.badge-pulse .badge-dot {
  animation: pulse 1.4s ease infinite;
}

.tabular {
  font-variant-numeric: tabular-nums;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  gap: 18px;
}

.dashboard-sidebar {
  position: sticky;
  top: 28px;
  align-self: start;
  padding: 20px;
}

.brand {
  margin-bottom: 6px;
  font-size: 1.1rem;
  font-weight: 800;
}

.nav-list,
.module-list,
.result-list,
.check-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.nav-item,
.module-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 48px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-soft);
}

.module-grid,
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.metric-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.module-card,
.metric-card,
.upload-card,
.results-card {
  padding: 20px;
}

.module-card h2,
.metric-card h2 {
  margin-bottom: 8px;
  font-size: 1.05rem;
}

.metric-value {
  color: var(--color-text);
  font-size: 2.15rem;
  font-weight: 800;
}

.form-panel {
  display: grid;
  gap: 18px;
  width: min(680px, 100%);
  margin: 0 auto;
}

.file-upload {
  display: grid;
  gap: 14px;
}

.drop-zone {
  display: grid;
  place-items: center;
  min-height: 168px;
  padding: 24px;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
  color: var(--color-text-secondary);
  text-align: center;
  cursor: pointer;
  transition:
    border-color var(--transition-fast),
    background var(--transition-fast);
}

.drop-zone.dragging,
.drop-zone:hover:not(.disabled) {
  border-color: var(--color-accent);
  background: rgba(116, 215, 200, 0.08);
}

.drop-zone.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.drop-zone input {
  display: none;
}

.drop-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin-bottom: 12px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  color: var(--color-accent);
  font-size: 1.4rem;
  font-weight: 800;
}

.drop-title {
  display: block;
  margin-bottom: 6px;
  color: var(--color-text);
  font-weight: 800;
}

.drop-hint,
.file-size,
.form-help {
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 82px;
  padding: 14px;
}

.file-icon {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: var(--radius-md);
  color: var(--color-accent);
  background: rgba(116, 215, 200, 0.12);
  font-size: 0.72rem;
  font-weight: 800;
}

.file-meta {
  min-width: 0;
  flex: 1;
}

.file-name {
  overflow: hidden;
  margin-bottom: 4px;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 700;
}

.icon-button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  background: rgba(255, 255, 255, 0.04);
  cursor: pointer;
}

.icon-button.danger {
  color: var(--color-danger);
}

.form-error {
  margin: 0;
  color: var(--color-danger);
  font-size: 0.9rem;
}

.toggle-row,
.button-row,
.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.toggle-row {
  justify-content: center;
}

.advanced-audit-settings {
  padding: 10px 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.advanced-audit-settings summary {
  cursor: pointer;
  color: var(--color-text);
  font-weight: 700;
}

.advanced-audit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.advanced-audit-grid label {
  display: grid;
  gap: 6px;
  min-width: 0;
  color: var(--color-text-muted);
  font-size: 0.82rem;
}

.advanced-audit-grid input,
.advanced-audit-grid select {
  width: 100%;
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  background: rgba(255, 255, 255, 0.05);
}

.advanced-audit-grid select {
  appearance: auto;
}

.overlay {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(12, 16, 18, 0.72);
  backdrop-filter: blur(10px);
}

.progress-card {
  display: grid;
  gap: 12px;
  width: min(680px, 100%);
  max-height: min(82vh, 760px);
  overflow: auto;
  padding: 24px;
  text-align: center;
}

.progress-actions {
  justify-content: center;
  padding-top: 2px;
}

.progress-mark {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  margin: 0 auto;
  border-radius: 999px;
  color: var(--color-accent);
  background: rgba(116, 215, 200, 0.12);
  font-weight: 800;
}

.progress-mark.danger {
  color: var(--color-danger);
  background: rgba(241, 154, 154, 0.12);
}

.progress-track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--color-accent);
  transition: width var(--transition-normal);
}

.progress-headline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
  color: var(--color-text-muted);
  text-align: left;
}

.progress-headline strong {
  color: var(--color-text);
  white-space: nowrap;
}

.progress-headline.compact {
  font-size: 0.92rem;
}

.progress-checklist {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  text-align: left;
}

.progress-check {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.035);
}

.progress-check-id {
  color: var(--color-text);
  font-weight: 700;
}

.progress-check-name {
  overflow: hidden;
  color: var(--color-text-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-check-status {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  white-space: nowrap;
}

.progress-check-running {
  border-color: rgba(116, 215, 200, 0.46);
  background: rgba(116, 215, 200, 0.09);
}

.progress-check-passed {
  border-color: rgba(122, 205, 166, 0.36);
}

.progress-check-failed,
.progress-check-needs_review {
  border-color: rgba(241, 204, 122, 0.46);
  background: rgba(241, 204, 122, 0.08);
}

.progress-check-error {
  border-color: rgba(241, 154, 154, 0.48);
  background: rgba(241, 154, 154, 0.08);
}

.codex-progress {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(116, 215, 200, 0.28);
  border-radius: var(--radius-sm);
  background: rgba(116, 215, 200, 0.07);
  text-align: left;
}

.codex-progress-retrying {
  border-color: rgba(241, 204, 122, 0.48);
  background: rgba(241, 204, 122, 0.08);
}

.codex-progress-failed {
  border-color: rgba(241, 154, 154, 0.48);
  background: rgba(241, 154, 154, 0.08);
}

.codex-progress-grid {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 6px 12px;
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

.codex-progress-grid strong {
  overflow-wrap: anywhere;
  color: var(--color-text-secondary);
  font-weight: 600;
}

.result-card,
.check-row,
.clause-card {
  padding: 16px;
}

.check-row,
.clause-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
}

.issue-danger {
  border-color: rgba(241, 154, 154, 0.48);
  background: rgba(241, 154, 154, 0.08);
}

.issue-warn {
  border-color: rgba(242, 192, 120, 0.46);
  background: rgba(242, 192, 120, 0.08);
}

.row-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.row-title {
  margin-bottom: 6px;
  font-weight: 800;
}

.row-summary,
.evidence-text,
.diagnostic-list {
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.codex-overview {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.codex-summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.codex-summary-item {
  display: grid;
  gap: 4px;
  min-height: 68px;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
}

.codex-summary-label {
  color: var(--color-text-muted);
  font-size: 0.82rem;
}

.codex-review-list {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

.codex-review-list-title {
  margin-bottom: 0;
  color: var(--color-accent);
  font-size: 0.82rem;
  font-weight: 800;
}

.codex-review-item {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
}

.codex-review-success {
  border-color: rgba(143, 208, 170, 0.34);
}

.codex-review-danger {
  border-color: rgba(241, 154, 154, 0.38);
}

.codex-review-warn {
  border-color: rgba(242, 192, 120, 0.38);
}

.codex-review-accent {
  border-color: rgba(116, 215, 200, 0.34);
}

.codex-review-title {
  margin-bottom: 4px;
  color: var(--color-text);
  font-weight: 800;
}

.codex-review-target,
.codex-review-summary,
.codex-review-refs,
.codex-review-meta,
.codex-suggested-finding,
.codex-error {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  line-height: 1.55;
}

.codex-review-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}

.codex-suggested-finding {
  padding: 8px;
  border-radius: var(--radius-sm);
  background: rgba(116, 215, 200, 0.08);
}

.codex-error {
  padding: 8px;
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  background: rgba(241, 154, 154, 0.1);
}

.details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.final-review-panel {
  display: grid;
  gap: 12px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid rgba(116, 215, 200, 0.28);
  border-radius: var(--radius-md);
  background: rgba(116, 215, 200, 0.055);
}

.final-review-title {
  margin: 0;
  color: var(--color-text);
  font-size: 1.05rem;
  font-weight: 900;
}

.final-review-summary {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.final-review-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 8px;
}

.final-review-stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  background: rgba(255, 255, 255, 0.035);
}

.final-review-stat strong {
  color: var(--color-text);
  font-size: 1rem;
}

.final-review-stat-success strong {
  color: var(--color-success);
}

.final-review-stat-danger strong {
  color: var(--color-danger);
}

.final-review-stat-warn strong {
  color: var(--color-warning);
}

.technical-details {
  margin-top: 12px;
  border-top: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.technical-details > summary {
  cursor: pointer;
  padding: 10px 0;
  color: var(--color-text);
  font-weight: 800;
}

.technical-details-body {
  display: grid;
  gap: 12px;
  padding-bottom: 4px;
}

.technical-evidence-text {
  max-height: 320px;
  margin: 6px 0 0;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: 0.78rem;
  line-height: 1.55;
}

.trace-section {
  display: grid;
  gap: 6px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
}

.trace-section p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.trace-callout {
  margin: 10px 0 0;
  padding: 10px 12px;
  border-left: 3px solid var(--color-warn);
  background: rgba(242, 192, 120, 0.08);
  color: var(--color-text) !important;
}

.trace-callout-danger {
  border-left-color: var(--color-danger);
  background: rgba(241, 154, 154, 0.08);
}

.sequence-offset-group + .sequence-offset-group {
  margin-top: 14px;
}

.trace-meta {
  font-size: 0.8rem;
}

.trace-decision {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
}

.trace-final {
  border-bottom: 0;
}

.comparison-details {
  display: grid;
  gap: 10px;
  margin-bottom: 12px;
}

.comparison-details-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.comparison-title {
  margin: 0;
  color: var(--color-text);
  font-weight: 800;
}

.comparison-source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.comparison-source {
  padding: 4px 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.82rem;
}

.comparison-reason {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.comparison-reason strong {
  margin-right: 8px;
  color: var(--color-text);
}

.explanation-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.explanation-summary-grid > div,
.explanation-evidence-group {
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.035);
}

.explanation-summary-grid p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.detail-kicker {
  margin-bottom: 4px !important;
  color: var(--color-text) !important;
  font-size: 0.78rem;
  font-weight: 800;
}

.explanation-evidence-groups {
  display: grid;
  gap: 10px;
}

.explanation-evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.comparison-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.comparison-table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  font-size: 0.86rem;
}

.comparison-table th,
.comparison-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: top;
}

.comparison-table th {
  color: var(--color-text);
  background: rgba(255, 255, 255, 0.05);
  font-weight: 800;
}

.comparison-table td {
  color: var(--color-text-secondary);
  overflow-wrap: anywhere;
}

.comparison-table tr:last-child td {
  border-bottom: 0;
}

.inactive-model-details {
  color: var(--color-text-secondary);
}

.inactive-model-details > summary {
  cursor: pointer;
  padding: 6px 0;
  color: var(--color-text-secondary);
  font-size: 0.84rem;
  font-weight: 700;
}

.inactive-model-details[open] > summary {
  color: var(--color-text);
}

.comparison-row-success td {
  background: rgba(143, 208, 170, 0.045);
}

.comparison-row-danger td {
  background: rgba(241, 154, 154, 0.06);
}

.comparison-row-warn td {
  background: rgba(242, 192, 120, 0.055);
}

.diff-viewer {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  line-height: 1.8;
}

.diff-fragment {
  padding: 1px 5px;
  border-radius: 5px;
  white-space: pre-wrap;
}

.diff-insert {
  color: var(--color-success);
  background: rgba(143, 208, 170, 0.14);
}

.diff-delete {
  color: var(--color-danger);
  background: rgba(241, 154, 154, 0.14);
  text-decoration: line-through;
}

.diff-replace {
  color: var(--color-warn);
  background: rgba(242, 192, 120, 0.14);
}

.diff-equal {
  color: var(--color-text-secondary);
}

.panel-stack {
  display: grid;
  gap: 14px;
}

.split-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.65;
    transform: scale(1.24);
  }
}

@media (max-width: 760px) {
  .page-header,
  .dashboard-grid,
  .module-grid,
  .metric-grid,
  .metric-grid.three,
  .codex-summary-grid,
  .progress-checklist,
  .split-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    display: grid;
  }

  .dashboard-sidebar {
    position: static;
  }
}
```

## `frontend/src/app/styles.css`

```css
:root {
  color: #edf7f6;
  background: #101417;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* {
  box-sizing: border-box;
}

body {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  background:
    linear-gradient(135deg, rgba(21, 83, 94, 0.28), transparent 34%),
    linear-gradient(220deg, rgba(112, 72, 38, 0.24), transparent 32%),
    #101417;
}

button,
input,
textarea,
select {
  font: inherit;
}

.shell {
  min-height: 100vh;
  padding: 28px;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 20px;
  max-width: 1180px;
  margin: 0 auto;
}

.sidebar,
.panel,
.metric {
  border: 1px solid rgba(205, 229, 226, 0.14);
  border-radius: 8px;
  background: rgba(20, 28, 32, 0.74);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(18px);
}

.sidebar {
  position: sticky;
  top: 28px;
  align-self: start;
  padding: 20px;
}

.brand {
  margin: 0 0 6px;
  font-size: 1.05rem;
  font-weight: 700;
}

.muted {
  color: #9eb8b6;
}

.sidebar-note {
  margin: 0 0 22px;
  color: #9eb8b6;
  line-height: 1.6;
}

.nav-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid rgba(205, 229, 226, 0.1);
  border-radius: 8px;
  color: #d8e8e6;
  background: rgba(255, 255, 255, 0.04);
}

.content {
  display: grid;
  gap: 18px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 4px 0 2px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #74d7c8;
  font-size: 0.78rem;
  font-weight: 700;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  max-width: 780px;
  margin-bottom: 0;
  font-size: clamp(2rem, 6vw, 3.8rem);
  line-height: 1.02;
}

h2 {
  margin-bottom: 14px;
  font-size: 1rem;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.metric {
  padding: 18px;
}

.metric-label {
  margin-bottom: 10px;
  color: #9eb8b6;
  font-size: 0.82rem;
}

.metric-value {
  font-size: 1.65rem;
  font-weight: 700;
}

.panel {
  padding: 20px;
}

.module-list {
  display: grid;
  gap: 12px;
}

.module-row {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) minmax(0, 2fr) auto;
  gap: 14px;
  align-items: center;
  min-height: 54px;
  padding: 12px 0;
  border-top: 1px solid rgba(205, 229, 226, 0.1);
}

.module-row:first-child {
  border-top: 0;
}

.module-title {
  margin: 0;
  font-weight: 700;
}

.module-desc {
  margin: 0;
  color: #9eb8b6;
  line-height: 1.5;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  min-height: 28px;
  padding: 4px 10px;
  border: 1px solid transparent;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}

.status-pill.ready {
  border-color: rgba(116, 215, 200, 0.4);
  color: #8ff0e3;
  background: rgba(34, 150, 134, 0.16);
}

.status-pill.pending {
  border-color: rgba(229, 179, 102, 0.38);
  color: #ffd08a;
  background: rgba(178, 113, 34, 0.16);
}

@media (max-width: 760px) {
  .shell {
    padding: 18px;
  }

  .workspace,
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
  }

  .page-head,
  .module-row {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .page-head {
    display: grid;
  }
}
```
