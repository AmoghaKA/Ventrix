"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, Search } from "lucide-react";
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
    <div className="overflow-hidden rounded-sm border border-border bg-card shadow-sm">
      <div className="border-b border-border p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-text-primary">
                Startup analyses
              </h2>
              <Badge variant="warning">Demo data</Badge>
            </div>
            <p className="mt-1 text-xs text-text-secondary">
              Search and filter preview records. No real company data is shown.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-secondary" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search startups or industries"
                aria-label="Search startup analyses"
                className="h-10 w-full rounded-sm border border-border bg-white pl-9 pr-3 text-sm text-text-primary placeholder:text-text-secondary/70 focus:border-blue-accent focus:outline-none focus:ring-1 focus:ring-blue-accent/30 sm:w-64"
              />
            </div>

            <select
              value={status}
              onChange={(event) =>
                setStatus(event.target.value as (typeof statusOptions)[number])
              }
              aria-label="Filter by status"
              className="h-10 rounded-sm border border-border bg-white px-3 text-sm text-text-primary focus:border-blue-accent focus:outline-none focus:ring-1 focus:ring-blue-accent/30"
            >
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>

            <select
              value={industry}
              onChange={(event) => setIndustry(event.target.value)}
              aria-label="Filter by industry"
              className="h-10 rounded-sm border border-border bg-white px-3 text-sm text-text-primary focus:border-blue-accent focus:outline-none focus:ring-1 focus:ring-blue-accent/30"
            >
              {industryOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-left">
          <thead>
            <tr className="border-b border-border bg-secondary/50">
              <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                Startup name
              </th>
              <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                Industry
              </th>
              <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                Analysis date
              </th>
              <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                Status
              </th>
              <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                Overall assessment
              </th>
              <th className="px-5 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filtered.map((analysis) => (
              <tr
                key={analysis.id}
                className="transition-colors duration-200 hover:bg-secondary/30"
              >
                <td className="px-5 py-4">
                  <p className="text-sm font-semibold text-text-primary">
                    {analysis.name}
                  </p>
                </td>
                <td className="px-5 py-4 text-sm text-text-secondary">
                  {analysis.industry}
                </td>
                <td className="px-5 py-4 text-sm text-text-secondary">
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
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-accent transition-colors duration-200 hover:text-blue-700"
                  >
                    View report
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </td>
              </tr>
            ))}

            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-12 text-center">
                  <p className="text-sm font-medium text-text-primary">
                    No analyses match your filters
                  </p>
                  <p className="mt-1 text-xs text-text-secondary">
                    Try a different search term, status, or industry.
                  </p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="border-t border-border px-5 py-3">
        <p className="text-xs text-text-secondary">
          Showing {filtered.length} of {demoAnalyses.length} demo analyses
        </p>
      </div>
    </div>
  );
}
