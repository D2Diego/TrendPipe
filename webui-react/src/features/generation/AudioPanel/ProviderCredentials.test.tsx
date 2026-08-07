import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import { ProviderCredentials } from "./ProviderCredentials";

describe("ProviderCredentials", () => {
  it("loads and persists provider-specific credentials", async () => {
    vi.spyOn(configApi, "getConfigSection").mockResolvedValue({ speech_region: "eastus", speech_key: "old" });
    vi.spyOn(configApi, "setConfigValue").mockResolvedValue({ updated: true });
    render(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><ProviderCredentials provider="azure-tts-v2" /></I18nextProvider></QueryClientProvider>);
    const key = await screen.findByLabelText(i18n.t("Speech Key"));
    fireEvent.change(key, { target: { value: "new" } }); fireEvent.blur(key);
    await waitFor(() => expect(configApi.setConfigValue).toHaveBeenCalledWith("azure", "speech_key", "new"));
  });
});
