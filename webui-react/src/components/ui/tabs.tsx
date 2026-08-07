import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TabDef { key: string; label: ReactNode; content: ReactNode }

export function Tabs({ tabs }: { tabs: TabDef[] }) {
  const [active, setActive] = useState(tabs[0]?.key);
  return <div>
    <div role="tablist" className="mb-4 flex gap-1 overflow-x-auto border-b border-border">
      {tabs.map((tab) => <button key={tab.key} role="tab" type="button" aria-selected={tab.key === active} className={cn("whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium", tab.key === active ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")} onClick={() => setActive(tab.key)}>{tab.label}</button>)}
    </div>
    {tabs.find((tab) => tab.key === active)?.content}
  </div>;
}
