export interface MaterialInfo {
  provider: string;
  url: string;
  duration?: number;
  source_info?: Record<string, unknown> | null;
}

export interface VideoParams {
  video_subject: string;
  video_script: string;
  video_terms: string | string[] | null;
  video_aspect: "9:16" | "16:9" | "1:1";
  video_concat_mode: "random" | "sequential";
  video_transition_mode: string | null;
  video_clip_duration: number;
  video_clip_speed: number;
  match_materials_to_script: boolean;
  video_count: number;
  video_source: string;
  video_materials: MaterialInfo[] | null;
  custom_audio_file: string | null;
  video_language: string;
  voice_name: string;
  voice_volume: number;
  voice_rate: number;
  bgm_type: string;
  bgm_file: string;
  bgm_volume: number;
  video_music_prompt: string;
  sonilo_bgm_prompt: string;
  subtitle_enabled: boolean;
  subtitle_position: string;
  custom_position: number;
  font_name: string;
  text_fore_color: string;
  text_background_color: string | boolean;
  rounded_subtitle_background: boolean;
  font_size: number;
  stroke_color: string;
  stroke_width: number;
  n_threads: number;
  paragraph_number: number;
  video_script_prompt: string;
  custom_system_prompt: string;
}

export const DEFAULT_VIDEO_PARAMS: VideoParams = {
  video_subject: "", video_script: "", video_terms: null,
  video_aspect: "9:16", video_concat_mode: "random", video_transition_mode: null,
  video_clip_duration: 3, video_clip_speed: 1, match_materials_to_script: false,
  video_count: 1, video_source: "pexels", video_materials: null,
  custom_audio_file: null, video_language: "", voice_name: "",
  voice_volume: 1, voice_rate: 1, bgm_type: "random", bgm_file: "",
  bgm_volume: 0.2, video_music_prompt: "", sonilo_bgm_prompt: "",
  subtitle_enabled: true, subtitle_position: "bottom", custom_position: 70,
  font_name: "MicrosoftYaHeiBold.ttc", text_fore_color: "#FFFFFF",
  text_background_color: false, rounded_subtitle_background: false,
  font_size: 60, stroke_color: "#000000", stroke_width: 1.5,
  n_threads: 2, paragraph_number: 1, video_script_prompt: "", custom_system_prompt: "",
};
