/**
 * Login page -- Supabase authentication with Magic Link and Password methods.
 *
 * Flow (Magic Link):
 * 1. User enters email -> signInWithOtp sends a magic link
 * 2. Page shows "check your email" confirmation
 * 3. User clicks link in email -> /auth/callback exchanges code for session
 * 4. Middleware validates session and role, redirects to /management
 *
 * Flow (Password):
 * 1. User enters email + password -> signInWithPassword creates session
 * 2. On success, redirect directly to /management
 *
 * Flow (Sign Up):
 * 1. User enters email + password + confirm password -> signUp creates account
 * 2. Confirmation message shown (email verification may be required)
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Building2, Mail, Lock, Loader2 } from "lucide-react";
import { supabase } from "@/lib/supabase/client";

// ---------------------------------------------------------------------------
// Error messages (Hebrew)
// ---------------------------------------------------------------------------

const ERROR_MESSAGES: Record<string, string> = {
  unauthorized:
    "\u05D0\u05D9\u05DF \u05DC\u05DA \u05D4\u05E8\u05E9\u05D0\u05D4 \u05DC\u05E6\u05E4\u05D5\u05EA \u05D1\u05D0\u05E4\u05DC\u05D9\u05E7\u05E6\u05D9\u05D4. \u05E4\u05E0\u05D4 \u05DC\u05DE\u05E0\u05D4\u05DC \u05D4\u05DE\u05E2\u05E8\u05DB\u05EA.",
  auth_failed:
    "\u05D0\u05D9\u05DE\u05D5\u05EA \u05E0\u05DB\u05E9\u05DC. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1.",
  missing_code:
    "\u05E7\u05D9\u05E9\u05D5\u05E8 \u05DC\u05D0 \u05EA\u05E7\u05D9\u05DF. \u05E0\u05E1\u05D4 \u05DC\u05D4\u05EA\u05D7\u05D1\u05E8 \u05E9\u05D5\u05D1.",
  no_email:
    "\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D4 \u05DB\u05EA\u05D5\u05D1\u05EA \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1.",
};

// ---------------------------------------------------------------------------
// Magic Link form (preserves ALL existing logic)
// ---------------------------------------------------------------------------

function MagicLinkForm() {
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
      setError(
        "\u05E0\u05D0 \u05DC\u05D4\u05D6\u05D9\u05DF \u05DB\u05EA\u05D5\u05D1\u05EA \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC"
      );
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setError(
        "\u05DB\u05EA\u05D5\u05D1\u05EA \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC \u05DC\u05D0 \u05EA\u05E7\u05D9\u05E0\u05D4"
      );
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
        console.error("[Login] OTP error:", otpError.message, otpError);

        // Treat ALL OTP errors as failures -- don't show "check your email"
        // when the request actually failed
        if (otpError.message?.includes("rate limit")) {
          setError(
            "\u05E0\u05E9\u05DC\u05D7\u05D5 \u05D9\u05D5\u05EA\u05E8 \u05DE\u05D3\u05D9 \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC\u05D9\u05DD. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1 \u05D1\u05E2\u05D5\u05D3 \u05DB\u05DE\u05D4 \u05D3\u05E7\u05D5\u05EA."
          );
        } else {
          const devInfo =
            process.env.NODE_ENV === "development"
              ? ` (${otpError.message})`
              : "";
          setError(
            `\u05E9\u05DC\u05D9\u05D7\u05EA \u05D4\u05E7\u05D9\u05E9\u05D5\u05E8 \u05E0\u05DB\u05E9\u05DC\u05D4. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1.${devInfo}`
          );
        }
        return;
      }

      setEmailSent(true);
    } catch {
      setError(
        "\u05D0\u05D9\u05E8\u05E2\u05D4 \u05E9\u05D2\u05D9\u05D0\u05D4. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1."
      );
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

  // ---- Email input form (Magic Link) ----
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label
          htmlFor="magic-email"
          className="text-sm font-medium text-megido-text-body"
        >
          {"\u05D4\u05DB\u05E0\u05E1 \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC"}
        </label>
        <Input
          id="magic-email"
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
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            {"\u05E9\u05D5\u05DC\u05D7 \u05E7\u05D9\u05E9\u05D5\u05E8..."}
          </span>
        ) : (
          "\u05E9\u05DC\u05D7 \u05E7\u05D9\u05E9\u05D5\u05E8 \u05DB\u05E0\u05D9\u05E1\u05D4"
        )}
      </Button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Password form (login + signup)
// ---------------------------------------------------------------------------

function PasswordForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [signUpSuccess, setSignUpSuccess] = useState(false);
  const searchParams = useSearchParams();

  // Show error from callback redirect (shared across tabs)
  useEffect(() => {
    const errorParam = searchParams.get("error");
    if (errorParam && ERROR_MESSAGES[errorParam]) {
      setError(ERROR_MESSAGES[errorParam]);
    }
  }, [searchParams]);

  /** Validate email format. Returns error string or empty string. */
  function validateEmail(value: string): string {
    if (!value) {
      return "\u05E0\u05D0 \u05DC\u05D4\u05D6\u05D9\u05DF \u05DB\u05EA\u05D5\u05D1\u05EA \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC";
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      return "\u05DB\u05EA\u05D5\u05D1\u05EA \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC \u05DC\u05D0 \u05EA\u05E7\u05D9\u05E0\u05D4";
    }
    return "";
  }

  async function handleLogin(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const trimmedEmail = email.trim().toLowerCase();
    const emailError = validateEmail(trimmedEmail);
    if (emailError) {
      setError(emailError);
      return;
    }

    if (!password) {
      setError("\u05E0\u05D0 \u05DC\u05D4\u05D6\u05D9\u05DF \u05E1\u05D9\u05E1\u05DE\u05D4");
      return;
    }

    setIsLoading(true);

    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: trimmedEmail,
        password,
      });

      if (signInError) {
        console.error("[Login] Password error:", signInError.message, signInError);
        const devInfo =
          process.env.NODE_ENV === "development"
            ? ` (${signInError.message})`
            : "";
        setError(
          `\u05D0\u05D9\u05DE\u05D9\u05D9\u05DC \u05D0\u05D5 \u05E1\u05D9\u05E1\u05DE\u05D4 \u05E9\u05D2\u05D5\u05D9\u05D9\u05DD${devInfo}`
        );
        return;
      }

      // Password login creates session immediately -- redirect to /management
      window.location.href = "/management";
    } catch {
      setError(
        "\u05D0\u05D9\u05E8\u05E2\u05D4 \u05E9\u05D2\u05D9\u05D0\u05D4. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1."
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSignUp(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const trimmedEmail = email.trim().toLowerCase();
    const emailError = validateEmail(trimmedEmail);
    if (emailError) {
      setError(emailError);
      return;
    }

    if (password.length < 8) {
      setError(
        "\u05D4\u05E1\u05D9\u05E1\u05DE\u05D4 \u05D7\u05D9\u05D9\u05D1\u05EA \u05DC\u05D4\u05DB\u05D9\u05DC \u05DC\u05E4\u05D7\u05D5\u05EA 8 \u05EA\u05D5\u05D5\u05D9\u05DD"
      );
      return;
    }

    if (password !== confirmPassword) {
      setError(
        "\u05D4\u05E1\u05D9\u05E1\u05DE\u05D0\u05D5\u05EA \u05DC\u05D0 \u05EA\u05D5\u05D0\u05DE\u05D5\u05EA"
      );
      return;
    }

    setIsLoading(true);

    try {
      const { error: signUpError } = await supabase.auth.signUp({
        email: trimmedEmail,
        password,
      });

      if (signUpError) {
        console.error("[Login] SignUp error:", signUpError.message, signUpError);

        if (signUpError.message?.includes("already registered")) {
          setError(
            "\u05D0\u05D9\u05DE\u05D9\u05D9\u05DC \u05D6\u05D4 \u05DB\u05D1\u05E8 \u05E8\u05E9\u05D5\u05DD. \u05E0\u05E1\u05D4 \u05DC\u05D4\u05EA\u05D7\u05D1\u05E8."
          );
        } else {
          const devInfo =
            process.env.NODE_ENV === "development"
              ? ` (${signUpError.message})`
              : "";
          setError(
            `\u05D4\u05E8\u05E9\u05DE\u05D4 \u05E0\u05DB\u05E9\u05DC\u05D4. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1.${devInfo}`
          );
        }
        return;
      }

      setSignUpSuccess(true);
    } catch {
      setError(
        "\u05D0\u05D9\u05E8\u05E2\u05D4 \u05E9\u05D2\u05D9\u05D0\u05D4. \u05E0\u05E1\u05D4 \u05E9\u05D5\u05D1."
      );
    } finally {
      setIsLoading(false);
    }
  }

  // ---- Sign-up success state ----
  if (signUpSuccess) {
    return (
      <div className="space-y-4 text-center" dir="rtl">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <Mail className="h-8 w-8 text-green-600" />
        </div>
        <h3 className="text-lg font-semibold text-megido-text-heading">
          {"\u05D4\u05D4\u05E8\u05E9\u05DE\u05D4 \u05D4\u05E6\u05DC\u05D9\u05D7\u05D4!"}
        </h3>
        <p className="text-sm text-megido-text-muted">
          {"\u05E9\u05DC\u05D7\u05E0\u05D5 \u05D0\u05D9\u05DE\u05D9\u05D9\u05DC \u05D0\u05D9\u05DE\u05D5\u05EA \u05DC-"}
          <span className="font-medium text-megido-text-body" dir="ltr">
            {email}
          </span>
        </p>
        <p className="text-xs text-megido-text-muted">
          {"\u05D0\u05E9\u05E8 \u05D0\u05EA \u05D4\u05D0\u05D9\u05DE\u05D9\u05D9\u05DC \u05D5\u05D7\u05D6\u05D5\u05E8 \u05DC\u05D4\u05EA\u05D7\u05D1\u05E8"}
        </p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => {
            setSignUpSuccess(false);
            setIsSignUp(false);
            setPassword("");
            setConfirmPassword("");
          }}
        >
          {"\u05D7\u05D6\u05E8\u05D4 \u05DC\u05D4\u05EA\u05D7\u05D1\u05E8\u05D5\u05EA"}
        </Button>
      </div>
    );
  }

  // ---- Sign-up form ----
  if (isSignUp) {
    return (
      <form onSubmit={handleSignUp} className="space-y-4">
        <div className="space-y-2">
          <label
            htmlFor="signup-email"
            className="text-sm font-medium text-megido-text-body"
          >
            {"\u05D0\u05D9\u05DE\u05D9\u05D9\u05DC"}
          </label>
          <Input
            id="signup-email"
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

        <div className="space-y-2">
          <label
            htmlFor="signup-password"
            className="text-sm font-medium text-megido-text-body"
          >
            {"\u05E1\u05D9\u05E1\u05DE\u05D4"}
          </label>
          <Input
            id="signup-password"
            type="password"
            placeholder="\u05DC\u05E4\u05D7\u05D5\u05EA 8 \u05EA\u05D5\u05D5\u05D9\u05DD"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            dir="ltr"
            className="text-left"
            autoComplete="new-password"
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="signup-confirm-password"
            className="text-sm font-medium text-megido-text-body"
          >
            {"\u05D0\u05D9\u05DE\u05D5\u05EA \u05E1\u05D9\u05E1\u05DE\u05D4"}
          </label>
          <Input
            id="signup-confirm-password"
            type="password"
            placeholder="\u05D4\u05D6\u05DF \u05E1\u05D9\u05E1\u05DE\u05D4 \u05E9\u05D5\u05D1"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            dir="ltr"
            className="text-left"
            autoComplete="new-password"
          />
        </div>

        <p className="text-xs text-megido-text-muted">
          {"\u05D4\u05E1\u05D9\u05E1\u05DE\u05D4 \u05D7\u05D9\u05D9\u05D1\u05EA \u05DC\u05D4\u05DB\u05D9\u05DC \u05DC\u05E4\u05D7\u05D5\u05EA 8 \u05EA\u05D5\u05D5\u05D9\u05DD"}
        </p>

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
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              {"\u05E0\u05E8\u05E9\u05DD..."}
            </span>
          ) : (
            "\u05D4\u05E8\u05E9\u05DE\u05D4"
          )}
        </Button>

        <div className="text-center">
          <button
            type="button"
            className="text-sm text-megido-primary hover:underline"
            onClick={() => {
              setIsSignUp(false);
              setError("");
              setConfirmPassword("");
            }}
          >
            {"\u05D9\u05E9 \u05DC\u05DA \u05DB\u05D1\u05E8 \u05D7\u05E9\u05D1\u05D5\u05DF? \u05D4\u05EA\u05D7\u05D1\u05E8"}
          </button>
        </div>
      </form>
    );
  }

  // ---- Password login form ----
  return (
    <form onSubmit={handleLogin} className="space-y-4">
      <div className="space-y-2">
        <label
          htmlFor="password-email"
          className="text-sm font-medium text-megido-text-body"
        >
          {"\u05D0\u05D9\u05DE\u05D9\u05D9\u05DC"}
        </label>
        <Input
          id="password-email"
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

      <div className="space-y-2">
        <label
          htmlFor="password-input"
          className="text-sm font-medium text-megido-text-body"
        >
          {"\u05E1\u05D9\u05E1\u05DE\u05D4"}
        </label>
        <Input
          id="password-input"
          type="password"
          placeholder="\u05D4\u05D6\u05DF \u05E1\u05D9\u05E1\u05DE\u05D4"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          dir="ltr"
          className="text-left"
          autoComplete="current-password"
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
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            {"\u05DE\u05EA\u05D7\u05D1\u05E8..."}
          </span>
        ) : (
          "\u05DB\u05E0\u05D9\u05E1\u05D4 \u05E2\u05DD \u05E1\u05D9\u05E1\u05DE\u05D4"
        )}
      </Button>

      <div className="text-center">
        <button
          type="button"
          className="text-sm text-megido-primary hover:underline"
          onClick={() => {
            setIsSignUp(true);
            setError("");
          }}
        >
          {"\u05D0\u05D9\u05DF \u05DC\u05DA \u05D7\u05E9\u05D1\u05D5\u05DF? \u05D4\u05E8\u05E9\u05DD \u05E2\u05DB\u05E9\u05D9\u05D5"}
        </button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Combined login form with tabs
// ---------------------------------------------------------------------------

function LoginForm() {
  return (
    <Tabs defaultValue="magic-link" dir="rtl" className="w-full">
      <TabsList className="w-full">
        <TabsTrigger value="magic-link" className="flex-1 gap-1.5">
          <Mail className="h-4 w-4" />
          {"\u05E7\u05D9\u05E9\u05D5\u05E8 \u05E7\u05E1\u05DD"}
        </TabsTrigger>
        <TabsTrigger value="password" className="flex-1 gap-1.5">
          <Lock className="h-4 w-4" />
          {"\u05E1\u05D9\u05E1\u05DE\u05D4"}
        </TabsTrigger>
      </TabsList>

      <TabsContent value="magic-link" className="mt-4">
        <Suspense fallback={null}>
          <MagicLinkForm />
        </Suspense>
      </TabsContent>

      <TabsContent value="password" className="mt-4">
        <Suspense fallback={null}>
          <PasswordForm />
        </Suspense>
      </TabsContent>
    </Tabs>
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
          <LoginForm />
        </CardContent>
      </Card>
    </div>
  );
}
