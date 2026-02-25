/**
 * Zustand store for dashboard filter state.
 *
 * Manages the global filter selections used across dashboard pages
 * (cities, regions, purposes, statuses, date range). Persisted to
 * sessionStorage so filters survive page navigations but reset on
 * new browser sessions.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DateRange {
  start: Date | null;
  end: Date | null;
}

type FilterKey = "cities" | "regions" | "purposes" | "statuses";

interface FilterState {
  cities: string[];
  regions: string[];
  purposes: string[];
  statuses: string[];
  dateRange: DateRange;
  setFilter: (key: FilterKey, value: string[]) => void;
  setDateRange: (range: DateRange) => void;
  clearFilters: () => void;
}

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

const initialState: Pick<
  FilterState,
  "cities" | "regions" | "purposes" | "statuses" | "dateRange"
> = {
  cities: [],
  regions: [],
  purposes: [],
  statuses: [],
  dateRange: { start: null, end: null },
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useFilterStore = create<FilterState>()(
  persist(
    (set) => ({
      ...initialState,

      setFilter: (key: FilterKey, value: string[]) => {
        set({ [key]: value });
      },

      setDateRange: (range: DateRange) => {
        set({ dateRange: range });
      },

      clearFilters: () => {
        set(initialState);
      },
    }),
    {
      name: "filter-store",
      storage: createJSONStorage(() => {
        // Guard against SSR where sessionStorage is not available
        if (typeof window === "undefined") {
          return {
            getItem: () => null,
            setItem: () => {},
            removeItem: () => {},
          };
        }
        return sessionStorage;
      }),
      // Custom serialization for Date objects in dateRange
      partialize: (state) => ({
        cities: state.cities,
        regions: state.regions,
        purposes: state.purposes,
        statuses: state.statuses,
        dateRange: {
          start: state.dateRange.start?.toISOString() ?? null,
          end: state.dateRange.end?.toISOString() ?? null,
        },
      }),
      merge: (persisted, current) => {
        const p = persisted as Record<string, unknown> | null;
        if (!p) return current;

        const dateRange = p.dateRange as {
          start: string | null;
          end: string | null;
        } | null;

        return {
          ...current,
          ...(p as Partial<FilterState>),
          dateRange: {
            start: dateRange?.start ? new Date(dateRange.start) : null,
            end: dateRange?.end ? new Date(dateRange.end) : null,
          },
        };
      },
    },
  ),
);
