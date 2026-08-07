import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as fontsApi from "@/api/fonts";
import * as configApi from "@/api/config";
import { useGenerationStore } from "@/store/generationStore";
import { SubtitlePanel } from "./SubtitlePanel";

describe("SubtitlePanel", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en"); vi.restoreAllMocks();
    vi.spyOn(fontsApi, "listFonts").mockResolvedValue({ fonts: ["MicrosoftYaHeiBold.ttc"] });
    vi.spyOn(fontsApi, "checkFontSupport").mockResolvedValue({ supported: true });
    vi.spyOn(configApi, "getUiConfig").mockResolvedValue({});
    vi.spyOn(configApi, "setUiConfigValue").mockResolvedValue({ updated: true });
    useGenerationStore.getState().reset();
  });
  it("gates controls and validates a custom position", () => {
    render(<QueryClientProvider client={new QueryClient()}><SubtitlePanel /></QueryClientProvider>);
    fireEvent.click(screen.getByLabelText(i18n.t("Enable Subtitles")));
    expect(screen.getByLabelText(i18n.t("Font"))).toBeDisabled();
    fireEvent.click(screen.getByLabelText(i18n.t("Enable Subtitles")));
    fireEvent.change(screen.getByLabelText(i18n.t("Position")), { target: { value: "custom" } });
    fireEvent.change(screen.getByLabelText(i18n.t("Custom Position (% from top)")), { target: { value: "150" } });
    expect(screen.getByRole("alert")).toHaveTextContent(/0.*100/);
  });
  it("hydrates persisted subtitle preferences and warns about unsupported text", async () => {
    vi.mocked(configApi.getUiConfig).mockResolvedValue({ font_size: 72, subtitle_position: "top" });
    vi.mocked(fontsApi.checkFontSupport).mockResolvedValue({ supported: false });
    useGenerationStore.getState().setParam("video_subject", "Olá");
    render(<QueryClientProvider client={new QueryClient()}><SubtitlePanel /></QueryClientProvider>);
    expect(await screen.findByText(i18n.t("Subtitle Font Does Not Support Text"))).toBeInTheDocument();
    expect(useGenerationStore.getState().params).toEqual(expect.objectContaining({ font_size: 72, subtitle_position: "top" }));
  });
});
