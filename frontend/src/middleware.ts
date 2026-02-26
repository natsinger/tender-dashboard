/**
 * Next.js middleware for cookie-based authentication with role-based access.
 *
 * Role logic (mirrors the Python app.py):
 * - team   -> email in NEXT_PUBLIC_TEAM_EMAILS       -> all 4 pages
 * - management -> email in NEXT_PUBLIC_MANAGEMENT_EMAILS -> /management only
 * - unknown    -> redirect to /login with error param
 *
 * Cookie: "user_email" (set by the login page, 30-day expiry).
 */
import { NextResponse, type NextRequest } from "next/server";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Parse a comma-separated env var into a Set of lowercased, trimmed emails. */
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

  const teamEmails = parseEmailList(process.env.NEXT_PUBLIC_TEAM_EMAILS);
  if (teamEmails.has(normalised)) return "team";

  const managementEmails = parseEmailList(
    process.env.NEXT_PUBLIC_MANAGEMENT_EMAILS,
  );
  if (managementEmails.has(normalised)) return "management";

  return null;
}

/** Routes that only "team" role can access. */
const TEAM_ONLY_PATHS = ["/dashboard", "/explorer", "/analytics", "/watchlist"];

/** Routes that do NOT require authentication. */
const PUBLIC_PATHS = ["/login"];

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const userEmail = request.cookies.get("user_email")?.value;

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  // ── Authenticated user visiting /login -> redirect to /management ──
  if (isPublicPath && userEmail) {
    const role = resolveRole(decodeURIComponent(userEmail));
    if (role) {
      return NextResponse.redirect(new URL("/management", request.url));
    }
    // If the cookie has an unknown email, clear it and let them stay on /login
    const response = NextResponse.next();
    response.cookies.delete("user_email");
    return response;
  }

  // ── Unauthenticated user on a protected path -> redirect to /login ──
  if (!isPublicPath && !userEmail) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // ── Authenticated user on a protected path -> check role ──
  if (!isPublicPath && userEmail) {
    const role = resolveRole(decodeURIComponent(userEmail));

    // Unknown email -> clear cookie and redirect to /login with error
    if (!role) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("error", "unauthorized");
      const response = NextResponse.redirect(loginUrl);
      response.cookies.delete("user_email");
      return response;
    }

    // Management role trying to access team-only pages -> redirect to /management
    if (
      role === "management" &&
      TEAM_ONLY_PATHS.some((p) => pathname.startsWith(p))
    ) {
      return NextResponse.redirect(new URL("/management", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  /*
   * Match all routes except:
   * - _next (static files, images, etc.)
   * - api routes
   * - favicon.ico and other static assets
   */
  matcher: ["/((?!_next|api|favicon\\.ico|.*\\..*).*)"],
};
