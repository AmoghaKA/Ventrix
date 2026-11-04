import Link from "next/link";
import { ArrowUpRight, Bot, Clock, FileCheck2, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { demoActivity } from "@/lib/demo-data";

const activityMeta = {
  report: {
    icon: FileText,
    tile: "bg-blue-50 text-blue-600 ring-blue-100",
  },
  agent: {
    icon: Bot,
    tile: "bg-violet-50 text-violet-600 ring-violet-100",
  },
  evidence: {
    icon: FileCheck2,
    tile: "bg-emerald-50 text-emerald-600 ring-emerald-100",
  },
  queue: {
    icon: Clock,
    tile: "bg-amber-50 text-amber-600 ring-amber-100",
  },
};

export function ActivityFeed() {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200/70 bg-white shadow-soft">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-slate-900">
            Recent activity
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            What your diligence desk has been up to
          </p>
        </div>
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
        </span>
      </div>

      <ul className="flex-1 space-y-1 p-5">
        {demoActivity.map((item, index) => {
          const meta = activityMeta[item.kind];
          const Icon = meta.icon;
          const last = index === demoActivity.length - 1;
          return (
            <li key={item.id} className="relative flex gap-3 pb-4 last:pb-0">
              {!last && (
                <span className="absolute left-[15px] top-9 h-[calc(100%-20px)] w-px bg-slate-200" />
              )}
              <span
                className={cn(
                  "relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset",
                  meta.tile
                )}
              >
                <Icon className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <p className="text-xs font-semibold leading-snug text-slate-800">
                  {item.title}
                </p>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                  {item.detail}
                </p>
                <p className="mt-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  {item.time}
                </p>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="border-t border-slate-100 p-3">
        <Link
          href="/dashboard/analysis-history"
          className="flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-50 hover:text-blue-600"
        >
          View all activity
          <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
