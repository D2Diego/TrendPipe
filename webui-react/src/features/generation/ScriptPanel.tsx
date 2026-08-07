import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Select } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { generateScript, generateTerms, previewScriptPrompt } from "@/api/scripts";
import { useGenerationStore } from "@/store/generationStore";
import { Panel } from "./Panel";

const SCRIPT_LANGUAGES = ["", "zh-CN", "zh-HK", "zh-TW", "de-DE", "en-US", "es-ES", "fr-FR", "pt-BR", "ru-RU", "vi-VN", "th-TH", "tr-TR"];

export function ScriptPanel() {
  const { t } = useTranslation();
  const params = useGenerationStore((state) => state.params);
  const setParam = useGenerationStore((state) => state.setParam);
  const [previewOpen, setPreviewOpen] = useState(false);
  const preview = useMutation({ mutationFn: () => previewScriptPrompt({
    video_subject: params.video_subject,
    video_language: params.video_language,
    paragraph_number: params.paragraph_number,
    video_script_prompt: params.video_script_prompt,
    custom_system_prompt: params.custom_system_prompt,
  }), onSuccess: () => setPreviewOpen(true) });

  const scriptAndTerms = useMutation({ mutationFn: async () => {
    const script = await generateScript({
      video_subject: params.video_subject,
      video_language: params.video_language,
      paragraph_number: params.paragraph_number,
      video_script_prompt: params.video_script_prompt,
      custom_system_prompt: params.custom_system_prompt,
    });
    setParam("video_script", script.video_script);
    const terms = await generateTerms({ video_subject: params.video_subject, video_script: script.video_script, amount: params.match_materials_to_script ? 8 : 5, match_materials_to_script: params.match_materials_to_script });
    setParam("video_terms", terms.video_terms.join(", "));
  }});
  const termsOnly = useMutation({ mutationFn: async () => {
    const terms = await generateTerms({ video_subject: params.video_subject, video_script: params.video_script, amount: params.match_materials_to_script ? 8 : 5, match_materials_to_script: params.match_materials_to_script });
    setParam("video_terms", terms.video_terms.join(", "));
  }});
  const error = scriptAndTerms.error || termsOnly.error;

  return <Panel title={t("Video Script Settings")}>
    <Field label={t("Video Subject")} htmlFor="video-subject">
      <Textarea id="video-subject" aria-label={t("Video Subject")} rows={3} placeholder={t("Video Subject Placeholder")} value={params.video_subject} onChange={(event) => setParam("video_subject", event.target.value)} />
    </Field>
    <Field label={t("Script Language")} htmlFor="script-language">
      <Select id="script-language" aria-label={t("Script Language")} value={params.video_language} onChange={(event) => setParam("video_language", event.target.value)}>
        {SCRIPT_LANGUAGES.map((language) => <option key={language || "auto"} value={language}>{language || t("Auto Detect")}</option>)}
      </Select>
    </Field>
    <details className="rounded-md border border-border p-3">
      <summary className="cursor-pointer font-medium">{t("Advanced Script Settings")}</summary>
      <div className="mt-4 space-y-4">
        <Field label={`${t("Script Paragraph Number")}: ${params.paragraph_number}`} htmlFor="paragraph-number">
          <input id="paragraph-number" aria-label={t("Script Paragraph Number")} className="w-full accent-primary" type="range" min={1} max={10} value={params.paragraph_number} onChange={(event) => setParam("paragraph_number", Number(event.target.value))} />
        </Field>
        <Field label={t("Custom Script Requirements")} htmlFor="script-requirements">
          <Textarea id="script-requirements" maxLength={2000} rows={4} value={params.video_script_prompt} onChange={(event) => setParam("video_script_prompt", event.target.value)} placeholder={t("Custom Script Requirements Placeholder")} />
        </Field>
        <Field label={t("Custom System Prompt")} htmlFor="system-prompt">
          <Textarea id="system-prompt" maxLength={8000} rows={8} value={params.custom_system_prompt} onChange={(event) => setParam("custom_system_prompt", event.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Button type="button" onClick={() => setParam("custom_system_prompt", "")}>{t("Restore Default System Prompt")}</Button>
          <Button type="button" disabled={preview.isPending} onClick={() => preview.mutate()}>{t("Preview Final Prompt")}</Button>
        </div>
        {preview.error ? <p role="alert" className="text-sm text-destructive-foreground">{String(preview.error)}</p> : null}
      </div>
    </details>
    <Button className="w-full" type="button" disabled={!params.video_subject.trim() || scriptAndTerms.isPending} onClick={() => scriptAndTerms.mutate()}>{t("Generate Video Script and Keywords")}</Button>
    <Field label={t("Video Script")} htmlFor="video-script" help={t("Video Script Help")}>
      <Textarea id="video-script" aria-label={t("Video Script")} rows={7} value={params.video_script} onChange={(event) => setParam("video_script", event.target.value)} />
    </Field>
    <Button className="w-full" type="button" disabled={!params.video_script.trim() || termsOnly.isPending} onClick={() => termsOnly.mutate()}>{t("Generate Video Keywords")}</Button>
    <Field label={t("Video Keywords")} htmlFor="video-terms" help={t("Video Keywords Help")}>
      <Textarea id="video-terms" aria-label={t("Video Keywords")} rows={3} value={Array.isArray(params.video_terms) ? params.video_terms.join(", ") : params.video_terms || ""} onChange={(event) => setParam("video_terms", event.target.value)} />
    </Field>
    {error ? <p role="alert" className="text-sm text-destructive-foreground">{String(error)}</p> : null}
    <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} title={t("Final Prompt Preview")}><pre className="max-h-[65vh] overflow-auto whitespace-pre-wrap rounded bg-muted p-3 text-xs text-muted-foreground">{preview.data?.prompt}</pre></Dialog>
  </Panel>;
}
