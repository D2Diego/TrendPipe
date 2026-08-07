import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const VARIANTS = {
  default: "bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border",
  primary: "bg-primary text-primary-foreground hover:bg-primary/90 border border-transparent",
  destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90 border border-transparent",
  ghost: "bg-transparent hover:bg-accent hover:text-accent-foreground border border-transparent",
} as const;

export type ButtonVariant = keyof typeof VARIANTS;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export function Button({ className, variant = "default", ...props }: ButtonProps) {
  return <button className={cn(
    "rounded-md px-3 py-2 text-sm font-medium shadow-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50",
    VARIANTS[variant],
    className,
  )} {...props} />;
}
