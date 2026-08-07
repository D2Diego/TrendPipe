import { apiGet, apiPost } from "./client";
export interface LlmProviderExtraField { config_suffix: string; label_key: string; required: boolean; secret: boolean; default_value: string }
export interface LlmProvider { provider_id: string; default_label: string; adapter: string; api_key_url: string; default_model: string; default_base_url: string; requires_api_key: boolean; requires_model_name: boolean; requires_base_url: boolean; show_api_key: boolean; show_base_url: boolean; extra_fields?: LlmProviderExtraField[] }
export const listLlmProviders = () => apiGet<{ providers: LlmProvider[] }>("/providers/llm");
export const listGroqModels = (apiKey: string, baseUrl: string) => apiPost<{ models: string[] }>("/providers/llm/groq/models", { api_key: apiKey, base_url: baseUrl });
export const testLlmConnection = () => apiPost<{ ok: boolean; error: string; elapsed: number }>("/providers/llm/test");
export const testSoniloConnection = () => apiPost<{ ok: boolean; error: string }>("/providers/bgm/sonilo/test");
export const testElevenLabsMusicConnection = () => apiPost<{ ok: boolean; error: string; paid_plan_required: boolean }>("/providers/bgm/elevenlabs/test");
