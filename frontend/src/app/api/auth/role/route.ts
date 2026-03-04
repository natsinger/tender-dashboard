/**
 * API route to resolve the current user's role from server-side allowlists.
 *
 * Called by the client auth store after session initialization to get
 * the user's role without exposing the email lists to the browser.
 */
import { NextResponse } from "next/server";
import { createAuthClient } from "@/lib/supabase/server";

function parseEmailList(envVar: string | undefined): Set<string> {
  if (!envVar) return new Set();
  return new Set(
    envVar
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean)
  );
}

export async function GET() {
  const supabase = await createAuthClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user?.email) {
    return NextResponse.json({ role: null }, { status: 401 });
  }

  const email = user.email.toLowerCase().trim();
  const teamEmails = parseEmailList(process.env.TEAM_EMAILS);
  const managementEmails = parseEmailList(process.env.MANAGEMENT_EMAILS);

  let role: string | null = null;
  if (teamEmails.has(email)) role = "team";
  else if (managementEmails.has(email)) role = "management";

  return NextResponse.json({ role });
}
