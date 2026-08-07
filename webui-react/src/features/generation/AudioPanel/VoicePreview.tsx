import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/api/client";
import { previewVoice, type VoicePreviewResult } from "@/api/voices";
import { Button } from "@/components/ui/button";
import { useGenerationStore } from "@/store/generationStore";
import { estimateVoiceoverDurationRange } from "./estimateVoiceoverDuration";

const SAMPLE = "Hello! This is a short preview of the selected voice.";

export function VoicePreview() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const params = useGenerationStore((state) => state.params);
  const provider = useGenerationStore((state) => state.ttsServer);
  const audio = useGenerationStore((state) => state.voicePreviewAudio);
  const setAudio = useGenerationStore((state) => state.setVoicePreviewAudio);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const estimate = estimateVoiceoverDurationRange(params.video_script, params.voice_rate);

  const request = async (kind: "sample" | "full", content: string) => {
    setPending(true); setError(null);
    try {
      const result = await queryClient.fetchQuery<VoicePreviewResult>({
        queryKey: ["voice-preview", kind, provider, content, params.voice_name, params.voice_rate, params.voice_volume],
        queryFn: () => previewVoice({ content, voice_name: params.voice_name, voice_rate: params.voice_rate, voice_volume: params.voice_volume }),
        staleTime: Infinity,
      });
      if (!result.audio_base64) setError(t("Voice Preview No Audio"));
      else setAudio({ audioBase64: result.audio_base64, mimeType: result.mime_type, duration: result.duration });
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 503 ? t("Voice Preview Busy") : t("Voice Preview Failed", { error: cause instanceof Error ? cause.message : String(cause) }));
    } finally { setPending(false); }
  };

  return <div className="space-y-2 border-t border-border pt-3">
    <p className="text-xs text-muted-foreground">{estimate ? t("Estimated Voiceover Duration", { min: estimate.min, max: estimate.max }) : t("Voiceover Script Required")}</p>
    <div className="grid grid-cols-2 gap-2">
      <Button type="button" disabled={pending || !params.voice_name} onClick={() => void request("sample", SAMPLE)}>{t("Play Voice")}</Button>
      <Button type="button" title={t("Full Voiceover Preview Cost Hint")} disabled={pending || !params.video_script.trim() || !params.voice_name} onClick={() => void request("full", params.video_script.trim())}>{t("Generate Full Voiceover Preview")}</Button>
    </div>
    {error ? <p role="alert" className="text-sm text-destructive-foreground">{error}</p> : null}
    {audio ? <><audio role="audio" className="w-full" controls autoPlay src={`data:${audio.mimeType};base64,${audio.audioBase64}`} />{audio.duration ? <p className="text-xs text-muted-foreground">{t("Actual Voiceover Duration", { duration: audio.duration.toFixed(1) })}</p> : null}</> : null}
  </div>;
}
