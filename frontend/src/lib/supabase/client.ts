/**
 * Browser-side Supabase client.
 * Creates a singleton client using public environment variables.
 * Use this in client components and React hooks.
 */
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    "[Supabase] Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. " +
      "Supabase client will not function correctly."
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
