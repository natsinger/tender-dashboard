/**
 * Client-side auth guard component.
 *
 * Wraps page content and enforces authentication + role-based access.
 * Initializes auth state from the Supabase session on mount.
 *
 * NOTE: The middleware already handles redirects server-side, so this is a
 * defence-in-depth layer for client-side navigation and hydration.
 */
"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore, type UserRole } from "@/stores/auth-store";

// ---------------------------------------------------------------------------
// Route -> required role mapping
// ---------------------------------------------------------------------------

const TEAM_ONLY_PATHS = ["/dashboard", "/explorer", "/analytics", "/watchlist"];

function isRoleAllowed(role: UserRole, pathname: string): boolean {
  if (!role) return false;
  if (role === "team") return true;
  return !TEAM_ONLY_PATHS.some((p) => pathname.startsWith(p));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, role, isLoading, initialize } = useAuthStore();

  // Initialize auth state from Supabase session
  useEffect(() => {
    initialize();
  }, [initialize]);

  // Redirect to login if not authenticated (after loading completes)
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-megido-primary border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  // Authenticated but wrong role for this page
  if (!isRoleAllowed(role, pathname)) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-4 py-20 text-center"
        dir="rtl"
      >
        <div className="rounded-lg border border-megido-danger/20 bg-red-50 p-8">
          <p className="text-lg font-semibold text-megido-danger">
            {"\u05D0\u05D9\u05DF \u05DC\u05DA \u05D4\u05E8\u05E9\u05D0\u05D4"}
          </p>
          <p className="mt-2 text-sm text-megido-text-muted">
            {"\u05D0\u05D9\u05DF \u05DC\u05DA \u05D4\u05E8\u05E9\u05D0\u05D4 \u05DC\u05E6\u05E4\u05D5\u05EA \u05D1\u05E2\u05DE\u05D5\u05D3 \u05D6\u05D4. \u05E4\u05E0\u05D4 \u05DC\u05DE\u05E0\u05D4\u05DC \u05D4\u05DE\u05E2\u05E8\u05DB\u05EA."}
          </p>
          <button
            type="button"
            onClick={() => router.push("/management")}
            className="mt-4 rounded-lg bg-megido-primary px-6 py-2 text-sm font-medium text-white hover:bg-megido-primary-hover"
          >
            {"\u05D7\u05D6\u05E8\u05D4 \u05DC\u05DC\u05D5\u05D7 \u05D4\u05E0\u05D4\u05DC\u05D4"}
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
