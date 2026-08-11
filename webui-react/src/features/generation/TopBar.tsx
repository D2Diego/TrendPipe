import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Search, Settings, Video } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useSearchParams } from "react-router-dom";
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
  const [searchParams, setSearchParams] = useSearchParams();
  const { pathname } = useLocation();
  const isHome = pathname === "/";
  const isGenerator = pathname === "/generate";
  const isResearch = pathname.startsWith("/researches");
  const backTarget = pathname.startsWith("/researches/") ? "/researches" : "/";
  const requestedSettingsTab = searchParams.get("settings") === "researcher" ? "researcher" : undefined;
  const uiConfig = useQuery({ queryKey: ["ui-config"], queryFn: getUiConfig, staleTime: 30_000 });
  const languageHydrated = useRef(false);
  useEffect(() => {
    if (languageHydrated.current || !uiConfig.data) return;
    languageHydrated.current = true;
    const savedLanguage = String(uiConfig.data.language || "").split("-")[0];
    if (savedLanguage in localeFiles) void i18n.changeLanguage(savedLanguage);
  }, [i18n, uiConfig.data]);
  useEffect(() => {
    if (requestedSettingsTab) setSettingsOpen(true);
  }, [requestedSettingsTab]);
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
  const closeSettings = () => {
    setSettingsOpen(false);
    if (!requestedSettingsTab) return;
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete("settings");
    setSearchParams(nextParams, { replace: true });
  };
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-card px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        {!isHome ? <Link className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary px-3 py-2 text-sm font-medium text-secondary-foreground shadow-sm transition-colors hover:bg-secondary/80" to={backTarget}><ArrowLeft className="size-4" />{t("Back")}</Link> : null}
        <div className="text-xl font-bold tracking-tight text-foreground">
          TrendPipe <span className="text-xs font-normal text-muted-foreground">v{version.data?.current_version || import.meta.env.VITE_APP_VERSION || ""}</span>
        </div>
        {version.data?.available_version ? <a className="text-xs font-medium text-primary hover:underline" href={version.data.release_url} target="_blank" rel="noreferrer">{t("Update Available", { version: version.data.available_version })}</a> : null}
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2">
        {isGenerator ? <Link className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary px-3 py-2 text-sm font-medium text-secondary-foreground shadow-sm transition-colors hover:bg-secondary/80" to="/researches"><Search className="size-4" />{t("Do Research")}</Link> : null}
        {isResearch ? <Link className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary px-3 py-2 text-sm font-medium text-secondary-foreground shadow-sm transition-colors hover:bg-secondary/80" to="/generate"><Video className="size-4" />{t("Create Video")}</Link> : null}
        <TaskManagerPanel />
        <Button id="open-settings-dialog-button" data-tour-id="settings" type="button" className="inline-flex items-center gap-1" onClick={() => setSettingsOpen(true)}><Settings className="size-4" />{t("Settings")}</Button>
        <Select aria-label="Language / Languages" className="w-auto" value={i18n.language.split("-")[0]} onChange={(event) => changeLanguage(event.target.value)}>
          {Object.entries(localeFiles).map(([code, locale]) => <option key={code} value={code}>{locale.Language}</option>)}
        </Select>
      </div>
      <SettingsModal key={requestedSettingsTab ?? "default"} open={settingsOpen} onClose={closeSettings} initialTab={requestedSettingsTab} />
    </header>
  );
}
