import i18n from "@/i18n";
import type { GenerationReadiness } from "@/api/config";
import type { VoiceMode } from "@/store/generationStore";
import type { VideoParams } from "@/types/videoParams";

export interface ValidationContext {
  params: VideoParams;
  voiceMode: VoiceMode;
  hasLocalMaterials: boolean;
  hasUploadedAudio: boolean;
  readiness: GenerationReadiness;
  restoredCustomAudioMissing?: boolean;
}

export function validateBeforeSubmit(context: ValidationContext): string | null {
  const { params, readiness } = context;
  if (!params.video_subject.trim() && !params.video_script.trim()) return i18n.t("Video Script and Subject Cannot Both Be Empty");
  if (!["pexels", "pixabay", "coverr", "local"].includes(params.video_source)) return i18n.t("Please Select a Valid Video Source");
  if (params.video_source === "pexels" && !readiness.pexels) return i18n.t("Please Enter the Pexels API Key");
  if (params.video_source === "pixabay" && !readiness.pixabay) return i18n.t("Please Enter the Pixabay API Key");
  if (params.video_source === "coverr" && !readiness.coverr) return i18n.t("Please Enter the Coverr API Key");
  if (params.bgm_type === "sonilo" && params.bgm_volume > 0 && !readiness.sonilo) return i18n.t("Sonilo API Key Required");
  if (params.bgm_type === "elevenlabs" && params.bgm_volume > 0 && !readiness.elevenlabs) return i18n.t("ElevenLabs API Key Required");
  if (params.video_source === "local" && !context.hasLocalMaterials) return i18n.t("Please Upload Local Materials First");
  if (context.voiceMode === "upload" && !context.hasUploadedAudio) return i18n.t("Please Upload Voiceover File First");
  if (context.restoredCustomAudioMissing) return i18n.t("Task Restore Custom Audio Warning");
  return null;
}
