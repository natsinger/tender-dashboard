/**
 * HebrewTooltip component.
 *
 * Custom Recharts tooltip that formats numbers with Hebrew locale,
 * maps English data keys to Hebrew labels, and renders in RTL layout
 * with MEGIDO design system styling.
 */
"use client";

import { corePalette, neutralScale } from "@/design-system/tokens/colors";

// ---------------------------------------------------------------------------
// Default English key → Hebrew label mapping
// ---------------------------------------------------------------------------

const DEFAULT_LABEL_MAP: Record<string, string> = {
  tender_count: "מכרזים",
  total_units: 'יח"ד',
  count: "כמות",
  units: 'יח"ד',
  value: "ערך",
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TooltipPayloadEntry {
  name?: string;
  dataKey?: string | number;
  value?: number | string;
  color?: string;
  payload?: Record<string, unknown>;
}

interface HebrewTooltipProps {
  /** Whether the tooltip is currently active (provided by Recharts). */
  active?: boolean;
  /** Tooltip payload entries (provided by Recharts). */
  payload?: TooltipPayloadEntry[];
  /** Category axis label (provided by Recharts). */
  label?: string | number;
  /** Optional override map for data key → Hebrew label. */
  labelMap?: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatValue(val: unknown): string {
  if (typeof val === "number") {
    return val.toLocaleString("he-IL");
  }
  return String(val ?? "");
}

function resolveLabel(
  key: string | number | undefined,
  labelMap?: Record<string, string>,
): string {
  const k = String(key ?? "");
  return labelMap?.[k] ?? DEFAULT_LABEL_MAP[k] ?? k;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function HebrewTooltip({
  active,
  payload,
  label,
  labelMap,
}: HebrewTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div
      dir="rtl"
      style={{
        backgroundColor: corePalette.bgCard,
        border: `1px solid ${neutralScale[200]}`,
        borderRadius: 8,
        padding: "8px 12px",
        boxShadow: "0 2px 8px rgba(0, 0, 0, 0.12)",
        fontSize: 13,
        lineHeight: 1.6,
        color: corePalette.textBody,
      }}
    >
      {label != null && label !== "" && (
        <p
          style={{
            margin: 0,
            marginBottom: 4,
            fontWeight: 600,
            color: corePalette.textHeading,
          }}
        >
          {String(label)}
        </p>
      )}

      {payload.map((entry, idx) => {
        const key = String(entry.dataKey ?? entry.name ?? idx);
        const hebrewLabel = resolveLabel(entry.dataKey ?? entry.name, labelMap);

        return (
          <p key={key + idx} style={{ margin: 0 }}>
            <span
              style={{
                display: "inline-block",
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: entry.color ?? corePalette.primary,
                marginLeft: 6,
              }}
            />
            {hebrewLabel}: {formatValue(entry.value)}
          </p>
        );
      })}
    </div>
  );
}
