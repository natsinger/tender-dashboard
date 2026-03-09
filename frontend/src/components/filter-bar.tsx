/**
 * FilterBar component.
 *
 * Four inline multiselect filters (city, region, purpose, status) in a
 * single row. Each filter uses a dropdown with checkboxes. Connected to
 * the Zustand useFilterStore for global filter state persistence.
 * Mirrors the 4-column filter pattern from the Streamlit explorer page.
 */
"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, X } from "lucide-react";
import { useFilterStore } from "@/stores/filter-store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FilterKey = "cities" | "regions" | "purposes" | "statuses";

interface FilterConfig {
  key: FilterKey;
  label: string;
  placeholder: string;
  options: string[];
}

interface FilterBarProps {
  /** Available city options. */
  cities: string[];
  /** Available region options. */
  regions: string[];
  /** Available purpose options. */
  purposes: string[];
  /** Available status options. */
  statuses: string[];
  /** Additional CSS classes on the outer container. */
  className?: string;
}

// ---------------------------------------------------------------------------
// MultiSelect dropdown (internal)
// ---------------------------------------------------------------------------

interface MultiSelectProps {
  label: string;
  placeholder: string;
  options: string[];
  selected: string[];
  onChange: (value: string[]) => void;
}

function MultiSelect({
  label,
  placeholder,
  options,
  selected,
  onChange,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Auto-focus search input when dropdown opens
  useEffect(() => {
    if (open && searchRef.current) {
      searchRef.current.focus();
    }
  }, [open]);

  const toggleOption = useCallback(
    (opt: string) => {
      if (selected.includes(opt)) {
        onChange(selected.filter((s) => s !== opt));
      } else {
        onChange([...selected, opt]);
      }
    },
    [selected, onChange],
  );

  const clearAll = useCallback(() => {
    onChange([]);
  }, [onChange]);

  const filteredOptions = useMemo(
    () =>
      search.trim() === ""
        ? options
        : options.filter((opt) =>
            opt.toLowerCase().includes(search.trim().toLowerCase()),
          ),
    [options, search],
  );

  const displayText =
    selected.length === 0
      ? placeholder
      : selected.length <= 2
        ? selected.join(", ")
        : `${selected.length} \u05E0\u05D1\u05D7\u05E8\u05D5`;

  return (
    <div ref={ref} className="relative flex-1" dir="rtl">
      <label className="mb-1 block text-xs font-medium text-megido-neutral-600">
        {label}
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-md border border-megido-border bg-megido-bg-card px-3 py-2 text-sm",
          "hover:border-megido-neutral-300 focus:outline-none focus:ring-2 focus:ring-megido-primary/40",
          selected.length > 0 ? "text-megido-text-heading" : "text-megido-text-muted",
        )}
      >
        <span className="truncate">{displayText}</span>
        <div className="flex shrink-0 items-center gap-1">
          {selected.length > 0 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                clearAll();
              }}
              className="rounded-full p-0.5 text-megido-text-muted hover:bg-megido-neutral-100 hover:text-megido-neutral-600"
            >
              <X className="h-3 w-3" />
            </button>
          )}
          <ChevronDown className="h-4 w-4 text-megido-text-muted" />
        </div>
      </button>

      {open && (
        <div className="absolute end-0 top-full z-50 mt-1 w-full rounded-md border border-megido-border bg-megido-bg-card shadow-lg">
          {/* Search input */}
          <div className="border-b border-megido-neutral-100 p-2">
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`\u05D7\u05E4\u05E9...`}
              className="w-full rounded border border-megido-border bg-megido-neutral-50 px-2 py-1.5 text-sm outline-none placeholder:text-megido-text-muted focus:border-megido-primary focus:ring-1 focus:ring-megido-primary/40"
            />
          </div>

          <div className="max-h-48 overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <p className="p-3 text-center text-sm text-megido-text-muted">
                {"\u05D0\u05D9\u05DF \u05D0\u05E4\u05E9\u05E8\u05D5\u05D9\u05D5\u05EA"}
              </p>
            ) : (
              filteredOptions.map((opt) => (
                <label
                  key={opt}
                  className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm hover:bg-megido-neutral-50"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(opt)}
                    onChange={() => toggleOption(opt)}
                    className="rounded border-megido-neutral-300 text-megido-primary focus:ring-blue-500"
                  />
                  <span className="truncate">{opt}</span>
                </label>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function FilterBar({
  cities,
  regions,
  purposes,
  statuses,
  className,
}: FilterBarProps) {
  const store = useFilterStore();

  const filters: FilterConfig[] = [
    {
      key: "cities",
      label: "\u05E2\u05D9\u05E8",
      placeholder: "\u05D4\u05DB\u05DC",
      options: cities,
    },
    {
      key: "regions",
      label: "\u05DE\u05D7\u05D5\u05D6",
      placeholder: "\u05D4\u05DB\u05DC",
      options: regions,
    },
    {
      key: "purposes",
      label: "\u05D9\u05D9\u05E2\u05D5\u05D3",
      placeholder: "\u05D4\u05DB\u05DC",
      options: purposes,
    },
    {
      key: "statuses",
      label: "\u05E1\u05D8\u05D8\u05D5\u05E1",
      placeholder: "\u05D4\u05DB\u05DC",
      options: statuses,
    },
  ];

  return (
    <div
      dir="rtl"
      className={cn("flex items-end gap-3", className)}
    >
      {filters.map((f) => (
        <MultiSelect
          key={f.key}
          label={f.label}
          placeholder={f.placeholder}
          options={f.options}
          selected={store[f.key]}
          onChange={(value) => store.setFilter(f.key, value)}
        />
      ))}
    </div>
  );
}
