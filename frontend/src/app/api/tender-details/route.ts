/**
 * API route that proxies RMI tender detail requests.
 *
 * Fetches the full tender detail (including the Tik[] array with per-lot
 * financial data) from the Israel Land Authority API and returns it to
 * the client. This avoids CORS issues when calling the government API
 * directly from the browser.
 *
 * Usage: GET /api/tender-details?id=20250507
 */
import { NextRequest, NextResponse } from "next/server";

const RMI_DETAIL_API =
  "https://apps.land.gov.il/MichrazimSite/api/MichrazDetailsApi/Get";

export async function GET(request: NextRequest) {
  const tenderId = request.nextUrl.searchParams.get("id");

  if (!tenderId || !/^\d+$/.test(tenderId)) {
    return NextResponse.json(
      { error: "Missing or invalid tender ID" },
      { status: 400 },
    );
  }

  try {
    const response = await fetch(
      `${RMI_DETAIL_API}?michrazID=${tenderId}`,
      {
        headers: {
          Accept: "application/json",
          "User-Agent": "TenderDashboard/1.0",
        },
        next: { revalidate: 3600 }, // cache for 1 hour
      },
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: `RMI API returned ${response.status}` },
        { status: 502 },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { error: `Failed to fetch tender details: ${message}` },
      { status: 502 },
    );
  }
}
