import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getConfigSection, setConfigValue } from "@/api/config";
import { listGroqModels, listLlmProviders, testLlmConnection } from "@/api/providers";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";

export function LlmSettingsTab() {
  const { t } = useTranslation();
  const providers = useQuery({ queryKey: ["llm-providers"], queryFn: listLlmProviders });
  const config = useQuery({ queryKey: ["config", "app"], queryFn: () => getConfigSection("app") });
  const [providerId, setProviderId] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    if (!config.data) return;
    setProviderId(String(config.data.llm_provider || providers.data?.providers[0]?.provider_id || ""));
    setValues(Object.fromEntries(Object.entries(config.data).map(([key, value]) => [key, value == null ? "" : String(value)])));
    setHydrated(true);
  }, [config.data, providers.data]);

  const provider = providers.data?.providers.find((item) => item.provider_id === providerId) || providers.data?.providers[0];
  const key = (suffix: string) => `${provider?.provider_id || ""}_${suffix}`;
  const value = (configKey: string, fallback = "") => values[configKey] ?? String(config.data?.[configKey] ?? fallback);
  const commit = (configKey: string) => setConfigValue("app", configKey, value(configKey));
  const apiKey = value(key("api_key"));
  const baseUrl = value(key("base_url"), provider?.default_base_url);
  const groqModels = useQuery({ queryKey: ["groq-models", apiKey, baseUrl], queryFn: () => listGroqModels(apiKey, baseUrl), enabled: provider?.provider_id === "groq" && Boolean(apiKey), retry: false });
  const test = useMutation({ mutationFn: testLlmConnection });
  const tipKey = provider ? `llm_provider_tips.${provider.provider_id}` : "";
  const tip = useMemo(() => tipKey ? t(tipKey) : "", [t, tipKey]);

  if (providers.isLoading || config.isLoading || !hydrated) return <p role="status">{t("Loading")}</p>;
  if (!provider) return <p role="alert">{t("No LLM providers available")}</p>;

  const textField = (label: string, configKey: string, fallback = "", secret = false) => <Field key={configKey} label={t(label)} htmlFor={configKey}><Input id={configKey} aria-label={t(label)} type={secret ? "password" : "text"} value={value(configKey, fallback)} onChange={(event) => setValues((current) => ({ ...current, [configKey]: event.target.value }))} onBlur={() => void commit(configKey)} /></Field>;

  return <div className="space-y-4">
    <Field label={t("LLM Provider")} htmlFor="llm-provider"><Select id="llm-provider" aria-label={t("LLM Provider")} value={provider.provider_id} onChange={(event) => { setProviderId(event.target.value); void setConfigValue("app", "llm_provider", event.target.value); }}>{providers.data?.providers.map((item) => <option key={item.provider_id} value={item.provider_id}>{item.default_label}</option>)}</Select></Field>
    {provider.show_api_key ? textField("API Key", key("api_key"), "", true) : null}
    {provider.show_base_url ? textField("Base Url", key("base_url"), provider.default_base_url) : null}
    {provider.provider_id === "groq" && groqModels.data?.models.length ? <Field label={t("Model Name")} htmlFor="llm-model"><Select id="llm-model" aria-label={t("Model Name")} value={value(key("model_name"), provider.default_model)} onChange={(event) => { setValues((current) => ({ ...current, [key("model_name")]: event.target.value })); void setConfigValue("app", key("model_name"), event.target.value); }}>{groqModels.data.models.map((model) => <option key={model}>{model}</option>)}</Select></Field> : textField("Model Name", key("model_name"), provider.default_model)}
    {(provider.extra_fields || []).map((field) => textField(field.label_key, key(field.config_suffix), field.default_value, field.secret))}
    {tip && tip !== tipKey ? <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground">{tip}</p> : null}
    <Button type="button" className="w-full" onClick={() => test.mutate()} disabled={test.isPending}>{t("Test LLM Connection")}</Button>
    {test.data?.ok ? <p role="status" className="text-sm text-success">{t("LLM Connection Successful")} ({test.data.elapsed.toFixed(2)}s)</p> : null}
    {test.data && !test.data.ok ? <p role="alert" className="text-sm text-destructive-foreground">{test.data.error || t("LLM Connection Failed")}</p> : null}
    {test.error ? <p role="alert" className="text-sm text-destructive-foreground">{String(test.error)}</p> : null}
  </div>;
}
