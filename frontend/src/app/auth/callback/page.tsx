/**
 * Auth callback page for Supabase Magic Link.
 *
 * Handles two flows:
 * 1. PKCE code exchange — Supabase redirects with ?code=AUTH_CODE
 * 2. Direct token verification — email template links with ?token_hash=HASH&type=TYPE
 *
 * Uses the BROWSER Supabase client so the PKCE code_verifier cookie is
 * accessible. After establishing the session, navigates to /management
 * (full page load triggers the proxy for role validation).
 */
"use client";

import { useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase/client";
import type { EmailOtpType } from "@supabase/supabase-js";

function CallbackHandler() {
  const searchParams = useSearchParams();
  const processed = useRef(false);

  useEffect(() => {
    // Prevent double-processing in React strict mode
    if (processed.current) return;
    processed.current = true;

    async function handleCallback() {
      const code = searchParams.get("code");
      const tokenHash = searchParams.get("token_hash");
      const type = searchParams.get("type") as EmailOtpType | null;

      try {
        if (tokenHash && type) {
          // Direct token verification (custom email template)
          const { error } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type,
          });

          if (error) {
            console.error("[Auth Callback] verifyOtp failed:", error.message);
            window.location.href = "/login?error=auth_failed";
            return;
          }
        } else if (code) {
          // PKCE code exchange (default Supabase email flow)
          const { error } = await supabase.auth.exchangeCodeForSession(code);

          if (error) {
            console.error("[Auth Callback] exchangeCodeForSession failed:", error.message);
            window.location.href = "/login?error=auth_failed";
            return;
          }
        } else {
          window.location.href = "/login?error=missing_code";
          return;
        }

        // Session established — full page nav triggers proxy role validation
        window.location.href = "/management";
      } catch (err) {
        console.error("[Auth Callback] Unexpected error:", err);
        window.location.href = "/login?error=auth_failed";
      }
    }

    handleCallback();
  }, [searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-megido-bg-main">
      <div className="text-center" dir="rtl">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-megido-primary border-t-transparent" />
        <p className="text-sm text-megido-text-muted">
          {"מאמת כניסה..."}
        </p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-megido-bg-main">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-megido-primary border-t-transparent" />
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
