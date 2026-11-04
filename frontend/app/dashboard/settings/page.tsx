"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card } from "@/components/ui/card";
import { getSystemStatus, getSystemUsage, type SystemStatus, type SystemUsage } from "@/lib/api";

export default function SettingsPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [usage, setUsage] = useState<SystemUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getSystemStatus(), getSystemUsage()])
      .then(([statusData, usageData]) => {
        setStatus(statusData);
        setUsage(usageData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load system status"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Settings"
        title="Settings and system information"
        description="Manage your workspace profile, analysis usage, and provider configuration."
      />

      <Card className="p-6">
        <h2 className="text-sm font-semibold text-text-primary">User profile</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-sm border border-border bg-secondary/30 p-3">
            <p className="text-[10px] uppercase tracking-wider text-text-secondary">Name</p>
            <p className="mt-1 text-sm text-text-primary">Ventrix User</p>
          </div>
          <div className="rounded-sm border border-border bg-secondary/30 p-3">
            <p className="text-[10px] uppercase tracking-wider text-text-secondary">Workspace</p>
            <p className="mt-1 text-sm text-text-primary">Default workspace</p>
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-sm font-semibold text-text-primary">Analysis usage</h2>
        {loading && <p className="mt-3 text-sm text-text-secondary">Loading...</p>}
        {error && <p className="mt-3 text-sm text-critical">{error}</p>}
        {status && (
          <div className="mt-3">
            <p className="text-sm text-text-secondary">
              {usage
                ? `${usage.completed_analyses} of ${usage.max_analyses} successful runs used (${usage.remaining_analyses} remaining)`
                : `${status.analysis_count} of ${status.max_analyses} analyses used`}
            </p>
            <div className="mt-2 h-2 w-full rounded-full bg-secondary">
              <div
                className="h-2 rounded-full bg-blue-accent"
                style={{
                  width: `${Math.min(100, (status.analysis_count / status.max_analyses) * 100)}%`,
                }}
              />
            </div>
          </div>
        )}
      </Card>

      <Card className="p-6">
        <h2 className="text-sm font-semibold text-text-primary">API provider status</h2>
        {status && (
          <div className="mt-3 space-y-2">
            <p className="text-sm text-text-secondary">
              Active provider: {status.active_provider}
            </p>
            {status.providers.map((provider) => (
              <div
                key={provider.name}
                className="flex items-center justify-between rounded-sm border border-border bg-secondary/30 px-3 py-2 text-sm"
              >
                <span>{provider.name}</span>
                <span className={provider.configured ? "text-success" : "text-text-secondary"}>
                  {provider.configured ? "Configured" : "Not configured"}
                  {provider.active ? " (active)" : ""}
                </span>
              </div>
            ))}
            <p className="text-xs text-text-secondary">
              Fallback history: {status.fallback_history.length ? status.fallback_history.join(", ") : "None"}
            </p>
          </div>
        )}
      </Card>

      <Card className="p-6">
        <h2 className="text-sm font-semibold text-text-primary">System configuration</h2>
        {status && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 text-sm text-text-secondary">
            <span>API status: {status.api_status}</span>
            <span>Database: {status.database}</span>
            <span>Version: {status.version}</span>
            <span>Max analyses: {status.max_analyses}</span>
          </div>
        )}
      </Card>
    </div>
  );
}
