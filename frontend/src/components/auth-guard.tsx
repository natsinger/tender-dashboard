/**
 * Client-side auth guard component.
 *
 * Wraps page content and enforces authentication + role-based access.
 * - If not authenticated -> redirects to /login
 * - If authenticated but wrong role for current page -> shows permission error
 * - Otherwise -> renders children
 *
 * NOTE: The middleware already handles redirects server-side, so this is a
 * defence-in-depth layer for client-side navigation and hydration mismatches.
 */
"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore, type UserRole } from "@/stores/auth-store";

// ---------------------------------------------------------------------------
// Route -> required role mapping
// ---------------------------------------------------------------------------

/** Pages that only "team" role can access. */
const TEAM_ONLY_PATHS = ["/dashboard", "/explorer", "/analytics"];

/** Check whether the given role is allowed on the current path. */
function isRoleAllowed(role: UserRole, pathname: string): boolean {
  if (!role) return false;
  if (role === "team") return true;
  // Management can only access /management
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
  const { isAuthenticated, role } = useAuthStore();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    setChecked(true);
  }, [isAuthenticated, router]);

  // Still checking auth state
  if (!checked) {
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
            אין לך הרשאה
          </p>
          <p className="mt-2 text-sm text-megido-text-muted">
            אין לך הרשאה לצפות בעמוד זה. פנה למנהל המערכת.
          </p>
          <button
            type="button"
            onClick={() => router.push("/management")}
            className="mt-4 rounded-lg bg-megido-primary px-6 py-2 text-sm font-medium text-white hover:bg-megido-primary-hover"
          >
            חזרה ללוח הנהלה
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
