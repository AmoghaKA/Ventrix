"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Play } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  getWorkflowAgents,
  runAgent,
  type WorkflowAgentStatusRecord,
} from "@/lib/api";

const tabs = [
  { key: "financial", label: "Financial Agent" },
  { key: "marketing", label: "Marketing Agent" },
  { key: "legal", label: "Legal Agent" },
  { key: "verification", label: "Verification Agent" },
  { key: "controller", label: "Controller Agent" },
];

function AgentTabsInner() {
  const params = useSearchParams();
  const analysisId = params.get("analysis") || "1";
  const [agents, setAgents] = useState<WorkflowAgentStatusRecord[]>([]);
  const [active, setActive] = useState("financial");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setAgents(await getWorkflowAgents(analysisId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agent results");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [analysisId]);

  const agentMap = useMemo(
    () => new Map(agents.map((item) => [item.agent_key, item])),
    [agents]
  );

  const handleRun = async (key: string) => {
    setRunning(key);
    try {
      await runAgent(analysisId, key);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setRunning(null);
    }
  };

  const selected = agentMap.get(active);
  const output = selected?.output ?? null;
  const findings = Array.isArray(output?.findings) ? output.findings : [];

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Agent analysis"
        title="Individual agent results"
        description={`Analysis ID: ${analysisId}. Results are loaded from the backend workflow.`}
      />

      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActive(tab.key)}
            className={`rounded-xl border px-3.5 py-2 text-xs font-semibold transition-colors ${
              active === tab.key
                ? "border-blue-200 bg-blue-50 text-blue-700"
                : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && <p className="text-sm text-text-secondary">Loading agent results...</p>}
      {error && <p className="text-sm text-critical">{error}</p>}

      {!loading && (
        <Card className="p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                {tabs.find((tab) => tab.key === active)?.label}
              </h2>
              <p className="mt-1 text-xs text-text-secondary">
                Status: {selected?.status ?? "Not available"} · Attempts:{" "}
                {selected?.attempt_count ?? 0}
              </p>
            </div>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => handleRun(active)}
              disabled={running === active}
            >
              {running === active ? (
                <span className="mr-2 h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
              ) : (
                <Play className="mr-2 h-3.5 w-3.5" />
              )}
              Run
            </Button>
          </div>

          {selected?.error_details && (
            <p className="mt-3 text-xs text-critical">{selected.error_details}</p>
          )}

          {output && (
            <div className="mt-4 space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-sm border border-border bg-secondary/30 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-text-secondary">Risk level</p>
                  <p className="mt-1 text-sm font-semibold text-text-primary">
                    {String(output.risk_level ?? "Unknown")}
                  </p>
                </div>
                <div className="rounded-sm border border-border bg-secondary/30 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-text-secondary">Evidence status</p>
                  <p className="mt-1 text-sm font-semibold text-text-primary">
                    {String(output.evidence_status ?? "Unavailable")}
                  </p>
                </div>
                <div className="rounded-sm border border-border bg-secondary/30 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-text-secondary">Execution</p>
                  <p className="mt-1 text-sm font-semibold text-text-primary">
                    {String(output.execution_status ?? "Unknown")}
                  </p>
                </div>
              </div>

              {typeof output.investor_impact === "string" && (
                <p className="text-sm text-text-secondary">{output.investor_impact}</p>
              )}

              <div className="space-y-3">
                {findings.map((finding, index) => (
                  <details
                    key={index}
                    className="rounded-sm border border-border bg-white p-4"
                  >
                    <summary className="cursor-pointer text-sm font-semibold text-text-primary">
                      {String(finding.dimension ?? "Finding")} - {String(finding.risk_level ?? "Unknown")}
                    </summary>
                    <div className="mt-3 space-y-2 text-xs text-text-secondary">
                      <p>{String(finding.summary ?? "")}</p>
                      <p>{String(finding.explanation ?? "")}</p>
                      <p>
                        Evidence status: {String(finding.evidence_status ?? "Unavailable")}
                      </p>
                      <p>Investor impact: {String(finding.investor_impact ?? "Not provided")}</p>
                      <p>
                        Source references:{" "}
                        {Array.isArray(finding.evidence_references)
                          ? finding.evidence_references.join(", ")
                          : "None"}
                      </p>
                    </div>
                  </details>
                ))}
              </div>

              {Array.isArray(output.missing_information) && output.missing_information.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                    Missing information
                  </h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-text-secondary">
                    {output.missing_information.map((item, index) => (
                      <li key={index}>{String(item)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {!output && !loading && (
            <p className="mt-4 text-sm text-text-secondary">
              No stored output for this agent. Run the agent or workflow to populate results.
            </p>
          )}
        </Card>
      )}
    </div>
  );
}

export default function AgentAnalysisPage() {
  return (
    <Suspense fallback={<p className="text-sm text-text-secondary">Loading...</p>}>
      <AgentTabsInner />
    </Suspense>
  );
}
