"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ArrowRight,
  ChevronDown,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  demoAnalyses,
  type DemoAnalysisStatus,
  type DemoAssessment,
} from "@/lib/demo-data";

const statusVariant: Record<
  DemoAnalysisStatus,
  "success" | "warning" | "default"
> = {
  Completed: "success",
  "In progress": "warning",
  Pending: "default",
};

const assessmentVariant: Record<
  DemoAssessment,
  "success" | "warning" | "critical"
> = {
  Strong: "success",
  Moderate: "warning",
  "High risk": "critical",
};

const statusOptions: ("All statuses" | DemoAnalysisStatus)[] = [
  "All statuses",
  "Completed",
  "In progress",
  "Pending",
];

const industryOptions = [
  "All industries",
  ...Array.from(new Set(demoAnalyses.map((analysis) => analysis.industry))),
];

const avatarGradients = [
  "from-blue-500 to-indigo-600",
  "from-emerald-500 to-teal-600",
  "from-violet-500 to-purple-600",
  "from-amber-500 to-orange-600",
  "from-rose-500 to-pink-600",
  "from-cyan-500 to-blue-600",
];

export function AnalysisTable() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<(typeof statusOptions)[number]>(
    "All statuses"
  );
  const [industry, setIndustry] = useState("All industries");

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return demoAnalyses.filter((analysis) => {
      const matchesQuery =
        !normalizedQuery ||
        analysis.name.toLowerCase().includes(normalizedQuery) ||
        analysis.industry.toLowerCase().includes(normalizedQuery);

      const matchesStatus =
        status === "All statuses" || analysis.status === status;
      const matchesIndustry =
        industry === "All industries" || analysis.industry === industry;

      return matchesQuery && matchesStatus && matchesIndustry;
    });
  }, [query, status, industry]);

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-soft">
      <div className="border-b border-slate-100 p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold tracking-tight text-slate-900">
                Startup analyses
              </h2>
              <Badge variant="warning">Demo data</Badge>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Search and filter preview records. No real company data is shown.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search startups or industries"
                aria-label="Search startup analyses"
                className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-900 shadow-sm transition-colors placeholder:text-slate-400 hover:border-slate-300 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10 sm:w-60"
              />
            </div>

            <div className="relative">
              <SlidersHorizontal className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as (typeof statusOptions)[number])
                }
                aria-label="Filter by status"
                className="h-10 w-full appearance-none rounded-xl border border-slate-200 bg-white pl-9 pr-8 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:border-slate-300 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10"
              >
                {statusOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            </div>

            <div className="relative">
              <select
                value={industry}
                onChange={(event) => setIndustry(event.target.value)}
                aria-label="Filter by industry"
                className="h-10 w-full appearance-none rounded-xl border border-slate-200 bg-white px-3.5 pr-8 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:border-slate-300 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10"
              >
                {industryOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            </div>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-left">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/70">
              {[
                "Startup",
                "Industry",
                "Analysis date",
                "Status",
                "Overall assessment",
              ].map((heading) => (
                <th
                  key={heading}
                  className="px-5 py-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500"
                >
                  {heading}
                </th>
              ))}
              <th className="px-5 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((analysis, index) => (
              <tr
                key={analysis.id}
                className="group transition-colors duration-150 hover:bg-slate-50/80"
              >
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${
                        avatarGradients[index % avatarGradients.length]
                      } text-xs font-bold text-white shadow-sm`}
                    >
                      {analysis.name.charAt(0)}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {analysis.name}
                      </p>
                      <p className="mt-0.5 truncate text-[11px] text-slate-500">
                        {analysis.country}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-4">
                  <span className="inline-flex rounded-lg bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-600">
                    {analysis.industry}
                  </span>
                </td>
                <td className="px-5 py-4 text-xs text-slate-500">
                  {analysis.date}
                </td>
                <td className="px-5 py-4">
                  <Badge variant={statusVariant[analysis.status]}>
                    {analysis.status}
                  </Badge>
                </td>
                <td className="px-5 py-4">
                  <Badge variant={assessmentVariant[analysis.assessment]}>
                    {analysis.assessment}
                  </Badge>
                </td>
                <td className="px-5 py-4 text-right">
                  <Link
                    href={`/dashboard/analyses/${analysis.id}`}
                    className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-blue-600 transition-colors hover:bg-blue-50"
                  >
                    View report
                    <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </td>
              </tr>
            ))}

            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-16 text-center">
                  <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
                    <Search className="h-5 w-5" />
                  </div>
                  <p className="mt-3 text-sm font-semibold text-slate-800">
                    No analyses match your filters
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Try a different search term, status, or industry.
                  </p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-2 border-t border-slate-100 px-5 py-3 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <p>
          Showing{" "}
          <span className="font-semibold text-slate-700">{filtered.length}</span>{" "}
          of {demoAnalyses.length} analyses
        </p>
        <p className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Synced just now
        </p>
      </div>
    </div>
  );
}
