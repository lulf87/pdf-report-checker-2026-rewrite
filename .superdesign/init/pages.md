# Page Dependency Trees

The root layout is `frontend/src/app/App.tsx` (documented in `layouts.md`). The trees below trace every local TypeScript/TSX import recursively from each active route entry. The global stylesheet is included explicitly because it is imported once by `frontend/src/main.tsx` rather than by individual pages.

## #/ — Dashboard / landing page

Entry: `frontend/src/features/dashboard/DashboardPage.tsx`
Render branch: Unconditional two-column desktop grid with a sticky project sidebar and a main stack containing the hero header, two module-entry cards, and three metrics.
Dependencies:
- frontend/src/features/dashboard/DashboardPage.tsx
  - frontend/src/shared/ui/Badge.tsx
  - frontend/src/shared/ui/Button.tsx
  - frontend/src/shared/ui/GlassCard.tsx
- frontend/src/index.css (global stylesheet imported by frontend/src/main.tsx)
  - frontend/src/shared/styles/design-tokens.css

## #/report-check — Report self-check

Entry: `frontend/src/features/report-check/pages/ReportCheckPage.tsx`
Render branch: Conditional route: initial state renders ReportUpload; completed state renders ReportResults. Both branches are part of the page UI.
Dependencies:
- frontend/src/features/report-check/pages/ReportCheckPage.tsx
  - frontend/src/entities/task/types.ts
    - frontend/src/entities/codexReview/types.ts
      - frontend/src/entities/finding/types.ts
    - frontend/src/entities/finding/types.ts (shared; listed earlier)
  - frontend/src/shared/lib/taskSessionStorage.ts
    - frontend/src/entities/task/types.ts (shared; listed earlier)
  - frontend/src/features/report-check/components/ReportResults.tsx
    - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
    - frontend/src/entities/finding/types.ts (shared; listed earlier)
    - frontend/src/entities/report/types.ts
      - frontend/src/entities/finding/types.ts (shared; listed earlier)
      - frontend/src/entities/task/types.ts (shared; listed earlier)
    - frontend/src/entities/task/types.ts (shared; listed earlier)
    - frontend/src/shared/ui/AnimatedCounter.tsx
    - frontend/src/shared/ui/Badge.tsx
    - frontend/src/shared/ui/Button.tsx
    - frontend/src/shared/ui/ExportButton.tsx
      - frontend/src/entities/task/types.ts (shared; listed earlier)
      - frontend/src/shared/api/client.ts
        - frontend/src/entities/task/types.ts (shared; listed earlier)
      - frontend/src/shared/ui/Button.tsx (shared; listed earlier)
    - frontend/src/shared/ui/GlassCard.tsx
    - frontend/src/features/codex-review/components/CodexReviewPanel.tsx
      - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
      - frontend/src/shared/ui/Badge.tsx (shared; listed earlier)
      - frontend/src/shared/ui/GlassCard.tsx (shared; listed earlier)
    - frontend/src/features/report-check/model/finalView.ts
      - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
      - frontend/src/entities/finding/types.ts (shared; listed earlier)
      - frontend/src/entities/task/types.ts (shared; listed earlier)
  - frontend/src/features/report-check/components/ReportUpload.tsx
    - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
    - frontend/src/entities/task/types.ts (shared; listed earlier)
    - frontend/src/features/codex-review/components/CodexModelSelector.tsx
      - frontend/src/entities/task/types.ts (shared; listed earlier)
      - frontend/src/features/codex-review/api.ts
        - frontend/src/entities/task/types.ts (shared; listed earlier)
        - frontend/src/shared/api/client.ts (shared; listed earlier)
    - frontend/src/shared/ui/Button.tsx (shared; listed earlier)
    - frontend/src/shared/ui/FileUpload.tsx
      - frontend/src/shared/ui/GlassCard.tsx (shared; listed earlier)
    - frontend/src/shared/ui/GlassCard.tsx (shared; listed earlier)
    - frontend/src/shared/ui/ProgressOverlay.tsx
      - frontend/src/entities/task/types.ts (shared; listed earlier)
      - frontend/src/shared/ui/Button.tsx (shared; listed earlier)
      - frontend/src/shared/ui/GlassCard.tsx (shared; listed earlier)
    - frontend/src/shared/lib/taskSessionStorage.ts (shared; listed earlier)
    - frontend/src/features/report-check/api.ts
      - frontend/src/shared/api/client.ts (shared; listed earlier)
      - frontend/src/entities/task/types.ts (shared; listed earlier)
