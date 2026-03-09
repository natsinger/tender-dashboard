# MEGIDO Dashboard Design Critique Report

**Date:** 2026-03-08
**Reviewer:** Automated Design Audit (Claude)
**Scope:** Full frontend application (`frontend/src/`)

---

## Overall Score: 64/100 — Grade: C+

> **Solid foundation with significant gaps in design system compliance and UX polish.**
> The dashboard has a well-structured component architecture, good use of shadcn/ui primitives, and a functional design system scaffold. However, the system is underutilized — tokens are defined but bypassed, variants are declared but unused, and critical UX patterns (error handling, confirmations, accessibility) are missing.

### Score Breakdown

| # | Dimension | Weight | Raw Score | Weighted |
|---|-----------|--------|-----------|----------|
| 1 | Design System Compliance | 15% | 52 | 7.8 |
| 2 | Layout & Visual Hierarchy | 20% | 68 | 13.6 |
| 3 | Component Quality | 20% | 72 | 14.4 |
| 4 | Responsive & RTL | 20% | 62 | 12.4 |
| 5 | UX Heuristics | 25% | 62 | 15.5 |
| | **Overall** | **100%** | | **63.7 → 64** |

---

## Top 5 Strengths

1. **Well-structured component hierarchy** — Clear separation between pages, layout components, feature components, and UI primitives. Each page has a dedicated directory with focused sub-components.

2. **Design system scaffold exists** — Token files for colors, typography, spacing, borders, shadows, and chart colors are defined in `src/design-system/tokens/`. The foundation is there; it just needs consistent adoption.

3. **shadcn/ui primitives well-integrated** — Button, Card, Dialog, Table, Tabs, Badge, and other UI components follow shadcn/ui patterns with proper variant support via `cva`.

4. **Custom hooks for data fetching** — `use-tenders`, `use-watchlist`, `use-analytics`, `use-documents`, `use-reviews` etc. cleanly encapsulate Supabase queries, keeping components focused on rendering.

5. **Zustand for state management** — Filter store and auth store use Zustand, which is lightweight and appropriate for the project scale. No over-engineering with Redux.

---

## Top 10 Action Items

