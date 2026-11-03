"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bot,
  FileText,
  History,
  LayoutDashboard,
  Menu,
  PlusCircle,
  Search,
  Settings,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
  alsoMatches?: string;
}

const workspaceNav: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    href: "/dashboard/new",
    label: "New Due Diligence",
    icon: PlusCircle,
  },
  {
    href: "/dashboard/analysis-history",
    label: "Analysis History",
    icon: History,
    alsoMatches: "/dashboard/analyses",
  },
  {
    href: "/dashboard/agents",
    label: "Agent Analysis",
    icon: Bot,
  },
  {
    href: "/dashboard/reports",
    label: "Investor Reports",
    icon: FileText,
  },
  {
    href: "/dashboard/evidence",
    label: "Evidence Explorer",
    icon: Search,
  },
];

const accountNav: NavItem[] = [
  {
    href: "/dashboard/settings",
    label: "Settings",
    icon: Settings,
  },
];

export function DashboardShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const isActive = (item: NavItem) => {
    if (item.exact) return pathname === item.href;
    if (pathname.startsWith(item.href)) return true;
    return Boolean(item.alsoMatches && pathname.startsWith(item.alsoMatches));
  };

  return (
    <div className="min-h-screen bg-background">
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Close navigation"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-white transition-transform duration-200 lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-border px-5">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-accent shadow-sm shadow-blue-200">
              <span className="text-xs font-bold tracking-widest text-white">
                V
              </span>
            </div>
            <span className="text-lg font-bold tracking-tight text-text-primary">
              Ventrix
            </span>
          </Link>
          <button
            type="button"
            className="rounded-sm p-1.5 text-text-secondary hover:bg-secondary lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-4 pt-5">
          <Link
            href="/dashboard/new"
            className="group block rounded-sm border border-blue-200 bg-blue-50 p-4 transition-colors duration-200 hover:bg-blue-100/70"
          >
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-blue-accent">
              <PlusCircle className="h-3.5 w-3.5" />
              Quick action
            </div>
            <p className="mt-2 text-sm font-semibold text-text-primary">
              New Due Diligence
            </p>
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">
              Submit a company for analysis.
            </p>
          </Link>
        </div>

        <nav
          className="flex-1 overflow-y-auto px-3 py-5"
          aria-label="Dashboard navigation"
        >
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
            Workspace
          </p>
          <div className="space-y-1">
            {workspaceNav.map((item) => {
              const Icon = item.icon;
              const active = isActive(item);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-sm px-3 py-2.5 text-sm font-medium transition-colors duration-200 ${
                    active
                      ? "bg-blue-50 text-blue-accent"
                      : "text-text-secondary hover:bg-secondary hover:text-text-primary"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </div>

          <p className="mt-6 px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
            Account
          </p>
          <div className="space-y-1">
            {accountNav.map((item) => {
              const Icon = item.icon;
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-sm px-3 py-2.5 text-sm font-medium transition-colors duration-200 ${
                    active
                      ? "bg-blue-50 text-blue-accent"
                      : "text-text-secondary hover:bg-secondary hover:text-text-primary"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>

        <div className="border-t border-border p-4">
          <Link
            href="/"
            className="mb-4 block text-xs font-medium text-text-secondary transition-colors duration-200 hover:text-blue-accent"
          >
            ← Back to marketing site
          </Link>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-accent text-xs font-semibold text-white">
              AM
            </div>
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-text-primary">
                Alex Morgan
              </p>
              <p className="truncate text-[11px] text-text-secondary">
                Investment team
              </p>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-white/90 px-4 backdrop-blur sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-sm p-2 text-text-secondary hover:bg-secondary lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <p className="text-sm font-semibold text-text-primary">
                Investor workspace
              </p>
              <p className="text-[11px] text-text-secondary">
                Due diligence command center
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="warning">Preview workspace</Badge>
            <div className="hidden items-center gap-2.5 border-l border-border pl-3 sm:flex">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-accent text-[11px] font-semibold text-white">
                AM
              </div>
              <div className="leading-tight">
                <p className="text-xs font-semibold text-text-primary">
                  Alex Morgan
                </p>
                <p className="text-[10px] text-text-secondary">
                  Investment team
                </p>
              </div>
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
