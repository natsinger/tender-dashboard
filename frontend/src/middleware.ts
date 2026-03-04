/**
 * Next.js middleware for Supabase Auth session validation and role-based access.
 *
 * On every request to a protected route:
 * 1. Creates a Supabase middleware client (reads/refreshes session cookies)
 * 2. Validates the session via supabase.auth.getUser()
 * 3. Resolves the user's role from server-side email allowlists
 * 4. Redirects unauthorized users to /login
 * 5. Enforces role-based route restrictions
 */
import { type NextRequest } from "next/server";
import { createMiddlewareClient } from "@/lib/supabase/middleware";

// ---------------------------------------------------------------------------
// Helpers (server-side only — reads TEAM_EMAILS, not NEXT_PUBLIC_*)
// ---------------------------------------------------------------------------

function parseEmailList(envVar: string | undefined): Set<string> {
  if (!envVar) return new Set();
  return new Set(
    envVar
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean),
  );
}

type Role = "team" | "management" | null;

function resolveRole(email: string): Role {
  const normalised = email.toLowerCase().trim();

  const teamEmails = parseEmailList(process.env.TEAM_EMAILS);
  if (teamEmails.has(normalised)) return "team";

  const managementEmails = parseEmailList(process.env.MANAGEMENT_EMAILS);
  if (managementEmails.has(normalised)) return "management";

  return null;
}

/** Routes that only "team" role can access. */
const TEAM_ONLY_PATHS = ["/dashboard", "/explorer", "/analytics", "/watchlist"];

/** Routes that do NOT require authentication. */
const PUBLIC_PATHS = ["/login", "/auth/callback"];

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  // Create Supabase client with cookie bridging (also refreshes tokens)
  const { supabase, response } = createMiddlewareClient(request);

  // Validate session via JWT verification
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // ── Public path handling ──
  if (isPublicPath) {
    if (user?.email) {
      const role = resolveRole(user.email);
      if (role) {
        const url = request.nextUrl.clone();
        url.pathname = "/management";
        url.search = "";
        return Response.redirect(url);
      }
    }
    return response;
  }

  // ── Protected path: no session -> redirect to login ──
  if (!user?.email) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return Response.redirect(url);
  }

  // ── Protected path: validate role ──
  const role = resolveRole(user.email);

  if (!role) {
    await supabase.auth.signOut();
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("error", "unauthorized");
    return Response.redirect(url);
  }

  // Management role trying to access team-only pages -> redirect
  if (
    role === "management" &&
    TEAM_ONLY_PATHS.some((p) => pathname.startsWith(p))
  ) {
    const url = request.nextUrl.clone();
    url.pathname = "/management";
    url.search = "";
    return Response.redirect(url);
  }

  // Return the response object (carries refreshed session cookies)
  return response;
}

export const config = {
  matcher: ["/((?!_next|api|favicon\\.ico|.*\\..*).*)"],
};
