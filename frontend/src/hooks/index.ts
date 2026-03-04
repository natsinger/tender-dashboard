/**
 * Barrel export for all React Query hooks.
 *
 * Import hooks from "@/hooks" instead of individual files.
 */

// Tender data
export { useActiveTenders, useTender, useTenders } from "./use-tenders";

// Documents
export { useNewDocuments, useTenderDocuments } from "./use-documents";

// Lots & building rights
export {
  useBuildingRights,
  useTenderBuildingRights,
  useTenderLots,
} from "./use-lots";

// Prices & taba analytics
export { useTabaAnalytics, useTenderPrices } from "./use-prices";

// Watchlist
export {
  useAddToWatchlist,
  useRemoveFromWatchlist,
  useSetWatchlistNote,
  useTeamWatchlist,
  useWatchlist,
} from "./use-watchlist";

// Reviews
export { useReviewStatuses, useSetReviewStatus } from "./use-reviews";
