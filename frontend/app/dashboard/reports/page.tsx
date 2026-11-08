"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Compass,
  Download,
  FileText,
  Gauge,
  HelpCircle,
  Layers3,
  Link2,
  ListChecks,
  Loader2,
  PauseCircle,
  Search,
  SearchX,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  downloadReportPdf,
  getReport,
  listAnalyses,
  type AnalysisRecord,
} from "@/lib/api";

type Report = Record<string, unknown>;
type Tone = "success" | "warning" | "critical" | "neutral";

const toneStyles: Record<
  Tone,
  { text: string; dot: string; bar: string; soft: string; ring: string }
> = {
  success: {
    text: "text-emerald-700",
    dot: "bg-emerald-500",
    bar: "bg-emerald-500",
    soft: "border-emerald-200/70 bg-emerald-50/70",
    ring: "ring-emerald-200/70",
  },
  warning: {
    text: "text-amber-700",
    dot: "bg-amber-500",
    bar: "bg-amber-500",
    soft: "border-amber-200/70 bg-amber-50/70",
    ring: "ring-amber-200/70",
  },
  critical: {
    text: "text-rose-700",
    dot: "bg-rose-500",
    bar: "bg-rose-500",
    soft: "border-rose-200/70 bg-rose-50/70",
    ring: "ring-rose-200/70",
  },
  neutral: {
    text: "text-blue-700",
    dot: "bg-blue-500",
    bar: "bg-blue-500",
    soft: "border-blue-200/70 bg-blue-50/70",
    ring: "ring-blue-200/70",
  },
};

