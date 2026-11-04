"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Download,
  FileText,
  Layers3,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  downloadReportPdf,
  getReport,
  listAnalyses,
  type AnalysisRecord,
} from "@/lib/api";

type Report = Record<string, unknown>;

function text(value: unknown): string {
  if (value == null) return "";
  return typeof value === "string" ? value : String(value);
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function riskVariant(value: unknown): "success" | "warning" | "critical" | "neutral" {
  const normalized = text(value).toLowerCase();
  if (normalized.includes("critical") || normalized.includes("high")) return "critical";
  if (normalized.includes("medium") || normalized.includes("moderate")) return "warning";
  if (normalized.includes("low") || normalized.includes("strong")) return "success";
  return "neutral";
}

function formatDate(value: unknown): string {
  if (typeof value !== "string" || !value) return "Unavailable";
  const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function Chart({ chart }: { chart: Record<string, unknown> }) {
  const labels = asArray(chart.labels).map(text);
  const values = asArray(chart.values).map((value) => Number(value) || 0);
  const max = Math.max(...values, 1);

  return (
    <div className="rounded-xl border border-slate-200/70 bg-slate-50/70 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-xs font-semibold text-slate-800">
          {text(chart.title) || "Chart"}
        </p>
        {chart.unit ? (
          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
            {text(chart.unit)}
          </span>
        ) : null}
      </div>
      <div className="space-y-2">
        {labels.map((label, index) => (
          <div key={`${label}-${index}`} className="grid grid-cols-[minmax(9rem,1fr)_2fr_auto] items-center gap-3">
            <span className="truncate text-[11px] text-slate-600">{label}</span>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200/80">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-cyan-400"
                style={{ width: `${(values[index] / max) * 100}%` }}
              />
            </div>
            <span className="text-[11px] font-semibold text-slate-700">
              {values[index]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: "success" | "warning" | "critical" | "neutral";
}) {
  const colors = {
    success: "from-emerald-500/15 to-emerald-500/[0.03] text-emerald-700",
    warning: "from-amber-500/15 to-amber-500/[0.03] text-amber-700",
    critical: "from-rose-500/15 to-rose-500/[0.03] text-rose-700",
    neutral: "from-blue-500/15 to-blue-500/[0.03] text-blue-700",
  };

  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm">
      <div className={`mb-3 h-1 rounded-full bg-gradient-to-r ${colors[tone].split(" ")[0]} ${colors[tone].split(" ")[1]}`} />
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
        {label}
      </p>
      <p className={`mt-2 text-2xl font-bold tracking-tight ${colors[tone].split(" ")[2]}`}>
        {value}
      </p>
      {detail ? <p className="mt-1 text-xs text-slate-500">{detail}</p> : null}
    </div>
  );
}

export default function InvestorReportsPage() {
  const [analysisId, setAnalysisId] = useState("");
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    listAnalyses()
      .then((items) => {
        setAnalyses(items);
        if (items.length > 0 && !analysisId) {
          setAnalysisId(String(items[0].id));
        }
      })
      .catch(() => setAnalyses([]));
  }, []);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await getReport(analysisId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await downloadReportPdf(analysisId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ventrix-report-${analysisId}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "PDF download failed");
    } finally {
      setDownloading(false);
    }
  };

  const [activeTab, setActiveTab] = useState<
    "overview" | "findings" | "verification" | "gaps"
  >("overview");

  const sections = asArray(report?.sections) as Record<string, unknown>[];
  const charts = asArray(report?.charts) as Record<string, unknown>[];
  const findings = asArray(report?.all_findings) as Record<string, unknown>[];
  const missing = asArray(report?.missing_information).map(text);
  const questions = asArray(report?.investor_questions).map(text);
  const reliability = asArray(report?.source_reliability) as Record<string, unknown>[];
  const assessment = (report?.controller_assessment ?? null) as Record<string, unknown> | null;
  const findingSections = sections.filter((section) =>
    !["Verification and Cross-Analysis", "Information Gaps", "Investor Questions", "Investment Considerations", "Final Assessment"].includes(
      text(section.title)
    )
  );
  const verificationSection = sections.find(
    (section) => text(section.title) === "Verification and Cross-Analysis"
  );
  const finalSection = sections.find(
    (section) => text(section.title) === "Final Assessment"
  );
  const tabButton = (tab: typeof activeTab, label: string) => (
    <button
      type="button"
      onClick={() => setActiveTab(tab)}
      className={`rounded-xl px-4 py-2 text-xs font-semibold transition-colors ${
        activeTab === tab
          ? "bg-blue-600 text-white shadow-sm"
          : "bg-white text-slate-600 ring-1 ring-inset ring-slate-200 hover:bg-slate-50"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Investor reports"
        title="Investor report"
        description="Load a generated report by analysis ID and export it as PDF."
      />

      <Card className="overflow-hidden border-slate-200/70 bg-white/95 p-5 shadow-soft">
        <div className="space-y-2">
          <label className="text-xs font-medium text-text-secondary">Analysis ID</label>
          <div className="flex items-center gap-3">
            <div className="min-w-0 flex-1">
              <Input
                value={analysisId}
                onChange={(event) => setAnalysisId(event.target.value)}
              />
            </div>
            <div className="flex shrink-0 gap-2">
              <Button onClick={loadReport} disabled={loading || !analysisId}>
                {loading ? "Loading..." : "Load report"}
              </Button>
              <Button
                variant="secondary"
                onClick={handleDownload}
                disabled={downloading || !analysisId}
              >
                {downloading ? "Downloading..." : "Download PDF"}
              </Button>
            </div>
          </div>
          {analyses.length > 0 && (
            <p className="text-xs text-text-secondary">
              Available analyses: {analyses.map((item) => item.id).join(", ")}
            </p>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-critical">{error}</p>}
      </Card>

      {report && (
        <>
          <Card className="overflow-hidden border-slate-200/70 bg-gradient-to-br from-white via-blue-50/40 to-violet-50/50 p-6 shadow-soft">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge variant={riskVariant(report.overall_risk)} dot>
                    {text(report.overall_risk) || "Unknown"} risk
                  </Badge>
                  <Badge variant="default">
                    {text(report.final_assessment_category) || "Unavailable"}
                  </Badge>
                  <Badge variant="neutral">
                    {text(report.verification_status) || "Unavailable"} verification
                  </Badge>
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-slate-900">
                  {text(report.title) || "Investor Due Diligence Report"}
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-slate-600">
                  {text(report.executive_summary)}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200/70 bg-white/80 p-4 text-xs text-slate-500 shadow-sm">
                <p className="font-semibold text-slate-700">Generated</p>
                <p className="mt-1">{formatDate(report.generated_at)}</p>
                <p className="mt-3 font-semibold text-slate-700">Recommendation</p>
                <p className="mt-1 max-w-xs">{text(report.recommendation) || "Review the report before deciding."}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label="Overall risk"
                value={text(report.overall_risk) || "Unknown"}
                detail={text(report.overall_assessment)}
                tone={riskVariant(report.overall_risk)}
              />
              <MetricCard
                label="Verification"
                value={text(report.verification_status) || "Unavailable"}
                detail={`${asArray(report.missing_information).length} missing items`}
                tone={riskVariant(report.verification_status)}
              />
              <MetricCard
                label="Evidence"
                value={text(report.evidence_status) || "Unavailable"}
                detail={`${asArray(report.evidence_references).length} references`}
                tone="neutral"
              />
              <MetricCard
                label="Final assessment"
                value={text(report.final_assessment_category) || "Unavailable"}
                detail={`${asArray(report.failed_agents).length} failed agents`}
                tone={riskVariant(report.final_assessment_category)}
              />
            </div>
          </Card>

          <div className="flex flex-wrap gap-2">
            {tabButton("overview", "Overview")}
            {tabButton("findings", "Findings")}
            {tabButton("verification", "Verification")}
            {tabButton("gaps", "Gaps & Questions")}
          </div>

          {activeTab === "overview" && (
            <>
              {assessment && (
                <Card className="border-blue-200/70 bg-blue-50/40 p-6">
                  <div className="mb-4 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-blue-600" />
                    <h3 className="text-sm font-semibold text-slate-900">Controller assessment</h3>
                  </div>
                  <p className="text-sm leading-relaxed text-slate-700">
                    {text(assessment.summary)}
                  </p>
                  <div className="mt-4 grid gap-4 md:grid-cols-3">
                    {[
                      ["Key risks", assessment.key_risks],
                      ["Missing information", assessment.missing_information],
                      ["Recommended next steps", assessment.recommended_next_steps],
                    ].map(([label, value]) => (
                      <div key={String(label)} className="rounded-xl bg-white/80 p-4">
                        <p className="text-xs font-semibold text-slate-700">{String(label)}</p>
                        <ul className="mt-2 space-y-1 text-xs text-slate-600">
                          {asArray(value).map((item, index) => (
                            <li key={index} className="flex gap-2">
                              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                              <span>{text(item)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {charts.length > 0 && (
                <Card className="p-6">
                  <div className="mb-4 flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-blue-600" />
                    <h3 className="text-sm font-semibold text-slate-900">Risk and verification overview</h3>
                  </div>
                  <div className="grid gap-4 lg:grid-cols-2">
                    {charts.map((chart, index) => (
                      <Chart key={index} chart={chart} />
                    ))}
                  </div>
                </Card>
              )}

              {finalSection && (
                <Card className="p-6">
                  <h3 className="text-base font-semibold text-slate-900">
                    {text(finalSection.title) || "Final assessment"}
                  </h3>
                  <div className="mt-3 space-y-3">
                    {asArray(finalSection.content).map((paragraph, pIndex) => (
                      <p key={pIndex} className="text-sm leading-relaxed text-slate-600">
                        {text(paragraph)}
                      </p>
                    ))}
                  </div>
                </Card>
              )}
            </>
          )}

          {activeTab === "findings" && (
            <div className="grid gap-4">
              {findingSections.map((section, index) => {
                const sectionCharts = asArray(section.charts) as Record<string, unknown>[];
                const sectionTables = asArray(section.tables) as Record<string, unknown>[];
                const indicators = asArray(section.risk_indicators) as Record<string, unknown>[];
                const sectionFindings = asArray(section.findings) as Record<string, unknown>[];

                return (
                  <Card key={index} className="p-6">
                    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900">
                          {text(section.title) || `Section ${index + 1}`}
                        </h3>
                        {section.verification_status ? (
                          <p className="mt-1 text-xs text-slate-500">
                            Verification: {text(section.verification_status)}
                          </p>
                        ) : null}
                      </div>
                      {indicators.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {indicators.map((indicator, iIndex) => (
                            <Badge key={iIndex} variant={riskVariant(indicator.level)}>
                              {text(indicator.label)}: {text(indicator.level)}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="space-y-3">
                      {asArray(section.content).map((paragraph, pIndex) => (
                        <p key={pIndex} className="text-sm leading-relaxed text-slate-600">
                          {text(paragraph)}
                        </p>
                      ))}
                    </div>

                    {sectionFindings.length > 0 && (
                      <div className="mt-5 grid gap-3 md:grid-cols-2">
                        {sectionFindings.map((finding, fIndex) => (
                          <div
                            key={fIndex}
                            className="rounded-xl border border-slate-200/70 bg-slate-50/70 p-4"
                          >
                            <div className="mb-2 flex items-center justify-between gap-2">
                              <p className="text-xs font-semibold text-slate-800">
                                {text(finding.dimension) || text(finding.title) || "Finding"}
                              </p>
                              <Badge variant={riskVariant(finding.risk_level)}>
                                {text(finding.risk_level) || "Unknown"}
                              </Badge>
                            </div>
                            <p className="text-xs leading-relaxed text-slate-600">
                              {text(finding.summary)}
                            </p>
                            {finding.evidence_status ? (
                              <p className="mt-2 text-[10px] font-medium uppercase tracking-wider text-slate-400">
                                {text(finding.evidence_status)}
                              </p>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    )}

                    {sectionCharts.length > 0 && (
                      <div className="mt-5 grid gap-4 lg:grid-cols-2">
                        {sectionCharts.map((chart, cIndex) => (
                          <Chart key={cIndex} chart={chart} />
                        ))}
                      </div>
                    )}

                    {sectionTables.length > 0 && (
                      <div className="mt-5 space-y-4">
                        {sectionTables.map((table, tIndex) => (
                          <div key={tIndex} className="overflow-x-auto rounded-xl border border-slate-200/70">
                            <p className="border-b border-slate-200/70 bg-slate-50/80 px-3 py-2 text-xs font-semibold text-slate-800">
                              {text(table.title) || "Table"}
                            </p>
                            <table className="min-w-full border-collapse text-xs">
                              <thead>
                                <tr className="bg-slate-50/70">
                                  {asArray(table.columns).map((column, cIndex) => (
                                    <th
                                      key={cIndex}
                                      className="border-b border-slate-200 px-3 py-2 text-left font-semibold text-slate-600"
                                    >
                                      {text(column)}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {asArray(table.rows).map((row, rIndex) => (
                                  <tr key={rIndex} className="border-b border-slate-100 last:border-0">
                                    {asArray(row).map((cell, cellIndex) => (
                                      <td
                                        key={cellIndex}
                                        className="px-3 py-2 text-slate-600"
                                      >
                                        {text(cell)}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          )}

          {activeTab === "verification" && (
            <>
              {verificationSection && (
                <Card className="p-6">
                  <h3 className="text-base font-semibold text-slate-900">
                    {text(verificationSection.title) || "Verification"}
                  </h3>
                  <div className="mt-3 space-y-3">
                    {asArray(verificationSection.content).map((paragraph, pIndex) => (
                      <p key={pIndex} className="text-sm leading-relaxed text-slate-600">
                        {text(paragraph)}
                      </p>
                    ))}
                  </div>
                  {asArray(verificationSection.risk_indicators).length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {asArray(verificationSection.risk_indicators).map((indicator, iIndex) => (
                        <Badge key={iIndex} variant={riskVariant((indicator as Record<string, unknown>).level)}>
                          {text((indicator as Record<string, unknown>).label)}: {text((indicator as Record<string, unknown>).level)}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {asArray(verificationSection.charts).length > 0 && (
                    <div className="mt-5 grid gap-4 lg:grid-cols-2">
                      {asArray(verificationSection.charts).map((chart, cIndex) => (
                        <Chart key={cIndex} chart={chart as Record<string, unknown>} />
                      ))}
                    </div>
                  )}
                </Card>
              )}

              {reliability.length > 0 && (
                <Card className="p-6">
                  <div className="mb-4 flex items-center gap-2">
                    <Layers3 className="h-4 w-4 text-blue-600" />
                    <h3 className="text-sm font-semibold text-slate-900">Source reliability</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50/70">
                          {["Evidence", "Status", "Reliability", "Score"].map((heading) => (
                            <th key={heading} className="px-3 py-2 text-left font-semibold text-slate-600">
                              {heading}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {reliability.map((item, index) => (
                          <tr key={index} className="border-b border-slate-100 last:border-0">
                            <td className="px-3 py-2 text-slate-700">{text(item.id)}</td>
                            <td className="px-3 py-2 text-slate-600">{text(item.status)}</td>
                            <td className="px-3 py-2 text-slate-600">{text(item.reliability)}</td>
                            <td className="px-3 py-2 text-slate-600">{text(item.score)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </>
          )}

          {activeTab === "gaps" && (
            <>
              {missing.length > 0 && (
                <Card className="p-6">
                  <div className="mb-4 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <h3 className="text-sm font-semibold text-slate-900">Information gaps</h3>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {missing.map((item, index) => (
                      <div
                        key={index}
                        className="rounded-xl border border-amber-200/70 bg-amber-50/60 px-3 py-2 text-xs text-amber-800"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {questions.length > 0 && (
                <Card className="p-6">
                  <div className="mb-4 flex items-center gap-2">
                    <FileText className="h-4 w-4 text-blue-600" />
                    <h3 className="text-sm font-semibold text-slate-900">Investor questions</h3>
                  </div>
                  <div className="space-y-2">
                    {questions.map((question, index) => (
                      <div
                        key={index}
                        className="rounded-xl border border-slate-200/70 bg-slate-50/70 px-3 py-2 text-sm text-slate-700"
                      >
                        {question}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {report.disclaimer ? (
                <Card className="border-slate-200/70 bg-slate-50/70 p-5">
                  <div className="flex gap-3">
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
                    <p className="text-xs leading-relaxed text-slate-500">
                      {text(report.disclaimer)}
                    </p>
                  </div>
                </Card>
              ) : null}
            </>
          )}
        </>
      )}
    </div>
  );
}
