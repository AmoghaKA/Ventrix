import type { Metadata } from "next";
import { AnalysisTable } from "@/components/dashboard/analysis-table";
import { PageHeader } from "@/components/dashboard/page-header";

export const metadata: Metadata = {
  title: "Analysis History — Ventrix",
  description: "Browse every startup analysis in your Ventrix workspace.",
};

export default function AnalysisHistoryPage() {
  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Workspace"
        title="Analysis history"
        description="Browse every analysis record in your workspace. Browse every analysis record in your workspace."
      />

      <AnalysisTable />
    </div>
  );
}
