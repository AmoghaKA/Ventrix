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
          "w-full bg-secondary border border-border rounded-sm px-4 py-2.5 text-sm text-text-primary placeholder-text-secondary/60 focus:outline-none focus:ring-1 focus:ring-blue-accent transition-colors duration-200",
          error && "border-critical focus:ring-critical",
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
