import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResearchListPage } from "./ResearchListPage";
import * as researchApi from "@/api/research";

const completed = {
  id: "r1", topic: "cats", status: "completed" as const, depth: "quick" as const,
  sources: ["reddit"], error_message: null, report_json: null, created_at: "", updated_at: "",
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><MemoryRouter><ResearchListPage /></MemoryRouter></QueryClientProvider>);
}

describe("ResearchListPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("lists past researches and links to their detail", async () => {
    vi.spyOn(researchApi, "listResearches").mockResolvedValue({ researches: [completed] });
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({ available_sources: [] });
    renderPage();

    await waitFor(() => expect(screen.getByRole("link", { name: "cats" })).toHaveAttribute("href", "/researches/r1"));
    expect(screen.getByText(/completed/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /research credentials|credenciais de pesquisa/i })).not.toBeInTheDocument();
  });

  it("deletes a research after confirmation", async () => {
    vi.spyOn(researchApi, "listResearches").mockResolvedValue({ researches: [completed] });
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({ available_sources: [] });
    const deleteMock = vi.spyOn(researchApi, "deleteResearch").mockResolvedValue({ deleted: true });
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: /delete|excluir/i }));
    await userEvent.click(screen.getByRole("button", { name: /confirm/i }));
    await waitFor(() => expect(deleteMock).toHaveBeenCalledWith("r1"));
  });

  it("disables deletion while running", async () => {
    vi.spyOn(researchApi, "listResearches").mockResolvedValue({ researches: [{ ...completed, status: "running" }] });
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({ available_sources: [] });
    renderPage();

    expect(await screen.findByRole("button", { name: /delete|excluir/i })).toBeDisabled();
  });
});
