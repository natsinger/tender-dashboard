/**
 * API route for on-demand GovMap TABA URL resolution.
 *
 * Proxies requests to the GovMap internal TABA search API to avoid
 * CORS issues. Caches responses for 24 hours.
 *
 * Usage: GET /api/govmap?planNumber=33/101/02/24
 */
import { NextRequest, NextResponse } from "next/server";

const GOVMAP_TABA_API = "https://www.govmap.gov.il/api/taba/taba/plan";
const GOVMAP_VIEWER_BASE = "https://www.govmap.gov.il/?app=app07&ma=";

interface TabaPlan {
  mishasava?: number;
  [key: string]: unknown;
}

interface TabaResponse {
  tabaPlans?: TabaPlan[];
  [key: string]: unknown;
}

export async function GET(request: NextRequest) {
  const planNumber = request.nextUrl.searchParams.get("planNumber");

  if (!planNumber || !planNumber.trim()) {
    return NextResponse.json(
      { url: null, error: "Missing or empty planNumber parameter" },
      { status: 400 },
    );
  }

  const encoded = encodeURIComponent(planNumber.trim());

  try {
    const response = await fetch(`${GOVMAP_TABA_API}/${encoded}`, {
      headers: {
        Accept: "application/json",
        "User-Agent": "TenderDashboard/1.0",
      },
      next: { revalidate: 86400 }, // cache for 24 hours
    });

    if (!response.ok) {
      return NextResponse.json(
        { url: null, error: `GovMap API returned ${response.status}` },
        { status: 502 },
      );
    }

    const data: TabaResponse = await response.json();

    const tabaPlans = data.tabaPlans;
    if (!tabaPlans || !Array.isArray(tabaPlans) || tabaPlans.length === 0) {
      return NextResponse.json({ url: null, error: "Plan not found on GovMap" });
    }

    const match = tabaPlans.find((plan) => plan.mishasava);
    if (!match || !match.mishasava) {
      return NextResponse.json({ url: null, error: "Plan not found on GovMap" });
    }

    return NextResponse.json({
      url: `${GOVMAP_VIEWER_BASE}${match.mishasava}`,
      mishasava: match.mishasava,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { url: null, error: `Failed to fetch from GovMap: ${message}` },
      { status: 502 },
    );
  }
}
