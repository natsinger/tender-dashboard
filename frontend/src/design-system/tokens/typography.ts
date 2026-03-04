/**
 * MEGIDO typography tokens.
 *
 * Font families, type scale (1.25 ratio, 16px base), weights, and line heights.
 * Hebrew body text uses Heebo; Latin headings/UI uses Inter; code uses JetBrains Mono.
 */

// ---------------------------------------------------------------------------
// Font families
// ---------------------------------------------------------------------------

export const fontFamily = {
  /** Latin / UI text — loaded via next/font/google in layout.tsx */
  sans: "var(--font-inter), var(--font-heebo), system-ui, sans-serif",
  /** Hebrew body text */
  hebrew: "var(--font-heebo), sans-serif",
  /** Code / monospace */
  mono: "'JetBrains Mono', ui-monospace, SFMono-Regular, monospace",
} as const;

// ---------------------------------------------------------------------------
// Type scale — Major Third (1.25 ratio), base 16px
//
//   step -2  = 10.24px  (xs)
//   step -1  = 12.80px  (sm)
//   step  0  = 16.00px  (base)
//   step  1  = 20.00px  (lg)
//   step  2  = 25.00px  (xl)
//   step  3  = 31.25px  (2xl)
//   step  4  = 39.06px  (3xl)
//   step  5  = 48.83px  (4xl)
//   step  6  = 61.04px  (5xl)
// ---------------------------------------------------------------------------

export const fontSize = {
  xs: "0.64rem",    // 10.24px
  sm: "0.80rem",    // 12.80px
  base: "1rem",     // 16px
  lg: "1.25rem",    // 20px
  xl: "1.563rem",   // 25px
  "2xl": "1.953rem", // 31.25px
  "3xl": "2.441rem", // 39.06px
  "4xl": "3.052rem", // 48.83px
  "5xl": "3.815rem", // 61.04px
} as const;

// ---------------------------------------------------------------------------
// Heading presets — map semantic headings to scale steps
// ---------------------------------------------------------------------------

export const headingSize = {
  h1: fontSize["4xl"],  // 48.83px — page titles
  h2: fontSize["3xl"],  // 39.06px — section titles
  h3: fontSize["2xl"],  // 31.25px — subsection titles
  h4: fontSize.xl,      // 25px — card titles
  h5: fontSize.lg,      // 20px — widget titles
  h6: fontSize.base,    // 16px — small headings
} as const;

// ---------------------------------------------------------------------------
// Body text presets
// ---------------------------------------------------------------------------

export const bodySize = {
  sm: fontSize.sm,     // 12.80px — captions, meta text
  base: fontSize.base, // 16px — default body
  lg: fontSize.lg,     // 20px — lead text, callouts
} as const;

// ---------------------------------------------------------------------------
// Label sizes (form labels, badges, tags)
// ---------------------------------------------------------------------------

export const labelSize = {
  xs: fontSize.xs,   // 10.24px — tiny labels
  sm: fontSize.sm,   // 12.80px — default labels
  base: fontSize.base, // 16px — large labels
} as const;

// ---------------------------------------------------------------------------
// Font weights
// ---------------------------------------------------------------------------

export const fontWeight = {
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
} as const;

// ---------------------------------------------------------------------------
// Line heights
// ---------------------------------------------------------------------------

export const lineHeight = {
  none: "1",
  tight: "1.25",
  snug: "1.375",
  normal: "1.5",
  relaxed: "1.75",
  loose: "2",
} as const;

// ---------------------------------------------------------------------------
// Letter spacing
// ---------------------------------------------------------------------------

export const letterSpacing = {
  tighter: "-0.05em",
  tight: "-0.025em",
  normal: "0em",
  wide: "0.025em",
  wider: "0.05em",
} as const;

// ---------------------------------------------------------------------------
// Merged typography export
// ---------------------------------------------------------------------------

export const typography = {
  fontFamily,
  fontSize,
  headingSize,
  bodySize,
  labelSize,
  fontWeight,
  lineHeight,
  letterSpacing,
} as const;

export type Typography = typeof typography;
