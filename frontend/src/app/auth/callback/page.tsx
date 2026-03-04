/**
 * Auth callback page for Supabase Magic Link.
 *
 * IMPORTANT: createBrowserClient from @supabase/ssr auto-detects ?code=
 * in the URL and exchanges it during initialization (detectSessionInUrl).
 * We must NOT call exchangeCodeForSession() ourselves — the code is
 * single-use and would fail on the second call. Instead, we listen for
 * the session to appear via onAuthStateChange.
 *
 * For ?token_hash= flow (custom email templates), we call verifyOtp()
 * explicitly since that's not auto-detected.
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
    if (processed.current) return;
    processed.current = true;

    const code = searchParams.get("code");
    const tokenHash = searchParams.get("token_hash");
    const type = searchParams.get("type") as EmailOtpType | null;

    // No auth parameters at all
    if (!code && !tokenHash) {
      window.location.href = "/login?error=missing_code";
      return;
    }

    // --- token_hash flow (custom email templates) ---
    // Not auto-detected, so we verify explicitly.
    if (tokenHash && type) {
      supabase.auth
        .verifyOtp({ token_hash: tokenHash, type })
        .then(({ error }) => {
          if (error) {
            console.error("[Auth Callback] verifyOtp failed:", error.message);
            window.location.href = "/login?error=auth_failed";
          } else {
            window.location.href = "/management";
          }
        });
      return;
    }

    // --- ?code= PKCE flow ---
    // createBrowserClient auto-detects ?code= and exchanges it during
    // initialization. We just wait for the session to appear.
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (session) {
          cleanup();
          window.location.href = "/management";
        }
      },
    );

    // Check if session was already established before we subscribed
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        cleanup();
        window.location.href = "/management";
      }
    });

    // Timeout: if session isn't established within 10s, something failed
    const timeout = setTimeout(() => {
      cleanup();
      console.error("[Auth Callback] Timed out waiting for session");
      window.location.href = "/login?error=auth_failed";
    }, 10_000);

    function cleanup() {
      subscription.unsubscribe();
      clearTimeout(timeout);
    }

    return cleanup;
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
