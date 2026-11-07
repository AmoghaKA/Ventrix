"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { supabase } from "@/lib/supabase";
import { updatePassword, validatePassword } from "@/lib/auth";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let mounted = true;

    const { data: subscription } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY" || session) {
        if (mounted) setReady(true);
      }
    });

    // Supabase puts the recovery tokens in the URL hash; the client detects
    // them automatically (detectSessionInUrl). Give it a moment to resolve.
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      if (data.session) setReady(true);
      setChecking(false);
    });

    // Fallback: if no session after a short delay, stop the spinner.
    const timer = setTimeout(() => {
      if (mounted) setChecking(false);
    }, 2000);

    return () => {
      mounted = false;
      subscription.subscription.unsubscribe();
      clearTimeout(timer);
    };
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setPasswordError(null);
    setConfirmError(null);

    const pwError = validatePassword(password);
    if (pwError) {
      setPasswordError(pwError);
      return;
    }
    if (password !== confirmPassword) {
      setConfirmError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await updatePassword(password);
      setSuccessMessage("Your password has been updated. Redirecting to sign in…");
      setTimeout(() => router.push("/sign-in"), 1500);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update password.";
      setFormError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-blue-accent" />
      </div>
    );
  }

  if (!ready) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
        <div className="w-full max-w-md">
          <Card padding="lg">
            <CardTitle className="mb-1">Invalid or expired link</CardTitle>
            <CardDescription className="mb-6">
              This password reset link is invalid or has expired. Please request a new one.
            </CardDescription>
            <Button className="w-full" onClick={() => router.push("/forgot-password")}>
              Request new link
            </Button>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-accent shadow-sm">
            <span className="text-sm font-bold tracking-widest text-white">V</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Set a new password
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            Choose a strong password for your account
          </p>
        </div>

        <Card padding="lg">
          <CardTitle className="mb-1">New password</CardTitle>
          <CardDescription className="mb-6">
            Enter and confirm your new password.
          </CardDescription>

          {formError && (
            <div className="mb-4 flex items-start gap-2 rounded-xl border border-critical/30 bg-critical/5 px-3 py-2.5">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-critical" />
              <p className="text-xs text-critical">{formError}</p>
            </div>
          )}

          {successMessage && (
            <div className="mb-4 flex items-start gap-2 rounded-xl border border-success/30 bg-success/5 px-3 py-2.5">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
              <p className="text-xs text-success">{successMessage}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="New password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              error={passwordError ?? undefined}
              autoComplete="new-password"
              required
            />
            <Input
              label="Confirm new password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat password"
              error={confirmError ?? undefined}
              autoComplete="new-password"
              required
            />

            <Button type="submit" className="w-full" disabled={submitting || !!successMessage}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Updating…
                </>
              ) : (
                "Update password"
              )}
            </Button>
          </form>
        </Card>
      </div>
    </main>
  );
}