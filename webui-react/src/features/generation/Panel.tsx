import type { ReactNode } from "react";
export function Panel({ title, children }: { title: ReactNode; children: ReactNode }) {
  return <section className="space-y-4 rounded-lg border border-border bg-card p-4 text-card-foreground shadow-sm"><h2 className="text-base font-semibold">{title}</h2>{children}</section>;
}
