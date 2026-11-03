export type DemoAnalysisStatus = "Completed" | "In progress" | "Pending";
export type DemoAssessment = "Strong" | "Moderate" | "High risk";

export interface DemoAnalysis {
  id: string;
  name: string;
  industry: string;
  date: string;
  status: DemoAnalysisStatus;
  assessment: DemoAssessment;
  website: string;
  country: string;
}

export const demoAnalyses: DemoAnalysis[] = [
  {
    id: "demo-1",
    name: "Acme Robotics",
    industry: "Industrial automation",
    date: "Oct 28, 2026",
    status: "Completed",
    assessment: "Strong",
    website: "https://acme-robotics.example",
    country: "United States",
  },
  {
    id: "demo-2",
    name: "Northwind Health",
    industry: "Digital health",
    date: "Oct 24, 2026",
    status: "Completed",
    assessment: "Strong",
    website: "https://northwind-health.example",
    country: "Canada",
  },
  {
    id: "demo-3",
    name: "Lumen Payments",
    industry: "Fintech infrastructure",
    date: "Oct 21, 2026",
    status: "In progress",
    assessment: "Moderate",
    website: "https://lumen-payments.example",
    country: "United Kingdom",
  },
  {
    id: "demo-4",
    name: "Atlas Energy",
    industry: "Climate tech",
    date: "Oct 18, 2026",
    status: "Completed",
    assessment: "High risk",
    website: "https://atlas-energy.example",
    country: "Germany",
  },
  {
    id: "demo-5",
    name: "Orbit Commerce",
    industry: "Marketplace",
    date: "Oct 14, 2026",
    status: "Pending",
    assessment: "Moderate",
    website: "https://orbit-commerce.example",
    country: "Singapore",
  },
  {
    id: "demo-6",
    name: "Vertex Bio",
    industry: "Biotechnology",
    date: "Oct 11, 2026",
    status: "Completed",
    assessment: "Strong",
    website: "https://vertex-bio.example",
    country: "United States",
  },
  {
    id: "demo-7",
    name: "Harbor Logistics",
    industry: "Supply chain",
    date: "Oct 06, 2026",
    status: "In progress",
    assessment: "Moderate",
    website: "https://harbor-logistics.example",
    country: "Netherlands",
  },
  {
    id: "demo-8",
    name: "Cobalt AI",
    industry: "Enterprise software",
    date: "Oct 02, 2026",
    status: "Completed",
    assessment: "Strong",
    website: "https://cobalt-ai.example",
    country: "Israel",
  },
];

export const demoActivity = [
  {
    id: "activity-1",
    title: "Acme Robotics analysis completed",
    detail: "Investor report is ready for review",
    time: "2 hours ago",
    kind: "report" as const,
  },
  {
    id: "activity-2",
    title: "Lumen Payments advanced to analysis",
    detail: "Five agents are processing the company record",
    time: "5 hours ago",
    kind: "agent" as const,
  },
  {
    id: "activity-3",
    title: "Northwind Health evidence verified",
    detail: "42 claims cross-referenced against public sources",
    time: "Yesterday",
    kind: "evidence" as const,
  },
  {
    id: "activity-4",
    title: "Orbit Commerce submitted",
    detail: "Waiting to enter the analysis queue",
    time: "Yesterday",
    kind: "queue" as const,
  },
];
