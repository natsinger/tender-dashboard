/**
 * Auth callback page for Supabase Magic Link.
 *
 * detectSessionInUrl is disabled on the browser client, so we handle
 * the code exchange explicitly here. This avoids race conditions and
 * lets us capture + display the actual error for debugging.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase/client";
import type { EmailOtpType } from "@supabase/supabase-js";

function CallbackHandler() {
  const searchParams = useSearchParams();
  const processed = useRef(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    async function handleCallback() {
      const code = searchParams.get("code");
      const tokenHash = searchParams.get("token_hash");
      const rawType = searchParams.get("type");

      // Validate OTP type against allowlist
      const VALID_OTP_TYPES: EmailOtpType[] = ["magiclink", "email"];
      const type: EmailOtpType | null =
        rawType && VALID_OTP_TYPES.includes(rawType as EmailOtpType)
          ? (rawType as EmailOtpType)
          : null;

      if (!code && !tokenHash) {
        setErrorMsg("\u05D4\u05E7\u05D9\u05E9\u05D5\u05E8 \u05D0\u05D9\u05E0\u05D5 \u05EA\u05E7\u05D9\u05E3 \u05D0\u05D5 \u05E9\u05E4\u05D2 \u05EA\u05D5\u05E7\u05E4\u05D5. \u05E0\u05E1\u05D4/\u05D9 \u05E9\u05E0\u05D9\u05EA.");
        return;
      }

      try {
        let error;

        if (tokenHash && type) {
          const result = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type,
          });
          error = result.error;
        } else if (code) {
          const result = await supabase.auth.exchangeCodeForSession(code);
          error = result.error;
        }

        if (error) {
          if (process.env.NODE_ENV === "development") {
            console.error("[Auth Callback] Error:", error.message, error);
          }
          setErrorMsg("\u05D0\u05D9\u05E8\u05E2\u05D4 \u05E9\u05D2\u05D9\u05D0\u05D4 \u05D1\u05EA\u05D4\u05DC\u05D9\u05DA \u05D4\u05D0\u05D9\u05DE\u05D5\u05EA. \u05E0\u05E1\u05D4/\u05D9 \u05E9\u05E0\u05D9\u05EA.");
          return;
        }

        // Session established — redirect
        window.location.href = "/management";
      } catch {
        setErrorMsg("\u05D0\u05D9\u05E8\u05E2\u05D4 \u05E9\u05D2\u05D9\u05D0\u05D4 \u05D1\u05EA\u05D4\u05DC\u05D9\u05DA \u05D4\u05D0\u05D9\u05DE\u05D5\u05EA. \u05E0\u05E1\u05D4/\u05D9 \u05E9\u05E0\u05D9\u05EA.");
      }
    }

    handleCallback();
  }, [searchParams]);

  // Show error with details for debugging
  if (errorMsg) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-megido-bg-main p-4">
        <div className="w-full max-w-md rounded-lg border border-red-200 bg-white p-6 text-center" dir="rtl">
          <p className="text-lg font-semibold text-red-600 mb-2">
            {"אימות נכשל"}
          </p>
          <p className="text-sm text-gray-600 mb-4">
            {errorMsg}
          </p>
          <a
            href="/login"
            className="inline-block rounded-lg bg-megido-primary px-6 py-2 text-sm font-medium text-white hover:bg-megido-primary-hover"
          >
            {"חזרה לדף הכניסה"}
          </a>
        </div>
      </div>
    );
  }

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
