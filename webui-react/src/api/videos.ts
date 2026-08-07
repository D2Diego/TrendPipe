import type { VideoParams } from "@/types/videoParams";
import { apiDelete, apiGet, apiPost } from "./client";
export interface TaskResponseData { task_id: string; request_id: string; params: VideoParams }
export interface TaskStatusData { task_id: string; state: number; progress: number; videos?: string[] | null; combined_videos?: string[] | null; warnings?: unknown[]; failed_stage?: string | null; error?: string | null }
export const createVideoTask = (params: VideoParams) => apiPost<TaskResponseData>("/videos", params);
export const getTaskStatus = (taskId: string) => apiGet<TaskStatusData>(`/tasks/${taskId}`);
export const getTaskLogs = (taskId: string) => apiGet<{ logs: string[] }>(`/tasks/${taskId}/logs`);
export const deleteTask = (taskId: string) => apiDelete<void>(`/tasks/${encodeURIComponent(taskId)}`);
