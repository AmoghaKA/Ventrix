"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/components/auth/auth-provider";
import { signUp as signUpService, validateEmail, validatePassword } from "@/lib/auth";

export default function SignUpPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [fullNameError, setFullNameError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!authLoading && user) {
      router.replace("/dashboard");
    }
  }, [authLoading, user, router]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);
    setFullNameError(null);
    setEmailError(null);
    setPasswordError(null);
    setConfirmError(null);

    let hasError = false;
    if (!fullName.trim()) {
      setFullNameError("Full name is required.");
      hasError = true;
    }
    if (!validateEmail(email)) {
      setEmailError("Please enter a valid email address.");
      hasError = true;
    }
    const pwError = validatePassword(password);
    if (pwError) {
      setPasswordError(pwError);
      hasError = true;
    }
    if (password !== confirmPassword) {
      setConfirmError("Passwords do not match.");
      hasError = true;
    }
    if (hasError) return;

    setSubmitting(true);
    try {
      const data = await signUpService({
        fullName: fullName.trim(),
        email: email.trim(),
        password,
      });

      // If Supabase returns a session, email verification is disabled -> go to dashboard.
      if (data.session) {
        router.push("/dashboard");
        return;
      }

      // Otherwise email verification is required.
      setSuccessMessage(
        "Account created. Please check your email to verify your account before signing in."
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sign up failed.";
      if (/already registered|already exists|duplicate/i.test(message)) {
        setFormError("An account with this email already exists. Please sign in instead.");
      } else {
        setFormError(message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-blue-accent" />
      </div>
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
            Create your account
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            Start your VENTRIX due diligence workspace
          </p>
        </div>

        <Card padding="lg">
          <CardTitle className="mb-1">Sign up</CardTitle>
          <CardDescription className="mb-6">
            Full name, email, and a strong password.
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
              label="Full name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Investor"
              error={fullNameError ?? undefined}
              autoComplete="name"
              required
            />
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
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              error={passwordError ?? undefined}
              autoComplete="new-password"
              required
            />
            <Input
              label="Confirm password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat password"
              error={confirmError ?? undefined}
              autoComplete="new-password"
              required
            />

            <p className="text-[11px] text-text-secondary">
              Password must be at least 8 characters and include uppercase, lowercase, and a number.
            </p>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating account…
                </>
              ) : (
                "Create account"
              )}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-text-secondary">
            Already have an account?{" "}
            <Link href="/sign-in" className="font-semibold text-blue-accent hover:underline">
              Sign in
            </Link>
          </p>
        </Card>
      </div>
    </main>
  );
}