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

  /**
   * Initialize auth state from the current Supabase session.
   * Called once on app load (in AuthGuard).
   */
  initialize: async () => {
    // Prevent duplicate initialization
    if (!get().isLoading) return;

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.user?.email) {
        // Fetch role from server-side API
        const res = await fetch("/api/auth/role");
        const { role } = (await res.json()) as { role: UserRole };

        set({
          email: session.user.email,
          role: role ?? null,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        set({
          email: null,
          role: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }
    } catch {
      set({
        email: null,
        role: null,
        isAuthenticated: false,
        isLoading: false,
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
    });
  },
}));