function text(value: unknown): string {
  if (value == null) return "";
  return typeof value === "string" ? value : String(value);
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function riskVariant(value: unknown): Tone {
  const normalized = text(value).toLowerCase();
  if (normalized.includes("critical") || normalized.includes("high")) return "critical";
  if (normalized.includes("medium") || normalized.includes("moderate")) return "warning";
  if (normalized.includes("low") || normalized.includes("strong")) return "success";
  return "neutral";
}

function verificationTone(value: unknown): Tone {
  const normalized = text(value).toLowerCase();
  if (normalized.includes("partial")) return "warning";
  if (
    normalized.includes("unverified") ||
    normalized.includes("failed") ||
    normalized.includes("invalid")
  ) {
    return "critical";
  }
  if (normalized.includes("verified")) return "success";
  return "neutral";
}

function isVerified(value: unknown): boolean {
  const normalized = text(value).toLowerCase();
  return (
    normalized === "verified" ||
    (normalized.includes("verified") &&
      !normalized.includes("un") &&
      !normalized.includes("partial"))
  );
}

function assessmentTone(value: unknown): Tone {
  const normalized = text(value).toLowerCase();
  if (normalized.includes("do not") || normalized.includes("reject")) return "critical";
  if (
    normalized.includes("hold") ||
    normalized.includes("investigation") ||
    normalized.includes("conditional")
  ) {
    return "warning";
  }
  if (normalized.includes("proceed")) return "success";
  return "neutral";
}

function decisionMessage(report: Report): string {
  const risk = (humanize(report.overall_risk) || "unknown").toLowerCase();
  const verification = (humanize(report.verification_status) || "unavailable").toLowerCase();
  const concerns = asArray(report.major_concerns).length;
  const gaps = asArray(report.missing_information).length;
  const failed = asArray(report.failed_agents).length;
  const parts = [
    `Overall risk is ${risk} and evidence verification is ${verification}.`,
    concerns > 0
      ? `${concerns} major concern${concerns === 1 ? "" : "s"} flagged.`
      : "No major concerns flagged.",
    gaps > 0
      ? `${gaps} information gap${gaps === 1 ? "" : "s"} remain open.`
      : "No open information gaps.",
    failed > 0
      ? `${failed} specialist agent${failed === 1 ? "" : "s"} did not complete.`
      : "",
  ].filter(Boolean);
  return parts.join(" ");
}
function investmentVerdict(category: unknown): {
  label: string;
  tone: Tone;
  Icon: typeof CheckCircle2;
} {
  const normalized = text(category).toLowerCase();
  if (normalized.includes("do not") || normalized.includes("reject")) {
    return { label: "Do Not Invest", tone: "critical", Icon: XCircle };
  }
  if (normalized.includes("hold") || normalized.includes("investigation")) {
    return { label: "Hold — Investigate Further", tone: "warning", Icon: PauseCircle };
  }
  if (normalized.includes("conditional")) {
    return { label: "Proceed Conditionally", tone: "warning", Icon: AlertCircle };
  }
  if (normalized.includes("proceed")) {
    return { label: "Consider Investing", tone: "success", Icon: CheckCircle2 };
  }
  return { label: text(category) || "Undecided", tone: "neutral", Icon: HelpCircle };
}

function humanize(value: unknown): string {
  const raw = text(value).replace(/_/g, " ").trim();
  if (!raw) return "";
  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

function countLabel(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
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

function sectionVisual(title: string) {
  const value = title.toLowerCase();
  if (value.includes("scorecard")) {
    return { Icon: Gauge, tile: "from-sky-500/15 to-blue-500/5 text-sky-600 ring-sky-200/70" };
  }
  if (value.includes("risk")) {
    return { Icon: AlertTriangle, tile: "from-rose-500/15 to-amber-500/5 text-rose-600 ring-rose-200/70" };
  }
  if (value.includes("invest") || value.includes("reason")) {
    return { Icon: TrendingUp, tile: "from-emerald-500/15 to-teal-500/5 text-emerald-600 ring-emerald-200/70" };
  }
  if (value.includes("agent")) {
    return { Icon: Layers3, tile: "from-violet-500/15 to-indigo-500/5 text-violet-600 ring-violet-200/70" };
  }
  if (value.includes("missing") || value.includes("gap")) {
    return { Icon: SearchX, tile: "from-amber-500/15 to-orange-500/5 text-amber-600 ring-amber-200/70" };
  }
  if (value.includes("evidence") || value.includes("source")) {
    return { Icon: Link2, tile: "from-cyan-500/15 to-blue-500/5 text-cyan-600 ring-cyan-200/70" };
  }
  if (value.includes("final") || value.includes("decision")) {
    return { Icon: Compass, tile: "from-blue-500/15 to-indigo-500/5 text-blue-600 ring-blue-200/70" };
  }
  if (value.includes("executive")) {
    return { Icon: Sparkles, tile: "from-indigo-500/15 to-violet-500/5 text-indigo-600 ring-indigo-200/70" };
  }
  return { Icon: FileText, tile: "from-slate-500/15 to-slate-500/5 text-slate-600 ring-slate-200/70" };
}

function barClass(label: string): string {
  const value = label.toLowerCase();
  if (value.includes("critical") || value.includes("high")) {
    return "from-rose-500 to-rose-400";
  }
  if (value.includes("medium")) return "from-amber-500 to-amber-400";
  if (value.includes("low")) return "from-emerald-500 to-emerald-400";
  return "from-blue-500 via-indigo-500 to-cyan-400";
}

function Chart({ chart }: { chart: Record<string, unknown> }) {
  const labels = asArray(chart.labels).map(text);
  const values = asArray(chart.values).map((value) => Number(value) || 0);
  const max = Math.max(...values, 1);

  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
            <BarChart3 className="h-3.5 w-3.5" />
          </span>
          <p className="text-xs font-semibold text-slate-800">
            {text(chart.title) || "Chart"}
          </p>
        </div>
        {chart.unit ? (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-slate-500">
            {text(chart.unit)}
          </span>
        ) : null}
      </div>
      <div className="space-y-3">
        {labels.map((label, index) => (
          <div
            key={`${label}-${index}`}
            className="grid grid-cols-[minmax(7rem,1fr)_2fr_2.5rem] items-center gap-3"
          >
            <span className="truncate text-[11px] font-medium text-slate-600">
              {label}
            </span>
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${barClass(label)} transition-all duration-700`}
                style={{ width: `${Math.max((values[index] / max) * 100, values[index] > 0 ? 6 : 0)}%` }}
              />
            </div>
            <span className="text-right text-[11px] font-semibold tabular-nums text-slate-700">
              {values[index]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function HeroPill({
  tone,
  children,
}: {
  tone: Tone;
  children: React.ReactNode;
}) {
  const styles: Record<Tone, string> = {
    success: "bg-emerald-50 text-emerald-700 ring-emerald-200/70",
    warning: "bg-amber-50 text-amber-700 ring-amber-200/70",
    critical: "bg-rose-50 text-rose-700 ring-rose-200/70",
    neutral: "bg-slate-100 text-slate-600 ring-slate-200/70",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ring-1 ring-inset ${styles[tone]}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          tone === "neutral" ? "bg-slate-400" : toneStyles[tone].dot
        }`}
      />
      {children}
    </span>
  );
}

function HeroStat({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail?: string;
  tone: Tone;
}) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm transition-colors duration-300 hover:shadow-ring">
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${toneStyles[tone].dot}`} />
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          {label}
        </p>
      </div>
      <p className="mt-2 text-lg font-semibold tracking-tight text-slate-900">
        {value}
      </p>
      {detail ? (
        <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{detail}</p>
      ) : null}
    </div>
  );
}

function SourceItem({ reference }: { reference: Record<string, unknown> }) {
  const url = text(reference.source_url);
  const title =
    text(reference.source_title) || `Evidence ${text(reference.evidence_id)}`;

  const inner = (
    <>
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
        <Link2 className="h-4 w-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-semibold text-slate-800">
          {title}
        </span>
        <span className="mt-0.5 block truncate text-[11px] text-slate-500">
          {url || "No public URL provided"}
        </span>
      </span>
      <span className="hidden shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-slate-500 sm:inline-flex">
        {humanize(reference.verification_status) || "Unverified"}
      </span>
      {url ? (
        <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-slate-400 transition-colors group-hover:text-blue-600" />
      ) : null}
    </>
  );

  const className =
    "group flex items-center gap-3 rounded-2xl border border-slate-200/70 bg-white p-3 transition-colors duration-200 hover:border-blue-200 hover:bg-blue-50/40";

  if (!url) return <div className={className}>{inner}</div>;

  return (
    <a href={url} target="_blank" rel="noreferrer" className={className}>
      {inner}
    </a>
  );
}

function SectionCard({ section }: { section: Record<string, unknown> }) {
  const title = text(section.title) || "Section";
  const content = asArray(section.content).map(text).filter(Boolean);
  const sectionFindings = asArray(section.findings) as Record<string, unknown>[];
  const sectionCharts = asArray(section.charts) as Record<string, unknown>[];
  const sectionTables = asArray(section.tables) as Record<string, unknown>[];
  const indicators = asArray(section.risk_indicators) as Record<string, unknown>[];
  const references = (asArray(section.evidence_references) as Record<string, unknown>[]).filter(
    (reference) => isVerified(reference.verification_status)
  );
  const { Icon, tile } = sectionVisual(title);

  return (
    <Card padding="none" className="overflow-hidden animate-fade-up">
      <div className="flex flex-col gap-3 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-3">
          <span
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ring-1 ring-inset ${tile}`}
          >
            <Icon className="h-5 w-5" />
          </span>
          <div>
            <h3 className="text-sm font-semibold tracking-tight text-slate-900 sm:text-base">
              {title}
            </h3>
            {section.verification_status ? (
              <p className="mt-0.5 text-[11px] font-medium text-slate-500">
                Verification · {humanize(section.verification_status)}
              </p>
            ) : null}
          </div>
        </div>
        {indicators.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {indicators.map((indicator, index) => (
              <Badge key={index} variant={riskVariant(indicator.level)}>
                {text(indicator.label)}: {humanize(indicator.level)}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-5 p-5 sm:p-6">
        {content.length > 0 && (
          <div className="space-y-3">
            {content.map((paragraph, index) => (
              <p
                key={index}
                className={
                  index === 0
                    ? "text-sm leading-relaxed text-slate-700"
                    : "text-sm leading-relaxed text-slate-600"
                }
              >
                {paragraph}
              </p>
            ))}
          </div>
        )}

        {sectionFindings.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2">
            {sectionFindings.map((finding, index) => {
              const tone = riskVariant(finding.risk_level);
              return (
                <div
                  key={index}
                  className="relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm transition-shadow duration-200 hover:shadow-ring"
                >
                  <span
                    className={`absolute inset-y-0 left-0 w-1 ${toneStyles[tone].bar}`}
                  />
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs font-semibold text-slate-900">
                      {text(finding.dimension) || text(finding.title) || "Finding"}
                    </p>
                    <Badge variant={tone}>
                      {humanize(finding.risk_level) || "Unknown"}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600">
                    {text(finding.summary)}
                  </p>
                  {finding.investor_impact ? (
                    <div className="mt-3 rounded-xl bg-slate-50/90 px-3 py-2 text-xs leading-relaxed text-slate-600">
                      <span className="font-semibold text-slate-700">
                        Investor impact:{" "}
                      </span>
                      {text(finding.investor_impact)}
                    </div>
                  ) : null}
                  {finding.evidence_status ? (
                    <div className="mt-3 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                      <ShieldCheck className="h-3 w-3" />
                      {humanize(finding.evidence_status)}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}

        {sectionCharts.length > 0 && (
          <div className="grid gap-4 lg:grid-cols-2">
            {sectionCharts.map((chart, index) => (
              <Chart key={index} chart={chart} />
            ))}
          </div>
        )}

        {sectionTables.length > 0 && (
          <div className="space-y-4">
            {sectionTables.map((table, index) => (
              <div
                key={index}
                className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-sm"
              >
                <div className="flex items-center gap-2 border-b border-slate-200/70 bg-slate-50/80 px-4 py-2.5">
                  <FileText className="h-3.5 w-3.5 text-slate-400" />
                  <p className="text-xs font-semibold text-slate-800">
                    {text(table.title) || "Table"}
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full border-collapse text-xs">
                    <thead>
                      <tr className="bg-white">
                        {asArray(table.columns).map((column, columnIndex) => (
                          <th
                            key={columnIndex}
                            className="border-b border-slate-200 px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500"
                          >
                            {text(column)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {asArray(table.rows).map((row, rowIndex) => (
                        <tr
                          key={rowIndex}
                          className="border-b border-slate-100 transition-colors last:border-0 odd:bg-white even:bg-slate-50/40 hover:bg-blue-50/40"
                        >
                          {asArray(row).map((cell, cellIndex) => (
                            <td
                              key={cellIndex}
                              className="px-4 py-2.5 align-top text-slate-600"
                            >
                              {text(cell)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}

        {references.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Link2 className="h-3.5 w-3.5 text-slate-400" />
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Sources
              </p>
            </div>
            {references.map((reference, index) => (
              <SourceItem key={index} reference={reference} />
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

export default function InvestorReportsPage() {
  const [analysisId, setAnalysisId] = useState("");
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const requestRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    const loadInitialReport = async () => {
      const requested = new URLSearchParams(window.location.search).get("analysis");
      let items: AnalysisRecord[] = [];
      try {
        items = await listAnalyses();
      } catch {
        items = [];
      }
      if (cancelled) return;

      setAnalyses(items);
      const initialId = requested || (items.length > 0 ? String(items[0].id) : "");
      if (!initialId) return;

      setAnalysisId(initialId);
      setLoading(true);
      try {
        const data = await getReport(initialId);
        if (!cancelled) setReport(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load report");
          setReport(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadInitialReport();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadReportById = async (id: string) => {
    if (!id) return;
    const requestId = ++requestRef.current;
    setAnalysisId(id);
    setActiveTab("overview");
    setLoading(true);
    setError(null);
    try {
      const data = await getReport(id);
      if (requestRef.current !== requestId) return;
      setReport(data);
      const url = new URL(window.location.href);
      url.searchParams.set("analysis", id);
      window.history.replaceState(null, "", url.toString());
    } catch (err) {
      if (requestRef.current !== requestId) return;
      setError(err instanceof Error ? err.message : "Failed to load report");
      setReport(null);
    } finally {
      if (requestRef.current === requestId) setLoading(false);
    }
  };

  const loadReport = () => {
    void loadReportById(analysisId);
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
  const evidenceReferences = (asArray(report?.evidence_references) as Record<string, unknown>[]).filter((reference) =>
    isVerified(reference.verification_status)
  );
  const questions = asArray(report?.investor_questions).map(text);
  const reliability = (asArray(report?.source_reliability) as Record<string, unknown>[]).filter((item) =>
    isVerified(item.verification_status)
  );
  const contradictions = asArray(report?.contradictions) as Record<string, unknown>[];

  const rawAssessment = (report?.controller_assessment ??
    null) as Record<string, unknown> | null;
  const rawAssessmentSummary = text(rawAssessment?.summary).trim();
  const assessmentIsUsable =
    Boolean(rawAssessment) &&
    rawAssessmentSummary.length > 0 &&
    !/^mock$/i.test(rawAssessmentSummary) &&
    !/assessment unavailable/i.test(rawAssessmentSummary);
  const fallbackSummary = report
    ? [
        `Overall risk is assessed as ${(humanize(report.overall_risk) || "unknown").toLowerCase()}.`,
        `Evidence is ${(humanize(report.evidence_status) || "unavailable").toLowerCase()}, with ${countLabel(
          asArray(report.missing_information).length,
          "open information gap"
        )} to resolve before an investment decision.`,
        asArray(report.failed_agents).length > 0
          ? `${countLabel(
              asArray(report.failed_agents).length,
              "specialist agent"
            )} did not complete successfully.`
          : "",
      ]
        .filter(Boolean)
        .join(" ")
    : "";

  const assessment = assessmentIsUsable
    ? rawAssessment
    : report
      ? {
          summary: fallbackSummary,
          key_risks: asArray(report.major_concerns).map(text),
          missing_information: asArray(report.missing_information).map(text),
          recommended_next_steps: text(report.recommendation)
            ? [text(report.recommendation)]
            : [],
        }
      : null;
  const assessmentCategories = assessment
    ? [
        {
          label: "Key risks",
          icon: AlertTriangle,
          tone: "critical" as Tone,
          items: asArray(assessment.key_risks).map(text).filter(Boolean),
        },
        {
          label: "Missing information",
          icon: Search,
          tone: "warning" as Tone,
          items: asArray(assessment.missing_information).map(text).filter(Boolean),
        },
        {
          label: "Recommended next steps",
          icon: TrendingUp,
          tone: "neutral" as Tone,
          items: asArray(assessment.recommended_next_steps).map(text).filter(Boolean),
        },
      ].filter((category) => category.items.length > 0)
    : [];

  const verificationSummary = (report?.verification_summary ??
    null) as Record<string, unknown> | null;

  const sectionByTitle = (title: string) =>
    sections.find((section) => text(section.title) === title);

  const overviewSections = [
    sectionByTitle("What Should the Investor Do?"),
    sectionByTitle("Investment Scorecard"),
    sectionByTitle("Final Investor Decision Guidance"),
  ].filter(Boolean) as Record<string, unknown>[];

  const findingSections = [
    sectionByTitle("Reasons to Consider Investing"),
    sectionByTitle("Major Risks and Red Flags"),
    sectionByTitle("Agent-by-Agent Analysis"),
  ].filter(Boolean) as Record<string, unknown>[];

  const evidenceSection = sectionByTitle("Evidence and Sources");
  const gapSection = sectionByTitle("Missing Information and Due Diligence Checklist");
  const verificationSection = sections.find((section) =>
    text(section.title).toLowerCase().includes("verification")
  );

  const tabs = [
    { key: "overview" as const, label: "Overview", Icon: Gauge },
    { key: "findings" as const, label: "Findings", Icon: ListChecks },
    { key: "verification" as const, label: "Verification", Icon: ShieldCheck },
    { key: "gaps" as const, label: "Gaps & Questions", Icon: AlertTriangle },
  ];

  const knownAnalysis = analyses.some((item) => String(item.id) === analysisId);

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Investor reports"
        title="Investor report"
        description="Review the generated due diligence memo, inspect the evidence, and export a board-ready PDF."
      />

      <Card className="border-slate-200/70 bg-white/85 p-5 shadow-soft backdrop-blur-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <div className="min-w-0 flex-1">
            <label className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Select analysis
            </label>
            <div className="relative mt-2">
              <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <select
                value={analysisId}
                onChange={(event) => void loadReportById(event.target.value)}
                className="h-11 w-full appearance-none rounded-xl border border-slate-200 bg-white pl-10 pr-10 text-sm font-medium text-slate-700 shadow-sm outline-none transition focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
              >
                {!analysisId && <option value="">Choose an analysis…</option>}
                {analysisId && !knownAnalysis && (
                  <option value={analysisId}>Analysis {analysisId}</option>
                )}
                {analyses.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.id} — {item.startup_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            </div>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button
              onClick={loadReport}
              disabled={loading || !analysisId}
              className="min-w-[8.5rem]"
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              {loading ? "Loading…" : "Load report"}
            </Button>
            <Button
              variant="secondary"
              onClick={handleDownload}
              disabled={downloading || !analysisId}
            >
              {downloading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              {downloading ? "Exporting…" : "Export PDF"}
            </Button>
          </div>
        </div>

        {analyses.length > 0 && (
          <p className="mt-3 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
            <span className="font-semibold text-slate-600">Recent:</span>
            {analyses.slice(0, 5).map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => void loadReportById(String(item.id))}
                className={`rounded-full px-2.5 py-1 font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 ${
                  String(item.id) === analysisId
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {item.startup_name}
              </button>
            ))}
          </p>
        )}

        {error && (
          <div className="mt-4 flex items-start gap-3 rounded-xl border border-rose-200/80 bg-rose-50/80 px-4 py-3 text-xs text-rose-700">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="leading-relaxed">{error}</p>
          </div>
        )}
      </Card>

      {loading && !report && (
        <Card className="p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-5 w-48 rounded-full bg-slate-200/80" />
            <div className="h-4 w-full rounded-full bg-slate-100" />
            <div className="h-4 w-4/5 rounded-full bg-slate-100" />
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[0, 1, 2, 3].map((item) => (
                <div key={item} className="h-24 rounded-2xl bg-slate-100" />
              ))}
            </div>
          </div>
        </Card>
      )}

      {!report && !loading && !error && (
        <Card className="relative overflow-hidden p-10 text-center">
          <div className="pointer-events-none absolute -left-16 -top-16 h-48 w-48 rounded-full bg-blue-500/10 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 -right-10 h-48 w-48 rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="relative mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-glow">
            <FileText className="h-6 w-6" />
          </div>
          <h3 className="relative mt-4 text-lg font-semibold tracking-tight text-slate-900">
            No report loaded yet
          </h3>
          <p className="relative mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-500">
            Choose a completed analysis above and load its investor report to
            review findings, verification, gaps, and the final recommendation.
          </p>
        </Card>
      )}

      {report && (
        <>
          <section className="relative overflow-hidden rounded-3xl border border-slate-200/70 bg-gradient-to-br from-white via-blue-50/40 to-indigo-50/40 px-6 py-7 shadow-soft sm:px-8 sm:py-8">
            <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-blue-200/40 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-32 left-1/3 h-64 w-64 rounded-full bg-indigo-200/30 blur-3xl" />
            <div className="pointer-events-none absolute inset-0 bg-grid opacity-[0.4]" />

            <div className="relative">
              <div className="flex flex-wrap items-center gap-2">
                <HeroPill tone={riskVariant(report.overall_risk)}>
                  {humanize(report.overall_risk) || "Unknown"} risk
                </HeroPill>
                <HeroPill tone={assessmentTone(report.final_assessment_category)}>
                  {text(report.final_assessment_category) || "Unavailable"}
                </HeroPill>
                <HeroPill tone={verificationTone(report.verification_status)}>
                  {humanize(report.verification_status) || "Unavailable"} verification
                </HeroPill>
              </div>

              <div className="mt-5 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl">
                  <h2 className="text-balance text-2xl font-bold tracking-[-0.03em] text-slate-900 sm:text-[30px] sm:leading-tight">
                    {text(report.title) || "Investor Due Diligence Report"}
                  </h2>
                  <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600">
                    {text(report.executive_summary)}
                  </p>
                </div>

                <div className="w-full max-w-sm rounded-2xl border border-slate-200/70 bg-white/85 p-4 shadow-sm backdrop-blur-sm">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Recommendation
                  </p>
                  <p className="mt-1.5 text-sm font-medium leading-relaxed text-slate-800">
                    {text(report.recommendation) || "Review the report before deciding."}
                  </p>
                  <div className="mt-4 flex items-center gap-2 border-t border-slate-200/70 pt-3 text-[11px] text-slate-500">
                    <CalendarDays className="h-3.5 w-3.5" />
                    Generated {formatDate(report.generated_at)}
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <HeroStat
                  label="Overall risk"
                  value={humanize(report.overall_risk) || "Unknown"}
                  detail={text(report.overall_assessment)}
                  tone={riskVariant(report.overall_risk)}
                />
                <HeroStat
                  label="Verification"
                  value={humanize(report.verification_status) || "Unavailable"}
                  detail={`${asArray(report.missing_information).length} missing items`}
                  tone={verificationTone(report.verification_status)}
                />
                <HeroStat
                  label="Evidence"
                  value={humanize(report.evidence_status) || "Unavailable"}
                  detail={`${asArray(report.evidence_references).length} references`}
                  tone={verificationTone(report.evidence_status)}
                />
                <HeroStat
                  label="Final assessment"
                  value={text(report.final_assessment_category) || "Unavailable"}
                  detail={`${asArray(report.failed_agents).length} failed agents`}
                  tone={assessmentTone(report.final_assessment_category)}
                />
              </div>
            </div>
          </section>

          {(() => {
            const verdict = investmentVerdict(report.final_assessment_category);
            const Icon = verdict.Icon;
            const topRisks = asArray(report.major_concerns)
              .map(text)
              .filter(Boolean)
              .slice(0, 4);
            return (
              <div
                className={`relative overflow-hidden rounded-3xl border p-7 shadow-lift animate-fade-up ${toneStyles[verdict.tone].soft}`}
              >
                <div
                  className={`pointer-events-none absolute inset-x-0 top-0 h-1.5 ${toneStyles[verdict.tone].bar}`}
                />
                <div className="pointer-events-none absolute -right-12 -top-12 h-48 w-48 rounded-full bg-white/50 blur-3xl" />
                <div className="pointer-events-none absolute -bottom-16 left-1/4 h-40 w-40 rounded-full bg-white/40 blur-3xl" />
                <div className="relative flex flex-col gap-5 sm:flex-row sm:items-start">
                  <span
                    className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-3xl bg-white shadow-md ring-1 ring-inset ${toneStyles[verdict.tone].ring} ${toneStyles[verdict.tone].text}`}
                  >
                    <Icon className="h-8 w-8" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                        Investment decision
                      </p>
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ring-1 ring-inset ${toneStyles[verdict.tone].soft} ${toneStyles[verdict.tone].text}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${toneStyles[verdict.tone].dot}`} />
                        Verdict
                      </span>
                    </div>
                    <h3
                      className={`mt-1.5 text-3xl font-extrabold tracking-tight ${toneStyles[verdict.tone].text}`}
                    >
                      {verdict.label}
                    </h3>
                    <p className="mt-3 text-sm leading-relaxed text-slate-700">
                      {decisionMessage(report)}
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-600">
                      {text(report.recommendation)}
                    </p>
                    {topRisks.length > 0 && (
                      <div className="mt-5">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                          Key considerations
                        </p>
                        <ul className="mt-2 grid gap-2 sm:grid-cols-2">
                          {topRisks.map((risk, index) => (
                            <li
                              key={index}
                              className="flex items-start gap-2.5 rounded-2xl bg-white/85 px-3.5 py-2.5 text-xs leading-relaxed text-slate-700 shadow-sm transition-shadow hover:shadow-ring"
                            >
                              <span
                                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${toneStyles[verdict.tone].dot}`}
                              />
                              <span>{risk}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })()}

          <div className="flex flex-wrap items-center gap-1.5 rounded-2xl border border-slate-200/70 bg-white/80 p-1.5 shadow-sm backdrop-blur-sm">
            {tabs.map(({ key, label, Icon }) => (
              <button
                key={key}
                type="button"
                onClick={() => setActiveTab(key)}
                className={`inline-flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 focus-visible:ring-offset-2 sm:flex-none ${
                  activeTab === key
                    ? "bg-gradient-to-b from-blue-500 to-blue-600 text-white shadow-[0_10px_24px_-14px_rgba(37,99,235,0.9)]"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </div>

          {activeTab === "overview" && (
            <div className="space-y-5">
              {assessment && (
                <Card className="relative overflow-hidden border-blue-200/70 bg-gradient-to-br from-blue-50/90 via-indigo-50/60 to-white p-6 animate-fade-up">
                  <div className="pointer-events-none absolute -right-16 -top-16 h-44 w-44 rounded-full bg-blue-500/10 blur-3xl" />
                  <div className="relative">
                    <div className="mb-4 flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-blue-600 shadow-sm ring-1 ring-blue-200/70">
                        <Sparkles className="h-5 w-5" />
                      </span>
                      <div>
                        <h3 className="text-sm font-semibold tracking-tight text-slate-900">
                          {assessmentIsUsable
                            ? "Controller assessment"
                            : "Assessment summary"}
                        </h3>
                        <p className="mt-0.5 text-[11px] font-medium text-slate-500">
                          Synthesis of specialist findings, verification, and open gaps
                        </p>
                      </div>
                    </div>
                    <p className="text-sm leading-relaxed text-slate-700">
                      {text(assessment.summary) || "No assessment summary is available."}
                    </p>
                    {assessmentCategories.length > 0 && (
                      <div className="mt-4 grid gap-3 md:grid-cols-3">
                        {assessmentCategories.map((category) => {
                          const Icon = category.icon;
                          return (
                            <div
                              key={category.label}
                              className={`rounded-2xl border bg-white/85 p-4 shadow-sm ${toneStyles[category.tone].soft}`}
                            >
                              <div className="flex items-center gap-2">
                                <span
                                  className={`flex h-7 w-7 items-center justify-center rounded-lg bg-white ring-1 ring-inset ${toneStyles[category.tone].ring} ${toneStyles[category.tone].text}`}
                                >
                                  <Icon className="h-3.5 w-3.5" />
                                </span>
                                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                                  {category.label}
                                </p>
                              </div>
                              <ul className="mt-3 space-y-1.5">
                                {category.items.map((item, index) => (
                                  <li
                                    key={index}
                                    className="flex gap-2 text-xs leading-relaxed text-slate-600"
                                  >
                                    <span
                                      className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${toneStyles[category.tone].dot}`}
                                    />
                                    <span>{item}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {overviewSections.map((section, index) => (
                <SectionCard key={index} section={section} />
              ))}

              {charts.length > 0 && (
                <Card className="p-6 animate-fade-up">
                  <div className="mb-4 flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-inset ring-blue-200/70">
                      <BarChart3 className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold tracking-tight text-slate-900">
                        Risk and verification overview
                      </h3>
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        Distribution of findings across the report
                      </p>
                    </div>
                  </div>
                  <div className="grid gap-4 lg:grid-cols-2">
                    {charts.map((chart, index) => (
                      <Chart key={index} chart={chart} />
                    ))}
                  </div>
                </Card>
              )}

              {evidenceSection && <SectionCard section={evidenceSection} />}

              {!evidenceSection && evidenceReferences.length > 0 && (
                <Card className="p-6 animate-fade-up">
                  <div className="mb-4 flex items-center gap-2">
                    <Link2 className="h-4 w-4 text-blue-600" />
                    <h3 className="text-sm font-semibold text-slate-900">
                      Evidence and sources
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {evidenceReferences.map((reference, index) => (
                      <SourceItem key={index} reference={reference} />
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}

          {activeTab === "findings" && (
            <div className="space-y-5">
              {findingSections.map((section, index) => (
                <SectionCard key={index} section={section} />
              ))}
              {findingSections.length === 0 && (
                <Card className="p-8 text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
                    <ListChecks className="h-5 w-5" />
                  </div>
                  <p className="mt-3 text-sm font-semibold text-slate-800">
                    No findings sections were included in this report.
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Re-run the analysis to generate a complete findings set.
                  </p>
                </Card>
              )}
            </div>
          )}

          {activeTab === "verification" && (
            <div className="space-y-5">
              <Card className="p-6 animate-fade-up">
                <div className="mb-4 flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 ring-1 ring-inset ring-emerald-200/70">
                    <ShieldCheck className="h-5 w-5" />
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold tracking-tight text-slate-900">
                      Verification summary
                    </h3>
                    <p className="mt-0.5 text-[11px] text-slate-500">
                      Claims cross-checked against stored evidence
                    </p>
                  </div>
                </div>

                {verificationSummary ? (
                  <>
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      {[
                        {
                          label: "Status",
                          value:
                            humanize(
                              verificationSummary.verification_status ??
                                verificationSummary.status
                            ) || "Unavailable",
                        },
                        {
                          label: "Claims reviewed",
                          value: text(verificationSummary.total_findings ?? 0),
                        },
                        {
                          label: "Valid references",
                          value: `${text(
                            verificationSummary.valid_references ?? 0
                          )} of ${text(verificationSummary.checked_references ?? 0)}`,
                        },
                        {
                          label: "Contradictions",
                          value: text(
                            asArray(verificationSummary.contradictions).length
                          ),
                        },
                      ].map((metric) => (
                        <div
                          key={metric.label}
                          className="rounded-2xl border border-slate-200/70 bg-slate-50/70 p-4"
                        >
                          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                            {metric.label}
                          </p>
                          <p className="mt-1.5 text-lg font-semibold tracking-tight text-slate-800">
                            {metric.value}
                          </p>
                        </div>
                      ))}
                    </div>
                    {verificationSummary.detailed_reasoning ? (
                      <p className="mt-4 text-sm leading-relaxed text-slate-600">
                        {text(verificationSummary.detailed_reasoning)}
                      </p>
                    ) : null}
                    {asArray(verificationSummary.issues).length > 0 && (
                      <div className="mt-4 rounded-xl border border-amber-200/70 bg-amber-50/70 p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-amber-700">
                          Issues
                        </p>
                        <ul className="mt-2 space-y-1 text-xs leading-relaxed text-amber-800">
                          {asArray(verificationSummary.issues).map((issue, index) => (
                            <li key={index} className="flex gap-2">
                              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                              {text(issue)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
                    No verification output is available for this report.
                  </p>
                )}
              </Card>

              {verificationSection && <SectionCard section={verificationSection} />}

              {contradictions.length > 0 && (
                <Card className="border-amber-200/70 bg-amber-50/50 p-6 animate-fade-up">
                  <div className="mb-4 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <h3 className="text-sm font-semibold text-slate-900">
                      Contradictions
                    </h3>
                  </div>
                  <ul className="space-y-2 text-sm text-slate-700">
                    {contradictions.map((contradiction, index) => (
                      <li
                        key={index}
                        className="rounded-xl border border-amber-200/70 bg-white/85 px-4 py-3 leading-relaxed"
                      >
                        {text(contradiction.reasoning) ||
                          text(contradiction.claim_a) ||
                          text(contradiction)}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {reliability.length > 0 && (
                <Card className="p-6 animate-fade-up">
                  <div className="mb-4 flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600 ring-1 ring-inset ring-violet-200/70">
                      <Layers3 className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold tracking-tight text-slate-900">
                        Source reliability
                      </h3>
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        Confidence assigned to each evidence record
                      </p>
                    </div>
                  </div>
                  <div className="overflow-hidden rounded-2xl border border-slate-200/70">
                    <div className="overflow-x-auto">
                      <table className="min-w-full border-collapse text-xs">
                        <thead>
                          <tr className="bg-slate-50/80">
                            {["Evidence", "Status", "Reliability", "Score"].map(
                              (heading) => (
                                <th
                                  key={heading}
                                  className="border-b border-slate-200 px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500"
                                >
                                  {heading}
                                </th>
                              )
                            )}
                          </tr>
                        </thead>
                        <tbody>
                          {reliability.map((item, index) => (
                            <tr
                              key={index}
                              className="border-b border-slate-100 transition-colors last:border-0 odd:bg-white even:bg-slate-50/40 hover:bg-blue-50/40"
                            >
                              <td className="px-4 py-2.5 text-slate-700">
                                {text(item.source_title) ||
                                  `Evidence ${text(item.evidence_id)}`}
                              </td>
                              <td className="px-4 py-2.5 text-slate-600">
                                {humanize(item.verification_status) || "Unknown"}
                              </td>
                              <td className="px-4 py-2.5">
                                <span
                                  className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                                    toneStyles[
                                      riskVariant(item.reliability_level)
                                    ].soft
                                  } ${toneStyles[riskVariant(item.reliability_level)].text}`}
                                >
                                  {humanize(item.reliability_level) || "Unknown"}
                                </span>
                              </td>
                              <td className="px-4 py-2.5 font-medium tabular-nums text-slate-600">
                                {text(item.reliability_score)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </Card>
              )}
            </div>
          )}

          {activeTab === "gaps" && (
            <div className="space-y-5">
              {gapSection ? (
                <SectionCard section={gapSection} />
              ) : (
                asArray(report.missing_information).length > 0 && (
                  <Card className="p-6 animate-fade-up">
                    <div className="mb-4 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      <h3 className="text-sm font-semibold text-slate-900">
                        Information gaps
                      </h3>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {asArray(report.missing_information).map((item, index) => (
                        <div
                          key={index}
                          className="rounded-xl border border-amber-200/70 bg-amber-50/60 px-3 py-2 text-xs text-amber-800"
                        >
                          {text(item)}
                        </div>
                      ))}
                    </div>
                  </Card>
                )
              )}

              {questions.length > 0 && (
                <Card className="p-6 animate-fade-up">
                  <div className="mb-4 flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-inset ring-blue-200/70">
                      <FileText className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold tracking-tight text-slate-900">
                        Investor questions
                      </h3>
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        Questions to resolve before an investment decision
                      </p>
                    </div>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {questions.map((question, index) => (
                      <div
                        key={index}
                        className="flex gap-3 rounded-2xl border border-slate-200/70 bg-slate-50/60 p-4 text-sm leading-relaxed text-slate-700"
                      >
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-[10px] font-semibold text-blue-600 ring-1 ring-blue-200/70">
                          {index + 1}
                        </span>
                        {question}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {report.disclaimer ? (
                <Card className="border-slate-200/70 bg-slate-50/70 p-5 animate-fade-up">
                  <div className="flex gap-3">
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
                    <p className="text-xs leading-relaxed text-slate-500">
                      {text(report.disclaimer)}
                    </p>
                  </div>
                </Card>
              ) : null}
            </div>
          )}
        </>
      )}
    </div>
  );
}
