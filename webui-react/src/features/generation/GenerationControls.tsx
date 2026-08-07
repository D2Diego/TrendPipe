import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getGenerationReadiness } from "@/api/config";
import { uploadBgm, uploadCustomAudio, uploadVideoMaterial } from "@/api/uploads";
import { createVideoTask } from "@/api/videos";
import { Button } from "@/components/ui/button";
import { useGenerationStore } from "@/store/generationStore";
import type { MaterialInfo, VideoParams } from "@/types/videoParams";
import { TaskProgressView } from "./TaskProgressView";
import { validateBeforeSubmit } from "./validation";

class SubmissionValidationError extends Error {}

export function GenerationControls() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const params = useGenerationStore((state) => state.params);
  const voiceMode = useGenerationStore((state) => state.voiceMode);
  const audioFile = useGenerationStore((state) => state.uploadedAudioFile);
  const bgmFile = useGenerationStore((state) => state.uploadedBgmFile);
  const localFiles = useGenerationStore((state) => state.localFilesToUpload);
  const savedLocal = useGenerationStore((state) => state.localVideoMaterials);
  const setSavedLocal = useGenerationStore((state) => state.setLocalVideoMaterials);
  const setTaskId = useGenerationStore((state) => state.setCurrentGenerationTaskId);
  const restoredCustomAudioMissing = useGenerationStore((state) => state.restoredCustomAudioMissing);

  const submit = useMutation({ mutationFn: async () => {
    const readiness = await queryClient.fetchQuery({ queryKey: ["generation-readiness"], queryFn: getGenerationReadiness, staleTime: 10_000 });
    const validation = validateBeforeSubmit({ params, voiceMode, hasLocalMaterials: localFiles.length > 0 || savedLocal.length > 0, hasUploadedAudio: Boolean(audioFile), readiness, restoredCustomAudioMissing });
    if (validation) throw new SubmissionValidationError(validation);

    const request: VideoParams = { ...params };
    if (voiceMode === "none") { request.voice_name = "no-voice"; request.custom_audio_file = null; }
    if (voiceMode === "tts") request.custom_audio_file = null;
    if (voiceMode === "upload" && audioFile) request.custom_audio_file = (await uploadCustomAudio(audioFile)).file;
    if (bgmFile && request.bgm_type === "custom" && request.bgm_volume > 0) request.bgm_file = (await uploadBgm(bgmFile)).file;
    if (bgmFile && request.bgm_volume <= 0) request.bgm_file = "";

    if (localFiles.length) {
      const uploaded = await Promise.all(localFiles.map(uploadVideoMaterial));
      const paths = uploaded.map((item) => item.file);
      request.video_materials = paths.map<MaterialInfo>((url) => ({ provider: "local", url, duration: 0 }));
      setSavedLocal(paths);
    } else if (request.video_source === "local") {
      request.video_materials = savedLocal.map((url) => ({ provider: "local", url, duration: 0 }));
    } else request.video_materials = null;

    const task = await createVideoTask(request);
    setTaskId(task.task_id);
    return task;
  }});
  const message = submit.error instanceof SubmissionValidationError ? submit.error.message : submit.error ? t("Video Generation Failed") : null;
  return <div className="space-y-4 px-4 pb-8">
    <Button data-tour-id="generate-video" variant="primary" className="w-full py-3" type="button" disabled={submit.isPending} onClick={() => submit.mutate()}>{submit.isPending ? t("Generating Video") : t("Generate Video")}</Button>
    {message ? <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/20 p-3 text-sm text-destructive-foreground">{message}</p> : null}
    <TaskProgressView />
  </div>;
}
