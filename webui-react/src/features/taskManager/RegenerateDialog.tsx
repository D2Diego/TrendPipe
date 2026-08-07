import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getTaskRestoreParams } from "@/api/taskHistory";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { useGenerationStore } from "@/store/generationStore";
import type { VideoParams } from "@/types/videoParams";

export function inferTtsServerFromVoice(voiceName: string): string {
  if (voiceName.startsWith("siliconflow:")) return "siliconflow";
  if (voiceName.startsWith("gemini:")) return "gemini-tts";
  if (voiceName.startsWith("mimo:")) return "mimo-tts";
  if (voiceName.startsWith("elevenlabs:")) return "elevenlabs";
  if (voiceName.startsWith("chatterbox:")) return "chatterbox";
  const normalized = voiceName.replace(/-(Female|Male)$/u, "").trim();
  return normalized.endsWith("-V2") ? "azure-tts-v2" : "azure-tts-v1";
}

export function RegenerateDialog({ open, taskId, onClose, onLoaded }: { open: boolean; taskId: string | null; onClose: () => void; onLoaded?: (message: string) => void }) {
  const { t } = useTranslation();
  const restore = useMutation({ mutationFn: () => getTaskRestoreParams(taskId!), onSuccess: (payload) => {
    const params = payload.params as unknown as VideoParams;
    const store = useGenerationStore.getState();
    store.loadParams(params);
    store.setUploadedAudioFile(null); store.setUploadedBgmFile(null); store.setLocalFilesToUpload([]); store.setLocalVideoMaterials([]);
    if (params.custom_audio_file) { store.setVoiceMode("upload"); store.setRestoredCustomAudioMissing(true); }
    else if (params.voice_name === "no-voice") store.setVoiceMode("none");
    else { store.setVoiceMode("tts"); store.setTtsServer(inferTtsServerFromVoice(params.voice_name || "")); }
    const requirements = [params.video_source === "local" ? t("Task Restore Local Materials Warning") : "", params.custom_audio_file ? t("Task Restore Custom Audio Warning") : ""].filter(Boolean);
    onLoaded?.([t("Task Configuration Loaded"), ...requirements].join(" "));
    onClose();
  }});
  return <Dialog open={open} onClose={onClose} title={t("Regenerate")}><div className="space-y-4"><p>{t("Regenerate Task Confirmation")}</p>{restore.error ? <p role="alert" className="text-sm text-destructive-foreground">{String(restore.error)}</p> : null}<div className="flex justify-end gap-2"><Button type="button" onClick={onClose}>{t("Cancel")}</Button><Button type="button" variant="primary" disabled={!taskId || restore.isPending} onClick={() => restore.mutate()}>{t("Load Task Configuration")}</Button></div></div></Dialog>;
}
