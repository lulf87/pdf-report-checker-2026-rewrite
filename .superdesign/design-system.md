# Report Checker Pro — Design System

## 1. Product context

Report Checker Pro is a desktop-first Chinese web application for automated review of medical-device inspection reports. It serves inspection staff, technical reviewers, and quality personnel who need to find document inconsistencies while preserving page-, field-, row-, caption-, and evidence-level traceability.

The application is not an autonomous compliance authority. Deterministic PDF/OCR/table/rule processing produces candidate findings; controlled Codex CLI review can confirm, refute, mark uncertain, or suggest an additional finding. The interface must visibly preserve both layers: “规则初判 + Codex 审核意见”. Human review remains explicit for uncertain or policy-dependent cases.

### Primary jobs to be done

1. Upload a single inspection-report PDF and run C01–C11 report self-checks.
2. Upload a PTR PDF plus an inspection-report PDF and compare Chapter 2 clauses and referenced tables.
3. Understand the final status without losing access to the original candidate finding, evidence, location, and Codex review trail.
4. Export structured results as JSON, PDF, or XLSX.

### Active product routes

- `#/`: landing page and module launcher.
- `#/report-check`: single-report C01–C11 upload, progress, results, evidence, and export.
- `#/ptr-compare`: dual-PDF PTR/report upload, progress, clause/table comparison, results, evidence, and export.

### Landing-page information architecture

The landing page must communicate the product and enable work, not behave like a generic public SaaS marketing page.

1. Compact brand/navigation bar with the text wordmark “Report Checker Pro” and visible product status.
2. Hero with a direct Chinese value proposition, restrained supporting copy, and two primary module actions.
3. A product-workflow visual using real supported stages: PDF 解析/OCR → 规则初判 → Codex 受控审核 → 证据与导出.
4. Two clearly differentiated task cards:
   - 报告自身核对 — one PDF, C01–C11.
   - PTR 条款核对 — PTR + report PDFs, Chapter 2 clauses and tables.
5. Evidence/trust section explaining traceable Finding location and the two-layer audit record.
6. Compact capability facts that are source-backed: C01–C11, PTR Chapter 2, three export formats, FastAPI backend contract. Do not invent accuracy, speed, adoption, certification, customer, or benchmark claims.
7. Minimal footer with architecture/tooling context; no fabricated legal links or company address.

## 2. Brand character

The product should feel calm, precise, evidence-led, and technically trustworthy. It is a regulated-document workspace, not a futuristic AI spectacle. Prefer quiet confidence, crisp hierarchy, and dense-but-readable information over decorative marketing tropes.

- Preserve the established dark glassmorphism direction.
- Use teal as the sole primary accent; amber, red, green, and blue are semantic states only.
- Use subtle technical-document motifs: page boundaries, clause rows, evidence links, and check traces.
- Avoid medical crosses, shields, locks, robot heads, holograms, glowing brains, stock photos, fake customer logos, and decorative 3D objects.
- No gradients that introduce colors outside the existing teal/amber-on-charcoal palette.
- No testimonials, percentages, accuracy claims, time-saved claims, or certification badges unless later supplied by the user.

## 3. Color tokens

Use these values exactly. Do not introduce additional brand colors.

### Foundations

- Canvas: `#101417` (`--color-bg`).
- Elevated glass: `rgba(20, 28, 32, 0.82)` (`--color-bg-elevated`).
- Soft inset surface: `rgba(255, 255, 255, 0.045)` (`--color-bg-soft`).
- Default border: `rgba(205, 229, 226, 0.14)` (`--color-border`).
- Strong border: `rgba(205, 229, 226, 0.24)` (`--color-border-strong`).

### Text

- Primary: `#edf7f6` (`--color-text`).
- Secondary: `#b7cbc8` (`--color-text-secondary`).
- Muted: `#8ea5a2` (`--color-text-muted`).
- Primary-button foreground: `#06100f`.

### Brand and semantic states

- Accent: `#74d7c8` (`--color-accent`).
- Accent strong: `#43b9aa` (`--color-accent-strong`).
- Success: `#8fd0aa` (`--color-success`).
- Danger: `#f19a9a` (`--color-danger`).
- Warning: `#f2c078` (`--color-warn`).
- Information: `#8fb9f0` (`--color-info`).

### Approved atmospheric backgrounds

The page canvas may layer only these established translucent fields over `#101417`:

- Teal diagonal: `linear-gradient(135deg, rgba(21, 83, 94, 0.28), transparent 34%)`.
- Warm diagonal: `linear-gradient(220deg, rgba(112, 72, 38, 0.24), transparent 32%)`.
- Teal radial: `radial-gradient(circle at 70% 8%, rgba(116, 215, 200, 0.13), transparent 28%)`.

Atmospheric fields remain subtle and never reduce text contrast.

## 4. Typography

