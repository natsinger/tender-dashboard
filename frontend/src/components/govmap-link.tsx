/**
 * GovMapLink component.
 *
 * Renders a clickable map icon that opens the tender's TABA plan on
 * govmap.gov.il. Uses pre-computed URL from DB or resolves on-demand.
 */
"use client";

import { Loader2, MapPin } from "lucide-react";

import { useGovmapUrl } from "@/hooks/use-govmap";
import type { Tender } from "@/types/database";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface GovMapLinkProps {
  tender: Tender | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function GovMapLink({ tender }: GovMapLinkProps) {
  const { url, isLoading } = useGovmapUrl(tender);

  // No plan_number on this tender — nothing to link to
  if (!tender?.plan_number) {
    return <span>{"\u2014"}</span>;
  }

  if (isLoading) {
    return <Loader2 className="h-4 w-4 animate-spin text-megido-text-muted" />;
  }

  if (!url) {
    return <span>{"\u2014"}</span>;
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      title={'פתח תב"ע ב-GovMap'}
      onClick={(e) => e.stopPropagation()}
    >
      <MapPin className="h-4 w-4 text-megido-primary hover:text-megido-primary/80" />
    </a>
  );
}
