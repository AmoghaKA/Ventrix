"use client";

import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "critical" | "neutral";
  dot?: boolean;
}

const dotColor: Record<NonNullable<BadgeProps["variant"]>, string> = {
  default: "bg-slate-400",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  critical: "bg-rose-500",
  neutral: "bg-slate-400",
};

export function Badge({
  className,
  variant = "default",
  dot,
  children,
  ...props
}: BadgeProps) {
  const variants = {
    default: "bg-slate-100/80 text-slate-600 ring-slate-200/80",
    success: "bg-emerald-50 text-emerald-700 ring-emerald-200/70",
    warning: "bg-amber-50 text-amber-700 ring-amber-200/70",
    critical: "bg-rose-50 text-rose-700 ring-rose-200/70",
    neutral: "bg-white text-slate-600 ring-slate-200/80",
  };

  const showDot = dot ?? (variant !== "default" && variant !== "neutral");

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ring-1 ring-inset",
        variants[variant],
        className
      )}
      {...props}
    >
      {showDot && (
        <span
          className={cn(
            "h-1.5 w-1.5 shrink-0 rounded-full",
            dotColor[variant]
          )}
        />
      )}
      {children}
    </span>
  );
}
