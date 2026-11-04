"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { searchEvidence, type EvidenceRecord } from "@/lib/api";

export default function EvidenceExplorerPage() {
  const [query, setQuery] = useState("");
  const [analysisId, setAnalysisId] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [items, setItems] = useState<EvidenceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await searchEvidence({
        analysisId: analysisId || undefined,
        query: query || undefined,
        category: category || undefined,
        status: status || undefined,
        limit: 100,
      });
      setItems(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evidence search failed");
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Evidence explorer"
        title="Evidence explorer"
        description="Search and inspect stored evidence, sources, verification status, and related findings."
      />

      <Card className="p-5">
        <div className="grid gap-3 md:grid-cols-4">
          <Input placeholder="Search text" value={query} onChange={(e) => setQuery(e.target.value)} />
          <Input placeholder="Analysis ID" value={analysisId} onChange={(e) => setAnalysisId(e.target.value)} />
          <Input placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} />
          <Input placeholder="Verification status" value={status} onChange={(e) => setStatus(e.target.value)} />
        </div>
        <Button className="mt-4" onClick={load} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </Button>
        {error && <p className="mt-3 text-sm text-critical">{error}</p>}
      </Card>

      <div className="space-y-4">
        {items.map((item) => (
          <Card key={item.id} className="p-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-text-primary">{item.source_title}</span>
              <span className="text-xs text-text-secondary">{item.verification_status}</span>
              <span className="text-xs text-text-secondary">{item.source_category}</span>
              <span className="text-xs text-text-secondary">{item.related_agent}</span>
            </div>
            <p className="mt-2 text-xs text-text-secondary break-all">{item.source_url}</p>
            <p className="mt-3 text-sm text-text-secondary">{item.extracted_information}</p>
            <div className="mt-3 grid gap-2 text-xs text-text-secondary sm:grid-cols-2">
              <span>Publication date: {item.publication_date ?? "Unavailable"}</span>
              <span>Retrieval date: {item.retrieval_date}</span>
              <span>Analysis ID: {item.analysis_id}</span>
              <span>Startup ID: {item.startup_id}</span>
            </div>
            {Array.isArray(item.findings) && item.findings.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-text-primary">Associated findings</p>
                <ul className="mt-1 list-disc pl-5 text-xs text-text-secondary">
                  {item.findings.map((finding, index) => (
                    <li key={index}>{String(finding.dimension ?? finding.summary ?? "Finding")}</li>
                  ))}
                </ul>
              </div>
            )}
          </Card>
        ))}
        {!loading && items.length === 0 && (
          <p className="text-sm text-text-secondary">No evidence found.</p>
        )}
      </div>
    </div>
  );
}
