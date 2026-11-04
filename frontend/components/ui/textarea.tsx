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
          "w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-text-primary shadow-sm transition-all duration-200 placeholder:text-text-secondary/60 hover:border-slate-300 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10",
          error && "border-critical focus:border-critical focus:ring-critical/10",
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
