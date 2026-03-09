/**
 * Competitive Intelligence section for the Analytics page.
 *
 * Tabbed layout with:
 *   1. Tender lifecycle analysis table
 *   2. Deadline overlap calendar view
 *   3. Region saturation index table with score badges
 *   4. Document intelligence metrics table
 */
"use client";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type {
  LifecycleRow,
  DeadlineOverlapRow,
  SaturationRow,
  DocumentIntelligenceRow,
} from "@/lib/utils/analytics-engine";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CompetitiveSectionProps {
  lifecycleData: LifecycleRow[];
  overlapData: DeadlineOverlapRow[];
  saturationData: SaturationRow[];
  docIntelData: DocumentIntelligenceRow[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const COMP_LABELS: Record<string, string> = {
  low: "נמוכה",
  medium: "בינונית",
  high: "גבוהה",
};

const COMP_BADGE: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
};

const TREND_LABELS: Record<string, string> = {
  saturating: "מתרווה",
  opening: "נפתח",
  stable: "יציב",
};

const TREND_BADGE: Record<string, string> = {
  saturating: "bg-red-100 text-red-700",
  opening: "bg-emerald-100 text-emerald-700",
  stable: "bg-megido-neutral-100 text-megido-neutral-600",
};

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("he-IL", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(d);
  } catch {
    return iso;
  }
}

