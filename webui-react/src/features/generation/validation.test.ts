import { describe, expect, it } from "vitest";
import { DEFAULT_VIDEO_PARAMS } from "@/types/videoParams";
import { validateBeforeSubmit, type ValidationContext } from "./validation";

const valid: ValidationContext = {
  params: { ...DEFAULT_VIDEO_PARAMS, video_subject: "cats" }, voiceMode: "tts",
  hasLocalMaterials: false, hasUploadedAudio: false,
  readiness: { pexels: true, pixabay: true, coverr: true, sonilo: true, elevenlabs: true },
};

describe("validateBeforeSubmit", () => {
  it("returns the first Streamlit-equivalent validation error", () => {
    expect(validateBeforeSubmit(valid)).toBeNull();
    expect(validateBeforeSubmit({ ...valid, params: { ...valid.params, video_subject: "", video_script: "" } })).toMatch(/cannot both be empty/i);
    expect(validateBeforeSubmit({ ...valid, params: { ...valid.params, video_source: "local" } })).toMatch(/local material/i);
    expect(validateBeforeSubmit({ ...valid, voiceMode: "upload" })).toMatch(/voiceover file/i);
  });
});
