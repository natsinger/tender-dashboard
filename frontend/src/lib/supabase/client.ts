/**
 * Browser-side Supabase client using @supabase/ssr.
 *
 * Stores the auth session in cookies (not localStorage) so that
 * Next.js middleware can validate the JWT server-side.
 * All hooks that import `supabase` from this module continue
 * to work unchanged — the export name is the same.
 */
import { createBrowserClient } from "@supabase/ssr";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    "[Supabase] Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY."
  );
}

export const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    // Disable auto-detection so we handle the code exchange explicitly
    // in /auth/callback. This avoids race conditions and lets us capture
    // the actual error when the exchange fails.
    detectSessionInUrl: false,
  },
});
