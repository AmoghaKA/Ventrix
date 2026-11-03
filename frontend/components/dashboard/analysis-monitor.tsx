"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CircleCheck,
  Clock,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getAnalysis, type AnalysisRecord } from "@/lib/api";
import { demoAnalyses, type DemoAnalysisStatus } from "@/lib/demo-data";

type StatusKey = "pending" | "running" | "completed" | "failed";

const statusMeta: Record<
  StatusKey,
  { label: string; variant: "success" | "warning" | "critical" | "default" }
> = {
  pending: { label: "Pending", variant: "warning" },
  running: { label: "In progress", variant: "default" },
  completed: { label: "Completed", variant: "success" },
  failed: { label: "Failed", variant: "critical" },
};

function getAssessmentVariant(
  value: string
): "success" | "warning" | "critical" {
  const normalized = value.toLowerCase();
  if (normalized.includes("high") || normalized.includes("risk")) {
    return "critical";
  }
  if (normalized.includes("moderate") || normalized.includes("caution")) {
    return "warning";
  }
  return "success";
}

const agentNames = [
  "Financial Analysis",
  "Market Intelligence",
  "Legal & Compliance",
  "Evidence Verification",
  "Investor Report",
];

function mapDemoStatus(status: DemoAnalysisStatus): StatusKey {
  if (status === "Completed") return "completed";
  if (status === "In progress") return "running";
  return "pending";
}

