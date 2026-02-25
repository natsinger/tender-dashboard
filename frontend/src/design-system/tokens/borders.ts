/**
 * MEGIDO border tokens.
 *
 * Border radii, widths, and default colors for the design system.
 */

// ---------------------------------------------------------------------------
// Border radii
// ---------------------------------------------------------------------------

export const radius = {
  /** 0px — sharp corners (tables, code blocks) */
  none: "0px",
  /** 4px — subtle rounding (inputs, small elements) */
  sm: "4px",
  /** 8px — default rounding (cards, buttons) */
  md: "8px",
  /** 12px — pronounced rounding (large cards, modals) */
  lg: "12px",
  /** 16px — extra rounding (feature cards, hero elements) */
  xl: "16px",
  /** 9999px — pill shape (badges, tags, toggles) */
  full: "9999px",
} as const;

// ---------------------------------------------------------------------------
// Border widths
// ---------------------------------------------------------------------------

export const width = {
  /** 1px — default, most borders */
  thin: "1px",
  /** 2px — emphasis borders, active states */
  medium: "2px",
  /** 3px — heavy emphasis, section dividers */
  thick: "3px",
} as const;

// ---------------------------------------------------------------------------
// Border colors — reference the color token palette
// ---------------------------------------------------------------------------

export const borderColor = {
  /** Default border — light slate */
  default: "#E2E8F0",
  /** Stronger border — for emphasis */
  strong: "#CBD5E1",
  /** Focus border — primary blue */
  focus: "#2563EB",
  /** Error border — danger red */
  error: "#EF4444",
  /** Sidebar internal border */
  sidebar: "#334155",
} as const;

// ---------------------------------------------------------------------------
// Merged borders export
// ---------------------------------------------------------------------------

export const borders = {
  radius,
  width,
  color: borderColor,
} as const;

export type Borders = typeof borders;
