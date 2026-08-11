import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SquareKanban } from "lucide-react";
import { useTranslation } from "react-i18next";
import { listTaskHistory, type TaskSummary } from "@/api/taskHistory";
import { deleteTask } from "@/api/videos";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Popover } from "@/components/ui/popover";
import { Tabs } from "@/components/ui/tabs";
import { taskStatusFilterKey } from "./format";
import { RegenerateDialog } from "./RegenerateDialog";
import { TaskTable } from "./TaskTable";

const streamUrl = (path: string) => `/api/v1/stream/${path.split("/").map(encodeURIComponent).join("/")}`;

export function TaskManagerPanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<TaskSummary | null>(null);
  const [restoreId, setRestoreId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const history = useQuery({ queryKey: ["task-history"], queryFn: listTaskHistory, refetchInterval: 2000 });
  const remove = useMutation({ mutationFn: deleteTask, onSuccess: () => { setMessage(t("Task Deleted")); void queryClient.invalidateQueries({ queryKey: ["task-history"] }); }, onError: () => setMessage(t("Task Delete Failed")) });
  const tasks = history.data?.tasks || [];
  const processingCount = tasks.filter((task) => taskStatusFilterKey(task) === "processing").length;
  const table = (filtered: TaskSummary[]) => <TaskTable tasks={filtered} onPlay={setPreview} onRegenerate={setRestoreId} onDelete={(taskId) => remove.mutate(taskId)} deletingId={remove.isPending ? String(remove.variables || "") : null} />;
  const triggerLabel = processingCount ? `${t("Task Manager")} · ${processingCount}` : t("Task Manager");
  return <>
    <Popover open={open} onOpenChange={setOpen} trigger={<Button type="button" className="inline-flex items-center gap-1" onClick={() => setOpen((value) => !value)}><SquareKanban className="size-4" />{triggerLabel}</Button>}>
      <div className="space-y-3"><h2 className="font-semibold">{t("Task Manager")}</h2>{history.error ? <p role="alert" className="text-sm text-destructive-foreground">{String(history.error)}</p> : null}{message ? <p role="status" className="text-sm text-muted-foreground">{message}</p> : null}<Tabs tabs={[
        { key: "all", label: t("All Tasks"), content: table(tasks) },
        { key: "processing", label: t("Task Status Processing"), content: table(tasks.filter((task) => taskStatusFilterKey(task) === "processing")) },
        { key: "complete", label: t("Task Status Complete"), content: table(tasks.filter((task) => taskStatusFilterKey(task) === "complete")) },
        { key: "failed", label: t("Task Status Failed"), content: table(tasks.filter((task) => taskStatusFilterKey(task) === "failed")) },
      ]} /></div>
    </Popover>
    <Dialog open={Boolean(preview)} onClose={() => setPreview(null)} title={preview?.subject || t("Play")} className="max-w-4xl">{preview?.video_file ? <video controls autoPlay className="max-h-[70vh] w-full rounded-md bg-background" src={streamUrl(preview.video_file)} /> : null}</Dialog>
    <RegenerateDialog open={Boolean(restoreId)} taskId={restoreId} onClose={() => setRestoreId(null)} onLoaded={setMessage} />
  </>;
}
