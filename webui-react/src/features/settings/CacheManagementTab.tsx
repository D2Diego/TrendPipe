import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { cleanCache, getCacheStats } from "@/api/cache";
import { Button } from "@/components/ui/button";
import { Field, Select } from "@/components/ui/field";

export function formatFileSize(bytes: number) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${unit < 2 ? Math.round(value) : value.toFixed(2)} ${units[unit]}`;
}

export function CacheManagementTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [range, setRange] = useState("30");
  const [confirmed, setConfirmed] = useState(false);
  const days = range === "all" ? undefined : Number(range);
  const stats = useQuery({ queryKey: ["cache-stats", days ?? "all"], queryFn: () => getCacheStats(days) });
  const cleanup = useMutation({ mutationFn: () => cleanCache(days), onSuccess: () => { setConfirmed(false); void queryClient.invalidateQueries({ queryKey: ["cache-stats"] }); } });
  return <div className="space-y-4">
    <div className="grid grid-cols-3 gap-3 rounded-md bg-muted p-3 text-center"><div><strong className="block text-lg">{stats.data?.file_count ?? 0}</strong><span className="text-xs text-muted-foreground">{t("Cache Files")}</span></div><div><strong className="block text-lg">{formatFileSize(stats.data?.total_size ?? 0)}</strong><span className="text-xs text-muted-foreground">{t("Cache Size")}</span></div><div><strong className="block text-sm">{stats.data?.oldest_mtime ? new Date(stats.data.oldest_mtime * 1000).toISOString().slice(0, 10) : "-"}</strong><span className="text-xs text-muted-foreground">{t("Oldest Cache File")}</span></div></div>
    <Field label={t("Cache Cleanup Range")} htmlFor="cache-range"><Select id="cache-range" value={range} onChange={(event) => { setRange(event.target.value); setConfirmed(false); }}><option value="30">30 {t("days")}</option><option value="7">7 {t("days")}</option><option value="90">90 {t("days")}</option><option value="all">{t("All")}</option></Select></Field>
    <p className="text-sm text-muted-foreground">{t("Cache Cleanup Preview", { count: stats.data?.file_count ?? 0, size: formatFileSize(stats.data?.total_size ?? 0) })}</p>
    <label className="flex items-center gap-2"><input type="checkbox" aria-label={t("Confirm Cache Cleanup")} checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />{t("Confirm Cache Cleanup")}</label>
    <div className="grid grid-cols-2 gap-2"><Button type="button" variant="destructive" disabled={!confirmed || !stats.data?.file_count || cleanup.isPending} onClick={() => cleanup.mutate()}>{t("Clean Cache Now")}</Button><Button type="button" onClick={() => void stats.refetch()}>{t("Refresh Cache Stats")}</Button></div>
    {cleanup.data ? <p role="status" className="text-sm text-success">{t("Cache Cleanup Complete")}: {cleanup.data.deleted_count}</p> : null}
    {cleanup.error ? <p role="alert" className="text-sm text-destructive-foreground">{String(cleanup.error)}</p> : null}
  </div>;
}
