import { useEffect, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Dialog({ open, onClose, title, children, className }: DialogProps) {
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;
  return <div data-testid="dialog-backdrop" className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4" onClick={onClose}>
    <div role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : undefined} className={cn("max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-border bg-card p-6 text-card-foreground shadow-lg", className)} onClick={(event) => event.stopPropagation()}>
      <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold">{title}</h2><button type="button" aria-label="Close" className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground" onClick={onClose}>✕</button></div>
      {children}
    </div>
  </div>;
}
