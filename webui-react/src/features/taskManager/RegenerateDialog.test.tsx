import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as api from "@/api/taskHistory";
import { useGenerationStore } from "@/store/generationStore";
import { inferTtsServerFromVoice, RegenerateDialog } from "./RegenerateDialog";

describe("RegenerateDialog", () => {
  beforeEach(() => { vi.restoreAllMocks(); useGenerationStore.getState().reset(); });
  it("loads params and marks custom audio for re-upload", async () => {
    vi.spyOn(api, "getTaskRestoreParams").mockResolvedValue({ task_id: "t1", subject: "cats", params: { video_subject: "restored", custom_audio_file: "old.mp3" } });
    const onClose = vi.fn();
    render(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><RegenerateDialog open taskId="t1" onClose={onClose} /></I18nextProvider></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Load Task Configuration") }));
    await waitFor(() => expect(useGenerationStore.getState().params.video_subject).toBe("restored"));
    expect(useGenerationStore.getState()).toEqual(expect.objectContaining({ voiceMode: "upload", restoredCustomAudioMissing: true }));
    expect(onClose).toHaveBeenCalled();
  });
  it("cancels without loading", () => {
    const request = vi.spyOn(api, "getTaskRestoreParams"); const onClose = vi.fn();
    render(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><RegenerateDialog open taskId="t1" onClose={onClose} /></I18nextProvider></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Cancel") }));
    expect(request).not.toHaveBeenCalled(); expect(onClose).toHaveBeenCalled();
  });
  it("infers the original TTS provider from stored voice identifiers", () => {
    expect(inferTtsServerFromVoice("siliconflow:model:voice-Female")).toBe("siliconflow");
    expect(inferTtsServerFromVoice("gemini:Kore-Female")).toBe("gemini-tts");
    expect(inferTtsServerFromVoice("elevenlabs:id:name")).toBe("elevenlabs");
    expect(inferTtsServerFromVoice("en-US-AvaMultilingualNeural-V2-Female")).toBe("azure-tts-v2");
    expect(inferTtsServerFromVoice("en-US-JennyNeural-Female")).toBe("azure-tts-v1");
  });
});
