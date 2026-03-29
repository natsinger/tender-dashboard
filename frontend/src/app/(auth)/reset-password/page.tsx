/**
 * Reset password page -- allows users to set a new password after
 * clicking the recovery link in their email.
 *
 * Flow:
 * 1. User clicks "שכחת סיסמה?" on login page → resetPasswordForEmail sends email
 * 2. User clicks link → /auth/callback exchanges code with type=recovery
 * 3. Callback redirects here with an active session
 * 4. User enters new password → updateUser({ password }) saves it
 * 5. Redirect to /management
 */
"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Building2, Lock, Loader2, CheckCircle2 } from "lucide-react";
import { supabase } from "@/lib/supabase/client";

export default function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("הסיסמה חייבת להכיל לפחות 8 תווים");
      return;
    }

    if (password !== confirmPassword) {
      setError("הסיסמאות לא תואמות");
      return;
    }

    setIsLoading(true);

    try {
      const { error: updateError } = await supabase.auth.updateUser({
        password,
      });

      if (updateError) {
        console.error("[ResetPassword] Error:", updateError.message);
        setError("עדכון הסיסמה נכשל. נסה שוב.");
        return;
      }

      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/management";
      }, 2000);
    } catch {
      setError("אירעה שגיאה. נסה שוב.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-megido-bg-main p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-megido-primary-light">
            <Building2 className="h-8 w-8 text-megido-primary" />
          </div>
          <CardTitle className="text-2xl font-bold text-megido-text-heading">
            {"עדכון סיסמה"}
          </CardTitle>
          <CardDescription className="text-megido-text-muted">
            {"הזן סיסמה חדשה לחשבון שלך"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {success ? (
            <div className="space-y-4 text-center" dir="rtl">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-megido-text-heading">
                {"הסיסמה עודכנה בהצלחה!"}
              </h3>
              <p className="text-sm text-megido-text-muted">
                {"מעביר אותך למערכת..."}
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" dir="rtl">
              <div className="space-y-2">
                <label
                  htmlFor="new-password"
                  className="text-sm font-medium text-megido-text-body"
                >
                  {"סיסמה חדשה"}
                </label>
                <div className="relative">
                  <Lock className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-megido-text-muted" />
                  <Input
                    id="new-password"
                    type="password"
                    placeholder="לפחות 8 תווים"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    dir="ltr"
                    className="pr-10 text-left"
                    autoComplete="new-password"
                    autoFocus
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="confirm-new-password"
                  className="text-sm font-medium text-megido-text-body"
                >
                  {"אימות סיסמה"}
                </label>
                <Input
                  id="confirm-new-password"
                  type="password"
                  placeholder="הזן סיסמה שוב"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  dir="ltr"
                  className="text-left"
                  autoComplete="new-password"
                />
              </div>

              <p className="text-xs text-megido-text-muted">
                {"הסיסמה חייבת להכיל לפחות 8 תווים"}
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
                    {"מעדכן..."}
                  </span>
                ) : (
                  "עדכן סיסמה"
                )}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
