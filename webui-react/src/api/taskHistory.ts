import { apiGet } from "./client";

export interface TaskSummary { task_id: string; subject: string; state: number | null; progress: number; mtime?: number; video_file?: string; task_path?: string; source?: string }
export interface TaskRestorePayload { task_id: string; subject: string; params: Record<string, unknown> }
export const listTaskHistory = () => apiGet<{ tasks: TaskSummary[] }>("/tasks/history");
export const getTaskRestoreParams = (taskId: string) => apiGet<TaskRestorePayload>(`/tasks/${encodeURIComponent(taskId)}/restore-params`);