/** Score badge color based on 0-100 value. */
function scoreBadgeClass(score: number): string {
  if (score >= 70) return "bg-red-500 text-white";
  if (score >= 40) return "bg-amber-500 text-white";
  return "bg-emerald-500 text-white";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CompetitiveSection({
  lifecycleData,
  overlapData,
  saturationData,
  docIntelData,
}: CompetitiveSectionProps) {
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-megido-text-heading">
        מודיעין תחרותי
      </h2>

      <Tabs defaultValue="lifecycle" dir="rtl">
        <TabsList>
          <TabsTrigger value="lifecycle">מחזור חיים</TabsTrigger>
          <TabsTrigger value="overlap">חפיפת מועדים</TabsTrigger>
          <TabsTrigger value="saturation">רוויה אזורית</TabsTrigger>
          <TabsTrigger value="docs">מודיעין מסמכים</TabsTrigger>
        </TabsList>

        {/* Tab 1: Lifecycle analysis */}
        <TabsContent value="lifecycle">
          {lifecycleData.length > 0 ? (
            <div className="space-y-2">
              <div className="overflow-x-auto rounded-lg border border-megido-border bg-megido-bg-card">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-megido-border bg-megido-neutral-50 text-end">
                      <th className="px-3 py-2 font-semibold">מחוז</th>
                      <th className="px-3 py-2 font-semibold">סוג מכרז</th>
                      <th className="px-3 py-2 text-center font-semibold">
                        ממוצע ימים
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        חציון ימים
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        מספר מכרזים
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {lifecycleData.map((row, i) => (
                      <tr
                        key={`${row.region}-${row.tenderType}-${i}`}
                        className="border-b border-megido-neutral-100 hover:bg-megido-neutral-50/50"
                      >
                        <td className="px-3 py-2">{row.region}</td>
                        <td className="px-3 py-2">{row.tenderType}</td>
                        <td className="px-3 py-2 text-center">
                          {row.avgLifecycleDays}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {row.medianLifecycleDays}
                        </td>
                        <td className="px-3 py-2 text-center">{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-megido-text-muted">
                ניתוח זמני מחזור חיים למכרזים שנסגרו -- מפרסום ועד סגירה
              </p>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין מכרזים סגורים בטווח הנבחר לניתוח מחזור חיים
            </p>
          )}
        </TabsContent>

        {/* Tab 2: Deadline overlap */}
        <TabsContent value="overlap">
          {overlapData.length > 0 ? (
            <div className="space-y-2">
              <div className="overflow-x-auto rounded-lg border border-megido-border bg-megido-bg-card">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-megido-border bg-megido-neutral-50 text-end">
                      <th className="px-3 py-2 font-semibold">תחילת שבוע</th>
                      <th className="px-3 py-2 text-center font-semibold">
                        מכרזים
                      </th>
                      <th className="px-3 py-2 font-semibold">מחוזות</th>
                      <th className="px-3 py-2 text-center font-semibold">
                        רמת תחרות
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {overlapData.map((row, i) => (
                      <tr
                        key={`${row.weekStart}-${i}`}
                        className="border-b border-megido-neutral-100 hover:bg-megido-neutral-50/50"
                      >
                        <td className="px-3 py-2">
                          {formatDate(row.weekStart)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {row.tenderCount}
                        </td>
                        <td className="max-w-[200px] truncate px-3 py-2">
                          {row.regionsInvolved}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <Badge
                            variant="secondary"
                            className={COMP_BADGE[row.competitionLevel]}
                          >
                            {COMP_LABELS[row.competitionLevel]}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-megido-text-muted">
                שבועות עם חפיפת מועדי סגירה -- רמת תחרות נמוכה (1-2), בינונית
                (3-5), גבוהה (6+)
              </p>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין נתוני מועדי סגירה לניתוח חפיפה
            </p>
          )}
        </TabsContent>

        {/* Tab 3: Region saturation */}
        <TabsContent value="saturation">
          {saturationData.length > 0 ? (
            <div className="space-y-2">
              <div className="overflow-x-auto rounded-lg border border-megido-border bg-megido-bg-card">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-megido-border bg-megido-neutral-50 text-end">
                      <th className="px-3 py-2 font-semibold">מחוז</th>
                      <th className="px-3 py-2 text-center font-semibold">
                        פעילים
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        סגורים
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        {`יח"ד`}
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        ציון רוויה
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        מגמה
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {saturationData.map((row) => (
                      <tr
                        key={row.region}
                        className="border-b border-megido-neutral-100 hover:bg-megido-neutral-50/50"
                      >
                        <td className="px-3 py-2">{row.region}</td>
                        <td className="px-3 py-2 text-center">
                          {row.activeCount}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {row.closedCount}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {row.totalUnits.toLocaleString("he-IL")}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span
                            className={cn(
                              "inline-block rounded-full px-2 py-0.5 text-xs font-semibold",
                              scoreBadgeClass(row.saturationScore),
                            )}
                          >
                            {row.saturationScore.toFixed(0)}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center">
                          <Badge
                            variant="secondary"
                            className={TREND_BADGE[row.trend]}
                          >
                            {TREND_LABELS[row.trend]}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-megido-text-muted">
                ציון רוויה 0-100 (ביחס למחוז הפעיל ביותר). 6 חודשים אחרונים.
              </p>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין מספיק נתונים לניתוח רוויה אזורית
            </p>
          )}
        </TabsContent>

        {/* Tab 4: Document intelligence */}
        <TabsContent value="docs">
          {docIntelData.length > 0 ? (
            <div className="space-y-2">
              <div className="overflow-x-auto rounded-lg border border-megido-border bg-megido-bg-card">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-megido-border bg-megido-neutral-50 text-end">
                      <th className="px-3 py-2 font-semibold">מחוז</th>
                      <th className="px-3 py-2 text-center font-semibold">
                        שיעור חוברות %
                      </th>
                      <th className="px-3 py-2 text-center font-semibold">
                        {`סה"כ מכרזים`}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {docIntelData.map((row) => (
                      <tr
                        key={row.region}
                        className="border-b border-megido-neutral-100 hover:bg-megido-neutral-50/50"
                      >
                        <td className="px-3 py-2">{row.region}</td>
                        <td className="px-3 py-2 text-center">
                          {row.brochureRatePct.toFixed(1)}%
                        </td>
                        <td className="px-3 py-2 text-center">
                          {row.totalTenders}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-megido-text-muted">
                מודיעין זמינות מסמכים וחוברות לפי מחוז
              </p>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-megido-text-muted">
              אין נתוני מסמכים זמינים
            </p>
          )}
        </TabsContent>
      </Tabs>
    </section>
  );
}
