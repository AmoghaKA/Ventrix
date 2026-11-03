import Link from "next/link";
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
import {
  demoActivity,
  demoAnalyses,
  type DemoAssessment,
} from "@/lib/demo-data";

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
  const total = demoAnalyses.length;
  const completed = demoAnalyses.filter(
    (analysis) => analysis.status === "Completed"
  ).length;
  const pending = total - completed;

  const stats = [
    {
      label: "Total analyses",
      value: total,
      detail: "All demo records",
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

      <div className="flex items-start gap-3 rounded-sm border border-warning/30 bg-warning/5 px-4 py-3">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-warning">
            Demo preview data
          </p>
          <p className="mt-1 text-xs leading-relaxed text-text-secondary">
            All counts, startup names, assessments, and activity on this page
            are sample data for UI preview. No real company statistics are
            shown.
          </p>
        </div>
      </div>

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

      <div className="grid gap-6 xl:grid-cols-[1.55fr_1fr]">
        <Card padding="none" className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-text-primary">
                  Recent startup evaluations
                </h2>
                <Badge variant="warning">Demo data</Badge>
              </div>
              <p className="mt-1 text-xs text-text-secondary">
                Latest preview records across the pipeline
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
            {demoAnalyses.slice(0, 4).map((analysis) => (
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
                <div className="flex shrink-0 items-center gap-3">
                  <Badge variant={assessmentVariant[analysis.assessment]}>
                    {analysis.assessment}
                  </Badge>
                  <ArrowRight className="h-4 w-4 text-text-secondary" />
                </div>
              </Link>
            ))}
          </div>
        </Card>

        <div className="space-y-6">
          <div className="rounded-sm border border-blue-200 bg-blue-50/70 p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-accent">
                  Quick action
                </p>
                <h2 className="mt-2 text-base font-semibold text-text-primary">
                  New Due Diligence
                </h2>
                <p className="mt-1 text-xs leading-relaxed text-text-secondary">
                  Submit a company website and start a new analysis record.
                </p>
              </div>
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm bg-white text-blue-accent">
                <PlusCircle className="h-4 w-4" />
              </span>
            </div>
            <Link
              href="/dashboard/new"
              className={buttonStyles({
                size: "sm",
                className: "mt-4 w-full",
              })}
            >
              Start Due Diligence
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <Card className="p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-text-primary">
                Recent activity
              </h2>
              <Badge variant="warning">Demo data</Badge>
            </div>
            <ol className="mt-4 space-y-4">
              {demoActivity.map((activity) => {
                const Icon = activityIcon[activity.kind];
                return (
                  <li key={activity.id} className="flex gap-3">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-sm bg-secondary text-text-secondary">
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-medium leading-relaxed text-text-primary">
                        {activity.title}
                      </p>
                      <p className="mt-0.5 text-[11px] leading-relaxed text-text-secondary">
                        {activity.detail}
                      </p>
                      <p className="mt-1 text-[10px] uppercase tracking-wider text-text-secondary/80">
                        {activity.time}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </Card>
        </div>
      </div>

      <AnalysisTable />
    </div>
  );
}
