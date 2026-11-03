import type { Metadata } from "next";
import { Bot } from "lucide-react";
import { WorkspacePlaceholder } from "@/components/dashboard/workspace-placeholder";

export const metadata: Metadata = {
  title: "Agent Analysis — Ventrix",
};

export default function AgentAnalysisPage() {
  return (
    <WorkspacePlaceholder
      title="Agent Analysis"
      description="Inspect each specialized agent's findings, confidence levels, and supporting evidence."
      icon={Bot}
    />
  );
}
