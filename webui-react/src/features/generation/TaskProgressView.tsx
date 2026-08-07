import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getUiConfig } from "@/api/config";
import { getTaskLogs, getTaskStatus } from "@/api/videos";
import { useGenerationStore } from "@/store/generationStore";

const TASK_STATE_FAILED = -1;
const TASK_STATE_COMPLETE = 1;
const terminal = (state?: number) => state === TASK_STATE_FAILED || state === TASK_STATE_COMPLETE;

export function TaskProgressView() {
  const { t } = useTranslation();
  const taskId = useGenerationStore((state) => state.currentGenerationTaskId);
  const ui = useQuery({ queryKey: ["ui-config"], queryFn: getUiConfig, enabled: Boolean(taskId), staleTime: 30_000 });
  const status = useQuery({
    queryKey: ["task-status", taskId], queryFn: () => getTaskStatus(taskId!), enabled: Boolean(taskId),
    refetchInterval: (query) => terminal(query.state.data?.state) ? false : 500,
  });
  const logs = useQuery({
    queryKey: ["task-logs", taskId], queryFn: () => getTaskLogs(taskId!),
    enabled: Boolean(taskId) && ui.isSuccess && ui.data.hide_log !== true,
    refetchInterval: () => terminal(status.data?.state) ? false : 500,
  });
  if (!taskId) return null;
  if (status.error) return <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/20 p-4 text-destructive-foreground">{t("Video Generation Failed")}: {status.error.message}</div>;
  const task = status.data;
  const state = task?.state;
  const progress = Math.max(0, Math.min(100, Number(task?.progress || 0)));
  const logBlock = logs.data?.logs.length ? <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-muted p-4 text-xs text-foreground">{logs.data.logs.join("\n")}</pre> : null;
  if (!task || state === 4) return <section role="status" className="space-y-3 rounded-lg border border-primary/30 bg-card p-4"><p className="font-medium text-primary">{t("Generating Video")}</p><div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} className="h-3 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} /></div><p className="text-sm">{t("Task Progress")}: {progress}%</p>{logBlock}</section>;
  if (state === TASK_STATE_FAILED) return <section role="alert" className="space-y-3 rounded-lg border border-destructive/40 bg-destructive/20 p-4 text-destructive-foreground"><p>{t("Video Generation Failed")}{task.error ? `: ${task.error}` : ""}</p>{logBlock}</section>;
  const videos = task.videos || [];
  if (state !== TASK_STATE_COMPLETE || !videos.length) return <section role="alert" className="space-y-3 rounded-lg border border-destructive/40 bg-destructive/20 p-4 text-destructive-foreground"><p>{t("Video Generation Failed")}</p>{logBlock}</section>;
  return <section role="status" className="space-y-4 rounded-lg border border-success/30 bg-card p-4"><p className="font-medium text-success">{t("Video Generation Completed")}</p>{(task.warnings || []).map((warning, index) => <p key={index} className="text-sm text-warning">{typeof warning === "string" ? warning : JSON.stringify(warning)}</p>)}<div className="grid gap-4 md:grid-cols-2">{videos.map((video, index) => <div key={video} className="space-y-2"><video controls className="w-full rounded-md" src={video} /><a className="inline-block rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground" href={video} download>{videos.length > 1 ? `${t("Download Video")} ${index + 1}` : t("Download Video")}</a></div>)}</div>{logBlock}</section>;
}
