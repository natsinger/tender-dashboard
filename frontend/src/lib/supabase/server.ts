/**
 * Server-side Supabase client for React Server Components.
 *
 * Uses the service role key (SUPABASE_SERVICE_ROLE_KEY) which bypasses
 * Row Level Security. Only use in server components, API routes, and
 * server actions -- never expose to the browser.
 */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";

if (!supabaseUrl || !serviceRoleKey) {
  console.warn(
    "[Supabase Server] Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY. " +
      "Server-side Supabase client will not function correctly."
  );
}

/**
 * Create a new server-side Supabase client.
 *
 * A fresh client is created per call to avoid leaking auth state between
 * requests in the serverless/edge environment.
 */
export function createServerClient(): SupabaseClient {
  return createClient(supabaseUrl, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
