"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bell,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  Command,
  HelpCircle,
  LogOut,
  Menu,
  Search,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/auth/auth-provider";
import { CommandPalette } from "./command-palette";
import {
  accountNav,
  allNavItems,
  isNavItemActive,
  workspaceNav,
  type NavItem,
} from "./navigation";

export function DashboardShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading: authLoading, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Protect the dashboard: redirect unauthenticated users to sign in.
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/sign-in");
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const displayName =
    (user?.user_metadata?.full_name as string | undefined) ||
    user?.email ||
    "User";
  const initials = (displayName || "U")
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-blue-accent" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const currentPage =
    allNavItems.find((item) => isNavItemActive(item, pathname)) ??
    allNavItems[0];

  const renderNavItem = (item: NavItem) => {
    const Icon = item.icon;
    const active = isNavItemActive(item, pathname);
    return (
      <Link
        key={item.href}
        href={item.href}
        aria-current={active ? "page" : undefined}
        className={cn(
          "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
          active
            ? "bg-gradient-to-r from-blue-50 to-indigo-50/60 text-blue-700 shadow-[inset_0_0_0_1px_rgba(37,99,235,0.12)]"
            : "text-slate-500 hover:bg-slate-100/80 hover:text-slate-900"
        )}
      >
        <span
          className={cn(
            "absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-gradient-to-b from-blue-500 to-indigo-500 transition-opacity",
            active ? "opacity-100" : "opacity-0"
          )}
        />
        <Icon
          className={cn(
            "h-4 w-4 shrink-0 transition-colors",
            active
              ? "text-blue-600"
              : "text-slate-400 group-hover:text-slate-600"
          )}
        />
        <span className="truncate">{item.label}</span>
      </Link>
    );
  };

  return (
    <div className="dashboard-ui min-h-screen">
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Close navigation"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[268px] flex-col overflow-hidden border-r border-slate-200/70 bg-white transition-transform duration-300 lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="pointer-events-none absolute -left-24 -top-16 h-64 w-64 rounded-full bg-blue-100/70 blur-3xl" />
        <div className="pointer-events-none absolute -right-24 top-52 h-56 w-56 rounded-full bg-indigo-100/60 blur-3xl" />
        <div className="bg-grid pointer-events-none absolute inset-0 opacity-30" />

        <div className="relative flex h-16 items-center justify-between border-b border-slate-100 px-5">
          <Link href="/" className="group flex items-center gap-2.5">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 via-blue-500 to-indigo-600 shadow-[0_8px_20px_-10px_rgba(37,99,235,0.9)] ring-1 ring-inset ring-white/25">
              <span className="text-sm font-bold tracking-widest text-white">V</span>
            </div>
            <div className="leading-none">
              <span className="block text-[17px] font-bold tracking-tight text-slate-900">
                Ventrix
              </span>
              <span className="mt-1 block text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                Diligence OS
              </span>
            </div>
          </Link>
          <button
            type="button"
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="relative px-4 pt-4">
          <button
            type="button"
            className="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-2.5 text-left shadow-sm transition-colors hover:border-slate-300 hover:bg-white"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-[11px] font-bold text-white shadow-sm ring-1 ring-inset ring-white/30">
              AC
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-xs font-semibold text-slate-900">
                Workspace
              </span>
              <span className="block truncate text-[11px] text-slate-500">
                Pro workspace
              </span>
            </span>
            <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          </button>

          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="mt-3 flex w-full items-center gap-2.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-700"
          >
            <Search className="h-3.5 w-3.5" />
            <span className="flex-1">Search workspace</span>
            <kbd className="flex items-center gap-0.5 rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold text-slate-400">
              <Command className="h-2.5 w-2.5" />K
            </kbd>
          </button>
        </div>

        <nav
          className="relative flex-1 overflow-y-auto px-3 py-5"
          aria-label="Dashboard navigation"
        >
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Workspace
          </p>
          <div className="space-y-1">{workspaceNav.map(renderNavItem)}</div>

          <p className="mt-6 px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Account
          </p>
          <div className="space-y-1">{accountNav.map(renderNavItem)}</div>
        </nav>

        <div className="relative border-t border-slate-100 p-4">
          <div className="flex items-center gap-2.5 rounded-xl px-1 py-1">
            <span className="relative flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-[11px] font-semibold text-white shadow-sm ring-2 ring-white">
              {initials}
              <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-500" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-slate-900">
                {displayName}
              </p>
              <p className="truncate text-[11px] text-slate-500">
                {user?.email}
              </p>
            </div>
            <button
              type="button"
              onClick={async () => {
                await signOut();
                router.push("/sign-in");
              }}
              className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              aria-label="Sign out"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </aside>

      <div className="lg:pl-[268px]">
        <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/80 shadow-[0_1px_2px_rgba(15,23,42,0.03)] backdrop-blur-xl">
          <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <button
                type="button"
                className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 lg:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Open navigation"
              >
                <Menu className="h-5 w-5" />
              </button>
              <nav className="flex min-w-0 items-center gap-1.5 text-sm">
                <span className="hidden text-slate-400 sm:inline">Workspace</span>
                <ChevronRight className="hidden h-3.5 w-3.5 shrink-0 text-slate-300 sm:inline" />
                <span className="truncate font-semibold text-slate-900">
                  {currentPage.label}
                </span>
              </nav>
            </div>

            <div className="flex items-center gap-2 sm:gap-3">
              <button
                type="button"
                onClick={() => setPaletteOpen(true)}
                className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:text-slate-700 md:flex"
              >
                <Search className="h-3.5 w-3.5" />
                <span>Search</span>
                <kbd className="ml-2 flex items-center gap-0.5 rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold text-slate-400">
                  <Command className="h-2.5 w-2.5" />K
                </kbd>
              </button>

              <span className="hidden items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-700 xl:inline-flex">
                <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-emerald-500" />
                All systems normal
              </span>

              <button
                type="button"
                className="relative rounded-xl border border-slate-200 bg-white p-2 text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:text-slate-700"
                aria-label="Notifications"
              >
                <Bell className="h-4 w-4" />
                <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-rose-500 ring-2 ring-white" />
              </button>

              <button
                type="button"
                className="hidden rounded-xl border border-slate-200 bg-white p-2 text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:text-slate-700 sm:block"
                aria-label="Help"
              >
                <HelpCircle className="h-4 w-4" />
              </button>

              <div className="flex items-center gap-2 border-l border-slate-200 pl-2 sm:pl-3">
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-xl px-1 py-1 transition-colors hover:bg-slate-100 sm:gap-2.5 sm:px-2"
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-[11px] font-semibold text-white ring-2 ring-white">
                    {initials}
                  </span>
                  <span className="hidden text-left leading-tight sm:block">
                    <span className="block text-xs font-semibold text-slate-900">
                      {displayName}
                    </span>
                    <span className="block text-[10px] text-slate-500">
                      Workspace
                    </span>
                  </span>
                  <ChevronDown className="hidden h-3.5 w-3.5 text-slate-400 sm:block" />
                </button>
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1500px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
          {children}
        </main>
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </div>
  );
}
