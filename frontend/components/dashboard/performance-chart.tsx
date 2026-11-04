"use client";

import { useMemo, useState } from "react";
import { TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

type RangeKey = "7D" | "30D" | "90D";

interface ChartRange {
  labels: string[];
  completed: number[];
  active: number[];
  total: string;
  delta: string;
}

const ranges: Record<RangeKey, ChartRange> = {
  "7D": {
    labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    completed: [4, 6, 5, 8, 7, 10, 9],
    active: [2, 3, 4, 3, 5, 4, 6],
    total: "18",
    delta: "+12.4%",
  },
  "30D": {
    labels: ["Week 1", "Week 2", "Week 3", "Week 4"],
    completed: [18, 26, 22, 34],
    active: [7, 9, 11, 13],
    total: "100",
    delta: "+24.8%",
  },
  "90D": {
    labels: ["Aug", "Sep", "Oct", "Nov"],
    completed: [62, 74, 88, 104],
    active: [16, 21, 26, 31],
    total: "264",
    delta: "+38.2%",
  },
};

const WIDTH = 640;
const HEIGHT = 230;
const PADDING_X = 8;
const PADDING_TOP = 16;
const PADDING_BOTTOM = 30;

export function PerformanceChart() {
  const [range, setRange] = useState<RangeKey>("30D");
  const data = ranges[range];

  const { completedLine, activeLine, completedArea, activeArea, max } =
    useMemo(() => {
      const all = [...data.completed, ...data.active];
      const maxValue = Math.max(...all) * 1.18 || 1;
      const innerWidth = WIDTH - PADDING_X * 2;
      const innerHeight = HEIGHT - PADDING_TOP - PADDING_BOTTOM;
      const count = data.labels.length;

      const x = (index: number) =>
        PADDING_X + (index / Math.max(count - 1, 1)) * innerWidth;
      const y = (value: number) =>
        PADDING_TOP + innerHeight - (value / maxValue) * innerHeight;

      const buildLine = (values: number[]) =>
        values
          .map(
            (value, index) =>
              `${index === 0 ? "M" : "L"}${x(index).toFixed(1)},${y(value).toFixed(1)}`
          )
          .join(" ");

      const buildArea = (values: number[]) =>
        `${buildLine(values)} L ${x(count - 1).toFixed(1)},${(
          HEIGHT - PADDING_BOTTOM
        ).toFixed(1)} L ${x(0).toFixed(1)},${(HEIGHT - PADDING_BOTTOM).toFixed(
          1
        )} Z`;

      return {
        completedLine: buildLine(data.completed),
        activeLine: buildLine(data.active),
        completedArea: buildArea(data.completed),
        activeArea: buildArea(data.active),
        max: maxValue,
      };
    }, [data]);

  const gridLines = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-soft">
      <div className="flex flex-col gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold tracking-tight text-slate-900">
              Analysis activity
            </h2>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
              <TrendingUp className="h-3 w-3" />
              {data.delta}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Completed and in-progress diligence runs
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden items-center gap-3 sm:flex">
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-slate-500">
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              Completed
            </span>
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-slate-500">
              <span className="h-2 w-2 rounded-full bg-violet-400" />
              In progress
            </span>
          </div>
          <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
            {(Object.keys(ranges) as RangeKey[]).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setRange(key)}
                className={cn(
                  "rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors",
                  range === key
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                )}
              >
                {key}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="p-5">
        <div className="mb-3 flex items-end gap-2">
          <span className="text-3xl font-bold tracking-[-0.03em] text-slate-900">
            {data.total}
          </span>
          <span className="mb-1 text-xs text-slate-500">
            analyses in the last {range.toLowerCase() === "7d" ? "7 days" : range.toLowerCase() === "30d" ? "30 days" : "90 days"}
          </span>
        </div>

        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-[230px] w-full"
          role="img"
          aria-label="Analysis activity over time"
        >
          <defs>
            <linearGradient id="completed-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="active-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.16" />
              <stop offset="100%" stopColor="#a78bfa" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="completed-stroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#3b82f6" />
            </linearGradient>
          </defs>

          {gridLines.map((ratio) => {
            const y =
              PADDING_TOP + (1 - ratio) * (HEIGHT - PADDING_TOP - PADDING_BOTTOM);
            return (
              <g key={ratio}>
                <line
                  x1={PADDING_X}
                  x2={WIDTH - PADDING_X}
                  y1={y}
                  y2={y}
                  stroke="#eef2f7"
                  strokeWidth="1"
                  strokeDasharray={ratio === 0 ? "0" : "4 6"}
                />
                <text
                  x={PADDING_X}
                  y={y - 6}
                  fontSize="11"
                  fill="#475569"
                  fontWeight="600"
                >
                  {Math.round(ratio * max)}
                </text>
              </g>
            );
          })}

          <path d={activeArea} fill="url(#active-fill)" />
          <path d={completedArea} fill="url(#completed-fill)" />
          <path
            d={activeLine}
            fill="none"
            stroke="#a78bfa"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="5 5"
          />
          <path
            d={completedLine}
            fill="none"
            stroke="url(#completed-stroke)"
            strokeWidth="2.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {data.labels.map((label, index) => {
            const innerWidth = WIDTH - PADDING_X * 2;
            const x =
              PADDING_X +
              (index / Math.max(data.labels.length - 1, 1)) * innerWidth;
            return (
              <text
                key={label}
                x={x}
                y={HEIGHT - 8}
                fontSize="12"
                fill="#475569"
                fontWeight="600"
                textAnchor={
                  index === 0
                    ? "start"
                    : index === data.labels.length - 1
                      ? "end"
                      : "middle"
                }
              >
                {label}
              </text>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
