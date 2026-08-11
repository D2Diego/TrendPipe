import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getResearchSettings } from "@/api/research";
import { CredentialRow } from "./CredentialRow";

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
  const settings = useQuery({ queryKey: ["research-settings"], queryFn: getResearchSettings });
  const presence = settings.data?.credential_keys ?? {};

  return <div data-testid="researcher-settings-tab" className="space-y-6">
    <div className="space-y-2">
      <h2 className="text-xl font-semibold">{t("Researcher Settings")}</h2>
      <p className="text-sm text-muted-foreground">{t("Configure the credentials and sources used by the research assistant.")}</p>
      <p className="text-sm text-muted-foreground">{t("Credential values are never returned by the API.")}</p>
    </div>

    {settings.isPending ? <p>{t("Loading...")}</p> : null}
    {settings.error ? <p role="alert" className="text-sm text-destructive">{settings.error.message}</p> : null}
    {settings.data ? <section className="space-y-3 rounded-lg border border-border bg-card p-4">
      <h2 className="font-semibold">{t("Available sources")}</h2>
      <p className="text-sm text-muted-foreground">{settings.data.available_sources.length ? settings.data.available_sources.join(", ") : t("None")}</p>
    </section> : null}

    {settings.data ? <section className="space-y-3 rounded-lg border border-border bg-card p-4">
      <h2 className="font-semibold">{t("Update credentials")}</h2>
      <div className="grid gap-3 md:grid-cols-2">
        {CREDENTIAL_KEYS.map((key) => <CredentialRow key={key} credKey={key} present={Boolean(presence[key])} />)}
      </div>
    </section> : null}
  </div>;
}
