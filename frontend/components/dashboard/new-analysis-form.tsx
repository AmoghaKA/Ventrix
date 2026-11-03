"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createAnalysis } from "@/lib/api";

interface FormValues {
  startupName: string;
  website: string;
  country: string;
  industry: string;
  additionalInformation: string;
}

type FormErrors = Partial<Record<keyof FormValues, string>>;

const industryOptions = [
  "SaaS",
  "Fintech",
  "Digital health",
  "Climate tech",
  "Industrial automation",
  "Enterprise software",
  "Marketplace",
  "Consumer",
  "Biotechnology",
  "Other",
];

const initialValues: FormValues = {
  startupName: "",
  website: "",
  country: "",
  industry: "",
  additionalInformation: "",
};

function normalizeWebsite(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed}`;
}

function validate(values: FormValues): FormErrors {
  const errors: FormErrors = {};

  if (!values.startupName.trim()) {
    errors.startupName = "Startup name is required.";
  }

  if (!values.website.trim()) {
    errors.website = "Company website is required.";
  } else {
    try {
      const url = new URL(normalizeWebsite(values.website));
      if (!["http:", "https:"].includes(url.protocol) || !url.hostname.includes(".")) {
        throw new Error("Invalid URL");
      }
    } catch {
      errors.website = "Enter a valid website URL (e.g. https://example.com).";
    }
  }

  return errors;
}

export function NewAnalysisForm() {
  const router = useRouter();
  const [values, setValues] = useState<FormValues>(initialValues);
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const updateValue = (field: keyof FormValues, value: string) => {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isSubmitting || submitted) return;

    const nextErrors = validate(values);
    setErrors(nextErrors);
    setServerError(null);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);

    try {
      const analysis = await createAnalysis({
        startup_name: values.startupName.trim(),
        website: normalizeWebsite(values.website),
        country: values.country.trim() || undefined,
        industry: values.industry || undefined,
        additional_information: values.additionalInformation.trim() || undefined,
      });

      if (!analysis?.id) {
        throw new Error("The analysis was created without an ID.");
      }

      setSubmitted(true);
      window.setTimeout(() => {
        router.push(`/dashboard/analyses/${analysis.id}`);
      }, 700);
    } catch (error) {
      const message =
        error instanceof Error && !/failed to fetch/i.test(error.message)
          ? error.message
          : "Could not reach the Ventrix API. Make sure the backend is running and try again.";
      setServerError(message);
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {serverError && (
        <div className="flex items-start gap-3 rounded-sm border border-critical/30 bg-critical/5 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-critical" />
          <div>
            <p className="text-xs font-semibold text-critical">
              Submission failed
            </p>
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">
              {serverError}
            </p>
          </div>
        </div>
      )}

      {submitted && (
        <div className="flex items-start gap-3 rounded-sm border border-success/30 bg-success/5 px-4 py-3">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
          <div>
            <p className="text-xs font-semibold text-success">
              Analysis submitted successfully
            </p>
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">
              Opening the analysis monitoring page…
            </p>
          </div>
        </div>
      )}

      <Input
        id="startup-name"
        label="Startup name *"
        placeholder="e.g. Acme Robotics"
        value={values.startupName}
        onChange={(event) => updateValue("startupName", event.target.value)}
        error={errors.startupName}
        disabled={isSubmitting || submitted}
        autoComplete="organization"
        aria-invalid={Boolean(errors.startupName)}
      />

      <Input
        id="company-website"
        label="Company website *"
        type="url"
        placeholder="https://example.com"
        value={values.website}
        onChange={(event) => updateValue("website", event.target.value)}
        error={errors.website}
        disabled={isSubmitting || submitted}
        autoComplete="url"
        aria-invalid={Boolean(errors.website)}
      />

      <div className="grid gap-5 sm:grid-cols-2">
        <Input
          id="country"
          label="Country"
          placeholder="e.g. United States"
          value={values.country}
          onChange={(event) => updateValue("country", event.target.value)}
          disabled={isSubmitting || submitted}
          autoComplete="country-name"
        />

        <Select
          id="industry"
          label="Industry"
          value={values.industry}
          onChange={(event) => updateValue("industry", event.target.value)}
          disabled={isSubmitting || submitted}
        >
          <option value="">Select an industry</option>
          {industryOptions.map((industry) => (
            <option key={industry} value={industry}>
              {industry}
            </option>
          ))}
        </Select>
      </div>

      <Textarea
        id="additional-information"
        label="Additional company information (optional)"
        placeholder="Add context such as stage, business model, known risks, or areas you want the analysis to focus on."
        rows={5}
        maxLength={5000}
        value={values.additionalInformation}
        onChange={(event) =>
          updateValue("additionalInformation", event.target.value)
        }
        hint={`${values.additionalInformation.length}/5000 characters`}
        disabled={isSubmitting || submitted}
      />

      <div className="flex flex-col gap-3 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-text-secondary">
          Fields marked with * are required.
        </p>
        <Button
          type="submit"
          disabled={isSubmitting || submitted}
          className="w-full sm:w-auto"
        >
          {submitted ? (
            <>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Submitted
            </>
          ) : isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Submitting…
            </>
          ) : (
            <>
              Start Analysis
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
