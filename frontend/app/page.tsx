"use client";

import { useRouter } from "next/navigation";
import {
  ArrowRight,
  BarChart3,
  FileCheck2,
  Globe2,
  Landmark,
  Play,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";

const agents = [
  { title: "Financial Analysis", description: "Model revenue, burn, margins, cap table, and unit economics in one intelligent workspace.", icon: BarChart3 },
  { title: "Market Intelligence", description: "Map markets, competitors, trends, and positioning with sourced, decision-ready insights.", icon: Globe2 },
  { title: "Legal & Compliance", description: "Verify entities, IP ownership, litigation exposure, and regulatory readiness with confidence.", icon: ShieldCheck },
  { title: "Evidence Verification", description: "Cross-reference founder claims against trusted sources and flag what needs a closer look.", icon: FileCheck2 },
  { title: "Investor Report", description: "Turn every finding into an institutional-grade memo your investment committee can act on.", icon: Landmark },
];

const workflowSteps = [
  { step: "01", title: "Add a startup", description: "Enter company details, website, and fundraising context." },
  { step: "02", title: "Let agents work", description: "Five specialized agents analyze every dimension in parallel." },
  { step: "03", title: "Review findings", description: "See sourced evidence, confidence scores, and key risks." },
  { step: "04", title: "Share the memo", description: "Export a polished report for your investment committee." },
];

export default function LandingPage() {
  const router = useRouter();

  return (
    <main className="min-h-screen overflow-hidden bg-background selection:bg-blue-accent/20 selection:text-blue-accent">
      <Navbar />

      <section className="relative px-6 pb-20 pt-32 md:pb-28 md:pt-40">
        <div className="absolute left-1/2 top-0 -z-0 h-[540px] w-[900px] -translate-x-1/2 rounded-full bg-blue-100/60 blur-3xl" />
        <div className="relative mx-auto max-w-7xl">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-white/80 px-3 py-1.5 text-xs font-semibold text-blue-accent shadow-sm">
              <Sparkles className="h-3.5 w-3.5" />
              The modern way to do due diligence
            </div>
            <h1 className="text-5xl font-bold leading-[1.05] tracking-[-0.04em] text-text-primary md:text-7xl">
              Make better bets,{" "}
              <span className="text-blue-accent">faster.</span>
            </h1>
            <p className="mx-auto mb-9 mt-7 max-w-2xl text-lg leading-relaxed text-text-secondary md:text-xl">
              Ventrix brings AI-powered research, evidence verification, and investor-grade reporting into one calm, collaborative workspace.
            </p>
            <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button variant="primary" size="lg" className="w-full sm:w-auto" onClick={() => router.push("/dashboard")}>
                Start due diligence <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button variant="secondary" size="lg" className="w-full sm:w-auto">
                <Play className="mr-2 h-4 w-4 fill-current" /> See how it works
              </Button>
            </div>
            <p className="mt-5 text-xs font-medium text-text-secondary">No credit card required · Set up in 2 minutes</p>
          </div>

          <div className="relative mx-auto mt-16 max-w-5xl">
            <div className="absolute -inset-4 rounded-[22px] bg-blue-200/30 blur-2xl" />
            <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl shadow-slate-200/70">
              <div className="flex items-center justify-between border-b border-border bg-slate-50/80 px-5 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-red-300" /><span className="h-2.5 w-2.5 rounded-full bg-amber-300" /><span className="h-2.5 w-2.5 rounded-full bg-emerald-300" /></div>
                  <span className="ml-3 text-xs font-medium text-slate-500">Ventrix / Workspace preview</span>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold text-slate-500">PREVIEW</span>
              </div>
              <div className="p-6">
                <p className="text-sm text-text-secondary">
                  Run an analysis to populate this workspace with live results.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="agents" className="border-y border-border bg-white px-6 py-24">
        <div className="mx-auto max-w-7xl">
          <div className="mb-14 max-w-2xl"><p className="mb-3 text-sm font-bold uppercase tracking-widest text-blue-accent">One platform, full context</p><h2 className="text-3xl font-bold tracking-tight text-text-primary md:text-4xl">Every angle covered. Every claim grounded.</h2><p className="mt-4 leading-relaxed text-text-secondary">Replace fragmented research with a coordinated intelligence layer built for confident investment decisions.</p></div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => { const Icon = agent.icon; return <Card key={agent.title} padding="lg" className="group"><div className="mb-6 flex h-11 w-11 items-center justify-center rounded-lg bg-blue-50 text-blue-accent transition-colors group-hover:bg-blue-accent group-hover:text-white"><Icon className="h-5 w-5" /></div><CardTitle>{agent.title}</CardTitle><CardDescription className="leading-relaxed">{agent.description}</CardDescription></Card>; })}
          </div>
        </div>
      </section>

      <section id="workflow" className="px-6 py-24">
        <div className="mx-auto max-w-7xl">
          <div className="grid items-start gap-14 lg:grid-cols-[0.8fr_1.2fr]">
            <div><p className="mb-3 text-sm font-bold uppercase tracking-widest text-blue-accent">Simple by design</p><h2 className="text-3xl font-bold tracking-tight text-text-primary md:text-4xl">From first look to conviction.</h2><p className="mt-5 leading-relaxed text-text-secondary">A focused workflow that gives your team more signal, less spreadsheet wrangling, and a clear audit trail for every decision.</p><Button variant="secondary" className="mt-8">Explore the platform <ArrowRight className="ml-2 h-4 w-4" /></Button></div>
            <div className="grid gap-4 sm:grid-cols-2">{workflowSteps.map((step) => <div key={step.step} className="rounded-xl border border-border bg-white p-6 shadow-sm"><span className="text-sm font-bold text-blue-accent">{step.step}</span><h3 className="mt-8 font-bold text-text-primary">{step.title}</h3><p className="mt-2 text-sm leading-relaxed text-text-secondary">{step.description}</p></div>)}</div>
          </div>
        </div>
      </section>

      <section className="px-6 pb-24">
        <div className="mx-auto max-w-5xl overflow-hidden rounded-2xl bg-slate-900 px-6 py-16 text-center shadow-xl shadow-slate-300/50 md:px-12"><div className="mx-auto max-w-2xl"><p className="mb-4 text-sm font-bold uppercase tracking-widest text-blue-300">Move with confidence</p><h2 className="text-3xl font-bold tracking-tight text-white md:text-5xl">Your next great investment deserves better diligence.</h2><p className="mx-auto mt-5 max-w-xl text-slate-300">Start your first analysis today and see what your team can uncover in minutes.</p><Button variant="primary" size="lg" className="mt-8 bg-white text-blue-accent hover:bg-blue-50" onClick={() => router.push("/dashboard")}>Start your free analysis <ArrowRight className="ml-2 h-4 w-4" /></Button></div></div>
      </section>
      <Footer />
    </main>
  );
}
