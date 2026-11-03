import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

const variants: Record<ButtonVariant, string> = {
  primary:
    "bg-blue-accent text-white shadow-sm hover:bg-blue-accent/90 hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-accent/50 focus:ring-offset-2 focus:ring-offset-background",
  secondary:
    "bg-white text-text-primary border border-border shadow-sm hover:bg-secondary hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-border",
  ghost:
    "bg-transparent text-text-secondary hover:bg-secondary focus:outline-none",
};

const sizes: Record<ButtonSize, string> = {
  sm: "px-4 py-2 text-xs",
  md: "px-6 py-3 text-sm",
  lg: "px-8 py-4 text-base",
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
    "inline-flex items-center justify-center font-medium rounded-sm transition-all duration-200 disabled:pointer-events-none disabled:opacity-60",
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
