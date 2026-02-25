/**
 * MEGIDO spacing tokens.
 *
 * Base unit: 4px. All spacing values are multiples of the base unit.
 * The numeric scale maps index -> pixel value (index * 4px, with exceptions).
 * Named aliases provide semantic shortcuts.
 */

// ---------------------------------------------------------------------------
// Base unit
// ---------------------------------------------------------------------------

/** Base spacing unit in pixels. */
export const SPACING_BASE = 4;

// ---------------------------------------------------------------------------
// Numeric scale — index values (multiply by 4px to get pixels)
//
// Usage: `spacing.scale[4]` = "16px" (4 * 4px)
// ---------------------------------------------------------------------------

const scaleValues = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64] as const;

export const scale = Object.fromEntries(
  scaleValues.map((v) => [v, `${v * SPACING_BASE}px`])
) as Record<(typeof scaleValues)[number], string>;

// ---------------------------------------------------------------------------
// Named spacing — semantic aliases for common use cases
// ---------------------------------------------------------------------------

export const named = {
  /** 4px — hairline gap, icon padding */
  xs: `${1 * SPACING_BASE}px`,      // 4px
  /** 8px — tight gap between related elements */
  sm: `${2 * SPACING_BASE}px`,      // 8px
  /** 16px — default gap, card padding */
  md: `${4 * SPACING_BASE}px`,      // 16px
  /** 24px — section gap, card body padding */
  lg: `${6 * SPACING_BASE}px`,      // 24px
  /** 32px — large section gap */
  xl: `${8 * SPACING_BASE}px`,      // 32px
  /** 48px — page-level vertical gap */
  "2xl": `${12 * SPACING_BASE}px`,  // 48px
  /** 64px — hero/splash spacing */
  "3xl": `${16 * SPACING_BASE}px`,  // 64px
} as const;

// ---------------------------------------------------------------------------
// Layout-specific spacing
// ---------------------------------------------------------------------------

export const layout = {
  /** Padding inside the sidebar */
  sidebarPadding: named.md,          // 16px
  /** Width of the sidebar */
  sidebarWidth: "256px",
  /** Width of the collapsed sidebar */
  sidebarCollapsedWidth: "64px",
  /** Horizontal padding of page content */
  pageInline: named.lg,              // 24px
  /** Vertical padding of page content */
  pageBlock: named.lg,               // 24px
  /** Gap between cards in a grid */
  cardGap: named.md,                 // 16px
  /** Internal card padding */
  cardPadding: named.lg,             // 24px
  /** Gap between form fields */
  formGap: named.md,                 // 16px
  /** Height of the topbar */
  topbarHeight: "56px",
} as const;

// ---------------------------------------------------------------------------
// Merged spacing export
// ---------------------------------------------------------------------------

export const spacing = {
  base: SPACING_BASE,
  scale,
  named,
  layout,
} as const;

export type Spacing = typeof spacing;
