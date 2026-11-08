"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CircleCheck,
  Clock,
  FileText,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  getAnalysis,
  getWorkflow,
  getWorkflowAgents,
  getWorkflowLogs,
  startAnalysisWorkflow,
  type AnalysisRecord,
  type WorkflowAgentStatusRecord,
  type WorkflowLogRecord,
  type WorkflowStatusRecord,
} from "@/lib/api";

type StatusKey = "pending" | "running" | "completed" | "failed";

const statusMeta: Record<
  StatusKey,
  { label: string; variant: "success" | "warning" | "critical" | "default" }
> = {
  pending: { label: "Pending", variant: "warning" },
  running: { label: "In progress", variant: "default" },
  completed: { label: "Completed", variant: "success" },
  failed: { label: "Failed", variant: "critical" },
};

const stageLabels: Record<string, string> = {
  data_retrieval: "Data retrieval",
  controller: "Controller Agent",
  financial: "Financial Agent",
  marketing: "Marketing Agent",
  legal: "Legal Agent",
  verification: "Verification Agent",
  report: "Final report generation",
};

const stageDescriptions: Record<string, string> = {
  data_retrieval: "Retrieve and store public evidence",
  controller: "Coordinate specialist agents and retries",
  financial: "Assess funding, revenue, cash flow, and financial risks",
  marketing: "Assess market, customers, competitors, and growth",
  legal: "Assess registration, compliance, and legal records",
  verification: "Cross-check specialist claims against stored evidence",
  report: "Generate the investor due diligence report",
};

function normalizeStatus(status: string): StatusKey {
  const normalized = status.toLowerCase();
  if (["completed", "complete", "done"].includes(normalized)) return "completed";
  if (["running", "in_progress", "processing"].includes(normalized))
    return "running";
  if (["failed", "error"].includes(normalized)) return "failed";
  return "pending";
}

