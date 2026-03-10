/**
 * GovMapLink component.
 *
 * Renders a clickable icon that opens the tender's TABA plan.
 * - GovMap URL (primary): blue MapPin icon → opens govmap.gov.il viewer.
 * - Mavat fallback: muted Search icon → opens mavat.iplan.gov.il search.
 */
"use client";

import { Loader2, MapPin, Search } from "lucide-react";

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
  const { url, isLoading, source } = useGovmapUrl(tender);

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

  const isGovmap = source === "govmap";

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      title={isGovmap ? 'פתח תב"ע ב-GovMap' : 'חפש תב"ע ב-Mavat'}
      onClick={(e) => e.stopPropagation()}
    >
      {isGovmap ? (
        <MapPin className="h-4 w-4 text-megido-primary hover:text-megido-primary/80" />
      ) : (
        <Search className="h-4 w-4 text-megido-text-muted hover:text-megido-primary/60" />
      )}
    </a>
  );
}