| # | Title | Severity | Effort | Dimension | Description | Files |
|---|-------|----------|--------|-----------|-------------|-------|
| 1 | **Replace hardcoded colors with design tokens** | High | Medium | Design System | 30+ instances of `text-slate-*`, `bg-slate-*`, `border-slate-*` bypass the token system. Charts use raw hex values (`#4F46E5`, `#10B981`, etc.) instead of importing from `chart-colors.ts`. | `components/charts/*.tsx`, `components/dashboard/*.tsx`, `components/metric-card.tsx` |
| 2 | **Convert physical CSS to logical properties for RTL** | High | Medium | Responsive & RTL | Pervasive use of `right-0`, `left-0`, `border-l`, `mr-*`, `pr-*`, `pl-*` instead of logical equivalents (`border-inline-start`, `me-*`, `ps-*`, `pe-*`). Breaks RTL layout. | `components/layout/sidebar-nav.tsx`, `components/layout/topbar.tsx`, `components/filter-bar.tsx`, `components/dashboard/*.tsx` |
| 3 | **Add error boundaries and error states** | High | Medium | Component Quality / UX | No React Error Boundaries wrapping page sections (note: `error-boundary.tsx` exists but needs to wrap key sections). No user-facing error states when Supabase queries fail — components silently render empty. | `app/(dashboard)/layout.tsx`, all page components, `components/charts/*.tsx` |
| 4 | **Add confirmation dialogs for destructive actions** | High | Small | UX Heuristics | Watchlist removal and review status changes execute immediately with no confirmation. Users can accidentally delete tracked tenders. | `components/watchlist-manager.tsx`, `components/review-status-editor.tsx` |
| 5 | **Add toast/notification system** | High | Small | UX Heuristics | No feedback after mutations (add to watchlist, change review status, etc.). Users cannot tell if their action succeeded or failed. | `components/watchlist-manager.tsx`, `components/review-status-editor.tsx`, `app/(dashboard)/layout.tsx` |
| 6 | **Restructure dashboard layout hierarchy** | Medium | Medium | Layout & Visual Hierarchy | KPI MetricCards are subordinated in a `2fr` column while tables get `3fr`. ReviewStatusTable (most actionable content) is buried as the 3rd section. KPIs should be top-row, review table should be elevated. | `app/(dashboard)/dashboard/page.tsx`, `components/dashboard/*.tsx` |
| 7 | **Fix chart RTL axis orientation** | Medium | Small | Responsive & RTL | Recharts Y-axis renders on the left (LTR default). For Hebrew RTL, the Y-axis should be on the right side. Add `orientation="right"` to YAxis components. | `components/charts/bar-chart.tsx`, `components/charts/line-chart.tsx`, `components/dashboard/city-bar-chart.tsx` |
| 8 | **Standardize font sizes to design tokens** | Medium | Small | Design System | 4 non-standard font sizes used: `text-[11px]`, `text-[13px]`, `text-[15px]`, `text-[22px]`. These should map to the typography scale in `tokens/typography.ts`. | Various component files |
| 9 | **Add ARIA labels and keyboard navigation to charts** | Medium | Medium | Component Quality | Chart SVGs have no `aria-label` or `role="img"`. No `tabIndex` for keyboard navigation. Screen readers cannot interpret chart content. | `components/charts/*.tsx`, `components/charts/chart-wrapper.tsx` |
| 10 | **Remove duplicate city chart and reduce table page sizes** | Low | Small | Layout & Visual Hierarchy | City distribution chart appears in both dashboard and DetailedAnalytics. Document tables with `pageSize=8` push 700px+ of content; review table `pageSize=20` creates 800px of scroll. Reduce defaults. | `components/dashboard/detailed-analytics.tsx`, `components/dashboard/city-bar-chart.tsx`, `components/dashboard/new-documents-section.tsx`, `components/dashboard/review-status-table.tsx` |

---

## Quick Wins (< 1 hour each, high impact)

### 1. Add Toast Notifications
Install `sonner` (already compatible with shadcn/ui). Wrap layout in `<Toaster />`. Add `toast.success()` / `toast.error()` calls after mutation hooks resolve.
- **Files:** `app/(dashboard)/layout.tsx`, `components/watchlist-manager.tsx`, `components/review-status-editor.tsx`
- **Impact:** Immediately improves user confidence in all actions

### 2. Confirmation Dialog for Deletions
Use the existing `Dialog` component from `components/ui/dialog.tsx` to wrap the watchlist remove action in a confirm/cancel flow.
- **Files:** `components/watchlist-manager.tsx`
- **Impact:** Prevents accidental data loss

### 3. Fix Chart Y-Axis for RTL
Add `orientation="right"` to all `<YAxis>` components in Recharts. One prop change per chart.
- **Files:** `components/charts/bar-chart.tsx`, `components/charts/line-chart.tsx`, `components/dashboard/city-bar-chart.tsx`
- **Impact:** Charts read correctly in Hebrew context

### 4. Apply `ltr-nums` Utility
The `ltr-nums` class is defined in CSS but never applied. Add it to all numeric displays (MetricCards, table cells with amounts/dates).
- **Files:** `components/metric-card.tsx`, `components/data-table.tsx`
- **Impact:** Numbers display correctly in RTL context

### 5. Remove Duplicate City Chart
The city distribution bar chart appears in both the dashboard overview and DetailedAnalytics. Remove the duplicate instance.
- **Files:** `components/dashboard/detailed-analytics.tsx`
- **Impact:** Reduces visual clutter and page weight

---

## Strategic Improvements (Larger Changes)

### 1. Design Token Migration (2-3 days)
Systematically replace all hardcoded Tailwind color classes (`text-slate-600`, `bg-gray-50`, etc.) with semantic token references. Update chart components to import from `chart-colors.ts`. Remove unused tokens and add missing ones. Wire up `cva` variants in `variants.ts` to actual components.

