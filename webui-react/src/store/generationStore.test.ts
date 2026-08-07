import { beforeEach, describe, expect, it } from "vitest";
import { useGenerationStore } from "./generationStore";

describe("generation store", () => {
  beforeEach(() => useGenerationStore.getState().reset());
  it("updates a parameter without mutating the previous object", () => {
    const before = useGenerationStore.getState().params;
    useGenerationStore.getState().setParam("video_subject", "cats");
    expect(useGenerationStore.getState().params).not.toBe(before);
    expect(useGenerationStore.getState().params.video_subject).toBe("cats");
  });
  it("restores UI and request defaults", () => {
    useGenerationStore.getState().setVoiceMode("upload");
    useGenerationStore.getState().setCurrentGenerationTaskId("task");
    useGenerationStore.getState().reset();
    expect(useGenerationStore.getState()).toEqual(expect.objectContaining({ voiceMode: "tts", currentGenerationTaskId: null }));
  });
  it("loads restored parameters", () => {
    useGenerationStore.getState().loadParams({ video_subject: "restored" } as never);
    expect(useGenerationStore.getState().params.video_subject).toBe("restored");
  });
});
