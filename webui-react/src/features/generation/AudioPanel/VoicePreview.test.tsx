import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { useGenerationStore } from "@/store/generationStore";
import * as voicesApi from "@/api/voices";
import { VoicePreview } from "./VoicePreview";

describe("VoicePreview", () => {
  beforeEach(() => { void i18n.changeLanguage("en"); vi.restoreAllMocks(); useGenerationStore.getState().reset(); useGenerationStore.getState().setParam("voice_name", "en-US-JennyNeural-Female"); });
  it("previews full script audio and retains it for playback", async () => {
    useGenerationStore.getState().setParam("video_script", "A test script.");
    vi.spyOn(voicesApi, "previewVoice").mockResolvedValue({ audio_base64: "ZmFrZQ==", mime_type: "audio/mpeg", duration: 2 });
    render(<QueryClientProvider client={new QueryClient()}><VoicePreview /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Generate Full Voiceover Preview") }));
    await waitFor(() => expect(screen.getByRole("audio")).toBeInTheDocument());
    expect(useGenerationStore.getState().voicePreviewAudio?.duration).toBe(2);
  });
});
