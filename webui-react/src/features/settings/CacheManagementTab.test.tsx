import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as cacheApi from "@/api/cache";
import { CacheManagementTab } from "./CacheManagementTab";

describe("CacheManagementTab", () => {
  beforeEach(() => { vi.restoreAllMocks(); vi.spyOn(cacheApi, "getCacheStats").mockResolvedValue({ file_count: 3, total_size: 5242880, oldest_mtime: 1700000000, newest_mtime: 1700003600 }); });
  it("requires confirmation and cleans the selected cache range", async () => {
    vi.spyOn(cacheApi, "cleanCache").mockResolvedValue({ deleted_count: 3, deleted_size: 5242880, failed_count: 0 });
    render(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><CacheManagementTab /></I18nextProvider></QueryClientProvider>);
    await screen.findByText("3");
    const clean = screen.getByRole("button", { name: i18n.t("Clean Cache Now") });
    expect(clean).toBeDisabled();
    fireEvent.click(screen.getByLabelText(i18n.t("Confirm Cache Cleanup")));
    fireEvent.click(clean);
    await waitFor(() => expect(cacheApi.cleanCache).toHaveBeenCalled());
  });
});
