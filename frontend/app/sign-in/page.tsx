"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/components/auth/auth-provider";
import { signIn as signInService } from "@/lib/auth";
import { validateEmail } from "@/lib/auth";

export default function SignInPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Redirect already-authenticated users away from the sign in page.
  useEffect(() => {
    if (!authLoading && user) {
      router.replace("/dashboard");
    }
  }, [authLoading, user, router]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setEmailError(null);
    setPasswordError(null);

    if (!validateEmail(email)) {
      setEmailError("Please enter a valid email address.");
      return;
    }
    if (!password) {
      setPasswordError("Password is required.");
      return;
    }

    setSubmitting(true);
    try {
      await signInService({ email, password });
      router.push("/dashboard");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sign in failed.";
      if (/invalid login credentials/i.test(message)) {
        setFormError("Invalid email or password. Please try again.");
      } else if (/email not confirmed/i.test(message)) {
        setFormError("Please verify your email before signing in.");
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
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            Sign in to your Ventrix workspace
          </p>
        </div>

        <Card padding="lg">
          <CardTitle className="mb-1">Sign in</CardTitle>
          <CardDescription className="mb-6">
            Use your email and password to continue.
          </CardDescription>

          {formError && (
            <div className="mb-4 flex items-start gap-2 rounded-xl border border-critical/30 bg-critical/5 px-3 py-2.5">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-critical" />
              <p className="text-xs text-critical">{formError}</p>
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
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              error={passwordError ?? undefined}
              autoComplete="current-password"
              required
            />

            <div className="flex items-center justify-between text-xs">
              <Link
                href="/forgot-password"
                className="font-medium text-blue-accent hover:underline"
              >
                Forgot password?
              </Link>
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-text-secondary">
            Don&apos;t have an account?{" "}
            <Link href="/sign-up" className="font-semibold text-blue-accent hover:underline">
              Create one
            </Link>
          </p>
        </Card>
      </div>
    </main>
  );
}