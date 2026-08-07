import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import { MaterialApiTab } from "./MaterialApiTab";

describe("MaterialApiTab", () => {
  beforeEach(() => { vi.restoreAllMocks(); vi.spyOn(configApi, "getConfigSection").mockResolvedValue({ pexels_api_keys: ["a", "b"], pixabay_api_keys: [], coverr_api_keys: [] }); vi.spyOn(configApi, "setConfigValue").mockResolvedValue({ updated: true }); });
  it("loads and persists comma-separated keys as lists", async () => {
    render(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><MaterialApiTab /></I18nextProvider></QueryClientProvider>);
    expect((await screen.findByLabelText(i18n.t("Pexels API Key")) as HTMLInputElement).value).toBe("a,b");
    const pixabay = screen.getByLabelText(i18n.t("Pixabay API Key"));
    fireEvent.change(pixabay, { target: { value: "x, y ,,z" } });
    fireEvent.blur(pixabay);
    await waitFor(() => expect(configApi.setConfigValue).toHaveBeenCalledWith("app", "pixabay_api_keys", ["x", "y", "z"]));
  });
});
