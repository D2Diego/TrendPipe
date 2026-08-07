import { apiUpload } from "./client";
export const uploadBgm = (file: File) => apiUpload<{ file: string }>("/musics", file);
export const uploadVideoMaterial = (file: File) => apiUpload<{ file: string }>("/video_materials", file);
export const uploadCustomAudio = (file: File) => apiUpload<{ file: string }>("/audio_upload", file);
