import { cn } from "@/lib/utils";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Textarea({
  className,
  label,
  error,
  hint,
  id,
  ...props
}: TextareaProps) {
  return (
    <div className="w-full">
      {label && (
        <label htmlFor={id} className="mb-1.5 block text-xs font-medium text-text-secondary">
          {label}
        </label>
      )}
      <textarea
        id={id}
        className={cn(
          "w-full rounded-sm border border-border bg-white px-3 py-2.5 text-sm text-text-primary placeholder:text-text-secondary/70 transition-colors duration-200 focus:border-blue-accent focus:outline-none focus:ring-1 focus:ring-blue-accent/30",
          error && "border-critical focus:border-critical focus:ring-critical/30",
          className
        )}
        {...props}
      />
      {error ? (
        <p className="mt-1 text-xs text-critical">{error}</p>
      ) : (
        hint && <p className="mt-1 text-xs text-text-secondary">{hint}</p>
      )}
    </div>
  );
}
