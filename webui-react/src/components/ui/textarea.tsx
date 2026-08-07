import type { TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { inputClass } from "./field";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(inputClass, className)} {...props} />;
}
