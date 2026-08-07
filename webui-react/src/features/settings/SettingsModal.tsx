import { useTranslation } from "react-i18next";
import { Dialog } from "@/components/ui/dialog";
import { Tabs } from "@/components/ui/tabs";
import { CacheManagementTab } from "./CacheManagementTab";
import { InterfaceSettingsTab } from "./InterfaceSettingsTab";
import { LlmSettingsTab } from "./LlmSettingsTab";
import { MaterialApiTab } from "./MaterialApiTab";
import { ResearcherSettingsTab } from "@/features/researches/ResearchSettingsPage";

export function SettingsModal({ open, onClose, initialTab }: { open: boolean; onClose: () => void; initialTab?: string }) {
  const { t } = useTranslation();
  return <Dialog open={open} onClose={onClose} title={t("Settings")} className="max-w-5xl"><Tabs initialTab={initialTab} tabs={[
    { key: "llm", label: t("LLM Settings Tab"), content: <LlmSettingsTab /> },
    { key: "material", label: t("Material API Tab"), content: <MaterialApiTab /> },
    { key: "researcher", label: t("Researcher Settings Tab"), content: <ResearcherSettingsTab /> },
    { key: "cache", label: t("Cache Management Tab"), content: <CacheManagementTab /> },
    { key: "interface", label: t("Interface Settings Tab"), content: <InterfaceSettingsTab /> },
  ]} /></Dialog>;
}
