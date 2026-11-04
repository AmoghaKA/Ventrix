import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between",
        className
      )}
    >
      <div className="min-w-0 max-w-2xl">
        {eyebrow && (
          <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-600">
            <span className="h-1 w-1 rounded-full bg-blue-600" />
            {eyebrow}
          </p>
        )}
        <h1 className="mt-2 text-2xl font-bold tracking-[-0.03em] text-slate-900 md:text-[32px] md:leading-[1.15]">
          {title}
        </h1>
        {description && (
          <p className="mt-2 text-sm leading-relaxed text-slate-500">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2.5 sm:flex-nowrap xl:shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
}
