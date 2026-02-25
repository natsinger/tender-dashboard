/**
 * MEGIDO Deep Blue color tokens.
 *
 * Single source of truth for every color in the design system.
 * To rebrand, update the values here and regenerate CSS custom properties
 * via the `generateCssCustomProperties()` helper in tokens/index.ts.
 *
 * Structure:
 *   - Core palette (flat hex values)
 *   - Color scales (50-950 HSL-derived shades for primary, secondary, accent)
 *   - Semantic aliases (map purpose -> palette color)
 */

// ---------------------------------------------------------------------------
// Core palette
// ---------------------------------------------------------------------------

export const corePalette = {
  primary: "#2563EB",
  primaryHover: "#1D4ED8",
  primaryLight: "#DBEAFE",
  secondary: "#1E3A5F",
  accent: "#60A5FA",
  bgMain: "#F8FAFC",
  bgCard: "#FFFFFF",
  sidebarBg: "#0F172A",
  textHeading: "#1E293B",
  textBody: "#334155",
  textMuted: "#64748B",
  textOnDark: "#E2E8F0",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  border: "#E2E8F0",
} as const;

// ---------------------------------------------------------------------------
// Color scales (50-950)
// Derived from the base hue of each core color using HSL shifts.
// ---------------------------------------------------------------------------

export const primaryScale = {
  50: "#EFF6FF",
  100: "#DBEAFE",
  200: "#BFDBFE",
  300: "#93C5FD",
  400: "#60A5FA",
  500: "#3B82F6",
  600: "#2563EB",
  700: "#1D4ED8",
  800: "#1E40AF",
  900: "#1E3A8A",
  950: "#172554",
} as const;

export const secondaryScale = {
  50: "#F0F4F8",
  100: "#D9E2EC",
  200: "#BCCCDC",
  300: "#9FB3C8",
  400: "#829AB1",
  500: "#627D98",
  600: "#486581",
  700: "#334E68",
  800: "#1E3A5F",
  900: "#163152",
  950: "#0F2440",
} as const;

export const accentScale = {
  50: "#EFF6FF",
  100: "#DBEAFE",
  200: "#BFDBFE",
  300: "#93C5FD",
  400: "#60A5FA",
  500: "#3B82F6",
  600: "#2563EB",
  700: "#1D4ED8",
  800: "#1E40AF",
  900: "#1E3A8A",
  950: "#172554",
} as const;

export const neutralScale = {
  50: "#F8FAFC",
  100: "#F1F5F9",
  200: "#E2E8F0",
  300: "#CBD5E1",
  400: "#94A3B8",
  500: "#64748B",
  600: "#475569",
  700: "#334155",
  800: "#1E293B",
  900: "#0F172A",
  950: "#020617",
} as const;

export const successScale = {
  50: "#ECFDF5",
  100: "#D1FAE5",
  200: "#A7F3D0",
  300: "#6EE7B7",
  400: "#34D399",
  500: "#10B981",
  600: "#059669",
  700: "#047857",
  800: "#065F46",
  900: "#064E3B",
  950: "#022C22",
} as const;

export const warningScale = {
  50: "#FFFBEB",
  100: "#FEF3C7",
  200: "#FDE68A",
  300: "#FCD34D",
  400: "#FBBF24",
  500: "#F59E0B",
  600: "#D97706",
  700: "#B45309",
  800: "#92400E",
  900: "#78350F",
  950: "#451A03",
} as const;

export const dangerScale = {
  50: "#FEF2F2",
  100: "#FEE2E2",
  200: "#FECACA",
  300: "#FCA5A5",
  400: "#F87171",
  500: "#EF4444",
  600: "#DC2626",
  700: "#B91C1C",
  800: "#991B1B",
  900: "#7F1D1D",
  950: "#450A0A",
} as const;

// ---------------------------------------------------------------------------
// Semantic aliases — map purpose to concrete values.
// Components should reference these rather than raw hex where possible.
// ---------------------------------------------------------------------------

export const semantic = {
  // Surfaces
  "card-bg": corePalette.bgCard,
  "page-bg": corePalette.bgMain,
  "sidebar-bg": corePalette.sidebarBg,
  "input-bg": corePalette.bgCard,
  "muted-bg": neutralScale[100],

  // Text
  heading: corePalette.textHeading,
  body: corePalette.textBody,
  muted: corePalette.textMuted,
  "on-dark": corePalette.textOnDark,
  "on-primary": "#FFFFFF",

  // Interactive
  "interactive-default": corePalette.primary,
  "interactive-hover": corePalette.primaryHover,
  "interactive-active": primaryScale[800],
  "interactive-focus-ring": corePalette.primary,

  // Feedback
  "feedback-success": corePalette.success,
  "feedback-warning": corePalette.warning,
  "feedback-danger": corePalette.danger,
  "feedback-info": corePalette.accent,

  // Borders
  "border-default": corePalette.border,
  "border-strong": neutralScale[300],
  "border-focus": corePalette.primary,

  // Sidebar
  "sidebar-text": corePalette.textOnDark,
  "sidebar-active": corePalette.primary,
  "sidebar-hover": neutralScale[800],
} as const;

// ---------------------------------------------------------------------------
// Merged colors export
// ---------------------------------------------------------------------------

export const colors = {
  core: corePalette,
  primary: primaryScale,
  secondary: secondaryScale,
  accent: accentScale,
  neutral: neutralScale,
  success: successScale,
  warning: warningScale,
  danger: dangerScale,
  semantic,
} as const;

export type CorePalette = typeof corePalette;
export type ColorScale = typeof primaryScale;
export type SemanticColors = typeof semantic;
export type Colors = typeof colors;
