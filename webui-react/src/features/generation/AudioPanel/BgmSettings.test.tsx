import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import * as providersApi from "@/api/providers";
import { useGenerationStore } from "@/store/generationStore";
import { BgmSettings } from "./BgmSettings";

describe("BgmSettings", () => {
  const renderSettings = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><BgmSettings /></QueryClientProvider>);
  beforeEach(() => {
    vi.restoreAllMocks();
    void i18n.changeLanguage("en");
    useGenerationStore.getState().reset();
    vi.spyOn(configApi, "getConfigSection").mockResolvedValue({});
    vi.spyOn(configApi, "setConfigValue").mockResolvedValue({ updated: true });
  });
  it("reveals custom music controls and binds volume", () => {
    renderSettings();
    fireEvent.change(screen.getByLabelText(i18n.t("Background Music Source")), { target: { value: "custom" } });
    expect(screen.getByLabelText(i18n.t("Upload Background Music"))).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(i18n.t("Background Music Volume")), { target: { value: "0.5" } });
    expect(useGenerationStore.getState().params.bgm_volume).toBe(0.5);
  });
  it("persists the Sonilo key and tests the configured connection", async () => {
    vi.spyOn(providersApi, "testSoniloConnection").mockResolvedValue({ ok: true, error: "" });
    renderSettings();
    fireEvent.change(screen.getByLabelText(i18n.t("Background Music Source")), { target: { value: "sonilo" } });
    const key = await screen.findByLabelText(i18n.t("Sonilo API Key"));
    fireEvent.change(key, { target: { value: "secret" } });
    fireEvent.blur(key);
    expect(configApi.setConfigValue).toHaveBeenCalledWith("app", "sonilo_api_key", "secret");
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Test Sonilo Connection") }));
    expect(await screen.findByText(i18n.t("Sonilo Connection Test Succeeded"))).toBeInTheDocument();
  });
});
