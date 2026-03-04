/**
 * Design system token barrel.
 *
 * Re-exports every token module and provides a merged `theme` object
 * that gives one-stop access to the complete design language.
 *
 * Usage:
 *   import { theme } from "@/design-system/tokens";
 *   theme.colors.core.primary  // "#2563EB"
 *
 * Or import individual modules:
 *   import { corePalette, primaryScale } from "@/design-system/tokens/colors";
 */

// Individual module re-exports
export {
  colors,
  corePalette,
  primaryScale,
  secondaryScale,
  accentScale,
  neutralScale,
  successScale,
  warningScale,
  dangerScale,
  semantic,
} from "./colors";
export type { Colors, CorePalette, ColorScale, SemanticColors } from "./colors";

export {
  typography,
  fontFamily,
  fontSize,
  headingSize,
  bodySize,
  labelSize,
  fontWeight,
  lineHeight,
  letterSpacing,
} from "./typography";
export type { Typography } from "./typography";

export {
  spacing,
  SPACING_BASE,
  scale as spacingScale,
  named as namedSpacing,
} from "./spacing";
export type { Spacing } from "./spacing";

export { shadows, elevation, componentShadows } from "./shadows";
export type { Shadows } from "./shadows";

export { borders, radius, width as borderWidth, borderColor } from "./borders";
export type { Borders } from "./borders";

export {
  chartColors,
  MEGIDO_CHART_COLORS,
  MEGIDO_CHART_COLORS_EXTENDED,
  categoricalColors,
  goldHeatmapScale,
  blueHeatmapScale,
  statusColors,
  divergingColors,
} from "./chart-colors";
export type { ChartColors } from "./chart-colors";

// ---------------------------------------------------------------------------
// Import concrete objects for the merged theme
// ---------------------------------------------------------------------------
import { colors } from "./colors";
import { typography } from "./typography";
import { spacing } from "./spacing";
import { shadows } from "./shadows";
import { borders } from "./borders";
import { chartColors } from "./chart-colors";

// ---------------------------------------------------------------------------
// Merged theme
// ---------------------------------------------------------------------------

export const theme = {
  colors,
  typography,
  spacing,
  shadows,
  borders,
  chartColors,
} as const;

export type Theme = typeof theme;

// ---------------------------------------------------------------------------
// CSS custom property generator
//
// Call `generateCssCustomProperties()` to get a flat record of
// `--megido-*` property names to values. Useful for injecting tokens
// into CSS-in-JS or a <style> tag at build time.
// ---------------------------------------------------------------------------

export function generateCssCustomProperties(): Record<string, string> {
  const props: Record<string, string> = {};

  // Core palette
  for (const [key, value] of Object.entries(colors.core)) {
    props[`--megido-${camelToKebab(key)}`] = value;
  }

  // Color scales
  const scales = {
    primary: colors.primary,
    secondary: colors.secondary,
    accent: colors.accent,
    neutral: colors.neutral,
    success: colors.success,
    warning: colors.warning,
    danger: colors.danger,
  } as const;

  for (const [scaleName, scaleObj] of Object.entries(scales)) {
    for (const [step, value] of Object.entries(scaleObj)) {
      props[`--megido-${scaleName}-${step}`] = value;
    }
  }

  // Semantic aliases
  for (const [key, value] of Object.entries(colors.semantic)) {
    props[`--megido-${key}`] = value;
  }

  // Shadows
  for (const [key, value] of Object.entries(shadows.elevation)) {
    props[`--megido-shadow-${key}`] = value;
  }
  for (const [key, value] of Object.entries(shadows.component)) {
    props[`--megido-shadow-${camelToKebab(key)}`] = value;
  }

  // Border radii
  for (const [key, value] of Object.entries(borders.radius)) {
    props[`--megido-radius-${key}`] = value;
  }

  return props;
}

/** Convert camelCase to kebab-case: "primaryHover" -> "primary-hover". */
function camelToKebab(str: string): string {
  return str.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
}
