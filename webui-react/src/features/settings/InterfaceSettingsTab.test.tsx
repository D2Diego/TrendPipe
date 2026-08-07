import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import { InterfaceSettingsTab } from "./InterfaceSettingsTab";

describe("InterfaceSettingsTab", () => {
  it("persists Hide Log immediately", async () => {
    vi.spyOn(configApi, "getUiConfig").mockResolvedValue({ hide_log: false });
    vi.spyOn(configApi, "setUiConfigValue").mockResolvedValue({ updated: true });
    render(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><InterfaceSettingsTab /></I18nextProvider></QueryClientProvider>);
    fireEvent.click(await screen.findByLabelText(i18n.t("Hide Log")));
    await waitFor(() => expect(configApi.setUiConfigValue).toHaveBeenCalledWith("hide_log", true));
  });
});
