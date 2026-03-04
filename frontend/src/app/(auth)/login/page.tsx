/**
 * Login page -- email-based authentication with role validation.
 * Stores the user email in a cookie (30-day expiry) and Zustand auth store.
 * Redirects to /management on successful login.
 * Shows error if the email is not in any allowed list.
 */
"use client";

import { useState, useEffect, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Building2 } from "lucide-react";
import { useAuthStore, resolveRole } from "@/stores/auth-store";

// ---------------------------------------------------------------------------
// Inner form component (needs useSearchParams which requires Suspense)
// ---------------------------------------------------------------------------

function LoginForm() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((s) => s.login);

  // Show error from middleware redirect (e.g., unauthorized email in cookie)
  useEffect(() => {
    if (searchParams.get("error") === "unauthorized") {
      setError("אין לך הרשאה לצפות באפליקציה. פנה למנהל המערכת.");
    }
  }, [searchParams]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const trimmedEmail = email.trim().toLowerCase();

    if (!trimmedEmail) {
      setError("נא להזין כתובת אימייל");
      return;
    }

    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setError("כתובת אימייל לא תקינה");
      return;
    }

    // Role validation -- reject emails not in any allowed list
    const role = resolveRole(trimmedEmail);
    if (!role) {
      setError("אין לך הרשאה לצפות באפליקציה. פנה למנהל המערכת.");
      return;
    }

    setIsLoading(true);

    try {
      // Store email in a cookie (expires in 30 days)
      const expiryDate = new Date();
      expiryDate.setDate(expiryDate.getDate() + 30);
      document.cookie = `user_email=${encodeURIComponent(
        trimmedEmail,
      )}; path=/; expires=${expiryDate.toUTCString()}; SameSite=Lax`;

      // Set Zustand auth state
      login(trimmedEmail);

      router.push("/management");
      router.refresh();
    } catch {
      setError("אירעה שגיאה. נסה שוב.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label
          htmlFor="email"
          className="text-sm font-medium text-megido-text-body"
        >
          הכנס אימייל
        </label>
        <Input
          id="email"
          type="email"
          placeholder="name@company.com"
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
        {isLoading ? "מתחבר..." : "כניסה"}
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
            כניסה למערכת
          </CardTitle>
          <CardDescription className="text-megido-text-muted">
            מערכת מודיעין למכרזי קרקע -- MEGIDO
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
