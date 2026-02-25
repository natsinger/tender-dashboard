/**
 * Application constants ported from the Python config.py and data_client.py.
 *
 * Keeps all magic numbers, status lists, and lookup maps in one place
 * so components and hooks can import them without duplicating values.
 */

// ---------------------------------------------------------------------------
// Tender type codes (GeneralTablesApi Table 215)
// ---------------------------------------------------------------------------

/** Tender type codes shown in the dashboard. */
export const RELEVANT_TENDER_TYPES: ReadonlySet<number> = new Set([1, 5, 6, 8, 9]);

/** Human-readable tender type names (Hebrew). */
export const TENDER_TYPE_MAP: Readonly<Record<number, string>> = {
  1: "מכרז פומבי רגיל",
  2: "הרשמה והגרלה",
  3: "מכרז למגרש בלתי מסוים",
  4: "קדימות על פי עדיפות",
  5: "מחיר מטרה",
  6: "דיור להשכרה",
  7: "מחיר למשתכן",
  8: "דיור במחיר מופחת",
  9: "מכרז ייזום",
  10: "מכרזי עמידר",
  11: "מכרזי החברה לפיתוח עכו",
};

// ---------------------------------------------------------------------------
// Purpose codes (GeneralTablesApi Table -1)
// ---------------------------------------------------------------------------

/** Land-use purpose labels (Hebrew). */
export const PURPOSE_MAP: Readonly<Record<number, string>> = {
  1: "בנייה נמוכה/צמודת קרקע",
  2: "בנייה רוויה",
  3: "מסחר ו/או משרדים",
  4: "תעשיה",
  5: "מוסדות ו/או בניינים ציבוריים",
  6: "חניונים",
  7: "תחנות דלק",
  8: "מלונאות",
  9: "ספורט/נופש/תיירות/מלונאות",
  10: "כרייה וחציבה",
  11: "חקלאות",
  12: "מגורים/מסחר/מלונאות/נופש",
  13: "דיור מוגן (בית אבות)",
  14: "נכסי הרשות - מכירה - מגורים",
  15: "נכסי הרשות - מכירה - אחר",
  16: "עודפים",
  17: "נופש וחקלאות",
  18: "הטמנת פסולת",
  20: "דיור להשכרה",
  21: "נכסי הרשות - השכרה - מגורים",
  22: "נכסי הרשות - השכרה - אחר",
  23: "אנרגיה מתחדשת",
  24: "תחנת כוח",
  25: "תכנון וביצוע לכריה וחציבה",
  26: "תעסוקה",
  99: "אחר",
};

// ---------------------------------------------------------------------------
// Status codes
// ---------------------------------------------------------------------------

/** API status code labels. */
export const STATUS_MAP: Readonly<Record<number, string>> = {
  1: "טיוטה",
  2: "נדון בוועדת מכרזים",
  3: "פעיל",
  4: "מושהה",
  5: "נסגר",
  7: "בוטל",
};

/** Statuses excluded from the default "active" tender view. */
export const NON_ACTIVE_STATUSES: readonly string[] = [
  "נסגר",
  "בוטל",
  "לא אקטואלי",
  "תהליך מסתיים",
  "עוכב",
  "מכרז סגור",
] as const;

// ---------------------------------------------------------------------------
// Review stages (ordered pipeline)
// ---------------------------------------------------------------------------

/** Ordered review stages matching user_db.py REVIEW_STAGES. */
export const REVIEW_STAGES: readonly string[] = [
  "לא נסקר",
  "סקירה ראשונית",
  "בדיקה מעמיקה",
  "הוצג בפורום",
  "אושר בפורום",
] as const;

// ---------------------------------------------------------------------------
// Dashboard defaults
// ---------------------------------------------------------------------------

/** Number of days before deadline to flag as "closing soon". */
export const CLOSING_SOON_DAYS = 14;

/** Supabase REST API max rows per request. */
export const SUPABASE_PAGE_SIZE = 1000;

// ---------------------------------------------------------------------------
// External URLs
// ---------------------------------------------------------------------------

/** RMI tender site base URL. */
export const RMI_SITE_URL = "https://apps.land.gov.il/MichrazimSite/#/michraz";

// ---------------------------------------------------------------------------
// Environment-derived values
// ---------------------------------------------------------------------------

/**
 * Shared team email used for the management watchlist.
 * All team members see the same list when logged in with this email.
 */
export const TEAM_EMAIL: string =
  process.env.NEXT_PUBLIC_TEAM_EMAIL ?? "team@tender-dashboard.local";

// ---------------------------------------------------------------------------
// Scoring weights (must match analytics_engine.py _SCORE_WEIGHTS)
// ---------------------------------------------------------------------------

export const SCORE_WEIGHTS = {
  urgency: 0.20,
  size: 0.20,
  readiness: 0.25,
  location: 0.20,
  freshness: 0.15,
} as const;
