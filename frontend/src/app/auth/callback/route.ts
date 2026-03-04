/**
 * Auth callback route for Supabase Magic Link.
 *
 * When a user clicks the magic link in their email, Supabase redirects
 * them here with a `code` query parameter. This route exchanges the code
 * for a session, sets the session cookies on the redirect response, and
 * redirects to the appropriate page.
 *
 * IMPORTANT: We create the Supabase client inline (not via createAuthClient)
 * so that session cookies are set directly on the NextResponse redirect
 * object. Using cookies() from next/headers loses cookies on redirect.
 */
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

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

  // Create the redirect response FIRST — cookies will be set on it
  const redirectUrl = new URL("/management", siteUrl);
  const response = NextResponse.redirect(redirectUrl);

  // Create Supabase client that writes cookies directly to the response
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          for (const { name, value, options } of cookiesToSet) {
            response.cookies.set(name, value, options);
          }
        },
      },
    }
  );

  // Exchange the code for a session (this sets cookies on the response)
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    console.error("[Auth Callback] Code exchange failed:", error.message);
    return NextResponse.redirect(
      new URL("/login?error=auth_failed", siteUrl)
    );
  }

  // Get the authenticated user
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user?.email) {
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

  // Return the redirect response WITH session cookies attached
  return response;
}
