/**
 * Auth callback route for Supabase Magic Link.
 *
 * When a user clicks the magic link in their email, Supabase redirects
 * them here with a `code` query parameter. This route exchanges the code
 * for a session, validates the email against the server-side allowlist,
 * and redirects to the appropriate page.
 */
import { NextResponse, type NextRequest } from "next/server";
import { createAuthClient } from "@/lib/supabase/server";

// ---------------------------------------------------------------------------
// Server-side role resolution (env vars without NEXT_PUBLIC_ prefix)
// ---------------------------------------------------------------------------

function parseEmailList(envVar: string | undefined): Set<string> {
  if (!envVar) return new Set();
  return new Set(
    envVar
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean)
  );
}

function resolveRole(email: string): "team" | "management" | null {
  const normalised = email.toLowerCase().trim();

  const teamEmails = parseEmailList(process.env.TEAM_EMAILS);
  if (teamEmails.has(normalised)) return "team";

  const managementEmails = parseEmailList(process.env.MANAGEMENT_EMAILS);
  if (managementEmails.has(normalised)) return "management";

  return null;
}

// ---------------------------------------------------------------------------
// GET handler
// ---------------------------------------------------------------------------

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get("code");
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? request.nextUrl.origin;

  if (!code) {
    return NextResponse.redirect(
      new URL("/login?error=missing_code", siteUrl)
    );
  }

  const supabase = await createAuthClient();

  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    console.error("[Auth Callback] Code exchange failed:", error.message);
    return NextResponse.redirect(
      new URL("/login?error=auth_failed", siteUrl)
    );
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user?.email) {
    await supabase.auth.signOut();
    return NextResponse.redirect(
      new URL("/login?error=no_email", siteUrl)
    );
  }

  // Validate against the server-side allowlist
  const role = resolveRole(user.email);

  if (!role) {
    await supabase.auth.signOut();
    return NextResponse.redirect(
      new URL("/login?error=unauthorized", siteUrl)
    );
  }

  return NextResponse.redirect(new URL("/management", siteUrl));
}