function humanize(value: string | null | undefined): string {
  const raw = (value ?? "").replace(/_/g, " ").trim();
  if (!raw) return "";
  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

function formatDate(value: string | null) {
  if (!value) return "Unavailable";
  const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value)
    ? value
    : `${value}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function AnalysisMonitor({ analysisId }: { analysisId: string }) {
  const [analysis, setAnalysis] = useState<AnalysisRecord | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowStatusRecord | null>(null);
  const [agents, setAgents] = useState<WorkflowAgentStatusRecord[]>([]);
  const [logs, setLogs] = useState<WorkflowLogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const load = useCallback(async () => {
    try {
      const analysisData = await getAnalysis(analysisId);
      setAnalysis(analysisData);
      try {
        const workflowData = await getWorkflow(analysisId);
        setWorkflow(workflowData);
        const [agentData, logData] = await Promise.all([
          getWorkflowAgents(analysisId),
          getWorkflowLogs(analysisId, 100, 0),
        ]);
        setAgents(agentData);
        setLogs(logData);
      } catch {
        setWorkflow(null);
        setAgents([]);
        setLogs([]);
      }
      setError(null);
    } catch (loadError) {
      const message =
        loadError instanceof Error && !/failed to fetch/i.test(loadError.message)
          ? loadError.message
          : "Could not reach the Ventrix API. Make sure the backend is running and try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    setLoading(true);
    load();
    const interval = window.setInterval(load, 3000);
    return () => window.clearInterval(interval);
  }, [load]);

  const handleStart = async () => {
    setStarting(true);
    try {
      await startAnalysisWorkflow(analysisId, 2, 5);
      await load();
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Workflow start failed");
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 animate-pulse rounded-sm bg-secondary" />
        <div className="h-64 animate-pulse rounded-sm border border-border bg-white" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <p className="text-sm text-critical">{error}</p>
        <Button className="mt-4" size="sm" onClick={load}>
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Retry
        </Button>
      </Card>
    );
  }

  const companyName = analysis?.startup_name ?? "Analysis";
  const website = analysis?.website ?? null;
  const industry = analysis?.industry ?? null;
  const country = analysis?.country ?? null;
  const submittedAt = analysis ? formatDate(analysis.created_at) : "Unavailable";
  const assessment = analysis?.overall_assessment ?? null;
  const status: StatusKey = workflow
    ? normalizeStatus(workflow.status)
    : analysis
      ? normalizeStatus(analysis.status)
      : "pending";

  const orderedAgents = [
    "data_retrieval",
    "controller",
    "financial",
    "marketing",
    "legal",
    "verification",
    "report",
  ];
  const agentMap = new Map(agents.map((item) => [item.agent_key, item]));
  const hasWorkflow = Boolean(workflow);

  return (
    <div className="space-y-7">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 transition-colors duration-200 hover:text-blue-600"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to dashboard
      </Link>

      <PageHeader
        eyebrow="Analysis monitoring"
        title={companyName}
        description={`Analysis ID: ${analysisId}`}
        actions={
          <>
            <Badge variant={statusMeta[status].variant}>
              {statusMeta[status].label}
            </Badge>
            {assessment && <Badge variant="success">{assessment}</Badge>}
            {!hasWorkflow && (
              <Button size="sm" onClick={handleStart} disabled={starting}>
                {starting ? (
                  <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                ) : null}
                Start workflow
              </Button>
            )}
          </>
        }
      />

      <Card padding="none" className="overflow-hidden">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-text-primary">Company snapshot</h2>
        </div>
        <dl className="grid gap-0 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border-b border-border px-5 py-4 sm:border-r lg:border-b-0">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">Website</dt>
            <dd className="mt-1.5 truncate text-sm text-text-primary">{website || "Unavailable"}</dd>
          </div>
          <div className="border-b border-border px-5 py-4 lg:border-b-0 lg:border-r">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">Industry</dt>
            <dd className="mt-1.5 text-sm text-text-primary">{industry || "Unavailable"}</dd>
          </div>
          <div className="border-b border-border px-5 py-4 sm:border-b-0 sm:border-r">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">Country</dt>
            <dd className="mt-1.5 text-sm text-text-primary">{country || "Unavailable"}</dd>
          </div>
          <div className="px-5 py-4">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">Submitted</dt>
            <dd className="mt-1.5 text-sm text-text-primary">{submittedAt}</dd>
          </div>
        </dl>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-text-primary">Workflow stages</h2>
          <ol className="mt-5 space-y-4">
            {orderedAgents.map((key, index) => {
              const agent = agentMap.get(key);
              const stageStatus = agent ? normalizeStatus(agent.status) : "pending";
              return (
                <li key={key} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <span
                      className={`flex h-7 w-7 items-center justify-center rounded-full border ${
                        stageStatus === "completed"
                          ? "border-blue-accent bg-blue-50 text-blue-accent"
                          : stageStatus === "running"
                            ? "border-warning bg-warning/10 text-warning"
                            : stageStatus === "failed"
                              ? "border-critical bg-critical/10 text-critical"
                              : "border-border bg-white text-text-secondary"
                      }`}
                    >
                      {stageStatus === "completed" ? (
                        <CircleCheck className="h-4 w-4" />
                      ) : stageStatus === "running" ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : stageStatus === "failed" ? (
                        <AlertCircle className="h-4 w-4" />
                      ) : (
                        <span className="text-[10px] font-semibold">{index + 1}</span>
                      )}
                    </span>
                    {index < orderedAgents.length - 1 && (
                      <span className="mt-1 h-6 w-px bg-border" />
                    )}
                  </div>
                  <div className="pb-2">
                    <p className="text-xs font-semibold text-text-primary">
                      {stageLabels[key]}
                    </p>
                    <p className="mt-0.5 text-xs text-text-secondary">
                      {stageDescriptions[key]}
                    </p>
                    <p className="mt-1 text-[10px] uppercase tracking-wider text-text-secondary/80">
                      {agent
                        ? `${statusMeta[stageStatus].label} · ${agent.attempt_count} attempt${
                            agent.attempt_count === 1 ? "" : "s"
                          } · started ${formatDate(agent.started_at)} · completed ${formatDate(agent.completed_at)}`
                        : "Not started"}
                    </p>
                    {agent?.error_details && (
                      <p className="mt-1 text-xs text-critical">{agent.error_details}</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </Card>

        <Card className="p-6">
          <h2 className="text-sm font-semibold text-text-primary">Activity log</h2>
          <div className="mt-4 max-h-96 space-y-3 overflow-y-auto">
            {logs.length === 0 && (
              <p className="text-xs text-text-secondary">No activity recorded yet.</p>
            )}
            {logs.map((log) => (
              <div key={log.id} className="rounded-sm border border-border bg-secondary/30 px-3 py-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-accent">
                    {humanize(log.event)}
                  </span>
                  <span className="text-[10px] text-text-secondary">
                    {formatDate(log.timestamp)}
                  </span>
                </div>
                <p className="mt-1 text-xs text-text-primary">{log.message}</p>
                {log.agent_key && (
                  <p className="mt-1 text-[10px] text-text-secondary">
                    Agent: {humanize(log.agent_key)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {workflow?.error_details && (
        <div className="flex items-start gap-3 rounded-sm border border-critical/30 bg-critical/5 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-critical" />
          <div>
            <p className="text-xs font-semibold text-critical">Workflow failed</p>
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">
              {workflow.error_details}
            </p>
          </div>
        </div>
      )}

      {workflow?.report && (
        <Card className="p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-text-primary">Report ready</h2>
              <p className="mt-1 text-xs text-text-secondary">
                Final assessment: {String(workflow.report.final_assessment_category ?? "Unavailable")}
              </p>
            </div>
            <Link
              href={`/dashboard/reports?analysis=${analysisId}`}
              className="inline-flex items-center gap-1 text-xs font-medium text-blue-accent hover:underline"
            >
              <FileText className="h-3.5 w-3.5" />
              Open report
            </Link>
          </div>
        </Card>
      )}
    </div>
  );
}
