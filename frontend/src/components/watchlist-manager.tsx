/**
 * WatchlistManager component.
 *
 * Manages a user's personal or team watchlist. Provides a select dropdown
 * to pick a tender (name + city format), an "add to watchlist" button,
 * and a list of current watchlist items with delete buttons.
 *
 * Mirrors the sidebar watchlist management from pages/dashboard.py.
 */
"use client";

import { useState, useMemo, useCallback } from "react";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  const [selectedTenderId, setSelectedTenderId] = useState<string>("");

  const addMutation = useAddToWatchlist();
  const removeMutation = useRemoveFromWatchlist();

  // Build label map for the select dropdown
  const tenderLabels = useMemo(() => {
    const labels: Record<string, string> = {};
    for (const t of tenders) {
      const name = (t.tender_name ?? "").slice(0, 40);
      const city = (t.city ?? "").slice(0, 15);
      labels[String(t.tender_id)] = city
        ? `${name} \u2014 ${city}`
        : name;
    }
    return labels;
  }, [tenders]);

  const handleAdd = useCallback(() => {
    if (!selectedTenderId) return;
    addMutation.mutate(
      { email, tenderId: parseInt(selectedTenderId, 10) },
      {
        onSuccess: () => setSelectedTenderId(""),
      },
    );
  }, [selectedTenderId, email, addMutation]);

  const handleRemove = useCallback(
    (tenderId: number) => {
      removeMutation.mutate({ email, tenderId });
    },
    [email, removeMutation],
  );

  const buttonLabel = isTeam
    ? "\u05D4\u05D5\u05E1\u05E3 \u05DC\u05DE\u05E2\u05E7\u05D1 \u05E6\u05D5\u05D5\u05EA"
    : "\u05D4\u05D5\u05E1\u05E3 \u05DC\u05DE\u05E2\u05E7\u05D1";

  return (
    <div dir="rtl" className={cn("space-y-3", className)}>
      {/* Add tender select + button */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Select
            value={selectedTenderId}
            onValueChange={setSelectedTenderId}
          >
            <SelectTrigger className="w-full">
              <SelectValue
                placeholder={
                  "\u05D4\u05E7\u05DC\u05D3 \u05E9\u05DD \u05DE\u05DB\u05E8\u05D6 \u05D0\u05D5 \u05E2\u05D9\u05E8..."
                }
              />
            </SelectTrigger>
            <SelectContent>
              {tenders.map((t) => (
                <SelectItem key={t.tender_id} value={String(t.tender_id)}>
                  {tenderLabels[String(t.tender_id)] ?? String(t.tender_id)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          onClick={handleAdd}
          disabled={!selectedTenderId || addMutation.isPending}
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
            const displayName = (tender?.tender_name ?? String(item.tender_id)).slice(0, 25);
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
