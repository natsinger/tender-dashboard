/**
 * MEGIDO shadow / elevation tokens.
 *
 * Five elevation levels from flat to modal overlay.
 * Includes blue-tinted hover shadows that match the Deep Blue palette.
 */

// ---------------------------------------------------------------------------
// Elevation levels
// ---------------------------------------------------------------------------

export const elevation = {
  /** No shadow — flush with surface */
  none: "none",
  /** Subtle lift — form inputs, flat cards */
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  /** Default card shadow */
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05)",
  /** Raised elements — dropdowns, popovers */
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04)",
  /** Floating elements — modals, sheets */
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.10), 0 8px 10px -6px rgba(0, 0, 0, 0.04)",
} as const;

// ---------------------------------------------------------------------------
// Semantic shadows — named by component
// ---------------------------------------------------------------------------

export const componentShadows = {
  /** Default card resting state */
  card: elevation.md,
  /** Card hover — blue-tinted for interactive feedback */
  cardHover: "0 8px 16px -4px rgba(37, 99, 235, 0.10), 0 4px 8px -4px rgba(37, 99, 235, 0.06)",
  /** Sidebar (fixed, drops shadow onto content) */
  sidebar: "4px 0 12px -2px rgba(0, 0, 0, 0.12)",
  /** RTL sidebar shadow (inverted direction) */
  sidebarRtl: "-4px 0 12px -2px rgba(0, 0, 0, 0.12)",
  /** Modal overlay */
  modal: elevation.xl,
  /** Dropdown / popover */
  dropdown: elevation.lg,
  /** Topbar (bottom edge shadow) */
  topbar: "0 1px 3px 0 rgba(0, 0, 0, 0.06)",
  /** Blue-tinted focus ring shadow (used alongside outline) */
  focusRing: "0 0 0 3px rgba(37, 99, 235, 0.15)",
  /** Button hover — subtle blue glow */
  buttonHover: "0 4px 12px -2px rgba(37, 99, 235, 0.20)",
} as const;

// ---------------------------------------------------------------------------
// Merged shadows export
// ---------------------------------------------------------------------------

export const shadows = {
  elevation,
  component: componentShadows,
} as const;

export type Shadows = typeof shadows;
