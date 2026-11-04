import {
  Bot,
  FileText,
  History,
  LayoutDashboard,
  PlusCircle,
  Search,
  Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  description: string;
  exact?: boolean;
  alsoMatches?: string;
}

export const workspaceNav: NavItem[] = [
  {
    href: "/dashboard",
    label: "Overview",
    description: "Portfolio health, activity, and live diligence coverage",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    href: "/dashboard/new",
    label: "New Due Diligence",
    description: "Submit a startup for a new analysis",
    icon: PlusCircle,
  },
  {
    href: "/dashboard/analysis-history",
    label: "Analysis History",
    description: "Browse every analysis in the workspace",
    icon: History,
    alsoMatches: "/dashboard/analyses",
  },
  {
    href: "/dashboard/agents",
    label: "Agent Analysis",
    description: "Inspect specialist agent results",
    icon: Bot,
  },
  {
    href: "/dashboard/reports",
    label: "Investor Reports",
    description: "Open and export investor-grade reports",
    icon: FileText,
  },
  {
    href: "/dashboard/evidence",
    label: "Evidence Explorer",
    description: "Search verified sources and findings",
    icon: Search,
  },
];

export const accountNav: NavItem[] = [
  {
    href: "/dashboard/settings",
    label: "Settings",
    description: "Workspace, usage, and provider configuration",
    icon: Settings,
  },
];

export const allNavItems: NavItem[] = [...workspaceNav, ...accountNav];

export function isNavItemActive(item: NavItem, pathname: string) {
  if (item.exact) return pathname === item.href;
  if (pathname.startsWith(item.href)) return true;
  return Boolean(item.alsoMatches && pathname.startsWith(item.alsoMatches));
}
