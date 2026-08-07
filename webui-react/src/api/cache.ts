import { apiDelete, apiGet } from "./client";

export interface VideoCacheStats { file_count: number; total_size: number; oldest_mtime: number | null; newest_mtime: number | null }
export interface VideoCacheCleanupResult { deleted_count: number; deleted_size: number; failed_count: number }

export const getCacheStats = (maxAgeDays?: number) => apiGet<VideoCacheStats>("/cache/video/stats", maxAgeDays === undefined ? undefined : { max_age_days: String(maxAgeDays) });
export const cleanCache = (maxAgeDays?: number) => apiDelete<VideoCacheCleanupResult>(`/cache/video${maxAgeDays === undefined ? "" : `?max_age_days=${maxAgeDays}`}`);
