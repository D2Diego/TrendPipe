import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { listVoices } from "@/api/voices";
import { getUiConfig, setUiConfigValue } from "@/api/config";
import { Field, Select } from "@/components/ui/field";
import { LocalAudioPreview } from "@/components/ui/LocalAudioPreview";
import { useGenerationStore, type VoiceMode } from "@/store/generationStore";
import { Panel } from "../Panel";
import { BgmSettings } from "./BgmSettings";
import { VoicePreview } from "./VoicePreview";
import { ProviderCredentials } from "./ProviderCredentials";

const providers = [["azure-tts-v1", "Azure TTS V1"], ["azure-tts-v2", "Azure TTS V2"], ["siliconflow", "SiliconFlow TTS"], ["gemini-tts", "Google Gemini TTS"], ["mimo-tts", "Xiaomi MiMo TTS"], ["elevenlabs", "ElevenLabs TTS"], ["chatterbox", "Chatterbox TTS"]] as const;
const volumeOptions = [0.6, 0.8, 1, 1.2, 1.5, 2, 3, 4, 5];
const rateOptions = [0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.5, 1.8, 2];

export function AudioPanel() {
  const { t, i18n } = useTranslation();
  const params = useGenerationStore((state) => state.params);
  const setParam = useGenerationStore((state) => state.setParam);
  const mode = useGenerationStore((state) => state.voiceMode);
  const setMode = useGenerationStore((state) => state.setVoiceMode);
  const provider = useGenerationStore((state) => state.ttsServer);
  const setProvider = useGenerationStore((state) => state.setTtsServer);
  const setUpload = useGenerationStore((state) => state.setUploadedAudioFile);
  const uploadedAudio = useGenerationStore((state) => state.uploadedAudioFile);
  const uiConfig = useQuery({ queryKey: ["ui-config"], queryFn: getUiConfig, staleTime: 30_000 });
  const voices = useQuery({ queryKey: ["voices", provider], queryFn: () => listVoices(provider), enabled: mode === "tts", retry: false });
  const hydrated = useRef(false);

  useEffect(() => {
    if (hydrated.current || !uiConfig.data) return;
    hydrated.current = true;
    const savedProvider = String(uiConfig.data.tts_server || "");
    if (providers.some(([value]) => value === savedProvider)) setProvider(savedProvider);
    const savedMode = uiConfig.data.voice_mode;
    if (savedMode === "tts" || savedMode === "upload" || savedMode === "none") setMode(savedMode);
    if (typeof uiConfig.data.voice_name === "string") setParam("voice_name", uiConfig.data.voice_name);
  }, [setMode, setParam, setProvider, uiConfig.data]);

  useEffect(() => {
    const options = voices.data?.voices || [];
    if (mode !== "tts" || !options.length || options.includes(params.voice_name)) return;
    const language = i18n.language.toLowerCase();
    setParam("voice_name", options.find((voice) => voice.toLowerCase().startsWith(language)) || options[0]);
  }, [i18n.language, mode, params.voice_name, setParam, voices.data]);

  const changeMode = (next: VoiceMode) => {
    setMode(next);
    void setUiConfigValue("voice_mode", next);
    if (next === "none") { setParam("voice_name", "no-voice"); setUpload(null); }
    if (next === "tts" && params.voice_name === "no-voice") setParam("voice_name", "");
  };

  return <Panel title={t("Audio Settings")}>
    <div><span className="mb-1 block text-sm font-medium">{t("Voiceover Mode")}</span><div role="radiogroup" aria-label={t("Voiceover Mode")} className="grid grid-cols-3 rounded-md border border-border p-1">
      {([["tts", "Automatic Voiceover"], ["upload", "Upload Voiceover"], ["none", "No Voiceover"]] as const).map(([value, label]) => <button key={value} type="button" role="radio" aria-checked={mode === value} onClick={() => changeMode(value)} className={`rounded px-2 py-1.5 text-sm ${mode === value ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}>{t(label)}</button>)}
    </div></div>
    {mode === "tts" ? <>
      <Field label={t("Voiceover Service")} htmlFor="tts-provider"><Select id="tts-provider" aria-label={t("Voiceover Service")} value={provider} onChange={(event) => { setProvider(event.target.value); setParam("voice_name", ""); void setUiConfigValue("tts_server", event.target.value); }}>{providers.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select></Field>
      <ProviderCredentials key={provider} provider={provider} />
      <Field label={t("Voiceover Voice")} htmlFor="voice-name"><Select id="voice-name" aria-label={t("Voiceover Voice")} disabled={voices.isLoading || !voices.data?.voices.length} value={params.voice_name} onChange={(event) => { setParam("voice_name", event.target.value); void setUiConfigValue("voice_name", event.target.value); }}>{(voices.data?.voices || []).map((voice) => <option key={voice} value={voice}>{voice.replace(/-Female|-Male|Neural/g, "")}</option>)}</Select></Field>
      {voices.error ? <p role="alert" className="text-sm text-warning">{t("No voices available for the selected TTS server. Please select another server.")}</p> : null}
      <div className="grid grid-cols-2 gap-2"><Field label={t("Voiceover Volume")} htmlFor="voice-volume" help={t("Voiceover Volume Help")}><Select id="voice-volume" value={params.voice_volume} onChange={(event) => setParam("voice_volume", Number(event.target.value))}>{volumeOptions.map((value) => <option key={value} value={value}>{value * 100}%</option>)}</Select></Field><Field label={t("Voiceover Speed")} htmlFor="voice-rate" help={t("Voiceover Speed Help")}><Select id="voice-rate" value={params.voice_rate} onChange={(event) => setParam("voice_rate", Number(event.target.value))}>{rateOptions.map((value) => <option key={value} value={value}>{value.toFixed(1)}×</option>)}</Select></Field></div>
      <VoicePreview />
    </> : null}
    {mode === "upload" ? <>
      <Field label={t("Upload Voiceover File")} htmlFor="voice-upload" help={t("Upload Voiceover File Help")}><input id="voice-upload" aria-label={t("Upload Voiceover File")} className="block w-full text-sm" type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg" onChange={(event) => setUpload(event.target.files?.[0] || null)} /></Field>
      <LocalAudioPreview file={uploadedAudio} label={t("Upload Voiceover File")} />
      <Field label={t("Voiceover Volume")} htmlFor="upload-volume" help={t("Voiceover Volume Help")}><Select id="upload-volume" value={params.voice_volume} onChange={(event) => setParam("voice_volume", Number(event.target.value))}>{volumeOptions.map((value) => <option key={value} value={value}>{value * 100}%</option>)}</Select></Field>
    </> : null}
    <BgmSettings />
  </Panel>;
}