- frontend/src/index.css (global stylesheet imported by frontend/src/main.tsx)
  - frontend/src/shared/styles/design-tokens.css

## #/ptr-compare — PTR comparison

Entry: `frontend/src/features/ptr-compare/pages/PTRComparePage.tsx`
Render branch: Conditional route: initial state renders PTRUpload; completed state renders PTRResults. Both branches are part of the page UI.
Dependencies:
- frontend/src/features/ptr-compare/pages/PTRComparePage.tsx
  - frontend/src/entities/task/types.ts
    - frontend/src/entities/codexReview/types.ts
      - frontend/src/entities/finding/types.ts
    - frontend/src/entities/finding/types.ts (shared; listed earlier)
  - frontend/src/shared/lib/taskSessionStorage.ts
    - frontend/src/entities/task/types.ts (shared; listed earlier)
  - frontend/src/features/ptr-compare/components/PTRResults.tsx
    - frontend/src/entities/ptr/types.ts
      - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
      - frontend/src/entities/finding/types.ts (shared; listed earlier)
      - frontend/src/entities/task/types.ts (shared; listed earlier)
    - frontend/src/entities/task/types.ts (shared; listed earlier)
    - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
    - frontend/src/features/codex-review/components/CodexReviewPanel.tsx
      - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
      - frontend/src/shared/ui/Badge.tsx
      - frontend/src/shared/ui/GlassCard.tsx
    - frontend/src/shared/ui/AnimatedCounter.tsx
    - frontend/src/shared/ui/Badge.tsx (shared; listed earlier)
    - frontend/src/shared/ui/Button.tsx
    - frontend/src/shared/ui/ExportButton.tsx
      - frontend/src/entities/task/types.ts (shared; listed earlier)
      - frontend/src/shared/api/client.ts
        - frontend/src/entities/task/types.ts (shared; listed earlier)
      - frontend/src/shared/ui/Button.tsx (shared; listed earlier)
    - frontend/src/shared/ui/GlassCard.tsx (shared; listed earlier)
    - frontend/src/features/ptr-compare/components/ClauseList.tsx
      - frontend/src/entities/ptr/types.ts (shared; listed earlier)
      - frontend/src/features/ptr-compare/components/ClauseCard.tsx
        - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
        - frontend/src/entities/finding/types.ts (shared; listed earlier)
        - frontend/src/entities/ptr/types.ts (shared; listed earlier)
        - frontend/src/entities/task/types.ts (shared; listed earlier)
        - frontend/src/shared/ui/Badge.tsx (shared; listed earlier)
        - frontend/src/shared/ui/Button.tsx (shared; listed earlier)
        - frontend/src/features/codex-review/components/CodexReviewPanel.tsx (shared; listed earlier)
        - frontend/src/features/ptr-compare/components/DiffViewer.tsx
          - frontend/src/entities/finding/types.ts (shared; listed earlier)
  - frontend/src/features/ptr-compare/components/PTRUpload.tsx
    - frontend/src/entities/codexReview/types.ts (shared; listed earlier)
    - frontend/src/entities/task/types.ts (shared; listed earlier)
    - frontend/src/features/codex-review/components/CodexModelSelector.tsx
      - frontend/src/entities/task/types.ts (shared; listed earlier)
      - frontend/src/features/codex-review/api.ts
        - frontend/src/entities/task/types.ts (shared; listed earlier)
        - frontend/src/shared/api/client.ts (shared; listed earlier)
    - frontend/src/shared/ui/Button.tsx (shared; listed earlier)
    - frontend/src/shared/ui/FileUpload.tsx
      - frontend/src/shared/ui/GlassCard.tsx (shared; listed earlier)
    - frontend/src/shared/ui/GlassCard.tsx (shared; listed earlier)
    - frontend/src/shared/ui/ProgressOverlay.tsx
      - frontend/src/entities/task/types.ts (shared; listed earlier)
      - frontend/src/shared/ui/Button.tsx (shared; listed earlier)
      - frontend/src/shared/ui/GlassCard.tsx (shared; listed earlier)
    - frontend/src/shared/lib/taskSessionStorage.ts (shared; listed earlier)
    - frontend/src/features/ptr-compare/api.ts
      - frontend/src/shared/api/client.ts (shared; listed earlier)
      - frontend/src/entities/task/types.ts (shared; listed earlier)
- frontend/src/index.css (global stylesheet imported by frontend/src/main.tsx)
  - frontend/src/shared/styles/design-tokens.css
