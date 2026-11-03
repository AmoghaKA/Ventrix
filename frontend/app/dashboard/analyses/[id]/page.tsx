import type { Metadata } from "next";
import { AnalysisMonitor } from "@/components/dashboard/analysis-monitor";

export const metadata: Metadata = {
  title: "Analysis Monitoring — Ventrix",
  description: "Track the status of a Ventrix due diligence analysis.",
};

export default function AnalysisMonitoringPage({
  params,
}: {
  params: { id: string };
}) {
  return <AnalysisMonitor analysisId={params.id} />;
}
