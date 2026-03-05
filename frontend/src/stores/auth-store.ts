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
// Store
// ---------------------------------------------------------------------------

export const useAuthStore = create<AuthState>()((set, get) => ({
  email: null,
  role: null,
  isAuthenticated: false,
  isLoading: true,
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
