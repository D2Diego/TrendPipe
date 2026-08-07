import { apiDelete, apiGet, apiPost, apiPut } from "./client";
export const getUiConfig = () => apiGet<Record<string, unknown>>("/config/ui");
export const setUiConfigValue = async (key: string, value: unknown) => {
  const result = await apiPut<{ updated: boolean }>(`/config/ui/${key}`, { value });
  await saveConfig();
  return result;
};
export interface GenerationReadiness { pexels: boolean; pixabay: boolean; coverr: boolean; sonilo: boolean; elevenlabs: boolean }
export const getGenerationReadiness = () => apiGet<GenerationReadiness>("/config/readiness");
export const getConfigSection = (section: string) => apiGet<Record<string, unknown>>(`/config/${section}`);
export const setConfigValue = async (section: string, key: string, value: unknown) => {
  const result = await apiPut<{ updated: boolean }>(`/config/${section}/${key}`, { value });
  await saveConfig();
  return result;
};
export const deleteConfigValue = async (section: string, key: string) => {
  const result = await apiDelete<{ deleted: boolean }>(`/config/${section}/${key}`);
  await saveConfig();
  return result;
};
export const saveConfig = () => apiPost<{ saved: boolean }>("/config/save");
