import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getConfigSection, setConfigValue } from "@/api/config";
import { Field, Input, Select } from "@/components/ui/field";

type FieldDef = { label: string; key: string; secret?: boolean; fallback?: string; options?: string[]; list?: boolean };
const SETTINGS: Record<string, { section: string; fields: FieldDef[] }> = {
  "azure-tts-v2": { section: "azure", fields: [{ label: "Speech Region", key: "speech_region" }, { label: "Speech Key", key: "speech_key", secret: true }] },
  "gemini-tts": { section: "app", fields: [{ label: "Gemini API Key", key: "gemini_api_key", secret: true }] },
  siliconflow: { section: "siliconflow", fields: [{ label: "SiliconFlow API Key", key: "api_key", secret: true }] },
  "mimo-tts": { section: "app", fields: [{ label: "MiMo API Key", key: "mimo_api_key", secret: true }] },
  elevenlabs: { section: "elevenlabs", fields: [{ label: "ElevenLabs API Key", key: "api_key", secret: true }, { label: "ElevenLabs Model", key: "model_id", fallback: "eleven_multilingual_v2", options: ["eleven_multilingual_v2", "eleven_flash_v2_5", "eleven_v3"] }] },
  chatterbox: { section: "chatterbox", fields: [{ label: "Chatterbox Base URL", key: "base_url", fallback: "http://localhost:4123/v1" }, { label: "Chatterbox API Key", key: "api_key", secret: true }, { label: "Chatterbox Model", key: "model_id", fallback: "chatterbox" }, { label: "Chatterbox Voices", key: "voices", fallback: "default-Female, narrator-Male", list: true }] },
};

export function ProviderCredentials({ provider }: { provider: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const settings = SETTINGS[provider];
  const config = useQuery({ queryKey: ["config", settings?.section], queryFn: () => getConfigSection(settings!.section), enabled: Boolean(settings) });
  const [values, setValues] = useState<Record<string, string>>({});
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    if (!settings || !config.data) return;
    setValues(Object.fromEntries(settings.fields.map((field) => { const raw = config.data?.[field.key]; return [field.key, Array.isArray(raw) ? raw.join(", ") : String(raw ?? field.fallback ?? "")]; })));
    setHydrated(true);
  }, [config.data, settings]);
  const tipKey = `tts_provider_tips.${provider}`; const tip = t(tipKey);
  if (!settings) return null;
  if (!config.data || !hydrated) return <p role="status" className="text-sm text-muted-foreground">{t("Loading")}</p>;
  const save = async (field: FieldDef) => { const raw = values[field.key] || ""; await setConfigValue(settings.section, field.key, field.list ? raw.split(",").map((item) => item.trim()).filter(Boolean) : raw.trim()); await queryClient.invalidateQueries({ queryKey: ["voices", provider] }); };
  return <div className="space-y-3 rounded-md border border-border bg-muted/40 p-3">{tip !== tipKey ? <p className="text-sm text-muted-foreground">{tip}</p> : null}{settings.fields.map((field) => <Field key={field.key} label={t(field.label)} htmlFor={`provider-${field.key}`}>{field.options ? <Select id={`provider-${field.key}`} aria-label={t(field.label)} value={values[field.key] || field.fallback} onChange={(event) => { setValues((current) => ({ ...current, [field.key]: event.target.value })); void setConfigValue(settings.section, field.key, event.target.value); }}>{field.options.map((option) => <option key={option}>{option}</option>)}</Select> : <Input id={`provider-${field.key}`} aria-label={t(field.label)} type={field.secret ? "password" : "text"} value={values[field.key] || ""} onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))} onBlur={() => void save(field)} />}</Field>)}</div>;
}
