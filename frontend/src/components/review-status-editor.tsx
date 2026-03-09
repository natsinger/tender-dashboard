/**
 * ReviewStatusEditor component.
 *
 * Allows updating the review status and notes for a tender from the
 * team watchlist. Provides a tender select, a status dropdown with
 * the 5 ordered REVIEW_STAGES, a notes text input, and an update button.
 *
 * Mirrors the sidebar review status editing from pages/dashboard.py.
 */
"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSetReviewStatus } from "@/hooks";
import { REVIEW_STAGES } from "@/lib/constants";
import type { Tender, TenderReview } from "@/types/database";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ReviewStatusEditorProps {
  /** Currently authenticated user email. */
  email: string;
  /** Tenders in the team watchlist (filtered to team-watched only). */
  tenders: Tender[];
  /** Review statuses map: tender_id -> TenderReview. */
  reviewMap: Record<number, TenderReview>;
  /** Additional CSS classes. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReviewStatusEditor({
  email,
  tenders,
  reviewMap,
  className,
}: ReviewStatusEditorProps) {
  const [selectedTenderId, setSelectedTenderId] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<string>(REVIEW_STAGES[0]);
  const [notes, setNotes] = useState<string>("");
  const [confirmRegression, setConfirmRegression] = useState(false);

  const mutation = useSetReviewStatus();

  // Build label map
  const tenderLabels = useMemo(() => {
    const labels: Record<string, string> = {};
    for (const t of tenders) {
      const name = (t.tender_name ?? "").slice(0, 30);
      const city = (t.city ?? "").slice(0, 15);
      labels[String(t.tender_id)] = `${name} \u2014 ${city}`;
    }
    return labels;
  }, [tenders]);

  // When selected tender changes, load its current status + notes
  useEffect(() => {
    if (!selectedTenderId) return;
    const tid = parseInt(selectedTenderId, 10);
    const review = reviewMap[tid];
    if (review) {
      setSelectedStatus(review.status);
      setNotes(review.notes ?? "");
    } else {
      setSelectedStatus(REVIEW_STAGES[0]);
      setNotes("");
    }
  }, [selectedTenderId, reviewMap]);

  /** Execute the actual mutation (called directly or after confirmation). */
  const executeUpdate = useCallback(() => {
    if (!selectedTenderId) return;

    const tid = parseInt(selectedTenderId, 10);
    const prevStatus = reviewMap[tid]?.status ?? "\u05D7\u05D3\u05E9";

    mutation.mutate(
      {
        tenderId: tid,
        status: selectedStatus,
        updatedBy: email,
        notes: notes || undefined,
      },
      {
        onSuccess: () => {
          toast.success(`סטטוס עודכן: ${prevStatus} \u2192 ${selectedStatus}`);
          setConfirmRegression(false);
        },
        onError: (error) => {
          toast.error("שגיאה בעדכון סטטוס", {
            description: error.message,
          });
          setConfirmRegression(false);
        },
      },
    );
  }, [selectedTenderId, selectedStatus, notes, email, reviewMap, mutation]);

  /** Check for status regression before updating. */
  const handleUpdate = useCallback(() => {
    if (!selectedTenderId) return;

    const tid = parseInt(selectedTenderId, 10);
    const currentStatus = reviewMap[tid]?.status ?? REVIEW_STAGES[0];
    const currentIdx = REVIEW_STAGES.indexOf(currentStatus);
    const newIdx = REVIEW_STAGES.indexOf(selectedStatus);

    // If moving backward in the pipeline, ask for confirmation
    if (currentIdx > 0 && newIdx < currentIdx) {
      setConfirmRegression(true);
      return;
    }

    executeUpdate();
  }, [selectedTenderId, selectedStatus, reviewMap, executeUpdate]);

  if (tenders.length === 0) {
    return (
      <div dir="rtl" className={cn("text-sm text-megido-text-muted", className)}>
        {"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD \u05DE\u05D5\u05E2\u05D3\u05E4\u05D9\u05DD \u05DC\u05E2\u05D3\u05DB\u05D5\u05DF"}
      </div>
    );
  }

  return (
    <div dir="rtl" className={cn("space-y-3", className)}>
      {/* Tender select */}
      <div>
        <label className="mb-1 block text-xs font-medium text-megido-neutral-600">
          {"\u05DE\u05DB\u05E8\u05D6"}
        </label>
        <Select value={selectedTenderId} onValueChange={setSelectedTenderId}>
          <SelectTrigger className="w-full">
            <SelectValue
              placeholder={"\u05D1\u05D7\u05E8 \u05DE\u05DB\u05E8\u05D6..."}
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

      {/* Status select */}
      <div>
        <label className="mb-1 block text-xs font-medium text-megido-neutral-600">
          {"\u05E1\u05D8\u05D8\u05D5\u05E1 \u05D7\u05D3\u05E9"}
        </label>
        <Select value={selectedStatus} onValueChange={setSelectedStatus}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {REVIEW_STAGES.map((stage) => (
              <SelectItem key={stage} value={stage}>
                {stage}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Notes input */}
      <div>
        <label className="mb-1 block text-xs font-medium text-megido-neutral-600">
          {"\u05D4\u05E2\u05E8\u05D5\u05EA"}
        </label>
        <Input
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="..."
          dir="rtl"
        />
      </div>

      {/* Update button */}
      <Button
        onClick={handleUpdate}
        disabled={!selectedTenderId || mutation.isPending}
        className="w-full"
      >
        {mutation.isPending
          ? "\u05DE\u05E2\u05D3\u05DB\u05DF..."
          : "\u05E2\u05D3\u05DB\u05DF \u05E1\u05D8\u05D8\u05D5\u05E1"}
      </Button>

      {/* Regression confirmation dialog */}
      <Dialog
        open={confirmRegression}
        onOpenChange={(open) => {
          if (!open) setConfirmRegression(false);
        }}
      >
        <DialogContent dir="rtl" showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>{"שינוי סטטוס לאחור"}</DialogTitle>
            <DialogDescription>
              {"הסטטוס החדש נמוך מהסטטוס הנוכחי. האם להמשיך?"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:justify-start">
            <Button
              variant="destructive"
              onClick={executeUpdate}
              disabled={mutation.isPending}
            >
              {"עדכן בכל זאת"}
            </Button>
            <Button
              variant="outline"
              onClick={() => setConfirmRegression(false)}
            >
              {"ביטול"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