function normalizeStatus(status: string): StatusKey {
  const normalized = status.toLowerCase();
  if (["completed", "complete", "done"].includes(normalized)) return "completed";
  if (["running", "in_progress", "processing"].includes(normalized)) {
    return "running";
  }
  if (["failed", "error"].includes(normalized)) return "failed";
  return "pending";
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function AnalysisMonitor({ analysisId }: { analysisId: string }) {
  const demo = useMemo(
    () => demoAnalyses.find((analysis) => analysis.id === analysisId),
    [analysisId]
  );

  const [analysis, setAnalysis] = useState<AnalysisRecord | null>(null);
  const [loading, setLoading] = useState(!demo);
  const [error, setError] = useState<string | null>(null);

  const loadAnalysis = useCallback(async () => {
    try {
      const data = await getAnalysis(analysisId);
      setAnalysis(data);
      setError(null);
    } catch (loadError) {
      const message =
        loadError instanceof Error && !/failed to fetch/i.test(loadError.message)
          ? loadError.message
          : "Could not reach the Ventrix API. Make sure the backend is running and try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    if (demo) return;

    setLoading(true);
    loadAnalysis();
    const interval = window.setInterval(loadAnalysis, 5000);

    return () => window.clearInterval(interval);
  }, [demo, loadAnalysis]);

  const status: StatusKey = demo
    ? mapDemoStatus(demo.status)
    : analysis
      ? normalizeStatus(analysis.status)
      : "pending";

  const companyName = demo?.name ?? analysis?.startup_name ?? "Analysis";
  const website = demo?.website ?? analysis?.website ?? null;
  const industry = demo?.industry ?? analysis?.industry ?? null;
  const country = demo?.country ?? analysis?.country ?? null;
  const submittedAt = demo?.date ?? (analysis ? formatDate(analysis.created_at) : "—");
  const assessment = demo?.assessment ?? analysis?.overall_assessment ?? null;

  const steps = [
    {
      label: "Submitted",
      description: "Company record created",
      done: true,
    },
    {
      label: "Agent analysis",
      description: "Five agents review the company",
      done: status === "running" || status === "completed",
    },
    {
      label: "Evidence verification",
      description: "Claims cross-referenced against sources",
      done: status === "completed",
    },
    {
      label: "Investor report",
      description: "Memo ready for investor review",
      done: status === "completed",
    },
  ];

  const agentState =
    status === "completed"
      ? "Complete"
      : status === "running"
        ? "In progress"
        : status === "failed"
          ? "Failed"
          : "Queued";

  const agentVariant =
    status === "completed"
      ? "success"
      : status === "running"
        ? "warning"
        : status === "failed"
          ? "critical"
          : "default";

  if (loading && !demo) {
    return (
      <div className="space-y-6">
        <div className="h-4 w-32 animate-pulse rounded-sm bg-secondary" />
        <div className="h-8 w-64 animate-pulse rounded-sm bg-secondary" />
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div
              key={item}
              className="h-28 animate-pulse rounded-sm border border-border bg-white"
            />
          ))}
        </div>
        <div className="h-64 animate-pulse rounded-sm border border-border bg-white" />
      </div>
    );
  }

  if (error && !demo) {
    return (
      <div className="space-y-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary transition-colors duration-200 hover:text-blue-accent"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to dashboard
        </Link>

        <Card className="p-6">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm bg-critical/10 text-critical">
              <AlertCircle className="h-5 w-5" />
            </span>
            <div className="flex-1">
              <h1 className="text-base font-semibold text-text-primary">
                Analysis unavailable
              </h1>
              <p className="mt-1 text-sm leading-relaxed text-text-secondary">
                {error}
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-4"
                onClick={loadAnalysis}
              >
                <RefreshCw className="mr-2 h-3.5 w-3.5" />
                Retry request
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary transition-colors duration-200 hover:text-blue-accent"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to dashboard
      </Link>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-accent">
            Analysis monitoring
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-text-primary md:text-3xl">
            {companyName}
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            Analysis ID: <span className="font-medium text-text-primary">{analysisId}</span>
            {demo && (
              <span className="ml-2 text-warning">· Demo data preview</span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={statusMeta[status].variant}>
            {statusMeta[status].label}
          </Badge>
          {assessment && (
            <Badge variant={getAssessmentVariant(assessment)}>
              {assessment}
            </Badge>
          )}
          {demo && <Badge variant="warning">Demo data</Badge>}
        </div>
      </div>

      {status === "failed" && (
        <div className="flex items-start gap-3 rounded-sm border border-critical/30 bg-critical/5 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-critical" />
          <div>
            <p className="text-xs font-semibold text-critical">
              Analysis failed
            </p>
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">
              The analysis could not be completed. Please retry the submission
              or contact support with the analysis ID above.
            </p>
          </div>
        </div>
      )}

      <Card padding="none" className="overflow-hidden">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-text-primary">
            Company snapshot
          </h2>
        </div>
        <dl className="grid gap-0 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border-b border-border px-5 py-4 sm:border-r lg:border-b-0">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
              Website
            </dt>
            <dd className="mt-1.5 truncate text-sm text-text-primary">
              {website ? (
                <a
                  href={website}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-accent hover:underline"
                >
                  {website.replace(/^https?:\/\//, "")}
                </a>
              ) : (
                "Unavailable"
              )}
            </dd>
          </div>
          <div className="border-b border-border px-5 py-4 lg:border-b-0 lg:border-r">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
              Industry
            </dt>
            <dd className="mt-1.5 text-sm text-text-primary">
              {industry || "Unavailable"}
            </dd>
          </div>
          <div className="border-b border-border px-5 py-4 sm:border-b-0 sm:border-r">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
              Country
            </dt>
            <dd className="mt-1.5 text-sm text-text-primary">
              {country || "Unavailable"}
            </dd>
          </div>
          <div className="px-5 py-4">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
              Submitted
            </dt>
            <dd className="mt-1.5 text-sm text-text-primary">{submittedAt}</dd>
          </div>
        </dl>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-text-primary">
            Analysis progress
          </h2>
          <ol className="mt-5 space-y-4">
            {steps.map((step, index) => (
              <li key={step.label} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span
                    className={`flex h-7 w-7 items-center justify-center rounded-full border ${
                      step.done
                        ? "border-blue-accent bg-blue-50 text-blue-accent"
                        : "border-border bg-white text-text-secondary"
                    }`}
                  >
                    {step.done ? (
                      <CircleCheck className="h-4 w-4" />
                    ) : (
                      <span className="text-[10px] font-semibold">
                        {index + 1}
                      </span>
                    )}
                  </span>
                  {index < steps.length - 1 && (
                    <span className="mt-1 h-6 w-px bg-border" />
                  )}
                </div>
                <div className="pb-2">
                  <p className="text-xs font-semibold text-text-primary">
                    {step.label}
                  </p>
                  <p className="mt-0.5 text-xs text-text-secondary">
                    {step.description}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary">
              Agent coverage
            </h2>
            <Badge variant={agentVariant}>{agentState}</Badge>
          </div>
          <ul className="mt-5 space-y-2.5">
            {agentNames.map((agent) => (
              <li
                key={agent}
                className="flex items-center justify-between gap-3 rounded-sm border border-border bg-secondary/30 px-3 py-2.5"
              >
                <span className="text-xs font-medium text-text-primary">
                  {agent}
                </span>
                <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                  {status === "completed" ? (
                    <CircleCheck className="h-3.5 w-3.5 text-success" />
                  ) : status === "running" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-warning" />
                  ) : status === "failed" ? (
                    <AlertCircle className="h-3.5 w-3.5 text-critical" />
                  ) : (
                    <Clock className="h-3.5 w-3.5" />
                  )}
                  {agentState}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="rounded-sm border border-border bg-secondary/50 p-5">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
          Status note
        </p>
        <p className="mt-2 text-xs leading-relaxed text-text-secondary">
          {demo
            ? "This is a demo monitoring view. All company records and assessments shown are sample data, not real startup statistics."
            : status === "completed"
              ? "Analysis complete. Agent outputs and the investor report are available for review."
              : "Your submission has been saved. Agent processing will update this page automatically as the analysis pipeline progresses."}
        </p>
      </div>
    </div>
  );
}
