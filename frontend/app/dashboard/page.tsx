"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Bot,
  CircleCheck,
  Clock,
  FileCheck2,
  FileText,
  PlusCircle,
} from "lucide-react";
import { AnalysisTable } from "@/components/dashboard/analysis-table";
import { Badge } from "@/components/ui/badge";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { listAnalyses, type AnalysisRecord } from "@/lib/api";
import { demoActivity, demoAnalyses, type DemoAssessment } from "@/lib/demo-data";

const assessmentVariant: Record<
  DemoAssessment,
  "success" | "warning" | "critical"
> = {
  Strong: "success",
  Moderate: "warning",
  "High risk": "critical",
};

const activityIcon = {
  report: FileText,
  agent: Bot,
  evidence: FileCheck2,
  queue: Clock,
};

export default function DashboardPage() {
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAnalyses()
      .then(setAnalyses)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load analyses")
      )
      .finally(() => setLoading(false));
  }, []);

  const total = analyses.length || demoAnalyses.length;
  const completed = analyses.length
    ? analyses.filter((analysis) => analysis.status === "completed").length
    : demoAnalyses.filter((analysis) => analysis.status === "Completed").length;
  const pending = total - completed;

  const stats = [
    {
      label: "Total analyses",
      value: total,
      detail: analyses.length ? "Backend records" : "Demo preview",
      icon: BarChart3,
    },
    {
      label: "Completed analyses",
      value: completed,
      detail: "Reports ready for review",
      icon: CircleCheck,
    },
    {
      label: "Pending analyses",
      value: pending,
      detail: "Queued or in progress",
      icon: Clock,
    },
  ];

  const recent = analyses.length ? analyses.slice(0, 4) : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-accent">
            Overview
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-text-primary md:text-3xl">
            Investor dashboard
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-text-secondary">
            Monitor diligence coverage, review recent evaluations, and start a
            new analysis from one workspace.
          </p>
        </div>
        <Link
          href="/dashboard/new"
          className={buttonStyles({ className: "w-full sm:w-auto" })}
        >
          <PlusCircle className="h-4 w-4" />
          New Due Diligence
        </Link>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-sm border border-warning/30 bg-warning/5 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <p className="text-xs text-text-secondary">{error}</p>
        </div>
      )}

      {loading && <p className="text-sm text-text-secondary">Loading dashboard...</p>}

      <div className="grid gap-4 sm:grid-cols-3">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-text-secondary">
                    {stat.label}
                  </p>
                  <p className="mt-2 text-3xl font-bold tracking-tight text-text-primary">
                    {stat.value}
                  </p>
                  <p className="mt-1 text-[11px] text-text-secondary">
                    {stat.detail}
                  </p>
                </div>
                <span className="flex h-9 w-9 items-center justify-center rounded-sm bg-blue-50 text-blue-accent">
                  <Icon className="h-4 w-4" />
                </span>
              </div>
            </Card>
          );
        })}
      </div>

      <Card padding="none" className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-text-primary">
              Recent startup evaluations
            </h2>
            <p className="mt-1 text-xs text-text-secondary">
              {analyses.length ? "Backend records" : "Demo preview records"}
            </p>
          </div>
          <Link
            href="/dashboard/analysis-history"
            className="hidden items-center gap-1 text-xs font-medium text-blue-accent hover:underline sm:inline-flex"
          >
            View all
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="divide-y divide-border">
          {(recent
            ? recent.map((analysis) => (
                <Link
                  key={analysis.id}
                  href={`/dashboard/analyses/${analysis.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-4 transition-colors duration-200 hover:bg-secondary/30"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm bg-blue-50 text-sm font-bold text-blue-accent">
                      {analysis.startup_name.charAt(0)}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-text-primary">
                        {analysis.startup_name}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-text-secondary">
                        {analysis.industry || "Unknown industry"} · {analysis.status}
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-text-secondary" />
                </Link>
              ))
            : demoAnalyses.slice(0, 4).map((analysis) => (
                <Link
                  key={analysis.id}
                  href={`/dashboard/analyses/${analysis.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-4 transition-colors duration-200 hover:bg-secondary/30"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm bg-blue-50 text-sm font-bold text-blue-accent">
                      {analysis.name.charAt(0)}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-text-primary">
                        {analysis.name}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-text-secondary">
                        {analysis.industry} · {analysis.date}
                      </p>
                    </div>
                  </div>
                  <Badge variant={assessmentVariant[analysis.assessment]}>
                    {analysis.assessment}
                  </Badge>
                </Link>
              )))}
        </div>
      </Card>

      <AnalysisTable />
    </div>
  );
}
