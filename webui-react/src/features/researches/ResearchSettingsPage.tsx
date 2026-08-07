import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { getResearchSettings, updateResearchSettings } from "@/api/research";

const CREDENTIAL_KEYS = [
  "OPENROUTER_API_KEY",
  "GOOGLE_API_KEY",
  "OPENAI_API_KEY",
  "XAI_API_KEY",
  "PERPLEXITY_API_KEY",
  "SCRAPECREATORS_API_KEY",
  "GITHUB_TOKEN",
  "BRAVE_API_KEY",
  "EXA_API_KEY",
  "SERPER_API_KEY",
];

export function ResearcherSettingsTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<Record<string, string>>({});
  const settings = useQuery({ queryKey: ["research-settings"], queryFn: getResearchSettings });
  const save = useMutation({
    mutationFn: () => updateResearchSettings(Object.fromEntries(
      Object.entries(values).filter(([, value]) => value.length > 0),
    )),
    onSuccess: async () => {
      setValues({});
      await queryClient.invalidateQueries({ queryKey: ["research-settings"] });
    },
  });

  const credentials = settings.data?.permission_preflight?.credentials ?? {};

  return <div data-testid="researcher-settings-tab" className="space-y-6">
    <div className="space-y-2">
      <h2 className="text-xl font-semibold">{t("Researcher Settings")}</h2>
      <p className="text-sm text-muted-foreground">{t("Configure the credentials and sources used by the research assistant.")}</p>
      <p className="text-sm text-muted-foreground">{t("Credential values are never returned by the API.")}</p>
    </div>

    {settings.isPending ? <p>{t("Loading...")}</p> : null}
    {settings.error ? <p role="alert" className="text-sm text-destructive">{settings.error.message}</p> : null}
    {settings.data ? <section className="space-y-3 rounded-lg border border-border bg-card p-4">
      <div>
        <h2 className="font-semibold">{t("Available sources")}</h2>
        <p className="text-sm text-muted-foreground">{settings.data.available_sources.length ? settings.data.available_sources.join(", ") : t("None")}</p>
      </div>
      <div>
        <h2 className="font-semibold">{t("Credential status")}</h2>
        <ul className="mt-2 grid gap-2 sm:grid-cols-2">
          {Object.entries(credentials).map(([key, info]) => <li key={key} className="flex items-center justify-between gap-3 rounded border border-border p-2 text-sm">
            <span>{info.label}</span>
            <span className="text-muted-foreground">{info.present ? t("configured") : t("missing")}</span>
          </li>)}
        </ul>
      </div>
    </section> : null}

    <form className="space-y-4 rounded-lg border border-border bg-card p-4" onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
      <h2 className="font-semibold">{t("Update credentials")}</h2>
      <p className="text-sm text-muted-foreground">{t("Leave a field blank to keep its current value.")}</p>
      <div className="grid gap-4 md:grid-cols-2">
        {CREDENTIAL_KEYS.map((key) => <Field key={key} label={key} htmlFor={key}>
          <Input id={key} aria-label={key} type="password" autoComplete="off" value={values[key] ?? ""} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} />
        </Field>)}
      </div>
      <Button type="submit" variant="primary" disabled={save.isPending || !Object.values(values).some(Boolean)}>{save.isPending ? t("Saving...") : t("Save")}</Button>
      {save.isSuccess ? <p role="status" className="text-sm text-muted-foreground">{t("Saved.")}</p> : null}
      {save.error ? <p role="alert" className="text-sm text-destructive">{save.error.message}</p> : null}
    </form>
  </div>;
}
