/**
 * TenderDetailModal component.
 *
 * Shows full tender details in a shadcn Dialog. Displays tender name,
 * ID, city, region, type, purpose, units, status, deadline with days
 * remaining, booklet status, location (shchuna), gush/helka, building
 * rights section, and lots data section. All labels in Hebrew.
 *
 * Mirrors the _show_tender_detail dialog from pages/management.py and
 * the detail viewer from pages/explorer.py.
 */
"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { DeadlineBadge } from "@/components/deadline-badge";
import type { Tender, TenderLot, BuildingRight } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TenderDetailModalProps {
  /** Whether the modal is open. */
  open: boolean;
  /** Callback to close the modal. */
  onOpenChange: (open: boolean) => void;
  /** The tender to display. Null = no content. */
  tender: Tender | null;
  /** Optional lot data for the tender. */
  lots?: TenderLot[];
  /** Optional building rights data. */
  buildingRights?: BuildingRight[];
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function computeDaysRemaining(deadline: string | null): number | null {
  if (!deadline) return null;
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return null;
  const now = new Date();
  return Math.floor((d.getTime() - now.getTime()) / 86_400_000);
}

function formatDate(value: string | null): string {
  if (!value) return "\u2014";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "\u2014";
  return d.toLocaleDateString("he-IL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Detail field row
// ---------------------------------------------------------------------------

function DetailField({
  label,
  value,
  children,
}: {
  label: string;
  value?: string | number | null;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2 py-1">
      <span className="shrink-0 text-sm font-semibold text-slate-700">
        {label}:
      </span>
      {children ?? (
        <span className="text-sm text-slate-600">
          {value != null ? String(value) : "\u2014"}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TenderDetailModal({
  open,
  onOpenChange,
  tender,
  lots,
  buildingRights,
  className,
}: TenderDetailModalProps) {
  const daysRemaining = useMemo(
    () => (tender ? computeDaysRemaining(tender.deadline) : null),
    [tender],
  );

  if (!tender) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn("max-w-2xl", className)}
        dir="rtl"
      >
        <DialogHeader>
          <DialogTitle>
            {"\u05DE\u05DB\u05E8\u05D6"} {tender.tender_name ?? tender.tender_id}
          </DialogTitle>
          <DialogDescription>
            {"\u05DE\u05E1' \u05DE\u05DB\u05E8\u05D6"}: {tender.tender_id}
          </DialogDescription>
        </DialogHeader>

        {/* Main detail grid */}
        <div className="grid grid-cols-2 gap-x-8 gap-y-0.5">
          <DetailField label={"\u05E2\u05D9\u05E8"} value={tender.city} />
          <DetailField label={"\u05DE\u05D7\u05D5\u05D6"} value={tender.region} />
          <DetailField label={"\u05E1\u05D5\u05D2"} value={tender.tender_type} />
          <DetailField label={"\u05D9\u05D9\u05E2\u05D5\u05D3"} value={tender.purpose} />
          <DetailField label={'\u05D9\u05D7"\u05D3'} value={tender.units} />
          <DetailField label={"\u05E1\u05D8\u05D8\u05D5\u05E1"} value={tender.status} />

          {/* Deadline with badge */}
          <DetailField label={"\u05DE\u05D5\u05E2\u05D3 \u05E1\u05D2\u05D9\u05E8\u05D4"}>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600">
                {formatDate(tender.deadline)}
              </span>
              <DeadlineBadge daysRemaining={daysRemaining} />
            </div>
          </DetailField>

          {/* Booklet status */}
          <DetailField label={"\u05D7\u05D5\u05D1\u05E8\u05EA"}>
            {tender.published_booklet ? (
              <Badge
                variant="secondary"
                className="bg-emerald-50 text-emerald-700 border-emerald-200"
              >
                {"\u05D9\u05E9 \u05D7\u05D5\u05D1\u05E8\u05EA"}
              </Badge>
            ) : (
              <Badge variant="outline">{"\u05D0\u05D9\u05DF \u05D7\u05D5\u05D1\u05E8\u05EA"}</Badge>
            )}
          </DetailField>
        </div>

        {/* Location (shchuna) */}
        {tender.location && (
          <DetailField label={"\u05E9\u05DB\u05D5\u05E0\u05D4"} value={tender.location} />
        )}

        {/* Gush / Helka */}
        {tender.gush && (
          <DetailField
            label={"\u05D2\u05D5\u05E9/\u05D7\u05DC\u05E7\u05D4"}
            value={`${tender.gush} / ${tender.helka ?? "\u2014"}`}
          />
        )}

        {/* Building rights section */}
        {buildingRights && buildingRights.length > 0 && (
          <div className="mt-4 border-t pt-3">
            <h4 className="mb-2 text-sm font-semibold text-slate-800">
              {"\u05D6\u05DB\u05D5\u05D9\u05D5\u05EA \u05D1\u05E0\u05D9\u05D9\u05D4"}
            </h4>
            <div className="max-h-48 overflow-y-auto rounded-md border">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-slate-50">
                    <th className="px-2 py-1 text-right">{"\u05D9\u05E2\u05D5\u05D3"}</th>
                    <th className="px-2 py-1 text-right">{"\u05E9\u05D9\u05DE\u05D5\u05E9"}</th>
                    <th className="px-2 py-1 text-right">{'\u05E9\u05D8\u05D7 \u05DE\u05D2\u05E8\u05E9 (\u05DE"\u05E8)'}</th>
                    <th className="px-2 py-1 text-right">{'\u05D9\u05D7"\u05D3'}</th>
                    <th className="px-2 py-1 text-right">{"\u05E7\u05D5\u05DE\u05D5\u05EA"}</th>
                  </tr>
                </thead>
                <tbody>
                  {buildingRights.map((r, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="px-2 py-1">{r.designation ?? "\u2014"}</td>
                      <td className="px-2 py-1">{r.use_type ?? "\u2014"}</td>
                      <td className="px-2 py-1">
                        {r.plot_size_absolute?.toLocaleString("he-IL") ?? "\u2014"}
                      </td>
                      <td className="px-2 py-1">{r.housing_units ?? "\u2014"}</td>
                      <td className="px-2 py-1">{r.floors_above ?? "\u2014"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Lots data section */}
        {lots && lots.length > 0 && (
          <div className="mt-4 border-t pt-3">
            <h4 className="mb-2 text-sm font-semibold text-slate-800">
              {"\u05E0\u05EA\u05D5\u05E0\u05D9 \u05DE\u05EA\u05D7\u05DE\u05D9\u05DD"} ({lots.length})
            </h4>
            <div className="max-h-48 overflow-y-auto rounded-md border">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-slate-50">
                    <th className="px-2 py-1 text-right">{"\u05DE\u05EA\u05D7\u05DD"}</th>
                    <th className="px-2 py-1 text-right">{"\u05D2\u05D5\u05E9"}</th>
                    <th className="px-2 py-1 text-right">{"\u05D7\u05DC\u05E7\u05D4"}</th>
                    <th className="px-2 py-1 text-right">{'\u05E1\u05D4"\u05DB \u05D9\u05D7"\u05D3'}</th>
                    <th className="px-2 py-1 text-right">{"\u05E9\u05D5\u05E7 \u05D7\u05D5\u05E4\u05E9\u05D9"}</th>
                    <th className="px-2 py-1 text-right">{"\u05DE\u05D7\u05D9\u05E8 \u05DE\u05D8\u05E8\u05D4"}</th>
                  </tr>
                </thead>
                <tbody>
                  {lots.map((lot, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="px-2 py-1">{lot.lot_number ?? "\u2014"}</td>
                      <td className="px-2 py-1">{lot.gush ?? "\u2014"}</td>
                      <td className="px-2 py-1">{lot.helka ?? "\u2014"}</td>
                      <td className="px-2 py-1">{lot.total_units ?? "\u2014"}</td>
                      <td className="px-2 py-1">{lot.units_free_market ?? "\u2014"}</td>
                      <td className="px-2 py-1">{lot.units_target_price ?? "\u2014"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
