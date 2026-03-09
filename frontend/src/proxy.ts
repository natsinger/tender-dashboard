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
import { NextResponse, type NextRequest } from "next/server";
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
// Proxy (renamed from middleware for Next.js 16)
// ---------------------------------------------------------------------------

export default async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // ── Intercept auth code from Supabase email redirects ──
  // Signup confirmation emails redirect to the Site URL (/) instead of
  // /auth/callback. If we see a ?code= param with a Supabase `type` param
  // on any non-callback route, forward it to the callback handler.
  const authCode = request.nextUrl.searchParams.get("code");
  const authType = request.nextUrl.searchParams.get("type");
  if (authCode && authType && !pathname.startsWith("/auth/callback")) {
    const callbackUrl = new URL("/auth/callback", request.url);
    callbackUrl.searchParams.set("code", authCode);
    callbackUrl.searchParams.set("type", authType);
    return NextResponse.redirect(callbackUrl);
  }

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  // Dev-only auth bypass: skip all session checks in local development
  if (
    process.env.NODE_ENV === "development" &&
    process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === "true"
  ) {
    return NextResponse.next();
  }

  try {
    // Create Supabase client with cookie bridging (also refreshes tokens).
    // NOTE: Do NOT destructure `response` here -- it would capture a stale
    // value. The getter on the returned object always returns the latest
    // response after any token refresh performed by getUser().
    const client = createMiddlewareClient(request);
    const { supabase } = client;

    // Validate session via JWT verification
    const {
      data: { user },
      error,
    } = await supabase.auth.getUser();

    // Read response AFTER getUser() so we get the version with refreshed cookies
    const response = client.response;

    if (process.env.NODE_ENV === "development") {
      console.log("[Middleware]", pathname, "| user:", user?.email ?? "none", "| error:", error?.message ?? "none");
    }

    // ── Public path handling ──
    if (isPublicPath) {
      if (user?.email) {
        const role = resolveRole(user.email);
        if (role) {
          const redirect = NextResponse.redirect(new URL("/management", request.url));
          // Copy refreshed session cookies to the redirect response
          for (const cookie of response.cookies.getAll()) {
            redirect.cookies.set(cookie.name, cookie.value);
          }
          return redirect;
        }
      }
      return response;
    }

    // ── Protected path: no session -> redirect to login ──
    if (!user?.email) {
      if (process.env.NODE_ENV === "development") {
        console.log("[Middleware] No session, redirecting to /login");
      }
      return NextResponse.redirect(new URL("/login", request.url));
    }

    // ── Protected path: validate role ──
    const role = resolveRole(user.email);
    if (process.env.NODE_ENV === "development") {
      console.log("[Middleware] Role for", user.email, ":", role);
    }

    if (!role) {
      // Don't call signOut() here -- it clears cookies on the internal
      // middleware response, not on the redirect we actually send.
      // The login page will handle the unauthorized state.
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("error", "unauthorized");
      return NextResponse.redirect(loginUrl);
    }

    // Management role trying to access team-only pages -> redirect
    if (
      role === "management" &&
      TEAM_ONLY_PATHS.some((p) => pathname.startsWith(p))
    ) {
      return NextResponse.redirect(new URL("/management", request.url));
    }

    // Return the response object (carries refreshed session cookies)
    return response;
  } catch (err) {
    // If anything fails, redirect to login for safety
    if (process.env.NODE_ENV === "development") {
      console.error("[Middleware] Error:", err);
    }
    if (isPublicPath) {
      return NextResponse.next();
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }
}

export const config = {
  matcher: ["/((?!_next|api|favicon\\.ico|.*\\..*).*)"],
};
