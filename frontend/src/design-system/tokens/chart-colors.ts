/**
 * MEGIDO chart color tokens.
 *
 * Color palettes optimized for data visualization:
 *   - Primary ordered palette for bar/line/area charts
 *   - Categorical palette for pie/donut charts (maximizes visual distinction)
 *   - Gold heatmap scale for intensity maps
 *   - Status palette for KPI/metric indicators
 *   - Diverging palette for comparison charts
 */

// ---------------------------------------------------------------------------
// Primary chart palette — ordered by visual weight
// Used for bar, line, area charts where order matters.
// ---------------------------------------------------------------------------

export const MEGIDO_CHART_COLORS = [
  "#2563EB", // primary blue
  "#1E3A5F", // secondary navy
  "#60A5FA", // accent sky
  "#10B981", // success green
  "#F59E0B", // warning amber
  "#EF4444", // danger red
] as const;

// ---------------------------------------------------------------------------
// Extended palette — for charts with more than 6 categories
// ---------------------------------------------------------------------------

export const MEGIDO_CHART_COLORS_EXTENDED = [
  ...MEGIDO_CHART_COLORS,
  "#8B5CF6", // violet
  "#EC4899", // pink
  "#14B8A6", // teal
  "#F97316", // orange
  "#6366F1", // indigo
  "#84CC16", // lime
] as const;

// ---------------------------------------------------------------------------
// Categorical palette — maximizes perceptual distance between colors
// Best for pie charts, donut charts, and legends.
// ---------------------------------------------------------------------------

export const categoricalColors = [
  "#2563EB", // blue
  "#10B981", // green
  "#F59E0B", // amber
  "#EF4444", // red
  "#8B5CF6", // violet
  "#EC4899", // pink
  "#14B8A6", // teal
  "#F97316", // orange
  "#1E3A5F", // navy
  "#84CC16", // lime
] as const;

// ---------------------------------------------------------------------------
// Gold heatmap scale — warm progression for intensity/density maps
// From light cream to deep gold to dark brown.
// ---------------------------------------------------------------------------

export const goldHeatmapScale = [
  "#FFFBEB", // 50  — nearly white
  "#FEF3C7", // 100 — cream
  "#FDE68A", // 200 — light gold
  "#FCD34D", // 300 — gold
  "#FBBF24", // 400 — amber
  "#F59E0B", // 500 — deep amber
  "#D97706", // 600 — dark amber
  "#B45309", // 700 — brown
  "#92400E", // 800 — deep brown
  "#78350F", // 900 — dark brown
] as const;

// ---------------------------------------------------------------------------
// Blue heatmap scale — cool progression for density/volume maps
// ---------------------------------------------------------------------------

export const blueHeatmapScale = [
  "#EFF6FF", // 50
  "#DBEAFE", // 100
  "#BFDBFE", // 200
  "#93C5FD", // 300
  "#60A5FA", // 400
  "#3B82F6", // 500
  "#2563EB", // 600
  "#1D4ED8", // 700
  "#1E40AF", // 800
  "#1E3A8A", // 900
] as const;

// ---------------------------------------------------------------------------
// Status colors — for KPI badges, status indicators, sparklines
// ---------------------------------------------------------------------------

export const statusColors = {
  positive: "#10B981",
  negative: "#EF4444",
  neutral: "#64748B",
  warning: "#F59E0B",
  info: "#2563EB",
} as const;

// ---------------------------------------------------------------------------
// Diverging palette — for comparison charts (positive vs negative)
// Center value is neutral gray; extremes are green / red.
// ---------------------------------------------------------------------------

export const divergingColors = [
  "#EF4444", // strong negative
  "#F87171", // moderate negative
  "#FCA5A5", // slight negative
  "#E2E8F0", // neutral
  "#6EE7B7", // slight positive
  "#34D399", // moderate positive
  "#10B981", // strong positive
] as const;

// ---------------------------------------------------------------------------
// Merged chart colors export
// ---------------------------------------------------------------------------

export const chartColors = {
  primary: MEGIDO_CHART_COLORS,
  extended: MEGIDO_CHART_COLORS_EXTENDED,
  categorical: categoricalColors,
  goldHeatmap: goldHeatmapScale,
  blueHeatmap: blueHeatmapScale,
  status: statusColors,
  diverging: divergingColors,
} as const;

export type ChartColors = typeof chartColors;
