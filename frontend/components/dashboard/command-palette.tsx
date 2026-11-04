"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CornerDownLeft, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { allNavItems } from "./navigation";

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return allNavItems;
    return allNavItems.filter((item) =>
      `${item.label} ${item.description}`.toLowerCase().includes(normalized)
    );
  }, [query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(0);
    const timer = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  if (!open) return null;

  const go = (href: string) => {
    onClose();
    router.push(href);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, results.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      const target = results[activeIndex];
      if (target) go(target.href);
    } else if (event.key === "Escape") {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[12vh] sm:pt-[16vh]">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Close search"
      />
      <div className="relative w-full max-w-xl animate-fade-up overflow-hidden rounded-2xl border border-white/60 bg-white shadow-[0_40px_120px_-40px_rgba(15,23,42,0.55)]">
        <div className="flex items-center gap-3 border-b border-slate-100 px-4">
          <Search className="h-4 w-4 shrink-0 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search pages, reports, agents..."
            className="h-14 w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
          />
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close search"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-80 overflow-y-auto p-2">
          {results.length === 0 && (
            <p className="px-3 py-8 text-center text-sm text-slate-500">
              No results for &ldquo;{query}&rdquo;
            </p>
          )}

          {results.map((item, index) => {
            const Icon = item.icon;
            return (
              <button
                key={item.href}
                type="button"
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => go(item.href)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
                  index === activeIndex
                    ? "bg-slate-900 text-white"
                    : "text-slate-700 hover:bg-slate-50"
                )}
              >
                <span
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border",
                    index === activeIndex
                      ? "border-white/15 bg-white/10 text-white"
                      : "border-slate-200 bg-slate-50 text-slate-500"
                  )}
                >
                  <Icon className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold">
                    {item.label}
                  </span>
                  <span
                    className={cn(
                      "block truncate text-xs",
                      index === activeIndex ? "text-slate-300" : "text-slate-500"
                    )}
                  >
                    {item.description}
                  </span>
                </span>
                {index === activeIndex && (
                  <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                )}
              </button>
            );
          })}
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/70 px-4 py-2.5 text-[11px] text-slate-500">
          <span>Navigate with ↑ ↓</span>
          <span className="flex items-center gap-1.5">
            <kbd className="rounded border border-slate-200 bg-white px-1.5 py-0.5 font-sans text-[10px] font-semibold text-slate-500">
              Enter
            </kbd>
            to open
          </span>
        </div>
      </div>
    </div>
  );
}
