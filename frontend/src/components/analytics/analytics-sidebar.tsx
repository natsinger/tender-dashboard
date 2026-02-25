/**
 * Analytics sidebar component.
 *
 * Provides date range picker (start/end), region multiselect, and
 * quick stats footer showing record counts and last update time.
 * Designed for the right side in RTL layout.
 */
"use client";

import { useCallback } from "react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AnalyticsSidebarProps {
  /** ISO date of earliest publish_date in dataset. */
  minDate: string | null;
  /** ISO date of latest publish_date in dataset. */
  maxDate: string | null;
  /** Current start filter value. */
  startDate: string | null;
  /** Current end filter value. */
  endDate: string | null;
  /** Available region options. */
  regions: string[];
  /** Currently selected regions. */
  selectedRegions: string[];
  /** Total number of filtered tenders. */
  filteredCount: number;
  /** Total number of relevant (unfiltered) tenders. */
  totalCount: number;
  /** Callback when start date changes. */
  onStartDateChange: (value: string | null) => void;
  /** Callback when end date changes. */
  onEndDateChange: (value: string | null) => void;
  /** Callback when region selection changes. */
  onRegionsChange: (value: string[]) => void;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AnalyticsSidebar({
  minDate,
  maxDate,
  startDate,
  endDate,
  regions,
  selectedRegions,
  filteredCount,
  totalCount,
  onStartDateChange,
  onEndDateChange,
  onRegionsChange,
  className,
}: AnalyticsSidebarProps) {
  const handleRegionToggle = useCallback(
    (region: string) => {
      if (selectedRegions.includes(region)) {
        onRegionsChange(selectedRegions.filter((r) => r !== region));
      } else {
        onRegionsChange([...selectedRegions, region]);
      }
    },
    [selectedRegions, onRegionsChange],
  );

  const handleClearRegions = useCallback(() => {
    onRegionsChange([]);
  }, [onRegionsChange]);

  const handleClearDates = useCallback(() => {
    onStartDateChange(null);
    onEndDateChange(null);
  }, [onStartDateChange, onEndDateChange]);

  const now = new Date();
  const dateStr = new Intl.DateTimeFormat("he-IL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(now);

  return (
    <aside
      className={cn(
        "space-y-5 rounded-xl border border-slate-200 bg-white p-4",
        className,
      )}
    >
      {/* Date range filter */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-700">סינון תאריך</h3>

        <div className="space-y-1.5">
          <label className="block text-xs text-slate-500">מתאריך</label>
          <input
            type="date"
            className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm text-slate-700 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            value={startDate ? startDate.slice(0, 10) : ""}
            min={minDate?.slice(0, 10) ?? ""}
            max={endDate?.slice(0, 10) ?? maxDate?.slice(0, 10) ?? ""}
            onChange={(e) =>
              onStartDateChange(e.target.value || null)
            }
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs text-slate-500">עד תאריך</label>
          <input
            type="date"
            className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm text-slate-700 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            value={endDate ? endDate.slice(0, 10) : ""}
            min={startDate?.slice(0, 10) ?? minDate?.slice(0, 10) ?? ""}
            max={maxDate?.slice(0, 10) ?? ""}
            onChange={(e) =>
              onEndDateChange(e.target.value || null)
            }
          />
        </div>

        {(startDate || endDate) && (
          <button
            type="button"
            onClick={handleClearDates}
            className="text-xs text-blue-600 hover:underline"
          >
            נקה תאריכים
          </button>
        )}
      </div>

      {/* Region filter */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">סינון מחוז</h3>
          {selectedRegions.length > 0 && (
            <button
              type="button"
              onClick={handleClearRegions}
              className="text-xs text-blue-600 hover:underline"
            >
              נקה ({selectedRegions.length})
            </button>
          )}
        </div>

        <div className="max-h-48 space-y-1 overflow-y-auto rounded-md border border-slate-100 p-2">
          {regions.length > 0 ? (
            regions.map((region) => (
              <label
                key={region}
                className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-sm hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={selectedRegions.includes(region)}
                  onChange={() => handleRegionToggle(region)}
                  className="h-3.5 w-3.5 rounded border-slate-300 accent-blue-600"
                />
                <span className="text-slate-700">{region}</span>
              </label>
            ))
          ) : (
            <p className="py-1 text-xs text-slate-400">אין מחוזות זמינים</p>
          )}
        </div>

        {selectedRegions.length === 0 && (
          <p className="text-xs text-slate-400">כל המחוזות</p>
        )}
      </div>

      {/* Quick stats footer */}
      <div className="space-y-1 border-t border-slate-100 pt-3">
        <p className="text-xs text-slate-400">
          עדכון: {dateStr}
        </p>
        <p className="text-xs text-slate-400">
          רשומות: {filteredCount.toLocaleString("he-IL")} (מ-
          {totalCount.toLocaleString("he-IL")})
        </p>
      </div>
    </aside>
  );
}
