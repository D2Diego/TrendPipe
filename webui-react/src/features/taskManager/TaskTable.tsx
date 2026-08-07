import { useTranslation } from "react-i18next";
import type { TaskSummary } from "@/api/taskHistory";
import { Button } from "@/components/ui/button";
import { formatTaskSubject, formatTaskTime, taskStatusFilterKey } from "./format";

const STATUS_LABELS = { processing: "Task Status Processing", complete: "Task Status Complete", failed: "Task Status Failed", history: "Task Status History" } as const;

export function TaskTable({ tasks, onPlay, onRegenerate, onDelete, deletingId }: { tasks: TaskSummary[]; onPlay: (task: TaskSummary) => void; onRegenerate: (taskId: string) => void; onDelete: (taskId: string) => void; deletingId?: string | null }) {
  const { t } = useTranslation();
  if (!tasks.length) return <p className="py-8 text-center text-sm text-muted-foreground">{t("No Tasks Match Filter")}</p>;
  return <div className="max-h-[390px] overflow-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="sticky top-0 bg-card"><tr className="border-b border-border"><th className="p-2">{t("Status")}</th><th className="p-2">{t("Updated At")}</th><th className="p-2">{t("Subject")}</th><th className="p-2">{t("Progress")}</th><th className="p-2">{t("Actions")}</th></tr></thead><tbody>{tasks.slice(0, 12).map((task) => {
    const status = taskStatusFilterKey(task);
    return <tr key={task.task_id} className="border-b border-border/70"><td className="p-2"><span className={status === "failed" ? "text-destructive-foreground" : status === "complete" ? "text-success" : status === "processing" ? "text-primary" : "text-muted-foreground"}>{t(STATUS_LABELS[status])}</span></td><td className="whitespace-nowrap p-2">{formatTaskTime(task.mtime)}</td><td className="p-2" title={task.subject}>{formatTaskSubject(task.subject)}</td><td className="p-2">{Math.max(0, Math.min(100, Number(task.progress || 0)))}%</td><td className="flex gap-1 p-2"><Button type="button" variant="ghost" className="px-2 py-1" aria-label={t("Play")} disabled={!task.video_file} onClick={() => onPlay(task)}>{t("Play")}</Button><Button type="button" variant="ghost" className="px-2 py-1" aria-label={t("Regenerate")} disabled={status === "processing"} onClick={() => onRegenerate(task.task_id)}>{t("Regenerate")}</Button><Button type="button" variant="destructive" className="px-2 py-1" aria-label={t("Delete Task")} disabled={status === "processing" || deletingId === task.task_id} onClick={() => onDelete(task.task_id)}>{t("Delete")}</Button></td></tr>;
  })}</tbody></table></div>;
}
