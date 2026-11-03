import type { Metadata } from "next";
import { AnalysisTable } from "@/components/dashboard/analysis-table";

export const metadata: Metadata = {
  title: "Analysis History — Ventrix",
  description: "Browse every startup analysis in your Ventrix workspace.",
};

export default function AnalysisHistoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-blue-accent">
          Workspace
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-text-primary md:text-3xl">
          Analysis History
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-secondary">
          Browse every analysis record in your workspace. The table below uses
          labelled demo data until analysis history is connected.
        </p>
      </div>

      <AnalysisTable />
    </div>
  );
}
