/**
 * Zustand store for authentication state.
 *
 * Syncs with the Supabase Auth session. Role is resolved server-side
 * (in middleware and /api/auth/role) to keep the email allowlists
 * off the browser. The store no longer manages cookies or resolves
 * roles from env vars.
 */
import { create } from "zustand";
import { supabase } from "@/lib/supabase/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type UserRole = "team" | "management" | null;

interface AuthState {
  email: string | null;
  role: UserRole;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** Whether initialize() has completed successfully with an authenticated user. */
  initialized: boolean;
  initialize: () => Promise<void>;
  logout: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Dev bypass: compute initial state at module load time (no async, no effects)
// ---------------------------------------------------------------------------

const DEV_BYPASS =
  process.env.NODE_ENV === "development" &&
  process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === "true";

const DEV_EMAIL = process.env.NEXT_PUBLIC_TEAM_EMAIL ?? "dev@megido.co.il";
const DEV_PASSWORD = process.env.NEXT_PUBLIC_DEV_PASSWORD ?? "";

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAuthStore = create<AuthState>()((set, get) => ({
  // When dev bypass is active, start already authenticated (no flicker)
  // but NOT initialized, so initialize() still runs to create a real
  // Supabase session for RLS-protected data queries.
  email: DEV_BYPASS ? DEV_EMAIL : null,
  role: DEV_BYPASS ? "team" : null,
  isAuthenticated: DEV_BYPASS,
  isLoading: !DEV_BYPASS,
  initialized: false,

  /**
   * Initialize auth state from the current Supabase session.
   * Called once on app load (in AuthGuard).
   *
   * Allows retry: if the user is not authenticated, `initialized` stays
   * false so a subsequent call (e.g., after magic-link callback) can
   * re-attempt.
   */
  initialize: async () => {
    // Prevent duplicate initialization only when already authenticated
    if (get().initialized) return;

    set({ isLoading: true });

    try {
      // Dev bypass: auto-signin with password to create a real Supabase session
      // (needed for RLS-protected data queries)
      if (DEV_BYPASS && DEV_PASSWORD) {
        const { data: { user }, error } = await supabase.auth.signInWithPassword({
          email: DEV_EMAIL,
          password: DEV_PASSWORD,
        });

        if (!error && user?.email) {
          console.info("[Auth] Dev auto-signin successful as", user.email);
          set({
            email: user.email,
            role: "team",
            isAuthenticated: true,
            isLoading: false,
            initialized: true,
          });
          return;
        }

        console.warn("[Auth] Dev auto-signin failed:", error?.message ?? "no user");
      }

      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (user?.email) {
        // Fetch role from server-side API
        const res = await fetch("/api/auth/role");

        if (!res.ok) {
          // Non-200 response -- treat as unauthenticated
          set({
            email: null,
            role: null,
            isAuthenticated: false,
            isLoading: false,
            initialized: false,
          });
          return;
        }

        const { role } = (await res.json()) as { role: UserRole };

        set({
          email: user.email,
          role: role ?? null,
          isAuthenticated: true,
          isLoading: false,
          initialized: true,
        });
      } else {
        set({
          email: null,
          role: null,
          isAuthenticated: false,
          isLoading: false,
          initialized: false,
        });
      }
    } catch {
      set({
        email: null,
        role: null,
        isAuthenticated: false,
        isLoading: false,
        initialized: false,
      });
    }
  },

  /** Sign out via Supabase (clears session cookies) and reset state. */
  logout: async () => {
    await supabase.auth.signOut();
    set({
      email: null,
      role: null,
      isAuthenticated: false,
      isLoading: false,
      initialized: false,
    });
  },
}));