- Use only `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.
- Do not introduce serif, display, condensed, monospace, or decorative fonts.
- Page/hero H1: `clamp(2.5rem, 6vw, 4.75rem)`, 0.98–1.05 line height, weight 800; keep Chinese line breaks intentional.
- Page H1 in application flows: current `clamp(2rem, 5vw, 3.5rem)`.
- Section H2: 1.5–2rem, line height 1.15, weight 800.
- Card title: 1.05–1.25rem, weight 800.
- Body: 0.95–1rem, line height 1.6.
- Muted/meta: 0.78–0.9rem, line height 1.5.
- Eyebrow labels: 0.78rem, uppercase where English, weight 700–800; do not add letter spacing beyond the current zero value.
- Numeric and status values should use tabular numerals.

## 5. Spacing and layout

- Desktop content width: maximum 1180px.
- Page gutter: 16px minimum; 28px vertical start on desktop; 18px on compact screens.
- Approved spacing values: 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 40, 48, 64, 80px.
- Default section separation on the landing page: 64–80px desktop, 40–48px mobile.
- Default card grid gap: 14–18px.
- Landing hero should occupy the first viewport without forcing every supporting section above the fold.
- Use asymmetry only where it clarifies hierarchy; align card contents to a consistent grid.
- Responsive breakpoint: 760px. At and below it, navigation, hero, module cards, proof points, and workflow columns collapse to one column.
- Avoid a permanent dashboard sidebar in the new landing variants unless it serves as a deliberate application-launch rail; public-marketing navigation should be a compact top bar.

## 6. Shape, borders, shadows, and glass

- Small radius: 6px (`--radius-sm`).
- Default card/control radius: 8px (`--radius-md`).
- Pills only: 999px.
- Do not introduce large 20–32px “friendly SaaS” radii.
- Default glass border: 1px solid `--color-border`.
- Interactive/emphasized border: `--color-border-strong`.
- Glass background: `--color-bg-elevated`.
- Glass effect: `backdrop-filter: blur(18px) saturate(1.18)`.
- Default glass shadow: `0 16px 48px rgba(0, 0, 0, 0.3)`.
- Optional accent glow is limited to `0 0 32px rgba(116, 215, 200, 0.08)` and should appear on at most one key surface per viewport.
- Avoid neon outer glows, thick gradient borders, and layered floating-card clutter.

## 7. Components and patterns

### Top navigation

- Text wordmark “Report Checker Pro”; no substitute logo asset exists in the repository.
- Optional short Chinese descriptor “医疗器械检验报告核对”.
- Compact anchors may include 功能, 工作流程, 审核证据.
- Primary action should launch 报告自身核对; PTR核对 is a clear secondary action or adjacent equal-weight task choice.
- Use a 1px bottom border or a restrained glass bar. Do not create a bulky marketing navbar.

### Buttons

- Primary: accent background, dark foreground, 8px radius, weight 700.
- Secondary: thin default border, primary text, 6% white background.
- Ghost: transparent background and secondary text.
- Height: 40px default, 48px large CTA, 32px compact.
- Hover: translate upward at most 1px; never scale dramatically.

### Badges and status

- 28px minimum height, 999px radius, 1px current-color border, 7px dot, 0.78rem/700 text.
- Accent badges identify feature categories; success/warn/danger/info are reserved for actual state semantics.
- Do not label an unavailable or unverified feature “READY”.

### Glass cards

- Use the existing GlassCard treatment for modules, proof points, workflow stages, evidence samples, and status summaries.
- Interactive cards may translate upward 2px and strengthen their border.
- Each module card needs: clear document input, scope, evidence output, and a task-launch action.

### Workflow visual

- Represent four connected stages with concise labels and small document/row/evidence symbols drawn as inline SVG or CSS.
- The connection should read left-to-right on desktop and top-to-bottom on mobile.
- Make the separation between deterministic rules and Codex review visually explicit.
- Do not imply that Codex silently replaces deterministic findings.

### Evidence sample

- A compact product mock panel may show a plausible interface structure, but it must use only source-backed labels such as C01, C07, PTR_TABLE, Finding, confirm/refute/uncertain, page, field, evidence, JSON/PDF/XLSX.
- Avoid invented inspection values, device claims, certificate numbers, pass rates, or fabricated report content.

## 8. Iconography and imagery

- The repository has no logo or icon asset set. Use the text wordmark for identity.
- If icons are necessary, use minimal inline SVG line icons with 1.5–2px strokes and currentColor. Keep them secondary to labels.
- Approved metaphors: document page, two-document compare, table rows, check trace, evidence link, download.
- No stock imagery, hero photos, medical photography, 3D illustration, emojis, or generic AI imagery.

## 9. Motion

- Fast interaction: 140ms ease.
- Normal transitions: 220ms ease.
- Slow reveal/counter: 360ms ease.
- Hover translations: buttons −1px, cards −2px maximum.
- Landing entrance motion may use opacity + 8–12px vertical translation with 45ms stagger, capped at 360ms.
- Respect `prefers-reduced-motion`; content must remain fully understandable without animation.
- Avoid looping decoration. Pulse is reserved for a genuinely active status dot.

## 10. Accessibility and content rules

- Maintain WCAG-aware contrast using the approved tokens; muted text must not carry critical meaning alone.
- Keyboard focus must be visible with accent/strong border treatment.
- Interactive cards must still contain an explicit button or link label.
- Use semantic heading order, landmarks, and descriptive Chinese action labels.
- Do not encode pass/fail/review state using color alone; pair color with a label and/or icon.
- Body copy is primarily Simplified Chinese. Keep established technical names in English where helpful: PTR, PDF, OCR, Finding, Codex, FastAPI, JSON, XLSX.
- Frontend copy must not claim that the browser performs C01–C11 or PTR judgments; those results come from the backend.
- Clearly distinguish candidate findings, final audit state, and items requiring human review.

## 11. Landing-page design constraints

- Preserve the two current product entry points and their real route intent.
- Make “报告自身核对” and “PTR 条款核对” visible in the first viewport on common desktop sizes.
- Explain why the product is trustworthy through architecture and evidence traceability, not through fabricated social proof.
- The design may be more polished and editorial than the current dashboard, but it must remain recognizably part of the same application.
- Keep the palette, font stack, compact radii, glass treatment, semantic colors, and motion values fixed across all variants.
- The landing page is a design exploration only. Do not alter C01–C11/PTR logic or imply new backend capabilities.
