import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import * as voicesApi from "@/api/voices";
import { useGenerationStore } from "@/store/generationStore";
import { AudioPanel } from "./AudioPanel";

describe("AudioPanel", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
    vi.restoreAllMocks();
    vi.spyOn(configApi, "getUiConfig").mockResolvedValue({});
    vi.spyOn(configApi, "getConfigSection").mockResolvedValue({});
    vi.spyOn(configApi, "setUiConfigValue").mockResolvedValue({ updated: true });
    useGenerationStore.getState().reset();
  });
  it("loads provider voices and switches cleanly to upload mode", async () => {
    vi.spyOn(voicesApi, "listVoices").mockResolvedValue({ voices: ["en-US-JennyNeural-Female"] });
    render(<QueryClientProvider client={new QueryClient()}><AudioPanel /></QueryClientProvider>);
    await waitFor(() => expect(voicesApi.listVoices).toHaveBeenCalledWith("azure-tts-v1"));
    fireEvent.click(screen.getByRole("radio", { name: i18n.t("Upload Voiceover") }));
    expect(useGenerationStore.getState().voiceMode).toBe("upload");
    expect(screen.queryByLabelText(i18n.t("Voiceover Voice"))).not.toBeInTheDocument();
    expect(screen.getByLabelText(i18n.t("Upload Voiceover File"))).toBeInTheDocument();
  });
});
