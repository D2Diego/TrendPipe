import { create } from "zustand";
import { DEFAULT_VIDEO_PARAMS, type VideoParams } from "@/types/videoParams";

export type VoiceMode = "tts" | "upload" | "none";
export interface VoicePreviewAudio { audioBase64: string; mimeType: string; duration: number | null }

interface GenerationState {
  params: VideoParams;
  voiceMode: VoiceMode;
  ttsServer: string;
  uploadedAudioFile: File | null;
  uploadedBgmFile: File | null;
  localFilesToUpload: File[];
  localVideoMaterials: string[];
  voicePreviewAudio: VoicePreviewAudio | null;
  currentGenerationTaskId: string | null;
  videoCodec: string;
  restoredCustomAudioMissing: boolean;
  setParam: <K extends keyof VideoParams>(key: K, value: VideoParams[K]) => void;
  loadParams: (params: VideoParams) => void;
  setVoiceMode: (mode: VoiceMode) => void;
  setTtsServer: (server: string) => void;
  setUploadedAudioFile: (file: File | null) => void;
  setUploadedBgmFile: (file: File | null) => void;
  setLocalFilesToUpload: (files: File[]) => void;
  setLocalVideoMaterials: (materials: string[]) => void;
  setVoicePreviewAudio: (audio: VoicePreviewAudio | null) => void;
  setCurrentGenerationTaskId: (taskId: string | null) => void;
  setVideoCodec: (codec: string) => void;
  setRestoredCustomAudioMissing: (missing: boolean) => void;
  reset: () => void;
}

const uiDefaults = {
  voiceMode: "tts" as VoiceMode,
  ttsServer: "azure-tts-v1",
  uploadedAudioFile: null,
  uploadedBgmFile: null,
  localFilesToUpload: [] as File[],
  localVideoMaterials: [] as string[],
  voicePreviewAudio: null,
  currentGenerationTaskId: null,
  videoCodec: "default",
  restoredCustomAudioMissing: false,
};

export const useGenerationStore = create<GenerationState>((set) => ({
  params: { ...DEFAULT_VIDEO_PARAMS },
  ...uiDefaults,
  setParam: (key, value) => set((state) => ({ params: { ...state.params, [key]: value } })),
  loadParams: (params) => set({ params }),
  setVoiceMode: (voiceMode) => set((state) => ({ voiceMode, restoredCustomAudioMissing: voiceMode === "upload" ? state.restoredCustomAudioMissing : false })),
  setTtsServer: (ttsServer) => set({ ttsServer }),
  setUploadedAudioFile: (uploadedAudioFile) => set({ uploadedAudioFile, ...(uploadedAudioFile ? { restoredCustomAudioMissing: false } : {}) }),
  setUploadedBgmFile: (uploadedBgmFile) => set({ uploadedBgmFile }),
  setLocalFilesToUpload: (localFilesToUpload) => set({ localFilesToUpload }),
  setLocalVideoMaterials: (localVideoMaterials) => set({ localVideoMaterials }),
  setVoicePreviewAudio: (voicePreviewAudio) => set({ voicePreviewAudio }),
  setCurrentGenerationTaskId: (currentGenerationTaskId) => set({ currentGenerationTaskId }),
  setVideoCodec: (videoCodec) => set({ videoCodec }),
  setRestoredCustomAudioMissing: (restoredCustomAudioMissing) => set({ restoredCustomAudioMissing }),
  reset: () => set({ params: { ...DEFAULT_VIDEO_PARAMS }, ...uiDefaults }),
}));
