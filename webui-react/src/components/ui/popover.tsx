import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Popover({ open, onOpenChange, trigger, children, className }: { open: boolean; onOpenChange: (open: boolean) => void; trigger: ReactNode; children: ReactNode; className?: string }) {
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => { if (container.current && !container.current.contains(event.target as Node)) onOpenChange(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") onOpenChange(false); };
    document.addEventListener("mousedown", outside); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", outside); document.removeEventListener("keydown", escape); };
  }, [open, onOpenChange]);
  return <div ref={container} className="relative inline-block">{trigger}{open ? <div className={cn("absolute right-0 z-40 mt-2 max-h-[70vh] w-[min(94vw,58rem)] overflow-y-auto rounded-lg border border-border bg-card p-4 text-card-foreground shadow-lg", className)}>{children}</div> : null}</div>;
}
