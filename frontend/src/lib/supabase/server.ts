/**
 * Server-side Supabase clients for Route Handlers, Server Components,
 * and Server Actions.
 *
 * Two clients:
 * - createAuthClient(): user-scoped, reads session from cookies (for auth)
 * - createAdminClient(): service-role, bypasses RLS (for data operations)
 */
import { createServerClient } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";

/**
 * Create a user-scoped Supabase client that reads the auth session
 * from Next.js cookies. Use in Route Handlers and Server Components.
 */
export async function createAuthClient() {
  const cookieStore = await cookies();

  return createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        for (const { name, value, options } of cookiesToSet) {
          cookieStore.set(name, value, options);
        }
      },
    },
  });
}

/**
 * Create a service-role Supabase client (bypasses RLS).
 * Use for admin data operations only. Never expose to the browser.
 */
export function createAdminClient() {
  if (!supabaseUrl || !serviceRoleKey) {
    console.warn(
      "[Supabase Server] Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY."
    );
  }

  return createClient(supabaseUrl, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
