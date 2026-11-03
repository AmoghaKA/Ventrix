import type { Metadata } from "next";
import { Settings } from "lucide-react";
import { WorkspacePlaceholder } from "@/components/dashboard/workspace-placeholder";

export const metadata: Metadata = {
  title: "Settings — Ventrix",
};

export default function SettingsPage() {
  return (
    <WorkspacePlaceholder
      title="Settings"
      description="Manage workspace preferences, team access, notification rules, and data controls."
      icon={Settings}
    />
  );
}
