"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { sendPasswordResetEmail } from "@/lib/auth";
import { validateEmail } from "@/lib/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);
    setEmailError(null);

    if (!validateEmail(email)) {
      setEmailError("Please enter a valid email address.");
      return;
    }

    setSubmitting(true);
    try {
      const redirectTo = `${window.location.origin}/reset-password`;
      await sendPasswordResetEmail(email, redirectTo);
      setSuccessMessage(
        "If an account exists for this email, a password reset link has been sent. Please check your inbox."
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to send reset email.";
      setFormError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-accent shadow-sm">
            <span className="text-sm font-bold tracking-widest text-white">V</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Reset your password
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            We&apos;ll email you a link to choose a new password
          </p>
        </div>

        <Card padding="lg">
          <CardTitle className="mb-1">Forgot password</CardTitle>
          <CardDescription className="mb-6">
            Enter the email associated with your account.
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
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@firm.com"
              error={emailError ?? undefined}
              autoComplete="email"
              required
            />

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending…
                </>
              ) : (
                "Send reset link"
              )}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-text-secondary">
            Remembered it?{" "}
            <Link href="/sign-in" className="font-semibold text-blue-accent hover:underline">
              Back to sign in
            </Link>
          </p>
        </Card>
      </div>
    </main>
  );
}