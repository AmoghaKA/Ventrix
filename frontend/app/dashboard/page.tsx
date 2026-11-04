"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  CircleCheck,
  Clock,
  FileText,
  PlusCircle,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { AnalysisTable } from "@/components/dashboard/analysis-table";
import { PageHeader } from "@/components/dashboard/page-header";
import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import { buttonStyles } from "@/components/ui/button";
import { listAnalyses, type AnalysisRecord } from "@/lib/api";

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

  const total = analyses.length;
  const completed = analyses.filter(
    (analysis) => analysis.status === "completed"
  ).length;
  const pending = total - completed;
  const highRisk = analyses.filter((analysis) =>
    /high|critical/i.test(analysis.overall_assessment ?? "")
  ).length;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Overview"
        title="Investor dashboard"
        description="Monitor diligence coverage, review live analysis activity, and move every startup toward a confident decision."
        actions={
          <>
            <Link
              href="/dashboard/reports"
              className={buttonStyles({
                variant: "secondary",
                className: "whitespace-nowrap",
              })}
            >
              <FileText className="mr-2 h-4 w-4 shrink-0" />
              Investor reports
            </Link>
            <Link
              href="/dashboard/new"
              className={buttonStyles({ className: "whitespace-nowrap" })}
            >
              <PlusCircle className="mr-2 h-4 w-4 shrink-0" />
              New due diligence
            </Link>
          </>
        }
      />

      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
          <p className="text-xs text-slate-600">{error}</p>
        </div>
      )}

      <section className="animate-fade-up rounded-[26px] bg-gradient-to-br from-blue-200/70 via-slate-200/50 to-violet-200/70 p-px shadow-soft">
        <div className="relative overflow-hidden rounded-[25px] bg-white p-6 sm:p-8">
          <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-blue-200/60 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-32 left-1/3 h-72 w-72 rounded-full bg-violet-200/50 blur-3xl" />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-blue-50/70 via-transparent to-violet-50/60" />
          <div className="bg-grid pointer-events-none absolute inset-0 opacity-40" />

          <div className="relative grid gap-8 lg:grid-cols-[1.6fr_auto] lg:items-center">
            <div>
              <div className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-full border border-blue-200/80 bg-white/80 px-3 py-1.5 text-[11px] font-semibold text-blue-700 shadow-sm backdrop-blur">
                <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                Specialist agents ready
                <span className="ml-1 flex items-center gap-1 text-[10px] font-medium text-emerald-600">
                  <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-emerald-500" />
                  Live
                </span>
              </div>

              <h2 className="mt-5 max-w-xl text-2xl font-bold leading-[1.15] tracking-[-0.03em] text-slate-900 sm:text-[32px]">
                Turn scattered research into{" "}
                <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 bg-clip-text text-transparent">
                  board-ready conviction.
                </span>
              </h2>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-600">
                Run due diligence on real startups and review evidence-backed
                reports from your workspace.
              </p>

              <div className="mt-7 flex flex-wrap items-center gap-2.5">
                <Link
                  href="/dashboard/new"
                  className="inline-flex items-center justify-center rounded-xl bg-gradient-to-b from-blue-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_28px_-14px_rgba(37,99,235,0.95)] ring-1 ring-inset ring-white/20 transition-all hover:-translate-y-0.5 hover:from-blue-500 hover:to-blue-700"
                >
                  Start new analysis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
                <Link
                  href="/dashboard/analysis-history"
                  className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white/80 px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm backdrop-blur transition-colors hover:border-slate-300 hover:bg-white"
                >
                  View activity
                  <ArrowUpRight className="ml-2 h-4 w-4" />
                </Link>
              </div>
            </div>

            <div className="w-full justify-self-stretch rounded-2xl border border-slate-200/80 bg-white/80 p-5 shadow-soft backdrop-blur sm:justify-self-end lg:w-[256px]">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Portfolio health
                </p>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-slate-500 ring-1 ring-slate-200/70">
                  No data
                </span>
              </div>
              <p className="mt-6 text-center text-sm text-slate-500">
                Portfolio scores will appear after completed analyses.
              </p>
            </div>
          </div>
        </div>
      </section>

      <div
        className="grid animate-fade-up gap-4 sm:grid-cols-2 xl:grid-cols-4"
        style={{ animationDelay: "80ms" }}
      >
        <StatCard
          label="Total analyses"
          value={total}
          detail="Across your workspace"
          tone="blue"
          icon={BarChart3}
          spark={[]}
        />
        <StatCard
          label="Completed"
          value={completed}
          detail="Reports ready to review"
          tone="emerald"
          icon={CircleCheck}
          spark={[]}
        />
        <StatCard
          label="In pipeline"
          value={pending}
          detail="Diligence runs in motion"
          tone="amber"
          icon={Clock}
          spark={[]}
        />
        <StatCard
          label="High risk flagged"
          value={highRisk}
          detail="Queued for partner review"
          tone="rose"
          icon={ShieldAlert}
          spark={[]}
        />
      </div>

      <div className="animate-fade-up" style={{ animationDelay: "140ms" }}>
        <ActivityFeed />
      </div>

      <div className="animate-fade-up" style={{ animationDelay: "200ms" }}>
        <AnalysisTable />
      </div>

      {loading && (
        <p className="text-xs text-slate-400">Syncing live workspace data…</p>
      )}
    </div>
  );
}
