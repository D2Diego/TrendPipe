import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getConfigSection, setConfigValue } from "@/api/config";
import { Field, Input } from "@/components/ui/field";

const FIELDS = [["Pexels API Key", "pexels_api_keys"], ["Pixabay API Key", "pixabay_api_keys"], ["Coverr API Key", "coverr_api_keys"]] as const;

export function MaterialApiTab() {
  const { t } = useTranslation();
  const config = useQuery({ queryKey: ["config", "app"], queryFn: () => getConfigSection("app") });
  const [values, setValues] = useState<Record<string, string>>({});
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    if (!config.data) return;
    setValues(Object.fromEntries(FIELDS.map(([, key]) => [key, Array.isArray(config.data?.[key]) ? (config.data[key] as unknown[]).join(",") : String(config.data?.[key] || "")] )));
    setHydrated(true);
  }, [config.data]);
  if (!config.data || !hydrated) return <p role="status">{t("Loading")}</p>;
  return <div className="space-y-4">{FIELDS.map(([label, key]) => <Field key={key} label={t(label)} htmlFor={key}><Input id={key} aria-label={t(label)} type="password" value={values[key] || ""} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} onBlur={() => void setConfigValue("app", key, (values[key] || "").split(",").map((item) => item.trim()).filter(Boolean))} /></Field>)}</div>;
}
