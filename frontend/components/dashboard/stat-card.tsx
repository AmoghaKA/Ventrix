import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type StatTone = "blue" | "emerald" | "amber" | "rose" | "violet";

const tones: Record<
  StatTone,
  { tile: string; accent: string; stroke: string }
> = {
  blue: {
    tile: "from-blue-500/15 to-blue-500/[0.03] text-blue-600 ring-blue-500/15",
    accent: "from-blue-500 to-indigo-500",
    stroke: "#3b82f6",
  },
  emerald: {
    tile: "from-emerald-500/15 to-emerald-500/[0.03] text-emerald-600 ring-emerald-500/15",
    accent: "from-emerald-500 to-teal-500",
    stroke: "#10b981",
  },
  amber: {
    tile: "from-amber-500/15 to-amber-500/[0.03] text-amber-600 ring-amber-500/15",
    accent: "from-amber-400 to-orange-500",
    stroke: "#f59e0b",
  },
  rose: {
    tile: "from-rose-500/15 to-rose-500/[0.03] text-rose-600 ring-rose-500/15",
    accent: "from-rose-500 to-pink-500",
    stroke: "#f43f5e",
  },
  violet: {
    tile: "from-violet-500/15 to-violet-500/[0.03] text-violet-600 ring-violet-500/15",
    accent: "from-violet-500 to-indigo-500",
    stroke: "#8b5cf6",
  },
};

function sparklinePoints(values: number[], width = 96, height = 32) {
  if (values.length === 0) return "";
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((value - min) / range) * (height - 6) - 3;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function StatCard({
  label,
  value,
  detail,
  delta,
  trend = "up",
  tone = "blue",
  icon: Icon,
  spark = [3, 5, 4, 7, 6, 9, 8],
}: {
  label: string;
  value: string | number;
  detail?: string;
  delta?: string;
  trend?: "up" | "down";
  tone?: StatTone;
  icon: LucideIcon;
  spark?: number[];
}) {
  const config = tones[tone];
  const points = sparklinePoints(spark);
  const areaPoints = `${points} 96,32 0,32`;

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white p-5 shadow-soft transition-all duration-300 hover:-translate-y-0.5 hover:shadow-ring">
      <div
        className={cn(
          "absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r opacity-80",
          config.accent
        )}
      />
      <div className="flex items-start justify-between gap-3">
        <span
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ring-1 ring-inset",
            config.tile
          )}
        >
          <Icon className="h-[18px] w-[18px]" />
        </span>
        {delta && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[10px] font-semibold",
              trend === "up"
                ? "bg-emerald-50 text-emerald-600"
                : "bg-rose-50 text-rose-600"
            )}
          >
            {trend === "up" ? (
              <ArrowUpRight className="h-3 w-3" />
            ) : (
              <ArrowDownRight className="h-3 w-3" />
            )}
            {delta}
          </span>
        )}
      </div>

      <p className="mt-5 text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-[28px] font-bold leading-none tracking-[-0.03em] text-slate-900">
        {value}
      </p>

      <div className="mt-3 flex items-end justify-between gap-3">
        <p className="text-[11px] leading-relaxed text-slate-400">{detail}</p>
        <svg
          viewBox="0 0 96 32"
          className="h-8 w-24 shrink-0 overflow-visible"
          aria-hidden="true"
        >
          <polygon points={areaPoints} fill={config.stroke} opacity="0.08" />
          <polyline
            points={points}
            fill="none"
            stroke={config.stroke}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
}
