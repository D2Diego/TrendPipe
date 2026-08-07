import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getConfigSection, setConfigValue } from "@/api/config";
import { testElevenLabsMusicConnection, testSoniloConnection } from "@/api/providers";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { LocalAudioPreview } from "@/components/ui/LocalAudioPreview";
import { useGenerationStore } from "@/store/generationStore";

export function BgmSettings() {
  const { t } = useTranslation();
  const params = useGenerationStore((state) => state.params);
  const setParam = useGenerationStore((state) => state.setParam);
  const uploaded = useGenerationStore((state) => state.uploadedBgmFile);
  const setUploaded = useGenerationStore((state) => state.setUploadedBgmFile);
  const voiceMode = useGenerationStore((state) => state.voiceMode);
  const ttsServer = useGenerationStore((state) => state.ttsServer);
  const generated = params.bgm_type === "sonilo" || params.bgm_type === "elevenlabs";
  const configSection = params.bgm_type === "elevenlabs" ? "elevenlabs" : "app";
  const config = useQuery({
    queryKey: ["config", configSection],
    queryFn: () => getConfigSection(configSection),
    enabled: generated,
  });
  const [apiKey, setApiKey] = useState("");
  const [hydratedSection, setHydratedSection] = useState("");
  useEffect(() => {
    if (!config.data) return;
    const key = params.bgm_type === "elevenlabs" ? "api_key" : "sonilo_api_key";
    setApiKey(String(config.data[key] || ""));
    setHydratedSection(configSection);
  }, [config.data, params.bgm_type]);
  const testConnection = useMutation({
    mutationFn: params.bgm_type === "sonilo" ? testSoniloConnection : testElevenLabsMusicConnection,
  });
  const commitApiKey = (value = apiKey) => setConfigValue(
    configSection,
    params.bgm_type === "elevenlabs" ? "api_key" : "sonilo_api_key",
    value,
  );
  const elevenLabsKeyAlreadyShown = params.bgm_type === "elevenlabs" && voiceMode === "tts" && ttsServer === "elevenlabs";
  const paidPlanRequired = testConnection.data && "paid_plan_required" in testConnection.data && testConnection.data.paid_plan_required;
  return <div className="space-y-4 border-t border-border pt-4">
    <Field label={t("Background Music Source")} htmlFor="bgm-source">
      <Select id="bgm-source" aria-label={t("Background Music Source")} value={params.bgm_type} onChange={(event) => { setParam("bgm_type", event.target.value); if (event.target.value !== "custom") { setUploaded(null); setParam("bgm_file", ""); } }}>
        <option value="">{t("No Background Music")}</option><option value="random">{t("Random Background Music")}</option><option value="custom">{t("Custom Background Music")}</option><option value="sonilo">{t("Sonilo Background Music")}</option><option value="elevenlabs">{t("ElevenLabs Background Music")}</option>
      </Select>
    </Field>
    <Field label={t("Background Music Volume")} htmlFor="bgm-volume"><Select id="bgm-volume" aria-label={t("Background Music Volume")} disabled={!params.bgm_type} value={params.bgm_volume} onChange={(event) => setParam("bgm_volume", Number(event.target.value))}>{Array.from({ length: 11 }, (_, index) => index / 10).map((value) => <option key={value} value={value}>{Math.round(value * 100)}%</option>)}</Select></Field>
    {params.bgm_type === "custom" ? <>
      <Field label={t("Upload Background Music")} htmlFor="bgm-upload" help={t("Upload Background Music Help")}><input id="bgm-upload" aria-label={t("Upload Background Music")} className="block w-full text-sm" type="file" accept="audio/*,.mp3,.m4a,.aac,.wav,.flac,.ogg,.opus,.wma" onChange={(event) => setUploaded(event.target.files?.[0] || null)} /></Field>
      <Field label={t("Custom Background Music File")} htmlFor="bgm-path"><Input id="bgm-path" disabled={Boolean(uploaded)} value={params.bgm_file} onChange={(event) => setParam("bgm_file", event.target.value)} /></Field>
      {uploaded ? <><LocalAudioPreview file={uploaded} label={t("Background Music Ready")} /><p className="text-sm text-success">{t("Background Music Ready")}: {uploaded.name}</p></> : null}
    </> : null}
    {generated ? <>
      {config.isLoading || hydratedSection !== configSection ? <p role="status" className="text-sm text-muted-foreground">{t("Loading")}</p> : elevenLabsKeyAlreadyShown
        ? <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground">{t("ElevenLabs API Key Help")}</p>
        : <Field label={t(params.bgm_type === "sonilo" ? "Sonilo API Key" : "ElevenLabs Music API Key")} htmlFor="bgm-api-key">
          <Input id="bgm-api-key" aria-label={t(params.bgm_type === "sonilo" ? "Sonilo API Key" : "ElevenLabs Music API Key")} type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} onBlur={(event) => void commitApiKey(event.currentTarget.value)} />
        </Field>}
      <Field label={t(params.bgm_type === "sonilo" ? "Sonilo Music Prompt" : "ElevenLabs Music Prompt")} htmlFor="music-prompt" help={t(params.bgm_type === "sonilo" ? "Sonilo Music Prompt Help" : "ElevenLabs Music Prompt Help")}><Input id="music-prompt" maxLength={params.bgm_type === "sonilo" ? 2000 : 1000} value={params.video_music_prompt} onChange={(event) => { setParam("video_music_prompt", event.target.value); if (params.bgm_type === "sonilo") setParam("sonilo_bgm_prompt", event.target.value); }} /></Field>
      {params.video_count > 1 ? <p className="text-sm text-warning">{t(params.bgm_type === "sonilo" ? "Sonilo Multiple Videos Warning" : "ElevenLabs Multiple Videos Warning")}</p> : null}
      <Button type="button" className="w-full" disabled={testConnection.isPending} onClick={() => testConnection.mutate()}>{t(params.bgm_type === "sonilo" ? "Test Sonilo Connection" : "Test ElevenLabs Connection")}</Button>
      {testConnection.data?.ok ? <p role="status" className="text-sm text-success">{t(params.bgm_type === "sonilo" ? "Sonilo Connection Test Succeeded" : "ElevenLabs Connection Test Succeeded")}</p> : null}
      {paidPlanRequired ? <p role="alert" className="text-sm text-warning">{t("ElevenLabs Paid Plan Required")}</p> : null}
      {testConnection.data && !testConnection.data.ok && !paidPlanRequired ? <p role="alert" className="text-sm text-destructive-foreground">{t(params.bgm_type === "sonilo" ? "Sonilo Connection Test Failed" : "ElevenLabs Connection Test Failed", { error: testConnection.data.error })}</p> : null}
      {testConnection.error ? <p role="alert" className="text-sm text-destructive-foreground">{String(testConnection.error)}</p> : null}
    </> : null}
  </div>;
}
