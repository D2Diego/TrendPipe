import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import { useGenerationStore } from "@/store/generationStore";
import { VideoPanel } from "./VideoPanel";

describe("VideoPanel", () => {
  const renderPanel = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><VideoPanel /></QueryClientProvider>);
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(configApi, "getUiConfig").mockResolvedValue({});
    vi.spyOn(configApi, "setUiConfigValue").mockResolvedValue({ updated: true });
    void i18n.changeLanguage("en");
    useGenerationStore.getState().reset();
  });
  it("locks sequential concatenation while ordered matching is enabled", () => {
    renderPanel();
    fireEvent.click(screen.getByLabelText(i18n.t("Match Materials to Script Order")));
    expect(useGenerationStore.getState().params).toEqual(expect.objectContaining({ match_materials_to_script: true, video_concat_mode: "sequential" }));
    expect(screen.getByLabelText(i18n.t("Video Concat Mode"))).toBeDisabled();
  });
  it("only offers local uploads for the local source", () => {
    renderPanel();
    fireEvent.change(screen.getByLabelText(i18n.t("Video Source")), { target: { value: "local" } });
    expect(screen.getByLabelText(i18n.t("Upload Local Files"))).toBeInTheDocument();
  });
});
