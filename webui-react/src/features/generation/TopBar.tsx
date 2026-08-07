import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Settings } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/field";
import { localeFiles } from "@/i18n";
import { getUiConfig, setUiConfigValue } from "@/api/config";
import { getVersionStatus } from "@/api/version";
import { SettingsModal } from "@/features/settings/SettingsModal";
import { TaskManagerPanel } from "@/features/taskManager/TaskManagerPanel";

export function TopBar() {
  const { t, i18n } = useTranslation();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const uiConfig = useQuery({ queryKey: ["ui-config"], queryFn: getUiConfig, staleTime: 30_000 });
  const languageHydrated = useRef(false);
  useEffect(() => {
    if (languageHydrated.current || !uiConfig.data) return;
    languageHydrated.current = true;
    const savedLanguage = String(uiConfig.data.language || "").split("-")[0];
    if (savedLanguage in localeFiles) void i18n.changeLanguage(savedLanguage);
  }, [i18n, uiConfig.data]);
  const version = useQuery({
    queryKey: ["version"],
    queryFn: getVersionStatus,
    refetchInterval: (query) => query.state.data?.complete ? false : 1_000,
    staleTime: 12 * 60 * 60 * 1_000,
  });
  const changeLanguage = (code: string) => {
    void i18n.changeLanguage(code);
    void setUiConfigValue("language", code).catch(() => undefined);
  };
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-card px-4 py-3">
      <div className="flex flex-wrap items-baseline gap-2">
        <a href="https://github.com/harry0703/MoneyPrinterTurbo" target="_blank" rel="noreferrer" className="text-xl font-bold tracking-tight text-foreground">
          MoneyPrinterTurbo <span className="text-xs font-normal text-muted-foreground">v{version.data?.current_version || import.meta.env.VITE_APP_VERSION || ""}</span>
        </a>
        {version.data?.available_version ? <a className="text-xs font-medium text-primary hover:underline" href={version.data.release_url} target="_blank" rel="noreferrer">{t("Update Available", { version: version.data.available_version })}</a> : null}
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2">
        <TaskManagerPanel />
        <Button id="open-settings-dialog-button" data-tour-id="settings" type="button" onClick={() => setSettingsOpen(true)}><Settings className="mr-1 inline size-4" />{t("Settings")}</Button>
        <Select aria-label="Language / Languages" className="w-auto" value={i18n.language.split("-")[0]} onChange={(event) => changeLanguage(event.target.value)}>
          {Object.entries(localeFiles).map(([code, locale]) => <option key={code} value={code}>{locale.Language}</option>)}
        </Select>
      </div>
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </header>
  );
}
