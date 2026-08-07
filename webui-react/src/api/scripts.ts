import { apiPost } from "./client";
export interface ScriptPromptParams { video_subject: string; video_language?: string; paragraph_number: number; video_script_prompt?: string; custom_system_prompt?: string }
export const generateScript = (params: ScriptPromptParams) => apiPost<{ video_script: string }>("/scripts", params);
export const previewScriptPrompt = (params: ScriptPromptParams) => apiPost<{ prompt: string }>("/scripts/preview", params);
export const generateTerms = (params: { video_subject: string; video_script: string; amount: number; match_materials_to_script: boolean }) => apiPost<{ video_terms: string[] }>("/terms", params);
