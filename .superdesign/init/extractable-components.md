# Extractable Superdesign Components

## Layout Components

No standalone shared navigation, header, sidebar, footer, or app-shell component exists in the current codebase. The dashboard sidebar is embedded directly in `DashboardPage.tsx`, while upload/result pages render page-local headers. Extracting a layout component before the design is therefore not justified.

## Basic Components

## GlassCard
- Source: `frontend/src/shared/ui/GlassCard.tsx`
- Category: basic
- Description: Core dark glass surface used for module cards, metrics, upload panels, notices, and result groups.
- Extractable props: none required for current design drafts; `hover` and `glow` are visual variants and should be represented by separate static component variants if extracted later.
- Hardcoded: glass-card class structure, border, blur, background, radius, and shadow styling.

## Badge
- Source: `frontend/src/shared/ui/Badge.tsx`
- Category: basic
- Description: Compact semantic status badge used throughout dashboard, progress, and results views.
- Extractable props: `showBadge` (boolean, default: true) only if a draft needs conditional visibility.
- Hardcoded: dot icon, label text per usage, semantic color classes, pill sizing, and CSS.

## Button
- Source: `frontend/src/shared/ui/Button.tsx`
- Category: basic
- Description: Shared call-to-action and secondary-action control.
- Extractable props: none; navigation URLs or click behavior belong to the consuming draft.
- Hardcoded: visual variant classes, size classes, typography, radii, and transitions.

## FileUpload
- Source: `frontend/src/shared/ui/FileUpload.tsx`
- Category: basic
- Description: Single- or dual-slot PDF drag-and-drop uploader.
- Extractable props: `isDisabled` (boolean, default: false), `showSecondarySlot` (boolean, default: false).
- Hardcoded: PDF icon, helper copy, drop-zone structure, visual states, labels in each product flow, and CSS.

## ProgressOverlay
- Source: `frontend/src/shared/ui/ProgressOverlay.tsx`
- Category: basic
- Description: Modal task-progress surface with percentage, rule checklist, Codex audit status, and reset action.
- Extractable props: `showOverlay` (boolean, default: true), `progressPercent` (number, default: 48), `showCodexProgress` (boolean, default: true).
- Hardcoded: phase labels, progress structure, C01-C11 checklist presentation, semantic state colors, and CSS.

## CodexReviewPanel
- Source: `frontend/src/features/codex-review/components/CodexReviewPanel.tsx`
- Category: basic
- Description: Reusable overview and list patterns for rule-first findings plus Codex auditor decisions.
- Extractable props: `showReviewList` (boolean, default: true), `reviewCount` (number, default: 5).
- Hardcoded: five-way review taxonomy, status labels, badge styles, evidence structure, and CSS.

## ExportButtonGroup
- Source: `frontend/src/shared/ui/ExportButton.tsx`
- Category: basic
- Description: Three-button JSON, PDF, and XLSX export group.
- Extractable props: `isDisabled` (boolean, default: false).
- Hardcoded: export format labels, button order, and shared button styling.

## StatusPill
- Source: `frontend/src/shared/ui/StatusPill.tsx`
- Category: basic
- Description: Legacy READY/PENDING status pill retained by the unused legacy Dashboard component.
- Extractable props: `isReady` (boolean, default: true).
- Hardcoded: READY/PENDING text labels and pill styling.
