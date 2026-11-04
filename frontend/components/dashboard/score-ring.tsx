"use client";

import { useId } from "react";
import { cn } from "@/lib/utils";

export function ScoreRing({
  score,
  display,
  caption,
  variant = "light",
}: {
  score: number;
  display: string;
  caption?: string;
  variant?: "light" | "dark";
}) {
  const gradientId = `ring-${useId().replace(/:/g, "")}`;
  const clamped = Math.max(0, Math.min(100, score));
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const dash = (clamped / 100) * circumference;

  return (
    <div className="relative flex h-[168px] w-[168px] items-center justify-center">
      <div
        className={cn(
          "absolute inset-6 rounded-full blur-2xl",
          variant === "dark" ? "bg-blue-500/25" : "bg-blue-500/10"
        )}
      />
      <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#60a5fa" />
            <stop offset="50%" stopColor="#2563eb" />
            <stop offset="100%" stopColor="#7c3aed" />
          </linearGradient>
        </defs>
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={variant === "dark" ? "rgba(255,255,255,0.1)" : "#eef2f7"}
          strokeWidth="10"
        />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span
          className={cn(
            "text-[34px] font-bold leading-none tracking-[-0.04em]",
            variant === "dark" ? "text-white" : "text-slate-900"
          )}
        >
          {display}
        </span>
        {caption && (
          <span className="mt-1 whitespace-nowrap text-[0.625rem] font-semibold uppercase leading-none tracking-[0.04em] text-slate-400">
            {caption}
          </span>
        )}
      </div>
    </div>
  );
}
