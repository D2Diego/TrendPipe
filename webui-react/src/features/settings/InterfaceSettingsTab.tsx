import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getUiConfig, setUiConfigValue } from "@/api/config";

export function InterfaceSettingsTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const config = useQuery({ queryKey: ["ui-config"], queryFn: getUiConfig });
  const save = useMutation({ mutationFn: (value: boolean) => setUiConfigValue("hide_log", value), onSuccess: (_, value) => queryClient.setQueryData(["ui-config"], { ...(config.data || {}), hide_log: value }) });
  if (!config.data) return <p role="status">{t("Loading")}</p>;
  return <div className="space-y-3"><label className="flex items-center gap-2"><input type="checkbox" aria-label={t("Hide Log")} checked={config.data.hide_log === true} onChange={(event) => save.mutate(event.target.checked)} />{t("Hide Log")}</label>{save.error ? <p role="alert" className="text-sm text-destructive-foreground">{String(save.error)}</p> : null}</div>;
}