**Goal:** Raise Design System Compliance from 52 to 80+.

### 2. RTL-First CSS Refactor (1-2 days)
Audit all physical CSS properties and convert to logical equivalents. Tailwind v4 supports logical properties natively (`ms-*`, `me-*`, `ps-*`, `pe-*`, `border-s-*`). This is a search-and-replace operation across all component files.

**Goal:** Raise Responsive & RTL from 62 to 80+.

### 3. Dashboard Layout Restructure (1 day)
Redesign the dashboard page layout:
- KPI MetricCards as full-width top row
- ReviewStatusTable elevated to primary position (above document tables)
- Reduce default page sizes (documents: 5, reviews: 10)
- Add page title to topbar
- Add anchor-link in-page navigation for long pages

**Goal:** Raise Layout & Visual Hierarchy from 68 to 80+.

### 4. Comprehensive Error & Loading States (1-2 days)
- Wrap each dashboard section in an ErrorBoundary with a fallback UI
- Add skeleton loaders for all data-dependent sections
- Show inline error messages when Supabase queries fail
- Add retry buttons on error states

**Goal:** Raise UX Heuristics from 62 to 75+.

### 5. Mobile Responsiveness Pass (1-2 days)
- Ensure KPI cards stack properly on mobile (currently buried below tables)
- Make DashboardSidebar accessible via a Sheet/drawer on mobile
- Increase touch targets to minimum 44px
- Test all breakpoints with actual device widths

**Goal:** Raise Responsive & RTL further to 85+.

---

## Detailed Findings by Dimension

### 1. Design System Compliance (52/100)

**Token adoption rate: 48%** — Tokens are defined but not consistently consumed.

| Finding | Severity | Details |
|---------|----------|---------|
| Hardcoded Tailwind colors | High | 30+ instances of `text-slate-*`, `bg-slate-*`, `border-slate-*` used directly instead of through semantic token classes |
| Unused cva variants | High | `variants.ts` defines card, badge, and button variants via `cva` but no component imports or uses them |
| Non-standard font sizes | Medium | `text-[11px]`, `text-[13px]`, `text-[15px]`, `text-[22px]` — 4 arbitrary sizes outside the type scale |
| Chart colors hardcoded | Medium | Bar/Line/Pie charts use inline hex strings instead of importing from `tokens/chart-colors.ts` |
| Missing tokens | Low | 8 semantic tokens needed but not defined (e.g., `surface-hover`, `text-on-primary`, `border-focus`) |
| Unused tokens | Low | 11+ tokens defined in token files but never referenced in any component |

**Key files:** `src/design-system/tokens/*.ts`, `src/design-system/variants.ts`, `src/components/charts/*.tsx`

### 2. Layout & Visual Hierarchy (68/100)

| Finding | Severity | Details |
|---------|----------|---------|
| KPI cards under-weighted | High | Dashboard grid gives KPI column `2fr` vs tables `3fr`, making KPIs feel secondary |
| ReviewStatusTable buried | High | The most actionable section (review queue) is the 3rd section users see, after two document tables |
| Excessive table page sizes | Medium | Document tables default to `pageSize=8` (700px+), review table `pageSize=20` (800px+), pushing content below the fold |
| Duplicate city chart | Medium | City distribution bar chart rendered in both dashboard overview and DetailedAnalytics section |
| No page title in topbar | Low | Topbar shows logo and user menu but not the current page name |
| No in-page navigation | Low | Long pages (dashboard, analytics) have no anchor links or section nav |

**Key files:** `src/app/(dashboard)/dashboard/page.tsx`, `src/components/dashboard/*.tsx`, `src/components/layout/topbar.tsx`

### 3. Component Quality (72/100)

