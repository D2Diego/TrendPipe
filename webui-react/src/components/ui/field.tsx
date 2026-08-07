import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const inputClass =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-sm " +
  "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring " +
  "disabled:bg-muted disabled:text-muted-foreground";

export function Field({ label, htmlFor, children, help }: { label: ReactNode; htmlFor: string; children: ReactNode; help?: ReactNode }) {
  return <div><label htmlFor={htmlFor}>{label}</label>{children}{help ? <p className="mt-1 text-xs text-muted-foreground">{help}</p> : null}</div>;
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(inputClass, className)} {...props} />;
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(inputClass, className)} {...props} />;
}
