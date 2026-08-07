import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import * as providersApi from "@/api/providers";
import { LlmSettingsTab } from "./LlmSettingsTab";

function renderTab() { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><I18nextProvider i18n={i18n}><LlmSettingsTab /></I18nextProvider></QueryClientProvider>); }

describe("LlmSettingsTab", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(providersApi, "listLlmProviders").mockResolvedValue({ providers: [{ provider_id: "moonshot", default_label: "Moonshot", adapter: "openai_compatible", api_key_url: "", default_model: "model", default_base_url: "https://example.com", requires_api_key: true, requires_model_name: true, requires_base_url: true, show_api_key: true, show_base_url: true }] });
    vi.spyOn(configApi, "getConfigSection").mockResolvedValue({ llm_provider: "moonshot" });
    vi.spyOn(configApi, "setConfigValue").mockResolvedValue({ updated: true });
  });
  it("loads provider fields and saves text on blur", async () => {
    renderTab();
    const input = await screen.findByLabelText(i18n.t("API Key"));
    fireEvent.change(input, { target: { value: "sk-test" } });
    expect(configApi.setConfigValue).not.toHaveBeenCalled();
    fireEvent.blur(input);
    await waitFor(() => expect(configApi.setConfigValue).toHaveBeenCalledWith("app", "moonshot_api_key", "sk-test"));
  });
  it("tests the saved connection", async () => {
    vi.spyOn(providersApi, "testLlmConnection").mockResolvedValue({ ok: true, error: "", elapsed: 0.5 });
    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("Test LLM Connection") }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("0.50"));
  });
});
