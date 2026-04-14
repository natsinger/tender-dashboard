/**
 * ExpiredTendersTable component.
 *
 * Displays watchlisted tenders whose deadline has passed, with inline-editable
 * outcome fields: did we bid, our offer, winning bid (auto from API), position,
 * and notes. Saves changes on blur via useSetTenderOutcome.
 */
"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { useTenderOutcomes, useSetTenderOutcome } from "@/hooks/use-outcomes";
import { useTenderPrices } from "@/hooks/use-prices";
import type {
  Tender,
  TenderOutcome,
  TenderPrice,
  TenderReview,
  WatchlistItemWithTender,
} from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExpiredTendersTableProps {
  /** Watchlist items with past deadlines. */
  items: WatchlistItemWithTender[];
  /** Review status map (tender_id -> TenderReview). */
  reviewMap: Record<number, TenderReview> | undefined;
  /** Current user email for tracking who updated. */
  userEmail: string;
  /** Drag start handler — makes rows draggable back to active. */
  onDragStart?: (e: React.DragEvent, tenderId: number) => void;
  /** Restore handler — moves tender back to active list. */
  onRestore?: (tenderId: number) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDeadline(deadline: string | null): string {
  if (!deadline) return "\u2014";
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return "\u2014";
  return d.toLocaleDateString("he-IL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null || value === 0) return "\u2014";
  return `\u20AA${value.toLocaleString("he-IL", { maximumFractionDigits: 0 })}`;
}

function getReviewBadgeVariant(
  status: string,
): "default" | "secondary" | "outline" | "destructive" {
  switch (status) {
    case "\u05D0\u05D5\u05E9\u05E8 \u05D1\u05E4\u05D5\u05E8\u05D5\u05DD":
      return "default";
    case "\u05D4\u05D5\u05E6\u05D2 \u05D1\u05E4\u05D5\u05E8\u05D5\u05DD":
      return "secondary";
    case "\u05D1\u05D3\u05D9\u05E7\u05D4 \u05DE\u05E2\u05DE\u05D9\u05E7\u05D4":
      return "secondary";
    case "\u05E1\u05E7\u05D9\u05E8\u05D4 \u05E8\u05D0\u05E9\u05D5\u05E0\u05D9\u05EA":
      return "outline";
    default:
      return "outline";
  }
}

/** Get the primary winning bid from tender_prices (first lot with a bid). */
function getApiWinningBid(
  prices: TenderPrice[] | undefined,
): number | null {
  if (!prices || prices.length === 0) return null;
  for (const p of prices) {
    if (p.winning_bid != null && p.winning_bid > 0) return p.winning_bid;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Inline-editable cell components
// ---------------------------------------------------------------------------

function CheckboxCell({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
}) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      className="mx-auto block h-4 w-4 rounded border-megido-border text-megido-primary accent-megido-primary"
    />
  );
}

function NumberCell({
  value,
  onChange,
  isCurrency,
}: {
  value: number | null | undefined;
  onChange: (val: number | null) => void;
  isCurrency?: boolean;
}) {
  const ref = useRef<HTMLInputElement>(null);

  const formatDisplay = useCallback(
    (num: number | null | undefined): string => {
      if (num == null) return "";
      if (isCurrency) return `\u20AA${num.toLocaleString("he-IL")}`;
      return num.toLocaleString("he-IL");
    },
    [isCurrency],
  );

  const handleBlur = useCallback(() => {
    const raw = ref.current?.value.replace(/[^\d.-]/g, "") ?? "";
    const num = raw ? parseFloat(raw) : null;
    onChange(num);
    if (ref.current) {
      ref.current.value = formatDisplay(num);
    }
  }, [onChange, formatDisplay]);

  const handleFocus = useCallback(() => {
    if (ref.current) {
      const raw = ref.current.value.replace(/[^\d.-]/g, "");
      ref.current.value = raw;
      ref.current.select();
    }
  }, []);

  return (
    <input
      ref={ref}
      type="text"
      defaultValue={formatDisplay(value)}
      onBlur={handleBlur}
      onFocus={handleFocus}
      className="w-full rounded border border-transparent bg-transparent px-1 py-0.5 text-sm transition-colors focus:border-megido-primary focus:outline-none"
    />
  );
}

function TextCell({
  value,
  onChange,
}: {
  value: string | null | undefined;
  onChange: (val: string) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);

  const handleBlur = useCallback(() => {
    onChange(ref.current?.value ?? "");
  }, [onChange]);

  return (
    <input
      ref={ref}
      type="text"
      defaultValue={value ?? ""}
      onBlur={handleBlur}
      className="w-full rounded border border-transparent bg-transparent px-1 py-0.5 text-sm transition-colors focus:border-megido-primary focus:outline-none"
    />
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ExpiredTendersTable({
  items,
  reviewMap,
  userEmail,
  onDragStart,
  onRestore,
}: ExpiredTendersTableProps) {
  const tenderIds = useMemo(() => items.map((i) => i.tender_id), [items]);
  const { data: outcomeMap } = useTenderOutcomes(tenderIds);
  const { data: allPrices } = useTenderPrices();
  const setOutcome = useSetTenderOutcome();
  const [savedTenderId, setSavedTenderId] = useState<number | null>(null);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Group prices by tender_id
  const pricesByTender = useMemo(() => {
    if (!allPrices) return {};
    const map: Record<number, TenderPrice[]> = {};
    for (const p of allPrices) {
      if (!map[p.tender_id]) map[p.tender_id] = [];
      map[p.tender_id].push(p);
    }
    return map;
  }, [allPrices]);

  const handleUpdate = useCallback(
    (tenderId: number, fields: Partial<Omit<TenderOutcome, "id" | "tender_id" | "updated_by" | "updated_at">>) => {
      setOutcome.mutate(
        {
          tenderId,
          updatedBy: userEmail,
          didBid: fields.did_bid,
          ourOffer: fields.our_offer,
          ourPosition: fields.our_position,
          outcomeNotes: fields.outcome_notes,
        },
        {
          onSuccess: () => {
            setSavedTenderId(tenderId);
            if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
            savedTimerRef.current = setTimeout(() => setSavedTenderId(null), 2000);
          },
        },
      );
    },
    [setOutcome, userEmail],
  );

  if (items.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-base font-semibold text-megido-text-heading">
        {"\u05D4\u05D5\u05E1\u05E8\u05D5 \u05DE\u05D4\u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD"} ({items.length})
      </h3>

      <div className="overflow-x-auto rounded-md border">
        <table className="table-auto w-full min-w-[900px] text-sm" dir="rtl">
          <thead className="[&_tr]:border-b">
            <tr>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05E9\u05DD \u05DE\u05DB\u05E8\u05D6"}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05E2\u05D9\u05E8"}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{'\u05D9\u05D7"\u05D3'}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05E1\u05D5\u05D2"}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4"}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05E1\u05D8\u05D8\u05D5\u05E1 \u05E1\u05E7\u05D9\u05E8\u05D4"}</th>
              <th className="text-foreground h-10 px-2 text-center align-middle font-medium whitespace-nowrap">{"\u05D4\u05D2\u05E9\u05E0\u05D5?"}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05D4\u05D4\u05E6\u05E2\u05D4 \u05E9\u05DC\u05E0\u05D5"}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05D4\u05E6\u05E2\u05D4 \u05D6\u05D5\u05DB\u05D4"}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05DE\u05D9\u05E7\u05D5\u05DD"}</th>
              <th className="text-foreground h-10 px-2 text-right align-middle font-medium whitespace-nowrap">{"\u05D4\u05E2\u05E8\u05D5\u05EA"}</th>
              <th className="h-10 w-12 px-1" />
              <th className="h-10 w-10 px-1" />
            </tr>
          </thead>
          <tbody className="[&_tr:last-child]:border-0">
            {items.map((item) => {
              const tender = item.tender;
              if (!tender) return null;

              const review = reviewMap?.[item.tender_id];
              const outcome = outcomeMap?.[item.tender_id];
              const statusText =
                review?.status ?? "\u05DC\u05D0 \u05E0\u05E1\u05E7\u05E8";
              const apiWinBid = getApiWinningBid(pricesByTender[item.tender_id]);

              return (
                <tr
                  key={item.tender_id}
                  draggable={!!onDragStart}
                  onDragStart={onDragStart ? (e) => onDragStart(e, item.tender_id) : undefined}
                  className="border-b transition-colors hover:bg-muted/50"
                >
                  {/* Tender name */}
                  <td className="p-2 align-middle whitespace-nowrap text-sm font-medium max-w-[180px] truncate">
                    {tender.tender_name ?? tender.tender_id}
                  </td>

                  {/* City */}
                  <td className="p-2 align-middle whitespace-nowrap text-sm">
                    {tender.city ?? "\u2014"}
                  </td>

                  {/* Units */}
                  <td className="p-2 align-middle whitespace-nowrap text-sm">
                    {tender.units ?? "\u2014"}
                  </td>

                  {/* Type */}
                  <td className="p-2 align-middle whitespace-nowrap text-sm">
                    {tender.purpose ?? "\u2014"}
                  </td>

                  {/* Deadline */}
                  <td className="p-2 align-middle whitespace-nowrap text-sm">
                    {formatDeadline(tender.deadline)}
                  </td>

                  {/* Review status */}
                  <td className="p-2 align-middle whitespace-nowrap">
                    <Badge
                      variant={getReviewBadgeVariant(statusText)}
                      className="text-[0.64rem]"
                    >
                      {statusText}
                    </Badge>
                  </td>

                  {/* Did we bid? */}
                  <td className="p-2 align-middle whitespace-nowrap">
                    <CheckboxCell
                      checked={outcome?.did_bid ?? false}
                      onChange={(val) =>
                        handleUpdate(item.tender_id, { did_bid: val })
                      }
                    />
                  </td>

                  {/* Our offer */}
                  <td className="p-2 align-middle whitespace-nowrap">
                    <NumberCell
                      value={outcome?.our_offer}
                      isCurrency
                      onChange={(val) =>
                        handleUpdate(item.tender_id, { our_offer: val })
                      }
                    />
                  </td>

                  {/* Winning bid (auto from API or manual) */}
                  <td className="p-2 align-middle whitespace-nowrap text-sm">
                    {formatCurrency(apiWinBid)}
                  </td>

                  {/* Position */}
                  <td className="p-2 align-middle whitespace-nowrap">
                    <NumberCell
                      value={outcome?.our_position}
                      onChange={(val) =>
                        handleUpdate(item.tender_id, {
                          our_position: val != null ? Math.round(val) : null,
                        })
                      }
                    />
                  </td>

                  {/* Notes */}
                  <td className="p-2 align-middle whitespace-nowrap">
                    <TextCell
                      value={outcome?.outcome_notes}
                      onChange={(val) =>
                        handleUpdate(item.tender_id, { outcome_notes: val })
                      }
                    />
                  </td>

                  {/* Save indicator */}
                  <td className="p-1 align-middle">
                    {savedTenderId === item.tender_id && (
                      <span className="animate-in fade-in text-[0.6rem] font-medium text-emerald-600">
                        {"\u2713 \u05E0\u05E9\u05DE\u05E8"}
                      </span>
                    )}
                  </td>

                  {/* Restore button */}
                  <td className="px-1 py-2">
                    {onRestore && (
                      <button
                        type="button"
                        onClick={() => onRestore(item.tender_id)}
                        title={"\u05D4\u05D7\u05D6\u05E8 \u05DC\u05E4\u05E2\u05D9\u05DC\u05D9\u05DD"}
                        className="rounded p-0.5 text-megido-text-muted transition-colors hover:bg-megido-neutral-100 hover:text-megido-primary"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                          <path d="M3 3v5h5" />
                        </svg>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
