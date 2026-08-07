import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import {
  createResearch,
  getResearchSettings,
  type ResearchDepth,
} from "@/api/research";

const DEFAULT_SOURCES = [
  "reddit",
  "hackernews",
  "grounding",
  "polymarket",
  "github",
  "tiktok",
  "instagram",
  "youtube",
  "linkedin",
];

export function NewResearchForm({ onCreated }: { onCreated: (researchId: string) => void }) {
  const { t } = useTranslation();
  const [topic, setTopic] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("quick");
  const [sources, setSources] = useState<string[]>([]);
  const settings = useQuery({ queryKey: ["research-settings"], queryFn: getResearchSettings });
  const create = useMutation({
    mutationFn: () => createResearch({ topic: topic.trim(), depth, sources }),
    onSuccess: (created) => onCreated(created.id),
  });

  const available = new Set(settings.data?.available_sources ?? []);
  const allSources = [...new Set([...DEFAULT_SOURCES, ...available])];
  const hasUnavailableSources = allSources.some((source) => !available.has(source));

  function toggleSource(source: string) {
    setSources((current) => current.includes(source)
      ? current.filter((item) => item !== source)
      : [...current, source]);
  }

  return <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
    <Field label={t("Research Topic")} htmlFor="research-topic">
      <Input id="research-topic" aria-label={t("Research Topic")} value={topic} onChange={(event) => setTopic(event.target.value)} />
    </Field>
    <Field label={t("Depth")} htmlFor="research-depth">
      <Select id="research-depth" aria-label={t("Depth")} value={depth} onChange={(event) => setDepth(event.target.value as ResearchDepth)}>
        <option value="quick">{t("Quick")}</option>
        <option value="deep">{t("Deep")}</option>
      </Select>
    </Field>
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{t("Sources")}</legend>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {allSources.map((source) => <label key={source} className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            aria-label={source}
            disabled={!available.has(source)}
            checked={sources.includes(source)}
            onChange={() => toggleSource(source)}
          />
          <span>{source}</span>
          {!available.has(source) ? <span className="text-xs text-muted-foreground">({t("credential missing")})</span> : null}
        </label>)}
      </div>
      {hasUnavailableSources ? <p className="text-sm text-muted-foreground">{t("Some sources need credentials. Configure them in Settings > Researcher.")}</p> : null}
    </fieldset>
    <Button type="submit" variant="primary" disabled={settings.isPending || !topic.trim() || sources.length === 0 || create.isPending}>
      {create.isPending ? t("Starting...") : t("Search")}
    </Button>
    {settings.error ? <p role="alert" className="text-sm text-destructive">{settings.error.message}</p> : null}
    {create.error ? <p role="alert" className="text-sm text-destructive">{create.error.message}</p> : null}
  </form>;
}
