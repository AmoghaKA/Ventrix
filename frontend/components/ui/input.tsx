"use client";

import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ className, label, error, ...props }: InputProps) {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-xs font-medium text-text-secondary mb-1.5">
          {label}
        </label>
      )}
      <input
        className={cn(
          "h-11 w-full rounded-xl border border-slate-200 bg-white px-3.5 text-sm text-text-primary shadow-sm transition-all duration-200 placeholder:text-text-secondary/60 hover:border-slate-300 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10",
          error && "border-critical focus:border-critical focus:ring-critical/10",
          className
        )}
        {...props}
      />
      {error && (
        <p className="mt-1 text-xs text-critical">{error}</p>
      )}
    </div>
  );
}
