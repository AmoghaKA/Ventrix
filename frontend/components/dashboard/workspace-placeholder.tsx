import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export function WorkspacePlaceholder({
  title,
  description,
  icon: Icon,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
}) {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-blue-accent">
          Workspace
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-text-primary md:text-3xl">
          {title}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-secondary">
          {description}
        </p>
      </div>

      <Card className="p-8">
        <div className="mx-auto flex max-w-lg flex-col items-center text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-sm bg-blue-50 text-blue-accent">
            <Icon className="h-5 w-5" />
          </span>
          <Badge variant="warning" className="mt-4">
            Phase preview
          </Badge>
          <h2 className="mt-3 text-base font-semibold text-text-primary">
            This workspace view is being prepared
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-text-secondary">
            The {title.toLowerCase()} experience will be enabled in a later
            phase. The sidebar navigation is already in place so your workspace
            structure stays consistent.
          </p>
        </div>
      </Card>
    </div>
  );
}
