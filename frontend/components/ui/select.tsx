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
          "h-10 w-full rounded-sm border border-border bg-white px-3 text-sm text-text-primary transition-colors duration-200 focus:border-blue-accent focus:outline-none focus:ring-1 focus:ring-blue-accent/30",
          error && "border-critical focus:border-critical focus:ring-critical/30",
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
