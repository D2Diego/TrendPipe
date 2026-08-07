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

  it("shows credential presence without exposing values", async () => {
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({
      available_sources: ["reddit"],
      permission_preflight: { credentials: { openrouter: { present: true, label: "OpenRouter API key" } } },
    });
    renderPage();

    await waitFor(() => expect(screen.getByText(/OpenRouter API key/i)).toBeInTheDocument());
    expect(screen.getByText(/configured/i)).toBeInTheDocument();
    expect(screen.getByText(/reddit/i)).toBeInTheDocument();
  });

  it("saves entered keys", async () => {
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({ available_sources: [] });
    const saveMock = vi.spyOn(researchApi, "updateResearchSettings").mockResolvedValue({ saved: true });
    renderPage();

    await userEvent.type(await screen.findByLabelText(/OPENROUTER_API_KEY/i), "sk-or-abc");
    await userEvent.click(screen.getByRole("button", { name: /save|salvar/i }));
    await waitFor(() => expect(saveMock).toHaveBeenCalledWith({ OPENROUTER_API_KEY: "sk-or-abc" }));
  });
});
