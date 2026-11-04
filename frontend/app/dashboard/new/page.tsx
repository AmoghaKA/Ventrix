import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowLeft,
  Clock,
  FileCheck2,
  Search,
  ShieldCheck,
} from "lucide-react";
import { NewAnalysisForm } from "@/components/dashboard/new-analysis-form";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "New Due Diligence — Ventrix",
  description: "Submit a startup for evidence-backed due diligence analysis.",
};

const notes = [
  {
    icon: Search,
    title: "Public sources only",
    description:
      "Ventrix analyzes publicly accessible company information, including the company website and other public records.",
  },
  {
    icon: FileCheck2,
    title: "Unavailable data is labeled",
    description:
      "If a data point cannot be verified from public information, it is marked unavailable rather than estimated.",
  },
  {
    icon: Clock,
    title: "Monitoring after submission",
    description:
      "You will be redirected to a monitoring page that tracks the analysis status using its unique analysis ID.",
  },
  {
    icon: ShieldCheck,
    title: "Private workspace",
    description:
      "Submission details stay inside your investor workspace and are not shared with the startup.",
  },
];

export default function NewDueDiligencePage() {
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
        eyebrow="New analysis"
        title="New due diligence"
        description="Provide the essential company details below. Ventrix will create an analysis record and take you to the monitoring page."
      />

      <div className="grid items-start gap-6 xl:grid-cols-[1.5fr_1fr]">
        <Card className="p-6 md:p-7">
          <div className="mb-6 border-b border-border pb-5">
            <h2 className="text-base font-semibold text-text-primary">
              Company details
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">
              Start with the company name and website. Additional context helps
              focus the analysis.
            </p>
          </div>
          <NewAnalysisForm />
        </Card>

        <div className="space-y-4">
          <Card className="p-6">
            <h2 className="text-sm font-semibold text-text-primary">
              How this works
            </h2>
            <ul className="mt-4 space-y-4">
              {notes.map((note) => {
                const Icon = note.icon;
                return (
                  <li key={note.title} className="flex gap-3">
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-sm bg-blue-50 text-blue-accent">
                      <Icon className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-xs font-semibold text-text-primary">
                        {note.title}
                      </p>
                      <p className="mt-1 text-xs leading-relaxed text-text-secondary">
                        {note.description}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>

          <div className="rounded-sm border border-border bg-secondary/50 p-5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
              Data note
            </p>
            <p className="mt-2 text-xs leading-relaxed text-text-secondary">
              Missing information will be marked unavailable in the analysis.
              Ventrix does not invent company metrics or fill gaps with
              estimates.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
