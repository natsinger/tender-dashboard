/**
 * Login page -- Supabase Magic Link authentication.
 *
 * Flow:
 * 1. User enters email -> signInWithOtp sends a magic link
 * 2. Page shows "check your email" confirmation
 * 3. User clicks link in email -> /auth/callback exchanges code for session
 * 4. Middleware validates session and role, redirects to /management
 */
"use client";

import { useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Building2, Mail } from "lucide-react";
import { supabase } from "@/lib/supabase/client";

// ---------------------------------------------------------------------------
// Error messages (Hebrew)
// ---------------------------------------------------------------------------

const ERROR_MESSAGES: Record<string, string> = {
  unauthorized: "\u05D0\u05D9\u05DF \u05DC\u05DA \u05D4\u05E8\u05E9\u05D0\u05D4 \u05DC\u05E6\u05E4\u05D5\u05EA \u05D1\u05D0\u05E4\u05DC\u05D9\u05E7\u05E6\u05D9\u05D4. \u05E4\u05E0\u05D4 \u05DC\u05DE\u05E0\u05D4\u05DC \u05D4\u05DE\u05E2\u05E8\u05DB\u05EA.",
  auth_failed: "\u05D0\u05D9\u05DE\u05D5\u05EA \u05E0\u05DB\u05E9\u05DC. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1.",
  missing_code: "\u05E7\u05D9\u05E9\u05D5\u05E8 \u05DC\u05D0 \u05EA\u05E7\u05D9\u05DF. \u05E0\u05E1\u05D4 \u05DC\u05D4\u05EA\u05D7\u05D1\u05E8 \u05E9\u05D5\u05D1.",
  no_email: "\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D4 \u05DB\u05EA\u05D5\u05D1\u05EA \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1.",
};

// ---------------------------------------------------------------------------
// Inner form component (useSearchParams requires Suspense boundary)
// ---------------------------------------------------------------------------

function LoginForm() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const searchParams = useSearchParams();

  // Show error from callback redirect
  useEffect(() => {
    const errorParam = searchParams.get("error");
    if (errorParam && ERROR_MESSAGES[errorParam]) {
      setError(ERROR_MESSAGES[errorParam]);
    }
  }, [searchParams]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const trimmedEmail = email.trim().toLowerCase();

    if (!trimmedEmail) {
      setError("\u05E0\u05D0 \u05DC\u05D4\u05D6\u05D9\u05DF \u05DB\u05EA\u05D5\u05D1\u05EA \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setError("\u05DB\u05EA\u05D5\u05D1\u05EA \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC \u05DC\u05D0 \u05EA\u05E7\u05D9\u05E0\u05D4");
      return;
    }

    setIsLoading(true);

    try {
      const siteUrl =
        process.env.NEXT_PUBLIC_SITE_URL ?? window.location.origin;

      const { error: otpError } = await supabase.auth.signInWithOtp({
        email: trimmedEmail,
        options: {
          emailRedirectTo: `${siteUrl}/auth/callback`,
        },
      });

      if (otpError) {
        // Rate limit or other non-critical errors — log but still show
        // "check your email" since Supabase may have sent the email anyway
        if (process.env.NODE_ENV === "development") {
          console.warn("[Login] OTP warning:", otpError.message);
        }

        // Only block on critical errors, not rate limits or signup flows
        if (otpError.message?.includes("rate limit")) {
          setError("\u05E0\u05E9\u05DC\u05D7\u05D5 \u05D9\u05D5\u05EA\u05E8 \u05DE\u05D3\u05D9 \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC\u05D9\u05DD. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1 \u05D1\u05E2\u05D5\u05D3 \u05DB\u05DE\u05D4 \u05D3\u05E7\u05D5\u05EA.");
          return;
        }
      }

      setEmailSent(true);
    } catch {
      setError("\u05D0\u05D9\u05E8\u05E2\u05D4 \u05E9\u05D2\u05D9\u05D0\u05D4. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1.");
    } finally {
      setIsLoading(false);
    }
  }

  // ---- "Check your email" state ----
  if (emailSent) {
    return (
      <div className="space-y-4 text-center" dir="rtl">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <Mail className="h-8 w-8 text-green-600" />
        </div>
        <h3 className="text-lg font-semibold text-megido-text-heading">
          {"\u05D1\u05D3\u05D5\u05E7 \u05D0\u05EA \u05EA\u05D9\u05D1\u05EA \u05D4\u05D3\u05D5\u05D0\u05E8 \u05E9\u05DC\u05DA"}
        </h3>
        <p className="text-sm text-megido-text-muted">
          {"\u05E9\u05DC\u05D7\u05E0\u05D5 \u05E7\u05D9\u05E9\u05D5\u05E8 \u05DB\u05E0\u05D9\u05E1\u05D4 \u05DC-"}
          <span className="font-medium text-megido-text-body" dir="ltr">
            {email}
          </span>
        </p>
        <p className="text-xs text-megido-text-muted">
          {"\u05DC\u05D7\u05E5 \u05E2\u05DC \u05D4\u05E7\u05D9\u05E9\u05D5\u05E8 \u05D1\u05D0\u05D9\u05DE\u05D9\u05D9\u05DC \u05DB\u05D3\u05D9 \u05DC\u05D4\u05EA\u05D7\u05D1\u05E8 \u05DC\u05DE\u05E2\u05E8\u05DB\u05EA"}
        </p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => {
            setEmailSent(false);
            setEmail("");
          }}
        >
          {"\u05E9\u05DC\u05D7 \u05E9\u05D5\u05D1"}
        </Button>
      </div>
    );
  }

  // ---- Email input form ----
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label
          htmlFor="email"
          className="text-sm font-medium text-megido-text-body"
        >
          {"\u05D4\u05DB\u05E0\u05E1 \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC"}
        </label>
        <Input
          id="email"
          type="email"
          placeholder="name@megido.co.il"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          dir="ltr"
          className="text-left"
          autoComplete="email"
          autoFocus
        />
      </div>

      {error && (
        <p className="text-sm text-megido-danger" role="alert">
          {error}
        </p>
      )}

      <Button
        type="submit"
        className="w-full bg-megido-primary text-white hover:bg-megido-primary-hover"
        disabled={isLoading}
      >
        {isLoading
          ? "\u05E9\u05D5\u05DC\u05D7 \u05E7\u05D9\u05E9\u05D5\u05E8..."
          : "\u05E9\u05DC\u05D7 \u05E7\u05D9\u05E9\u05D5\u05E8 \u05DB\u05E0\u05D9\u05E1\u05D4"}
      </Button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-megido-bg-main p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-megido-primary-light">
            <Building2 className="h-8 w-8 text-megido-primary" />
          </div>
          <CardTitle className="text-2xl font-bold text-megido-text-heading">
            {"\u05DB\u05E0\u05D9\u05E1\u05D4 \u05DC\u05DE\u05E2\u05E8\u05DB\u05EA"}
          </CardTitle>
          <CardDescription className="text-megido-text-muted">
            {"\u05DE\u05E2\u05E8\u05DB\u05EA \u05DE\u05D5\u05D3\u05D9\u05E2\u05D9\u05DF \u05DC\u05DE\u05DB\u05E8\u05D6\u05D9 \u05E7\u05E8\u05E7\u05E2 -- MEGIDO"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={null}>
            <LoginForm />
          </Suspense>
        </CardContent>
      </Card>
    </div>
  );
}
