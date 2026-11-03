import type { Metadata } from "next";
import { Search } from "lucide-react";
import { WorkspacePlaceholder } from "@/components/dashboard/workspace-placeholder";

export const metadata: Metadata = {
  title: "Evidence Explorer — Ventrix",
};

export default function EvidenceExplorerPage() {
  return (
    <WorkspacePlaceholder
      title="Evidence Explorer"
      description="Search the source trail behind every finding, including citations, verification notes, and confidence scores."
      icon={Search}
    />
  );
}
