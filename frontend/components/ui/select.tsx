import { cn } from "@/lib/utils";

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

export function Select({
  className,
  label,
  error,
  id,
  children,
  ...props
}: SelectProps) {
  return (
    <div className="w-full">
      {label && (
        <label htmlFor={id} className="mb-1.5 block text-xs font-medium text-text-secondary">
          {label}
        </label>
      )}
      <select
        id={id}
        className={cn(
          "h-11 w-full rounded-xl border border-slate-200 bg-white px-3.5 text-sm text-text-primary shadow-sm transition-all duration-200 hover:border-slate-300 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10",
          error && "border-critical focus:border-critical focus:ring-critical/10",
          className
        )}
        {...props}
      >
        {children}
      </select>
      {error && <p className="mt-1 text-xs text-critical">{error}</p>}
    </div>
  );
}
