"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { downloadReportPdf, getReport, listAnalyses, type AnalysisRecord } from "@/lib/api";

export default function InvestorReportsPage() {
  const [analysisId, setAnalysisId] = useState("");
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([]);
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
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

  const sections = Array.isArray(report?.sections) ? report.sections : [];

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Investor reports"
        title="Investor report"
        description="Load a generated report by analysis ID and export it as PDF."
      />

      <Card className="p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="text-xs font-medium text-text-secondary">Analysis ID</label>
            <Input
              value={analysisId}
              onChange={(event) => setAnalysisId(event.target.value)}
              className="mt-1"
            />
          </div>
          <Button onClick={loadReport} disabled={loading}>
            {loading ? "Loading..." : "Load report"}
          </Button>
          <Button variant="secondary" onClick={handleDownload} disabled={downloading}>
            {downloading ? "Downloading..." : "Download PDF"}
          </Button>
        </div>
        {analyses.length > 0 && (
          <p className="mt-3 text-xs text-text-secondary">
            Available analyses: {analyses.map((item) => item.id).join(", ")}
          </p>
        )}
        {error && <p className="mt-3 text-sm text-critical">{error}</p>}
      </Card>

      {report && (
        <>
          <Card className="p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="warning">{String(report.overall_risk ?? "Unknown")} risk</Badge>
              <Badge variant="default">
                {String(report.final_assessment_category ?? "Unavailable")}
              </Badge>
            </div>
            <h2 className="mt-4 text-lg font-semibold text-text-primary">
              {String(report.title ?? "Investor Due Diligence Report")}
            </h2>
            <p className="mt-2 text-sm text-text-secondary">
              {String(report.executive_summary ?? "")}
            </p>
          </Card>

          <div className="grid gap-4">
            {sections.map((section: any, index: number) => (
              <Card key={index} className="p-6">
                <h3 className="text-sm font-semibold text-text-primary">
                  {String(section.title ?? `Section ${index + 1}`)}
                </h3>
                <div className="mt-3 space-y-2">
                  {Array.isArray(section.content) &&
                    section.content.map((paragraph: any, pIndex: number) => (
                      <p key={pIndex} className="text-sm text-text-secondary">
                        {String(paragraph)}
                      </p>
                    ))}
                </div>
                {Array.isArray(section.risk_indicators) && section.risk_indicators.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {section.risk_indicators.map((indicator: any, iIndex: number) => (
                      <Badge key={iIndex} variant="warning">
                        {String((indicator as Record<string, unknown>).label)}: {String((indicator as Record<string, unknown>).level)}
                      </Badge>
                    ))}
                  </div>
                )}
                {Array.isArray(section.tables) && section.tables.length > 0 && (
                  <div className="mt-4 space-y-4">
                    {section.tables.map((table: any, tIndex: number) => (
                      <div key={tIndex} className="overflow-x-auto">
                        <p className="text-xs font-semibold text-text-primary">
                          {String(table.title ?? "Table")}
                        </p>
                        <table className="mt-2 min-w-full border-collapse text-xs">
                          <thead>
                            <tr>
                              {Array.isArray(table.columns) &&
                                table.columns.map((column: any, cIndex: number) => (
                                  <th
                                    key={cIndex}
                                    className="border border-border bg-secondary/40 px-2 py-1 text-left"
                                  >
                                    {String(column)}
                                  </th>
                                ))}
                            </tr>
                          </thead>
                          <tbody>
                            {Array.isArray(table.rows) &&
                              table.rows.map((row: any, rIndex: number) => (
                                <tr key={rIndex}>
                                  {Array.isArray(row) &&
                                    row.map((cell: any, cellIndex: number) => (
                                      <td
                                        key={cellIndex}
                                        className="border border-border px-2 py-1 text-text-secondary"
                                      >
                                        {String(cell)}
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
            ))}
          </div>
        </>
      )}
    </div>
  );
}
