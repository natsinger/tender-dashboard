/**
 * WatchlistManager component.
 *
 * Manages a user's personal or team watchlist. Provides a searchable text
 * input to filter tenders by name, city, or ID — then an "add" button.
 * Below, a list of current watchlist items with delete buttons.
 */
"use client";

import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Trash2, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAddToWatchlist, useRemoveFromWatchlist } from "@/hooks";
import type { Tender, WatchlistItemWithTender } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WatchlistManagerProps {
  /** User email (or team email). */
  email: string;
  /** Whether this is the shared team watchlist. */
  isTeam?: boolean;
  /** All tenders available for selection. */
  tenders: Tender[];
  /** Current watchlist items (pre-fetched). */
  watchlistItems: WatchlistItemWithTender[];
  /** Loading state. */
  isLoading?: boolean;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a searchable label for a tender. */
function tenderLabel(t: Tender): string {
  const name = (t.tender_name ?? "").slice(0, 40);
  const city = (t.city ?? "").slice(0, 15);
  return city ? `${name} \u2014 ${city}` : name;
}

/** Max results shown in dropdown. */
const MAX_RESULTS = 30;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function WatchlistManager({
  email,
  isTeam = false,
  tenders,
  watchlistItems,
  isLoading = false,
  className,
}: WatchlistManagerProps) {
  const [searchText, setSearchText] = useState("");
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const addMutation = useAddToWatchlist();
  const removeMutation = useRemoveFromWatchlist();

  // IDs already on the watchlist (to exclude from search results)
  const watchlistIds = useMemo(
    () => new Set(watchlistItems.map((item) => item.tender_id)),
    [watchlistItems],
  );

  // Filter tenders by search text (name, city, or tender_id)
  const filteredTenders = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) return [];

    return tenders
      .filter((t) => {
        // Exclude already-watchlisted
        if (watchlistIds.has(t.tender_id)) return false;

        const name = (t.tender_name ?? "").toLowerCase();
        const city = (t.city ?? "").toLowerCase();
        const id = String(t.tender_id);

        return name.includes(q) || city.includes(q) || id.includes(q);
      })
      .slice(0, MAX_RESULTS);
  }, [searchText, tenders, watchlistIds]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectTender = useCallback((tender: Tender) => {
    setSelectedTender(tender);
    setSearchText(tenderLabel(tender));
    setDropdownOpen(false);
  }, []);

  const handleAdd = useCallback(() => {
    if (!selectedTender) return;
    addMutation.mutate(
      { email, tenderId: selectedTender.tender_id },
      {
        onSuccess: () => {
          setSelectedTender(null);
          setSearchText("");
        },
      },
    );
  }, [selectedTender, email, addMutation]);

  const handleRemove = useCallback(
    (tenderId: number) => {
      removeMutation.mutate({ email, tenderId });
    },
    [email, removeMutation],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchText(e.target.value);
      setSelectedTender(null);
      setDropdownOpen(true);
    },
    [],
  );

  const handleClear = useCallback(() => {
    setSearchText("");
    setSelectedTender(null);
    setDropdownOpen(false);
    inputRef.current?.focus();
  }, []);

  const buttonLabel = isTeam
    ? "\u05D4\u05D5\u05E1\u05E3 \u05DC\u05DE\u05E2\u05E7\u05D1 \u05E6\u05D5\u05D5\u05EA"
    : "\u05D4\u05D5\u05E1\u05E3 \u05DC\u05DE\u05E2\u05E7\u05D1";

  return (
    <div dir="rtl" className={cn("space-y-3", className)}>
      {/* Searchable tender selector + add button */}
      <div className="flex items-end gap-2">
        <div className="relative flex-1" ref={containerRef}>
          {/* Search input */}
          <div className="relative">
            <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              ref={inputRef}
              type="text"
              value={searchText}
              onChange={handleInputChange}
              onFocus={() => {
                if (searchText.trim()) setDropdownOpen(true);
              }}
              placeholder="הקלד שם של עיר או מספר מכרז"
              autoComplete="off"
              className="h-9 w-full rounded-md border border-megido-border bg-white px-9 text-sm text-slate-800 placeholder:text-slate-400 focus:border-megido-primary focus:outline-none focus:ring-1 focus:ring-megido-primary"
            />
            {searchText && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Dropdown results */}
          {dropdownOpen && searchText.trim() && (
            <div className="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-md border border-megido-border bg-white shadow-lg">
              {filteredTenders.length === 0 ? (
                <p className="px-3 py-2 text-sm text-slate-400">
                  {"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D5 \u05EA\u05D5\u05E6\u05D0\u05D5\u05EA"}
                </p>
              ) : (
                <ul>
                  {filteredTenders.map((t) => (
                    <li key={t.tender_id}>
                      <button
                        type="button"
                        onClick={() => handleSelectTender(t)}
                        className="flex w-full items-center gap-2 px-3 py-2 text-right text-sm transition-colors hover:bg-slate-50"
                      >
                        <div className="min-w-0 flex-1">
                          <span className="block truncate font-medium text-slate-800">
                            {(t.tender_name ?? "").slice(0, 40)}
                          </span>
                          <span className="flex items-center gap-2 text-xs text-slate-500">
                            {t.city && (
                              <span className="text-blue-500">{t.city}</span>
                            )}
                            <span className="text-slate-400">
                              #{t.tender_id}
                            </span>
                            {t.units != null && t.units > 0 && (
                              <span>
                                {t.units} {'\u05D9\u05D7"\u05D3'}
                              </span>
                            )}
                          </span>
                        </div>
                      </button>
                    </li>
                  ))}
                  {filteredTenders.length === MAX_RESULTS && (
                    <p className="px-3 py-1.5 text-xs text-slate-400">
                      {"\u05DE\u05E6\u05D9\u05D2 30 \u05EA\u05D5\u05E6\u05D0\u05D5\u05EA \u05E8\u05D0\u05E9\u05D5\u05E0\u05D5\u05EA, \u05D4\u05E7\u05DC\u05D3 \u05E2\u05D5\u05D3 \u05DC\u05E6\u05DE\u05E6\u05DD..."}
                    </p>
                  )}
                </ul>
              )}
            </div>
          )}
        </div>

        <Button
          onClick={handleAdd}
          disabled={!selectedTender || addMutation.isPending}
          className="shrink-0"
        >
          {addMutation.isPending
            ? "\u05DE\u05D5\u05E1\u05D9\u05E3..."
            : buttonLabel}
        </Button>
      </div>

      {/* Current watchlist items */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-10 animate-pulse rounded-md bg-slate-100"
            />
          ))}
        </div>
      ) : watchlistItems.length === 0 ? (
        <p className="text-sm text-slate-400">
          {isTeam
            ? "\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD"
            : "\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05D1\u05DE\u05E2\u05E7\u05D1 \u05D0\u05D9\u05E9\u05D9"}
        </p>
      ) : (
        <ul className="space-y-1">
          {watchlistItems.map((item) => {
            const tender = item.tender;
            const displayName = (
              tender?.tender_name ?? String(item.tender_id)
            ).slice(0, 25);
            const displayCity = (tender?.city ?? "").slice(0, 12);
            const units = tender?.units;
            const hasUnits = units != null && units > 0;

            return (
              <li
                key={item.tender_id}
                className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-slate-800">
                    {displayName}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-blue-500">{displayCity}</span>
                    {hasUnits && (
                      <Badge variant="secondary" className="text-[10px]">
                        {units} {'\u05D9\u05D7"\u05D3'}
                      </Badge>
                    )}
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => handleRemove(item.tender_id)}
                  disabled={removeMutation.isPending}
                  className="shrink-0 text-slate-400 hover:text-red-500"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
