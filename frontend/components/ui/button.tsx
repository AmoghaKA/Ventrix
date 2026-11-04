import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

const variants: Record<ButtonVariant, string> = {
  primary:
    "bg-gradient-to-b from-blue-500 to-blue-600 text-white shadow-[0_10px_24px_-12px_rgba(37,99,235,0.9)] ring-1 ring-inset ring-white/20 hover:from-blue-500 hover:to-blue-700 hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 focus-visible:ring-offset-2",
  secondary:
    "bg-white text-text-primary border border-slate-200 shadow-sm hover:border-slate-300 hover:bg-slate-50 hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-300",
  ghost:
    "bg-transparent text-text-secondary hover:bg-slate-100 hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-200",
};

const sizes: Record<ButtonSize, string> = {
  sm: "px-4 py-2 text-xs",
  md: "px-5 py-2.5 text-sm",
  lg: "px-7 py-3.5 text-sm",
};

export function buttonStyles({
  variant = "primary",
  size = "md",
  className,
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
} = {}) {
  return cn(
    "inline-flex items-center justify-center rounded-xl font-semibold tracking-tight transition-all duration-200 disabled:pointer-events-none disabled:opacity-60",
    variants[variant],
    sizes[size],
    className
  );
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={buttonStyles({ variant, size, className })}
      {...props}
    >
      {children}
    </button>
  );
}