| Finding | Severity | Details |
|---------|----------|---------|
| PieChart wrong palette | Medium | Uses `MEGIDO_CHART_COLORS` constant instead of the `categoricalColors` token from the design system |
| Tooltip shows raw keys | Medium | Chart tooltips display English data keys (e.g., `total_estimated`) instead of Hebrew labels |
| No ARIA labels on charts | Medium | Chart SVG containers lack `aria-label`, `role="img"`, or `aria-describedby` |
| No Error Boundaries in use | Medium | `error-boundary.tsx` exists but is not wrapping any page sections |
| Misleading hover states | Low | Cards have `hover:shadow-lg` transitions but are not clickable, creating false affordance |
| No error states for API failures | High | Components render empty/blank when Supabase queries fail — no error message shown to user |

**Key files:** `src/components/charts/pie-chart.tsx`, `src/components/charts/chart-wrapper.tsx`, `src/components/error-boundary.tsx`, `src/components/metric-card.tsx`

### 4. Responsive & RTL (62/100)

| Finding | Severity | Details |
|---------|----------|---------|
| Physical CSS properties | High | Widespread `right-0`, `left-0`, `border-l`, `mr-*`, `ml-*`, `pr-*`, `pl-*` instead of logical properties |
| Chart Y-axis wrong side | High | Recharts defaults Y-axis to left (LTR). Hebrew RTL users expect it on the right |
| `ltr-nums` never applied | Medium | Utility class defined in global CSS but not applied to any numeric content |
| KPIs buried on mobile | Medium | MetricCards end up below long tables on small screens due to grid ordering |
| Sidebar inaccessible on mobile | Medium | DashboardSidebar has no responsive drawer/sheet alternative for mobile |
| Touch targets too small | Low | Several interactive elements (table action buttons, filter chips) measure < 44px |

**Key files:** `src/components/layout/sidebar-nav.tsx`, `src/components/layout/topbar.tsx`, `src/components/charts/*.tsx`, `src/components/dashboard/dashboard-sidebar.tsx`

### 5. UX Heuristics (62/100)

| Finding | Severity | Details |
|---------|----------|---------|
| No toast/notification system | High | Mutations (watchlist add/remove, status change) provide zero feedback |
| No destructive action confirmation | High | Watchlist deletion and review status changes execute immediately |
| No error surfacing | High | Failed data fetches result in empty screens with no explanation |
| No onboarding / help | Medium | New users have no tooltips, walkthrough, or help page |
| No table filtering | Medium | Tables lack column-level filtering (only global filter bar exists) |
| No data export | Medium | No CSV/Excel export from any table view (note: `csv-export.tsx` exists for explorer only) |
| No keyboard shortcuts | Low | Power users cannot navigate or act without mouse |
| Non-clickable hover cards | Low | Cards suggest interactivity via hover effects but clicking does nothing |

**Key files:** `src/components/watchlist-manager.tsx`, `src/components/review-status-editor.tsx`, `src/components/explorer/csv-export.tsx`, `src/components/data-table.tsx`

---

## Methodology

This critique was conducted through systematic static analysis of the frontend source code in `frontend/src/`. Each dimension was evaluated by:

1. **Design System Compliance** — Grep-based audit of token usage vs. hardcoded values, cross-referencing defined tokens against actual imports.
2. **Layout & Visual Hierarchy** — Review of page layouts, grid configurations, component ordering, and content density.
3. **Component Quality** — Analysis of prop interfaces, error handling patterns, accessibility attributes, and data visualization correctness.
4. **Responsive & RTL** — Audit of CSS property directionality, breakpoint behavior, touch target sizing, and BiDi text handling.
5. **UX Heuristics** — Evaluation against Nielsen's 10 Usability Heuristics, focusing on feedback, error prevention, and user control.

Scores reflect the current state of the codebase as of 2026-03-08. The weighted formula prioritizes UX Heuristics (25%) as the dimension most directly impacting user satisfaction, with Layout, Component Quality, and RTL equally weighted (20% each), and Design System Compliance at 15% as an internal engineering concern.
