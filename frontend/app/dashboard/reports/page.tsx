import type { Metadata } from "next";
import { FileText } from "lucide-react";
import { WorkspacePlaceholder } from "@/components/dashboard/workspace-placeholder";

export const metadata: Metadata = {
  title: "Investor Reports — Ventrix",
};

export default function InvestorReportsPage() {
  return (
    <WorkspacePlaceholder
      title="Investor Reports"
      description="Open investment committee memos, risk summaries, and sourced appendices for your portfolio."
      icon={FileText}
    />
  );
}
