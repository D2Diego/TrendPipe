import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResearcherSettingsTab } from "./ResearchSettingsPage";
import * as researchApi from "@/api/research";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><MemoryRouter><ResearcherSettingsTab /></MemoryRouter></QueryClientProvider>);
}

describe("ResearcherSettingsTab", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows available sources and one row per credential key with per-key status", async () => {
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({
      available_sources: ["reddit"],
      credential_keys: { OPENROUTER_API_KEY: true, SCRAPECREATORS_API_KEY: false },
    });
    renderPage();

    await waitFor(() => expect(screen.getByText(/reddit/i)).toBeInTheDocument());
    expect(screen.getByText("OPENROUTER_API_KEY")).toBeInTheDocument();
    expect(screen.getByText("SCRAPECREATORS_API_KEY")).toBeInTheDocument();
    expect(screen.getAllByText(/configured/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/missing/i).length).toBeGreaterThan(0);
  });

  it("saves an entered key for one row without affecting others", async () => {
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({
      available_sources: [],
      credential_keys: { OPENROUTER_API_KEY: false, GOOGLE_API_KEY: false },
    });
    const saveMock = vi.spyOn(researchApi, "updateResearchSettings").mockResolvedValue({ saved: true });
    renderPage();

    await userEvent.type(await screen.findByLabelText("OPENROUTER_API_KEY"), "sk-or-abc");
    const saveButtons = screen.getAllByRole("button", { name: /save/i });
    await userEvent.click(saveButtons[0]);

    await waitFor(() => expect(saveMock).toHaveBeenCalledWith({ OPENROUTER_API_KEY: "sk-or-abc" }));
  });
});
