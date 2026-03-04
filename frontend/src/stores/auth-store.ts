/**
 * Zustand store for authentication state.
 *
 * Manages the current user's email and role. Role is determined by
 * checking the email against environment-provided allow lists
 * (NEXT_PUBLIC_TEAM_EMAILS and NEXT_PUBLIC_MANAGEMENT_EMAILS).
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type UserRole = "team" | "management" | null;

interface AuthState {
  email: string | null;
  role: UserRole;
  isAuthenticated: boolean;
  login: (email: string) => void;
  logout: () => void;
}

// ---------------------------------------------------------------------------
// Role resolution helpers
// ---------------------------------------------------------------------------

/**
 * Parse a comma-separated env var into a Set of lowercased emails.
 */
function parseEmailList(envVar: string | undefined): Set<string> {
  if (!envVar) return new Set();
  return new Set(
    envVar
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean),
  );
}

/**
 * Determine the user's role from their email.
 *
 * - If in TEAM_EMAILS -> "team" (full access to all pages)
 * - If in MANAGEMENT_EMAILS -> "management" (management page only)
 * - Otherwise -> null (blocked)
 */
export function resolveRole(email: string): UserRole {
  const normalEmail = email.toLowerCase().trim();

  const teamEmails = parseEmailList(
    process.env.NEXT_PUBLIC_TEAM_EMAILS,
  );
  if (teamEmails.has(normalEmail)) return "team";

  const managementEmails = parseEmailList(
    process.env.NEXT_PUBLIC_MANAGEMENT_EMAILS,
  );
  if (managementEmails.has(normalEmail)) return "management";

  return null;
}

// ---------------------------------------------------------------------------
// Cookie helpers
// ---------------------------------------------------------------------------

/** Remove the user_email cookie by expiring it. */
function clearAuthCookie(): void {
  if (typeof document === "undefined") return;
  document.cookie =
    "user_email=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      email: null,
      role: null,
      isAuthenticated: false,

      login: (email: string) => {
        const role = resolveRole(email);
        set({
          email: email.toLowerCase().trim(),
          role,
          isAuthenticated: role !== null,
        });
      },

      logout: () => {
        clearAuthCookie();
        set({
          email: null,
          role: null,
          isAuthenticated: false,
        });
      },
    }),
    {
      name: "auth-store",
    },
  ),
);
