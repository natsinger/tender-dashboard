/**
 * BrochureToggle component.
 *
 * Two-pill toggle filter for brochure availability: "הכל" (all) or
 * "עם חוברת" (with brochure). Matches the Streamlit st.pills pattern
 * from the management page.
 */
"use client";

import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type BrochureFilter = "all" | "with_brochure";

interface BrochureToggleProps {
  /** Current selected value. */
  value: BrochureFilter;
  /** Callback when the selection changes. */
  onChange: (value: BrochureFilter) => void;
  /** Additional CSS classes on the outer container. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Pill data
// ---------------------------------------------------------------------------

const PILLS: { value: BrochureFilter; label: string }[] = [
  { value: "all", label: "\u05D4\u05DB\u05DC" },
  { value: "with_brochure", label: "\u05E2\u05DD \u05D7\u05D5\u05D1\u05E8\u05EA" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BrochureToggle({
  value,
  onChange,
  className,
}: BrochureToggleProps) {
  return (
    <div
      dir="rtl"
      className={cn(
        "inline-flex items-center gap-1 rounded-lg bg-megido-neutral-100 p-1",
        className,
      )}
    >
      {PILLS.map((pill) => {
        const isActive = pill.value === value;
        return (
          <button
            key={pill.value}
            type="button"
            onClick={() => onChange(pill.value)}
            className={cn(
              "rounded-md px-3 py-1 text-sm font-medium transition-colors",
              isActive
                ? "bg-megido-primary text-white shadow-sm"
                : "bg-transparent text-megido-text-muted hover:text-megido-neutral-700",
            )}
          >
            {pill.label}
          </button>
        );
      })}
    </div>
  );
}

export type { BrochureFilter };
