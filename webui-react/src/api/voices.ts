import { apiGet, apiPost } from "./client";
export interface VoicePreviewResult { audio_base64: string; mime_type: string; duration: number | null }
export const listVoices = (provider: string) => apiGet<{ voices: string[] }>("/voices", { provider });
export const previewVoice = (params: { content: string; voice_name: string; voice_rate: number; voice_volume: number }) => apiPost<VoicePreviewResult>("/voices/preview", params);
