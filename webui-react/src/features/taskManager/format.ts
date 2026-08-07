export function formatTaskTime(mtime?: number) {
  if (!mtime) return "-";
  const date = new Date(mtime * 1000); const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
export function formatTaskSubject(subject: string, maxLength = 30) {
  const flat = String(subject || "").replace(/\r?\n/g, " ").trim();
  return flat.length > maxLength ? `${flat.slice(0, maxLength)}...` : flat || "-";
}
export type TaskFilterKey = "processing" | "failed" | "complete" | "history";
export function taskStatusFilterKey(task: { state: number | null; video_file?: string }): TaskFilterKey {
  if (task.state === 4) return "processing";
  if (task.state === -1) return "failed";
  if (task.state === 1 || task.video_file) return "complete";
  return "history";
}
